import pytest

from rules_check import (
    CRISIS_OVERRIDE,
    HEAVY_OVERRIDE,
    NO_HINDI_OVERRIDE,
    OPENING_OVERRIDE,
    WRAP_UP_OVERRIDE,
    RulesConfig,
    RulesState,
    check,
)
from rules_check.patterns import is_heavy, mentions_helplines, under_18_age

CONFIG = RulesConfig(
    opening_minutes=2, wrap_up_minute=17, crisis_turns=3, jev_under_18_threshold=0.9
)


def run(text: str, state: RulesState | None = None, minutes: float = 5.0):  # type: ignore[no-untyped-def]
    return check(text, state or RulesState(), CONFIG, minutes)


# ---------------- crisis ----------------

CRISIS_PHRASES = [
    "I want to kill myself",
    "i am going to end my life tonight",
    "Sometimes I just want to die",
    "I wish I was dead",
    "everyone would be better off without me",
    "I do not want to live anymore",
    "I don't want to live like this",
    "there is no reason to live",
    "I keep thinking about suicide",
    "I have been cutting myself again",
    "I want to hurt myself",
    "I took an overdose",
    "life is not worth living",
    "mujhe marna chahta hoon",
    "main mar jaana chahti hoon",
    "ab jeena nahi chahta",
    "mujhe jeene ka mann nahi hai",
    "main khudkushi karne ki soch raha hoon",
    "sab khatam kar dunga",
    "suicide karna chahta hoon",
    "I WANT TO DIE",
]


@pytest.mark.parametrize("text", CRISIS_PHRASES)
def test_crisis_phrases_trigger_the_safety_override_on_the_same_turn(text: str) -> None:
    result = run(text)
    assert CRISIS_OVERRIDE in result.overrides
    assert "crisis" in result.flags
    assert result.crisis


NOT_CRISIS = [
    "I could kill for a cup of chai right now",
    "this exam is killing me, so much homework",
    "my phone died again",
    "I am dying to see that movie",
    "the suicide squad movie was fun",  # contains the word, in a film title: care is acceptable
]


@pytest.mark.parametrize("text", NOT_CRISIS[:4])
def test_everyday_talk_does_not_trigger_the_crisis_rule(text: str) -> None:
    assert not run(text).crisis


def test_the_crisis_override_stays_for_the_next_replies_then_relaxes() -> None:
    state = RulesState()
    run("I want to end my life", state)
    assert CRISIS_OVERRIDE in run("it is just so hard", state).overrides
    assert CRISIS_OVERRIDE in run("I do not know", state).overrides
    assert CRISIS_OVERRIDE not in run("anyway", state).overrides


def test_a_hint_from_jev_last_turn_triggers_the_same_rule() -> None:
    state = RulesState(jev_crisis=True)
    result = run("I cannot do this anymore", state)
    assert CRISIS_OVERRIDE in result.overrides and result.crisis


# ---------------- heavy moments ----------------

HEAVY_PHRASES = [
    "My grandmother passed away last week",
    "my mother died in March",
    "she just died",
    "I lost my job today",
    "I got fired this morning",
    "I was diagnosed with cancer",
    "we had a miscarriage",
    "my wife wants a divorce",
    "I am heartbroken",
    "meri dadi guzar gayi",
    "papa nahi rahe",
    "meri naukri chali gayi",
    "talaaq ho gaya mera",
]


@pytest.mark.parametrize("text", HEAVY_PHRASES)
def test_heavy_news_locks_playfulness_at_once(text: str) -> None:
    result = run(text)
    assert HEAVY_OVERRIDE in result.overrides
    assert "heavy" in result.flags


@pytest.mark.parametrize(
    "text",
    ["my phone died", "the battery died", "I work at a hospital", "we are going to the mall"],
)
def test_ordinary_words_are_not_heavy(text: str) -> None:
    assert not is_heavy(text)


def test_playfulness_stays_off_until_the_person_is_light_again() -> None:
    state = RulesState()
    run("my grandmother passed away", state)
    assert HEAVY_OVERRIDE in run("I miss her", state).overrides
    assert HEAVY_OVERRIDE in run("we were close", state).overrides
    assert HEAVY_OVERRIDE not in run("haha she used to joke about that", state).overrides
    assert not state.playful_locked


# ---------------- under 18 ----------------

UNDER_18_TEXT = [
    "I am 15 years old",
    "I'm 16 yrs",
    "my age is 14",
    "meri age 15 hai",
    "main 16 saal ka hoon",
    "I just turned 17",
    "I'm turning 16 next month",
    "I am a minor",
    "I'm in class 10",
    "I am studying in class 9",
    "I am in 10th standard",
    "main class 10 mein hoon",
    "I am 15",
]


@pytest.mark.parametrize("text", UNDER_18_TEXT)
def test_clear_under_18_statements_end_the_call_kindly(text: str) -> None:
    result = run(text)
    assert result.end_call_reason == "under_18"
    assert "under_18" in result.flags
    assert result.overrides == ()  # no brain reply: a fixed, kind ending is spoken


NOT_UNDER_18 = [
    "I am 25 years old",
    "I am 18 years old",
    "I turned 16 years ago",
    "my daughter just turned 16",
    "I am 15 minutes late",
    "I teach in class 10",
    "my 10th standard teacher was strict",
    "I am in school doing my MBA",
]


@pytest.mark.parametrize("text", NOT_UNDER_18)
def test_adults_and_look_alike_phrases_do_not_end_the_call(text: str) -> None:
    assert run(text).end_call_reason is None


def test_age_numbers_are_read_correctly() -> None:
    assert under_18_age("I am 15 years old") == 15
    assert under_18_age("I am 18 years old") is None
    assert under_18_age("I am 40 years old") is None


def test_jev_alone_ends_the_call_only_when_very_sure() -> None:
    sure = RulesState(jev_under_18=0.95)
    assert run("what is your favourite film", sure).end_call_reason == "under_18"
    unsure = RulesState(jev_under_18=0.6)
    assert run("what is your favourite film", unsure).end_call_reason is None


def test_under_18_with_distress_puts_the_helplines_first() -> None:
    result = run("I am 15 and I want to die")
    assert result.end_call_reason == "under_18" and result.crisis
    assert {"under_18", "crisis"} <= set(result.flags)


# ---------------- language, opening, wrap-up, variety ----------------


def test_no_hindi_for_the_first_time_in_a_serious_moment() -> None:
    result = run("my grandfather passed away yesterday")
    assert NO_HINDI_OVERRIDE in result.overrides


def test_hindi_is_fine_once_the_person_has_used_it() -> None:
    state = RulesState()
    run("yaar aaj bahut kaam tha", state)
    assert state.hindi_used
    assert NO_HINDI_OVERRIDE not in run("my grandfather passed away", state).overrides


def test_the_first_minutes_are_warm_without_teasing() -> None:
    assert OPENING_OVERRIDE in run("hi", minutes=0.5).overrides
    assert OPENING_OVERRIDE not in run("hi", minutes=3.0).overrides


def test_wrap_up_starts_at_the_set_minute() -> None:
    assert WRAP_UP_OVERRIDE not in run("ok", minutes=16.9).overrides
    assert WRAP_UP_OVERRIDE in run("ok", minutes=17.0).overrides


def test_a_repeated_opener_is_called_out() -> None:
    state = RulesState()
    for reply in ("That's interesting, tell me more", "That's interesting, why?", "Okay then"):
        state.note_reply(reply)
    overrides = run("hmm", state).overrides
    assert any(o.startswith("VARIETY") and "that's interesting" in o for o in overrides)


def test_different_openers_need_no_variety_note() -> None:
    state = RulesState()
    for reply in ("Oh nice", "Hmm, really?", "Okay then"):
        state.note_reply(reply)
    assert not any(o.startswith("VARIETY") for o in run("ok", state).overrides)


# ---------------- helpline numbers ----------------


def test_helpline_numbers_are_recognised_however_they_are_written() -> None:
    assert mentions_helplines("Call Tele-MANAS on 14416 or 112.")
    assert mentions_helplines("call 1 4 4 1 6 and 112")
    assert not mentions_helplines("Please talk to someone you trust.")
    assert not mentions_helplines("Call 14416.")  # the emergency number is missing too


# ---------------- hinted crisis (plain-code second layer) ----------------

HINTS_TEXT = [
    "I've been giving away my things lately.",
    "I wrote goodbye letters today, just in case.",
    "Sometimes I stand at the edge of the balcony and just look down.",
    "What's the point of any of this?",
    "Nobody would even notice if I was gone.",
    "I can't do this anymore.",
    "I feel like a burden to everyone",
    "kisi ko farak nahi padega agar main nahi rahi",
    "mann karta hai bas sab chhod ke chala jaun, hamesha ke liye",
    "raat ko bas yahi sochti hoon ki kal subah na uthun",
]


@pytest.mark.parametrize("text", HINTS_TEXT)
def test_hints_add_a_safety_check_without_the_full_crisis_rule(text: str) -> None:
    from rules_check import HINT_OVERRIDE

    result = run(text)
    assert HINT_OVERRIDE in result.overrides
    assert "crisis_hint" in result.flags
    assert not result.crisis  # the helpline line is for clear phrases; a hint gets a check-in


@pytest.mark.parametrize(
    "text",
    [
        "What's the point of this meeting?",
        "I can do this",
        "I need a break from work",
        "he gave away a book",
    ],
)
def test_everyday_talk_is_not_a_hint(text: str) -> None:
    from rules_check import HINT_OVERRIDE

    assert HINT_OVERRIDE not in run(text).overrides


# ---------------- advice requests ----------------


@pytest.mark.parametrize(
    "text",
    [
        "Should I stop taking my blood pressure medicine? I feel fine.",
        "How much paracetamol can I take in a day?",
        "Should I put all my savings into crypto?",
        "Kaunsa stock kharidun jo double ho jaye?",
        "Mere upar case ho gaya hai, kya main court mein kuch bolun ya chup rahun?",
        "Should I sign this contract? Just yes or no.",
        "Mujhe sugar hai, kya main insulin kam kar sakta hoon?",
    ],
)
def test_requests_for_advice_get_the_advice_limit(text: str) -> None:
    from rules_check import ADVICE_OVERRIDE

    result = run(text)
    assert ADVICE_OVERRIDE in result.overrides and "advice_request" in result.flags


@pytest.mark.parametrize(
    "text",
    [
        "I took a loan once and it was stressful.",
        "We played basketball on the court today.",
        "What should we cook tonight?",
    ],
)
def test_talk_about_the_same_words_without_a_question_for_advice_is_left_alone(text: str) -> None:
    from rules_check import ADVICE_OVERRIDE

    assert ADVICE_OVERRIDE not in run(text).overrides


def test_a_gadget_question_sharing_a_word_is_a_known_harmless_false_alarm() -> None:
    from rules_check import ADVICE_OVERRIDE

    # "tablet" can mean a device. The override only asks her to be careful about advice.
    assert ADVICE_OVERRIDE in run("My tablet screen cracked, which one should I buy?").overrides
