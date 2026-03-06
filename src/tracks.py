"""
tracks.py
---------
Fetches the user's saved (liked) tracks from the Spotify library API,
filtering by a configurable start date.
"""

from datetime import date, datetime, timezone
from typing import Any

import spotipy


# Maximum number of tracks returned per API page (Spotify limit)
_PAGE_LIMIT = 50


def _parse_saved_at(saved_at_str: str) -> date:
    """
    Parse the ISO-8601 'added_at' timestamp returned by Spotify into a date.

    Spotify returns strings like '2024-03-15T18:42:00Z'.
    """
    dt = datetime.strptime(saved_at_str, "%Y-%m-%dT%H:%M:%SZ")
    return dt.replace(tzinfo=timezone.utc).date()


def get_saved_tracks(
    sp: spotipy.Spotify,
    start_date: date,
) -> list[dict[str, Any]]:
    """
    Retrieve all tracks saved in the user's library on or after *start_date*.

    Each item in the returned list is a dict with:
        - track_id   (str)  : Spotify track ID
        - track_uri  (str)  : Spotify URI  (e.g. 'spotify:track:...')
        - track_name (str)  : track title
        - artist     (str)  : primary artist name
        - album      (str)  : album name
        - saved_at   (date) : date the track was liked

    Args:
        sp:         Authenticated spotipy client.
        start_date: Only include tracks saved on this date or later.

    Returns:
        List of track dicts sorted by saved_at ascending.
    """
    print(f"[tracks] Fetching saved tracks from {start_date} onwards …")

    results: list[dict[str, Any]] = []
    offset = 0
    stop_early = False

    while True:
        page = sp.current_user_saved_tracks(limit=_PAGE_LIMIT, offset=offset)
        items = page.get("items", [])

        if not items:
            break

        for item in items:
            saved_at = _parse_saved_at(item["added_at"])

            # Spotify returns tracks in reverse-chronological order.
            # Once we reach a track older than start_date we can stop.
            if saved_at < start_date:
                stop_early = True
                break

            track = item["track"]
            if track is None:
                # Occasionally Spotify returns a null track (e.g. local files)
                continue

            results.append({
                "track_id":   track["id"],
                "track_uri":  track["uri"],
                "track_name": track["name"],
                "artist":     track["artists"][0]["name"] if track["artists"] else "Unknown",
                "album":      track["album"]["name"],
                "saved_at":   saved_at,
            })

        if stop_early or page["next"] is None:
            break

        offset += _PAGE_LIMIT

    # Sort ascending so grouping is chronologically consistent
    results.sort(key=lambda t: t["saved_at"])
    print(f"[tracks] Found {len(results)} track(s) saved since {start_date}.")
    return results
