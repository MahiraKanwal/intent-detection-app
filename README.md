# Intentia: Intent Detection for Short Commands

NLP course project (#15): classify short user commands such as "play music" or "set alarm" into intents, extract the details, and carry out the action in a web app.

- **15 intents:** play music, set alarm, set timer, set reminder, weather, send message, make call, web search, navigate, time and date, open website, smart home, tell a joke, calculate, greeting
- **Languages:** English plus some Roman Urdu commands ("gana chalao", "alarm lagao")
- **Stack:** Python, scikit-learn (TF-IDF + Logistic Regression), Flask backend, plain HTML/CSS/JS frontend
- **No paid APIs, no external AI service.** Everything runs on your machine.

---

## 1. Run it in VS Code (Windows, step by step)

Open the project folder in VS Code (`File > Open Folder`), then open the terminal (`Ctrl + ~`).

| Step | Command (cmd / PowerShell) | Why |
|---|---|---|
| 1 | `python --version` | Check Python is installed (3.9 or newer). If this fails, try `py --version`. |
| 2 | `pip --version` | Check pip works. |
| 3 | `python -m venv venv` | Create an isolated environment for this project. |
| 4 | `venv\Scripts\activate` | Activate it. The prompt now starts with `(venv)`. PowerShell blocked? Run `Set-ExecutionPolicy -Scope Process Bypass` first. |
| 5 | `pip install -r requirements.txt` | Install Flask, scikit-learn, pandas, numpy, joblib, matplotlib. |
| 6 | `pip list` | Confirm the versions that got installed (note them in PROGRESS.md). |
| 7 | `python build_dataset.py` | Generate `data/intents.csv` (3,900 labelled commands). |
| 8 | `python train.py` | Train, compare models, evaluate, save `models/intent_model.joblib`, metrics and plots. |
| 9 | `python -m unittest discover -s tests -v` | Run the automated tests (should print `OK`). |
| 10 | `python app.py` | Start the web app. |
| 11 | Open http://127.0.0.1:5000 | Use the app. Stop the server with `Ctrl + C`. |

On macOS / Linux use `python3` and `source venv/bin/activate`.

> The saved model was trained with a different scikit-learn version than yours. That is fine: step 8 re-trains it on your machine, and `app.py` also re-trains automatically if the model cannot be loaded.

---

## 2. Project structure

```
intent-detection-app/
├── app.py                 Flask backend (API + serves the page)
├── build_dataset.py       Creates data/intents.csv from templates + noise
├── train.py               Trains and evaluates the models, saves everything
├── core/
│   ├── preprocess.py      Text cleaning (keeps stop-words on purpose)
│   ├── slots.py           Rule-based slot extraction (time, duration, contact, place ...)
│   ├── actions.py         Intent + slots -> action (URL, timer, device switch, reply)
│   ├── calc.py            Safe calculator for "what is 15 percent of 200"
│   └── meta.py            Names and icons of the intents
├── data/
│   ├── intents.csv        Training data (generated)
│   └── hard_test.csv      91 hand-written sentences used only for testing
├── models/                intent_model.joblib, metrics.json
├── static/                style.css, app.js, plots (confusion matrix, model comparison)
├── templates/index.html   The page
├── tests/test_backend.py  Unit and API tests
├── Procfile               For deployment (gunicorn)
├── requirements.txt
├── PROGRESS.md            Step-by-step log of everything done
└── README.md
```

---

## 3. How the NLP part works (for your report)

1. **Data.** `build_dataset.py` fills hand-written sentence templates with slot values (songs, cities, times ...) and adds noise: polite prefixes, casing changes, missing punctuation and random typos. 260 sentences per intent, 3,900 total.
2. **Preprocessing.** Lower-casing and removing odd symbols. **Stop-words are kept**, because words like "on", "off", "in" and "to" decide the intent ("turn *off* the fan", "remind me *in* 10 minutes"). Digits and `+ - * /` are kept for the calculator.
3. **Features.** TF-IDF on word unigrams and bigrams, plus TF-IDF on character 2 to 5-grams, which makes the model robust to typos ("alrm" is close to "alarm").
4. **Classifier.** Four models are compared with 5-fold cross-validation: Naive Bayes, Linear SVM, Logistic Regression and Logistic Regression with word features only (an ablation showing the value of character n-grams). Logistic Regression is deployed because it outputs probabilities; its regularisation `C` is tuned with grid search.
5. **Confidence threshold.** If the best probability is below 0.45 the app answers "not sure" instead of guessing. The threshold comes from the confidences seen on the hard-test set (correct answers were 0.53 or higher; nonsense text mostly scored below 0.35).
6. **Slot filling.** Regular-expression rules extract times ("half past six" becomes 06:30), durations ("forty five seconds" becomes 45), contacts, messages, places, songs, sites, devices and arithmetic.
7. **Action.** The intent and slots become a concrete action (see table below).

### What each intent does

| Intent | Action in the app |
|---|---|
| play_music | Opens a YouTube (or Spotify) search for the song |
| set_alarm | Schedules an alarm that rings (sound + notification) while the tab is open |
| set_timer | Starts a countdown that rings at zero |
| set_reminder | In-page notification and an "Add to Google Calendar" link |
| get_weather | Opens the Google weather result for the city |
| send_message | Opens WhatsApp (`wa.me`) with the text filled in |
| make_call | Opens a `tel:` link for a number, otherwise WhatsApp Web |
| web_search | Opens a Google search |
| navigate | Opens Google Maps directions or a nearby search |
| get_time | Shows your local time/date, or opens time.is for another city |
| open_website | Opens the site in a new tab |
| smart_home | Switches a virtual device panel (lights, fan, AC, TV, door ...) |
| tell_joke / calculate / greeting | Replies in the page |

### Evaluation (numbers from the last training run)

| Evaluation | Result |
|---|---|
| Held-out test split (20%) | 99.9% accuracy |
| **Hand-written hard-test set (91 sentences)** | **96.7% accuracy** |

The first number is almost perfect because test sentences come from the same templates as the training data, so **report the hard-test number as the realistic one**. Be open about the method: after the first run (85.7% on the hard test) the generator was extended with more paraphrase templates based on the error analysis, so the hard-test set was used for model development and is not a fully untouched benchmark. For a fully clean estimate, add new sentences of your own to `data/hard_test.csv` that the generator never saw, and run `python train.py` again.

### Known limitations (good for the "Discussion" section)

- The training data is synthetic. Real users phrase things in more ways.
- The model is closed-set: it always picks one of the 15 intents. A confidence threshold catches most nonsense, but not all ("the quick brown fox jumps" still scores high for smart_home).
- Slot extraction is rule-based and mostly English. Roman Urdu is understood by the classifier, but slots in Roman Urdu are only partly extracted.
- Alarms and timers only ring while the browser tab stays open.
- Browsers may block automatically opened tabs; the amber button always works.

---

## 4. Using the app

- Type a command and press Enter, or click an example chip, or click any node on the dial.
- The dial lights up the detected intent while you type (live preview).
- Press the microphone button to speak (Chrome / Edge). Allow microphone access when asked.
- "Open links automatically" controls whether links open as soon as the command runs.

Try: `play tum hi ho`, `wake me up at 6:30 am`, `timer for 2 minutes`, `remind me to call ali at 5 pm`, `weather in lahore`, `text ali that i will be late`, `directions to faisal mosque`, `turn off the fan`, `what is 15 percent of 200`.

---

## 5. Put it online with your own domain

A hosted URL is what lets anyone open the app. These steps use Render (free tier, no credit card for a basic web service). Railway, PythonAnywhere and Fly.io work in a similar way.

1. **Put the code on GitHub.** In the project folder:
   ```
   git init
   git add .
   git commit -m "Intent detection app"
   ```
   Create an empty repository on github.com, then run the two commands it shows (`git remote add origin ...` and `git push -u origin main`).
2. **Create the service.** On render.com choose *New > Web Service*, connect the GitHub repository and set:
   - Runtime: **Python 3**
   - Build command: `pip install -r requirements.txt && python build_dataset.py && python train.py`
   - Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`
3. Click *Create Web Service*. After the build finishes you get a URL like `https://your-app.onrender.com`. Share that link.
4. **Free-tier behaviour:** the service sleeps after a period of inactivity, so the first visit after a pause can take about a minute.
5. **Custom domain (optional, paid).** Buy a domain from a registrar (Namecheap, GoDaddy, Cloudflare ...). In Render open *Settings > Custom Domains > Add*, enter the domain, and add the DNS record Render shows you at your registrar (a `CNAME` for `www`, an `A`/`ALIAS` record for the bare domain). HTTPS is added automatically after DNS updates, which can take from a few minutes to a few hours.

The page must be served over HTTPS for the microphone and notifications to work online; Render provides that automatically. On `127.0.0.1` they work without HTTPS.

---

## 6. Ideas to extend it

- Add more intents (volume control, take a note, translate) by adding templates in `build_dataset.py` and a branch in `core/actions.py`.
- Replace the synthetic data with a public dataset such as SNIPS or the Banking77 intent set and compare.
- Try a small transformer (for example DistilBERT) as a comparison against TF-IDF.
- Log real user commands (with permission) and retrain on them.
