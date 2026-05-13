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
    "half": 0,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    """Lowercase, collapse whitespace, strip ordinal suffixes."""
    s = s.lower().strip()
    s = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b", r"\1", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"([a-z])\.(\s|$)", r"\1\2", s)
    s = s.rstrip(".")
    return s


def _parse_number(token: str) -> int | None:
    if re.fullmatch(r"\d+", token):
        return int(token)
    return WORD_NUMBERS.get(token)


def _parse_quantity(tokens: list[str], pos: int) -> tuple[int, int]:
    """
    Parse a possibly compound English number starting at *pos*.
    Returns (value, new_pos).
    """
    v = _parse_number(tokens[pos])
    if v is None:
        return 0, pos
    pos += 1
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
    """'This Tuesday' — the coming Tuesday within the current week or next."""
    return _next_weekday(ref, weekday)


def _end_of_month(d: date) -> date:
    last_day = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last_day)


def _start_of_month(d: date) -> date:
    return date(d.year, d.month, 1)


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
    # 1. Simple named anchors
    # ------------------------------------------------------------------
    if s in ("today", "now"):
        return today
    if s == "tomorrow":
        return today + timedelta(days=1)
    if s == "yesterday":
        return today - timedelta(days=1)

    # ------------------------------------------------------------------
    # 2. "the day after tomorrow" / "the day before yesterday"
    # ------------------------------------------------------------------
    if s == "the day after tomorrow":
        return today + timedelta(days=2)
    if s == "the day before yesterday":
        return today - timedelta(days=2)

    # ------------------------------------------------------------------
    # 3. "next/last/this <weekday>" and bare weekday name
    # ------------------------------------------------------------------
    _wd_pat = "|".join(WEEKDAY_NAMES)
    m = re.fullmatch(r"(next|last|this|coming|this coming)\s+(" + _wd_pat + r")", s)
    if m:
        direction, day_name = m.group(1), m.group(2)
        wd = WEEKDAY_NAMES[day_name]
        if direction == "last":
            return _last_weekday(today, wd)
        else:  # next / this / coming / this coming → upcoming
            return _next_weekday(today, wd)

    # "coming <weekday>" or "on <weekday>" or "by <weekday>"
    m = re.fullmatch(r"(?:coming|on|by)\s+(" + _wd_pat + r")", s)
    if m:
        return _next_weekday(today, WEEKDAY_NAMES[m.group(1)])

    # bare weekday name → same as "next <weekday>"
    if s in WEEKDAY_NAMES:
        return _next_weekday(today, WEEKDAY_NAMES[s])

    # ------------------------------------------------------------------
    # 4. "next/last week/month/year"
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
    # 5. "start/beginning/end of (next/last/this) month/year"
    # ------------------------------------------------------------------
    m = re.fullmatch(
        r"(start|beginning|end)\s+of\s+(?:(next|last|this)\s+)?(month|year)", s
    )
    if m:
        boundary, direction, unit = m.group(1), m.group(2), m.group(3)
        direction = direction or "this"
        if unit == "month":
            if direction == "next":
                ref = _add_months(today, 1)
            elif direction == "last":
                ref = _add_months(today, -1)
            else:
                ref = today
            if boundary == "end":
                return _end_of_month(ref)
            else:
                return _start_of_month(ref)
        else:  # year
            if direction == "next":
                yr = today.year + 1
            elif direction == "last":
                yr = today.year - 1
            else:
                yr = today.year
            if boundary == "end":
                return date(yr, 12, 31)
            else:
                return date(yr, 1, 1)

    # ------------------------------------------------------------------
    # 6. "end/start of month" (shorthand without "this")
    # ------------------------------------------------------------------
    if s == "end of month":
        return _end_of_month(today)
    if s in ("start of month", "beginning of month"):
        return _start_of_month(today)
    if s == "end of year":
        return date(today.year, 12, 31)
    if s in ("start of year", "beginning of year"):
        return date(today.year, 1, 1)

    # ------------------------------------------------------------------
    # 7. "<N> <unit>(s) ago / from now / hence / later / from today"
    # ------------------------------------------------------------------
    m = re.fullmatch(r"(.+?)\s+(ago|from now|hence|later|from today)", s)
    if m:
        offset_str, direction = m.group(1), m.group(2)
        sign = -1 if direction == "ago" else 1
        delta = _parse_offset(offset_str)
        if delta is not None:
            return _apply_delta(today, delta, sign)

    # ------------------------------------------------------------------
    # 8. "in <N> <unit>(s)"  →  future
    # ------------------------------------------------------------------
    m = re.fullmatch(r"in\s+(.+)", s)
    if m:
        delta = _parse_offset(m.group(1))
        if delta is not None:
            return _apply_delta(today, delta, 1)

    # ------------------------------------------------------------------
    # 9. "<N> <unit>(s) before/after <anchor>"
    # ------------------------------------------------------------------
    for pivot in ("before", "after", "prior to", "following", "from"):
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
    # 10. "the Nth of <Month> [YYYY]" / "the <Month> Nth [YYYY]"
    # ------------------------------------------------------------------
    _mon_pat = "(" + "|".join(MONTH_NAMES) + ")"
    m = re.fullmatch(r"the\s+(\d{1,2})\s+of\s+" + _mon_pat + r"(?:,?\s+(\d{4}))?", s)
    if m:
        day = int(m.group(1))
        mon = MONTH_NAMES[m.group(2)]
        year = int(m.group(3)) if m.group(3) else today.year
        try:
            return date(year, mon, day)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # 11. Absolute date (various formats)
    # ------------------------------------------------------------------
    anchor = _parse_anchor(s, today)
    if anchor is not None:
        return anchor

    raise ValueError(f"Cannot parse date expression: {original!r}")


# ---------------------------------------------------------------------------
# Offset parsing  ("3 days", "1 year and 2 months", "a week", "a fortnight"…)
# ---------------------------------------------------------------------------

_Offset = tuple[int, int, int]  # (days, months, years)


def _parse_offset(s: str) -> _Offset | None:
    """
    Parse an offset like ``"3 days"``, ``"1 year and 2 months"``,
    ``"a week"``, ``"2 weeks and 3 days"``, ``"a fortnight"``.

    Returns (days, months, years) or None if unrecognized.
    """
    s = s.strip()
    # Remove filler words
    s = re.sub(r"\b(and|,)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    # Handle "a fortnight" / "fortnight"
    if s in ("a fortnight", "fortnight", "1 fortnight", "one fortnight"):
        return (14, 0, 0)

    days = 0
    months = 0
    years = 0

    tokens = s.split()
    i = 0
    matched_any = False

    while i < len(tokens):
        qty, new_i = _parse_quantity(tokens, i)
        if new_i == i:
            return None
        i = new_i

        if i >= len(tokens):
            return None
        unit = tokens[i].rstrip("s")  # strip plural 's'
        i += 1

        if unit in ("day",):
            days += qty
        elif unit in ("week",):
            days += qty * 7
        elif unit in ("fortnight",):
            days += qty * 14
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
    Try to parse *s* as an absolute date or a named anchor.
    """
    s = s.strip()

    # Named anchors
    if s in ("today", "now"):
        return today
    if s == "tomorrow":
        return today + timedelta(days=1)
    if s == "yesterday":
        return today - timedelta(days=1)

    # ISO: 2025-12-01
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None

    # YYYY/MM/DD: 2025/12/04
    m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None

    # YYYY.MM.DD: 2025.12.04
    m = re.fullmatch(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None

    # DD.MM.YYYY: 04.12.2025
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None

    # DD-MM-YYYY: 04-12-2025 (European format, only when year is 4 digits last)
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})-(\d{4})", s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None

    # MM/DD/YYYY or MM/DD/YY
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if m:
        mo, dy, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if yr < _TWO_DIGIT_YEAR_MAX:
            yr += _TWO_DIGIT_YEAR_BASE
        try:
            return date(yr, mo, dy)
        except ValueError:
            return None

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
