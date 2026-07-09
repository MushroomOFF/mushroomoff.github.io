import datetime
import os
import pandas as pd
import requests
import sqlite3
import traceback
from yandex_music import Client # for YM
from dotenv import load_dotenv
import amr_functions as amr

# ================= CONSTANTS & VARIABLES =================
SCRIPT_NAME = "Yandex.Music & Zvuk Lookup"
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

status_message = ''

HEADERS = {'Referer':'https://music.apple.com', 'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'}
session = requests.Session() 
session.headers.update(HEADERS)

# Yandex.Music ---------------------------
YM_CLIENT = Client(YM_TOKEN).init()

# Zvuk -----------------------------------
ZVUK_BASE_URL = "https://zvuk.com"
ZVUK_API_ENDPOINTS = {"lyrics": f"{ZVUK_BASE_URL}/api/tiny/lyrics", "stream": f"{ZVUK_BASE_URL}/api/tiny/track/stream", "graphql": f"{ZVUK_BASE_URL}/api/v1/graphql", "profile": f"{ZVUK_BASE_URL}/api/tiny/profile"}
ZVUK_ERROR = ''


# ================= FUNCTIONS =================

# Yandex.Music ---------------------------
def send_search_request_ym(query, year):
    ym_search_result = YM_CLIENT.search(query)
    if ym_search_result.albums:
        for ym_line in ym_search_result.albums.results:
            if str(ym_line.year) == str(year):
                return f'https://music.yandex.ru/album/{ym_line.id}'


def search_album_ym(query, year):
    ym_result = send_search_request_ym(query, year)
    if ym_result is None:
        query_error = ''
        if ' (' in query:
            query_error = query[0:query.find(' (')]
        elif ' [' in query:
            query_error = query[0:query.find(' [')]
        elif ' - EP' in query:
            query_error = query[0:query.find(' - EP')]
        elif ' - Single' in query:
            query_error = query[0:query.find(' - Single')]
        if query_error:
            ym_result = send_search_request_ym(query_error, year)
    return ym_result
#-----------------------------------------


# Zvuk -----------------------------------
def get_anonymous_token_zv():
    try:
        response = session.get(ZVUK_API_ENDPOINTS["profile"], headers=HEADERS)
        response.raise_for_status()

        zv_data = response.json()
        if ("result" in zv_data) and ("token" in zv_data["result"]):
            return zv_data["result"]["token"]

        raise ValueError("Token not found in API response")
    except Exception as zv_error:
        raise Exception(f"Failed to retrieve anonymous token: {zv_error}")


def get_auth_cookies_zv():
    """To get a token: 
    Log in to Zvuk.com in your browser. 
    Visit https://zvuk.com/api/v2/tiny/profile. 
    Copy the token value from the response
    """
    global ZVUK_TOKEN
    if not ZVUK_TOKEN:
        ZVUK_TOKEN = get_anonymous_token_zv()
    return {"auth": ZVUK_TOKEN}


def search_tracks_zv(query):
    graphql_query = """
    query getSearchReleases($query: String) {
      search(query: $query) {
        releases(limit: 10) {
          items {
            id
            title
            type
            date
            artists {
              id
              title
            }
            image {
              src
            }
          }
        }
      }
    }
    """
    payload = {"query": graphql_query, "variables": {"query": query}, "operationName": "getSearchReleases"}
    response = session.post(ZVUK_API_ENDPOINTS["graphql"], json=payload, headers=HEADERS, cookies=get_auth_cookies_zv())
    response.raise_for_status()
    zv_data = response.json()
    if (
        ("data" in zv_data)
        and ("search" in zv_data["data"])
        and ("releases" in zv_data["data"]["search"])
    ):
        return zv_data["data"]["search"]["releases"]["items"]
    return []


def search_command_zv(arg_query):
    releases_list = []
    try:
        zv_releases = search_tracks_zv(arg_query)
        if not zv_releases:
            return
        for i, release in enumerate(zv_releases, 1):
            artists = ", ".join([artist["title"] for artist in release["artists"]])
            urllen = len(release["image"]["src"])
            releases_list.append({
                "artist": artists,
                "release": release['title'],
                "type": release['type'],
                "date": release['date'][0:10],
                "id": release['id'],
                "hash": release["image"]["src"][urllen - 36:urllen]
            })
        return releases_list
    except Exception as zv_error:
        return f"Error: {zv_error}"


def search_album_zv(query):
    global ZVUK_ERROR
    sArtist = ""
    sRelease = ""
    sTypes = []
    search_split = query.split(" - ")
    if len(search_split) > 1:
        sArtist = search_split[0]
        if search_split[len(search_split) - 1] not in ['Single', 'EP']:
            sRelease = ' - '.join(search_split[1:])
            sTypes.append('album')
        else:
            sRelease = ' - '.join(search_split[1:len(search_split) - 1])
            if search_split[len(search_split) - 1] == 'EP':
                sTypes.append('album')
                sTypes.append('single')
            elif search_split[len(search_split) - 1] == 'Single':
                sTypes.append('single')

    search_query = [f"{sArtist} - {sRelease}", sRelease]
    for one_query in search_query:
        zv_releases = search_command_zv(one_query)
        if type(zv_releases) is list:
            for sType in sTypes:
                for zv_release in zv_releases:
                        if (sArtist.lower() in zv_release['artist'].lower().replace("’","'")) and (sRelease.lower() in zv_release['release'].lower().replace("’","'")) and (sType.lower() == zv_release['type']):
                            return f"https://zvuk.com/release/{zv_release['id']}"
        elif type(zv_releases) is str:
            # if search_command_zv return Error
            ZVUK_ERROR = f'Zvuk {zv_releases}' 
        # elif zv_releases is None:
            # if search_command_zv return None
            # amr.logger(f"Zvuk didn't find {one_query}", LOG_FILE, SCRIPT_NAME)
            # status_message += f"\n⚠️ Zvuk didn't find {one_query}"
#-----------------------------------------


def change_amr_button(source_code, separator, new_link, zvorym): 
    """Changing button state in AMR html files
    'zvorym' parameter in ['Яндекс.Музыка', 'Звук']
    """
    str_tuple = source_code.partition(f'<button data-frame-load="{separator}">Preview</button>')
    str_list = list(str_tuple)
    
    str_list[2] = str_list[2].replace(f'<a href="" target="_blank"><button disabled>{zvorym}</button>', 
                                      f'<a href="{new_link}" target="_blank"><button>{zvorym}</button>', 1)
    str_tuple = tuple(str_list)
    source_code = ''.join(str_tuple)
    return source_code


def change_amr_file(new_link, zvorym, amr_date, link):
    """Changing links in AMR html files
    'zvorym' parameter in ['Яндекс.Музыка', 'Звук']
    """    
    amr_link = f'{AMR_FOLDER}{amr_date[0:4]}/AMR {amr_date[0:7]}.html'
    with open(amr_link, 'r', encoding='utf-8') as html_file:
        source_code = html_file.read()
        link_split = link.split('/')
        id_to_find = link_split[len(link_split)-1]
        source_code = change_amr_button(source_code, id_to_find, new_link, zvorym)
            
    with open(amr_link, 'w') as html_file:
        html_file.write(source_code)


# ================= DATABASE FUNCTIONS =================

def get_no_zvym_releases(previous_date):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT row_id, artist, album, my_type, 
            album_link, album_link_ym, album_link_zv, 
            cover_link, update_date FROM new_releases
            WHERE my_type IN ('v', 'd', 'o') 
            AND (album_link_ym IS NULL OR album_link_zv IS NULL)
            AND update_date >= ?
        ''', (previous_date,))
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        print(f'Error getting recommended releases: {e}')
        traceback.print_exc()
        return None


def update_zvym_link(row_id, new_link, zvym):
    """Обновить ???"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f'UPDATE new_releases SET album_link_{zvym} = ? WHERE row_id = ?',
                       (new_link, row_id))
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
    

def main():
    global status_message

    if ENV == 'Local': 
        amr.print_name(SCRIPT_NAME, VERSION)

    app_version = f'v.{VERSION} [{ENV}]'
    welcome_message = f'🚀 *{SCRIPT_NAME}*\n{app_version}'
    amr.send_message(welcome_message, TOKEN, LOGGER_ID, None, None)

    # Searchig for new link for releases within last 15 days
    previous_date = datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(days=15), '%Y-%m-%d')
    new_ym_links = 0
    new_zv_links = 0

    releases_to_zvym = get_no_zvym_releases(previous_date)
    # 0 - row_id, 1 - artist, 2 - album, 3 - my_type, 
    # 4 - album_link, 5 - album_link_ym, 6 - album_link_zv, 
    # 7 - cover_link, 8 - update_date
    if releases_to_zvym:
        for row in releases_to_zvym:
            ym_result = ''
            zv_result = ''
            is_message = False
            ym_zv_search_string = f'{row[1].replace('&amp;','&')} - {row[2].replace('&amp;','&')}'
            if not row[5]: 
                ym_result = search_album_ym(ym_zv_search_string, row[8][0:4])
            if (not row[6]) and (not ZVUK_ERROR): 
                zv_result = search_album_zv(ym_zv_search_string)

            # Printing Artist and Album if found something
            if ((ym_result is not None) and (ym_result != '')) or ((zv_result is not None) and (zv_result != '')):
                logger_message = f'{row[0]}. {row[1]} - {row[2]}'
                status_message += f'\n{logger_message}'

            # Changing links for YM and Zvuk
            if (ym_result is not None) and (ym_result != ''):    
                update_zvym_link(row[0], ym_result, 'ym')
                change_amr_file(ym_result, 'Яндекс.Музыка', row[8], row[4])
                new_ym_links += 1
                is_message = True
            if (zv_result is not None) and (zv_result != ''):
                update_zvym_link(row[0], zv_result, 'zv')
                change_amr_file(zv_result, 'Звук', row[8], row[4])
                new_zv_links += 1
                is_message = True

            if is_message:
                if row[3] == 'v' or row[3] == 'd':
                    thread_name = 'New Releases'
                elif row[3] == 'o':
                    thread_name = 'Top Releases'
                image_url = row[7].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
                image_caption = (f'*{row[1].replace('&amp;','&')}* \\- '
                                 f'[{row[2].replace('&amp;','&')}]({row[4].replace('://','://embed.')})'
                                 f'\n\n\U0001F3B5 [Apple Music]({row[4]})'
                                 f'{f'\n\U0001F4A5 [Яндекс\\.Музыка]({ym_result})' if ym_result else ''}'
                                 f'{f'\n\U0001F50A [Звук]({zv_result})' if zv_result else ''}')
                message_to_send = amr.send_message(image_caption, TOKEN, CHAT_ID, image_url, thread_name)
                update_tg_message_id(row[0], message_to_send)

    if ZVUK_ERROR:
        status_message += f'\n⚠️ {ZVUK_ERROR}'
            
    if (new_ym_links + new_zv_links):
        logger_message = f'New links:\n💥 {new_ym_links} Yandex\\.Music\n🔊 {new_zv_links} Zvuk'
    else:
        logger_message = f'🤷‍♂️ No new links'
    amr.send_message(f'{logger_message}{f'\n{status_message}' if status_message else ''}', TOKEN, LOGGER_ID, None, None)


if __name__ == "__main__":
    main()
