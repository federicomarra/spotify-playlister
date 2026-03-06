# 🎵 Spotify Playlister

Automatically organise your Spotify **Liked Songs** into time-based playlists.
You choose the start date, the grouping window (1, 2, 3, 6 or 12 months), and the naming style — the script does the rest.
Re-running the script is always safe: existing tracks in a playlist are **never duplicated**.

---

## Project structure

```
spotify_playlister/
├── main.py              # CLI entry point – run this
├── requirements.txt     # Python dependencies
├── secrets.txt         # Your Spotify credentials (never commit this!)
└── src/
    ├── __init__.py
    ├── auth.py          # OAuth 2.0 authentication via spotipy
    ├── config.py        # Loads and validates secrets.txt + CLI inputs
    ├── tracks.py        # Fetches saved tracks from the Spotify library API
    ├── grouping.py      # Groups tracks into month-based time buckets
    ├── naming.py        # Generates playlist names (short / long / numeric)
    └── playlists.py     # Creates playlists and adds tracks without duplicates
```

---

## Setup

### 1 – Create a Spotify app

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and log in.
2. Click **Create app**.
3. Fill in any name and description.
4. Set **Redirect URI** to `http://127.0.0.1:8888/callback` (or any URI you prefer).
5. Copy your **Client ID** and **Client Secret**.

### 2 – Fill in `secrets.txt`

Edit the `secrets.txt` file in the project root:

```
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
REDIRECT_URI=http://127.0.0.1:8888/callback
USERNAME=your_spotify_username_here
```

> Your Spotify **username** is visible in your account settings at [spotify.com](https://www.spotify.com/account/overview/).
> ⚠️ Never commit `secrets.txt` to version control.

### 3 – Install dependencies

```bash
pip install -r requirements.txt
```

Python 3.10+ is recommended.

---

## Usage
The first time you run the script, a browser window will open asking you to log in to Spotify and authorise the app with the required permissions. After that, a token is cached in `.cache-<username>` and future runs will not require re-authentication unless the token expires or is deleted.

```
python main.py --start-date YYYY-MM-DD [options]
```

## Example usage
```bash
python main.py --start-date 2025-01-01 --interval 3 --style short --prefix "My songs"
```

### Required argument

| Argument | Description |
|---|---|
| `--start-date YYYY-MM-DD` | Only process tracks saved on or after this date |

### Optional arguments

| Argument | Default | Description |
|---|---|---|
| `--interval {1,2,3,6,12}` | `1` | Grouping window in months |
| `--style {short,long,numeric}` | `short` | Playlist naming style (see below) |
| `--prefix TEXT` | *(none)* | Text prepended to each playlist name |
| `--private` | *(public)* | Create playlists as private |
| `--dry-run` | *(off)* | Preview changes without touching Spotify |
| `--secrets FILE` | `.secrets.txt` | Path to credentials file |

### Naming styles

Given a 3-month period starting January 2024:

| Style | Example |
|---|---|
| `short` | `Jan-Mar 2024` |
| `long` | `January-March 2024` |
| `numeric` | `2024-01_03` |

With `--prefix "My Archive"` the name becomes `My Archive – Jan-Mar 2024`.

---

## Examples

```bash
# One playlist per month, starting from January 2024
python main.py --start-date 2024-01-01

# One playlist per quarter, long names, with a prefix
python main.py --start-date 2023-01-01 --interval 3 --style long --prefix "Liked"

# One playlist per year, numeric names, private
python main.py --start-date 2022-01-01 --interval 12 --style numeric --private

# Preview what would happen — no changes made
python main.py --start-date 2024-06-01 --interval 6 --dry-run
```

---

## How it works

1. **Authentication** (`auth.py`) — spotipy handles OAuth 2.0. On first run a browser window opens; the token is cached in `.cache-<username>` for future runs.
2. **Fetch tracks** (`tracks.py`) — iterates the `GET /me/tracks` endpoint, stopping once it reaches tracks older than `--start-date`.
3. **Group tracks** (`grouping.py`) — assigns each track to a period bucket based on its `saved_at` date and the chosen interval.
4. **Name playlists** (`naming.py`) — builds a human-readable name for each bucket using the chosen style and optional prefix.
5. **Sync playlists** (`playlists.py`) — for each bucket: finds an existing playlist with that name (or creates one), fetches its current tracks, then adds only the tracks that are not already present.

---

## Re-running safely

The script is **idempotent**: you can run it multiple times and it will never add the same track to a playlist twice. New tracks saved since the last run are picked up automatically.

---

## Required Spotify scopes

| Scope | Reason |
|---|---|
| `user-library-read` | Read your Liked Songs |
| `playlist-read-private` | Check whether a playlist already exists |
| `playlist-modify-public` | Create / update public playlists |
| `playlist-modify-private` | Create / update private playlists |
