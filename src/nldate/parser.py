"""Natural language date parser — pattern matching, no LLMs needed."""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

WEEKDAY_NAMES: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    # abbreviations
    "mon": 0,
    "tue": 1,
    "tues": 1,
    "wed": 2,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

MONTH_NAMES: dict[str, int] = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    # abbreviations
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

WORD_NUMBERS: dict[str, int] = {
    "zero": 0,
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
    "half": 0,  # "half a year" — handled specially
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation noise."""
    s = s.lower().strip()
    # Remove ordinal suffixes: 1st→1, 2nd→2, 3rd→3, 4th→4 …
    s = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b", r"\1", s)
    # Collapse multiple spaces
    s = re.sub(r"\s+", " ", s)
    return s


def _parse_number(token: str) -> int | None:
    """Convert a string token to an integer (digit string or English word)."""
    if re.fullmatch(r"\d+", token):
        return int(token)
    return WORD_NUMBERS.get(token)


def _parse_quantity(tokens: list[str], pos: int) -> tuple[int, int]:
    """
    Parse a possibly compound English number starting at *pos*.
    Returns (value, new_pos).

    Handles:
      "3"          → 3
      "three"      → 3
      "twenty two" → 22   (two consecutive word numbers that sum)
      "2"          → 2
    """
    v = _parse_number(tokens[pos])
    if v is None:
        return 0, pos
    pos += 1
    # Try to combine tens + units, e.g. "twenty" + "two"
    if pos < len(tokens):
        v2 = _parse_number(tokens[pos])
        tens_range = range(_TENS_MIN, _TENS_MAX, _TENS_STEP)
        if v2 is not None and 1 <= v2 <= _UNITS_DIGIT_MAX and v in tens_range:
            v += v2
            pos += 1
    return v, pos


_UNITS_DIGIT_MAX = 9
_TENS_MIN = 20
_TENS_MAX = 100
_TENS_STEP = 10
_TWO_DIGIT_YEAR_MAX = 100
_TWO_DIGIT_YEAR_BASE = 2000


def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(d.day, last_day)
    return date(year, month, day)


def _add_years(d: date, years: int) -> date:
    return _add_months(d, years * 12)


def _next_weekday(ref: date, weekday: int) -> date:
    """Return the next occurrence of *weekday* strictly after *ref*."""
    days_ahead = weekday - ref.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return ref + timedelta(days=days_ahead)


def _last_weekday(ref: date, weekday: int) -> date:
    """Return the most recent occurrence of *weekday* strictly before *ref*."""
    days_behind = ref.weekday() - weekday
    if days_behind <= 0:
        days_behind += 7
    return ref - timedelta(days=days_behind)


def _this_weekday(ref: date, weekday: int) -> date:
    """
    'This Tuesday' — the coming Tuesday within the current week (Mon-Sun),
    or next week if today is already past that day.
    """
    return _next_weekday(ref, weekday)


# ---------------------------------------------------------------------------
# Main parse function
# ---------------------------------------------------------------------------


def parse(s: str, today: date | None = None) -> date:
    """
    Parse a natural language date string and return a ``datetime.date``.

    Parameters
    ----------
    s:
        Natural language date expression, e.g. ``"next Tuesday"``,
        ``"5 days before December 1st, 2025"``,
        ``"1 year and 2 months after yesterday"``.
    today:
        Reference date for relative expressions.  Defaults to
        ``datetime.date.today()``.

    Returns
    -------
    datetime.date

    Raises
    ------
    ValueError
        If the string cannot be parsed.
    """
    if today is None:
        today = date.today()

    original = s
    s = _normalize(s)

    # ------------------------------------------------------------------
    # 1. Absolute anchors with optional offset
    # ------------------------------------------------------------------

    # "today", "tomorrow", "yesterday"
    if s == "today":
        return today
    if s == "tomorrow":
        return today + timedelta(days=1)
    if s == "yesterday":
        return today - timedelta(days=1)

    # ------------------------------------------------------------------
    # 2.  "next/last/this <weekday>"
    # ------------------------------------------------------------------
    m = re.fullmatch(
        r"(next|last|this)\s+(" + "|".join(WEEKDAY_NAMES) + r")", s
    )
    if m:
        direction, day_name = m.group(1), m.group(2)
        wd = WEEKDAY_NAMES[day_name]
        if direction == "next":
            return _next_weekday(today, wd)
        elif direction == "last":
            return _last_weekday(today, wd)
        else:  # this
            return _this_weekday(today, wd)

    # bare weekday name → same as "next <weekday>"
    if s in WEEKDAY_NAMES:
        return _next_weekday(today, WEEKDAY_NAMES[s])

    # ------------------------------------------------------------------
    # 3.  "next/last week/month/year"
    # ------------------------------------------------------------------
    m = re.fullmatch(r"(next|last)\s+(week|month|year)", s)
    if m:
        direction, unit = m.group(1), m.group(2)
        sign = 1 if direction == "next" else -1
        if unit == "week":
            return today + timedelta(weeks=sign)
        elif unit == "month":
            return _add_months(today, sign)
        else:
            return _add_years(today, sign)

    # ------------------------------------------------------------------
    # 4.  "<N> <unit>(s) ago / from now / ago/hence"
    # ------------------------------------------------------------------
    m = re.fullmatch(
        r"(.+?)\s+(ago|from now|hence|later|from today)", s
    )
    if m:
        offset_str, direction = m.group(1), m.group(2)
        sign = -1 if direction == "ago" else 1
        delta = _parse_offset(offset_str)
        if delta is not None:
            return _apply_delta(today, delta, sign)

    # ------------------------------------------------------------------
    # 5.  "in <N> <unit>(s)"  →  future
    # ------------------------------------------------------------------
    m = re.fullmatch(r"in\s+(.+)", s)
    if m:
        delta = _parse_offset(m.group(1))
        if delta is not None:
            return _apply_delta(today, delta, 1)

    # ------------------------------------------------------------------
    # 6.  "<N> <unit>(s) before/after <anchor>"
    # ------------------------------------------------------------------
    # We need to split on "before" or "after" that is *not* part of a month
    # name or other word.
    for pivot in ("before", "after", "prior to", "following", "from"):
        # build a regex that finds the pivot as a whole word
        pat = r"^(.+?)\s+\b" + re.escape(pivot) + r"\b\s+(.+)$"
        m = re.fullmatch(pat, s)
        if m:
            offset_str = m.group(1).strip()
            anchor_str = m.group(2).strip()
            sign = -1 if pivot in ("before", "prior to") else 1
            delta = _parse_offset(offset_str)
            anchor = _parse_anchor(anchor_str, today)
            if delta is not None and anchor is not None:
                return _apply_delta(anchor, delta, sign)

    # ------------------------------------------------------------------
    # 7.  Absolute date (various formats)
    # ------------------------------------------------------------------
    anchor = _parse_anchor(s, today)
    if anchor is not None:
        return anchor

    raise ValueError(f"Cannot parse date expression: {original!r}")


# ---------------------------------------------------------------------------
# Offset parsing  ("3 days", "1 year and 2 months", "a week", …)
# ---------------------------------------------------------------------------


# Offsets are stored as (days, months, years) tuples so we can apply
# calendar-aware arithmetic for months/years.
_Offset = tuple[int, int, int]  # (days, months, years)


def _parse_offset(s: str) -> _Offset | None:
    """
    Parse an offset like ``"3 days"``, ``"1 year and 2 months"``,
    ``"a week"``, ``"2 weeks and 3 days"``.

    Returns (days, months, years) or None if unrecognized.
    """
    s = s.strip()
    # Remove filler words
    s = re.sub(r"\b(and|,)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    days = 0
    months = 0
    years = 0

    tokens = s.split()
    i = 0
    matched_any = False

    while i < len(tokens):
        # Try to read a number
        qty, new_i = _parse_quantity(tokens, i)
        if new_i == i:
            # no number found — unrecognized token, bail
            return None
        i = new_i

        # Now expect a unit
        if i >= len(tokens):
            return None
        unit = tokens[i].rstrip("s")  # strip plural 's'
        i += 1

        if unit in ("day",):
            days += qty
        elif unit in ("week",):
            days += qty * 7
        elif unit in ("month",):
            months += qty
        elif unit in ("year",):
            years += qty
        else:
            return None
        matched_any = True

    if not matched_any:
        return None
    return (days, months, years)


def _apply_delta(anchor: date, delta: _Offset, sign: int) -> date:
    days, months, years = delta
    result = anchor
    result = _add_years(result, sign * years)
    result = _add_months(result, sign * months)
    result += timedelta(days=sign * days)
    return result


# ---------------------------------------------------------------------------
# Anchor parsing  (absolute date expressions)
# ---------------------------------------------------------------------------

_MONTH_PAT = "(" + "|".join(MONTH_NAMES) + ")"
_DAY_PAT = r"(\d{1,2})"
_YEAR_PAT = r"(\d{4})"


def _parse_anchor(s: str, today: date) -> date | None:
    """
    Try to parse *s* as an absolute date or a named anchor like
    ``"today"``, ``"tomorrow"``, ``"yesterday"``.
    """
    s = s.strip()

    # Named anchors
    if s == "today":
        return today
    if s == "tomorrow":
        return today + timedelta(days=1)
    if s == "yesterday":
        return today - timedelta(days=1)

    # ISO: 2025-12-01
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # MM/DD/YYYY or MM/DD/YY
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if m:
        mo, dy, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if yr < _TWO_DIGIT_YEAR_MAX:
            yr += _TWO_DIGIT_YEAR_BASE
        return date(yr, mo, dy)

    # "Month DD, YYYY"  or  "Month DD YYYY"  or  "Month YYYY" (no day→1st)
    m = re.fullmatch(
        _MONTH_PAT + r"(?:\s+" + _DAY_PAT + r")?" + r"(?:,?\s+" + _YEAR_PAT + r")?",
        s,
    )
    if m:
        mon = MONTH_NAMES[m.group(1)]
        day = int(m.group(2)) if m.group(2) else 1
        year = int(m.group(3)) if m.group(3) else today.year
        try:
            return date(year, mon, day)
        except ValueError:
            return None

    # "DD Month YYYY"  or  "DD Month"
    m = re.fullmatch(
        _DAY_PAT + r"\s+" + _MONTH_PAT + r"(?:,?\s+" + _YEAR_PAT + r")?",
        s,
    )
    if m:
        day = int(m.group(1))
        mon = MONTH_NAMES[m.group(2)]
        year = int(m.group(3)) if m.group(3) else today.year
        try:
            return date(year, mon, day)
        except ValueError:
            return None

    return None
