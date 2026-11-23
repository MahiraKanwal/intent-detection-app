"""Trains and evaluates the intent classifier.

Pipeline : clean_text -> TF-IDF (word 1-2 grams + char 2-5 grams) -> classifier
Compared : Naive Bayes, Linear SVM, Logistic Regression, Logistic Regression (word features only)
Evaluation:
  1. 5-fold cross-validation on the training split
  2. held-out test split (20%)
  3. "hard test": hand-written sentences that do NOT come from the generator templates
Outputs  : models/intent_model.joblib, models/metrics.json, static/img/*.png

Run:  python train.py
"""
import json
import time
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_validate, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

from core.preprocess import clean_text

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "intents.csv"
HARD = ROOT / "data" / "hard_test.csv"
MODEL_PATH = ROOT / "models" / "intent_model.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"
IMG = ROOT / "static" / "img"
SEED = 42

BG, FG, MUTED, ACCENT, ACCENT2 = "#0d1226", "#e9edf8", "#8b94b3", "#7c6cff", "#37e0c2"


def word_tfidf():
    return TfidfVectorizer(preprocessor=clean_text, ngram_range=(1, 2), sublinear_tf=True)


def char_tfidf():
    return TfidfVectorizer(preprocessor=clean_text, analyzer="char_wb", ngram_range=(2, 5),
                           sublinear_tf=True, min_df=2)


def features():
    return FeatureUnion([("word", word_tfidf()), ("char", char_tfidf())])


def build(clf, word_only=False):
    return Pipeline([("tfidf", word_tfidf() if word_only else features()), ("clf", clf)])


def style_axes(ax):
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_color(MUTED)
    ax.tick_params(colors=MUTED)


def plot_confusion(cm, labels, path):
    fig, ax = plt.subplots(figsize=(8.5, 7.2), facecolor=BG)
    style_axes(ax)
    im = ax.imshow(cm, cmap="viridis")
    ax.set_xticks(range(len(labels)), labels, rotation=60, ha="right", color=FG, fontsize=8)
    ax.set_yticks(range(len(labels)), labels, color=FG, fontsize=8)
    ax.set_xlabel("Predicted intent", color=FG)
    ax.set_ylabel("True intent", color=FG)
    for i in range(len(labels)):
        for j in range(len(labels)):
            if cm[i, j]:
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=8,
                        color="white" if cm[i, j] < cm.max() * 0.6 else "black")
    ax.set_title("Confusion matrix on hand-written hard-test set", color=FG, pad=12)
    fig.colorbar(im, ax=ax, fraction=0.046).ax.tick_params(colors=MUTED)
    fig.tight_layout()
    fig.savefig(path, dpi=140, facecolor=BG)
    plt.close(fig)


def plot_comparison(rows, path):
    names = [r["name"] for r in rows]
    cv = [r["cv_f1"] * 100 for r in rows]
    hard = [r["hard_acc"] * 100 for r in rows]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8.5, 4.4), facecolor=BG)
    style_axes(ax)
    ax.bar(x - 0.2, cv, 0.4, label="5-fold CV macro-F1", color=ACCENT)
    ax.bar(x + 0.2, hard, 0.4, label="Hard-test accuracy", color=ACCENT2)
    for xi, v in zip(x - 0.2, cv):
        ax.text(xi, v + 0.6, f"{v:.1f}", ha="center", color=FG, fontsize=8)
    for xi, v in zip(x + 0.2, hard):
        ax.text(xi, v + 0.6, f"{v:.1f}", ha="center", color=FG, fontsize=8)
    ax.set_xticks(x, names, color=FG, fontsize=9)
    ax.set_ylim(60, 112)
    ax.set_ylabel("Score (%)", color=FG)
    ax.set_title("Model comparison", color=FG, pad=10)
    ax.legend(facecolor=BG, edgecolor=MUTED, labelcolor=FG, loc="upper center", ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=140, facecolor=BG)
    plt.close(fig)


def main():
    t0 = time.time()
    df = pd.read_csv(DATA).dropna()
    hard = pd.read_csv(HARD).dropna()
    labels = sorted(df["intent"].unique())
    print(f"Dataset: {len(df)} rows, {len(labels)} intents | hard-test: {len(hard)} rows")

    X_tr, X_te, y_tr, y_te = train_test_split(
        df["text"], df["intent"], test_size=0.2, stratify=df["intent"], random_state=SEED)

    candidates = {
        "Naive Bayes": build(MultinomialNB(alpha=0.05)),
        "Linear SVM": build(LinearSVC(C=1.0)),
        "Logistic Reg.": build(LogisticRegression(C=20, max_iter=3000)),
        "LogReg (words only)": build(LogisticRegression(C=20, max_iter=3000), word_only=True),
    }
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)
    comparison = []
    print("\nModel comparison (5-fold CV on training split)")
    for name, pipe in candidates.items():
        scores = cross_validate(pipe, X_tr, y_tr, cv=cv, scoring=["accuracy", "f1_macro"], n_jobs=1)
        pipe.fit(X_tr, y_tr)
        row = {
            "name": name,
            "cv_acc": float(scores["test_accuracy"].mean()),
            "cv_f1": float(scores["test_f1_macro"].mean()),
            "test_acc": float(accuracy_score(y_te, pipe.predict(X_te))),
            "hard_acc": float(accuracy_score(hard["intent"], pipe.predict(hard["text"]))),
        }
        comparison.append(row)
        print(f"  {name:<22} CV acc {row['cv_acc']:.3f} | CV F1 {row['cv_f1']:.3f} | "
              f"test {row['test_acc']:.3f} | hard {row['hard_acc']:.3f}")

    print("\nTuning Logistic Regression (C) with 3-fold grid search ...")
    grid = GridSearchCV(build(LogisticRegression(max_iter=3000)),
                        {"clf__C": [1, 5, 20, 50, 100]}, cv=3, scoring="f1_macro", n_jobs=1)
    grid.fit(X_tr, y_tr)
    best_c = grid.best_params_["clf__C"]
    print(f"  best C = {best_c} (CV macro-F1 {grid.best_score_:.3f})")

    final = build(LogisticRegression(C=best_c, max_iter=3000))
    final.fit(X_tr, y_tr)
    pred_te = final.predict(X_te)
    pred_hard = final.predict(hard["text"])
    proba_hard = final.predict_proba(hard["text"])
    conf_hard = proba_hard.max(axis=1)
    correct = pred_hard == hard["intent"].values

    test_acc = accuracy_score(y_te, pred_te)
    test_f1 = f1_score(y_te, pred_te, average="macro")
    hard_acc = accuracy_score(hard["intent"], pred_hard)
    hard_f1 = f1_score(hard["intent"], pred_hard, average="macro")
    print(f"\nFinal model  test acc {test_acc:.3f} | test macro-F1 {test_f1:.3f} | "
          f"hard acc {hard_acc:.3f} | hard macro-F1 {hard_f1:.3f}")
    print("\nClassification report (hard-test set):")
    print(classification_report(hard["intent"], pred_hard, zero_division=0))

    report_hard = classification_report(hard["intent"], pred_hard, output_dict=True, zero_division=0)
    report_test = classification_report(y_te, pred_te, output_dict=True, zero_division=0)
    errors = [
        {"text": t, "true": a, "pred": p, "confidence": round(float(c), 3)}
        for t, a, p, c, ok in zip(hard["text"], hard["intent"], pred_hard, conf_hard, correct) if not ok
    ]

    cm = confusion_matrix(hard["intent"], pred_hard, labels=labels)
    plot_confusion(cm, labels, IMG / "confusion_matrix.png")
    plot_comparison(comparison, IMG / "model_comparison.png")

    # Refit on ALL generated data for the deployed model
    deployed = build(LogisticRegression(C=best_c, max_iter=3000))
    deployed.fit(df["text"], df["intent"])
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(deployed, MODEL_PATH)

    n_features = len(deployed.named_steps["tfidf"].get_feature_names_out())
    metrics = {
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sklearn_version": sklearn.__version__,
        "n_samples": int(len(df)),
        "n_intents": len(labels),
        "n_features": int(n_features),
        "n_hard_test": int(len(hard)),
        "best_C": best_c,
        "test_accuracy": float(test_acc),
        "test_macro_f1": float(test_f1),
        "hard_accuracy": float(hard_acc),
        "hard_macro_f1": float(hard_f1),
        "comparison": comparison,
        "per_intent_hard_f1": {k: round(report_hard[k]["f1-score"], 3) for k in labels if k in report_hard},
        "per_intent_test_f1": {k: round(report_test[k]["f1-score"], 3) for k in labels if k in report_test},
        "hard_errors": errors,
        "hard_conf_correct_mean": float(conf_hard[correct].mean()) if correct.any() else None,
        "hard_conf_wrong_mean": float(conf_hard[~correct].mean()) if (~correct).any() else None,
        "intent_counts": {k: int(v) for k, v in df["intent"].value_counts().sort_index().items()},
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\nSaved model -> {MODEL_PATH.relative_to(ROOT)}")
    print(f"Saved metrics -> {METRICS_PATH.relative_to(ROOT)} | features: {n_features}")
    print(f"Hard-test mistakes: {len(errors)}")
    for e in errors:
        print(f"  '{e['text']}'  true={e['true']}  pred={e['pred']}  conf={e['confidence']}")
    print(f"Done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
