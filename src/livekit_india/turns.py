"""Turn-taking defaults for Indian-language voice agents on LiveKit Agents.

Deciding when the caller has finished speaking is the most-felt quality
problem on Indian phone calls:

* Tamil: LiveKit's multilingual turn detector does not cover Tamil, so agents
  fall back to plain silence timing. The open TamilEOT model
  (``smart-turn-livekit``, trained on real Tamil phone calls) fills this gap.
  It is only consulted when the reported language is one it claims, and
  code-mixed Tamil is often reported as ``en-IN``, which silently switches it
  off. We claim ``("ta", "en")`` so it stays on for Tanglish.
* Hindi and English: LiveKit's ``MultilingualModel`` covers both.
* Short-answer flows (yes/no, slot picking): short replies often score below
  the threshold and wait the full ``max_delay``. ``short_answers=True`` caps
  that wait. See livekit/agents#6415.

Usage, inside your agent entrypoint (LiveKit's model needs a running job)::

    from livekit_india.turns import turn_handling, vad_options
    session = AgentSession(
        vad=silero.VAD.load(**vad_options("ta")),
        turn_handling=turn_handling("ta", short_answers=True),
        ...
    )
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("livekit_india")

#: Languages where we use LiveKit's MultilingualModel.
MULTILINGUAL_MODEL_LANGS = ("en", "hi")

DEFAULT_ENDPOINTING = {"min_delay": 0.5, "max_delay": 2.5}
SHORT_ANSWER_ENDPOINTING = {"min_delay": 0.3, "max_delay": 1.2}

#: smart-turn needs a VAD silence of at least 0.25 s before LiveKit asks it.
SMART_TURN_MIN_SILENCE = 0.25


def _base_lang(language: str) -> str:
    return language.lower().replace("_", "-").split("-")[0]


def _tamil_detector(model: str):
    try:
        from smart_turn_livekit import SmartTurnDetector
    except ImportError:
        logger.warning(
            "smart-turn-livekit is not installed; Tamil falls back to VAD timing. "
            "pip install 'livekit-india[tamil]'"
        )
        return "vad"
    return SmartTurnDetector(model=model, languages=("ta", "en"))


def _multilingual_model():
    try:
        from livekit.plugins.turn_detector.multilingual import MultilingualModel
    except ImportError:
        logger.warning(
            "livekit-plugins-turn-detector is not installed; falling back to VAD timing. "
            "pip install 'livekit-agents[turn-detector]'"
        )
        return "vad"
    return MultilingualModel()


def turn_detector(language: str, *, tamil_model: str = "smart-turn-tamil-tiny") -> Any:
    """The best available turn detector for ``language``, or ``"vad"``."""
    lang = _base_lang(language)
    if lang == "ta":
        return _tamil_detector(tamil_model)
    if lang in MULTILINGUAL_MODEL_LANGS:
        return _multilingual_model()
    logger.info("no tested turn model for %r; using VAD timing", language)
    return "vad"


def turn_handling(
    language: str,
    *,
    short_answers: bool = False,
    tamil_model: str = "smart-turn-tamil-tiny",
) -> dict:
    """``turn_handling`` options for ``AgentSession`` or an ``Agent``.

    Args:
        language: the call's language, e.g. ``"ta"``, ``"hi-IN"``, ``"en"``.
        short_answers: use for yes/no or slot-picking phases; caps the wait
            after a low-confidence turn at 1.2 s instead of 2.5 s.
        tamil_model: ``"smart-turn-tamil-tiny"`` (83 ms) or
            ``"smart-turn-tamil-base"`` (+2.4 accuracy points, 143 ms).
    """
    endpointing = SHORT_ANSWER_ENDPOINTING if short_answers else DEFAULT_ENDPOINTING
    return {
        "turn_detection": turn_detector(language, tamil_model=tamil_model),
        "endpointing": dict(endpointing),
    }


def vad_options(language: str) -> dict:
    """Keyword arguments for ``silero.VAD.load()`` that suit ``language``."""
    if _base_lang(language) == "ta":
        return {"min_silence_duration": SMART_TURN_MIN_SILENCE}
    return {}
