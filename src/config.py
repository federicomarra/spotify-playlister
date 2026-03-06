"""
config.py
---------
Reads Spotify credentials from a .secrets.txt file and exposes them
as a typed dataclass used throughout the application.
"""

import os
from dataclasses import dataclass


SECRETS_FILE = "secrets.txt"
REQUIRED_KEYS = ["CLIENT_ID", "CLIENT_SECRET", "REDIRECT_URI", "USERNAME"]
VALID_INTERVALS = [1, 2, 3, 6, 12]
VALID_STYLES = ["short", "long", "numeric"]


@dataclass
class SpotifyConfig:
    """Holds all Spotify API credentials loaded from the secrets file."""
    client_id: str
    client_secret: str
    redirect_uri: str
    username: str


def load_secrets(path: str = SECRETS_FILE) -> SpotifyConfig:
    """
    Parse the secrets.txt file and return a SpotifyConfig instance.

    The file must contain KEY=VALUE pairs (one per line).
    Lines starting with '#' are treated as comments and ignored.

    Raises:
        FileNotFoundError: if the secrets file does not exist.
        ValueError: if any required key is missing.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Secrets file '{path}' not found.\n"
            "Please create it based on the provided secrets.txt template."
        )

    secrets: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            secrets[key.strip()] = value.strip()

    missing = [k for k in REQUIRED_KEYS if k not in secrets]
    if missing:
        raise ValueError(
            f"Missing required key(s) in '{path}': {', '.join(missing)}"
        )

    return SpotifyConfig(
        client_id=secrets["CLIENT_ID"],
        client_secret=secrets["CLIENT_SECRET"],
        redirect_uri=secrets["REDIRECT_URI"],
        username=secrets["USERNAME"],
    )


def validate_interval(interval: int) -> None:
    """Raise ValueError if the grouping interval is not one of the allowed values."""
    if interval not in VALID_INTERVALS:
        raise ValueError(
            f"Interval '{interval}' is not valid. "
            f"Choose from: {VALID_INTERVALS}"
        )


def validate_style(style: str) -> None:
    """Raise ValueError if the naming style is not one of the allowed values."""
    if style not in VALID_STYLES:
        raise ValueError(
            f"Style '{style}' is not valid. "
            f"Choose from: {VALID_STYLES}"
        )
