import datetime
import os
import requests
import sqlite3
import traceback
import amr_functions as amr

# ================= CONSTANTS & VARIABLES =================
SCRIPT_NAME = "Covers Downloader"
VERSION = "2.026.07"

ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
DB_FOLDER = os.path.join(ROOT_FOLDER, 'Databases/')
DB_FILE = os.path.join(DB_FOLDER, 'music_releases.db')
COVERS_FOLDER = os.path.join(ROOT_FOLDER, 'Covers/Fresh Covers to Check/')

# ================= FUNCTIONS =================
def clean_folder_name(text: str) -> str:
    forbidden = set('()/:.')
    result = []
    # Проходим по исходному тексту, чтобы соседи не "съехали" во время обработки
    for i, char in enumerate(text):
        if char in forbidden:
            left = text[i-1] if i > 0 else None
            right = text[i+1] if i < len(text) - 1 else None
            # Заменяем на пробел только если символ окружён не-пробелами с обеих сторон
            if left is not None and right is not None and left != ' ' and right != ' ':
                result.append(' ')
            # В противном случае (начало/конец строки или рядом уже есть пробел) символ просто удаляется
        else:
            result.append(char)
    # Собираем строку, схлопываем множественные пробелы в один и убираем пробелы по краям
    return ' '.join(''.join(result).split())


def is_jp_chars(text: str):
    # Проверяем каждый символ по его Unicode-коду
    if any(0x3040 <= ord(ch) <= 0x309F or  # Хирагана
           0x30A0 <= ord(ch) <= 0x30FF or  # Катакана
           0x4E00 <= ord(ch) <= 0x9FFF     # Кандзи (CJK Unified Ideographs)
           for ch in text):
        return True
    return False


def replace_symbols(text_line):
    """Replacing unused characters in file names and folder paths"""
    symbols_to_replace = '\\/*:?<>|`"'
    for symbol in symbols_to_replace:
        text_line = text_line.replace(symbol, '_')
    return text_line


def image_download(file_name, folder, link):
    """Image downloading"""
    file_name = replace_symbols(file_name)
    folder = replace_symbols(folder)
    folder_path = os.path.join(COVERS_FOLDER, folder)

    os.makedirs(folder_path, exist_ok=True)

    response = requests.get(link)
    if response.status_code == 200:
        with open(os.path.join(folder_path, f"{file_name}.jpg"), "wb") as file:
            file.write(response.content)
    else:
        with open(os.path.join(folder_path, f"{file_name}.txt"), "wb") as file:
            file.write(response.content)


def count_covers_to_download():
    """Count covers to download"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(row_id) FROM my_releases 
            WHERE cover_download_date IS NULL
        ''')
        result = cursor.fetchone()
        conn.close()
        if result:
            return int(result[0])
        return None
    except Exception as e:
        print(f'Error counting covers to donwnload: {e}')
        traceback.print_exc()
        return None


def get_cover_to_download():
    """Get cover to download"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT row_id, main_artist, artist, album, release_date, cover_link  FROM my_releases 
            WHERE cover_download_date IS NULL
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()
        if result:
            return {'row_id': result[0], 'main_artist': result[1], 'artist': result[2], 'album': result[3], 'release_date': result[4], 'cover_link': result[5]}
        return None
    except Exception as e:
        print(f'Error getting cover to donwnload: {e}')
        traceback.print_exc()
        return None


def update_cover_downloaded(row_id, date_of_update):
    """Обновить дату обработки артиста (сохранение прогресса)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE my_releases SET cover_download_date = ? WHERE row_id = ?',
                       (date_of_update, row_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'Error updating cover download date: {e}')
        traceback.print_exc()
        return False


def main():
    amr.print_name(SCRIPT_NAME, VERSION)

    session = requests.Session() 
    session.headers.update({
        'Referer': 'https://itunes.apple.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
    })

    while True:
        covers_count = count_covers_to_download()
        cover_to_download = get_cover_to_download()
        if not cover_to_download:
            print("\nВсё скачано, качать нечего...")
            break

        row_id = int(cover_to_download['row_id'])

        # Убираем из имени Исполнителя символы, которые недопустимы в имени папки ('/', ':', '(', ')', '.' в конце)
        artist_folder_name = clean_folder_name(str(cover_to_download['main_artist']))
        # Проверяем на наличие японских символов. Если находим, мяеняем на "неочищенное" mainArtist
        non_JP_artist_name = str(cover_to_download['artist'])
        if is_jp_chars(non_JP_artist_name):
            non_JP_artist_name = str(cover_to_download['main_artist'])

        image_download(
            f"{non_JP_artist_name} - "
            f"{str(cover_to_download['album'])[:100]} - "
            f"{str(cover_to_download['release_date'])} [{row_id}]",
            artist_folder_name,
            str(cover_to_download['cover_link'])
        )
        
        print(f"ID: {row_id}. {str(cover_to_download['main_artist'])} | "
              f"{str(cover_to_download['artist'])} - "
              f"{str(cover_to_download['album'])} - "
              f"{str(cover_to_download['release_date'])}. "
              f"(Covers left: {covers_count - 1})")

        date_of_update = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not update_cover_downloaded(row_id, date_of_update):
            print(f'\n✗ Failed to update progress for cover № {row_id}')

    print("\nDONE")


if __name__ == "__main__":
    main()