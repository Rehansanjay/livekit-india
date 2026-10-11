"""LiveKit SIP trunk settings for Indian telephony providers.

Indian calls have two rules that break the default LiveKit setup:

1. Media and signalling must stay in India (DoT/TRAI). Point inbound trunks at
   LiveKit's India endpoint (``<subdomain>.india.sip.livekit.cloud``) and set
   ``destination_country="in"`` on outbound trunks.
   https://docs.livekit.io/telephony/features/region-pinning/
2. Indian carriers usually only accept SIP from allow-listed IPs. LiveKit's
   India egress ranges must be on the carrier's allow list, or outbound calls
   time out before any SIP response. The fix is on the carrier side.
   https://livekit.com/field-guides/guide/support-india-data-sovereignty

Each preset carries a setup checklist with these steps for one provider.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Sequence

#: LiveKit's India egress ranges. Confirm with LiveKit support before sending
#: them to a carrier; allocations can change.
LIVEKIT_INDIA_EGRESS_CIDRS: tuple[str, ...] = ("143.223.88.0/21", "161.115.160.0/19")

INDIA_REGION = "india"
DESTINATION_COUNTRY = "in"


def sip_subdomain(project: str) -> str:
    """Pull the SIP subdomain out of a SIP URI, hostname or project ID.

    Accepts ``sip:abc123.sip.livekit.cloud``, ``abc123.sip.livekit.cloud``,
    ``p_abc123`` or ``abc123``.
    """
    s = project.strip()
    s = re.sub(r"^sips?:", "", s)
    s = s.split(";")[0].split(":")[0]
    host = s.split(".")[0]
    if host.startswith("p_"):
        host = host[2:]
    if not re.fullmatch(r"[a-z0-9]+", host):
        raise ValueError(f"cannot find a LiveKit SIP subdomain in {project!r}")
    return host


def india_sip_host(project: str) -> str:
    """LiveKit's India-pinned SIP host for a project."""
    return f"{sip_subdomain(project)}.{INDIA_REGION}.sip.livekit.cloud"


def india_sip_uri(project: str, transport: str = "tcp") -> str:
    """The India-pinned SIP URI to give your carrier for inbound calls."""
    return f"sip:{india_sip_host(project)};transport={transport}"


@dataclass(frozen=True)
class CarrierPreset:
    key: str
    name: str
    transport: str  # "tcp" or "tls"
    outbound_auth: str  # "credentials" or "ip_allowlist"
    checklist: tuple[str, ...]
    gotchas: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    verified: bool = True  # False: generic guidance, check with the carrier

    def setup_steps(self, project: Optional[str] = None) -> list[str]:
        """The checklist with your project's India SIP URI filled in."""
        uri = india_sip_uri(project, self.transport) if project else "<your India SIP URI>"
        cidrs = ", ".join(LIVEKIT_INDIA_EGRESS_CIDRS)
        return [step.format(uri=uri, cidrs=cidrs) for step in self.checklist]


EXOTEL = CarrierPreset(
    key="exotel",
    name="Exotel (vSIP)",
    transport="tcp",
    outbound_auth="ip_allowlist",
    checklist=(
        "Get a contracted, KYC-completed Exotel account; SIP trunking needs both.",
        "Email hello@exotel.com with your LiveKit SIP URI ({uri}) and your Exophone; "
        "Exotel configures the inbound mapping.",
        "In LiveKit: create an inbound trunk for the Exophone (exactly as Exotel sends it, +91...) "
        "and a dispatch rule to your agent.",
        "Outbound: ask Exotel whether SIP outbound (vSIP) is enabled on your account. Some accounts "
        "only support outbound through Exotel's call API.",
        "If SIP outbound is enabled: ask Exotel to allow-list LiveKit's India egress ranges ({cidrs}) "
        "and create a LiveKit outbound trunk to Exotel's SIP gateway with destination_country='in'.",
    ),
    gotchas=(
        "Exotel asks for an FQDN and port: give the India host without 'sip:' and TCP port 5060.",
        "SIP outbound is not enabled on every Exotel account; check before building on it.",
        "Exotel only accepts outbound SIP from allow-listed static IPs.",
        "Media and signalling cannot leave India on SIP trunks.",
        "Exotel's WebSocket Voicebot applet is an alternative that skips SIP onboarding.",
    ),
    sources=(
        "https://support.exotel.com/support/solutions/articles/3000134145",
        "https://developer.exotel.com/docs/sip-trunking/flow-api-configuration",
        "https://github.com/livekit/sip/issues/428",
    ),
)

PLIVO = CarrierPreset(
    key="plivo",
    name="Plivo SIP trunking",
    transport="tcp",
    outbound_auth="credentials",
    checklist=(
        "Create the Plivo organization with data region = India. It cannot be changed later.",
        "Inbound: create an origination URI {uri} and an inbound trunk using it; link your number.",
        "Outbound: create a Plivo credential and an outbound trunk; copy its termination domain "
        "(<trunk_id>.zt.plivo.com).",
        "In LiveKit: create an outbound trunk to that domain with the same username/password "
        "and destination_country='in'.",
        "In LiveKit: create an inbound trunk and a dispatch rule to your agent.",
    ),
    gotchas=(
        "Hangup code 4590 means media left India: the LiveKit endpoint is not India-pinned.",
        "If the Plivo trunk is 'secure', enable TLS and media encryption in LiveKit too.",
        "Mixing PSTN and WebRTC legs in one conference triggers hangup 2070 (media anchoring).",
    ),
    sources=(
        "https://www.plivo.com/docs/voice-agents/sip-trunking/deploy/calling-in-india",
        "https://www.plivo.com/docs/voice-agents/sip-trunking/integration-guides/livekit",
    ),
)

BYO = CarrierPreset(
    key="byo",
    name="Other Indian carrier (Vobiz, Tata Smartflo, Airtel, ...)",
    transport="tcp",
    outbound_auth="ip_allowlist",
    checklist=(
        "Give the carrier your India-pinned SIP URI for inbound: {uri}.",
        "Ask the carrier to allow-list LiveKit's India egress ranges for outbound: {cidrs}.",
        "Confirm the carrier's termination host, port and transport (many use non-standard ports).",
        "In LiveKit: create the outbound trunk with destination_country='in' and the "
        "carrier's port in the address.",
        "Place a test call; if it times out with no SIP response, the allow-list is not in place.",
    ),
    gotchas=(
        "A raw TCP connect timeout on outbound almost always means the carrier's SBC is "
        "dropping LiveKit's IPs.",
        "You cannot pin a single LiveKit egress IP; if the carrier only allows one, put your "
        "own SBC in front.",
    ),
    sources=(
        "https://community.livekit.io/t/1887",
        "https://livekit.com/field-guides/guide/support-india-data-sovereignty",
    ),
    verified=False,
)

CARRIERS: dict[str, CarrierPreset] = {c.key: c for c in (EXOTEL, PLIVO, BYO)}


def get_carrier(key: str) -> CarrierPreset:
    try:
        return CARRIERS[key.lower()]
    except KeyError:
        raise ValueError(f"unknown carrier {key!r}; choose from {sorted(CARRIERS)}") from None


# --------------------------------------------------------------------------
# LiveKit trunk objects
# --------------------------------------------------------------------------


@dataclass
class TrunkProblem:
    field: str
    message: str


def _transport_enum(transport: str):
    from livekit import api

    return {
        "tcp": api.SIPTransport.SIP_TRANSPORT_TCP,
        "tls": api.SIPTransport.SIP_TRANSPORT_TLS,
        "udp": api.SIPTransport.SIP_TRANSPORT_UDP,
    }[transport]


def outbound_trunk(
    carrier: str | CarrierPreset,
    *,
    name: str,
    address: str,
    numbers: Sequence[str],
    auth_username: str = "",
    auth_password: str = "",
):
    """A LiveKit ``SIPOutboundTrunkInfo`` pinned to India for this carrier.

    Pass it to ``lkapi.sip.create_outbound_trunk(api.CreateSIPOutboundTrunkRequest(trunk=...))``.
    """
    from livekit import api

    preset = carrier if isinstance(carrier, CarrierPreset) else get_carrier(carrier)
    if preset.outbound_auth == "credentials" and not (auth_username and auth_password):
        raise ValueError(f"{preset.name} outbound trunks need auth_username and auth_password")
    return api.SIPOutboundTrunkInfo(
        name=name,
        address=address,
        numbers=list(numbers),
        auth_username=auth_username,
        auth_password=auth_password,
        destination_country=DESTINATION_COUNTRY,
        transport=_transport_enum(preset.transport),
    )


def inbound_trunk(
    *,
    name: str,
    numbers: Sequence[str],
    allowed_addresses: Sequence[str] = (),
    krisp_enabled: bool = True,
):
    """A LiveKit ``SIPInboundTrunkInfo`` for Indian numbers.

    Krisp noise cancellation is on by default: Indian callers are often on
    noisy mobile lines, and background noise is a common cause of false turns.
    """
    from livekit import api

    return api.SIPInboundTrunkInfo(
        name=name,
        numbers=list(numbers),
        allowed_addresses=list(allowed_addresses),
        krisp_enabled=krisp_enabled,
    )


def check_outbound_trunk(trunk) -> list[TrunkProblem]:
    """Find settings in an existing outbound trunk that break Indian calls."""
    problems: list[TrunkProblem] = []
    if (trunk.destination_country or "").lower() != DESTINATION_COUNTRY:
        problems.append(
            TrunkProblem(
                "destination_country",
                "not set to 'in': calls may route outside India and be rejected",
            )
        )
    if not trunk.address:
        problems.append(TrunkProblem("address", "missing the carrier's termination host"))
    for n in trunk.numbers:
        if not n.startswith("+91") and not n.startswith("91"):
            problems.append(TrunkProblem("numbers", f"{n} is not an Indian number"))
    return problems
