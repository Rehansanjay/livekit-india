import pytest
from livekit import api

from livekit_india.carriers import (
    BYO,
    CARRIERS,
    EXOTEL,
    LIVEKIT_INDIA_EGRESS_CIDRS,
    PLIVO,
    check_outbound_trunk,
    get_carrier,
    inbound_trunk,
    india_sip_host,
    india_sip_uri,
    outbound_trunk,
    sip_subdomain,
)


@pytest.mark.parametrize(
    "raw",
    ["sip:bwwn08a2m4o.sip.livekit.cloud", "bwwn08a2m4o.sip.livekit.cloud", "p_bwwn08a2m4o", "bwwn08a2m4o"],
)
def test_subdomain_from_any_form(raw):
    assert sip_subdomain(raw) == "bwwn08a2m4o"


def test_india_host_and_uri():
    assert india_sip_host("p_abc123") == "abc123.india.sip.livekit.cloud"
    assert india_sip_uri("abc123") == "sip:abc123.india.sip.livekit.cloud;transport=tcp"
    assert india_sip_uri("abc123", "tls").endswith(";transport=tls")


def test_bad_project_raises():
    with pytest.raises(ValueError):
        sip_subdomain("not a project!")


def test_carrier_lookup():
    assert get_carrier("EXOTEL") is EXOTEL
    assert set(CARRIERS) == {"exotel", "plivo", "byo"}
    with pytest.raises(ValueError):
        get_carrier("twilio")


def test_setup_steps_fill_in_uri_and_cidrs():
    steps = EXOTEL.setup_steps("p_abc123")
    joined = " ".join(steps)
    assert "sip:abc123.india.sip.livekit.cloud;transport=tcp" in joined
    for cidr in LIVEKIT_INDIA_EGRESS_CIDRS:
        assert cidr in joined
    assert "{" not in joined  # every placeholder was filled
    assert "<your India SIP URI>" in PLIVO.setup_steps()[1]


def test_byo_preset_is_marked_unverified():
    assert BYO.verified is False and EXOTEL.verified and PLIVO.verified


def test_outbound_trunk_is_pinned_to_india():
    t = outbound_trunk(
        "plivo", name="plivo-out", address="abc.zt.plivo.com",
        numbers=["+918000000000"], auth_username="user1", auth_password="pass!1",
    )
    assert isinstance(t, api.SIPOutboundTrunkInfo)
    assert t.destination_country == "in"
    assert t.transport == api.SIPTransport.SIP_TRANSPORT_TCP
    assert check_outbound_trunk(t) == []


def test_plivo_outbound_requires_credentials():
    with pytest.raises(ValueError):
        outbound_trunk("plivo", name="x", address="abc.zt.plivo.com", numbers=["+918000000000"])


def test_exotel_outbound_works_without_credentials():
    t = outbound_trunk("exotel", name="exo", address="gw.example:5070", numbers=["+918000000000"])
    assert t.auth_username == "" and t.destination_country == "in"


def test_check_outbound_trunk_flags_common_mistakes():
    bad = api.SIPOutboundTrunkInfo(name="bad", address="", numbers=["+14155550100"])
    fields = {p.field for p in check_outbound_trunk(bad)}
    assert fields == {"destination_country", "address", "numbers"}


def test_inbound_trunk_defaults_to_noise_cancellation():
    t = inbound_trunk(name="in", numbers=["+918000000000"])
    assert isinstance(t, api.SIPInboundTrunkInfo) and t.krisp_enabled
