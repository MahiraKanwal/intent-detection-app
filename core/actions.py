"""Maps (intent + slots) to a concrete action the browser can carry out.

Action types returned to the frontend:
  open_url   -> open `url` in a new tab
  alarm      -> schedule an in-page alarm (`hhmm`, `day`)
  timer      -> start an in-page countdown (`seconds`)
  reminder   -> in-page notification (if time/duration known) + Google Calendar link
  show_time  -> show the visitor's local time/date
  smart_home -> switch the virtual device panel
  reply      -> just show `message`
"""
import random
import re
from urllib.parse import quote_plus

from .calc import solve
from .slots import site_url

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I told my computer I needed a break, and now it won't stop sending me Kit-Kat ads.",
    "Why did the scarecrow win an award? He was outstanding in his field.",
    "There are 10 kinds of people: those who understand binary and those who don't.",
    "Why was the math book sad? It had too many problems.",
    "What do you call a fake noodle? An impasta.",
    "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
    "Why did the machine learning model go to therapy? It couldn't stop overfitting its past.",
    "I would tell you a UDP joke, but you might not get it.",
    "Why don't scientists trust atoms? Because they make up everything.",
    "What's a computer's favourite snack? Microchips.",
    "Why did the developer go broke? He used up all his cache.",
]


def _greeting_reply(text: str) -> str:
    t = text.lower()
    if re.search(r"assalam|salam", t):
        return "Wa alaikum assalam! How can I help you today?"
    if re.search(r"\b(bye|goodbye|see you|take care|khuda hafiz|catch you later|peace)\b", t):
        return "Goodbye! Come back whenever you need me."
    if re.search(r"\b(thanks|thank you|shukriya)\b", t):
        return "You're welcome!"
    if re.search(r"who are you|what can you do|\bhelp\b|capable", t):
        return ("I'm an NLP intent detector. Give me a short command like “play music”, "
                "“set an alarm for 7 am” or “weather in lahore” and I'll work out what you want and do it.")
    if re.search(r"good morning", t):
        return "Good morning! What would you like to do?"
    if re.search(r"good (evening|night|afternoon)", t):
        return "Hello! What can I do for you?"
    if re.search(r"how are you|how's it going|how is it going|how are things|what's up|kya haal", t):
        return "Doing great, thanks for asking! What can I do for you?"
    return "Hello! Tell me what you'd like me to do."


def _url(base: str, **params) -> str:
    return base + "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())


def build_action(intent: str, slots: dict, text: str) -> dict:
    if intent == "play_music":
        song = slots.get("song") or "top trending songs"
        if slots.get("platform") == "spotify":
            url = "https://open.spotify.com/search/" + quote_plus(song)
            where = "Spotify"
        else:
            url = "https://www.youtube.com/results?search_query=" + quote_plus(song)
            where = "YouTube"
        return {"type": "open_url", "url": url, "button": f"Play on {where}",
                "message": f"Searching {where} for “{song}”."}

    if intent == "set_alarm":
        t = slots.get("time")
        if not t:
            return {"type": "reply", "message": "I understood an alarm, but couldn't find a time. Try “set an alarm for 7:30 am”."}
        return {"type": "alarm", "hhmm": t["hhmm"], "day": slots.get("day"),
                "message": f"Alarm set for {t['hhmm']}" + (f" ({slots['day']})" if slots.get("day") else "") + "."}

    if intent == "set_timer":
        d = slots.get("duration")
        if not d:
            return {"type": "reply", "message": "I understood a timer, but couldn't find a duration. Try “timer for 10 minutes”."}
        return {"type": "timer", "seconds": d["seconds"], "label": "Timer",
                "message": f"Timer started for {d['pretty']}."}

    if intent == "set_reminder":
        task = slots.get("task") or "Reminder"
        cal = _url("https://calendar.google.com/calendar/render?action=TEMPLATE&", text=task)
        return {"type": "reminder", "task": task, "seconds": (slots.get("duration") or {}).get("seconds"),
                "hhmm": (slots.get("time") or {}).get("hhmm"), "day": slots.get("day"), "url": cal,
                "button": "Add to Google Calendar", "message": f"Reminder: {task}."}

    if intent == "get_weather":
        city = slots.get("city")
        q = f"weather {city}" if city else "weather"
        if slots.get("day"):
            q += f" {slots['day']}"
        return {"type": "open_url", "url": "https://www.google.com/search?q=" + quote_plus(q),
                "button": "Open forecast", "message": f"Opening the weather for {city or 'your location'}."}

    if intent == "send_message":
        contact, msg = slots.get("contact"), slots.get("message")
        url = "https://wa.me/?text=" + quote_plus(msg) if msg else "https://web.whatsapp.com/"
        who = f" to {contact}" if contact else ""
        note = "" if msg else " (no message text found, opening WhatsApp Web)"
        return {"type": "open_url", "url": url, "button": "Open WhatsApp",
                "message": f"Preparing a WhatsApp message{who}{note}. Pick the chat and press send."}

    if intent == "make_call":
        number, contact = slots.get("number"), slots.get("contact")
        if number:
            return {"type": "open_url", "url": "tel:" + number, "button": f"Call {number}",
                    "message": f"Dialling {number}."}
        who = contact or "your contact"
        return {"type": "open_url", "url": "https://web.whatsapp.com/", "button": "Open WhatsApp Web",
                "message": f"No phone number found for {who}. Open WhatsApp Web to call from there."}

    if intent == "web_search":
        q = slots.get("query") or text
        return {"type": "open_url", "url": "https://www.google.com/search?q=" + quote_plus(q),
                "button": "Search on Google", "message": f"Searching Google for “{q}”."}

    if intent == "navigate":
        place = slots.get("place")
        if not place:
            return {"type": "reply", "message": "I understood navigation, but couldn't find a destination. Try “directions to faisal mosque”."}
        if re.search(r"\bnear(est|by)?\b|\bclosest\b", text.lower()):
            url = "https://www.google.com/maps/search/" + quote_plus(place)
        else:
            url = "https://www.google.com/maps/dir/?api=1&destination=" + quote_plus(place)
        return {"type": "open_url", "url": url, "button": "Open Google Maps",
                "message": f"Opening Google Maps for “{place}”."}

    if intent == "get_time":
        city = slots.get("city")
        if city:
            return {"type": "open_url", "url": "https://time.is/" + quote_plus(city.replace(" ", "_")),
                    "button": f"Time in {city.title()}", "message": f"Opening the current time in {city.title()}."}
        return {"type": "show_time", "message": "Here is your local time."}

    if intent == "open_website":
        name = slots.get("site")
        if not name:
            return {"type": "reply", "message": "I understood “open a website”, but couldn't tell which one. Try “open github”."}
        url = site_url(name) or "https://www.google.com/search?q=" + quote_plus(name + " official website")
        return {"type": "open_url", "url": url, "button": f"Open {name.title()}",
                "message": f"Opening {name}."}

    if intent == "smart_home":
        device, state = slots.get("device"), slots.get("state")
        if not device:
            return {"type": "reply", "message": "Which device? Try “turn on the fan” or “lock the door”."}
        names = {"lights": "Lights", "fan": "Fan", "ac": "AC", "tv": "TV", "heater": "Heater", "door": "Front door",
                 "geyser": "Geyser", "coffee": "Coffee maker"}
        room = f" ({slots['room']})" if slots.get("room") else ""
        return {"type": "smart_home", "device": device, "state": state or "on", "value": slots.get("value"),
                "room": slots.get("room"),
                "message": f"{names.get(device, device.title())}{room} is now {state or 'on'}"
                           + (f" at {slots['value']}°C" if slots.get("value") else "") + "."}

    if intent == "tell_joke":
        return {"type": "reply", "message": random.choice(JOKES)}

    if intent == "calculate":
        r = solve(text)
        if not r:
            return {"type": "reply", "message": "I understood a calculation, but couldn't read the numbers. Try “what is 15 percent of 200”."}
        return {"type": "reply", "message": f"{r['expression']} = {r['result']}", "result": r["result"]}

    if intent == "greeting":
        return {"type": "reply", "message": _greeting_reply(text)}

    return {"type": "reply", "message": "I'm not sure what to do with that."}
