"""
auth.py
-------
Handles Spotify OAuth 2.0 authentication via the spotipy library.
A local cache file (.cache-<username>) is created automatically by spotipy
to store and refresh the access token between runs.
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from src.config import SpotifyConfig


# Scopes required by this application
SCOPES = " ".join([
    "user-library-read",       # Read the user's saved (liked) tracks
    "playlist-read-private",   # Read private playlists (to check existing ones)
    "playlist-modify-public",  # Create / modify public playlists
    "playlist-modify-private", # Create / modify private playlists
])


def get_spotify_client(config: SpotifyConfig) -> spotipy.Spotify:
    """
    Build and return an authenticated spotipy.Spotify client.

    On the first run a browser window opens for the user to authorise the app.
    Subsequent runs reuse the cached token (auto-refreshed when expired).

    Args:
        config: SpotifyConfig loaded from secrets.txt.

    Returns:
        An authenticated spotipy.Spotify instance.
    """
    auth_manager = SpotifyOAuth(
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=config.redirect_uri,
        scope=SCOPES,
        username=config.username,
        cache_path=f".cache-{config.username}",
        open_browser=True,
    )

    client = spotipy.Spotify(auth_manager=auth_manager)

    # Verify authentication works by fetching the current user profile
    user = client.current_user()
    print(f"[auth] Authenticated as: {user['display_name']} ({user['id']})")

    return client
