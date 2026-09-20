#!/usr/bin/env python3
"""
sync_json_to_sqlite.py

Synchronize SQLite tables from per-table JSON backup files.

Rules:
- JSON file name without .json is the SQLite table name.
- row_id is the unique row identifier.
- If row_id exists in DB: compare cells and update changed cells from JSON.
- If row_id does not exist in DB: insert row from JSON.
- Rows existing only in DB are not deleted.

Workflow:
- Phase 1: DRY-RUN (shows planned changes, DB is not modified).
- Then the script asks: apply changes? (y/n)
- Only answer "y" runs Phase 2 (real changes). Any other answer = no changes.

Usage examples:

    # Normal run: dry-run first, then y/n confirmation
    python sync_json_to_sqlite.py --db my_database.db --json-dir .

    # Dry-run only, no confirmation prompt
    python sync_json_to_sqlite.py --db my_database.db --json-dir . --dry-run

    # With automatic DB backup before applying changes
    python sync_json_to_sqlite.py --db my_database.db --json-dir . --backup
"""

import argparse
import json
import math
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def quote_ident(name: str) -> str:
    """Quote an SQL identifier."""
    return '"' + str(name).replace('"', '""') + '"'


def normalize_key(key: Any) -> str:
    """Normalize JSON/DB column names."""
    return str(key).strip().lower()


def normalize_row_id(value: Any) -> Any:
    """Normalize row_id value."""
    if value is None:
        return None

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, float) and value.is_integer():
        return int(value)

    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return ""

        try:
            return int(s)
        except ValueError:
            pass

        try:
            f = float(s)
            if f.is_integer():
                return int(f)
        except ValueError:
            pass

        return s

    return value


def clean_value(value: Any, strip_strings: bool) -> Any:
    """
    Normalize values before comparison or writing to DB.

    - bool -> int
    - dict/list -> JSON string
    - strings are stripped by default
    """
    if isinstance(value, bool):
        return int(value)

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    if strip_strings and isinstance(value, str):
        return value.strip()

    return value


def normalize_row(raw: Dict[str, Any], strip_strings: bool, source: str = "row") -> Dict[str, Any]:
    """Normalize one JSON object into a DB-ready dict."""
    row = {}

    for key, value in raw.items():
        normalized_key = normalize_key(key)
        if not normalized_key:
            continue
        row[normalized_key] = clean_value(value, strip_strings)

    if "row_id" not in row:
        raise RuntimeError(f"{source} has no 'row_id' field")

    row["row_id"] = normalize_row_id(row["row_id"])

    if row["row_id"] is None or row["row_id"] == "":
        raise RuntimeError(f"{source} has empty 'row_id'")

    return row


def load_json_rows(path: Path, strip_strings: bool) -> List[Dict[str, Any]]:
    """Load rows from JSON file."""
    try:
        text = path.read_text(encoding="utf-8-sig")
        data = json.loads(text)
    except Exception as exc:
        raise RuntimeError(f"Cannot read JSON file {path}: {exc}") from exc

    if isinstance(data, dict):
        if isinstance(data.get("rows"), list):
            data = data["rows"]
        else:
            lists = [v for v in data.values() if isinstance(v, list)]
            if len(lists) == 1:
                data = lists[0]
            else:
                data = [data]

    if not isinstance(data, list):
        raise RuntimeError(f"{path}: top-level JSON structure must be a list of row objects")

    rows = []
    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"{path}: item {i} is not a JSON object")
        rows.append(normalize_row(item, strip_strings, source=f"{path.name}, item {i}"))

    return rows


def values_equal(a: Any, b: Any) -> bool:
    """Compare DB value and JSON value (tolerant for common SQLite cases)."""
    if a is b:
        return True

    if a is None or b is None:
        return a is None and b is None

    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)

    if isinstance(a, int) and isinstance(b, int):
        return a == b

    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        try:
            return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-12)
        except Exception:
            return False

    if isinstance(a, str) and isinstance(b, (int, float)):
        try:
            return math.isclose(float(a.strip()), float(b), rel_tol=1e-9, abs_tol=1e-12)
        except Exception:
            return False

    if isinstance(b, str) and isinstance(a, (int, float)):
        try:
            return math.isclose(float(a), float(b.strip()), rel_tol=1e-9, abs_tol=1e-12)
        except Exception:
            return False

    if isinstance(a, bytes) and isinstance(b, str):
        try:
            return a.decode("utf-8") == b
        except UnicodeDecodeError:
            return False

    if isinstance(b, bytes) and isinstance(a, str):
        try:
            return b.decode("utf-8") == a
        except UnicodeDecodeError:
            return False

    return a == b


def short_repr(value: Any, limit: int = 80) -> str:
    """Short representation for logging."""
    s = repr(value)
    if len(s) <= limit:
        return s
    return s[:limit] + "..."


def get_actual_table_name(conn: sqlite3.Connection, table: str) -> Optional[str]:
    """Return actual table name from SQLite if it exists."""
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND lower(name) = lower(?)
        """,
        (table,),
    ).fetchone()

    if row is None:
        return None

    return row["name"]


def get_table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    """Return column names for table."""
    rows = conn.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()
    return [row["name"] for row in rows]


def make_column_lookup(columns: List[str]) -> Dict[str, str]:
    """Normalized column lookup: lowercase/stripped name -> actual DB column name."""
    lookup = {}
    for column in columns:
        lookup[normalize_key(column)] = column
    return lookup


def fetch_existing(
    conn: sqlite3.Connection,
    table: str,
    row_id_column: str,
    row_id: Any,
) -> Optional[Dict[str, Any]]:
    """Fetch one existing row by row_id."""
    sql = f"""
        SELECT *
        FROM {quote_ident(table)}
        WHERE {quote_ident(row_id_column)} = ?
        LIMIT 2
    """

    rows = conn.execute(sql, (row_id,)).fetchall()

    if len(rows) == 0:
        return None

    if len(rows) > 1:
        raise RuntimeError(
            f"Table '{table}' has more than one row with row_id={row_id!r}. "
            "row_id must be unique."
        )

    return dict(rows[0])


def insert_row(conn: sqlite3.Connection, table: str, data: Dict[str, Any]) -> None:
    """Insert one row."""
    if not data:
        raise RuntimeError("Cannot insert empty row")

    columns = list(data.keys())
    placeholders = ", ".join(["?"] * len(columns))
    column_sql = ", ".join(quote_ident(c) for c in columns)

    sql = f"""
        INSERT INTO {quote_ident(table)} ({column_sql})
        VALUES ({placeholders})
    """

    conn.execute(sql, [data[c] for c in columns])


def update_row(
    conn: sqlite3.Connection,
    table: str,
    row_id_column: str,
    row_id: Any,
    updates: Dict[str, Any],
) -> None:
    """Update one row by row_id."""
    if not updates:
        return

    set_sql = ", ".join(f"{quote_ident(column)} = ?" for column in updates)

    sql = f"""
        UPDATE {quote_ident(table)}
        SET {set_sql}
        WHERE {quote_ident(row_id_column)} = ?
    """

    params = list(updates.values()) + [row_id]
    conn.execute(sql, params)


def create_table_from_rows(
    conn: sqlite3.Connection,
    table: str,
    rows: List[Dict[str, Any]],
    dry_run: bool = False,
) -> List[str]:
    """Create missing table using JSON rows (non-row_id columns as TEXT)."""
    if not rows:
        raise RuntimeError(f"Cannot create table '{table}' from empty JSON row list")

    row_id_type = "INTEGER"
    for row in rows:
        if not isinstance(row.get("row_id"), int):
            row_id_type = "TEXT"
            break

    ordered_columns = []
    seen = set()

    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                ordered_columns.append(key)

    if "row_id" not in seen:
        raise RuntimeError(f"Cannot create table '{table}': no row_id field found")

    ordered_columns.remove("row_id")
    ordered_columns.insert(0, "row_id")

    column_defs = [f"{quote_ident('row_id')} {row_id_type} PRIMARY KEY"]

    for column in ordered_columns:
        if column == "row_id":
            continue
        column_defs.append(f"{quote_ident(column)} TEXT")

    sql = f"""
        CREATE TABLE {quote_ident(table)} (
            {', '.join(column_defs)}
        )
    """

    if dry_run:
        print(f"  [DRY-RUN] Would create table '{table}'")
    else:
        conn.execute(sql)
        print(f"  Created table '{table}'")

    return ordered_columns


def sync_table(
    conn: sqlite3.Connection,
    table: str,
    json_path: Path,
    args: argparse.Namespace,
    dry_run: bool,
) -> Dict[str, int]:
    """Synchronize one table from one JSON file."""
    rows = load_json_rows(json_path, args.strip_values)

    mode = "[DRY-RUN] " if dry_run else ""
    print(f"\n=== {mode}Table '{table}' from {json_path.name}: {len(rows)} JSON row(s) ===")

    stats = {
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
    }

    if not rows:
        return stats

    seen_row_ids = set()
    for row in rows:
        row_id = row["row_id"]
        if row_id in seen_row_ids:
            raise RuntimeError(f"Duplicate row_id {row_id!r} in {json_path.name}")
        seen_row_ids.add(row_id)

    actual_table_name = get_actual_table_name(conn, table)
    table_exists = actual_table_name is not None
    sql_table = actual_table_name if table_exists else table

    if table_exists:
        db_columns = get_table_columns(conn, sql_table)
    else:
        if not args.create_missing_tables:
            raise RuntimeError(
                f"Table '{table}' does not exist in DB. "
                "Use --create-missing-tables if you want to create it automatically."
            )

        db_columns = create_table_from_rows(
            conn=conn,
            table=sql_table,
            rows=rows,
            dry_run=dry_run,
        )

        table_exists = not dry_run

    column_lookup = make_column_lookup(db_columns)

    if "row_id" not in column_lookup:
        raise RuntimeError(f"Table '{sql_table}' does not have a row_id column")

    row_id_column = column_lookup["row_id"]

    all_json_fields = set()
    for row in rows:
        all_json_fields.update(key for key in row.keys() if key != "row_id")

    missing_fields = sorted(
        {
            field
            for field in all_json_fields
            if field not in column_lookup
            and any(row.get(field) is not None for row in rows)
        }
    )

    if missing_fields:
        if args.add_missing_columns:
            prefix = "[DRY-RUN] Would add" if dry_run else "Adding"
            print(f"  {prefix} missing columns: {', '.join(missing_fields)}")

            for field in missing_fields:
                if table_exists and not dry_run:
                    sql = f"""
                        ALTER TABLE {quote_ident(sql_table)}
                        ADD COLUMN {quote_ident(field)} TEXT
                    """
                    conn.execute(sql)

                column_lookup[field] = field
                db_columns.append(field)

        elif args.ignore_extra_json_fields:
            print(f"  Ignoring extra JSON fields: {', '.join(missing_fields)}")

        else:
            raise RuntimeError(
                f"JSON file {json_path.name} contains fields that do not exist "
                f"in table '{sql_table}': {', '.join(missing_fields)}. "
                "Use --add-missing-columns to add them automatically, or "
                "--ignore-extra-json-fields to ignore them."
            )

    for row in rows:
        row_id = row["row_id"]

        existing = None
        if table_exists:
            existing = fetch_existing(
                conn=conn,
                table=sql_table,
                row_id_column=row_id_column,
                row_id=row_id,
            )

        if existing is None:
            data = {row_id_column: row_id}

            for key, value in row.items():
                if key == "row_id":
                    continue

                column = column_lookup.get(key)

                if column is None:
                    if value is None or args.ignore_extra_json_fields:
                        continue
                    raise RuntimeError(
                        f"Field '{key}' from JSON is not present in table '{sql_table}'"
                    )

                data[column] = value

            if dry_run:
                print(f"  [DRY-RUN] INSERT row_id={row_id!r}")
                if args.verbose:
                    print(f"    values: {data}")
            else:
                insert_row(conn, sql_table, data)
                print(f"  INSERT row_id={row_id!r}")

            stats["inserted"] += 1
            continue

        updates = {}

        for key, new_value in row.items():
            if key == "row_id":
                continue

            column = column_lookup.get(key)

            if column is None:
                if new_value is None or args.ignore_extra_json_fields:
                    continue
                raise RuntimeError(
                    f"Field '{key}' from JSON is not present in table '{sql_table}'"
                )

            old_value = clean_value(existing.get(column), args.strip_values)

            if not values_equal(old_value, new_value):
                updates[column] = new_value

                if args.verbose:
                    print(
                        f"    row_id={row_id!r}, column '{column}': "
                        f"{short_repr(old_value)} -> {short_repr(new_value)}"
                    )

        if updates:
            if dry_run:
                print(
                    f"  [DRY-RUN] UPDATE row_id={row_id!r}, "
                    f"columns: {', '.join(updates.keys())}"
                )
                if args.verbose:
                    for column, value in updates.items():
                        print(f"    {column} = {short_repr(value)}")
            else:
                update_row(
                    conn=conn,
                    table=sql_table,
                    row_id_column=row_id_column,
                    row_id=row_id,
                    updates=updates,
                )
                print(f"  UPDATE row_id={row_id!r}, columns: {', '.join(updates.keys())}")

            stats["updated"] += 1
        else:
            if args.verbose:
                print(f"  {'[DRY-RUN] ' if dry_run else ''}UNCHANGED row_id={row_id!r}")

            stats["unchanged"] += 1

    print(
        f"  {mode}Summary: "
        f"inserted={stats['inserted']}, "
        f"updated={stats['updated']}, "
        f"unchanged={stats['unchanged']}"
    )

    return stats


def run_sync_phase(
    conn: sqlite3.Connection,
    table_file_pairs: List[Any],
    args: argparse.Namespace,
    dry_run: bool,
) -> Dict[str, int]:
    """Run full sync over all tables in one transaction. Dry-run rolls back."""
    totals = {
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
    }

    conn.execute("BEGIN")

    try:
        for table, json_path in table_file_pairs:
            stats = sync_table(conn, table, json_path, args, dry_run)
            for key in totals:
                totals[key] += stats.get(key, 0)

        if dry_run:
            conn.execute("ROLLBACK")
        else:
            conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise

    return totals


def ask_yes_no(prompt: str) -> bool:
    """Return True only if user answers 'y'/'Y'. Anything else (or no stdin) = False."""
    try:
        answer = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer == "y"


def backup_database(db_path: Path) -> Path:
    """Create timestamped copy of DB file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(f"{db_path.name}.backup_{timestamp}")
    shutil.copy2(db_path, backup_path)
    print(f"Backup created: {backup_path}")
    return backup_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync SQLite DB tables from per-table JSON backup files. "
                    "Always performs a dry-run first, then asks for confirmation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--db", required=True, help="Path to SQLite database file")
    parser.add_argument(
        "--json-dir",
        nargs="+",
        default=["."],
        metavar="DIR",
        help="One or more directories containing JSON files named as tables",
    )
    parser.add_argument("--tables", nargs="*", metavar="TABLE",
                        help="Sync only these tables. If omitted, all *.json files in --json-dir are used.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Perform only the dry-run phase and exit without confirmation prompt")
    parser.add_argument("--backup", action="store_true",
                        help="Create timestamped backup of DB file right before applying changes")
    parser.add_argument("--create-missing-tables", action="store_true",
                        help="Create tables if they do not exist in DB")
    parser.add_argument("--add-missing-columns", action="store_true",
                        help="Add missing columns to existing tables if JSON has extra fields")
    parser.add_argument("--ignore-extra-json-fields", action="store_true",
                        help="Ignore JSON fields that do not exist in DB instead of raising error")
    parser.add_argument("--verbose", action="store_true",
                        help="Print changed values and unchanged rows")
    parser.add_argument("--no-strip-values", dest="strip_values", action="store_false",
                        help="Do not strip leading/trailing whitespace from string values")

    parser.set_defaults(strip_values=True)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        sys.exit(f"ERROR: database file not found: {db_path}")

    json_dirs = []
    for directory in args.json_dir:
        d = Path(directory)
        if not d.is_dir():
            sys.exit(f"ERROR: JSON directory not found: {d}")
        json_dirs.append(d)

    table_file_pairs = []

    if args.tables:
        for table in args.tables:
            if table.endswith(".json"):
                table = table[:-5]

            json_path = None
            for d in json_dirs:
                candidate = d / f"{table}.json"
                if candidate.is_file():
                    json_path = candidate
                    break

            if json_path is None:
                dirs_list = ", ".join(str(d) for d in json_dirs)
                sys.exit(f"ERROR: JSON file for table '{table}' not found in: {dirs_list}")

            table_file_pairs.append((table, json_path))
    else:
        seen_tables = {}
        for d in json_dirs:
            for path in sorted(d.glob("*.json")):
                if not path.is_file():
                    continue

                table = path.stem
                if table in seen_tables:
                    sys.exit(
                        f"ERROR: table '{table}' has JSON files in two directories: "
                        f"{seen_tables[table]} and {path}. Keep only one."
                    )
                seen_tables[table] = path
                table_file_pairs.append((table, path))

        table_file_pairs.sort(key=lambda pair: pair[0])

    if not table_file_pairs:
        sys.exit(f"ERROR: no JSON files found in: {', '.join(str(d) for d in json_dirs)}")

    print("JSON sources:")
    for table, path in table_file_pairs:
        print(f"  {table} -> {path}")

    # ---------------- Phase 1: DRY-RUN ----------------
    print("=" * 60)
    print("PHASE 1: DRY-RUN (database will NOT be modified)")
    print("=" * 60)

    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row

    try:
        dry_totals = run_sync_phase(conn, table_file_pairs, args, dry_run=True)
    except Exception as exc:
        conn.close()
        print(f"ERROR during dry-run: {exc}", file=sys.stderr)
        sys.exit(1)

    conn.close()

    print(
        "\nDry-run summary: "
        f"would insert={dry_totals['inserted']}, "
        f"would update={dry_totals['updated']}, "
        f"unchanged={dry_totals['unchanged']}"
    )

    if args.dry_run:
        print("--dry-run specified: exiting without confirmation prompt.")
        return

    changes_needed = dry_totals["inserted"] + dry_totals["updated"]
    if changes_needed == 0:
        print("Nothing to change. Database is already in sync with JSON files.")
        return

    # ---------------- Confirmation ----------------
    print()
    if not ask_yes_no("Apply these changes to the database? [y/N]: "):
        print("Cancelled by user. Database was NOT modified.")
        return

    if args.backup:
        backup_database(db_path)

    # ---------------- Phase 2: APPLY ----------------
    print()
    print("=" * 60)
    print("PHASE 2: APPLYING CHANGES")
    print("=" * 60)

    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row

    try:
        real_totals = run_sync_phase(conn, table_file_pairs, args, dry_run=False)
    except Exception as exc:
        conn.close()
        print(f"ERROR while applying changes: {exc}. All changes rolled back.", file=sys.stderr)
        sys.exit(1)

    conn.close()

    print(
        "\nDone. Changes committed.\n"
        "Total: "
        f"inserted={real_totals['inserted']}, "
        f"updated={real_totals['updated']}, "
        f"unchanged={real_totals['unchanged']}"
    )


if __name__ == "__main__":
    main()