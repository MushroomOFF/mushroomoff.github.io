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
SCRIPT_NAME = "New Releases"
VERSION = "2.026.02"
ENV = 'Local'
if os.getenv("GITHUB_ACTIONS") == "true":
    ENV = 'GitHub'
    # GitHub version will always run complete list of artists

if ENV == 'Local':
    ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
elif ENV == 'GitHub':
    ROOT_FOLDER = ''
AMR_FOLDER = os.path.join(ROOT_FOLDER, 'AMRs/')
DB_FOLDER = os.path.join(ROOT_FOLDER, 'Databases/')
NEW_RELEASES_DB = os.path.join(DB_FOLDER, 'AMR_newReleases_DB.csv')
CS_RELEASES_DB = os.path.join(DB_FOLDER, 'AMR_csReleases_DB.csv')
RELEASES_DB = os.path.join(DB_FOLDER, 'AMR_releases_DB.csv')
ARTIST_ID_DB = os.path.join(DB_FOLDER, 'AMR_artisitIDs.csv')
LOG_FILE = os.path.join(ROOT_FOLDER, 'status.log')

message_new_releases = False
message_cs_releases = False

HEADERS = {'Referer':'https://music.apple.com', 'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'}
session = requests.Session() 
session.headers.update(HEADERS)

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

# HTML -----------------------------------
HTML_HEAD = """<head>
  <meta charset="utf-8">
  <title>Alternative & Metal Releases</title>
  <link rel="stylesheet" type="text/css" href="../../Resources/styles.css" />
  <SCRIPT language=JavaScript type=text/JavaScript>
    <!--
    function show(id) {
      if(document.getElementById("show" + id).style.display == 'none') {
        document.getElementById("show" + id).style.display = '';
      }else{
        document.getElementById("show" + id).style.display = 'none';
      }
    }

    function show_tr(id) {
      var elms;
      if (id=="v") {
        elms = document.querySelectorAll("[id='v']");
      } else if (id=="x") {
        elms = document.querySelectorAll("[id='x']");
      } else if (id=="d") {
        elms = document.querySelectorAll("[id='d']");
      } else if (id=="o") {
        elms = document.querySelectorAll("[id='o']");
      } else if (id=="") {
        elms = document.querySelectorAll("[id='']");
      }
      for (var i = 0; i < elms.length; i++) {
        if (elms[i].style.display == 'none') {
          elms[i].style.display = '';
        } else {
          elms[i].style.display = 'none';
        }
      }
    }
    //-->
  </SCRIPT>
</head>

<body>
  <input id="bV" type="button" value="V" onclick="show_tr('v');" class="bV" />
  <input id="bD" type="button" value="D" onclick="show_tr('d');" class="bD" />
  <input id="bX" type="button" value="O" onclick="show_tr('o');" class="bO" />
  <input id="bX" type="button" value="X" onclick="show_tr('x');" class="bX" />
  <input id="bE" type="button" value="  " onclick="show_tr('');" class="bE" />
  <input type="button" onclick="location.href='../../index.html';" value="Index"  class="bI"/>
  <hr>\n"""

HTML_END = """  </table>
  <hr>\n"""

HTML_FINAL = """  <!-- End of File -->
  <script id="rendered-js" >
    [...document.querySelectorAll('[data-frame-load]')].forEach(button => {
      button.addEventListener('click', () => {
        const group = button.getAttribute('data-frame-load');
        [...document.querySelectorAll(`[data-frame-group="${group}"]`)].forEach(frame => {
          javascript:show(frame.getAttribute('data-frame-group') + '_');
          frame.setAttribute('src', frame.getAttribute('data-frame-src'));
        });
      });
    });
  </script>
</body>\n"""

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

def make_html_start(update_date, category_name, category_color):
    tr_id = f'"{update_date}_{category_name}"'.lower().replace(' ','_')
    html_start = f"""  <table border="1">
    <tr id={tr_id}><th colspan="2" style="background: linear-gradient(to right, {category_color});">{update_date} | {category_name}</th></tr>
    <tr><th width="100px">Cover</th><th width="600px">Album</th></tr>\n"""    
    return html_start

def make_html_text(artist, album, image_link, album_link, artist_album_name, album_id, ym_result, zv_result):
    html_text = f"""  <!-- {artist.replace('&amp;','&')} - {album.replace('&amp;','&')} -->
    <tr style="display:;" id=''>
      <td><a href="{image_link.replace('296x296bb.webp', '100000x100000-999.jpg').replace('296x296bf.webp', '100000x100000-999.jpg')}" target="_blank"><img src="{image_link}" height="100px"></a></td>
      <td class="album_name"><a href="{album_link}" target="_blank"><b>{artist_album_name}</a><br><br><button data-frame-load="{album_id}">Preview</button>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href="{ym_result if ym_result is not None else ''}" target="_blank"><button{' disabled' if ym_result is None or ym_result == '' else ''}>Яндекс.Музыка</button></a>&nbsp;<a href="{zv_result if zv_result is not None else ''}" target="_blank"><button{' disabled' if zv_result is None or zv_result == '' else ''}>Звук</button></a></td>
    </tr> 
    <tr style="display:none;" id="show{album_id}_"><td colspan="2"><iframe id="embedPlayer" data-frame-group="{album_id}" data-frame-src="{album_link.replace('://', '://embed.')}?app=music&amp;itsct=music_box_player&amp;itscg=30200&amp;ls=1&amp;theme=light" height="450px" frameborder="0" sandbox="allow-forms allow-popups allow-same-origin allow-scripts allow-top-navigation-by-user-activation" allow="autoplay *; encrypted-media *; clipboard-write" style="width: 100%; overflow: hidden; border-radius: 10px; transform: translateZ(0px); animation: 2s ease 0s 6 normal none running loading-indicator; background-color: rgb(228, 228, 228);"></iframe></td></tr>\n"""
    return html_text

def make_artist_a_block(artist_list, artist_link_list):
    html_a_list = []
    for index, artist in enumerate(artist_list):
        html_a_list.append(f'''
             <a class="product-lockup__subtitle svelte-21e67y link" data-testid="product-lockup-subtitle" href="{artist_link_list[index]}">
              {artist}</a>''')
    artist_a_block = ',  '.join(html_a_list)
    return artist_a_block

def make_html_li_text(aria_label, artwork_bg_color, picture_srcset_webp, picture_srcset_jpeg, artist_list, artist_link_list, album, album_link, new_cs_release_css):
    artist_a_block = make_artist_a_block(artist_list, artist_link_list)
    html_li = f'''
       <li class="grid-item svelte-1p1n7nd" data-testid="grid-item">
        <div aria-label="{aria_label}" class="product-lockup svelte-21e67y" data-testid="product-lockup">
         <div aria-hidden="false" class="product-lockup__artwork svelte-21e67y has-controls">
          <div class="artwork-component artwork-component--aspect-ratio artwork-component--orientation-square svelte-e284u3 artwork-component--fullwidth artwork-component--has-borders" data-testid="artwork-component" style="
                  --artwork-bg-color: {artwork_bg_color};
                  --aspect-ratio: 1;
                  --placeholder-bg-color: {artwork_bg_color};
             ">
           <picture class="svelte-e284u3">
            <source sizes=" (max-width:1319px) 296px,(min-width:1320px) and (max-width:1679px) 316px,316px" srcset="{picture_srcset_webp}" type="image/webp"/>
            <source sizes=" (max-width:1319px) 296px,(min-width:1320px) and (max-width:1679px) 316px,316px" srcset="{picture_srcset_jpeg}" type="image/jpeg"/>
            <img alt="{aria_label}" class="artwork-component__contents artwork-component__image svelte-e284u3" decoding="async" height="316" loading="lazy" role="presentation" src="/assets/artwork/1x1.gif" style="opacity: 1;" width="316"/>
           </picture>
          </div>
         </div>
         <div class="product-lockup__content svelte-21e67y">
          <div class="product-lockup__content-details svelte-21e67y">
           <p class="product-lockup__subtitle-links svelte-21e67y product-lockup__subtitle-links--singlet" data-testid="product-lockup-subtitles">
            <div class="multiline-clamp svelte-1qrlry multiline-clamp--overflow" style="--lineClamp: 1;">{artist_a_block}
            </div>
           </p>           
           <div class="product-lockup__title-link svelte-21e67y product-lockup__title-link--multiline">
            <div class="multiline-clamp svelte-1qrlry multiline-clamp--overflow" style="--lineClamp: 2;">
             {new_cs_release_css} data-testid="product-lockup-title" href="{album_link}">
              {album}
             </a>
            </div>
           </div>
          </div>
         </div>
        </div>
       </li>\n'''
    return html_li

def make_html_li_final(date_of_update):
    html_li = f'''
      </ul>
    </div> 
  </div>\n</div>\n<div class="main">\n  <i>Updated: {date_of_update}</i>\n</div>\n</body>\n'''
    return html_li

def write_to_html(update_date, html_text, html_start):
    current_year = update_date[0:4]
    current_month = update_date[0:7]
    current_month_text = datetime.datetime.strptime(update_date, '%Y-%m-%d').strftime('%B')

    with open(f'{ROOT_FOLDER}index.html', 'r') as index_file:
        last_month_index = index_file.read()
        last_month_slice = last_month_index[last_month_index.find('<a href="AMRs'):last_month_index.find('</a><br>')]
        last_month = last_month_slice[last_month_slice.rfind(' ') + 1:last_month_slice.rfind('.html">')]
    last_month_text = datetime.datetime.strptime(last_month, '%Y-%m').strftime('%B')
    last_year = last_month[0:4]

    is_new_month = False
    is_new_year = False

    if current_year != last_year:
        is_new_year = True
        with open(f'{ROOT_FOLDER}index.html', 'r+') as index_file:
            index_content = index_file.read()
            index_content = index_content.replace(f'\n    <h2 class="title svelte-hprj71" data-testid="header-title">{last_year}:</h2>',
                                                  f'\n    <h2 class="title svelte-hprj71" data-testid="header-title">{current_year}:</h2>\n        <a href="AMRs/{current_year}/AMR {current_month}.html">{current_month_text}</a><br>\n    <h2 class="title svelte-hprj71" data-testid="header-title">{last_year}:</h2>')
            index_file.seek(0, 0)
            index_file.write(index_content)
    else:
        if current_month != last_month:
            is_new_month = True
            with open(f'{ROOT_FOLDER}index.html', 'r+') as index_file:
                index_content = index_file.read()
                index_content = index_content.replace(f'\n        <a href="AMRs/{last_year}/AMR {last_month}.html">{last_month_text}</a><br>',
                                                      f'\n        <a href="AMRs/{last_year}/AMR {last_month}.html">{last_month_text}</a> | \n        <a href="AMRs/{current_year}/AMR {current_month}.html">{current_month_text}</a><br>')
                index_file.seek(0, 0)
                index_file.write(index_content)

    if html_text:
        if is_new_month or is_new_year:
            with open(f'{AMR_FOLDER}{current_year}/AMR {current_month}.html', 'w') as html_file:
                html_file.write(HTML_HEAD + '\n' + html_start + html_text + HTML_END + '\n' + HTML_FINAL)         
        else:
            with open(f'{AMR_FOLDER}{current_year}/AMR {current_month}.html', 'r+') as html_file:
                html_content = html_file.read()
                html_content = html_content.replace(HTML_HEAD, '')
                html_file.seek(0, 0)
                html_file.write(HTML_HEAD + '\n' + html_start + html_text + HTML_END + '\n' + html_content)

def find_room_link(category_link, category_name):
    """ Searching correct link to room genre
    """
    request = session.get(category_link)
    request.encoding = 'UTF-8'
    response = request.text
    start_position = response.find(f'{"{"}"title":"{category_name}"')
    begin_position = response.find('"id":"', start_position) + len('"id":"')
    end_position = response.find('"', begin_position)
    category_id = response[begin_position:end_position].strip()
    room_link = f'{category_link[:category_link.find('/curator')]}/room/{category_id}'
    return room_link

def write_to_csv(artist, album, update_date, is_my_artist, image_link, album_link, category_abbr, album_id):
    global ZVUK_ERROR, TOKEN, CHAT_ID, message_new_releases
    
    field_names = ['date', 'category', 'artist', 'album', 'best_fav_new_ok', 'link', 'link_ym', 'link_zv', 'image_link', 'album_id', 'tg_message_id']
    artist_album_name = f'{artist} - {album}'

    ym_zv_search_string = f'{artist.replace('&amp;','&')} - {album.replace('&amp;','&')}' 
    ym_year = update_date[0:4]
    ym_result = ''
    zv_result = ''
    ym_result = search_album_ym(ym_zv_search_string, ym_year)
    if not ZVUK_ERROR:
        zv_result = search_album_zv(ym_zv_search_string)
    else:
        zv_result = ''

    artist_album_name = artist_album_name.replace(artist, f'{artist}</b>') if len(artist_album_name) < 80 else f'{artist_album_name[:artist_album_name[:80].rfind(' ') + 1].replace(artist, f'{artist}</b>')}<br>{artist_album_name[artist_album_name[:80].rfind(' ') + 1:]}'

    message_id = 0
    if is_my_artist:
        image_url = image_link.replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
        image_caption = f'*{amr.replace_symbols_markdown_v2(artist.replace('&amp;','&'))}* \\- [{amr.replace_symbols_markdown_v2(album.replace('&amp;','&'))}]({album_link.replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({album_link}){f'\n\U0001F4A5 [Яндекс\\.Музыка]({ym_result})' if ym_result is not None and ym_result != '' else ''}{f'\n\U0001F50A [Звук]({zv_result})' if zv_result is not None and zv_result != '' else ''}'
        message_id = amr.send_photo('New Releases', image_caption, image_url, TOKEN, CHAT_ID)
        message_new_releases = True

    with open(NEW_RELEASES_DB, 'a+', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, delimiter=';', fieldnames=field_names)
        writer.writerow({'date': update_date, 
                         'category': category_abbr, 
                         'artist': artist.replace('&amp;','&'), 
                         'album': album.replace('&amp;','&'), 
                         'best_fav_new_ok': '', 
                         'link': album_link, 
                         'link_ym': ym_result if ym_result is not None else '', # YM & Zvuk search
                         'link_zv': zv_result if zv_result is not None else '', # YM & Zvuk search
                         'image_link': image_link, 
                         'album_id': album_id, 
                         'tg_message_id': message_id})
    
    return artist_album_name, ym_result, zv_result

def collect_new_releases(category_link, category_name, category_color, category_abbr):
    global message_new_releases

    request = session.get(category_link)
    request.encoding = 'UTF-8'
    
    update_date = datetime.datetime.now().strftime('%Y-%m-%d') 

    html_start = make_html_start(update_date, category_name, category_color)
    html_text = ''

    new_releases_df = pd.read_csv(NEW_RELEASES_DB, sep=";")
    artist_id_df = pd.read_csv(ARTIST_ID_DB, sep=";")

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

            is_new_release = True        
            if int(album_id) in new_releases_df['album_id'].values:
                is_new_release = False

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
                    if int(artist_id) in artist_id_df['mainId'].values:
                        is_my_artist = True
            artist = '; '.join(artist_list)
            
            if is_new_release and artist:
                # Write informtaion to CSV
                artist_album_name, ym_result, zv_result = write_to_csv(artist, album, update_date, is_my_artist, image_link, album_link, category_abbr, album_id)
                # Add information to HTML
                html_text += make_html_text(artist, album, image_link, album_link, artist_album_name, album_id, ym_result, zv_result)

    # Save HTML file
    write_to_html(update_date, html_text, html_start)

    del new_releases_df
    del artist_id_df

def collect_cs_releases(category_name, category_color, category_abbr):
    """ Moving delayed Coming soon releases to New Releases  
    """
    field_names = ['date', 'category', 'artist', 'album', 'best_fav_new_ok', 'link', 'link_ym', 'link_zv', 'image_link', 'album_id', 'tg_message_id']
    
    # Preparation
    new_releases_df = pd.read_csv(NEW_RELEASES_DB, sep=";")
    cs_releases_df = pd.read_csv(CS_RELEASES_DB, sep=";")
    cs_to_new_releases_df = pd.DataFrame(columns=['artist', 'album', 'link', 'image_link'])

    for index, row in cs_releases_df.iterrows():
        if datetime.datetime.strptime(row['release__date'], "%Y-%m-%d %H:%M:%S") <= datetime.datetime.now():
            if not len(new_releases_df.loc[new_releases_df['link'] == row['album__href']]):
                request = session.get(row['album__href'])
                request.encoding = 'UTF-8'
                response = request.text
                date_time_string = 'data-testid="tracklist-footer-description">'
                date_time_begin = response.find(date_time_string)
                date_time_end = response.find('\n', date_time_begin)
                date_time_text = response[date_time_begin + len(date_time_string):date_time_end]
                date_time = datetime.datetime.strptime(date_time_text, '%B %d, %Y')
                if row['release__date'] != date_time and date_time > datetime.datetime.now():
                    cs_releases_df.loc[index, 'release__date'] = date_time
                    cs_releases_df.loc[index, 'release__date_text'] = date_time_text
                else:
                    cs_to_new_releases_df.loc[len(cs_to_new_releases_df.index)] = [row['artist__name'], row['album__name'], row['album__href'], row['album_cover__jpeg']]

    cs_releases_df.to_csv(CS_RELEASES_DB, sep=';', index=False)
    del new_releases_df
    del cs_releases_df

    # Main work
    if len(cs_to_new_releases_df):

        update_date = datetime.datetime.now().strftime('%Y-%m-%d')

        html_start = make_html_start(update_date, category_name, category_color)
        html_text = ''

        with open(NEW_RELEASES_DB, 'a+', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, delimiter=';', fieldnames=field_names)

            for index, row in cs_to_new_releases_df.iterrows():

                album_id = row['link'][row['link'].rfind('/') + 1:]

                #                                                                                                is_my_artist
                # Write informtaion to CSV                                                                       v
                artist_album_name, ym_result, zv_result = write_to_csv(row['artist'], row['album'], update_date, '', row['image_link'], row['link'], category_abbr, album_id)
                
                # Add information to HTML
                html_text += make_html_text(row['artist'], row['album'], row['image_link'], row['link'], artist_album_name, album_id, ym_result, zv_result)
        
        # Save HTML file
        write_to_html(update_date, html_text, html_start)
        
        del cs_to_new_releases_df

def coming_soon(category_link):
    global message_cs_releases
    
    request = session.get(category_link)
    request.encoding = 'UTF-8'

    update_date = datetime.datetime.now().strftime('%Y-%m-%d') 
    html_li = ''

    artist_id_df = pd.read_csv(ARTIST_ID_DB, sep=";")

    new_cs_releases_df = pd.DataFrame(columns=['apple_music_sort', 'aria_label', 'artwork_bg_color',
                                               'picture_srcset_webp', 'picture_srcset_jpeg',
                                               'album_link', 'album', 'artist_list', 'artist_id_list', 'artist_link_list',
                                               'apple_music_release_date', 'apple_music_release_date_text',
                                               'is_new_on_this_week'])
    
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
            
            # no logger here!
            print(f'Comming Soon [{li_index}]', end='\r')
    
    apple_music_release_date_text = 'Date 0, 9999'
    for index, row in new_cs_releases_df.sort_values(by=['apple_music_release_date', 'apple_music_sort'], ascending=[True, True]).iterrows():
        # Here is <li> building construction:
        if row['apple_music_release_date'] <= datetime.datetime.now():
            row['apple_music_release_date_text'] = 'Delayed'
        if apple_music_release_date_text != row['apple_music_release_date_text']:
            if apple_music_release_date_text != 'Date 0, 9999':
                html_li += '''
      </ul>\n'''

            html_li += f'''      <div class="main-date">
        <h2 class="title svelte-hprj71" data-testid="header-title">{row['apple_music_release_date_text']}</h2>
      </div>    
      <ul class="grid svelte-1p1n7nd grid--flow-row" data-testid="grid">\n'''
            
            apple_music_release_date_text = row['apple_music_release_date_text']

        # Always load new CS_RELEASES_DB, because later we write new rows into it
        cs_releases_df = pd.read_csv(CS_RELEASES_DB, sep=";")

        if not len(cs_releases_df.loc[cs_releases_df['album__href'] == row['album_link']]):
            row['is_new_on_this_week'] = 1

            field_names = ['update__date', 'album_cover__jpeg', 'album__href', 'album__name', 'artist__href', 'artist__name', 'release__date', 'release__date_text']
            image_link_jpeg = row['picture_srcset_jpeg'][0:row['picture_srcset_jpeg'].find(' ')]
            artist = '; '.join(row['artist_list'])

            with open(CS_RELEASES_DB, 'a+', newline='') as csv_file:
                writer = csv.DictWriter(csv_file, delimiter=';', fieldnames=field_names)
                writer.writerow({'update__date': update_date,
                                 'album_cover__jpeg': image_link_jpeg,
                                 'album__href': row['album_link'],
                                 'album__name': row['album'].replace('&amp;','&'), 
                                 'artist__href': row['artist_link_list'][0],
                                 'artist__name': artist.replace('&amp;','&'), 
                                 'release__date': row['apple_music_release_date'],
                                 'release__date_text': row['apple_music_release_date_text']})

            is_my_artist = False
            for artist_id in row['artist_id_list']:
                if int(artist_id) in artist_id_df['mainId'].values:
                    is_my_artist = True

            message_id = 0
            if is_my_artist:
                image_url = image_link_jpeg.replace('296x296bb-60.jpg', '632x632bb.webp').replace('296x296bf-60.jpg', '632x632bf.webp')
                image_caption = f'*{amr.replace_symbols_markdown_v2(artist.replace('&amp;','&'))}* \\- [{amr.replace_symbols_markdown_v2(row['album'].replace('&amp;','&'))}]({row['album_link'].replace('://','://embed.')})\n{amr.replace_symbols_markdown_v2(str(row['apple_music_release_date'])[0:10])}'
                message_id = amr.send_photo('Coming Soon', image_caption, image_url, TOKEN, CHAT_ID)
                message_cs_releases = True

        new_cs_release_css = '<a class="product-lockup__title svelte-21e67y"'
        if row['is_new_on_this_week'] == 1:
            new_cs_release_css = '<a class="product-lockup__title svelte-21e67y new-release"'

        html_li += make_html_li_text(row['aria_label'], row['artwork_bg_color'], row['picture_srcset_webp'], row['picture_srcset_jpeg'], row['artist_list'], row['artist_link_list'], row['album'], row['album_link'], new_cs_release_css)

    date_time_now = datetime.datetime.now()
    if ENV == 'GitHub':
        date_time_now = date_time_now + datetime.timedelta(hours=3)
    html_li += make_html_li_final(date_time_now.strftime('%Y-%m-%d %H:%M:%S'))

    with open(f'{ROOT_FOLDER}index.html', 'r+') as html_file:
        html_content = html_file.read()
        change_block_position = html_content.find('      <div class="main-date">')
        change_block = html_content[change_block_position:]
        html_content = html_content.replace(change_block, html_li)
        html_file.seek(0, 0)
        html_file.truncate(0)
        html_file.write(html_content)

def next_week_releases_sender():
    global TOKEN, CHAT_ID
    itunes_db_df = pd.read_csv(RELEASES_DB, sep=";")

    this_week_message = ''
    next_week_message = ''
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')

    this_week_message += '\U0001F50E This week releases:'
    if len(itunes_db_df[(itunes_db_df['downloadedRelease'] == 'd') & (itunes_db_df['releaseDate'] <= current_date)]):
        for index, row in itunes_db_df[(itunes_db_df['downloadedRelease'] == 'd') & (itunes_db_df['releaseDate'] <= current_date)].sort_values(by=['releaseDate','mainArtist'], ascending=[True, True]).iterrows():
            this_week_message += f'\n*{amr.replace_symbols_markdown_v2(row['artistName'].replace('&amp;','&'))}* \\- {amr.replace_symbols_markdown_v2(row['collectionName'].replace('&amp;','&'))}'
    else:
        this_week_message += '\n\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F'

    week_date = ''
    next_week_message += '\U000023F3 Next weeks releases:'
    if len(itunes_db_df[(itunes_db_df['downloadedRelease'] == 'd') & (itunes_db_df['releaseDate'] > current_date)]):
        for index, row in itunes_db_df[(itunes_db_df['downloadedRelease'] == 'd') & (itunes_db_df['releaseDate'] > current_date)].sort_values(by=['releaseDate','mainArtist'], ascending=[True, True]).iterrows():
            if week_date != row['releaseDate']:
                week_date = row['releaseDate']
                next_week_message += f'\n\n__{amr.replace_symbols_markdown_v2(week_date)}__'
            next_week_message += f'\n*{amr.replace_symbols_markdown_v2(row['artistName'].replace('&amp;','&'))}* \\- {amr.replace_symbols_markdown_v2(row['collectionName'].replace('&amp;','&'))}'
    else:
        next_week_message += '\n\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F'

    amr.send_message('Next Week Releases', next_week_message, TOKEN, CHAT_ID)
    amr.send_message('Next Week Releases', this_week_message, TOKEN, CHAT_ID)

    del itunes_db_df

def main():
    global TOKEN, CHAT_ID, YM_TOKEN, YM_CLIENT, ZVUK_TOKEN, ZVUK_ERROR, message_new_releases, message_cs_releases

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

    album_categories = [
        {
            "category_type": 'New Releases',
            "category_link": 'https://music.apple.com/us/curator/apple-music-metal/976439543',
            "category_name": 'METAL',
            "category_color": '#81BB98, #9AD292',
            "category_abbr": 'M'
        },
        {
            "category_type": 'New Releases',
            "category_link": 'https://music.apple.com/us/curator/apple-music-hard-rock/979231690',
            "category_name": 'ALTERNATIVE & HARD ROCK',
            "category_color": '#EE702E, #F08933',
            "category_abbr": 'HR'
        },
        {
            "category_type": 'New Releases',
            "category_link": 'https://music.apple.com/ru/curator/apple-music-метал/976439543',
            "category_name": 'METAL - RU',
            "category_color": '#81BB98, #9AD292',
            "category_abbr": 'MRU'
        },
        {
            "category_type": 'New Releases',
            "category_link": 'https://music.apple.com/ru/curator/apple-music-хард-рок/979231690',
            "category_name": 'ALTERNATIVE & HARD ROCK - RU',
            "category_color": '#EE702E, #F08933',
            "category_abbr": 'HRRU'
        },
        {
            "category_type": 'Coming Soon',
            "category_link": 'https://music.apple.com/us/curator/apple-music-metal/976439543',
            "category_name": 'METAL - CS',
            "category_color": '#81BB98, #9AD292',
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
            collect_new_releases(category_link, category["category_name"], category["category_color"], category["category_abbr"])
            amr.logger(logger_category, LOG_FILE, SCRIPT_NAME)
        elif category["category_type"] == 'Coming Soon':
            coming_soon(category_link)
            amr.logger('Coming Soon', LOG_FILE, SCRIPT_NAME)

            collect_cs_releases(category["category_name"], category["category_color"], category["category_abbr"])
            amr.logger(logger_category, LOG_FILE, SCRIPT_NAME)

    if not TOKEN or not CHAT_ID:
        print('Message not sent! No TOKEN or CHAT_ID')
    else:
        if not message_new_releases:
            amr.send_message('New Releases', '\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F', TOKEN, CHAT_ID)
        if not message_cs_releases:
            amr.send_message('Coming Soon', '\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F', TOKEN, CHAT_ID)

    if ZVUK_ERROR:
        amr.logger(f'{ZVUK_ERROR}', LOG_FILE, SCRIPT_NAME)    

    next_week_releases_sender()

    amr.logger(f'▼ DONE', LOG_FILE, SCRIPT_NAME) # End

if __name__ == "__main__":
    main()

