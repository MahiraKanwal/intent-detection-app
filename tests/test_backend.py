"""Quick checks for the model, slot extraction and API.  Run:  python -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402
from core.calc import solve  # noqa: E402
from core.slots import extract_duration, extract_time  # noqa: E402


class SlotTests(unittest.TestCase):
    def test_time(self):
        self.assertEqual(extract_time("wake me up at 7:30 am")["hhmm"], "07:30")
        self.assertEqual(extract_time("alarm for 5 pm")["hhmm"], "17:00")
        self.assertEqual(extract_time("set alarm at half past six")["hhmm"], "06:30")
        self.assertEqual(extract_time("alarm at midnight")["hhmm"], "00:00")

    def test_duration(self):
        self.assertEqual(extract_duration("timer for 10 minutes")["seconds"], 600)
        self.assertEqual(extract_duration("timer 1 hour 30 minutes")["seconds"], 5400)
        self.assertEqual(extract_duration("set a timer for half an hour")["seconds"], 1800)
        self.assertEqual(extract_duration("timer for forty five seconds")["seconds"], 45)

    def test_calc(self):
        self.assertEqual(solve("what is 15 percent of 200")["result"], 30)
        self.assertEqual(solve("what's 45 times 12")["result"], 540)
        self.assertEqual(solve("square root of 225")["result"], 15)
        self.assertEqual(solve("subtract 5 from 20")["result"], 15)
        self.assertIsNone(solve("__import__('os')"))


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def ask(self, text):
        r = self.client.post("/api/predict", json={"text": text})
        self.assertEqual(r.status_code, 200)
        return r.get_json()

    def test_intents(self):
        cases = {
            "play shape of you": "play_music", "set an alarm for 6 am": "set_alarm",
            "timer for 5 minutes": "set_timer", "remind me to buy milk tomorrow": "set_reminder",
            "weather in lahore": "get_weather", "text ali that i am late": "send_message",
            "call mom": "make_call", "search for machine learning": "web_search",
            "directions to faisal mosque": "navigate", "what time is it": "get_time",
            "open github": "open_website", "turn off the fan": "smart_home",
            "tell me a joke": "tell_joke", "what is 12 plus 30": "calculate", "good morning": "greeting",
        }
        for text, intent in cases.items():
            self.assertEqual(self.ask(text)["intent"], intent, text)

    def test_actions(self):
        self.assertIn("youtube.com/results", self.ask("play tum hi ho")["action"]["url"])
        self.assertEqual(self.ask("set a timer for 2 minutes")["action"]["seconds"], 120)
        self.assertEqual(self.ask("what is 12 plus 30")["action"]["result"], 42)

    def test_validation(self):
        self.assertEqual(self.client.post("/api/predict", json={"text": ""}).status_code, 400)
        self.assertEqual(self.client.post("/api/predict", json={"text": "x" * 500}).status_code, 400)
        self.assertEqual(self.client.post("/api/predict", data="nope").status_code, 400)

    def test_low_confidence_fallback(self):
        r = self.ask("purple elephant quantum banana")
        self.assertIn("action", r)


if __name__ == "__main__":
    unittest.main()
