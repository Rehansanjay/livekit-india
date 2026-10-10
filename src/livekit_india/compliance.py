"""Pre-call compliance checks for voice agents that call Indian phone numbers.

This module encodes the rules most often missed when an AI voice agent starts
making outbound calls in India. It is a safety net, not legal advice. Rules
change; confirm them with your DLT operator and telephony provider.

What is checked, and where each rule comes from:

* Calling hours: promotional calls only between 09:00 and 21:00 IST.
  TCCCPR 2018, as summarised by Exotel's developer docs
  (https://developer.exotel.com/docs/faqs/tcccpr-2018).
* Caller ID series: promotional voice calls must come from the 140 series;
  the 1600 series is for transactional/service calls (DoT allotment, 2024).
* Destination: Indian mobile numbers are 10 digits starting with 6, 7, 8 or 9.
* DND / NCPR: promotional calls need a fresh DND scrub. India has no public
  API for the registry, so this module takes your own checker as a callable.
* AI disclosure: a 2026 *draft* TRAI amendment proposes announcing at the start
  of every AI call that an AI is calling on behalf of the business. Not yet in
  force, but cheap to do now; ``disclosure_line()`` produces it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Callable, Optional
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

#: Window in which promotional calls may be placed (IST, end exclusive).
PROMOTIONAL_WINDOW: tuple[time, time] = (time(9, 0), time(21, 0))


class CallPurpose(str, Enum):
    """Why the call is being made. This decides which rules apply."""

    PROMOTIONAL = "promotional"  # sales, offers, cold or warm outreach
    TRANSACTIONAL = "transactional"  # OTPs, order/delivery updates, alerts
    SERVICE = "service"  # reminders and updates to existing customers


class InvalidNumberError(ValueError):
    """Raised when a string cannot be read as an Indian phone number."""


# --------------------------------------------------------------------------
# Phone numbers
# --------------------------------------------------------------------------

_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")


def _digits(number: str) -> str:
    return re.sub(r"[\s\-().]", "", number.strip())


def national_number(number: str) -> str:
    """Strip +91 / 91 / 0 prefixes and return the national number.

    >>> national_number("+91 98765 43210")
    '9876543210'
    """
    d = _digits(number)
    if d.startswith("+"):
        if not d.startswith("+91"):
            raise InvalidNumberError(f"{number!r} is not an Indian (+91) number")
        d = d[3:]
    elif d.startswith("0091"):
        d = d[4:]
    elif len(d) == 12 and d.startswith("91"):
        d = d[2:]
    elif len(d) == 11 and d.startswith("0"):
        d = d[1:]
    if not d.isdigit():
        raise InvalidNumberError(f"{number!r} contains characters that are not digits")
    return d


def normalize_indian_mobile(number: str) -> str:
    """Return an Indian mobile number in E.164 (``+91XXXXXXXXXX``).

    Raises :class:`InvalidNumberError` for anything that is not a 10-digit
    mobile number starting with 6-9 (landlines and short codes included).
    """
    d = national_number(number)
    if not _MOBILE_RE.match(d):
        raise InvalidNumberError(
            f"{number!r} is not an Indian mobile number "
            "(expected 10 digits starting with 6, 7, 8 or 9)"
        )
    return f"+91{d}"


class CallerIdSeries(str, Enum):
    PROMOTIONAL_140 = "140"
    TRANSACTIONAL_1600 = "1600"
    OTHER = "other"


def caller_id_series(number: str) -> CallerIdSeries:
    """Classify a caller ID by its TRAI/DoT number series."""
    d = national_number(number)
    if d.startswith("1600"):
        return CallerIdSeries.TRANSACTIONAL_1600
    if d.startswith("140"):
        return CallerIdSeries.PROMOTIONAL_140
    return CallerIdSeries.OTHER


# --------------------------------------------------------------------------
# Calling hours
# --------------------------------------------------------------------------


def _as_ist(now: Optional[datetime]) -> datetime:
    if now is None:
        return datetime.now(IST)
    if now.tzinfo is None:
        raise ValueError("pass a timezone-aware datetime (naive times are ambiguous)")
    return now.astimezone(IST)


def within_calling_hours(
    purpose: CallPurpose,
    now: Optional[datetime] = None,
    window: tuple[time, time] = PROMOTIONAL_WINDOW,
) -> bool:
    """True if a call for ``purpose`` may be placed at ``now``.

    Transactional and service calls are not time-restricted.
    """
    if purpose is not CallPurpose.PROMOTIONAL:
        return True
    t = _as_ist(now).time()
    start, end = window
    return start <= t < end


def next_allowed_time(
    purpose: CallPurpose,
    now: Optional[datetime] = None,
    window: tuple[time, time] = PROMOTIONAL_WINDOW,
) -> datetime:
    """The earliest moment at or after ``now`` when the call may be placed (IST)."""
    current = _as_ist(now)
    if within_calling_hours(purpose, current, window):
        return current
    start, _ = window
    candidate = current.replace(hour=start.hour, minute=start.minute, second=0, microsecond=0)
    if candidate <= current:
        candidate += timedelta(days=1)
    return candidate


# --------------------------------------------------------------------------
# Pre-call check
# --------------------------------------------------------------------------

#: Your DND/NCPR lookup. Return True if the number must NOT receive this call.
DndChecker = Callable[[str], bool]


@dataclass
class CallDecision:
    allowed: bool
    destination: Optional[str] = None
    reasons: list[str] = field(default_factory=list)  # why it was blocked
    warnings: list[str] = field(default_factory=list)  # allowed, but fix these
    retry_at: Optional[datetime] = None

    def __bool__(self) -> bool:
        return self.allowed


def check_call(
    to_number: str,
    purpose: CallPurpose,
    *,
    caller_id: Optional[str] = None,
    has_consent: bool = False,
    dnd_check: Optional[DndChecker] = None,
    now: Optional[datetime] = None,
) -> CallDecision:
    """Decide whether an outbound call may be placed right now.

    Blocks the call (``allowed=False``) for problems that risk penalties or
    blocked numbers, and adds ``warnings`` for things you should fix.

    Args:
        to_number: who you are calling.
        purpose: promotional, transactional or service.
        caller_id: the number you are calling from, to check its series.
        has_consent: whether you hold recorded, purpose-specific consent.
        dnd_check: your DND/NCPR lookup. Required to clear a promotional call
            without consent; without it such calls are blocked.
        now: override the current time (timezone-aware), mainly for tests.
    """
    decision = CallDecision(allowed=True)

    try:
        decision.destination = normalize_indian_mobile(to_number)
    except InvalidNumberError as e:
        decision.allowed = False
        decision.reasons.append(str(e))
        return decision

    if not within_calling_hours(purpose, now):
        decision.allowed = False
        decision.retry_at = next_allowed_time(purpose, now)
        decision.reasons.append(
            "promotional calls are only allowed 09:00-21:00 IST; "
            f"next window opens {decision.retry_at:%Y-%m-%d %H:%M} IST"
        )

    if purpose is CallPurpose.PROMOTIONAL and not has_consent:
        if dnd_check is None:
            decision.allowed = False
            decision.reasons.append(
                "promotional call without recorded consent needs a DND scrub; "
                "pass dnd_check=..."
            )
        elif dnd_check(decision.destination):
            decision.allowed = False
            decision.reasons.append("number is on the DND / NCPR registry")

    if caller_id is not None:
        try:
            series = caller_id_series(caller_id)
        except InvalidNumberError as e:
            decision.warnings.append(f"caller ID: {e}")
        else:
            if purpose is CallPurpose.PROMOTIONAL and series is not CallerIdSeries.PROMOTIONAL_140:
                decision.warnings.append(
                    "promotional voice calls should originate from a 140-series number"
                )
            if purpose is not CallPurpose.PROMOTIONAL and series is CallerIdSeries.PROMOTIONAL_140:
                decision.warnings.append(
                    "140-series numbers mark a call as promotional; use a 1600-series "
                    "number for transactional or service calls"
                )

    return decision


# --------------------------------------------------------------------------
# What the agent says first
# --------------------------------------------------------------------------

_DISCLOSURE = {
    "en": "Hello, this is an AI assistant calling on behalf of {business}.",
    "hi": "नमस्ते, यह {business} की ओर से एक AI सहायक की कॉल है।",
    "ta": "வணக்கம், இது {business} சார்பாக அழைக்கும் ஒரு AI உதவியாளர்.",
}

_RECORDING = {
    "en": "This call may be recorded for quality and training.",
    "hi": "गुणवत्ता और प्रशिक्षण के लिए यह कॉल रिकॉर्ड की जा सकती है।",
    "ta": "தரம் மற்றும் பயிற்சிக்காக இந்த அழைப்பு பதிவு செய்யப்படலாம்.",
}

SUPPORTED_LANGUAGES = tuple(_DISCLOSURE)


def _lang(language: str) -> str:
    code = language.lower().replace("_", "-").split("-")[0]
    if code not in _DISCLOSURE:
        raise ValueError(f"no disclosure text for {language!r}; supported: {SUPPORTED_LANGUAGES}")
    return code


def disclosure_line(business: str, language: str = "en") -> str:
    """The AI disclosure to say at the start of a call."""
    return _DISCLOSURE[_lang(language)].format(business=business)


def recording_notice(language: str = "en") -> str:
    """The recording notice, for calls you record."""
    return _RECORDING[_lang(language)]


def opening_line(business: str, language: str = "en", *, recorded: bool = True) -> str:
    """Disclosure plus (optionally) the recording notice, ready for ``session.say()``."""
    line = disclosure_line(business, language)
    return f"{line} {recording_notice(language)}" if recorded else line
