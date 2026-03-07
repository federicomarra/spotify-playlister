"""
auth.py
-------
Handles Spotify OAuth 2.0 authentication via the spotipy library.

Two modes are supported:
  - Interactive (local): opens a browser window on the first run; the token
    is cached in .cache-<username> for subsequent runs.
  - CI / headless: reads a refresh token from the SPOTIFY_REFRESH_TOKEN
    environment variable, writes a minimal cache file, and lets spotipy
    refresh the access token automatically -- no browser required.
"""

import json
import os
import time

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from src.config import SpotifyConfig


# Scopes required by this application
SCOPES = " ".join([
    "user-library-read",        # Read the user's saved (liked) tracks
    "playlist-read-private",    # Read private playlists (to check for existing ones)
    "playlist-modify-public",   # Create / modify public playlists
    "playlist-modify-private",  # Create / modify private playlists
])


def _is_ci() -> bool:
    """Return True when running inside a CI environment (e.g. GitHub Actions)."""
    return os.environ.get("CI", "").lower() in ("true", "1", "yes")


def _write_cache_from_refresh_token(
    cache_path: str,
    config: SpotifyConfig,
    refresh_token: str,
) -> None:
    """
    Write a minimal spotipy cache file containing only the refresh token.

    spotipy will exchange it for a valid access token on the first API call.

    Args:
        cache_path:    Path where the .cache-<username> file should be written.
        config:        SpotifyConfig with client credentials.
        refresh_token: The Spotify refresh token from SPOTIFY_REFRESH_TOKEN.
    """
    cache_data = {
        "access_token":  "",          # Empty -- spotipy will refresh it
        "token_type":    "Bearer",
        "expires_in":    3600,
        "refresh_token": refresh_token,
        "scope":         SCOPES,
        "expires_at":    int(time.time()) - 1,  # Force immediate refresh
    }
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(cache_data, fh)


def get_spotify_client(config: SpotifyConfig) -> spotipy.Spotify:
    """
    Build and return an authenticated spotipy.Spotify client.

    In interactive mode (local runs) a browser window opens for the first
    authorisation; the token is cached and reused on subsequent runs.

    In CI mode (GitHub Actions) the REFRESH_TOKEN environment variable must be set. The function writes a temporary cache file so
    spotipy can silently refresh the access token without a browser.

    Args:
        config: SpotifyConfig loaded from the secrets file.

    Returns:
        An authenticated spotipy.Spotify instance.

    Raises:
        EnvironmentError: In CI mode when REFRESH_TOKEN is not set.
    """
    cache_path = f".cache-{config.username}"

    if _is_ci():
        refresh_token = os.environ.get("REFRESH_TOKEN", "").strip()
        if not refresh_token:
            raise EnvironmentError(
                "CI mode detected but REFRESH_TOKEN is not set.\n"
                "Add it as a repository secret in GitHub Actions."
            )
        print("[auth] CI mode: using refresh token from environment.")
        _write_cache_from_refresh_token(cache_path, config, refresh_token)

    auth_manager = SpotifyOAuth(
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=config.redirect_uri,
        scope=SCOPES,
        username=config.username,
        cache_path=cache_path,
        open_browser=not _is_ci(),
    )

    client = spotipy.Spotify(auth_manager=auth_manager)

    # Verify authentication by fetching the current user profile
    user = client.current_user()
    print(f"[auth] Authenticated as: {user['display_name']} ({user['id']})")

    return client
