import sqlite3
import json
import os

# Скрипт лежит в ./Python Scripts/AMR_DB_Backup.py
# Поэтому корень проекта — это родительская папка для Python Scripts
SCRIPT_FOLDER = os.path.dirname(os.path.abspath(__file__))
ROOT_FOLDER = os.path.dirname(SCRIPT_FOLDER)

DB_FOLDER = os.path.join(ROOT_FOLDER, 'Databases')
DB_BACKUP_FOLDER = os.path.join(DB_FOLDER, 'Backups')
WEBSITE_FOLDER = os.path.join(ROOT_FOLDER, 'Website')

DB_FILE = os.path.join(DB_FOLDER, 'music_releases.db')

TABLES = [
    'artists',
    'my_releases',
    'new_releases',
    'soon_releases'
]

TABLE_EXPORT_FOLDERS = {
    'artists': DB_BACKUP_FOLDER,
    'my_releases': DB_BACKUP_FOLDER,
    'new_releases': WEBSITE_FOLDER,
    'soon_releases': DB_BACKUP_FOLDER,
}

def get_display_path(abs_path, root):
    """Возвращает путь относительно корня проекта с '/' в начале."""
    rel_path = os.path.relpath(abs_path, root)
    return '/' + rel_path.replace(os.sep, '/')

def export_database():
    # Проверяем наличие базы данных
    if not os.path.exists(DB_FILE):
        print(f"Ошибка: база данных '{get_display_path(DB_FILE, ROOT_FOLDER)}' не найдена.")
        return

    os.makedirs(DB_BACKUP_FOLDER, exist_ok=True)
    os.makedirs(WEBSITE_FOLDER, exist_ok=True)

    conn = sqlite3.connect(DB_FILE)

    try:
        cursor = conn.cursor()
        print(f"Начинаю экспорт из {get_display_path(DB_FILE, ROOT_FOLDER)}...\n")

        for table in TABLES:
            target_folder = TABLE_EXPORT_FOLDERS.get(table, DB_BACKUP_FOLDER)
            json_filename = os.path.join(target_folder, f"{table}.json")

            try:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                data = [dict(zip(columns, row)) for row in rows]

                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)

                print(f"[{table}] Экспортировано {len(data)} записей в '{get_display_path(json_filename, ROOT_FOLDER)}'")

            except sqlite3.Error as e:
                print(f"[{table}] Ошибка при работе с таблицей: {e}\n")

            except Exception as e:
                print(f"[{table}] Непредвиденная ошибка: {e}\n")

    finally:
        conn.close()

    print("\nЭкспорт завершен!")


if __name__ == "__main__":
    export_database()