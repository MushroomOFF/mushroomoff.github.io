import csv
import datetime
import json
import os
import pandas as pd
import requests
import sys # for Zvuk
from yandex_music import Client # for YM
import amr_functions as amr

# CONSTANTS
SCRIPT_NAME = "Yandex.Music & Zvuk Lookup"
VERSION = "2.026.02"
ENV = 'Local'
if os.getenv("GITHUB_ACTIONS") == "true":
    ENV = 'GitHub'

if ENV == 'Local':
    ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
elif ENV == 'GitHub':
    ROOT_FOLDER = ''
AMR_FOLDER = os.path.join(ROOT_FOLDER, 'AMRs/')
DB_FOLDER = os.path.join(ROOT_FOLDER, 'Databases/')
NEW_RELEASES_DB = os.path.join(DB_FOLDER, 'AMR_newReleases_DB.csv')
LOG_FILE = os.path.join(ROOT_FOLDER, 'status.log')

# Telegram -------------------------------
TOKEN = ''
CHAT_ID = ''
URL = 'https://api.telegram.org/bot'
THREAD_ID_DICT = {'New Updates': 6, 'Top Releases': 10, 'Coming Soon': 3, 'New Releases': 2, 'Next Week Releases': 80}

# Yandex.Music ---------------------------
YM_TOKEN = ''
YM_CLIENT = ''

# Zvuk -----------------------------------
ZVUK_BASE_URL = "https://zvuk.com"
ZVUK_API_ENDPOINTS = {"lyrics": f"{ZVUK_BASE_URL}/api/tiny/lyrics", "stream": f"{ZVUK_BASE_URL}/api/tiny/track/stream", "graphql": f"{ZVUK_BASE_URL}/api/v1/graphql", "profile": f"{ZVUK_BASE_URL}/api/tiny/profile"}
ZVUK_TOKEN = ''
ZVUK_ERROR = ''

HEADERS = {'Referer':'https://music.apple.com', 'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'}
session = requests.Session() 
session.headers.update(HEADERS)

# functions

# Yandex.Music ---------------------------
def send_search_request_ym(query, year):
    global YM_CLIENT
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
    sType = ""    
    search_split = query.split(" - ")
    if len(search_split) > 1:
        sArtist = search_split[0]
        if search_split[len(search_split) - 1] in ['Single']:
            sRelease = ' - '.join(search_split[1:len(search_split) - 1])
            sType = search_split[len(search_split) - 1]
        elif search_split[len(search_split) - 1] in ['EP']:
            sRelease = ' - '.join(search_split[1:len(search_split) - 1])
            sType = "Album"
        else:
            sRelease = ' - '.join(search_split[1:])
            sType = "Album"
    zv_releases = search_command_zv(query)
    if type(zv_releases) is list:
        for zv_release in zv_releases:
            if (sArtist.lower() == zv_release['artist'].lower()) and (sRelease.lower() == zv_release['release'].lower()) and (sType.lower() == zv_release['type']):
                return f'https://zvuk.com/release/{zv_release['id']}'
    elif type(zv_releases) is str:
        # if search_command_zv return Error
        ZVUK_ERROR = f'Zvuk {zv_releases}' 
    elif zv_releases is None:
        # if search_command_zv return None
        amr.logger(f"Zvuk didn't find {query}", LOG_FILE, SCRIPT_NAME)
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

def main():
    global TOKEN, CHAT_ID, YM_TOKEN, YM_CLIENT, ZVUK_TOKEN, ZVUK_ERROR

    if ENV == 'Local': 
        amr.print_name(SCRIPT_NAME, VERSION)
    amr.logger(f'▲ v.{VERSION} [{ENV}]', LOG_FILE, SCRIPT_NAME, 'noprint') # Begin

    if ENV == 'Local':
        PARAMS = input("[IMPORTANT!] TOKEN CHAT_ID YM_TOKEN ZV_TOKEN: ").split(' ')
        if len(PARAMS) < 4:
            amr.logger('Error: not enough parameters!', LOG_FILE, SCRIPT_NAME)
            amr.logger(f'▼ DONE', LOG_FILE, SCRIPT_NAME) # End
            sys.exit()
        TOKEN = PARAMS[0] # input("Telegram Bot TOKEN: ")
        CHAT_ID = PARAMS[1] # input("Telegram Bot CHAT_ID: ")
        YM_TOKEN = PARAMS[2] # input("Yandex.Music TOKEN: ")
        ZVUK_TOKEN = PARAMS[3] # input("Zvuk TOKEN: ")        
    elif ENV == 'GitHub': 
        TOKEN = os.environ['tg_token']
        CHAT_ID = os.environ['tg_channel_id']
        YM_TOKEN = os.environ['ym_token']
        ZVUK_TOKEN = os.environ['zv_token']

    YM_CLIENT = Client(YM_TOKEN).init()

    new_releases_df = pd.read_csv(NEW_RELEASES_DB, sep=";")

    # Searchig for new link for releases within last 15 days
    previous_date = datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(days=15), '%Y-%m-%d')
    new_ym_links = 0
    new_zv_links = 0
    for index, row in new_releases_df[(new_releases_df['Best_Fav_New_OK'].isin(['v','d','o'])) & (new_releases_df['link_ym'].isnull() | new_releases_df['link_zv'].isnull()) & (new_releases_df['date'] > previous_date)].iterrows():
        ym_result = ''
        zv_result = ''
        is_message = False
        ym_zv_search_string = f'{row.loc['artist'].replace('&amp;','&')} - {row.loc['album'].replace('&amp;','&')}'
        if pd.isna(row.loc['link_ym']): 
            ym_result = search_album_ym(ym_zv_search_string, row.loc['date'][0:4])
        if (pd.isna(row.loc['link_zv'])) and (not ZVUK_ERROR): 
            zv_result = search_album_zv(ym_zv_search_string)

        # Printing Artist and Album if found something
        if ((ym_result is not None) and (ym_result != '')) or ((zv_result is not None) and (zv_result != '')):
            amr.logger(f'{index}. {row.loc['artist']} - {row.loc['album']}', LOG_FILE, SCRIPT_NAME)

        # Changing links for YM and Zvuk
        if (ym_result is not None) and (ym_result != ''):    
            row.loc['link_ym'] = ym_result
            new_releases_df.loc[index,'link_ym'] = ym_result
            change_amr_file(ym_result, 'Яндекс.Музыка', row.loc['date'], row.loc['link'])
            new_ym_links += 1
            is_message = True
        if (zv_result is not None) and (zv_result != ''):
            row.loc['link_zv'] = zv_result
            new_releases_df.loc[index,'link_zv'] = zv_result
            change_amr_file(zv_result, 'Звук', row.loc['date'], row.loc['link'])
            new_zv_links += 1
            is_message = True

        if is_message:
            if (row.loc['Best_Fav_New_OK'] == 'v') or (row.loc['Best_Fav_New_OK'] == 'd'):
                thread_name = 'New Releases'
            elif row.loc['Best_Fav_New_OK'] == 'o':
                thread_name = 'Top Releases'
            image_url = row.loc['imga'].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
            image_caption = f'*{amr.replace_symbols_markdown_v2(row.loc['artist'].replace('&amp;','&'))}* \\- [{amr.replace_symbols_markdown_v2(row.loc['album'].replace('&amp;','&'))}]({row.loc['link'].replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({row.loc['link']}){'' if pd.isna(row.loc['link_ym']) else f'\n\U0001F4A5 [Яндекс\\.Музыка]({row.loc['link_ym']})'}{'' if pd.isna(row.loc['link_zv']) else f'\n\U0001F50A [Звук]({row.loc['link_zv']})'}'
            message_to_send = amr.send_photo(thread_name, image_caption, image_url, TOKEN, CHAT_ID)
            row.loc['TGmsgID'] = message_to_send
            new_releases_df.loc[index,'TGmsgID'] = message_to_send
            
    if (new_ym_links + new_zv_links):
        new_releases_df.to_csv(NEW_RELEASES_DB, sep=';', index=False)
        amr.logger(f'New links: {new_ym_links} Yandex.Music, {new_zv_links} Zvuk', LOG_FILE, SCRIPT_NAME)

    if ZVUK_ERROR:
        amr.logger(f'{ZVUK_ERROR}', LOG_FILE, SCRIPT_NAME)

    amr.logger(f'▼ DONE', LOG_FILE, SCRIPT_NAME) # End

if __name__ == "__main__":
    main()
