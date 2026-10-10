from datetime import datetime, timezone

import pytest

from livekit_india.compliance import (
    IST,
    CallerIdSeries,
    CallPurpose,
    InvalidNumberError,
    caller_id_series,
    check_call,
    disclosure_line,
    next_allowed_time,
    normalize_indian_mobile,
    opening_line,
    recording_notice,
    within_calling_hours,
)

P, T, S = CallPurpose.PROMOTIONAL, CallPurpose.TRANSACTIONAL, CallPurpose.SERVICE


def ist(h, m=0, day=12):
    return datetime(2026, 10, day, h, m, tzinfo=IST)


# --- numbers -------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    ["9876543210", "+919876543210", "+91 98765 43210", "919876543210", "09876543210", "0091-98765-43210"],
)
def test_normalizes_common_mobile_formats(raw):
    assert normalize_indian_mobile(raw) == "+919876543210"


@pytest.mark.parametrize(
    "raw",
    ["5876543210", "987654321", "98765432101", "+14155550100", "04423456789", "98765abc10", ""],
)
def test_rejects_non_mobile_numbers(raw):
    with pytest.raises(InvalidNumberError):
        normalize_indian_mobile(raw)


@pytest.mark.parametrize(
    "raw,series",
    [
        ("1401234567", CallerIdSeries.PROMOTIONAL_140),
        ("+91 140 123 4567", CallerIdSeries.PROMOTIONAL_140),
        ("1600123456", CallerIdSeries.TRANSACTIONAL_1600),
        ("9876543210", CallerIdSeries.OTHER),
    ],
)
def test_caller_id_series(raw, series):
    assert caller_id_series(raw) is series


# --- calling hours ---------------------------------------------------------


@pytest.mark.parametrize(
    "h,m,ok",
    [(8, 59, False), (9, 0, True), (13, 30, True), (20, 59, True), (21, 0, False), (23, 15, False), (2, 0, False)],
)
def test_promotional_window(h, m, ok):
    assert within_calling_hours(P, ist(h, m)) is ok


@pytest.mark.parametrize("purpose", [T, S])
def test_transactional_and_service_are_not_time_restricted(purpose):
    assert within_calling_hours(purpose, ist(23, 30))


def test_window_is_evaluated_in_ist_not_utc():
    # 14:00 UTC = 19:30 IST (allowed); 16:00 UTC = 21:30 IST (blocked)
    assert within_calling_hours(P, datetime(2026, 10, 12, 14, 0, tzinfo=timezone.utc))
    assert not within_calling_hours(P, datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc))


def test_naive_datetime_is_refused():
    with pytest.raises(ValueError):
        within_calling_hours(P, datetime(2026, 10, 12, 10, 0))


def test_next_allowed_time_same_morning_and_next_day():
    assert next_allowed_time(P, ist(7, 10)) == ist(9, 0)
    assert next_allowed_time(P, ist(22, 0)) == ist(9, 0, day=13)
    assert next_allowed_time(P, ist(10, 0)) == ist(10, 0)


# --- check_call ------------------------------------------------------------


def test_promotional_call_with_consent_in_hours_is_allowed():
    d = check_call("9876543210", P, has_consent=True, caller_id="1401234567", now=ist(11))
    assert d and d.destination == "+919876543210" and not d.reasons and not d.warnings


def test_promotional_after_hours_is_blocked_with_retry_time():
    d = check_call("9876543210", P, has_consent=True, now=ist(21, 30))
    assert not d
    assert d.retry_at == ist(9, 0, day=13)


def test_promotional_without_consent_requires_dnd_check():
    d = check_call("9876543210", P, now=ist(11))
    assert not d and "DND" in d.reasons[0]


def test_dnd_listed_number_is_blocked_and_clean_number_allowed():
    on_dnd = {"+919876543210"}
    assert not check_call("9876543210", P, dnd_check=on_dnd.__contains__, now=ist(11))
    assert check_call("9123456780", P, dnd_check=on_dnd.__contains__, now=ist(11))


def test_invalid_destination_is_blocked():
    d = check_call("044 2345 6789", T)
    assert not d and d.destination is None


def test_caller_id_series_warnings():
    promo_wrong = check_call("9876543210", P, has_consent=True, caller_id="9000000000", now=ist(11))
    assert promo_wrong and "140-series" in promo_wrong.warnings[0]
    service_wrong = check_call("9876543210", S, caller_id="1401234567", now=ist(23))
    assert service_wrong and "1600-series" in service_wrong.warnings[0]


def test_transactional_late_night_is_allowed():
    assert check_call("9876543210", T, caller_id="1600123456", now=ist(23, 45))


# --- opening lines ---------------------------------------------------------


@pytest.mark.parametrize("lang", ["en", "hi", "ta", "ta-IN", "hi_IN"])
def test_disclosure_contains_business_name(lang):
    assert "Acme Dental" in disclosure_line("Acme Dental", lang)


def test_opening_line_with_and_without_recording():
    assert opening_line("Acme", "en") == (
        "Hello, this is an AI assistant calling on behalf of Acme. "
        "This call may be recorded for quality and training."
    )
    assert opening_line("Acme", "ta", recorded=False) == disclosure_line("Acme", "ta")
    assert recording_notice("hi")


def test_unsupported_language_raises():
    with pytest.raises(ValueError):
        disclosure_line("Acme", "fr")


def test_readme_tamil_example_matches_real_output():
    readme = (__import__("pathlib").Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")
    assert opening_line("Acme Dental", "ta") in readme
