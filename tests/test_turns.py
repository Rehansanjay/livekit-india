import sys
import types

import pytest

from livekit_india import turns


class _FakeSmartTurn:
    """Stands in for smart-turn's ONNX weights so tests need no download."""

    def __init__(self, *a, **k):
        self.threshold = 0.5

    def probability(self, audio, sr=16000):
        return 0.9


@pytest.fixture
def fake_weights(monkeypatch):
    stl = pytest.importorskip("smart_turn_livekit.livekit")
    monkeypatch.setattr(stl, "SmartTurn", _FakeSmartTurn)


class _FakeMultilingual:
    model = "multilingual"
    provider = "livekit"


@pytest.fixture
def fake_multilingual(monkeypatch):
    mod = types.ModuleType("livekit.plugins.turn_detector.multilingual")
    mod.MultilingualModel = _FakeMultilingual
    monkeypatch.setitem(sys.modules, "livekit.plugins.turn_detector.multilingual", mod)


async def test_tamil_uses_smart_turn_and_stays_on_for_tanglish(fake_weights):
    det = turns.turn_detector("ta-IN")
    assert type(det).__name__ == "SmartTurnDetector"
    stream = det.stream()
    # Tanglish is often reported as en-IN; the detector must still run.
    assert await stream.supports_language("ta-IN")
    assert await stream.supports_language("en-IN")
    await det.aclose()


def test_tamil_falls_back_to_vad_without_the_package(monkeypatch):
    monkeypatch.setitem(sys.modules, "smart_turn_livekit", None)
    assert turns.turn_detector("ta") == "vad"


@pytest.mark.parametrize("lang", ["hi", "hi-IN", "en", "en_IN"])
def test_hindi_and_english_use_multilingual_model(fake_multilingual, lang):
    assert isinstance(turns.turn_detector(lang), _FakeMultilingual)


@pytest.mark.parametrize("lang", ["te", "kn-IN", "ml"])
def test_untested_languages_use_vad(lang):
    assert turns.turn_detector(lang) == "vad"


def test_short_answers_lower_the_max_wait(fake_multilingual):
    normal = turns.turn_handling("hi")
    short = turns.turn_handling("hi", short_answers=True)
    assert normal["endpointing"]["max_delay"] == 2.5
    assert short["endpointing"]["max_delay"] == 1.2
    # returned dicts are copies, so callers can tweak them safely
    short["endpointing"]["max_delay"] = 9
    assert turns.SHORT_ANSWER_ENDPOINTING["max_delay"] == 1.2


def test_vad_options():
    assert turns.vad_options("ta") == {"min_silence_duration": 0.25}
    assert turns.vad_options("hi") == {}


async def test_agent_session_accepts_the_options(fake_weights):
    from livekit.agents import Agent, AgentSession

    opts = turns.turn_handling("ta", short_answers=True)
    AgentSession(turn_handling=opts)
    Agent(instructions="test", turn_handling=turns.turn_handling("ta"))
