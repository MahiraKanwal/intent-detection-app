# PROGRESS.md: steps taken, in order

A log of every step so the project can be reproduced and explained in the viva. Entries marked **(sandbox)** were run while building; run the same commands on your own PC and write your versions in section 10.

## 1. Project choice
- Assignment list item **#15: Intent Detection for Short Commands**.
- Goal: an end-to-end app (data, model, backend, professional frontend, actions that open links, deployable with a domain), all built inside VS Code.

## 2. Environment check (sandbox)
```
python3 --version   -> Python 3.13.18
pip --version       -> pip 26.2.1
```
Libraries already available: scikit-learn 1.9.1, Flask 3.1.3, pandas 3.0.5, numpy 2.5.3, joblib 1.6.0, matplotlib 3.11.2.
Not installed and not needed: FastAPI, NLTK, gunicorn (gunicorn is only for deployment).
Design decision: **no NLTK / spaCy / paid API**, so the install is small and every NLP step is visible in our own code.

## 3. Folder structure
```
mkdir intent-detection-app
mkdir core data models templates static static/img tests
```

## 4. Dataset (`build_dataset.py`)
- 15 intents, 260 sentences each, 3,900 total.
- Method: sentence templates + slot values + noise (prefixes/suffixes, casing, missing punctuation, typos) + some Roman Urdu.
- Command: `python build_dataset.py` -> `data/intents.csv`.
- Wrote `data/hard_test.csv`: 91 sentences written by hand, phrased differently from the templates, used for a realistic test.

## 5. Model (`train.py`)
- Preprocessing: lower-case, strip odd symbols, **keep stop-words and digits** (they carry the intent).
- Features: TF-IDF word 1-2-grams + character 2-5-grams.
- 5-fold CV comparison (sandbox, first run):

| Model | CV macro-F1 | Test acc. | Hard-test acc. |
|---|---|---|---|
| Naive Bayes | 0.995 | 0.997 | 0.868 |
| Linear SVM | 0.999 | 1.000 | 0.868 |
| Logistic Regression | 0.999 | 1.000 | 0.857 |
| LogReg, words only | 0.990 | 0.996 | 0.835 |

- Error analysis of the first run: "how late is it in tokyo" and "how's it going" were predicted as weather; "lighten the mood" / "bring on the tunes" were not linked to joke / music.
- Fix: added paraphrase families to the templates (more ways to ask time, greet, ask for a joke, play music, search), regenerated data, retrained. The hard-test file was **not** edited.
- Second run (current):

| Model | CV macro-F1 | Test acc. | Hard-test acc. |
|---|---|---|---|
| Naive Bayes | 0.995 | 0.995 | 0.956 |
| Linear SVM | 0.999 | 0.999 | 0.978 |
| Logistic Regression (deployed) | 0.999 | 0.999 | 0.967 |
| LogReg, words only | 0.992 | 0.995 | 0.945 |

- Grid search over C: best C = 20.
- Remaining hard-test mistakes (3): "how humid is it right now" (predicted time), "lighten the mood" (predicted smart home, low confidence), "peace out see you tomorrow" (predicted send message).
- Outputs: `models/intent_model.joblib`, `models/metrics.json`, `static/img/confusion_matrix.png`, `static/img/model_comparison.png`.

## 7. Confidence threshold
- Correct hard-test predictions had confidence 0.53 or higher; nonsense text ("banana", "lorem ipsum ...") mostly scored 0.20 to 0.32.
- Threshold set to **0.45** in `app.py`. Below it the app says "not sure" and does nothing.

## 8. Backend
- `core/slots.py`: regex slot extraction (time, duration, contact, message, place, city, song, site, device, task, query).
- `core/calc.py`: safe arithmetic using `ast` (no `eval`), handles "15 percent of 200", "square root of 225", "subtract 5 from 20".
- `core/actions.py`: maps intent + slots to an action (open URL, alarm, timer, reminder, device switch, reply).
- `app.py`: Flask routes `GET /`, `POST /api/predict`, `GET /api/intents`, `GET /api/metrics`, `GET /api/health`. Input validation (empty, over 300 chars, invalid JSON). Auto-retrains if the saved model cannot be loaded.
- Tests: `python -m unittest discover -s tests -v` -> 7 tests, all OK.

## 9. Frontend
- Single page, no framework: `templates/index.html`, `static/style.css`, `static/app.js`.
- Intent dial: 15 nodes light up with the model's probabilities, live while typing.
- Result panel: detected intent, confidence, extracted details, top 3 guesses, the action and its button.
- Live panels: timers/alarms/reminders (sound + notification), virtual smart home, command history.
- Model results section reads `/api/metrics`: stats, model comparison, per-intent F1, confusion matrix, mistakes list.
- Checked in headless Chrome at desktop (1440 px) and phone (390 px) widths: no console errors; fixed the wrapping header links on phones, the headline line breaks and an overlapping chart legend.

## 10. Commands to run on YOUR computer (fill in your versions)
```
python --version        ->  ____________
pip --version           ->  ____________
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip list                ->  scikit-learn ____ | Flask ____ | pandas ____ | numpy ____
python build_dataset.py
python train.py         ->  hard-test accuracy ____
python -m unittest discover -s tests -v
python app.py           ->  open http://127.0.0.1:5000
```

## 11. Deployment (to do by you)
See README section 5: push to GitHub, create a Render web service, then attach a custom domain if you buy one.

## 12. Ideas not done yet
- More intents, a public dataset (SNIPS / Banking77), a transformer comparison, logging real user commands.
## 13. Online deployment (PythonAnywhere)
- Render asked for a card even on the free plan, so I used PythonAnywhere (free Beginner account, no card).
- Steps: created account "intentia", uploaded the project zip in the Files tab, unzipped it in a Bash console, checked the libraries (Python 3.13, scikit-learn 1.6.0), retrained the model there with `python3 train.py` (hard-test accuracy 0.967), then Web tab > Add a new web app > Manual configuration > Python 3.13, edited the WSGI file (project path /home/intentia/intent-detection-app, `from app import app as application`) and clicked Reload.
- Error faced: SyntaxError in the WSGI file, because the website link was pasted into the file by mistake. Fixed by replacing the whole file with the 7 correct lines.
- Live link: https://intentia.pythonanywhere.com
- Tested on a phone browser: it opens.
- The free app expires after 1 month. Click "Run until 1 month from today" on the Web tab to keep it running.
- Code is on GitHub (private): https://github.com/MahiraKanwal/intent-detection-app