"""
grouping.py
-----------
Groups a list of saved-track dicts into time-based buckets.
Each bucket covers *interval_months* months and starts at the first month
of that period (e.g. with interval=3 the periods are Jan-Mar, Apr-Jun, …).
"""

from collections import defaultdict
from datetime import date
from typing import Any

from dateutil.relativedelta import relativedelta


def _period_start(track_date: date, interval_months: int) -> date:
    """
    Return the first day of the period that contains *track_date*.

    Periods are aligned to calendar months:
      - interval=1 → each calendar month is its own period
      - interval=3 → Jan-Mar / Apr-Jun / Jul-Sep / Oct-Dec
      - interval=6 → Jan-Jun / Jul-Dec
      - interval=12 → the whole year
    For intervals that don't divide 12 evenly (2) the periods start from
    month 1 and advance in steps of *interval_months*.
    """
    month_index = (track_date.month - 1) // interval_months
    start_month = month_index * interval_months + 1
    return date(track_date.year, start_month, 1)


def group_tracks_by_period(
    tracks: list[dict[str, Any]],
    interval_months: int,
) -> dict[date, list[dict[str, Any]]]:
    """
    Partition *tracks* into buckets keyed by their period-start date.

    Args:
        tracks:          List of track dicts (as returned by tracks.get_saved_tracks).
        interval_months: Bucket size in months (1, 2, 3, 6, or 12).

    Returns:
        An ordered dict mapping period_start (date) → list of tracks,
        sorted chronologically.
    """
    buckets: dict[date, list[dict[str, Any]]] = defaultdict(list)

    for track in tracks:
        key = _period_start(track["saved_at"], interval_months)
        buckets[key].append(track)

    # Return sorted by period start date
    return dict(sorted(buckets.items()))


def period_end_date(period_start: date, interval_months: int) -> date:
    """Return the last day of the period that starts on *period_start*."""
    next_period = period_start + relativedelta(months=interval_months)
    return next_period - relativedelta(days=1)
