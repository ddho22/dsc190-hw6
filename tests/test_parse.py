"""Tests for nldate.parse()."""

from datetime import date

import pytest

from nldate import parse

# Reference date used across tests so results are deterministic.
TODAY = date(2025, 6, 15)  # Sunday


# ---------------------------------------------------------------------------
# Absolute dates
# ---------------------------------------------------------------------------


def test_iso_format() -> None:
    assert parse("2025-12-01", today=TODAY) == date(2025, 12, 1)


def test_month_day_year_words() -> None:
    assert parse("December 1st, 2025", today=TODAY) == date(2025, 12, 1)


def test_month_day_year_no_comma() -> None:
    assert parse("March 20 2026", today=TODAY) == date(2026, 3, 20)


def test_day_month_year() -> None:
    assert parse("1 January 2026", today=TODAY) == date(2026, 1, 1)


def test_slash_date() -> None:
    assert parse("12/25/2025", today=TODAY) == date(2025, 12, 25)


def test_month_only_defaults_to_day_1() -> None:
    assert parse("August 2026", today=TODAY) == date(2026, 8, 1)


def test_month_day_no_year_assumes_current_year() -> None:
    assert parse("July 4", today=TODAY) == date(2025, 7, 4)


# ---------------------------------------------------------------------------
# Named anchors
# ---------------------------------------------------------------------------


def test_today() -> None:
    assert parse("today", today=TODAY) == TODAY


def test_tomorrow() -> None:
    assert parse("tomorrow", today=TODAY) == date(2025, 6, 16)


def test_yesterday() -> None:
    assert parse("yesterday", today=TODAY) == date(2025, 6, 14)


# ---------------------------------------------------------------------------
# Relative — simple N units
# ---------------------------------------------------------------------------


def test_in_n_days() -> None:
    assert parse("in 3 days", today=TODAY) == date(2025, 6, 18)


def test_in_one_week() -> None:
    assert parse("in 1 week", today=TODAY) == date(2025, 6, 22)


def test_in_word_number_days() -> None:
    assert parse("in five days", today=TODAY) == date(2025, 6, 20)


def test_n_days_ago() -> None:
    assert parse("3 days ago", today=TODAY) == date(2025, 6, 12)


def test_n_weeks_ago() -> None:
    assert parse("2 weeks ago", today=TODAY) == date(2025, 6, 1)


def test_from_now() -> None:
    assert parse("10 days from now", today=TODAY) == date(2025, 6, 25)


def test_from_today() -> None:
    assert parse("10 days from today", today=TODAY) == date(2025, 6, 25)


def test_later() -> None:
    assert parse("7 days later", today=TODAY) == date(2025, 6, 22)


# ---------------------------------------------------------------------------
# Relative — months and years
# ---------------------------------------------------------------------------


def test_in_n_months() -> None:
    assert parse("in 2 months", today=TODAY) == date(2025, 8, 15)


def test_in_n_years() -> None:
    assert parse("in 1 year", today=TODAY) == date(2026, 6, 15)


def test_n_months_ago() -> None:
    assert parse("3 months ago", today=TODAY) == date(2025, 3, 15)


def test_next_month() -> None:
    assert parse("next month", today=TODAY) == date(2025, 7, 15)


def test_last_month() -> None:
    assert parse("last month", today=TODAY) == date(2025, 5, 15)


def test_next_year() -> None:
    assert parse("next year", today=TODAY) == date(2026, 6, 15)


def test_last_year() -> None:
    assert parse("last year", today=TODAY) == date(2024, 6, 15)


# ---------------------------------------------------------------------------
# Relative — compound offsets
# ---------------------------------------------------------------------------


def test_year_and_month_offset() -> None:
    # "1 year and 2 months after yesterday"
    expected = date(2026, 8, 14)
    assert parse("1 year and 2 months after yesterday", today=TODAY) == expected


def test_weeks_and_days_compound() -> None:
    assert parse("2 weeks and 3 days from now", today=TODAY) == date(2025, 7, 2)


def test_word_number_compound() -> None:
    # "two weeks from tomorrow"
    assert parse("two weeks from tomorrow", today=TODAY) == date(2025, 6, 30)


# ---------------------------------------------------------------------------
# Before / after absolute anchor
# ---------------------------------------------------------------------------


def test_days_before_absolute() -> None:
    assert parse("5 days before December 1st, 2025", today=TODAY) == date(2025, 11, 26)


def test_days_after_absolute() -> None:
    assert parse("10 days after January 1, 2026", today=TODAY) == date(2026, 1, 11)


def test_months_before_absolute() -> None:
    assert parse("2 months before March 15 2026", today=TODAY) == date(2026, 1, 15)


def test_prior_to() -> None:
    assert parse("1 week prior to July 4 2025", today=TODAY) == date(2025, 6, 27)


def test_following() -> None:
    assert parse("3 days following December 25 2025", today=TODAY) == date(2025, 12, 28)


# ---------------------------------------------------------------------------
# Weekday navigation
# ---------------------------------------------------------------------------


def test_next_tuesday() -> None:
    # TODAY = Sunday 2025-06-15; next Tuesday = 2025-06-17
    assert parse("next Tuesday", today=TODAY) == date(2025, 6, 17)


def test_next_monday() -> None:
    # Next Monday from Sunday = tomorrow
    assert parse("next Monday", today=TODAY) == date(2025, 6, 16)


def test_last_friday() -> None:
    # TODAY = Sunday; last Friday = 2025-06-13
    assert parse("last Friday", today=TODAY) == date(2025, 6, 13)


def test_last_saturday() -> None:
    assert parse("last Saturday", today=TODAY) == date(2025, 6, 14)


def test_bare_weekday() -> None:
    # bare "Wednesday" → next Wednesday
    assert parse("Wednesday", today=TODAY) == date(2025, 6, 18)


def test_this_weekday() -> None:
    # "this Friday" from Sunday → next Friday
    assert parse("this Friday", today=TODAY) == date(2025, 6, 20)


def test_next_week() -> None:
    assert parse("next week", today=TODAY) == date(2025, 6, 22)


def test_last_week() -> None:
    assert parse("last week", today=TODAY) == date(2025, 6, 8)


# ---------------------------------------------------------------------------
# Abbreviations and case insensitivity
# ---------------------------------------------------------------------------


def test_abbreviated_month() -> None:
    assert parse("Jan 5, 2026", today=TODAY) == date(2026, 1, 5)


def test_abbreviated_weekday() -> None:
    assert parse("next Mon", today=TODAY) == date(2025, 6, 16)


def test_case_insensitive() -> None:
    assert parse("NEXT TUESDAY", today=TODAY) == date(2025, 6, 17)


def test_mixed_case() -> None:
    assert parse("5 Days Before December 1st, 2025", today=TODAY) == date(2025, 11, 26)


# ---------------------------------------------------------------------------
# today parameter defaults to real today when omitted (smoke test)
# ---------------------------------------------------------------------------


def test_default_today_is_real_today() -> None:
    result = parse("today")
    assert result == date.today()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_unparseable_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Cannot parse"):
        parse("the day after never", today=TODAY)


def test_empty_string_raises() -> None:
    with pytest.raises(ValueError):
        parse("", today=TODAY)
