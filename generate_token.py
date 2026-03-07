"""
generate_token.py
-----------------
One-time helper script to obtain a Spotify refresh token for use in
GitHub Actions (or any other headless / CI environment).

Run this ONCE on your local machine:

    python generate_token.py

A browser window will open. Log in and authorise the app.
The script will then print the refresh token -- copy it and add it as a
GitHub Actions secret named SPOTIFY_REFRESH_TOKEN.

You do NOT need to run this script again unless you revoke the app's
permissions from your Spotify account.
"""

import json
import os

from src.config import load_secrets
from src.auth import SCOPES
from spotipy.oauth2 import SpotifyOAuth


def main() -> None:
    config = load_secrets("secrets.txt")

    auth_manager = SpotifyOAuth(
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=config.redirect_uri,
        scope=SCOPES,
        username=config.username,
        open_browser=True,
    )

    print("Opening browser for Spotify authorisation ...")
    print("After logging in, copy the full redirect URL and paste it below.\n")

    # Get the auth URL and open it
    auth_url = auth_manager.get_authorize_url()
    print(f"If the browser did not open, visit:\n  {auth_url}\n")

    import webbrowser
    webbrowser.open(auth_url)

    redirected_url = input("Paste the full redirect URL here: ").strip()
    code = auth_manager.parse_response_code(redirected_url)
    token_info = auth_manager.get_access_token(code, as_dict=True)

    refresh_token = token_info.get("refresh_token", "")

    if not refresh_token:
        print("[error] No refresh token returned. Make sure the app has offline_access or try again.")
        return

    print("\n" + "=" * 60)
    print("SUCCESS! Your Spotify refresh token is:\n")
    print(refresh_token)
    print("\n" + "=" * 60)
    print(
        "\nAdd this as a GitHub Actions secret:\n"
        "  Name : REFRESH_TOKEN\n"
        "  Value: (the token above)\n"
        "\nGo to: https://github.com/<you>/<repo>/settings/secrets/actions"
    )


if __name__ == "__main__":
    main()
