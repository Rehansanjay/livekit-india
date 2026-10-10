"""Production helpers for LiveKit voice agents that call Indian phone numbers."""

from .carriers import (
    CARRIERS,
    LIVEKIT_INDIA_EGRESS_CIDRS,
    check_outbound_trunk,
    get_carrier,
    inbound_trunk,
    india_sip_host,
    india_sip_uri,
    outbound_trunk,
)
from .compliance import (
    CallDecision,
    CallPurpose,
    InvalidNumberError,
    check_call,
    disclosure_line,
    normalize_indian_mobile,
    opening_line,
    recording_notice,
)
from .turns import turn_detector, turn_handling, vad_options

__version__ = "0.1.0"

__all__ = [
    "CARRIERS",
    "LIVEKIT_INDIA_EGRESS_CIDRS",
    "CallDecision",
    "CallPurpose",
    "InvalidNumberError",
    "check_call",
    "check_outbound_trunk",
    "disclosure_line",
    "get_carrier",
    "inbound_trunk",
    "india_sip_host",
    "india_sip_uri",
    "normalize_indian_mobile",
    "opening_line",
    "outbound_trunk",
    "recording_notice",
    "turn_detector",
    "turn_handling",
    "vad_options",
]
