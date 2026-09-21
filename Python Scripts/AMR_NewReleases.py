import datetime
import os
import pandas as pd
import requests
import sqlite3
import traceback
import urllib.parse
from yandex_music import Client # for YM
from dotenv import load_dotenv
import amr_functions as amr

# ================= CONSTANTS & VARIABLES =================
SCRIPT_NAME = "New Releases"
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

DB_FOLDER = os.path.join(ROOT_FOLDER, 'Databases/')
DB_FILE = os.path.join(DB_FOLDER, 'music_releases.db')

message_new_releases = False
message_cs_releases = False
status_message = ''

HEADERS = {'Referer':'https://music.apple.com', 'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'}
session = requests.Session() 
session.headers.update(HEADERS)

# Yandex.Music ---------------------------
YM_CLIENT = Client(YM_TOKEN).init()

# Zvuk -----------------------------------
ZVUK_BASE_URL = "https://zvuk.com"
ZVUK_API_ENDPOINTS = {"lyrics": f"{ZVUK_BASE_URL}/api/tiny/lyrics", 
                      "stream": f"{ZVUK_BASE_URL}/api/tiny/track/stream", 
                      "graphql": f"{ZVUK_BASE_URL}/api/v1/graphql", 
                      "profile": f"{ZVUK_BASE_URL}/api/tiny/profile",
                      "check_token": f"{ZVUK_BASE_URL}/api/v2/tiny/profile"}
ZVUK_ERROR = ''


# ================= FUNCTIONS =================

def uri_encode(text: str) -> str:
    return urllib.parse.quote(text, safe="")

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


def is_token_anonymous_zv():
    """Check if my ZVUK token is active:
    False - token is not anonymous = my token is active
    True - token is anonymous = my token disabled, need a new one
    """
    response = session.get(ZVUK_API_ENDPOINTS["check_token"], headers=HEADERS, cookies=get_auth_cookies_zv())
    response.raise_for_status()
    zv_data = response.json()
    return zv_data['result']['profile']['is_anonymous']


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
#-----------------------------------------

# ================= DATABASE FUNCTIONS =================

def insert_new_release(release_data):
    """Вставить релиз в БД с явным преобразованием типов"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO new_releases
            (update_date, genre_category, artist, album, album_id, album_link, 
            album_link_ym, album_link_zv, cover_link, tg_message_id)

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(release_data['update_date']),
            str(release_data['genre_category']),
            str(release_data['artist']),
            str(release_data['album']),
            int(release_data['album_id']),
            str(release_data['album_link']),
            str(release_data['album_link_ym']) if release_data['album_link_ym'] else None,
            str(release_data['album_link_zv']) if release_data['album_link_zv'] else None,
            str(release_data['cover_link']),
            int(release_data['tg_message_id'])
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'Error inserting release {release_data.get("album_id")}: {e}')
        traceback.print_exc()
        return False


def check_new_release(album_id):
    """If album_id exists in db, then it's NOT new release (False)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM new_releases WHERE album_id = ?', (album_id,))
        result = cursor.fetchone()
        conn.close()
        if int(result[0]) > 0:
            return False
        return True
    except Exception as e:
        print(f'Error checking cover for {album_id}: {e}')
        return False


def check_my_artist(artist_id):
    """If artist_id exists in db, then it's my artist (True)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM artists WHERE artist_id = ?', (artist_id,))
        result = cursor.fetchone()
        conn.close()
        if int(result[0]) > 0:
            return True
        return False
    except Exception as e:
        print(f'Error checking cover for {artist_id}: {e}')
        return False
    

def soon_to_new_releases(current_date):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT sr.row_id, sr.artist_name, sr.album_name, sr.album_link, 
            sr.cover_link, sr.release_date FROM soon_releases sr 
            LEFT JOIN new_releases nr ON sr.album_link = nr.album_link 
            WHERE nr.album_link IS NULL AND sr.release_date <= ?
        ''', (current_date,))
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        print(f'Error getting artist to find: {e}')
        traceback.print_exc()
        return None


def update_soon_release(row_id, release_date, release_date_text):
    """Обновить ???"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE soon_releases SET release_date = ?, release_date_text = ? WHERE row_id = ?',
                       (release_date, release_date_text, row_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'Error updating ???: {e}')
        traceback.print_exc()
        return False


def check_new_soon_on_this_week(album_link):
    """If album_link exists in db, then it's NOT new release (False)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM soon_releases WHERE album_link = ?', (album_link,))
        result = cursor.fetchone()
        conn.close()
        if int(result[0]) > 0:
            return False
        return True
    except Exception as e:
        print(f'Error checking cover for {album_link}: {e}')
        return False


def insert_soon_release(release_data):
    """Вставить релиз в БД с явным преобразованием типов"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO soon_releases
            (update_date, artist_name, album_name, artist_link, 
            album_link, cover_link, release_date, release_date_text)

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(release_data['update_date']),
            str(release_data['artist_name']),
            str(release_data['album_name']),
            str(release_data['artist_link']),
            str(release_data['album_link']),
            str(release_data['cover_link']),
            str(release_data['release_date']),
            str(release_data['release_date_text'])
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'Error inserting release {release_data.get("album_link")}: {e}')
        traceback.print_exc()
        return False    


def next_week_releases(current_date):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT artist, album, release_date FROM my_releases 
            WHERE release_date <= ? AND rate_tag = 'd' 
            ORDER BY release_date ASC, main_artist ASC
        ''', (current_date,))
        result_this = cursor.fetchall()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT artist, album, release_date FROM my_releases 
            WHERE release_date > ? AND rate_tag = 'd' 
            ORDER BY release_date ASC, main_artist ASC
        ''', (current_date,))
        result_next = cursor.fetchall()
        conn.close()
        return result_this, result_next
    except Exception as e:
        print(f'Error getting artist to find: {e}')
        traceback.print_exc()
        return None


# ================= MAIN FUNCTIONS =================

def find_room_link(category_link, category_name):
    """ Searching correct link to room genre"""
    request = session.get(category_link)
    request.encoding = 'UTF-8'
    response = request.text
    start_position = response.find(f'{"{"}"title":"{category_name}"')
    begin_position = response.find('"id":"', start_position) + len('"id":"')
    end_position = response.find('"', begin_position)
    category_id = response[begin_position:end_position].strip()
    room_link = f'{category_link[:category_link.find('/curator')]}/room/{category_id}'
    return room_link
    

def write_to_db(artist, album, update_date, is_my_artist, image_link, album_link, category_abbr, album_id):
    global message_new_releases
    
    ym_zv_search_string = f'{artist.replace('&amp;','&')} - {album.replace('&amp;','&')}' 
    ym_year = update_date[0:4]
    ym_result = ''
    zv_result = ''
    ym_result = search_album_ym(ym_zv_search_string, ym_year)
    if not ZVUK_ERROR:
        zv_result = search_album_zv(ym_zv_search_string)
    else:
        zv_result = ''

    message_id = 0
    if is_my_artist:
        image_url = image_link.replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
        image_caption = f'*{artist.replace('&amp;','&')}* \\- [{album.replace('&amp;','&')}]({album_link.replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({album_link}){f'\n\U0001F4A5 [Яндекс\\.Музыка]({ym_result})' if ym_result is not None and ym_result != '' else ''}{f'\n\U0001F50A [Звук]({zv_result})' if zv_result is not None and zv_result != '' else ''}'
        message_id = amr.send_message(image_caption, TOKEN, CHAT_ID, image_url, 'New Releases')

        message_new_releases = True

    new_release_data = {
        'update_date': update_date, 
        'genre_category': category_abbr, 
        'artist': artist.replace('&amp;','&'), 
        'album': album.replace('&amp;','&'), 
        'album_id': album_id, 
        'album_link': album_link, 
        'album_link_ym': ym_result if ym_result is not None else '', # YM & Zvuk search
        'album_link_zv': zv_result if zv_result is not None else '', # YM & Zvuk search
        'cover_link': image_link, 
        'tg_message_id': message_id
    }

    if not insert_new_release(new_release_data):
        print(f'  ✗ Failed to insert: {new_release_data["album"]}')


def collect_new_releases(category_link, category_abbr):
    update_date = datetime.datetime.now().strftime('%Y-%m-%d') 

    request = session.get(category_link)
    request.encoding = 'UTF-8'
    response = request.text

    li_list = response.split('<li class="grid-item ')
    for index, li in enumerate(li_list):
        if index > 0:  
            pic_srcset_list = li.split('<picture ')[1].split('srcset="')
            
            image_link = pic_srcset_list[1].split(' ')[0]

            release_list = pic_srcset_list[2].split('<div class="product-lockup__title-link ')[1]
            
            link_position_begin = release_list.find('<a href="') + len('<a href="')
            link_position_end = release_list.find('"', link_position_begin)
            album_link = release_list[link_position_begin:link_position_end].strip()
            album_id = album_link[album_link.rfind('/') + 1:]

            link_position_end = release_list.find('</a')
            link_position_begin = release_list.rfind('>', 0, link_position_end) + len('>')
            album = release_list[link_position_begin:link_position_end].strip()
            
            artist_line_list = release_list.split('" class="product-lockup__subtitle link')
            artist_list = []
            artist_id_list = []
            is_my_artist = False # Check Artist ID
            for idx, artist_line in enumerate(artist_line_list):
                if idx > 0:
                    link_position_end = artist_line.find('</a')
                    link_position_begin = artist_line.rfind('>', 0, link_position_end) + len('>')
                    artist_list.append(artist_line[link_position_begin:link_position_end].strip())
                    artist_id = artist_line_list[idx-1][artist_line_list[idx-1].rfind('/') + len('/'):]
                    artist_id_list.append(artist_id[artist_id.rfind('/') + len('/'):])
                    is_my_artist = check_my_artist(artist_id)
            artist = '; '.join(artist_list)
            
            if check_new_release(album_id) and artist:
                write_to_db(artist, album, update_date, is_my_artist, image_link, album_link, category_abbr, album_id)


def coming_soon(category_link):
    global message_cs_releases
    
    update_date = datetime.datetime.now().strftime('%Y-%m-%d') 

    new_cs_releases_df = pd.DataFrame(columns=['apple_music_sort', 'aria_label', 'artwork_bg_color',
                                               'picture_srcset_webp', 'picture_srcset_jpeg',
                                               'album_link', 'album', 'artist_list', 'artist_id_list', 'artist_link_list',
                                               'apple_music_release_date', 'apple_music_release_date_text',
                                               'is_new_on_this_week'])
    
    request = session.get(category_link)
    request.encoding = 'UTF-8'
    response = request.text
    li_list = response.split('<li class="grid-item ')
    for li_index, li in enumerate(li_list):
        if li_index > 0:  
            data_blocks = li.split('data-testid="')

            artist_list = []
            artist_link_list = []
            artist_id_list = []
            
            for index, data_block in enumerate(data_blocks):
                block_name = data_block[:data_block.find('"')]
                if block_name == 'square-lockup-wrapper':
                    link_position_begin = data_block.find('aria-label="') + len('aria-label="')
                    link_position_end = data_block.find('"', link_position_begin)
                    aria_label = data_block[link_position_begin:link_position_end].strip()
            
                if block_name == 'artwork-component':
                    srcsets = data_block.split('srcset="')
                    for idx, srcset in enumerate(srcsets):
                        if idx == 0:
                            link_position_begin = data_block.find('--artwork-bg-color: ') + len('--artwork-bg-color: ')
                            link_position_end = data_block.find(';', link_position_begin)
                            artwork_bg_color = data_block[link_position_begin:link_position_end].strip()
                        elif idx == 1:
                            picture_srcset_webp = srcset[:srcset.find('"')]
                        elif idx == 2:
                            picture_srcset_jpeg = srcset[:srcset.find('"')]
                    
                if block_name == 'product-lockup-title':
                    link_position_end = data_block.find('</a')
                    link_position_begin = data_block.rfind('>', 0, link_position_end) + len('>')
                    album = data_block[link_position_begin:link_position_end].strip()
                    
                    link_position_begin = data_blocks[index - 1].find('<a href="') + len('<a href="')
                    link_position_end = data_blocks[index - 1].find('"', link_position_begin)
                    album_link = data_blocks[index - 1][link_position_begin:link_position_end].strip()
            
                if block_name == 'product-lockup-subtitle':
                    link_position_end = data_block.find('</a')
                    link_position_begin = data_block.rfind('>', 0, link_position_end) + len('>')
                    artist = data_block[link_position_begin:link_position_end].strip()
                    artist_list.append(artist)
                    
                    link_position_begin = data_blocks[index - 1].find('<a href="') + len('<a href="')
                    link_position_end = data_blocks[index - 1].find('"', link_position_begin)
                    artist_link = data_blocks[index - 1][link_position_begin:link_position_end].strip()
                    artist_link_list.append(artist_link)
                    artist_id = artist_link[artist_link.rfind('/') + 1:]
                    artist_id_list.append(artist_id)

            # Searching release date
            request = session.get(album_link)
            request.encoding = 'UTF-8'
            response = request.text

            date_time_string = 'data-testid="tracklist-footer-description">'
            date_time_begin = response.find(date_time_string)
            date_time_end = response.find('\n', date_time_begin)
            date_time_text = response[date_time_begin + len(date_time_string):date_time_end]
            date_time = datetime.datetime.strptime(date_time_text, '%B %d, %Y')

            new_cs_releases_df.loc[len(new_cs_releases_df.index)] = [li_index, aria_label, artwork_bg_color, 
                                                                     picture_srcset_webp, picture_srcset_jpeg, 
                                                                     album_link, album, artist_list, artist_id_list, artist_link_list, 
                                                                     date_time, date_time_text, '']
            
            print(f'Comming Soon [{li_index}]', end='\r')
    
    for index, row in new_cs_releases_df.sort_values(by=['apple_music_release_date', 'apple_music_sort'], ascending=[True, True]).iterrows():
        if row['apple_music_release_date'] <= datetime.datetime.now():
            row['apple_music_release_date_text'] = 'Delayed'

        if check_new_soon_on_this_week(row['album_link']):
            row['is_new_on_this_week'] = 1

            image_link_jpeg = row['picture_srcset_jpeg'][0:row['picture_srcset_jpeg'].find(' ')]
            artist = '; '.join(row['artist_list'])

            soon_release_data = {
                'update_date': update_date,
                'artist_name': artist.replace('&amp;','&'), 
                'album_name': row['album'].replace('&amp;','&'), 
                'artist_link': row['artist_link_list'][0],
                'album_link': row['album_link'],
                'cover_link': image_link_jpeg,
                'release_date': row['apple_music_release_date'][0:10], # HERE'S might be an ERROR!!!
                'release_date_text': row['apple_music_release_date_text']
            }

            if not insert_soon_release(soon_release_data):
                print(f'  ✗ Failed to insert: {soon_release_data["album_name"]}')

            is_my_artist = False
            for artist_id in row['artist_id_list']:
                if check_my_artist(artist_id):
                    is_my_artist = True

            message_id = 0
            if is_my_artist:
                image_url = image_link_jpeg.replace('296x296bb-60.jpg', '632x632bb.webp').replace('296x296bf-60.jpg', '632x632bf.webp')
                image_caption = f'*{artist.replace('&amp;','&')}* \\- [{row['album'].replace('&amp;','&')}]({row['album_link'].replace('://','://embed.')})\n{str(row['apple_music_release_date'])[0:10]}'
                message_id = amr.send_message(image_caption, TOKEN, CHAT_ID, image_url, 'Coming Soon')
                message_cs_releases = True


def collect_cs_releases(category_abbr):
    """ Moving delayed Coming soon releases to New Releases"""
    global status_message
    
    cs_to_new_releases_df = pd.DataFrame(columns=['artist', 'album', 'link', 'image_link'])
    
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    soon2new_releases = soon_to_new_releases(current_date)
    # 0 - sr.row_id, 1 - sr.artist_name, 2 - sr.album_name, 
    # 3 - sr.album_link, 4 - sr.cover_link, 5 - sr.release_date
    if soon2new_releases:
        for row in soon2new_releases:
            request = session.get(row[3])
            request.encoding = 'UTF-8'
            response = request.text
            date_time_string = 'data-testid="tracklist-footer-description">'
            date_time_begin = response.find(date_time_string)
            if date_time_begin > -1:
                date_time_end = response.find('\n', date_time_begin)
                date_time_text = response[date_time_begin + len(date_time_string):date_time_end]
                date_time = datetime.datetime.strptime(date_time_text, '%B %d, %Y')
                if row[5] != date_time and date_time > datetime.datetime.now():
                    update_soon_release(row[0], str(date_time)[0:10], date_time_text)
                else:
                    cs_to_new_releases_df.loc[len(cs_to_new_releases_df.index)] = [row[1], row[2], row[3], row[4]]
            else:
                soon_db_error = f"⚠️ Coming Soon DB bad link: [{row[0]}] {row[1]} - {row[2]}"
                print(soon_db_error)
                status_message += f"\n{soon_db_error}"

    # Main work
    if len(cs_to_new_releases_df):
        for _, row in cs_to_new_releases_df.iterrows():
            album_id = row['link'][row['link'].rfind('/') + 1:]
            #                                                      is_my_artist
            write_to_db(row['artist'], row['album'], current_date, None, row['image_link'], row['link'], category_abbr, album_id)
        
        del cs_to_new_releases_df


def next_week_releases_sender():
    base_url = "https://rutracker.org/forum/tracker.php?nm="
    this_week_message = ''
    next_week_message = ''
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    tw_releases, nw_releases = next_week_releases(current_date)
    # 0 - artist, 1 - album, 2 - release_date

    this_week_message += '\U0001F50E This week releases:'
    if tw_releases:
        for row in tw_releases:
            artist_name = row[0].replace('&amp;','&')
            base_line = f"{base_url}{uri_encode(artist_name)}"
            this_week_message += f"\n*[{artist_name}]({base_line})* - {row[1].replace('&amp;','&')}"
    else:
        this_week_message += '\n\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F'

    week_date = ''
    next_week_message += '\U000023F3 Next weeks releases:'
    if nw_releases:
        for row in nw_releases:
            if week_date != row[2]:
                week_date = row[2]
                next_week_message += f'\n\n*{week_date}*'
            artist_name = row[0].replace('&amp;','&')
            base_line = f"{base_url}{uri_encode(artist_name)}"
            next_week_message += f"\n*[{artist_name}]({base_line})* - {row[1].replace('&amp;','&')}"
    else:
        next_week_message += '\n\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F'

    amr.send_message(next_week_message, TOKEN, CHAT_ID, None, 'Next Week Releases')
    amr.send_message(this_week_message, TOKEN, CHAT_ID, None, 'Next Week Releases')


def main():
    global status_message

    if ENV == 'Local': 
        amr.print_name(SCRIPT_NAME, VERSION)

    app_version = f'v.{VERSION} [{ENV}]'
    welcome_message = f'🚀 *{SCRIPT_NAME}*\n{app_version}'
    amr.send_message(welcome_message, TOKEN, LOGGER_ID, None, None)

    if is_token_anonymous_zv():
        status_message += f'\n⚠️ Zvuk token disabled'

    album_categories = [
        {
            "category_type": 'New Releases',
            "category_link": 'https://music.apple.com/us/curator/apple-music-metal/976439543',
            "category_name": 'METAL',
            "category_abbr": 'M'
        },
        {
            "category_type": 'New Releases',
            "category_link": 'https://music.apple.com/us/curator/apple-music-hard-rock/979231690',
            "category_name": 'ALTERNATIVE & HARD ROCK',
            "category_abbr": 'HR'
        },
        {
            "category_type": 'New Releases',
            "category_link": 'https://music.apple.com/ru/curator/apple-music-метал/976439543',
            "category_name": 'METAL - RU',
            "category_abbr": 'MRU'
        },
        {
            "category_type": 'New Releases',
            "category_link": 'https://music.apple.com/ru/curator/apple-music-хард-рок/979231690',
            "category_name": 'ALTERNATIVE & HARD ROCK - RU',
            "category_abbr": 'HRRU'
        },
        {
            "category_type": 'Coming Soon',
            "category_link": 'https://music.apple.com/us/curator/apple-music-metal/976439543',
            "category_name": 'METAL - CS',
            "category_abbr": 'MCS'
        }
    ]

    for category in album_categories:
        category_link = find_room_link(category["category_link"] , category["category_type"])
        if category["category_name"].find(' - ') > -1:
            logger_category = category["category_name"].replace(category["category_name"][:category["category_name"].find(' - ')], category["category_name"][:category["category_name"].find(' - ')].title())
        else:
            logger_category = category["category_name"].title()

        if category["category_type"] == 'New Releases':
            collect_new_releases(category_link, category["category_abbr"])
            print(logger_category)
            status_message += f'\n✅ {logger_category}'
            amr.db_backup(DB_FILE)
        elif category["category_type"] == 'Coming Soon':
            coming_soon(category_link)
            print('Coming Soon')
            status_message += f'\n✅ Coming Soon'
            amr.db_backup(DB_FILE)

            collect_cs_releases(category["category_abbr"])
            print(logger_category)
            status_message += f'\n✅ {logger_category}'
            amr.db_backup(DB_FILE)

    if not message_new_releases:
        amr.send_message('New Releases: \U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F', TOKEN, LOGGER_ID, None, None)
    if not message_cs_releases:
        amr.send_message('Coming Soon: \U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F', TOKEN, LOGGER_ID, None, None)

    if ZVUK_ERROR:
        status_message += f'\n⚠️ {ZVUK_ERROR}'
    
    amr.send_message(status_message, TOKEN, LOGGER_ID, None, None)

    next_week_releases_sender()

if __name__ == "__main__":
    main()
