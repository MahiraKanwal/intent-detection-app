"""Text preprocessing shared by training and the web app.

Design choice (worth explaining in the report): stop-words are NOT removed.
In short commands words like "to", "on", "off", "in", "at" carry the intent
("turn ON the light", "remind me IN 10 minutes"), so removing them hurts.
Digits and arithmetic symbols are kept for the same reason.
"""
import re

_KEEP = re.compile(r"[^a-z0-9\s'+\-*/%.:]")
_SPACES = re.compile(r"\s+")


def clean_text(text: str) -> str:
    text = str(text).lower().replace("’", "'").replace("‘", "'")
    text = _KEEP.sub(" ", text)
    text = _SPACES.sub(" ", text).strip()
    return text
