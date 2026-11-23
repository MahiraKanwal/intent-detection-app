"""Display information for every intent the model knows."""

INTENTS = {
    "play_music":    {"label": "Play Music",     "icon": "🎵", "hint": "Plays a song or playlist on YouTube / Spotify",   "example": "play shape of you"},
    "set_alarm":     {"label": "Set Alarm",      "icon": "⏰", "hint": "Rings at a clock time while this tab is open",     "example": "wake me up at 6:30 am"},
    "set_timer":     {"label": "Set Timer",      "icon": "⏳", "hint": "Counts down and rings when time is up",            "example": "set a timer for 10 minutes"},
    "set_reminder":  {"label": "Set Reminder",   "icon": "📌", "hint": "Notifies you and adds it to Google Calendar",      "example": "remind me to buy milk at 5 pm"},
    "get_weather":   {"label": "Weather",        "icon": "🌤️", "hint": "Opens the weather forecast for a city",            "example": "weather in lahore"},
    "send_message":  {"label": "Send Message",   "icon": "💬", "hint": "Opens WhatsApp with your message ready",           "example": "text ali that i will be late"},
    "make_call":     {"label": "Make Call",      "icon": "📞", "hint": "Dials a number or opens WhatsApp Web",             "example": "call 03001234567"},
    "web_search":    {"label": "Web Search",     "icon": "🔎", "hint": "Searches Google for your question",                "example": "search for machine learning"},
    "navigate":      {"label": "Navigate",       "icon": "🧭", "hint": "Opens Google Maps directions",                     "example": "directions to faisal mosque"},
    "get_time":      {"label": "Time & Date",    "icon": "🕒", "hint": "Tells the current time or date",                   "example": "what time is it"},
    "open_website":  {"label": "Open Website",   "icon": "🌐", "hint": "Opens a website in a new tab",                     "example": "open github"},
    "smart_home":    {"label": "Smart Home",     "icon": "💡", "hint": "Switches virtual lights, fan, AC, TV and door",    "example": "turn off the bedroom light"},
    "tell_joke":     {"label": "Tell a Joke",    "icon": "😄", "hint": "Tells a joke",                                     "example": "tell me a joke"},
    "calculate":     {"label": "Calculate",      "icon": "🧮", "hint": "Solves the arithmetic in your sentence",           "example": "what is 15 percent of 200"},
    "greeting":      {"label": "Greeting",       "icon": "👋", "hint": "Replies to greetings, thanks and small talk",      "example": "good morning"},
}


def label_of(intent: str) -> str:
    return INTENTS.get(intent, {}).get("label", intent.replace("_", " ").title())
