import asyncio
import json
from typing import Any

import aiohttp
import pytest
from aiohttp import web

from background_decisions import (
    BackgroundDecider,
    DecisionConfig,
    apply_decision,
    build_questions,
    format_window,
    parse_decision,
)
from background_decisions.decider import LANGUAGE_NOTES
from conductor.agent import VaaniAgent, load_instructions
from conductor.skills import SKILLS
from rules_check import RulesState
from vendors.decision_model import DecisionModel, DecisionModelError

CONFIG = DecisionConfig(
    enabled=True, window_turns=4, skill_switch_threshold=0.7, heavy_threshold=0.6,
    crisis_threshold=0.5,
)


def answers(
    skill: str = "support",
    p: float = 0.9,
    heavy: float = 0.1,
    crisis: float = 0.0,
    under_18: float = 0.0,
    hinglish: str = "light",
    intensity: str = "high",
) -> dict[str, Any]:
    others = {s: (1 - p) / 4 for s in SKILLS if s != skill}
    return {
        "skill": {"type": "choice", "choice": skill, "confidence": p,
                  "probabilities": {skill: p, **others}},
        "intensity": {"type": "choice", "choice": intensity, "confidence": 0.8,
                      "probabilities": {intensity: 0.8}},
        "heavy": {"type": "noul", "noul": heavy},
        "under_18": {"type": "noul", "noul": under_18},
        "hinted_crisis": {"type": "noul", "noul": crisis},
        "hinglish": {"type": "choice", "choice": hinglish, "confidence": 0.9,
                     "probabilities": {hinglish: 0.9}},
    }


class FakeJev:
    def __init__(self, reply: dict[str, Any] | Exception, delay: float = 0.0) -> None:
        self.reply, self.delay, self.calls = reply, delay, 0

    async def ask(self, state: str, questions: dict[str, Any]) -> tuple[dict[str, Any], float]:
        self.calls += 1
        await asyncio.sleep(self.delay)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply, 12.0


def agent() -> VaaniAgent:
    return VaaniAgent(load_instructions())


HISTORY = [("user", "I failed my exam again."), ("assistant", "That sounds heavy.")]


# ---- questions and parsing ----


def test_only_complete_skills_are_offered_to_jev() -> None:
    questions = build_questions(["casual_chat", "support"])
    assert set(questions["skill"]["criteria"]) == {"casual_chat", "support"}
    assert questions["heavy"]["type"] == "noul"
    assert questions["hinglish"]["type"] == "choice"


def test_a_decision_is_read_from_jevs_typed_answers() -> None:
    d = parse_decision(answers("support", 0.9, heavy=0.8, hinglish="heavy"), 40.0)
    assert (d.skill, d.intensity, d.hinglish) == ("support", "high", "heavy")
    assert d.heavy == 0.8 and d.skill_probability == 0.9 and d.latency_ms == 40.0


def test_a_missing_answer_is_an_error_not_a_guess() -> None:
    broken = answers()
    del broken["heavy"]
    with pytest.raises(KeyError):
        parse_decision(broken)


def test_jev_reads_only_the_last_few_exchanges() -> None:
    history = [("user", f"u{i}") if i % 2 == 0 else ("assistant", f"a{i}") for i in range(20)]
    text = format_window(history, window_turns=2)
    assert text.count("\n") == 3  # 4 lines: two exchanges
    assert "u0" not in text and "a19" in text
    assert text.splitlines()[-1].startswith("Vaani: ")


# ---- how answers are used ----


def test_a_clearly_sure_new_skill_is_switched_to() -> None:
    a = agent()
    notes = apply_decision(parse_decision(answers("support", 0.9)), a, CONFIG)
    assert a.skill == "support" and "jev:skill->support" in notes
    assert "Skill: support" in a.turn.skill_note


def test_an_unsure_new_skill_is_ignored_so_skills_do_not_flip_flop() -> None:
    a = agent()
    apply_decision(parse_decision(answers("playful_banter", 0.6)), a, CONFIG)
    assert a.skill == "casual_chat"


def test_the_same_skill_only_updates_its_intensity() -> None:
    a = agent()
    apply_decision(parse_decision(answers("casual_chat", 0.9, intensity="high")), a, CONFIG)
    assert a.skill == "casual_chat" and a.intensity == "high"


def test_heavy_and_crisis_hints_feed_the_rules_check_for_the_next_turn() -> None:
    a = agent()
    apply_decision(parse_decision(answers(heavy=0.8, crisis=0.7, under_18=0.95)), a, CONFIG)
    s = a.rules_state
    assert s.jev_heavy and s.jev_crisis and s.jev_under_18 == 0.95
    apply_decision(parse_decision(answers(heavy=0.1, crisis=0.1, under_18=0.0)), a, CONFIG)
    assert not s.jev_heavy and not s.jev_crisis


def test_the_language_note_follows_the_hinglish_level() -> None:
    a = agent()
    apply_decision(parse_decision(answers(hinglish="heavy")), a, CONFIG)
    assert a.turn.session_context == LANGUAGE_NOTES["heavy"]


# ---- the background decider ----


async def test_a_decision_is_applied_in_the_background() -> None:
    a, events = agent(), []
    decider = BackgroundDecider(FakeJev(answers("support", 0.95)), CONFIG, list(SKILLS),
                                on_event=lambda k, f: events.append((k, f)))
    decider.schedule(1, HISTORY, a)
    assert a.skill == "casual_chat"  # schedule() returned at once: nothing was waited for
    await decider.wait_idle()
    assert a.skill == "support"
    assert events[0][0] == "jev" and events[0][1]["skill"] == "support"
    assert "text" not in json.dumps(events[0][1])  # numbers and labels only, never words


@pytest.mark.parametrize("failure", [DecisionModelError("down"), KeyError("heavy")])
async def test_when_jev_fails_the_current_skill_stays(failure: Exception) -> None:
    a, events = agent(), []
    decider = BackgroundDecider(FakeJev(failure), CONFIG, list(SKILLS),
                                on_event=lambda k, f: events.append(k))
    a.set_skill("serious_discussion")
    decider.schedule(1, HISTORY, a)
    await decider.wait_idle()
    assert a.skill == "serious_discussion" and events == ["jev_failed"]


async def test_a_late_older_decision_does_not_undo_a_newer_one() -> None:
    a = agent()
    late = FakeJev(answers("playful_banter", 0.95), delay=0.2)
    slow = BackgroundDecider(late, CONFIG, list(SKILLS))
    slow.schedule(1, HISTORY, a)  # turn 1 answers late
    await asyncio.sleep(0.01)
    slow._applied_turn = 2  # a newer turn has already been applied
    await slow.wait_idle()
    assert a.skill == "casual_chat"


async def test_running_the_same_turn_twice_changes_nothing_more() -> None:
    a = agent()
    decider = BackgroundDecider(FakeJev(answers("support", 0.95)), CONFIG, list(SKILLS))
    decider.schedule(3, HISTORY, a)
    await decider.wait_idle()
    before = (a.skill, a.intensity, a.turn.session_context)
    decider.schedule(3, HISTORY, a)
    await decider.wait_idle()
    assert (a.skill, a.intensity, a.turn.session_context) == before


async def test_jev_switched_off_means_nothing_is_called() -> None:
    off = DecisionConfig(False, 4, 0.7, 0.6, 0.5)
    jev = FakeJev(answers())
    decider = BackgroundDecider(jev, off, list(SKILLS))
    decider.schedule(1, HISTORY, agent())
    await decider.wait_idle()
    assert jev.calls == 0


def test_jev_state_never_touches_the_fixed_layers() -> None:
    a = agent()
    before = load_instructions()
    apply_decision(parse_decision(answers("support", 0.9, hinglish="heavy")), a, CONFIG)
    assert load_instructions() == before
    assert isinstance(a.rules_state, RulesState)


# ---- the real HTTP client, against a local fake server ----


async def test_the_client_sends_state_and_questions_and_reads_the_answers() -> None:
    seen: dict[str, Any] = {}

    async def handler(request: web.Request) -> web.Response:
        seen["body"] = await request.json()
        seen["auth"] = request.headers["Authorization"]
        reply = {"model": "jev-x", "answers": {"q": {"type": "noul", "noul": 0.9}}}
        return web.json_response(reply)

    app = web.Application()
    app.router.add_post("/v1/systemone", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]  # type: ignore[union-attr]
    model = DecisionModel("k", "jev-latest", 2.0, url=f"http://127.0.0.1:{port}/v1/systemone")
    try:
        got, ms = await model.ask("Person: hi", {"q": {"type": "noul", "instructions": "?"}})
    finally:
        await model.aclose()
        await runner.cleanup()
    assert got["q"]["noul"] == 0.9 and ms >= 0
    assert seen["body"]["state"] == "Person: hi" and seen["body"]["model"] == "jev-latest"
    assert seen["auth"] == "Bearer k"


async def test_the_client_turns_errors_and_timeouts_into_one_error() -> None:
    async def slow(request: web.Request) -> web.Response:
        await asyncio.sleep(1)
        return web.json_response({})

    async def broken(request: web.Request) -> web.Response:
        return web.json_response({"detail": "no"}, status=500)

    app = web.Application()
    app.router.add_post("/slow", slow)
    app.router.add_post("/broken", broken)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]  # type: ignore[union-attr]
    base = f"http://127.0.0.1:{port}"
    try:
        for path, timeout in (("/slow", 0.1), ("/broken", 2.0)):
            model = DecisionModel("k", "m", timeout, url=base + path)
            with pytest.raises(DecisionModelError):
                await model.ask("s", {})
            await model.aclose()
        dead = DecisionModel("k", "m", 0.5, url="http://127.0.0.1:9/x")
        with pytest.raises(DecisionModelError):
            await dead.ask("s", {})
        await dead.aclose()
    finally:
        await runner.cleanup()
    assert isinstance(aiohttp.ClientError(), Exception)
