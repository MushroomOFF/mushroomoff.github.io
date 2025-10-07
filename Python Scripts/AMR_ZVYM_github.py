SCRIPT_NAME = "Apple Music Releases Yandex.Music & Zvuk Lookup"
VERSION = "v.2.025.09 [GitHub]"
# Python 3.12 & Pandas 2.2 ready
# Temporary block ZVUK
# comment will mark the specific code for GitHub

import os
import json
import datetime
import requests
import pandas as pd
import csv
import sys # for Zvuk
from yandex_music import Client # for YM

rootFolder = '' # root is root
amrsFolder = rootFolder + 'AMRs/'
dbFolder = rootFolder + 'Databases/'
newReleasesDB = dbFolder + 'AMR_newReleases_DB.csv' # This Week New Releases 
logFile = rootFolder + 'status.log' # path to log file
# Telegram -------------------------------
URL = 'https://api.telegram.org/bot'
TOKEN = os.environ['tg_token'] # GitHub Secrets
chat_id = os.environ['tg_channel_id'] # GitHub Secrets
thread_id = {'New Updates': 6, 'Top Releases': 10, 'Coming Soon': 3, 'New Releases': 2, 'Next Week Releases': 80}
# Yandex.Music ---------------------------
YM_TOKEN = os.environ['ym_token'] # GitHub Secrets
search_result = ''
client = Client(YM_TOKEN).init()
type_to_name = {'track': 'трек', 'artist': 'исполнитель', 'album': 'альбом', 'playlist': 'плейлист', 'video': 'видео', 'user': 'пользователь', 'podcast': 'подкаст', 'podcast_episode': 'эпизод подкаста'}

# Zvuk -----------------------------------
BASE_URL = "https://zvuk.com"
API_ENDPOINTS = {"lyrics": f"{BASE_URL}/api/tiny/lyrics", "stream": f"{BASE_URL}/api/tiny/track/stream", "graphql": f"{BASE_URL}/api/v1/graphql", "profile": f"{BASE_URL}/api/tiny/profile"}
ZVUK_TOKEN = os.environ['zv_token'] # GitHub Secrets
ZVUK_ERROR = ''
# ZVUK_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36", "Content-Type": "application/json"}

# Establishing session -------------------
HEADERS = {'Referer':'https://music.apple.com', 'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'}
s = requests.Session() 
s.headers.update(HEADERS)
#-----------------------------------------

# This logger is only for GitHub --------------------------------------------------------------------
def amnr_logger(logLine):
    with open(logFile, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        # GitHub server time is UTC (-3 from Moscow), so i add +3 hours to log actions in Moscow time. Only where time matters
        f.write(str(datetime.datetime.now() + datetime.timedelta(hours=3)) + ' - ' + SCRIPT_NAME + ' - ' + logLine.rstrip('\r\n') + '\n' + content)
#----------------------------------------------------------------------------------------------------

# YM -------------------------------------
def send_search_request_ym(query, year):
    global search_result
    search_result = client.search(query)
    if search_result.albums:
        for line in search_result.albums.results:
            artists = ""
            for artline in line.artists:
                if len(artists) == 0:
                    artists += f'{artline.name}'
                    frstartst = artline.name
                else:
                    artists += f', {artline.name}'
            if str(line.year) == str(year):
                return f'https://music.yandex.ru/album/{line.id}'

def search_album_ym(query, year):
    result = ''
    result = send_search_request_ym(query, year)
    if result is None:
        query_error = ''
        if query.find('(') > -1:
            query_error = query[0:query.find(' (')]
        elif query.find('[') > -1:
            query_error = query[0:query.find(' [')]
        elif query.find(' - EP') > -1:
            query_error = query[0:query.find(' - EP')]
        elif query.find(' - Single') > -1:
            query_error = query[0:query.find(' - Single')]
        if query_error != '':
            result = send_search_request_ym(query_error, year)
    return result
#-----------------------------------------

# Zvuk -----------------------------------
def get_anonymous_token():
    try:
        response = requests.get(API_ENDPOINTS["profile"], headers=HEADERS)
        response.raise_for_status()

        data = response.json()
        if "result" in data and "token" in data["result"]:
            return data["result"]["token"]

        raise ValueError("Token not found in API response")
    except Exception as e:
        raise Exception(f"Failed to retrieve anonymous token: {e}")

def get_auth_cookies():
# To get a token: Log in to Zvuk.com in your browser. Visit https://zvuk.com/api/v2/tiny/profile. Copy the token value from the response
    global ZVUK_TOKEN

    if not ZVUK_TOKEN:
        ZVUK_TOKEN = get_anonymous_token()
    
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
    response = requests.post(API_ENDPOINTS["graphql"], json=payload, headers=HEADERS, cookies=get_auth_cookies())
    response.raise_for_status()
    data = response.json()
    if (
        "data" in data
        and "search" in data["data"]
        and "releases" in data["data"]["search"]
    ):
        return data["data"]["search"]["releases"]["items"]
    return []

def search_command_zv(arg_query):
    releases_list = []
    try:
        releases = search_tracks_zv(arg_query)
        if not releases:
            # print("No releases found")
            return
        # print(f"Found {len(releases)} releases:")
        for i, release in enumerate(releases, 1):
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
    except Exception as e:
        return f"Error: {e}"

def search_album_zv(query):
    global ZVUK_ERROR
    sArtist = ""
    sRelease = ""
    sType = ""    
    search_split = query.split(" - ")
    if len(search_split) == 1:
        if len(search_split[0]) == 0:
            print("Empty search")
        else:
            sArtist = search_split[0]
    else:
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
    releases = search_command_zv(query)
    if type(releases) is list:
        for rel in releases:
            if (sArtist.lower() == rel['artist'].lower()) and (sRelease.lower() == rel['release'].lower()) and (sType.lower() == rel['type']):
                return f'https://zvuk.com/release/{rel['id']}'
    elif type(releases) is str:
        ZVUK_ERROR = 'Zvuk {releases}' # if search_command_zv return Error
    elif releases is None:
        amnr_logger(f"Zvuk didn't find {query}") # if search_command_zv return None
#-----------------------------------------
        
# Процедура Замены символов для Markdown v2
def ReplaceSymbols(rsTxt):
    rsTmplt = """'_*[]",()~`>#+-=|{}.!"""
    for rsf in range(len(rsTmplt)):
        rsTxt = rsTxt.replace(rsTmplt[rsf], '\\' + rsTmplt[rsf])
    return rsTxt

# Процедура Отправки изображения ботом в канал
def send_photo_url(topic, img_url, img_caption):
    method = URL + TOKEN + "/sendPhoto"
    r = requests.post(method, data={"message_thread_id": thread_id[topic], "chat_id": chat_id, "photo": img_url, "parse_mode": 'MarkdownV2', "caption": img_caption})
    json_response = json.loads(r.text)
    rmi = json_response['result']['message_id']    
    return rmi

# Изменение AMR_file
def change_amr_button(chstr, sepstr, chlink, zvorym): 
    # zvorym in ['Яндекс.Музыка', 'Звук']
    str_tuple = chstr.partition(f'<button data-frame-load="{sepstr}">Preview</button>')
    str_list = list(str_tuple)
    
    str_list[2] = str_list[2].replace(f'<a href="" target="_blank"><button disabled>{zvorym}</button>', 
                                      f'<a href="{chlink}" target="_blank"><button>{zvorym}</button>', 1)
    str_tuple = tuple(str_list)
    chstr = ''.join(str_tuple)
    return chstr

def do_amr_file(new_link, zvorym):
    amrLink = f'{amrsFolder}AMR {row.loc['date'][0:7]}.html'
    htmlFile = open(amrLink, 'r', encoding='utf-8')
    source_code = htmlFile.read()
    linksplit = row.loc['link'].split('/')
    id2find = linksplit[len(linksplit)-1]
    source_code = change_amr_button(source_code, id2find, new_link, zvorym)
            
    with open(amrLink, 'w') as h2r:
        h2r.write(source_code)
    h2r.close()   

#----------------------------------------------------------------------------------------------------

amnr_logger(f"{VERSION} (c)&(p) 2022-{str(datetime.datetime.now())[0:4]} by Viktor 'MushroomOFF' Gribov")

pdNR = pd.read_csv(newReleasesDB, sep=";")

prev_date = datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(days=15), '%Y-%m-%d')
isYMchanged = 0
isZVchanged = 0
for index, row in pdNR[(pdNR['Best_Fav_New_OK'].isin(['v','d','o'])) & (pdNR['link_ym'].isnull() | pdNR['link_zv'].isnull()) & (pdNR['date'] > prev_date)].iterrows():
    ym_result = ''
    zv_result = ''
    need2sendmes = 0
    ym_zv_search_string = f'{row.loc['artist'].replace('&amp;','&')} - {row.loc['album'].replace('&amp;','&')}'
    if pd.isna(row.loc['link_ym']): 
        ym_result = search_album_ym(ym_zv_search_string, row.loc['date'][0:4])
    if pd.isna(row.loc['link_zv']): 
        if ZVUK_ERROR == '':
            zv_result = search_album_zv(ym_zv_search_string)     
        
    if ((ym_result is not None) & (ym_result != '')) | ((zv_result is not None) & (zv_result != '')):
        amnr_logger(f'{index}. {row.loc['artist']} - {row.loc['album']}')
    if (ym_result is not None) & (ym_result != ''):    
        row.loc['link_ym'] = ym_result
        pdNR.loc[index,'link_ym'] = ym_result
        do_amr_file(ym_result, 'Яндекс.Музыка')
        isYMchanged += 1
        need2sendmes = 1
    if (zv_result is not None) & (zv_result != ''):
        row.loc['link_zv'] = zv_result
        pdNR.loc[index,'link_zv'] = zv_result
        do_amr_file(zv_result, 'Звук')
        isZVchanged += 1
        need2sendmes = 1

    if need2sendmes == 1:
        if row.loc['Best_Fav_New_OK'] == 'v' or row.loc['Best_Fav_New_OK'] == 'd':
            thread_name = 'New Releases'
        elif row.loc['Best_Fav_New_OK'] == 'o':
            thread_name = 'Top Releases'
        img_url = row.loc['imga'].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
        img_caption = f'*{ReplaceSymbols(row.loc['artist'].replace('&amp;','&'))}* \\- [{ReplaceSymbols(row.loc['album'].replace('&amp;','&'))}]({row.loc['link'].replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({row.loc['link']}){'' if pd.isna(row.loc['link_ym']) else f'\n\U0001F4A5 [Яндекс\\.Музыка]({row.loc['link_ym']})'}{'' if pd.isna(row.loc['link_zv']) else f'\n\U0001F50A [Звук]({row.loc['link_zv']})'}'
        message2send = send_photo_url(thread_name, img_url, img_caption)
        row.loc['TGmsgID'] = message2send
        pdNR.loc[index,'TGmsgID'] = message2send
        
if (isYMchanged + isZVchanged) > 0:
    pdNR.to_csv(newReleasesDB, sep=';', index=False)
    amnr_logger(f'New links: {isYMchanged} Yandex.Music, {isZVchanged} Zvuk')

if ZVUK_ERROR != '':
    amnr_logger(f'{ZVUK_ERROR}')

amnr_logger('[V] Done!')
