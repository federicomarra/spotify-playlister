"""
main.py
-------
Command-line entry point for Spotify Playlister.

Usage examples
--------------
# Group liked tracks monthly from Jan 2024, short names
python main.py --start-date 2024-01-01 --interval 1 --style short

# Group every 3 months with a custom prefix, private playlists
python main.py --start-date 2023-06-01 --interval 3 --style long \\
               --prefix "My Favourites" --private

# Preview what would be created/updated without touching Spotify
python main.py --start-date 2024-01-01 --interval 6 --dry-run

# Use a custom secrets file location
python main.py --start-date 2024-01-01 --secrets /path/to/my_secrets.txt
"""

import argparse
import sys
from datetime import date

from src.auth import get_spotify_client
from src.config import (
    VALID_INTERVALS,
    VALID_STYLES,
    load_secrets,
    validate_interval,
    validate_style,
)
from src.grouping import group_tracks_by_period
from src.naming import format_playlist_name
from src.playlists import get_user_playlists, sync_period_to_playlist
from src.tracks import get_saved_tracks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Spotify Playlister – organise your Liked Songs into "
            "time-based playlists automatically."
        )
    )

    parser.add_argument(
        "--start-date",
        required=True,
        metavar="YYYY-MM-DD",
        help="Only process tracks saved on or after this date.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1,
        choices=VALID_INTERVALS,
        metavar="{1,2,3,6,12}",
        help=(
            "Grouping window in months. "
            "1 = one playlist per month, 12 = one per year. "
            f"Allowed values: {VALID_INTERVALS}. Default: 1."
        ),
    )
    parser.add_argument(
        "--style",
        default="short",
        choices=VALID_STYLES,
        metavar="{short,long,numeric}",
        help=(
            "Playlist naming style. "
            "short='Jan 2024', long='January 2024', numeric='2024-01'. "
            "Default: short."
        ),
    )
    parser.add_argument(
        "--prefix",
        default="",
        metavar="TEXT",
        help=(
            "Optional text prepended to each playlist name, "
            "e.g. 'Liked Songs' → 'Liked Songs – Jan 2024'."
        ),
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Create new playlists as private (default: public).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a summary of what would be done without making any changes.",
    )
    parser.add_argument(
        "--secrets",
        default=".secrets.txt",
        metavar="FILE",
        help="Path to the secrets file. Default: .secrets.txt",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # --- Validate inputs -------------------------------------------------------
    try:
        start_date = date.fromisoformat(args.start_date)
    except ValueError:
        print(f"[error] Invalid date format '{args.start_date}'. Use YYYY-MM-DD.")
        sys.exit(1)

    try:
        validate_interval(args.interval)
        validate_style(args.style)
    except ValueError as exc:
        print(f"[error] {exc}")
        sys.exit(1)

    # --- Load credentials and authenticate ------------------------------------
    try:
        config = load_secrets(args.secrets)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[error] {exc}")
        sys.exit(1)

    if args.dry_run:
        print("[dry-run] No changes will be made to Spotify.\n")

    sp = get_spotify_client(config)

    # --- Fetch liked tracks ---------------------------------------------------
    tracks = get_saved_tracks(sp, start_date)

    if not tracks:
        print("No tracks found for the given date range. Nothing to do.")
        return

    # --- Group tracks into time buckets ---------------------------------------
    groups = group_tracks_by_period(tracks, args.interval)
    print(f"[grouping] {len(groups)} period(s) to process.\n")

    # --- Load existing playlists (avoids redundant API calls) -----------------
    existing_playlists = get_user_playlists(sp, config.username)
    print(f"[playlists] Found {len(existing_playlists)} existing playlist(s).\n")

    # --- Sync each period to a playlist ---------------------------------------
    results = []

    for period_start, period_tracks in groups.items():
        playlist_name = format_playlist_name(
            period_start=period_start,
            interval_months=args.interval,
            style=args.style,
            prefix=args.prefix,
        )

        print(f"Processing '{playlist_name}' ({len(period_tracks)} track(s)) …")

        summary = sync_period_to_playlist(
            sp=sp,
            username=config.username,
            playlist_name=playlist_name,
            tracks=period_tracks,
            existing_playlists=existing_playlists,
            public=not args.private,
            dry_run=args.dry_run,
        )
        results.append(summary)

        action = "created" if summary["created"] else "updated"
        print(
            f"  ✓ Playlist {action}: '{summary['playlist_name']}' | "
            f"added={summary['added']}  skipped={summary['skipped']}\n"
        )

    # --- Final summary --------------------------------------------------------
    total_added   = sum(r["added"]   for r in results)
    total_skipped = sum(r["skipped"] for r in results)
    total_created = sum(1 for r in results if r["created"])

    print("=" * 60)
    print("Done!")
    print(f"  Playlists processed : {len(results)}")
    print(f"  Playlists created   : {total_created}")
    print(f"  Tracks added        : {total_added}")
    print(f"  Tracks skipped      : {total_skipped} (already present)")
    if args.dry_run:
        print("\n  (dry-run mode – no actual changes were made)")
    print("=" * 60)


if __name__ == "__main__":
    main()
