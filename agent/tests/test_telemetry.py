import json
from pathlib import Path

from settings import REPO_ROOT, Settings
from settings.settings import parse_env_file
from telemetry import FORMAT_VERSION, CostMeter, Prices, TelemetryWriter, TurnRecorder


class Clock:
    now = 50.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def run_turn(rec: TurnRecorder, clock: Clock) -> None:
    rec.speech_ended()
    clock.advance(0.4)
    rec.llm_requested()
    clock.advance(0.3)
    rec.first_word()
    clock.advance(0.25)
    rec.first_audio()


def test_a_turn_is_split_into_stages() -> None:
    clock = Clock()
    rec = TurnRecorder(now=clock)
    run_turn(rec, clock)
    record = rec.finish()
    assert record is not None
    assert record["kind"] == "user"
    assert record["stages_ms"] == {
        "turn_detection_ms": 400.0,
        "first_word_ms": 300.0,
        "first_audio_ms": 250.0,
        "reply_total_ms": 950.0,
    }


def test_the_greeting_has_no_turn_detection_stage() -> None:
    clock = Clock()
    rec = TurnRecorder(now=clock)
    rec.llm_requested()
    clock.advance(0.5)
    rec.first_word()
    clock.advance(0.2)
    rec.first_audio()
    record = rec.finish()
    assert record is not None and record["kind"] == "greeting"
    assert "turn_detection_ms" not in record["stages_ms"]
    assert record["stages_ms"]["reply_total_ms"] == 700.0


def test_a_turn_with_no_sound_reports_nothing() -> None:
    rec = TurnRecorder(now=Clock())
    rec.speech_ended()
    assert rec.finish() is None


def test_notes_and_vendor_numbers_are_kept_once() -> None:
    clock = Clock()
    rec = TurnRecorder(now=clock)
    rec.speech_ended()
    rec.note("m1_failed")
    rec.note("m1_failed")
    rec.set_brain("m2")
    rec.add_livekit_ms("llm_ttft", 812.345)
    rec.llm_requested()
    rec.first_word()
    rec.first_audio()
    record = rec.finish()
    assert record is not None
    assert record["notes"] == ["m1_failed"] and record["brain"] == "m2"
    assert record["livekit_ms"] == {"llm_ttft": 812.3}


def prices() -> Prices:
    values = parse_env_file(REPO_ROOT / ".env.example")
    return Prices.from_settings(Settings(values=values))


def test_cost_is_counted_per_vendor_in_rupees() -> None:
    meter = CostMeter(prices(), {"m1": "big", "m2": "mid", "s1": "small"})
    meter.add_llm("big", 1_000_000, 1_000_000)
    meter.add_stt(3600)
    meter.add_tts("Sarvam", 10_000, 5.0)
    units, cost = meter.take()
    assert cost["m1"] == round(29.28 + 73.2, 4)
    assert cost["speech_to_text"] == 30.0
    assert cost["voice"] == 30.0  # 10,000 Bulbul characters
    assert cost["total"] == round(29.28 + 73.2 + 30.0 + 30.0, 4)
    assert units.to_dict()["bulbul_chars"] == 10_000


def test_the_meter_reports_what_is_new_each_time() -> None:
    meter = CostMeter(prices(), {"m1": "big"})
    meter.add_llm("big", 100, 50)
    meter.take()
    units, cost = meter.take()
    assert cost["total"] == 0.0 and units.llm_in["m1"] == 0
    assert meter.total.llm_in["m1"] == 100  # the session total keeps counting


def test_an_unknown_model_is_not_priced() -> None:
    meter = CostMeter(prices(), {"m1": "big"})
    assert meter.add_llm("mystery", 10, 10) is None


def test_records_carry_a_version_and_the_session_and_no_words(tmp_path: Path) -> None:
    writer = TelemetryWriter(tmp_path, "room/one two")
    writer.write("turn", stages_ms={"reply_total_ms": 900.0})
    writer.write("turn", stages_ms={"reply_total_ms": 1000.0})
    lines = [json.loads(x) for x in writer.path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    assert all(x["format_version"] == FORMAT_VERSION for x in lines)
    assert all(x["session_id"] == "room/one two" for x in lines)
    assert "room_one_two" in writer.path.name  # safe file name


def test_a_turn_record_can_have_its_own_kind_field(tmp_path: Path) -> None:
    writer = TelemetryWriter(tmp_path, "s1")
    writer.write("turn", kind="user", turn=1)  # "kind" inside the record must not clash
    line = json.loads(writer.path.read_text(encoding="utf-8").splitlines()[0])
    assert line["type"] == "turn" and line["kind"] == "user"
