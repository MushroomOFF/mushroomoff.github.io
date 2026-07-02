import datetime
import json
import os
import pandas as pd
import requests
import sqlite3
import time
import traceback
from dotenv import load_dotenv
import amr_functions as amr

# ================= CONSTANTS & VARIABLES =================
SCRIPT_NAME = "LookApp"
VERSION = "2.026.07"
ENV = 'Local'
if os.getenv("GITHUB_ACTIONS") == "true":
    ENV = 'GitHub'

if ENV == 'Local':
    ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
    load_dotenv(os.path.join(ROOT_FOLDER, '.env'))
elif ENV == 'GitHub':
    ROOT_FOLDER = ''

TOKEN = os.environ.get('tg_token')
LOGGER_ID = os.environ.get('tg_logger_id')
DB_FOLDER = os.path.join(ROOT_FOLDER, 'Databases/')
DB_FILE = os.path.join(DB_FOLDER, 'music_releases.db')
LOG_FILE = os.path.join(ROOT_FOLDER, 'status.log')

EMOJI_DICT = {
    'us': '\U0001F1FA\U0001F1F8', 'ru': '\U0001F1F7\U0001F1FA', 'jp': '\U0001F1EF\U0001F1F5',
    'no': '\U0001F3F3\U0000FE0F', 'wtf': '\U0001F914', 'album': '\U0001F4BF',
    'cover': '\U0001F3DE\U0000FE0F', 'error': '\U00002757\U0000FE0F',
    'empty': '\U0001F6AB', 'badid': '\U0000274C'
}

countries_list = []
message_to_send = ''
message_empty = ''
message_error = ''
message_bad_id = ''
log_in_file = False

session = requests.Session()
session.headers.update({
    'Referer': 'https://itunes.apple.com',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
})

# ================= DATABASE FUNCTIONS =================
def init_db():
    """Инициализация базы данных SQLite"""
    try:
        os.makedirs(DB_FOLDER, exist_ok=True)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Таблица релизов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS my_releases (
                row_id INTEGER,
                update_date TEXT,
                rate_tag TEXT,
                main_artist TEXT,
                artist TEXT,
                album TEXT,
                tracks INTEGER,
                release_date TEXT,
                release_year INTEGER,
                main_artist_id INTEGER,
                artist_id INTEGER,
                album_id INTEGER,
                country TEXT,
                cover_link TEXT,
                cover_download_date TEXT,
                update_reason TEXT,
                PRIMARY KEY(row_id AUTOINCREMENT)
            )
        ''')

        # Таблица артистов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS artists (
                row_id INTEGER,
                artist TEXT,
                artist_id INTEGER,
                artist_genre TEXT,
                update_type INTEGER,
                update_date TEXT,
                PRIMARY KEY(row_id AUTOINCREMENT)
            )
        ''')

        conn.commit()
        conn.close()
        print('Database initialized\n')
    except Exception as e:
        print(f'Error initializing database: {e}')
        traceback.print_exc()
        raise


def get_artist_to_find(select_where):
    """Получить первого необработанного артиста"""
    if select_where in ['2', '1']:
        where_condition = f'AND update_type = {select_where}'
    elif select_where == '0':
        where_condition = ''
    else:
        where_condition = 'AND update_type IN (2, 1) '
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT artist_id, artist FROM artists 
            WHERE update_date IS NULL AND artist_id > 0 {where_condition} 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()
        if result:
            return {'artist_id': result[0], 'artist': result[1]}
        return None
    except Exception as e:
        print(f'Error getting artist to find: {e}')
        traceback.print_exc()
        return None


def update_artist_downloaded(main_id, date_of_update):
    """Обновить дату обработки артиста (сохранение прогресса)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE artists SET update_date = ? WHERE artist_id = ?',
                       (date_of_update, main_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'Error updating artist download date: {e}')
        traceback.print_exc()
        return False


def reset_artists_downloaded(select_where):
    """Сбросить прогресс обработки всех артистов"""
    if select_where in ['2', '1']:
        where_condition = f'WHERE update_type = {select_where}'
    elif select_where == '0':
        where_condition = ''
    else:
        where_condition = 'WHERE update_type IN (2, 1) '

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f'UPDATE artists SET update_date = NULL {where_condition}')
        conn.commit()
        conn.close()
        print('Artists progress reset')
        return True
    except Exception as e:
        print(f'Error resetting artists: {e}')
        traceback.print_exc()
        return False


def check_collection_exists(album_id):
    """Проверить, существует ли релиз в БД"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM my_releases WHERE album_id = ?', (album_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] > 0
    except Exception as e:
        print(f'Error checking collection {album_id}: {e}')
        return False


def check_cover_exists(album_id, artwork_url):
    """Проверить, совпадает ли обложка (сравнение с 40-го символа)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT cover_link FROM my_releases WHERE album_id = ?', (album_id,))
        result = cursor.fetchall()
        conn.close()
        if result:
            for row in result:
                if len(row[0]) > 40 and len(artwork_url) > 40:
                    if row[0][40:] == artwork_url[40:]:
                        return True
        return False
    except Exception as e:
        print(f'Error checking cover for {album_id}: {e}')
        return False


def insert_release(release_data):
    """Вставить релиз в БД с явным преобразованием типов"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO my_releases
            (update_date, main_artist, artist, album, tracks, release_date, 
             release_year, main_artist_id, artist_id, album_id, country, 
             cover_link, update_reason)

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(release_data['dateUpdate']),
            str(release_data['mainArtist']),
            str(release_data['artistName']),
            str(release_data['collectionName']),
            int(release_data['trackCount']),
            str(release_data['releaseDate']),
            int(release_data['releaseYear']),
            int(release_data['mainId']),
            int(release_data['artistId']),
            int(release_data['collectionId']),
            str(release_data['country']),
            str(release_data['artworkUrlD']),
            str(release_data['updReason'])
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'Error inserting release {release_data.get("collectionId")}: {e}')
        traceback.print_exc()
        return False


# ================= MAIN FUNCTIONS =================
def find_releases(find_artist_id, artist_print_name):
    """Поиск релизов одного артиста по всем странам"""
    global message_to_send, message_empty, message_error, message_bad_id, log_in_file

    all_releases_df = pd.DataFrame()
    export_df = pd.DataFrame()

    for country in countries_list:
        try:
            url = f'https://itunes.apple.com/lookup?id={find_artist_id}&country={country}&entity=album&limit=200'
            response = session.get(url, timeout=30)

            if response.status_code == 200:
                try:
                    json_parsed = response.json()
                    if json_parsed.get('resultCount', 0) > 1:
                        temp_df = pd.DataFrame(json_parsed['results'])
                        temp_df = temp_df[['artistName', 'artistId', 'collectionId', 'collectionName',
                                           'artworkUrl100', 'trackCount', 'country', 'releaseDate']].copy()
                        all_releases_df = pd.concat([all_releases_df, temp_df], ignore_index=True)
                    else:
                        print(f'{artist_print_name} - {find_artist_id} - {country} - EMPTY')
                        message_empty += f'\n{EMOJI_DICT[country]} *{artist_print_name.replace(" &amp;", "and")}*'
                except json.JSONDecodeError as e:
                    print(f'JSON decode error for {artist_print_name} - {country}: {e}')
            else:
                if not log_in_file:
                    try:
                        amr.logger(f'▲ v.{VERSION} [{ENV}]', LOG_FILE, SCRIPT_NAME, 'noprint')
                        log_in_file = True
                    except Exception:
                        pass
                try:
                    amr.logger(f'{artist_print_name} - {find_artist_id} - {country} - ERROR ({response.status_code})',
                               LOG_FILE, SCRIPT_NAME)
                except Exception:
                    pass
                message_error += f'\n{EMOJI_DICT[country]} *{artist_print_name.replace(" &amp;", "and")}*'

        except requests.exceptions.RequestException as e:
            print(f'Request error for {artist_print_name} - {country}: {e}')
        except Exception as e:
            print(f'Unexpected error for {artist_print_name} - {country}: {e}')
            traceback.print_exc()

        # Пауза для обхода блокировок iTunes
        time.sleep(1)

    # Удаление дубликатов
    if not all_releases_df.empty:
        all_releases_df.drop_duplicates(subset='artworkUrl100', keep='first', inplace=True, ignore_index=True)
        export_df = all_releases_df.loc[all_releases_df['collectionName'].notna()].copy()
    elif len(countries_list) > 1:
        print(f'{artist_print_name} - {find_artist_id} - Bad ID')
        message_bad_id += f'\n{EMOJI_DICT["no"]} *{artist_print_name.replace(" &amp;", "and")}*'

    if not export_df.empty:
        update_date = datetime.datetime.now().strftime('%Y-%m-%d')
        new_release_counter = 0
        new_cover_counter = 0

        for _, row in export_df.iterrows():
            # Каждый релиз обрабатываем отдельно — если один упадет, продолжим со следующего
            try:
                collection_id = int(row['collectionId'])
                artwork_url_d = str(row['artworkUrl100']).replace('100x100bb', '10000x10000-999')

                # Безопасное преобразование типов
                track_count = int(row['trackCount']) if pd.notna(row.get('trackCount')) else 0
                artist_id = int(row['artistId']) if pd.notna(row.get('artistId')) else 0
                release_date_str = str(row.get('releaseDate', ''))

                if not check_collection_exists(collection_id):
                    update_reason = 'New release'
                    new_release_counter += 1
                elif not check_cover_exists(collection_id, artwork_url_d):
                    update_reason = 'New cover'
                    new_cover_counter += 1
                else:
                    continue

                release_data = {
                    'dateUpdate': update_date,
                    'mainArtist': artist_print_name,
                    'artistName': str(row.get('artistName', '')),
                    'collectionName': str(row.get('collectionName', '')),
                    'trackCount': track_count,
                    'releaseDate': release_date_str[:10] if len(release_date_str) >= 10 else release_date_str,
                    'releaseYear': int(release_date_str[:4]) if len(release_date_str) >= 4 else 0,
                    'mainId': find_artist_id,
                    'artistId': artist_id,
                    'collectionId': collection_id,
                    'country': str(row.get('country', '')),
                    'artworkUrlD': artwork_url_d,
                    'updReason': update_reason
                }

                if not insert_release(release_data):
                    print(f'  ✗ Failed to insert: {release_data["collectionName"]}')

            except Exception as e:
                print(f'  ✗ Error processing release row: {e}')
                traceback.print_exc()
                continue  # Продолжаем со следующего релиза

        if (new_release_counter + new_cover_counter) > 0:
            print(f'{artist_print_name} - {find_artist_id} - {new_release_counter + new_cover_counter} '
                  f'new records: {new_release_counter} releases, {new_cover_counter} covers')
            iconka = 'album' if new_release_counter else 'cover'
            message_to_send += (f'\n{EMOJI_DICT[iconka]} '
                                f'*{artist_print_name.replace(" &amp;", "and")}*: '
                                f'{new_release_counter + new_cover_counter}')


def main():
    global message_to_send, message_empty, message_error, message_bad_id, countries_list, log_in_file

    try:
        if ENV == 'Local':
            amr.print_name(SCRIPT_NAME, VERSION)

        # Инициализация БД
        init_db()

        # Выбор стран
        if ENV == 'Local':
            countries_input = input("\nChoose countries to check:"
                                    "\nEnter: [us, ru, jp]"
                                    "\n2:     [us, ru]"
                                    "\njp:    [jp]\n ")
            if countries_input == 'jp':
                countries_list = ['jp']
            elif countries_input == '2':
                countries_list = ['us', 'ru']
            else:
                countries_list = ['us', 'ru', 'jp']
            print(f'{countries_list}\n')

            artists_input = input("\nChoose artists to check:"
                                  "\nEnter:  [2, 1]"
                                  "\n2 or 1: [2] or [1]]"
                                  "\n0:      ! ALL [2, 1, 0]\n ")
            if artists_input in ['2', '1']:
                select_where = artists_input
                print(f'Only: {select_where}')
            elif artists_input == '0':
                select_where = artists_input
                print(f'ALL!')
            else:
                select_where = ''
                print('2 and 1')
        elif ENV == 'GitHub':
            countries_list = ['us', 'ru']
            select_where = '2'

        app_version = f'v.{VERSION} [{ENV}]'
        welcome_message = f'🚀 *{SCRIPT_NAME}*\n{app_version}'

        try:
            amr.send_message(welcome_message, TOKEN, LOGGER_ID, None, None)
        except Exception as e:
            print(f'Error sending welcome message: {e}')

        message_to_send = ''
        message_error_part = '======== ERRORS ========'
        message_error = f'{EMOJI_DICT["error"]} 503 Service Unavailable {EMOJI_DICT["error"]}'
        message_empty = f'{EMOJI_DICT["empty"]} Not available in country {EMOJI_DICT["empty"]}'
        message_bad_id = f'{EMOJI_DICT["badid"]}               Bad ID                {EMOJI_DICT["badid"]}'

        check_mes_send_len = len(message_to_send)
        check_mes_error_len = len(message_error)
        check_mes_empty_len = len(message_empty)
        check_mes_badid_len = len(message_bad_id)

        # Local режим: интерактивная проверка прогресса
        if ENV == 'Local':
            artist_info = get_artist_to_find(select_where)
            if not artist_info:
                key_logger = input("All done. [Enter] to start over:  ")
                if not key_logger:
                    reset_artists_downloaded(select_where)
            else:
                key_logger = input(
                    f"Stopped at {artist_info['artist']}. [Enter] to continue. Anything else to start over:  ")
                if key_logger:
                    reset_artists_downloaded(select_where)
            print('')
        elif ENV == 'GitHub':
            # В GitHub режиме сбрасываем прогресс перед каждым запуском (как в оригинале)
            reset_artists_downloaded(select_where)

        # Основной цикл обработки артистов
        while True:
            try:
                artist_info = get_artist_to_find(select_where)
                if not artist_info:
                    break

                artist_id = int(artist_info['artist_id'])
                artist_print_name = str(artist_info['artist'])
                print(f'{artist_print_name} - {artist_id}'.ljust(55), end='\r')

                # Обработка артиста — если упадет, идем дальше
                try:
                    find_releases(artist_id, artist_print_name)
                except Exception as e:
                    print(f'\n✗ Error processing artist {artist_print_name}: {e}')
                    traceback.print_exc()
                    # ВАЖНО: все равно сохраняем прогресс, чтобы не зациклиться
                    # на проблемном артисте

                # Сохраняем прогресс ПОСЛЕ каждого артиста
                if ENV == 'Local':
                    date_of_update = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                elif ENV == 'GitHub':
                    date_of_update = (datetime.datetime.now() + datetime.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')

                if not update_artist_downloaded(artist_id, date_of_update):
                    print(f'\n✗ Failed to update progress for {artist_print_name}')

                # Пауза для обхода блокировок iTunes
                time.sleep(1.5)

            except Exception as e:
                print(f'\n✗ Error in main loop: {e}')
                traceback.print_exc()
                break

        print(''.ljust(55))

        # Отправка итогового сообщения
        if not TOKEN or not LOGGER_ID:
            print('Message not sent! No TOKEN or LOGGER_ID')
        else:
            try:
                if check_mes_send_len == len(message_to_send):
                    message_to_send += f'\n{EMOJI_DICT["wtf"]}'

                if (check_mes_error_len != len(message_error) or
                        check_mes_empty_len != len(message_empty) or
                        check_mes_badid_len != len(message_bad_id)):
                    message_to_send += f'\n\n{message_error_part}'
                    if check_mes_badid_len != len(message_bad_id):
                        message_to_send += f'\n\n{message_bad_id}'
                    if check_mes_error_len != len(message_error):
                        message_to_send += f'\n\n{message_error}'
                    if check_mes_empty_len != len(message_empty):
                        message_to_send += f'\n\n{message_empty}'

                amr.send_message(message_to_send, TOKEN, LOGGER_ID, None, None)
            except Exception as e:
                print(f'Error sending final message: {e}')

        if log_in_file:
            try:
                amr.logger('▼ DONE', LOG_FILE, SCRIPT_NAME, 'noprint')
            except Exception as e:
                print(f'Error logging done: {e}')

    except Exception as e:
        print(f'Critical error in main: {e}')
        traceback.print_exc()
        if log_in_file:
            try:
                amr.logger(f'▼ CRITICAL ERROR: {e}', LOG_FILE, SCRIPT_NAME, 'noprint')
            except Exception:
                pass


if __name__ == "__main__":
    main()