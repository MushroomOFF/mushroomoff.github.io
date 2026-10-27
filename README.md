# Alternative & Metal Releases (AMR)

Personal music-release tracking system: it watches an **artists list** for new
albums on Apple Music (plus Yandex.Music and Zvuk), stores everything in a
SQLite database, publishes a static website with the results and posts updates
to a Telegram channel — automatically, via GitHub Actions.

## Repository structure

```
.
├── databases/
│   ├── music_releases.db          # Main SQLite DB (artists, my_releases, new_releases, soon_releases, tg_queue)
│   └── backups/                   # JSON backups of DB tables (source of truth for sync/restore)
│       ├── artists.json           # Personal artists list (name, artist_id, genre, update_type)
│       └── my_releases.json       # Found releases history
├── scripts/                # All automation scripts
│   ├── amr_functions.py           # Shared helpers: logger, Telegram MarkdownV2, send_message, DB backup
│   ├── lookapp.py             # Scans artists for new releases on Apple Music (iTunes Search API)
│   ├── new_releases.py         # Builds new/coming-soon release lists, messages, website JSON
│   ├── zvym_links.py                # Yandex.Music & Zvuk lookup
│   ├── lookapp_errors.py      # Re-checks artists/releases that previously errored
│   ├── db_backup.py           # Exports DB tables to JSON backups
│   ├── db_sync.py             # Imports JSON backups into SQLite (dry-run + confirm)
│   ├── covers_downloader.py    # Downloads album covers
│   ├── covers_renamer.py       # Renames/formats big cover files
│   ├── server.py                  # Local dev web server for the releases page (localhost:8000)
│   └── requirements.txt           # Python dependencies
├── website/                       # Static site (GitHub Pages): releases table, coming-soon page, icons
├── .github/workflows/             # CI: weekly update, deploy, ZVYM run, manual trigger
└── status.log                     # Script run log
```

## How it works

1. **`lookapp.py`** iterates over the `artists` table (your personal
   artists list). For each unprocessed artist it queries the iTunes Search
   API for albums in the selected countries (`us`, `ru`, `jp`), filters out
   already-known releases and inserts new ones into `my_releases`.
2. **`new_releases.py`** compiles recent and upcoming releases into
   `new_releases` / `soon_releases`, exports `website/new_releases.json` and
   `website/soon_releases.json` for the site, and posts formatted messages to
   Telegram topics.
3. **`zvym_links.py`** cross-checks releases on Yandex.Music and Zvuk
   (requires `ym_token` / `zv_token`).
4. **GitHub Actions** (`.github/workflows/amr-weekly-update.yml`) runs the
   pipeline every Friday, commits the updated data and deploys the site.
5. **Database ↔ JSON**: `db_backup.py` dumps tables to
   `databases/backups/*.json`; `db_sync.py` restores/syncs them back
   (row-by-row, dry-run first).

## Requirements

- Python 3.12+ (CI uses 3.14)
- Dependencies: `pip install -r "scripts/requirements.txt"`
  (`requests`, `pandas`, `python-dotenv`, `yandex-music`)
- Optional secrets (only needed for Telegram/YM/Zvuk features):
  `tg_token`, `tg_channel_id`, `tg_logger_id`, `ym_token`, `zv_token`, `admin_token`

## Quick start

```bash
git clone <your-fork-url> && cd mushroomoff.github.io
python3 -m venv .venv && source .venv/bin/activate
pip install -r "scripts/requirements.txt"
```

Then follow the **[Local Run Tutorial](docs/LOCAL_RUN_TUTORIAL.md)** to set up
the project on your own machine with **your own personal artists list**.

## Scripts reference

| Script | Purpose | Needs `.env` |
|---|---|---|
| `lookapp.py` | Find new releases for artists (Apple Music) | optional (Telegram logging) |
| `new_releases.py` | Build release lists + website JSON + Telegram posts | yes (`tg_*`, `ym_token`, `zv_token`) |
| `zvym_links.py` | Yandex.Music / Zvuk lookup | yes |
| `lookapp_errors.py` | Retry artists that returned errors | no |
| `db_backup.py` | Export SQLite tables → JSON | no |
| `db_sync.py` | Import JSON → SQLite (`--db`, `--json-dir`, `--dry-run`) | no |
| `covers_downloader.py` | Download covers for new releases | no |
| `covers_renamer.py` | Rename large cover files | no |
| `server.py` | Local web server for editing/publishing releases | yes |

> **Note:** most scripts contain a hard-coded `ROOT_FOLDER` pointing to the
> author's machine. When running locally, edit it to your repository path —
> see the tutorial.

## License

Private/personal project — all rights reserved by the author.
