"""
naming.py
---------
Generates human-readable playlist names for a given time period.

Supported styles
----------------
short   → "Jan 2024"  /  "Jan-Mar 2024"  /  "Jan 2024 - Feb 2025"
long    → "January 2024"  /  "January-March 2024"
numeric → "2024-01"  /  "2024-01_03"  (year-firstMonth_lastMonth)

An optional *prefix* string is prepended with " – " as separator,
e.g. prefix="Liked Songs" → "Liked Songs – Jan 2024".
"""

from datetime import date

from dateutil.relativedelta import relativedelta


_MONTH_SHORT = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]
_MONTH_LONG = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def format_playlist_name(
    period_start: date,
    interval_months: int,
    style: str = "short",
    prefix: str = "",
) -> str:
    """
    Build a playlist name for a period.

    Args:
        period_start:    First day of the period (always the 1st of a month).
        interval_months: Duration of the period in months.
        style:           One of 'short', 'long', 'numeric'.
        prefix:          Optional string prepended to the name.

    Returns:
        Formatted playlist name string.
    """
    period_end = period_start + relativedelta(months=interval_months - 1)

    y_start, m_start = period_start.year, period_start.month
    y_end,   m_end   = period_end.year,   period_end.month

    if style == "numeric":
        if interval_months == 1:
            name = f"{y_start}-{m_start:02d}"
        elif y_start == y_end:
            name = f"{y_start}-{m_start:02d}_{m_end:02d}"
        else:
            name = f"{y_start}-{m_start:02d}_{y_end}-{m_end:02d}"

    elif style == "long":
        ms = _MONTH_LONG[m_start - 1]
        me = _MONTH_LONG[m_end - 1]
        if interval_months == 1:
            name = f"{ms} {y_start}"
        elif y_start == y_end:
            name = f"{ms}-{me} {y_start}"
        else:
            name = f"{ms} {y_start} - {me} {y_end}"

    else:  # default: "short"
        ms = _MONTH_SHORT[m_start - 1]
        me = _MONTH_SHORT[m_end - 1]
        if interval_months == 1:
            name = f"{ms} {y_start}"
        elif y_start == y_end:
            name = f"{ms}-{me} {y_start}"
        else:
            name = f"{ms} {y_start} - {me} {y_end}"

    if prefix:
        name = f"{prefix} – {name}"

    return name
