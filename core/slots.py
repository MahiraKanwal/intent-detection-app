"""Rule-based slot extraction (the second NLP step after intent classification).

The classifier says WHAT the user wants; these regex rules pull out the details
(time, duration, contact, place, song ...). Best-effort by design: every
extractor returns None when it is not sure.
"""
import re

_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "ninety": 90,
}
_TENS = {20, 30, 40, 50, 60, 90}
_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_TRAILING = r"(?:\s+(?:please|for me|now|right now|thanks|asap|today|tomorrow|tonight|this weekend))+$"

_SITES = {
    "youtube": "https://www.youtube.com", "facebook": "https://www.facebook.com", "google": "https://www.google.com",
    "gmail": "https://mail.google.com", "github": "https://github.com", "twitter": "https://x.com",
    "x": "https://x.com", "instagram": "https://www.instagram.com", "linkedin": "https://www.linkedin.com",
    "whatsapp": "https://web.whatsapp.com", "netflix": "https://www.netflix.com",
    "wikipedia": "https://www.wikipedia.org", "amazon": "https://www.amazon.com",
    "stackoverflow": "https://stackoverflow.com", "stack overflow": "https://stackoverflow.com",
    "reddit": "https://www.reddit.com", "daraz": "https://www.daraz.pk", "spotify": "https://open.spotify.com",
    "chatgpt": "https://chatgpt.com", "claude": "https://claude.ai", "canva": "https://www.canva.com",
    "kaggle": "https://www.kaggle.com", "google drive": "https://drive.google.com",
    "google maps": "https://maps.google.com", "maps": "https://maps.google.com", "drive": "https://drive.google.com",
    "outlook": "https://outlook.live.com", "zoom": "https://zoom.us", "tiktok": "https://www.tiktok.com",
}

_DEVICES = [
    ("lights", r"\b(?:lights?|lamp|bulb)\b"), ("fan", r"\bfan\b"),
    ("ac", r"\b(?:ac|a\.c\.|air conditioner|air conditioning|thermostat|cooler|cooling)\b"),
    ("tv", r"\b(?:tv|television)\b"), ("heater", r"\bheater\b"), ("door", r"\bdoor\b"),
    ("geyser", r"\bgeyser\b"), ("coffee", r"\bcoffee maker\b"),
]
_ROOMS = ["living room", "bedroom", "kitchen", "bathroom", "porch", "garden", "hall"]


def words_to_digits(text: str) -> str:
    """'five minutes' -> '5 minutes', 'forty five seconds' -> '45 seconds'."""
    tokens, out, i = text.split(), [], 0
    while i < len(tokens):
        w = tokens[i]
        if w in _NUMBER_WORDS:
            n = _NUMBER_WORDS[w]
            if n in _TENS and i + 1 < len(tokens) and tokens[i + 1] in _NUMBER_WORDS and 1 <= _NUMBER_WORDS[tokens[i + 1]] <= 9:
                n += _NUMBER_WORDS[tokens[i + 1]]
                i += 1
            out.append(str(n))
        else:
            out.append(w)
        i += 1
    return " ".join(out)


def _strip(s):
    if not s:
        return None
    s = re.sub(_TRAILING, "", s.strip(" .?!,:;"), flags=re.I).strip(" .?!,:;")
    return s or None


# ---------- time / duration / day ----------
def extract_day(text: str):
    t = text.lower()
    if "tomorrow" in t or "kal " in t + " ":
        return "tomorrow"
    if re.search(r"\b(today|tonight|aaj)\b", t):
        return "today"
    for d in _DAYS:
        if d in t:
            return d
    if "weekend" in t:
        return "weekend"
    return None


def extract_time(text: str):
    t = words_to_digits(text.lower().replace(".", ":") if re.search(r"\d\.\d\d", text) else text.lower())
    evening = bool(re.search(r"\b(evening|afternoon|night|shaam|raat|pm)\b", t))
    hour = minute = None
    raw = None

    m = re.search(r"\bhalf past (\d{1,2})\b", t)
    if m:
        hour, minute, raw = int(m.group(1)), 30, m.group(0)
    if hour is None:
        m = re.search(r"\bquarter past (\d{1,2})\b", t)
        if m:
            hour, minute, raw = int(m.group(1)), 15, m.group(0)
    if hour is None:
        m = re.search(r"\bquarter to (\d{1,2})\b", t)
        if m:
            hour, minute, raw = (int(m.group(1)) - 1) % 24, 45, m.group(0)
    if hour is None:
        m = re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)?", t)
        if m:
            hour, minute, raw = int(m.group(1)), int(m.group(2)), m.group(0).strip()
            ap = (m.group(3) or "").replace(".", "")
            if ap == "pm" and hour < 12:
                hour += 12
            elif ap == "am" and hour == 12:
                hour = 0
            elif not ap and evening and hour < 12:
                hour += 12
    if hour is None:
        m = re.search(r"\b(\d{1,2}) (\d{2})\b(?!\s*(?:minutes?|mins?|seconds?|hours?))", t)
        if m and int(m.group(2)) < 60 and int(m.group(1)) <= 12:
            hour, minute, raw = int(m.group(1)), int(m.group(2)), m.group(0)
            if evening and hour < 12:
                hour += 12
    if hour is None:
        m = re.search(r"\b(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)", t)
        if m:
            hour, minute, raw = int(m.group(1)), 0, m.group(0)
            ap = m.group(2).replace(".", "")
            if ap == "pm" and hour < 12:
                hour += 12
            elif ap == "am" and hour == 12:
                hour = 0
    if hour is None:
        m = re.search(r"\b(\d{1,2})\s*(?:o'?clock|baje)", t)
        if m:
            hour, minute, raw = int(m.group(1)), 0, m.group(0)
            if evening and hour < 12:
                hour += 12
    if hour is None and re.search(r"\bnoon\b", t):
        hour, minute, raw = 12, 0, "noon"
    if hour is None and re.search(r"\bmidnight\b", t):
        hour, minute, raw = 0, 0, "midnight"
    if hour is None:
        m = re.search(r"\b(?:at|by|for|wake me at|alarm for|alarm)\s+(\d{1,2})\b(?!\s*(?:minutes?|mins?|seconds?|hours?|percent|degrees?|%))", t)
        if m and int(m.group(1)) <= 24:
            hour, minute, raw = int(m.group(1)), 0, m.group(0).split()[-1]
            if evening and hour < 12:
                hour += 12

    if hour is None or not (0 <= hour <= 24 and 0 <= (minute or 0) < 60):
        return None
    hour %= 24
    return {"raw": raw, "hour": hour, "minute": minute or 0, "hhmm": f"{hour:02d}:{minute or 0:02d}"}


def extract_duration(text: str):
    t = text.lower()
    t = re.sub(r"\bhalf an hour\b", "30 minutes", t)
    t = re.sub(r"\ban hour\b", "1 hour", t)
    t = re.sub(r"\ba minute\b", "1 minute", t)
    t = re.sub(r"\ba second\b", "1 second", t)
    t = words_to_digits(t)
    total, parts = 0.0, []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|minutes?|mins?|seconds?|secs?)\b", t):
        n, unit = float(m.group(1)), m.group(2)
        mult = 3600 if unit.startswith(("h")) else 60 if unit.startswith("m") else 1
        total += n * mult
        parts.append(m.group(0))
    if not parts:
        return None
    seconds = int(total)
    return {"raw": " ".join(parts), "seconds": seconds, "pretty": _pretty_seconds(seconds)}


def _pretty_seconds(sec: int) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    out = []
    if h:
        out.append(f"{h} hour{'s' if h != 1 else ''}")
    if m:
        out.append(f"{m} minute{'s' if m != 1 else ''}")
    if s:
        out.append(f"{s} second{'s' if s != 1 else ''}")
    return " ".join(out) or "0 seconds"


# ---------- contacts, messages, numbers ----------
def extract_number(text: str):
    m = re.search(r"(\+?\d[\d\s\-]{5,}\d)", text)
    return re.sub(r"[\s\-]", "", m.group(1)) if m else None


_NOT_NAMES = {"a", "an", "the", "to", "message", "text", "sms", "whatsapp", "email", "mail", "me", "up", "it", "this", "that", "hi"}
_NAME = r"((?:my |the )?[a-z][a-z']*)"


def extract_contact(text: str):
    t = text.lower().strip()
    patterns = [
        rf"\b{_NAME}\s+ko\s+(?:call|phone|message|whatsapp|sms|text)\b",
        rf"\b{_NAME}\s+se\s+baat\b",
        rf"\bmessage bhejo\s+{_NAME}\s+ko\b",
        rf"\blet\s+{_NAME}\s+know\b",
        rf"\b(?:to|for|with)\s+{_NAME}(?=\s+(?:saying|that|about|on|via|by|with|at|and|:)|\s*[:?.!,]|$)",
        rf"\b(?:call|phone|dial|ring|text|message|msg|whatsapp|sms|email|mail|tell|inform|get)\s+{_NAME}",
    ]
    for p in patterns:
        for m in re.finditer(p, t):
            name = m.group(1).strip()
            if name.split()[-1] not in _NOT_NAMES and name not in _NOT_NAMES:
                return name
    return None


def extract_message(text: str):
    t = text.strip()
    m = re.search(r"\b(?:saying|says|say|that|ke|about)\b[:\s]+(.+)$", t, flags=re.I)
    if m:
        return _strip(m.group(1))
    m = re.search(r":\s*(.+)$", t)
    if m:
        return _strip(m.group(1))
    m = re.search(r"\bsend\s+(.+?)\s+to\s+[a-z' ]+$", t, flags=re.I)
    if m and m.group(1).lower() not in {"a message", "an sms", "a text", "a whatsapp message", "an email", "hi"}:
        return _strip(m.group(1))
    return None


# ---------- other slot types ----------
def extract_task(text: str):
    t = text.strip()
    patterns = [
        r"\bremind(?:ed)?\s+(?:me\s+)?(?:in\s+[\w\s.]+?\s+)?(?:to|about)\s+(.+)$",
        r"\bnote to self[:,]?\s+(.+)$", r"\bdon'?t (?:let me )?forget(?: to)?\s+(.+)$",
        r"\breminder(?: for| to)?\s+(.+)$", r"\bmake a note to remind me to\s+(.+)$",
        r"\bping me later to\s+(.+)$", r"\bya?ad dil(?:a)?o\s+(.+)$", r"\bke\s+(.+)$",
    ]
    for p in patterns:
        m = re.search(p, t, flags=re.I)
        if m:
            task = m.group(1)
            task = re.sub(r"\s+(?:at|on|by|in|tomorrow|tonight|today|this)\s+(?:\d|noon|midnight|monday|tuesday|wednesday|thursday|friday|saturday|sunday|morning|evening|weekend|a |an ).*$", "", task, flags=re.I)
            task = re.sub(r"\s+(?:tomorrow|tonight|today|this evening|this weekend|tomorrow morning)$", "", task, flags=re.I)
            return _strip(task)
    return None


_SEARCH_PREFIX = re.compile(
    r"^(?:(?:please|hey assistant|hey|ok|um|so|assistant|yo)\s+)*(?:(?:can|could) you\s+)?"
    r"(?:search (?:the web |google |online )?(?:for |about )?|search images of |google |look(?:ing)? (?:up|for) |"
    r"find (?:me )?(?:information|info) (?:about|on) |find me |find |show me results for |tell me about |"
    r"i want to know about )", re.I)
_SEARCH_SUFFIX = re.compile(r"\s+(?:on google|online|on the web)$", re.I)


def extract_query(text: str):
    t = text.strip(" ?.!")
    q = _SEARCH_PREFIX.sub("", t)
    q = _SEARCH_SUFFIX.sub("", q)
    q = re.sub(r"\s+ke bare mein search karo$", "", q, flags=re.I)
    q = re.sub(r"^google par\s+|\s+dhundo$", "", q, flags=re.I)
    return _strip(q) or _strip(t)


def extract_song(text: str):
    t = text.strip(" ?.!")
    t = re.sub(r"^(?:(?:please|hey assistant|hey|ok|um|so|assistant|yo)\s+)+", "", t, flags=re.I)
    platform = "spotify" if re.search(r"\bspotify\b", t, re.I) else "youtube"
    m = re.search(r"\b(?:play(?: me)?|listen to|put on|queue up|start playing|throw on|blast|hear|shuffle)\s+(?:the song |the |some |my |that |something )?(.+)$", t, flags=re.I)
    song = m.group(1) if m else None
    if not song:
        m = re.search(r"^(.+?)\s+(?:chalao|sunao|lagao)\b", t, flags=re.I) or re.search(r"\bmujhe\s+(.+?)\s+sunna\b", t, flags=re.I)
        song = m.group(1) if m else None
    if song:
        song = re.sub(r"\s+(?:on|in|from|using)\s+(?:youtube|spotify|the living room)\b.*$", "", song, flags=re.I)
        song = re.sub(r"^(?:on )?spotify[, ]+", "", song, flags=re.I)
        song = re.sub(r"\s+(?:while i \w+|right now)$", "", song, flags=re.I)
        song = _strip(song)
    if song and song.lower() in {"music", "some music", "something", "songs", "tunes", "the tunes", "my playlist", "the next song", "gana", "koi acha sa gana"}:
        song = None
    return {"song": song, "platform": platform}


_PLACE_PATTERNS = [
    r"\b(?:navigate|navigation|directions?|route|way|drive me|drive|walk|get|go|take me|show me the (?:route|way)|find the way)\s+(?:me\s+)?(?:to|towards)\s+(.+)$",
    r"\bwhere(?:'s| is)\s+(?:the\s+)?(.+)$", r"\bhow far is\s+(.+)$", r"\bmap of\s+(.+)$",
    r"\bshow\s+(.+?)\s+on the map\b", r"\bhow long (?:to|will it take to)\s+(?:get to|drive to|reach)\s+(.+)$",
    r"\b(?:nearest|closest|nearby)\s+(.+?)(?:\s+(?:near|to|around)\s+me)?(?:\s+kahan hai)?$",
    r"\bfind\s+(.+?)\s+near(?:by)?\s+(?:me|(.+))$", r"\bmujhe\s+(.+?)\s+jana hai", r"^(.+?)\s+ka rasta\b",
    r"\bway\s+(home)\b", r"\b(?:get me to|route me to)\s+(.+)$",
]


def extract_place(text: str):
    t = text.strip(" ?.!").lower()
    t = re.sub(r"^(?:(?:please|hey assistant|hey|ok|um|so|assistant|yo)\s+)+", "", t)
    if re.search(r"\bway home\b|\bhome\b$", t):
        return "home"
    for p in _PLACE_PATTERNS:
        m = re.search(p, t)
        if m:
            g = m.group(1) if m.group(1) else m.group(2)
            if "near" in p and m.lastindex and m.lastindex > 1 and m.group(2):
                return _strip(f"{m.group(1)} near {m.group(2)}")
            return _strip(g)
    return None


def extract_city(text: str):
    t = text.strip(" ?.!").lower()
    m = re.search(r"\b(?:in|for|at)\s+([a-z][a-z' ]*?)(?:\s+(?:today|tomorrow|tonight|now|right now|this weekend|please|this evening|next \w+))?$", t)
    if m:
        city = m.group(1).strip()
        if city not in {"here", "the morning", "the evening", "the afternoon", "general", "the world", "my area", "the night", "a minute", "outside"} and not city.startswith(("the ", "my ")):
            return city
    m = re.search(r"\b([a-z]+)\s+(?:ka mausam|mein kya time)", t)
    if m:
        return m.group(1)
    m = re.search(r"\bshow me the\s+([a-z ]+?)\s+weather\b", t)
    if m:
        return m.group(1)
    return None


def extract_site(text: str):
    t = text.strip(" ?.!").lower()
    t = re.sub(r"^(?:(?:please|hey assistant|hey|ok|um|so|assistant|yo)\s+)+", "", t)
    m = re.search(r"\b(?:open|launch|visit|start|go to|bring up|pull up|fire up|hop onto|check|load|take me to)\s+(?:the |my |a )?(.+)$", t)
    name = m.group(1) if m else None
    if not name:
        m = re.search(r"^(.+?)\s+(?:kholo|open karo|par le jao|khol do)\b", t)
        name = m.group(1) if m else None
    if not name:
        return None
    name = re.sub(r"\s+(?:website|site|web site|for me|in a new tab|inbox|page|app|please|now)\b", "", name)
    name = re.sub(r"\s+(?:website|site|for me|in a new tab|inbox|page|app|please|now)$", "", name).strip()
    return name or None


def site_url(name: str):
    n = name.lower().strip()
    if n in _SITES:
        return _SITES[n]
    m = re.fullmatch(r"(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})(?:/\S*)?", n)
    if m:
        return n if n.startswith("http") else f"https://{n}"
    return None


def extract_smart_home(text: str):
    t = text.lower()
    device = next((name for name, pat in _DEVICES if re.search(pat, t)), None)
    room = next((r for r in _ROOMS if r in t), None)
    state, value = None, None
    if re.search(r"\bunlock\b", t):
        device, state = "door", "unlocked"
    elif re.search(r"\block\b", t):
        device, state = "door", "locked"
    elif re.search(r"\bdim\b", t):
        device, state = device or "lights", "dim"
    elif re.search(r"\b(?:off|band|kill|shut off|shut down|stop|switch off)\b", t) and not re.search(r"\b(?:turn|switch) (?:it )?on\b", t):
        state = "off"
    elif re.search(r"\b(?:on|chalao|jala|jalao|start|switch on|lights on)\b", t):
        state = "on"
    m = re.search(r"\b(?:to|at)\s+(\d{2})\b|\b(\d{2})\s*degrees?", t)
    if m:
        value = int(m.group(1) or m.group(2))
        device = device or "ac"
        state = state or "on"
    if re.search(r"\b(?:cooler|colder)\b", t):
        device, state = device or "ac", state or "on"
    if re.search(r"\bwarmer\b", t):
        device, state = device or "heater", state or "on"
    if not device and not state:
        return None
    return {"device": device, "state": state, "value": value, "room": room}


def extract_slots(intent: str, text: str) -> dict:
    """Returns only the slots that were actually found for this intent."""
    s = {}
    if intent == "play_music":
        s.update(extract_song(text))
    elif intent == "set_alarm":
        s["time"], s["day"] = extract_time(text), extract_day(text)
    elif intent == "set_timer":
        s["duration"] = extract_duration(text)
    elif intent == "set_reminder":
        s["task"], s["time"] = extract_task(text), extract_time(text)
        s["duration"], s["day"] = extract_duration(text), extract_day(text)
    elif intent == "get_weather":
        s["city"], s["day"] = extract_city(text), extract_day(text)
    elif intent == "get_time":
        s["city"] = extract_city(text)
    elif intent == "send_message":
        s["contact"], s["message"] = extract_contact(text), extract_message(text)
        if s["contact"] and not s["message"]:
            m = re.search(rf"\b(?:text|message|msg|whatsapp|sms|tell)\s+{re.escape(s['contact'])}\s+(.+)$", text.strip(), flags=re.I)
            if m and not re.match(r"(?:a|an)\s+(?:message|text|sms|whatsapp|email)\b", m.group(1), flags=re.I):
                s["message"] = _strip(m.group(1))
    elif intent == "make_call":
        s["number"], s["contact"] = extract_number(text), extract_contact(text)
    elif intent == "web_search":
        s["query"] = extract_query(text)
    elif intent == "navigate":
        s["place"] = extract_place(text)
    elif intent == "open_website":
        s["site"] = extract_site(text)
    elif intent == "smart_home":
        s.update(extract_smart_home(text) or {})
    return {k: v for k, v in s.items() if v not in (None, "", {})}
