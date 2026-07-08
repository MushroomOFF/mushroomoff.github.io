import sqlite3
import json
import csv
import os

# Настройки
ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
DB_FOLDER = os.path.join(ROOT_FOLDER, 'Databases/')
DB_BACKUP_FOLDER = os.path.join(DB_FOLDER, 'Backups/')
DB_FILE = os.path.join(DB_FOLDER, 'music_releases.db')
TABLES = ['artists', 'my_releases', 'new_releases', 'soon_releases']

def export_database():
    # Проверяем наличие базы данных
    if not os.path.exists(DB_FILE):
        print(f"Ошибка: база данных '{DB_FILE}' не найдена в текущей папке.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print(f"Начинаю экспорт из {DB_FILE}...\n")

    for table in TABLES:
        json_filename = os.path.join(DB_FOLDER, f"{table}.json")

        try:
            # --- ЧТЕНИЕ ДАННЫХ ИЗ БД (один раз на обе выгрузки) ---
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            data = [dict(zip(columns, row)) for row in rows]

            # ==========================================
            # ЭКСПОРТ В JSON
            # ==========================================
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"[{table}][JSON] Экспортировано {len(data)} записей в '{json_filename}'.")

        except sqlite3.Error as e:
            print(f"[{table}] Ошибка при работе с таблицей: {e}\n")
        except Exception as e:
            print(f"[{table}] Непредвиденная ошибка: {e}\n")

    conn.close()
    print("Экспорт завершен!")

if __name__ == "__main__":
    export_database()