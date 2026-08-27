# 🎵 Spotify Playlister

Automatically organise your Spotify **Liked Songs** into time-based playlists.
You choose the start date, the grouping window (1, 2, 3, 6 or 12 months), and the naming style.
Re-running the script is always safe: each playlist is kept as an exact mirror of the matching liked songs — same tracks, same order (newest first) — so tracks are never duplicated, and tracks you have **unliked** are automatically **removed**. A playlist that already matches is left untouched.

A **GitHub Actions workflow** is included to run the sync automatically every day with no manual intervention.

---

## Project structure

```
spotify-playlister/
├── main.py                          # CLI entry point – run this
├── generate_token.py                # One-time helper to get your refresh token
├── requirements.txt                 # Python dependencies
├── secrets.txt                      # Your Spotify credentials (never commit this!)
├── secrets.example.txt              # Template for secrets.txt
├── .github/
│   └── workflows/
│       └── sync.yml                 # Daily GitHub Actions workflow
└── src/
    ├── __init__.py
    ├── auth.py          # OAuth 2.0 – interactive (local) and headless (CI) modes
    ├── config.py        # Loads and validates secrets.txt + CLI inputs
    ├── tracks.py        # Fetches saved tracks from the Spotify library API
    ├── grouping.py      # Groups tracks into month-based time buckets
    ├── naming.py        # Generates playlist names (short / long / numeric)
    └── playlists.py     # Reads, creates and syncs playlists
```

---

## Local setup

### 1 – Create a Spotify app

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and log in.
2. Click **Create app** and fill in a name and description.
3. Set **Redirect URI** to `http://127.0.0.1:8888/callback`.
4. Under **APIs used**, select **Web API**.
5. Copy your **Client ID** and **Client Secret**.

### 2 – Fill in `secrets.txt`

```
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
REDIRECT_URI=http://127.0.0.1:8888/callback
USERNAME=your_spotify_username_here
```

> Your Spotify **username** is visible at [spotify.com/account](https://www.spotify.com/account/overview/).
> ⚠️ `secrets.txt` is in `.gitignore` — never commit it.

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
| `--no-remove` | *(off)* | Skip removal of unliked tracks |
| `--dry-run` | *(off)* | Report what would change without writing anything |
| `--secrets FILE` | `secrets.txt` | Path to credentials file |

### Naming styles

Given a 3-month period starting January 2024:

| Style | Example |
|---|---|
| `short` | `Jan-Mar 2024` |
| `long` | `January-March 2024` |
| `numeric` | `2024-01_03` |

With `--prefix "My songs"` the name becomes `My songs – Jan-Mar 2024`.

A full year (`--interval 12` starting in January) is named by the year alone in every style — `2024`, or `My songs – 2024` with a prefix.

---

## Examples

```bash
# One playlist per month from January 2024
python main.py --start-date 2024-01-01

# One playlist per quarter with prefix
python main.py --start-date 2024-01-01 --interval 3 --style short --prefix "My songs"

# One playlist per year, numeric names, private
python main.py --start-date 2022-01-01 --interval 12 --style numeric --private

# Sync without removing unliked tracks
python main.py --start-date 2024-01-01 --interval 3 --no-remove

# Preview without making any changes
python main.py --start-date 2024-01-01 --interval 3 --dry-run
```

---

## Example output

```
[tracks] Fetching saved tracks from 2016-01-01 onwards ...
[tracks] Found 1296 track(s) saved since 2016-01-01.
[grouping] 11 period(s) to process.

[playlists] Found 99 existing playlist(s).

Processing 'My songs – 2025' (99 liked track(s)) ...
  = Unchanged: 99 track(s) already in sync

Processing 'My songs – 2026' (218 liked track(s)) ...
  V Updated: added=3  removed=1  kept=215  reordered=yes

============================================================
Done!
  Playlists processed  : 11
  Playlists unchanged  : 10
  Playlists updated    : 1
  Playlists created    : 0
  Tracks added         : 3
  Tracks removed       : 1
  Playlists reordered  : 1
============================================================
```

`Unchanged` means the playlist already matched your liked songs exactly — content *and* order — so it was not written to at all. On a typical daily run every playlist is unchanged. `kept` counts tracks that were already there and stayed; `reordered=yes` means existing tracks were moved to restore the Liked Songs order.

---

## How it works

1. **Authentication** (`auth.py`) — spotipy handles OAuth 2.0. On first run a browser window opens; the token is cached in `.cache-<username>` for future runs. In CI mode the refresh token is read from the `REFRESH_TOKEN` environment variable (no browser needed).
2. **Fetch tracks** (`tracks.py`) — paginates `GET /me/tracks`, stopping once it reaches tracks older than `--start-date`.
3. **Group tracks** (`grouping.py`) — assigns each track to a period bucket based on its `saved_at` date and the chosen interval.
4. **Name playlists** (`naming.py`) — builds a human-readable name for each bucket using the chosen style and optional prefix.
5. **Sync playlists** (`playlists.py`) — for each bucket: finds or creates the playlist, reads its current contents in order, and compares them against the desired ordered track list. If they already match exactly, the playlist is left alone and no write is made. If anything differs — a new like, an unlike, or just a track out of position — the playlist is rewritten in a single pass so its contents and order always mirror your Liked Songs. Rewriting the whole list is what makes re-runs idempotent: duplicates are impossible by construction.

---

## Unliked-track removal

By default, if you unlike a song after it was added to a playlist, the next run will **remove it** from the playlist automatically. This keeps your playlists perfectly in sync with your liked songs.

To disable this behaviour, pass `--no-remove`.

---

## GitHub Actions – daily automatic sync

The workflow in `.github/workflows/sync.yml` runs every day at **02:00 UTC** and can also be triggered manually from the **Actions** tab.

### One-time setup

#### Step 1 – Get a refresh token (run once, locally)

Because GitHub Actions cannot open a browser, you need to generate a refresh token on your machine and store it as a secret:

```bash
python generate_token.py
```

A browser will open for Spotify login. After authorising, copy the refresh token printed to your terminal.

#### Step 2 – Add repository secrets

Go to **Settings → Secrets and variables → Actions** in your GitHub repository and add these secrets:

| Secret name | Value |
|---|---|
| `CLIENT_ID` | Your app's Client ID |
| `CLIENT_SECRET` | Your app's Client Secret |
| `REDIRECT_URI` | `http://127.0.0.1:8888/callback` |
| `USERNAME` | Your Spotify username |
| `REFRESH_TOKEN` | The token from `generate_token.py` |

#### Step 3 – Push to GitHub

Commit and push the `.github/` folder. The workflow will run automatically every day, or you can trigger it manually at any time.

---

## Required Spotify scopes

| Scope | Reason |
|---|---|
| `user-library-read` | Read your Liked Songs |
| `playlist-read-private` | Find existing playlists and read their contents |
| `playlist-modify-public` | Create / update public playlists |
| `playlist-modify-private` | Create / update private playlists |
