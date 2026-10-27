"""Word and pattern lists for the rules check, in English and Roman Hinglish.

Plain code, no AI (hard rule 5): crisis and age rules must apply on the same turn and must
never depend on Jev. The lists favour clear phrases. Vaguer or indirect wording is left to
the rules in layer 1 and to Jev's second safety net on the next turn (V0_01 section 5).
Every list has tests in `agent/tests/test_rules_check.py`.
"""

from __future__ import annotations

import re


def words(*phrases: str) -> re.Pattern[str]:
    """A pattern that matches any of the phrases as whole words, ignoring case."""
    joined = "|".join(re.escape(p).replace(r"\ ", r"\s+") for p in phrases)
    return re.compile(rf"(?<![a-z])(?:{joined})(?![a-z])", re.IGNORECASE)


# ---- Crisis: thoughts of suicide or self-harm, or being in danger ----
CRISIS = words(
    "kill myself", "killing myself", "end my life", "ending my life", "take my own life",
    "want to die", "wanna die", "wish i was dead", "wish i were dead", "better off dead",
    "better off without me", "no reason to live", "do not want to live", "don't want to live",
    "dont want to live", "do not want to be alive", "don't want to be alive", "suicide",
    "suicidal", "hurt myself", "harm myself", "cut myself", "cutting myself", "self harm",
    "self-harm", "overdose", "end it all", "not worth living", "life is not worth living",
    # Hinglish
    "marna chahta", "marna chahti", "mar jana chahta", "mar jana chahti", "mar jaana chahta",
    "mar jaana chahti", "mar jaun", "mar jaaun", "jeena nahi chahta", "jeena nahi chahti",
    "jeene ka mann nahi", "jeene ka mood nahi", "jeene ki ichha nahi", "khudkushi",
    "khud ko khatam", "apni jaan", "jaan de dunga", "jaan de dungi", "zindagi khatam",
    "sab khatam kar", "suicide karna", "suicide kar",
)

# ---- Hints that may mean the person is thinking about ending their life (never joked about) ----
HINTS = words(
    "giving away my things", "giving away my stuff", "giving away my belongings",
    "gave away my things", "goodbye letter", "goodbye letters", "goodbye note",
    "edge of the balcony", "edge of the roof", "edge of the bridge", "edge of the terrace",
    "what's the point of any of this", "what is the point of any of this",
    "what's the point of living", "what is the point of living",
    "nobody would notice if i was gone", "nobody would even notice if i was gone",
    "no one would notice if i was gone", "nobody would miss me", "can't do this anymore",
    "cannot do this anymore", "can not do this anymore", "wish i could disappear",
    "just disappeared", "just disappear", "i am a burden", "i'm a burden", "a burden to everyone",
    "won't be around much longer", "stopped caring whether i live", "don't see a future",
    "do not see a future", "don't see a future for myself",
    # Hinglish
    "farak nahi padega agar main nahi", "chhod ke chala jaun", "chhod ke chali jaun",
    "gaayab ho jaun", "sab khatam ho jaye", "subah na uthun", "main bojh hoon", "bojh hoon",
)

# ---- A request for medical, legal or money advice (a topic word plus a decision question) ----
ADVICE_TOPIC = words(
    "medicine", "medicines", "medication", "tablet", "tablets", "pills", "dose", "dosage",
    "antibiotic", "antibiotics", "antidepressant", "antidepressants", "insulin", "paracetamol",
    "prescription", "chest pain", "fever", "symptoms", "stock", "stocks", "crypto", "mutual fund",
    "invest", "investing", "loan", "emi", "legal notice", "lawsuit", "court", "contract",
    "sign this", "police case", "case ho gaya", "dawai", "dawa", "goli", "sugar hai", "bimari",
)
ADVICE_ASK = words(
    "should i", "can i", "do i need", "is it okay", "is it safe", "what should", "which",
    "what's the best", "tell me", "how much", "yes or no", "kya main", "kaunsa", "kaun sa",
    "kitna", "kya karun", "bolun", "kharidun", "lun", "kam kar", "chup rahun",
)


def asks_for_advice(text: str) -> bool:
    """A medical, legal or money topic together with a "should I" style question."""
    return bool(ADVICE_TOPIC.search(text) and ADVICE_ASK.search(text))


# ---- Heavy disclosure: something painful was just shared ----
HEAVY = words(
    "passed away", "passed on", "death of", "funeral", "lost my mother",
    "lost my father", "lost my mom", "lost my dad", "lost my brother", "lost my sister",
    "lost my husband", "lost my wife", "lost my job", "got fired", "got laid off", "laid off",
    "diagnosed", "cancer", "miscarriage", "divorce", "breakup", "broke up", "cheated on me",
    "abused", "abuse", "assaulted", "molested", "raped", "in the hospital", "had an accident",
    "was in an accident", "car accident", "heartbroken",
    "i am so alone", "i feel so alone", "feel hopeless", "hopeless", "cannot sleep for weeks",
    "haven't eaten", "have not eaten",
    # Hinglish
    "guzar gaye", "guzar gayi", "guzar gaya", "nahi rahe", "nahi rahi", "nidhan", "cancer hai",
    "naukri chali gayi", "naukri chali gaya", "naukri se nikal", "talaaq", "breakup ho gaya",
    "dil toot", "bahut akela", "akela feel", "hospital mein", "accident ho gaya",
)
# "my mother died", "she just died" (but not "my phone died")
HEAVY_DIED = re.compile(
    r"\b(?:he|she|they|someone|mom|mum|dad|mother|father|brother|sister|friend|grandma|grandpa|"
    r"grandmother|grandfather|uncle|aunt|dog|cat|husband|wife|boyfriend|girlfriend)\s+"
    r"(?:just\s+|recently\s+)?died\b",
    re.IGNORECASE,
)


def is_heavy(text: str) -> bool:
    """Something painful was just shared."""
    return bool(HEAVY.search(text) or HEAVY_DIED.search(text))


# ---- The person is bringing lightness back ----
LIGHT = words(
    "haha", "hahaha", "hehe", "lol", "lmao", "joke", "kidding", "funny", "mazaak", "masti"
)

# ---- Under 18: only clear statements about the speaker (ending a call is a heavy step) ----
_AGE_UNIT = r"(?:years?|yrs?|saal|sal|varsh)"
UNDER_18 = [
    # "I am 15 years old", "I'm 16 yrs"
    re.compile(rf"\b(?:i\s*am|i'm|im)\s+(\d{{1,2}})\s*{_AGE_UNIT}\b", re.IGNORECASE),
    # "my age is 16", "meri age 15 hai", "meri umar 14 hai"
    re.compile(
        r"\b(?:my\s+age\s+is|my\s+age|meri\s+age|meri\s+umar|meri\s+umr)"
        r"\s+(?:is\s+|hai\s+)?(\d{1,2})\b",
        re.IGNORECASE,
    ),
    # "main 16 saal ka hoon"
    re.compile(rf"\b(?:main|mai|mein)\s+(\d{{1,2}})\s*{_AGE_UNIT}\b", re.IGNORECASE),
    # "I just turned 16", "I'm turning 17 next month" (not "turned 16 years ago", not others)
    re.compile(
        r"\bi(?:'m|\s+am)?\s+(?:just\s+)?turn(?:ed|ing)\s+(\d{1,2})\b(?!\s*(?:years?|yrs?)\s+ago)",
        re.IGNORECASE,
    ),
    # "I am 15." or "I am 15 and ..." (but not "I am 15 minutes late")
    re.compile(
        r"\b(?:i\s*am|i'm|im)\s+(\d{1,2})\s*(?:$|[.,!?]|and\b|but\b|so\b)", re.IGNORECASE
    ),
]
UNDER_18_PHRASES = [
    re.compile(r"\bi(?:'m|\s+am)?\s+(?:a\s+)?(?:minor|underage)\b", re.IGNORECASE),
    # "I am in class 10", "I'm studying in class 9"
    re.compile(
        r"\bi(?:'m|\s+am)?\s+(?:currently\s+)?(?:studying\s+)?in\s+"
        r"(?:class|grade|std|standard)\s*(?:5|6|7|8|9|10)\b",
        re.IGNORECASE,
    ),
    # "I am in 10th standard"
    re.compile(
        r"\bi(?:'m|\s+am)?\s+(?:currently\s+)?(?:studying\s+)?in\s+(?:5|6|7|8|9|10)th\s+"
        r"(?:class|grade|std|standard)\b",
        re.IGNORECASE,
    ),
    # "main class 10 mein hoon", "main 9th mein padhta hoon"
    re.compile(
        r"\b(?:main|mai)\s+(?:class\s+)?(?:5|6|7|8|9|10)(?:th)?\s*(?:class\s*)?(?:mein|me)\b",
        re.IGNORECASE,
    ),
]


def mentions_school_age(text: str) -> bool:
    return any(p.search(text) for p in UNDER_18_PHRASES)


# ---- Hindi and Hinglish markers (to know whether the person has used Hindi yet) ----
HINDI = words(
    "yaar", "yar", "hai", "hain", "nahi", "nahin", "kya", "kyun", "kaise", "kab", "kahan",
    "acha", "accha", "achha", "theek", "thik", "bhai", "behen", "haan", "mujhe", "mera", "meri",
    "mere", "aap", "tum", "tumhe", "hum", "kal", "aaj", "bahut", "bohot", "thoda", "zyada",
    "kuch", "matlab", "bas", "abhi", "ghar", "kaam", "baat", "dost", "mummy", "papa", "chalo",
    "arre", "arrey", "toh", "wala", "wali", "raha", "rahi", "gaya", "gayi", "karna", "karo",
    "chahta", "chahti", "lagta", "lagti", "pata", "sach", "dekho", "suno", "bolo",
)

# Words that must not count as a "Hindi" signal on their own because they are common English
HINDI_AMBIGUOUS = {"bas", "kal", "hum", "wala", "toh", "pata", "sach", "mera"}

# ---- Sending the person to a professional ----
PROFESSIONAL_WORDS = (
    "doctor", "pharmacist", "physician", "lawyer", "advocate", "solicitor", "financial adviser",
    "financial advisor", "adviser", "advisor", "professional", "chartered accountant",
)


def mentions_professional(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in PROFESSIONAL_WORDS)


# ---- Helplines ----
HELPLINE_NUMBERS = ("14416", "112")


def mentions_helplines(text: str) -> bool:
    """True when a reply carries both the Tele-MANAS number and the emergency number."""
    compact = re.sub(r"[\s-]", "", text)
    return all(number in compact for number in HELPLINE_NUMBERS)


def under_18_age(text: str) -> int | None:
    """The age stated in the text, if it is under 18 and clearly about the speaker."""
    for pattern in UNDER_18:
        match = pattern.search(text)
        if match and 5 <= int(match.group(1)) <= 17:
            return int(match.group(1))
    return None
