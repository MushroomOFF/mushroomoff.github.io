import os
import sqlite3
import traceback
from dotenv import load_dotenv
import amr_functions as amr

# ================= CONSTANTS & VARIABLES =================
SCRIPT_NAME = "Recommender"
VERSION = "2.026.07"
ENV = 'Local'
if os.getenv("GITHUB_ACTIONS") == "true":
    ENV = 'GitHub'

if ENV == 'Local':
    ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
    load_dotenv(os.path.join(ROOT_FOLDER, '.env'))
elif ENV == 'GitHub':
    ROOT_FOLDER = ''

TOKEN = os.environ['tg_token']
CHAT_ID = os.environ['tg_channel_id']
LOGGER_ID = os.environ['tg_logger_id']
YM_TOKEN = os.environ['ym_token']
ZVUK_TOKEN = os.environ['zv_token']

AMR_FOLDER = os.path.join(ROOT_FOLDER, 'AMRs/')
DB_FOLDER = os.path.join(ROOT_FOLDER, 'Databases/')
DB_FILE = os.path.join(DB_FOLDER, 'music_releases.db')

# ================= DATABASE FUNCTIONS =================

def get_empty_new_releases():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT row_id, update_date, artist, album FROM new_releases WHERE my_type IS NULL')
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        print(f'Error getting empty new releases: {e}')
        traceback.print_exc()
        return None


def get_recommended_releases():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT row_id, artist, album, my_type, 
            album_link, album_link_ym, album_link_zv, 
            cover_link FROM new_releases
            WHERE my_type IN ('v', 'd', 'o') AND tg_message_id = 0
        ''')
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        print(f'Error getting recommended releases: {e}')
        traceback.print_exc()
        return None


def update_empty_new_release(row_id, new_type):
    """Обновить ???"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE new_releases SET my_type = ? WHERE row_id = ?',
                       (new_type, row_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'Error updating ??? {row_id}: {e}')
        traceback.print_exc()
        return False


def update_tg_message_id(row_id, tg_message_id):
    """Обновить ???"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE new_releases SET tg_message_id = ? WHERE row_id = ?',
                       (tg_message_id, row_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'Error updating tg_message_id in {row_id}: {e}')
        traceback.print_exc()
        return False


# ================= FUNCTIONS =================
def main():
    if ENV == 'Local': 
        amr.print_name(SCRIPT_NAME, VERSION)

    app_version = f'v.{VERSION} [{ENV}]'
    welcome_message = f'🚀 *{SCRIPT_NAME}*\n{app_version}'
    amr.send_message(welcome_message, TOKEN, LOGGER_ID, None, None)

    ok_counter = 0
    error_counter = 0
    empty_counter = 0

    # Check AMR files for recomendations
    empty_new_releases = get_empty_new_releases()
    # 0 - row_id, 1 - update_date, 2 - artist, 3 - album
    if empty_new_releases:
        for row in empty_new_releases:
            amr_link = f'{AMR_FOLDER}{row[1][0:4]}/AMR {row[1][0:7]}.html'
            with open(amr_link, 'r', encoding='utf-8') as html_file:
                source_code = html_file.read()
                release_position = source_code.find(f'<!-- {row[2]} - {row[3]} -->')
                begin_position = source_code.find("id='", release_position) + len("id='")
                end_position = source_code.find("'>", begin_position)
                release_record = source_code[begin_position:end_position].strip()
                if len(release_record) == 1:
                    update_empty_new_release(row[0], release_record)
                    ok_counter += 1
                elif len(release_record) == 0:
                    empty_counter += 1
                else:
                    update_empty_new_release(row[0], 'E')
                    error_counter += 1

    errors_accent = f'❌ Errors: {error_counter}'
    if error_counter:
        errors_accent = f'❌ *Errors: {error_counter}*    ⚠️'
    logger_message = f'🟢 OK: {ok_counter}\n⭕️ Emptys: {empty_counter}\n{errors_accent}'
    
    releases_to_send = get_recommended_releases()
    # 0 - row_id, 1 - artist, 2 - album, 3 - my_type, 
    # 4 - album_link, 5 - album_link_ym, 6 - album_link_zv, 
    # 7 - cover_link
    top_release_counter = 0
    new_release_counter = 0
    if releases_to_send:
        for row in releases_to_send:
            image_url = row[7].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
            text = (f'*{row[1].replace('&amp;','&')}* \\- '
                    f'[{row[2].replace('&amp;','&')}]({row[4].replace('://','://embed.')})'
                    f'\n\n\U0001F3B5 [Apple Music]({row[4]})'
                    f'{f'\n\U0001F4A5 [Яндекс\\.Музыка]({row[5]})' if row[5] else ''}'
                    f'{f'\n\U0001F50A [Звук]({row[6]})' if row[6] else ''}')
            if row[3] == 'o':
                tg_category = 'Top Releases'
                top_release_counter += 1
            elif row[3] == 'v' or row[3] == 'd':
                tg_category = 'New Releases'
                new_release_counter += 1
            message_to_send = amr.send_message(text, TOKEN, CHAT_ID, image_url, tg_category)
            if message_to_send:
                update_tg_message_id(row[0], message_to_send)    

    logger_message += f'\n\n🔥 New Releases: {new_release_counter}\n🔝 Top Releases: {top_release_counter}'
    amr.send_message(logger_message, TOKEN, LOGGER_ID, None, None)


if __name__ == "__main__":
    main()
