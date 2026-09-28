# Alternative & Metal Releases (AMR)

Personal music-release tracking system: it watches an **artists list** for new
albums on Apple Music (plus Yandex.Music and Zvuk), stores everything in a
SQLite database, publishes a static website with the results and posts updates
to a Telegram channel — automatically, via GitHub Actions.

## Repository structure

```
.
├── Databases/
│   ├── music_releases.db          # Main SQLite DB (artists, my_releases, new_releases, soon_releases, tg_queue)
│   └── Backups/                   # JSON backups of DB tables (source of truth for sync/restore)
│       ├── artists.json           # Personal artists list (name, artist_id, genre, update_type)
│       └── my_releases.json       # Found releases history
├── Python Scripts/                # All automation scripts
│   ├── amr_functions.py           # Shared helpers: logger, Telegram MarkdownV2, send_message, DB backup
│   ├── AMR_LookApp.py             # Scans artists for new releases on Apple Music (iTunes Search API)
│   ├── AMR_NewReleases.py         # Builds new/coming-soon release lists, messages, website JSON
│   ├── AMR_ZVYM.py                # Yandex.Music & Zvuk lookup
│   ├── AMR_LookApp_Errors.py      # Re-checks artists/releases that previously errored
│   ├── AMR_DB_Backup.py           # Exports DB tables to JSON backups
│   ├── AMR_DB_Sync.py             # Imports JSON backups into SQLite (dry-run + confirm)
│   ├── AMR_CoversDownloader.py    # Downloads album covers
│   ├── AMR_CoversRenamer.py       # Renames/formats big cover files
│   ├── server.py                  # Local dev web server for the releases page (localhost:8000)
│   └── requirements.txt           # Python dependencies
├── Website/                       # Static site (GitHub Pages): releases table, coming-soon page, icons
├── website/                       # Legacy site assets (releases.css/js, new_releases.json)
├── .github/workflows/             # CI: weekly update, deploy, ZVYM run, manual trigger
└── status.log                     # Script run log
```

## How it works

1. **`AMR_LookApp.py`** iterates over the `artists` table (your personal
   artists list). For each unprocessed artist it queries the iTunes Search
   API for albums in the selected countries (`us`, `ru`, `jp`), filters out
   already-known releases and inserts new ones into `my_releases`.
2. **`AMR_NewReleases.py`** compiles recent and upcoming releases into
   `new_releases` / `soon_releases`, exports `Website/new_releases.json` and
   `Website/soon_releases.json` for the site, and posts formatted messages to
   Telegram topics.
3. **`AMR_ZVYM.py`** cross-checks releases on Yandex.Music and Zvuk
   (requires `ym_token` / `zv_token`).
4. **GitHub Actions** (`.github/workflows/amr-weekly-update.yml`) runs the
   pipeline every Friday, commits the updated data and deploys the site.
5. **Database ↔ JSON**: `AMR_DB_Backup.py` dumps tables to
   `Databases/Backups/*.json`; `AMR_DB_Sync.py` restores/syncs them back
   (row-by-row, dry-run first).

## Requirements

- Python 3.12+ (CI uses 3.14)
- Dependencies: `pip install -r "Python Scripts/requirements.txt"`
  (`requests`, `pandas`, `python-dotenv`, `yandex-music`)
- Optional secrets (only needed for Telegram/YM/Zvuk features):
  `tg_token`, `tg_channel_id`, `tg_logger_id`, `ym_token`, `zv_token`, `admin_token`

## Quick start

```bash
git clone <your-fork-url> && cd mushroomoff.github.io
python3 -m venv .venv && source .venv/bin/activate
pip install -r "Python Scripts/requirements.txt"
```

Then follow the **[Local Run Tutorial](docs/LOCAL_RUN_TUTORIAL.md)** to set up
the project on your own machine with **your own personal artists list**.

## Scripts reference

| Script | Purpose | Needs `.env` |
|---|---|---|
| `AMR_LookApp.py` | Find new releases for artists (Apple Music) | optional (Telegram logging) |
| `AMR_NewReleases.py` | Build release lists + website JSON + Telegram posts | yes (`tg_*`, `ym_token`, `zv_token`) |
| `AMR_ZVYM.py` | Yandex.Music / Zvuk lookup | yes |
| `AMR_LookApp_Errors.py` | Retry artists that returned errors | no |
| `AMR_DB_Backup.py` | Export SQLite tables → JSON | no |
| `AMR_DB_Sync.py` | Import JSON → SQLite (`--db`, `--json-dir`, `--dry-run`) | no |
| `AMR_CoversDownloader.py` | Download covers for new releases | no |
| `AMR_CoversRenamer.py` | Rename large cover files | no |
| `server.py` | Local web server for editing/publishing releases | yes |

> **Note:** most scripts contain a hard-coded `ROOT_FOLDER` pointing to the
> author's machine. When running locally, edit it to your repository path —
> see the tutorial.

## License

Private/personal project — all rights reserved by the author.
