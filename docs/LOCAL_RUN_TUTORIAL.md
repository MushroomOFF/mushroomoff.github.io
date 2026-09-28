# Tutorial: Local Personal Run with Your Own Artists List

This tutorial shows how to run the AMR pipeline **on your own machine**, for
**your own personal artists list**, without touching the author's Telegram
channel or GitHub Actions. By the end you will have a fresh SQLite database,
your artists in it, and new releases found automatically from Apple Music.

> Difficulty: beginner-friendly. All commands are shown for macOS/Linux;
> on Windows use `py -3` instead of `python3` and `\` paths.

---

## Step 0 — What you need

- Python 3.12+ (`python3 --version`)
- Git
- Internet access (iTunes Search API is used — no Apple account needed)
- *(Optional)* Telegram bot token + channel/chat IDs, Yandex.Music and Zvuk
  tokens — only if you want notifications and streaming-service lookup.
  **Everything works without them.**

## Step 1 — Clone the repository

```bash
git clone <repo-url> amr
cd amr
```

## Step 2 — Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r "Python Scripts/requirements.txt"
```

## Step 3 — Point the scripts at YOUR folder

Most scripts hard-code the author's path. Replace it with your repo path.

Open each file listed below in `Python Scripts/` and change the value of
`ROOT_FOLDER`:

```python
# BEFORE (author's machine):
ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'

# AFTER (your machine), e.g.:
ROOT_FOLDER = '/home/you/projects/amr/'
# or make it portable (recommended):
ROOT_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
```

Files to edit:

- [ ] `AMR_LookApp.py`
- [ ] `AMR_NewReleases.py`
- [ ] `AMR_ZVYM.py`
- [ ] `AMR_LookApp_Errors.py`
- [ ] `AMR_CoversDownloader.py` (also `COVERS_FOLDER` if you download covers)
- [ ] `AMR_CoversRenamer.py` (also `ORIGINAL_COVERS_FOLDER`)
- [ ] `server.py`

`AMR_DB_Backup.py` and `AMR_DB_Sync.py` already compute paths relative to the
script location — no changes needed.

## Step 4 — Create `.env` (optional but recommended)

Create a `.env` file in the repository root (it is git-ignored). Even if you
skip Telegram/YM/Zvuk, create it with empty values so scripts that read
`os.environ[...]` don't crash:

```dotenv
# Telegram (create a bot via @BotFather; IDs from @userinfobot or Bot API getUpdates)
tg_token=
tg_channel_id=
tg_logger_id=
# Streaming services (browser cookies after login)
ym_token=
zv_token=
# Local web server admin
admin_token=
```

If you leave the Telegram values empty, `amr_functions.send_message()` simply
skips sending (see `status.log`: *"Message not sent! No TOKEN or CHAT_ID"*),
and the scripts keep working locally.

To run `AMR_NewReleases.py` / `AMR_ZVYM.py` fully, either fill in real tokens
or temporarily change their `os.environ['key']` reads to
`os.environ.get('key')`.

## Step 5 — Start with a clean database

The repo ships with the author's `Databases/music_releases.db`. For a personal
run, remove it (the table schema will be recreated automatically):

```bash
rm Databases/music_releases.db
```

> Keep `Databases/Backups/*.json` only if you want the author's data as a
> starting point — otherwise delete them too; they are just JSON exports.

## Step 6 — Build YOUR personal artists list

Artists live in the `artists` table. The easiest way to fill it is SQL:

```bash
sqlite3 Databases/music_releases.db <<'SQL'
CREATE TABLE IF NOT EXISTS artists (
    row_id INTEGER,
    artist TEXT,
    artist_id INTEGER,
    artist_genre TEXT,
    update_type INTEGER,
    update_date TEXT,
    PRIMARY KEY(row_id AUTOINCREMENT)
);
INSERT INTO artists (artist, artist_id, artist_genre, update_type, update_date) VALUES
    ('Power Paladin', 1540478964, 'Power Metal',  2, NULL),
    ('Mob Rules',     286753887,  'Heavy Metal',  2, NULL),
    ('My New Band',   123456789,  'Rock',         1, NULL);
SQL
```

Field meanings:

| Field | Meaning |
|---|---|
| `artist` | Display name of the artist |
| `artist_id` | Apple Music **artist ID** (see "Finding an artist ID" below); must be `> 0` |
| `artist_genre` | Free text label |
| `update_type` | Priority tier used by LookApp: `2` = checked weekly in CI & interactive filters, `1` = regular, `0` = only when you choose "ALL" |
| `update_date` | `NULL` = needs checking; a timestamp = last processed date |

### Finding an artist ID

Open the artist's page on Apple Music and copy the number from the URL:

```
https://music.apple.com/us/artist/power-paladin/1540478964
                                            ^^^^^^^^^^ artist_id
```

Or search via the public API:

```bash
curl -s "https://itunes.apple.com/search?term=power+paladin&entity=musicArtist&limit=3" \
  | python3 -c "import json,sys; [print(r['artistName'], r['artistId']) for r in json.load(sys.stdin)['results']]"
```

### Alternative: manage the list in JSON

You can also keep your list as `Databases/Backups/artists.json` (same fields,
see the shipped example) and import it into SQLite:

```bash
cd "Python Scripts"
python AMR_DB_Sync.py --db ../Databases/music_releases.db --json-dir ../Databases/Backups
# dry-run is shown first — answer y to apply
```

## Step 7 — First scan: find new releases

Run LookApp interactively:

```bash
cd "Python Scripts"
python AMR_LookApp.py
```

It will ask:

```
Choose countries to check: [us, ru, jp] / 2:[us, ru] / jp:[jp]
Choose artists to check:   Enter:[2,1] / 2 / 1 / 0:! ALL [2,1,0]
```

Pick your countries and artist tiers. The script walks through every artist
with `update_date IS NULL`, queries iTunes for their albums, skips releases
already in `my_releases`, inserts genuinely new ones, prints progress, and
writes results to `status.log` in the repo root.

Typical statuses per artist: `N new records`, `EMPTY` (not available in that
country store), `ERROR (50x)` (API hiccup — rerun `AMR_LookApp_Errors.py`
later to retry).

## Step 8 — Verify your data

```bash
sqlite3 ../Databases/music_releases.db \
  "SELECT main_artist, album, release_date FROM my_releases ORDER BY release_date DESC LIMIT 10;"
```

Back up your personal DB + artists list to JSON at any time:

```bash
python AMR_DB_Backup.py
```

## Step 9 — Website & local server (optional)

To serve the releases page locally with editing/publishing support:

```bash
python server.py
# open http://localhost:8000/index.html
```

Without a filled `admin_token`/Telegram config, publishing actions are logged
but messages are not sent — the site still renders from
`Website/new_releases.json`.

For a purely static preview you can also just open `Website/index.html` via
any local static server, e.g. `python3 -m http.server 8000 -d Website`.

## Step 10 — Make it a habit

- Re-run `AMR_LookApp.py` whenever you want (weekly matches the CI cadence).
  Reset progress for a full re-scan by setting `update_date = NULL` again:
  ```sql
  UPDATE artists SET update_date = NULL WHERE update_type IN (1, 2);
  ```
- Add new favorite artists anytime (Step 6) — next run picks them up.
- Your fork's GitHub Actions will NOT run these scripts against your private
  data unless you add the secrets in repo Settings → Secrets — until then the
  cloud pipeline is inert and everything stays local. ✅

## Troubleshooting

| Symptom | Fix |
|---|---|
| `FileNotFoundError` on `Databases/...` | Wrong `ROOT_FOLDER` — redo Step 3 (must end with `/`) |
| `KeyError: 'tg_token'` | Missing `.env` (Step 4) or strict `os.environ[...]` access — use `.get()` |
| `Bad ID` in log | `artist_id` ≤ 0 or wrong — fix in `artists` table |
| Many `ERROR (502/503)` | Apple API throttling — wait and run `AMR_LookApp_Errors.py` |
| Nothing found for an artist | Artist has no albums in that country store (`EMPTY`) or all releases already known |

Happy listening! 🤘
