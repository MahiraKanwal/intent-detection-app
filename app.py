"""Flask backend for the Intent Detection app.

Run:  python app.py        (development, http://127.0.0.1:5000)
Prod: gunicorn app:app     (Linux)   |   waitress-serve --port=5000 app:app   (Windows)
"""
import json
import os
import time
from pathlib import Path

import joblib
from flask import Flask, jsonify, render_template, request

from core.actions import build_action
from core.meta import INTENTS, label_of
from core.preprocess import clean_text
from core.slots import extract_slots

ROOT = Path(__file__).parent
MODEL_PATH = ROOT / "models" / "intent_model.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"
CONFIDENCE_THRESHOLD = 0.45  # chosen from hard-test confidences: correct answers >= 0.53, junk text mostly < 0.35
MAX_LEN = 300

app = Flask(__name__)
app.json.sort_keys = False


def load_model():
    """Loads the saved model; retrains automatically if it is missing or was saved by an incompatible scikit-learn."""
    try:
        return joblib.load(MODEL_PATH)
    except Exception as exc:  # missing file or version mismatch
        print(f"[app] Could not load model ({exc.__class__.__name__}); training a fresh one ...")
        if not (ROOT / "data" / "intents.csv").exists():
            import build_dataset
            build_dataset.main()
        import train
        train.main()
        return joblib.load(MODEL_PATH)


model = load_model()
CLASSES = list(model.classes_)


def predict(text: str) -> dict:
    t0 = time.perf_counter()
    proba = model.predict_proba([text])[0]
    order = proba.argsort()[::-1]
    top = [{"intent": CLASSES[i], "label": label_of(CLASSES[i]), "prob": round(float(proba[i]), 4)} for i in order[:3]]
    best = top[0]
    confident = best["prob"] >= CONFIDENCE_THRESHOLD
    result = {
        "text": text,
        "cleaned": clean_text(text),
        "intent": best["intent"] if confident else "unknown",
        "label": best["label"] if confident else "Not sure",
        "confidence": best["prob"],
        "is_confident": confident,
        "top": top,
        "probabilities": {CLASSES[i]: round(float(proba[i]), 4) for i in range(len(CLASSES))},
    }
    if confident:
        slots = extract_slots(best["intent"], text)
        result["slots"] = slots
        result["action"] = build_action(best["intent"], slots, text)
    else:
        result["slots"] = {}
        result["action"] = {
            "type": "reply",
            "message": f"I'm not sure what you mean. My best guess was “{best['label']}” "
                       f"({best['prob'] * 100:.0f}%). Try a short command like “play music” or “set a timer for 5 minutes”.",
        }
    result["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return result


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/predict")
def api_predict():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify(error="Type or say a command first."), 400
    if len(text) > MAX_LEN:
        return jsonify(error=f"Command is too long (max {MAX_LEN} characters)."), 400
    return jsonify(predict(text))


@app.get("/api/intents")
def api_intents():
    return jsonify([{"intent": k, **v} for k, v in INTENTS.items()])


@app.get("/api/metrics")
def api_metrics():
    if not METRICS_PATH.exists():
        return jsonify(error="Run train.py to create metrics."), 404
    return jsonify(json.loads(METRICS_PATH.read_text(encoding="utf-8")))


@app.get("/api/health")
def api_health():
    return jsonify(status="ok", intents=len(CLASSES))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
