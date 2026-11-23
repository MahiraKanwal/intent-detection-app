"""Builds data/intents.csv: a labelled dataset of short voice-style commands.

Method: hand-written sentence templates per intent + slot fillers (songs, cities,
times ...) + realistic noise (polite prefixes/suffixes, casing, missing
punctuation, typos). Includes some Roman-Urdu commands.

Run:  python build_dataset.py
"""
import csv
import random
import re
from collections import Counter
from pathlib import Path

random.seed(7)
ROOT = Path(__file__).parent
OUT = ROOT / "data" / "intents.csv"
PER_INTENT = 260

SLOTS = {
    "song": ["shape of you", "tum hi ho", "blinding lights", "kesariya", "coke studio", "believer", "faded",
             "perfect", "senorita", "levitating", "bad guy", "lofi beats", "arijit singh", "atif aslam",
             "ed sheeran", "taylor swift", "bohemian rhapsody", "pasoori", "afreen afreen", "dil dil pakistan",
             "nusrat fateh ali khan", "imran khan songs", "someone like you", "closer", "dance monkey"],
    "genre": ["jazz", "rock", "pop music", "lofi", "classical music", "bollywood songs", "hip hop", "qawwali",
              "relaxing music", "sad songs", "workout music", "punjabi songs", "instrumental music"],
    "time": ["6 am", "7:30 am", "5 pm", "8 o'clock", "6:15", "noon", "midnight", "4:45 pm", "9 pm", "5:30 am",
             "10 pm", "seven thirty", "half past six", "6 in the morning", "quarter to seven", "7", "5:00",
             "3:15 pm", "11 am", "6:45 am", "4 am", "8:30 in the evening"],
    "duration": ["5 minutes", "10 minutes", "30 seconds", "1 hour", "15 minutes", "2 hours", "45 seconds",
                 "20 mins", "90 seconds", "an hour", "half an hour", "three minutes", "two minutes",
                 "one minute", "25 minutes", "ten minutes", "45 minutes", "a minute", "40 seconds", "1 minute"],
    "task": ["buy milk", "take my medicine", "submit the assignment", "call the plumber", "pay the electricity bill",
             "water the plants", "go to the gym", "attend the meeting", "book tickets", "study for the exam",
             "pick up the kids", "send the report", "charge my phone", "feed the cat", "renew my passport",
             "drink water", "buy groceries", "call the bank", "check my email"],
    "when": ["tomorrow", "tonight", "this evening", "next monday", "on friday", "today", "this weekend",
             "tomorrow morning", "on saturday"],
    "city": ["islamabad", "lahore", "karachi", "london", "new york", "dubai", "tokyo", "paris", "peshawar",
             "rawalpindi", "quetta", "multan", "istanbul", "toronto", "sydney", "berlin", "murree", "faisalabad"],
    "contact": ["mom", "dad", "ali", "sara", "ahmed", "my brother", "hassan", "ayesha", "my boss", "john",
                "fatima", "bilal", "zainab", "uncle", "the doctor", "usman", "my wife", "hamza", "my friend"],
    "msg": ["i will be late", "happy birthday", "where are you", "call me back", "see you tomorrow",
            "dinner is ready", "i am on my way", "the meeting is at 5", "thanks for the help",
            "let's meet at the cafe", "good morning", "i'll be there in ten minutes", "i reached home"],
    "number": ["03001234567", "0321 5551234", "+923331234567", "555 0199", "03451234567", "0300 1112223"],
    "query": ["machine learning", "python tutorials", "best laptops under 1000 dollars", "capital of france",
              "how photosynthesis works", "nlp project ideas", "pakistan independence day", "latest news",
              "cricket scores", "recipe for biryani", "tf idf explained", "albert einstein", "stock market today",
              "iphone price", "bitcoin price", "benefits of exercise", "history of the internet",
              "scikit learn documentation", "football world cup winners", "flask tutorial"],
    "person": ["elon musk", "albert einstein", "imran khan", "quaid e azam", "cristiano ronaldo", "bill gates",
               "malala yousafzai", "alan turing"],
    "howto": ["tie a tie", "cook rice", "install python", "learn nlp", "reset a router", "make tea",
              "write a resume", "lose weight", "train a classifier"],
    "place": ["the airport", "the nearest hospital", "faisal mosque", "lahore fort", "the train station",
              "giga mall", "centaurus mall", "my office", "the university", "the city center", "badshahi mosque",
              "the beach", "murree", "f-10 markaz", "the bus stand", "home"],
    "poi": ["pizza place", "petrol pump", "atm", "pharmacy", "coffee shop", "restaurant", "hospital", "mosque",
            "supermarket", "hotel", "bank"],
    "site": ["youtube", "facebook", "google", "gmail", "github", "twitter", "instagram", "linkedin", "whatsapp",
             "netflix", "wikipedia", "amazon", "stackoverflow", "reddit", "daraz", "spotify", "chatgpt",
             "canva", "kaggle", "google drive", "youtube.com", "github.com"],
    "device": ["lights", "light", "fan", "ac", "air conditioner", "tv", "heater", "bedroom light",
               "kitchen lights", "lamp", "coffee maker", "geyser", "living room lights", "bathroom light",
               "porch light"],
    "temp": ["18", "20", "22", "24", "25", "26", "28"],
    "q2": ["deep learning", "java", "tea and coffee", "a virus and a bacteria", "tcp and udp", "a list and a tuple",
           "precision and accuracy", "weather and climate"],
    "food": ["a banana", "an apple", "a slice of pizza", "a cup of rice", "an egg", "a samosa", "a bowl of oats"],
    "kind": ["dad", "funny", "programming", "short", "clean", "silly", "random"],
    "a": [str(n) for n in (2, 3, 5, 7, 8, 9, 12, 15, 18, 20, 25, 36, 45, 50, 64, 75, 100, 120, 144, 250, 500, 1200)],
    "b": [str(n) for n in (2, 3, 4, 6, 7, 9, 10, 11, 12, 14, 16, 25, 30, 40, 55, 80, 125, 300)],
    "c": [str(n) for n in (1, 2, 5, 10, 20, 100)],
    "p": ["5", "10", "15", "20", "25", "30", "50", "75"],
}

TEMPLATES = {
    "play_music": [
        "i'm in the mood for {genre}", "play some tunes", "bring on the {genre}", "put some {genre} on", "i want some {genre} right now", "blast {song}", "let me hear some {genre} while i work",
        "play {song}", "play some {genre}", "put on {song}", "i want to listen to {song}",
        "start playing {song}", "play the song {song}", "can you play {song}", "play {song} on youtube",
        "play {song} on spotify", "turn on some music", "play music", "play my favorite songs",
        "shuffle my playlist", "play the next song", "i feel like listening to {song}", "queue up {song}",
        "let's hear {song}", "music please", "play something relaxing", "start my workout playlist",
        "play {genre} on spotify", "i'd like to hear some {genre}", "could you put on some {genre}",
        "play me {song}", "throw on {song}", "gana chalao", "{song} chalao", "koi acha sa gana lagao",
        "{song} sunao", "mujhe {song} sunna hai", "music chalao",
    ],
    "set_alarm": [
        "set my wakeup call for {time}", "set a wake up call for {time}", "make sure i wake up at {time}", "alarm please for {time}", "get me up at {time} sharp",
        "set an alarm for {time}", "wake me up at {time}", "alarm at {time}", "set alarm {time}",
        "create an alarm for {time}", "i need an alarm at {time}", "please wake me at {time} tomorrow",
        "set my alarm to {time}", "can you set an alarm for {time}", "add a new alarm for {time}",
        "schedule an alarm at {time}", "wake me up tomorrow at {time}", "set a wake up alarm for {time}",
        "set a recurring alarm for {time} every weekday", "alarm lagao {time} ka", "subah {time} baje alarm lagao",
        "mujhe {time} par jagana", "{time} ka alarm set karo", "set the alarm {time}", "i want to wake up at {time}",
        "alarm for {time} tomorrow morning", "wake me at {time}",
    ],
    "set_timer": [
        "set a timer for {duration}", "timer for {duration}", "start a {duration} timer", "countdown {duration}",
        "count down from {duration}", "set timer {duration}", "begin a timer of {duration}",
        "can you time {duration} for me", "{duration} timer please", "{duration} ka timer lagao",
        "timer start karo {duration}", "i need a timer for {duration}", "start a {duration} countdown",
        "set a cooking timer for {duration}", "start the timer for {duration}", "put a timer on for {duration}",
        "set a {duration} timer", "timer {duration}",
    ],
    "set_reminder": [
        "remind me to {task}", "remind me to {task} at {time}", "set a reminder to {task}",
        "remind me to {task} {when}", "add a reminder {task}", "don't let me forget to {task}",
        "create a reminder for {task} at {time}", "reminder to {task} {when}", "remind me about {task} {when}",
        "i need a reminder to {task}", "remind me in {duration} to {task}", "mujhe yaad dilana ke {task}",
        "{task} ka reminder lagao", "yaad dilao {task} {when}", "note a reminder to {task} at {time}",
        "set a reminder for {when} to {task}", "please remind me to {task} {when}", "reminder {task} at {time}",
        "make a note to remind me to {task}",
    ],
    "get_weather": [
        "what's the weather like in {city}", "weather in {city}", "how's the weather today",
        "will it rain {when}", "what is the temperature in {city}", "is it going to rain in {city}",
        "weather forecast for {city}", "do i need an umbrella today", "how hot is it in {city}",
        "is it cold outside", "show me the {city} weather", "what's the forecast for {when}",
        "aaj mausam kaisa hai", "{city} ka mausam batao", "kya aaj barish hogi", "temperature in {city} right now",
        "what's the weather {when}", "is it sunny in {city}", "check the weather in {city}", "weather today",
        "how cold is it in {city} {when}", "tell me the weather",
    ],
    "send_message": [
        "send a message to {contact} saying {msg}", "text {contact} {msg}", "message {contact} that {msg}",
        "send {contact} a text {msg}", "whatsapp {contact} {msg}", "tell {contact} {msg}",
        "send an sms to {contact}", "write a message to {contact}", "send a whatsapp message to {contact} saying {msg}",
        "text {contact}", "compose a message for {contact}", "{contact} ko message bhejo {msg}",
        "{contact} ko whatsapp karo", "message bhejo {contact} ko ke {msg}",
        "send an email to {contact} saying {msg}", "send {contact} a message", "drop a text to {contact} {msg}",
        "let {contact} know that {msg}", "send {msg} to {contact}", "whatsapp {contact} saying {msg}",
    ],
    "make_call": [
        "connect me with {contact}", "get {contact} on the phone", "i want to talk to {contact}", "ring {contact} up", "connect me to {contact}", "call customer care at {number}",
        "call {contact}", "phone {contact}", "dial {contact}", "make a call to {contact}", "ring {contact}",
        "give {contact} a call", "can you call {contact}", "call {contact} on speaker",
        "start a video call with {contact}", "dial {number}", "call {number}", "{contact} ko call karo",
        "{contact} ko phone lagao", "{contact} se baat karao", "call my {contact}", "please call {contact}",
        "i want to call {contact}", "phone call to {contact}", "make a phone call to {number}",
        "start a voice call with {contact}",
    ],
    "web_search": [
        "what's the difference between {query} and {q2}", "how many calories in {food}", "what does {query} mean", "meaning of {query}", "find me tutorials on {query}", "who won the {query}", "look for cheap {query}", "how many calories are in {food}", "difference between {q2}",
        "search for {query}", "google {query}", "look up {query}", "find information about {query}",
        "search the web for {query}", "what is {query}", "who is {person}", "tell me about {query}",
        "i want to know about {query}", "search {query} on google", "show me results for {query}",
        "{query} ke bare mein search karo", "google par {query} dhundo", "find me {query}", "how to {howto}",
        "search images of {query}", "how do i {howto}", "look for {query} online", "search about {person}",
        "can you search {query}", "find {query}", "when was {person} born", "why is {query} important",
    ],
    "navigate": [
        "navigate to {place}", "give me directions to {place}", "how do i get to {place}", "take me to {place}",
        "show me the route to {place}", "find the way to {place}", "directions to {place}", "where is {place}",
        "find {poi} near me", "nearest {poi}", "how far is {place}", "map of {place}", "start navigation to {place}",
        "{place} ka rasta batao", "mujhe {place} jana hai", "nearest {poi} kahan hai", "closest {poi} to me",
        "show {place} on the map", "drive me to {place}", "how long to get to {place}", "route to {place}",
    ],
    "get_time": [
        "how late is it", "how late is it in {city}", "what hour is it", "what hour is it in {city}", "is it already {time}", "what's the date", "tell me the date and day", "is it past {time} yet",
        "what time is it", "what's the time", "tell me the current time", "what time is it in {city}",
        "current time please", "do you know the time", "time now", "what is the time in {city}",
        "what's today's date", "what day is it today", "what is the date today", "abhi kitne baje hain",
        "time kya hua hai", "aaj kya tareekh hai", "{city} mein kya time ho raha hai", "tell me the time",
        "what's the time in {city} right now", "current date", "what is today", "time check",
    ],
    "open_website": [
        "open {site}", "go to {site} website", "launch {site}", "open {site} for me", "visit {site}",
        "open the {site} website", "start {site}", "open {site} in a new tab", "bring up {site}",
        "{site} kholo", "{site} open karo", "{site} par le jao", "take me to the {site} website",
        "i want to open {site}", "can you open {site}", "load {site}", "open my {site}", "pull up {site}",
    ],
    "smart_home": [
        "turn on the {device}", "turn off the {device}", "switch on the {device}", "switch off the {device}",
        "{device} on", "{device} off", "please turn the {device} on", "dim the lights",
        "set the thermostat to {temp} degrees", "make the room cooler", "lock the front door", "unlock the door",
        "turn the {device} off", "switch the {device} on", "{device} band karo", "{device} on karo",
        "{device} band kar do", "{device} jala do", "set the ac to {temp}", "shut off the {device}",
        "kill the {device}", "turn it up a bit warmer", "lock the door", "can you turn off the {device}",
    ],
    "tell_joke": [
        "cheer me up", "make me smile", "entertain me", "i'm bored say something funny", "give me a laugh", "make me chuckle", "lighten the mood with something funny",
        "tell me a joke", "say something funny", "make me laugh", "i want to hear a joke", "got any jokes",
        "tell me a funny joke", "joke please", "crack a joke", "tell me a {kind} joke",
        "can you tell me something funny", "cheer me up with a joke", "koi latifa sunao", "mujhe hasao",
        "ek joke sunao", "funny baat batao", "tell me a dad joke", "do you know any jokes", "say a joke",
        "i need a laugh", "tell me another joke",
    ],
    "calculate": [
        "what is {a} plus {b}", "calculate {a} times {b}", "{a} divided by {b}", "how much is {a} minus {b}",
        "{a} + {b}", "{a} * {b}", "what's {a} multiplied by {b}", "compute {a} plus {b} minus {c}",
        "square root of {a}", "what is {p} percent of {a}", "add {a} and {b}", "subtract {b} from {a}",
        "multiply {a} by {b}", "divide {a} by {b}", "{a} plus {b} kitne hotay hain", "{a} ko {b} se multiply karo",
        "solve {a} * {b} + {c}", "{a} - {b}", "{a} / {b}", "calculate {p} percent of {a}", "{a} x {b}",
        "what's {a} times {b}", "{a} minus {b} equals", "work out {a} plus {b}",
    ],
    "greeting": [
        "how is it going", "how are things", "nice to see you", "long time no see", "what's new", "catch you later", "salam kaise ho", "assalam o alaikum kaise ho", "how's everything",
        "hello", "hi", "hey there", "good morning", "good evening", "good afternoon", "hi assistant",
        "hello how are you", "how are you", "what's up", "hey buddy", "greetings", "yo", "hey assistant",
        "good night", "bye", "goodbye", "see you later", "thanks", "thank you", "assalam o alaikum", "salam",
        "kya haal hai", "shukriya", "khuda hafiz", "who are you", "what can you do", "help", "hey",
        "thanks a lot", "nice to meet you", "how's your day", "see you", "take care", "hello there",
    ],
}

PREFIX = ["", "", "", "", "", "please ", "hey assistant ", "ok ", "hey ", "yo ", "um ", "so ", "assistant ",
          "hey assistant can you ", "could you ", "i want you to "]
SUFFIX = ["", "", "", "", "", " please", " for me", " now", " thanks", " right now", " asap"]
QUESTION_STARTS = ("what", "how", "is", "will", "do", "where", "who", "can", "when", "why", "kya", "abhi")


def fill(template: str) -> str:
    keys = set(re.findall(r"{(\w+)}", template))
    return template.format(**{k: random.choice(SLOTS[k]) for k in keys})


def typo(s: str) -> str:
    if len(s) < 6:
        return s
    i = random.randrange(1, len(s) - 2)
    kind = random.choice(["drop", "dup", "swap"])
    if kind == "drop":
        return s[:i] + s[i + 1:]
    if kind == "dup":
        return s[:i] + s[i] + s[i:]
    return s[:i] + s[i + 1] + s[i] + s[i + 2:]


def noisy(s: str, allow_prefix: bool = True) -> str:
    if allow_prefix:
        s = random.choice(PREFIX) + s
    s += random.choice(SUFFIX)
    s = s.strip()
    if s.split()[0] in QUESTION_STARTS and random.random() < 0.5:
        s += "?"
    r = random.random()
    if r < 0.60:
        s = s.lower()
    elif r < 0.90:
        s = s[:1].upper() + s[1:]
    else:
        s = s.upper()
    if random.random() < 0.12:
        s = typo(s)
    return s


def main():
    rows = []
    for intent, templates in TEMPLATES.items():
        seen = set()
        attempts = 0
        while len(seen) < PER_INTENT and attempts < 40000:
            attempts += 1
            text = noisy(fill(random.choice(templates)))
            key = re.sub(r"\W+", " ", text.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            rows.append((text, intent))
    random.shuffle(rows)
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text", "intent"])
        w.writerows(rows)
    counts = Counter(i for _, i in rows)
    print(f"Wrote {len(rows)} rows to {OUT}")
    for k, v in sorted(counts.items()):
        print(f"  {k:<14}{v}")


if __name__ == "__main__":
    main()
