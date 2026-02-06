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

message_new_releases = '' 
message_cs_releases = '' 

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
  <hr>
"""

HTML_END = """  </table>
  <hr>
"""

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
</body>
"""

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
    <tr><th width="100px">Cover</th><th width="600px">Album</th></tr>
"""    
    return html_start

def make_html_text(artist, album, imga, link, aralinsert, ym_result, zv_result):
    html_text = f"""  <!-- {artist.replace('&amp;','&')} - {album.replace('&amp;','&')} -->
    <tr style="display:;" id=''>
      <td><a href="{imga.replace('296x296bb.webp', '100000x100000-999.jpg').replace('296x296bf.webp', '100000x100000-999.jpg')}" target="_blank"><img src="{imga}" height="100px"></a></td>
      <td class="album_name"><a href="{link}" target="_blank"><b>{aralinsert}</a><br><br><button data-frame-load="{link[link.rfind('/') + 1:]}">Preview</button>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href="{ym_result if ym_result is not None else ''}" target="_blank"><button{' disabled' if ym_result is None or ym_result == '' else ''}>Яндекс.Музыка</button></a>&nbsp;<a href="{zv_result if zv_result is not None else ''}" target="_blank"><button{' disabled' if zv_result is None or zv_result == '' else ''}>Звук</button></a></td>
    </tr> 
    <tr style="display:none;" id="show{link[link.rfind('/') + 1:]}_"><td colspan="2"><iframe id="embedPlayer" data-frame-group="{link[link.rfind('/') + 1:]}" data-frame-src="{link.replace('://', '://embed.')}?app=music&amp;itsct=music_box_player&amp;itscg=30200&amp;ls=1&amp;theme=light" height="450px" frameborder="0" sandbox="allow-forms allow-popups allow-same-origin allow-scripts allow-top-navigation-by-user-activation" allow="autoplay *; encrypted-media *; clipboard-write" style="width: 100%; overflow: hidden; border-radius: 10px; transform: translateZ(0px); animation: 2s ease 0s 6 normal none running loading-indicator; background-color: rgb(228, 228, 228);"></iframe></td></tr>
"""
    return html_text

def find_room_link(category_link, category_name):
    """ Searching correct link to room genre
    """
    request = session.get(category_link)
    request.encoding = 'UTF-8'
    response = request.text
    start_position = response.find(f'{"title":"{category_name}"')
    begin_position = response.find('"id":"', start_position) + len('"id":"')
    end_position = response.find('"', begin_position)
    category_id = response[begin_position:end_position].strip()
    room_link = f'{category_link[:category_link.find('/curator')]}/room/{category_id}'
    return room_link

def collect_new_releases(category_link, category_name, category_color, category_abbr):
    global message_new_releases
    request = session.get(category_link)
    request.encoding = 'UTF-8'
    
    update_date = datetime.datetime.now().strftime('%Y-%m-%d')
    html_start = make_html_start(update_date, category_name, category_color)
    html_text = ''

    fieldNames = ['date', 'category', 'artist', 'album', 'Best_Fav_New_OK', 'rec_send2TG', 'link', 'link_ym', 'link_zv', 'imga', 'send2TG', 'TGmsgID']
    pdDB = pd.read_csv(NEW_RELEASES_DB, sep=";")
    pdAIDDB = pd.read_csv(ARTIST_ID_DB, sep=";")
    csvfile = open(NEW_RELEASES_DB, 'a+', newline='')
    writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldNames)

    res = request.text
    i = res.find('<div class="content-container ')
    pos = res.find('<footer ')

    fullCard0 = '<li class="grid-item '
    fullCard1 = '</li>'
    while i < pos:
        if res.find(fullCard0, i) > -1:
            posCard0 = res.find(fullCard0, i) + len(fullCard0)
            posCard1 = res.find(fullCard1, posCard0) 
            i = posCard0
            while i < posCard1:
                sstr = '<picture '
                if res[i:i + len(sstr)] == sstr:
                    posPic0 = res.find('srcset="', i) + len('srcset="')
                    posPic1 = res.find(' ', posPic0)
                    imga = res[posPic0:posPic1].strip()    
                    i = res.find('</picture>', i)
                sstr = '<div class="product-lockup__title-link '
                if res[i:i + len(sstr)] == sstr:
                    posLink0 = res.find('<a href="', i) + len('<a href="')
                    posLink1 = res.find('"', posLink0)
                    link = res[posLink0:posLink1].strip()    
                    i = posLink1
                    posAlbum0 = res.find('>', i) + len('>')
                    posAlbum1 = res.find('<', posAlbum0)
                    album = res[posAlbum0:posAlbum1].strip()
                    i = posAlbum1           
                    sstr = '<p data-testid="product-lockup-subtitles" '
                    i = res.find(sstr, i) + len(sstr)
                    pEnd = res.find('</p>', i) 
                    artist = ''
                    artistID = ''
                    isMyArtist = 0 # Check Artist ID
                    while i < pEnd:
                        posArtID1 = res.find('" class="product-lockup__subtitle link', i)
                        if posArtID1 < pEnd and posArtID1 > -1:
                            posArtID0 = res.rfind('/', i, posArtID1) + len('/')
                            artistID = res[posArtID0:posArtID1].strip()
                            if float(artistID) in pdAIDDB['mainId'].values:
                                isMyArtist += 1
                        posArtist0 = res.find('>', i) + len('>')
                        posArtist1 = res.find('<', posArtist0)
                        if res[posArtist0:posArtist1].strip() == ',':
                            artist += ';'
                        else:
                            artist += res[posArtist0:posArtist1].strip()
                        i = posArtist1
                        i += 1
                    artist = artist.replace('&amp;','_&_')
                    artist = artist.replace(';','; ')
                    artist = artist.replace('_&_', '&amp;')
                    check = 0
                    for index, row in pdDB.iterrows():
                        if row.iloc[6][row.iloc[6].rfind('/') + 1:] == link[link.rfind('/') + 1:]:
                            check = 1
                    if check == 0:
                        if artist != '':
                            aralname = artist + ' - ' + album
                            # YM & Zvuk search --------------
                            ym_zv_search_string = f'{artist.replace('&amp;','&')} - {album.replace('&amp;','&')}' 
                            ym_year = update_date[0:4]
                            ym_result = ''
                            zv_result = ''
                            ym_result = search_album_ym(ym_zv_search_string, ym_year)
                            if ZVUK_ERROR == '':
                                zv_result = search_album_zv(ym_zv_search_string)
                            else:
                                zv_result = ''
                            # -------------------------------
                            aralinsert = aralname.replace(artist, artist + '</b>') if len(aralname) < 80 else aralname[:aralname[:80].rfind(' ') + 1].replace(artist, artist + '</b>') + '<br>' + aralname[aralname[:80].rfind(' ') + 1:]
                            if isMyArtist > 0:
                                img_url = imga.replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
                                img_caption = f'*{amr.replace_symbols_markdown_v2(artist.replace('&amp;','&'))}* \\- [{amr.replace_symbols_markdown_v2(album.replace('&amp;','&'))}]({link.replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({link}){f'\n\U0001F4A5 [Яндекс\\.Музыка]({ym_result})' if ym_result is not None and ym_result != '' else ''}{f'\n\U0001F50A [Звук]({zv_result})' if zv_result is not None and zv_result != '' else ''}'
                                message_new_releases = amr.send_photo_url('New Releases', img_caption, img_url, TOKEN, CHAT_ID)

                            writer.writerow({'date': update_date, 
                                             'category': category_abbr, 
                                             'artist': artist.replace('&amp;','&'), 
                                             'album': album.replace('&amp;','&'), 
                                             'Best_Fav_New_OK': '', 
                                             'rec_send2TG': '', 
                                             'link': link, 
                                             'link_ym': ym_result if ym_result is not None else '', # YM & Zvuk search
                                             'link_zv': zv_result if zv_result is not None else '', # YM & Zvuk search
                                             'imga': imga, 
                                             'send2TG': '', 
                                             'TGmsgID': message_new_releases if message_new_releases > 1 else ''})
                            message_new_releases = 1 if message_new_releases > 0 else 0
                            html_text += make_html_text(artist, album, imga, link, aralinsert, ym_result, zv_result)
#                             html_text += f"""  <!-- {artist.replace('&amp;','&')} - {album.replace('&amp;','&')} -->
#     <tr style="display:;" id=''>
#       <td><a href="{imga.replace('296x296bb.webp', '100000x100000-999.jpg').replace('296x296bf.webp', '100000x100000-999.jpg')}" target="_blank"><img src="{imga}" height="100px"></a></td>
#       <td class="album_name"><a href="{link}" target="_blank"><b>{aralinsert}</a><br><br><button data-frame-load="{link[link.rfind('/') + 1:]}">Preview</button>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href="{ym_result if ym_result is not None else ''}" target="_blank"><button{' disabled' if ym_result is None or ym_result == '' else ''}>Яндекс.Музыка</button></a>&nbsp;<a href="{zv_result if zv_result is not None else ''}" target="_blank"><button{' disabled' if zv_result is None or zv_result == '' else ''}>Звук</button></a></td>
#     </tr> 
#     <tr style="display:none;" id="show{link[link.rfind('/') + 1:]}_"><td colspan="2"><iframe id="embedPlayer" data-frame-group="{link[link.rfind('/') + 1:]}" data-frame-src="{link.replace('://', '://embed.')}?app=music&amp;itsct=music_box_player&amp;itscg=30200&amp;ls=1&amp;theme=light" height="450px" frameborder="0" sandbox="allow-forms allow-popups allow-same-origin allow-scripts allow-top-navigation-by-user-activation" allow="autoplay *; encrypted-media *; clipboard-write" style="width: 100%; overflow: hidden; border-radius: 10px; transform: translateZ(0px); animation: 2s ease 0s 6 normal none running loading-indicator; background-color: rgb(228, 228, 228);"></iframe></td></tr>
# """
                    i += 1
                i += 1
        i += 1

    csvfile.close()

    yearNOW = update_date[0:4]
    monthNOW = update_date[0:7]
    monthTextNOW = datetime.datetime.strptime(update_date, '%Y-%m-%d').strftime('%B')    
    HTMLFile = open(ROOT_FOLDER + "index.html", "r")
    index = HTMLFile.read()
    monthDBslice = index[index.find('<a href="AMRs'):index.find('</a><br>')]
    monthDB = monthDBslice[monthDBslice.rfind(' ') + 1:monthDBslice.rfind('.html">')]
    HTMLFile.close()
    monthTextDB = datetime.datetime.strptime(monthDB, '%Y-%m').strftime('%B')
    yearDB = monthDB[0:4]
    newMonth = 0
    newYear = 0

    if yearNOW != yearDB:
        newYear = 1
        with open(ROOT_FOLDER + 'index.html', 'r+') as idx:
            idxContent = idx.read()
            idxContent = idxContent.replace(f'\n    <h2 class="title svelte-hprj71" data-testid="header-title">{yearDB}:</h2>',
                                            f'\n    <h2 class="title svelte-hprj71" data-testid="header-title">{yearNOW}:</h2>\n        <a href="AMRs/{yearNOW}/AMR {monthNOW}.html">{monthTextNOW}</a><br>\n    <h2 class="title svelte-hprj71" data-testid="header-title">{yearDB}:</h2>')
            idx.seek(0, 0)
            idx.write(idxContent)
        idx.close()
    else:
        if monthNOW != monthDB:
            newMonth = 1
            with open(ROOT_FOLDER + 'index.html', 'r+') as idx:
                idxContent = idx.read()
                idxContent = idxContent.replace(f'\n        <a href="AMRs/{yearDB}/AMR {monthDB}.html">{monthTextDB}</a><br>',
                                                f'\n        <a href="AMRs/{yearDB}/AMR {monthDB}.html">{monthTextDB}</a> | \n        <a href="AMRs/{yearNOW}/AMR {monthNOW}.html">{monthTextNOW}</a><br>')
                idx.seek(0, 0)
                idx.write(idxContent)
            idx.close()

    if html_text != '':
        if newMonth == 1 or newYear == 1:
            with open(f'{AMR_FOLDER}{yearNOW}/AMR {monthNOW}.html', 'w') as h2r:
                h2r.write(HTML_HEAD + '\n' + htmlStart + html_text + HTML_END + '\n' + HTML_FINAL)
            h2r.close()            
        else:
            with open(f'{AMR_FOLDER}{yearNOW}/AMR {monthNOW}.html', 'r+') as h2r:
                h2rContent = h2r.read()
                h2rContent = h2rContent.replace(HTML_HEAD, '')
                h2r.seek(0, 0)
                h2r.write(HTML_HEAD + '\n' + htmlStart + html_text + HTML_END + '\n' + h2rContent)
            h2r.close()
#----------------------------------------------------------------------------------------------------

def coming_soon(category_link):
    global message_cs_releases
    CS_request = session.get(category_link)
    CS_request.encoding = 'UTF-8'
    CS_res = CS_request.text

    ul_r = CS_res.find('<ul class="grid')
    ul_p = CS_res.find('</ul>', ul_r)
    ul_string = CS_res[ul_r:ul_p + len('</ul>')]

    product_lockup_aria_label = ''
    artwork_component_artwork_bg_color = ''
    artwork_component_artwork_placeholder_bg_color = ''
    picture_srcset_webp = ''
    picture_srcset_jpeg = ''
    picture_img_alt = ''
    a_product_lockup__title_href = ''
    a_product_lockup__title = ''
    a_product_lockup__subtitle_href = ''
    a_product_lockup__subtitle = ''
    
    pdNR = pd.DataFrame(columns=['amSort',
                                 'product_lockup_aria_label',
                                 'artwork_component_artwork_bg_color',
                                 'artwork_component_artwork_placeholder_bg_color',
                                 'picture_srcset_webp',
                                 'picture_srcset_jpeg',
                                 'picture_img_alt',
                                 'a_product_lockup__title_href',
                                 'a_product_lockup__title',
                                 'a_product_lockup__subtitle_href',
                                 'a_product_lockup__subtitle',
                                 'amReleaseDate',
                                 'amReleaseDateText',
                                 'newOnThisWeek'])
    amSort = 0

    html_li = ''''''

    i = 0
    pos = len(ul_string) - 1

    fullCard0 = '<li class="grid-item '
    fullCard1 = '</li>'
    while i < pos:
        if ul_string.find(fullCard0, i) > -1:
            posCard0 = ul_string.find(fullCard0, i) + len(fullCard0)
            posCard1 = ul_string.find(fullCard1, posCard0) 
            i = posCard0
            while i < posCard1:
                pos_a = '<div class="product-lockup '
                pos_z = '" data-testid="product-lockup">'
                pos_i = 'aria-label="'
                if ul_string[i:i + len(pos_a)] == pos_a:
                    posStr0 = ul_string.find(pos_i, i) + len(pos_i)
                    posStr1 = ul_string.find(pos_z, posStr0)
                    product_lockup_aria_label = ul_string[posStr0:posStr1].strip() #--- ! ----
                    i = ul_string.find(pos_z, i)

                pos_a = '<div data-testid="artwork-component"'
                pos_z = '<picture'
                pos_i = 'artwork-bg-color: '
                pos_j = ';'
                if ul_string[i:i + len(pos_a)] == pos_a:
                    posStr0 = ul_string.find(pos_i, i) + len(pos_i)
                    posStr1 = ul_string.find(pos_j, posStr0)
                    artwork_component_artwork_bg_color = ul_string[posStr0:posStr1].strip() #--- ! ----
                    i = ul_string.find(pos_z, i)

                pos_a = '<picture '
                pos_z = '</picture>'
                pos_i = 'srcset="'
                pos_j = '" type'
                if ul_string[i:i + len(pos_a)] == pos_a:
                    posStr0 = ul_string.find(pos_i, i) + len(pos_i)
                    posStr1 = ul_string.find(pos_j, posStr0)
                    picture_srcset_webp = ul_string[posStr0:posStr1].strip() #--- ! ----
                    i = posStr1

                    posStr0 = ul_string.find(pos_i, i) + len(pos_i)
                    posStr1 = ul_string.find(pos_j, posStr0)
                    picture_srcset_jpeg = ul_string[posStr0:posStr1].strip() #--- ! ----
                    i = ul_string.find(pos_z, i)

                pos_a = '<div class="product-lockup__content '
                pos_z = posCard1 - 1
                if ul_string[i:i + len(pos_a)] == pos_a:
                    pos_i = 'a href="'
                    pos_j = '"'
                    posStr0 = ul_string.find(pos_i, i) + len(pos_i)
                    posStr1 = ul_string.find(pos_j, posStr0)
                    a_product_lockup__title_href = ul_string[posStr0:posStr1].strip() #--- ! ----
                    i = posStr1

                    pos_i = '>'
                    pos_j = '</a'
                    posStr0 = ul_string.find(pos_i, i) + len(pos_i)
                    posStr1 = ul_string.find(pos_j, posStr0)
                    a_product_lockup__title = ul_string[posStr0:posStr1].strip() #--- ! ----
                    i = posStr1

                    pos_i = 'a href="'
                    pos_j = '"'
                    posStr0 = ul_string.find(pos_i, i) + len(pos_i)
                    posStr1 = ul_string.find(pos_j, posStr0)
                    a_product_lockup__subtitle_href = ul_string[posStr0:posStr1].strip() #--- ! ----
                    i = posStr1

                    pos_i = '>'
                    pos_j = '<'
                    posStr0 = ul_string.find(pos_i, i) + len(pos_i)
                    posStr1 = ul_string.find(pos_j, posStr0)
                    a_product_lockup__subtitle = ul_string[posStr0:posStr1].strip() #--- ! ----
                    i = pos_z

                i += 1

            CS2_request = session.get(a_product_lockup__title_href)
            CS2_request.encoding = 'UTF-8'
            CS2_res = CS2_request.text

            bigstring = 'data-testid="tracklist-footer-description">'
            ul2_r = CS2_res.find(bigstring)
            ul2_p = CS2_res.find('\n', ul2_r)
            ul2_string = CS2_res[ul2_r + len(bigstring):ul2_p]
            date_time2 = datetime.datetime.strptime(ul2_string, '%B %d, %Y')

            amSort += 1
            serTemp = pd.Series(data=[amSort,
                                      product_lockup_aria_label,
                                      artwork_component_artwork_bg_color,
                                      artwork_component_artwork_placeholder_bg_color,
                                      picture_srcset_webp,
                                      picture_srcset_jpeg,
                                      picture_img_alt,
                                      a_product_lockup__title_href,
                                      a_product_lockup__title,
                                      a_product_lockup__subtitle_href,
                                      a_product_lockup__subtitle,
                                      date_time2, 
                                      ul2_string, 
                                      ''], index=pdNR.columns)

            pdNR.loc[len(pdNR.index)] = serTemp

            print('Comming Soon [' + str(amSort) + ']', end='\r')
        i += 1
    
    AMRelDate = 'Date 0, 9999'
    for index, row in pdNR.sort_values(by=['amReleaseDate', 'amSort'], ascending=[True, True]).iterrows():
        #here must be <li> building construction!
        if row.iloc[11] <= datetime.datetime.now():
            row.iloc[12] = 'Delayed'
        if AMRelDate != row.iloc[12]:
            if AMRelDate != 'Date 0, 9999':
                html_li += '''
      </ul>
'''         
            html_li += '''      <div class="main-date">
        <h2 class="title svelte-hprj71" data-testid="header-title">''' + row.iloc[12] + '''</h2>
      </div>    
      <ul class="grid svelte-1p1n7nd grid--flow-row" data-testid="grid">
'''
            AMRelDate = row.iloc[12]

        pdCS = pd.read_csv(CS_RELEASES_DB, sep=";")
        pdAIDDB = pd.read_csv(ARTIST_ID_DB, sep=";")
        if len(pdCS.loc[pdCS['album__href'] == row.iloc[7]]) == 0:
            row.iloc[13] = 1

            fieldNamesCS = ['update__date', 'album_cover__jpeg', 'album__href', 'album__name', 'artist__href', 'artist__name', 'release__date', 'release__date_text']
            csvCS = open(CS_RELEASES_DB, 'a+', newline='') 
            writerCS = csv.DictWriter(csvCS, delimiter=';', fieldnames=fieldNamesCS)

            writerCS.writerow({'update__date': str(datetime.datetime.now())[0:10],
                               'album_cover__jpeg': row.iloc[5][0:row.iloc[5].find(' ')],
                               'album__href': row.iloc[7],
                               'album__name': row.iloc[8].replace('&amp;','&'), 
                               'artist__href': row.iloc[9],
                               'artist__name': row.iloc[10].replace('&amp;','&'), 
                               'release__date': row.iloc[11],
                               'release__date_text': row.iloc[12]})

            if float(row.iloc[9][row.iloc[9].rfind('/', 0, len(row.iloc[9])) + 1:]) in pdAIDDB['mainId'].values:
                img_url = row.iloc[5][0:row.iloc[5].find(' ')].replace('296x296bb-60.jpg', '632x632bb.webp').replace('296x296bf-60.jpg', '632x632bf.webp')
                img_caption = f'*{amr.replace_symbols_markdown_v2(row.iloc[10].replace('&amp;','&'))}* \\- [{amr.replace_symbols_markdown_v2(row.iloc[8].replace('&amp;','&'))}]({row.iloc[7].replace('://','://embed.')})\n{amr.replace_symbols_markdown_v2(str(row.iloc[11])[0:10])}'
                message_cs_releases = amr.send_photo_url('Coming Soon', img_caption, img_url, TOKEN, CHAT_ID)

        css_newRelease = '<a class="product-lockup__title svelte-21e67y"'
        if row.iloc[13] == 1:
            css_newRelease = '<a class="product-lockup__title svelte-21e67y new-release"'

        html_li += '''
       <li class="grid-item svelte-1p1n7nd" data-testid="grid-item">
        <div aria-label="''' + row.iloc[1] + '''" class="product-lockup svelte-21e67y" data-testid="product-lockup">
         <div aria-hidden="false" class="product-lockup__artwork svelte-21e67y has-controls">
          <div class="artwork-component artwork-component--aspect-ratio artwork-component--orientation-square svelte-e284u3 artwork-component--fullwidth artwork-component--has-borders" data-testid="artwork-component" style="
                  --artwork-bg-color: ''' + row.iloc[2] + ''';
                  --aspect-ratio: 1;
                  --placeholder-bg-color: ''' + row.iloc[2] + ''';
             ">
           <picture class="svelte-e284u3">
            <source sizes=" (max-width:1319px) 296px,(min-width:1320px) and (max-width:1679px) 316px,316px" srcset="''' + row.iloc[4] + '''" type="image/webp"/>
            <source sizes=" (max-width:1319px) 296px,(min-width:1320px) and (max-width:1679px) 316px,316px" srcset="''' + row.iloc[5] + '''" type="image/jpeg"/>
            <img alt="''' + row.iloc[6] + '''" class="artwork-component__contents artwork-component__image svelte-e284u3" decoding="async" height="316" loading="lazy" role="presentation" src="/assets/artwork/1x1.gif" style="opacity: 1;" width="316"/>
           </picture>
          </div>
         </div>
         <div class="product-lockup__content svelte-21e67y">
          <div class="product-lockup__content-details svelte-21e67y">
           <p class="product-lockup__subtitle-links svelte-21e67y product-lockup__subtitle-links--singlet" data-testid="product-lockup-subtitles">
            <div class="multiline-clamp svelte-1qrlry multiline-clamp--overflow" style="--lineClamp: 1;">
             <a class="product-lockup__subtitle svelte-21e67y link" data-testid="product-lockup-subtitle" href="''' + row.iloc[9] + '''">
              ''' + row.iloc[10] + '''
             </a>
            </div>
           </p>           
           <div class="product-lockup__title-link svelte-21e67y product-lockup__title-link--multiline">
            <div class="multiline-clamp svelte-1qrlry multiline-clamp--overflow" style="--lineClamp: 2;">
             ''' + css_newRelease + ''' data-testid="product-lockup-title" href="''' + row.iloc[7] + '''">
              ''' + row.iloc[8] + '''
             </a>
            </div>
           </div>
          </div>
         </div>
        </div>
       </li>
'''
    
    html_li += '''
      </ul>
    </div> 
  </div>   
</div>
<div class="main">
  <i>Updated: ''' + str(datetime.datetime.now()) + '''</i>
</div>
</body>
'''

    with open(ROOT_FOLDER + 'index.html', 'r+') as idx2:
        idx2Content = idx2.read()
        ul_idx_r = idx2Content.find('      <div class="main-date">')
        ul_idx_string = idx2Content[ul_idx_r:]
        idx2Content = idx2Content.replace(ul_idx_string, html_li)
        idx2.seek(0, 0)
        idx2.truncate(0)
        idx2.write(idx2Content)
    idx2.close()    
#----------------------------------------------------------------------------------------------------

def CS2NR():
# Coming soon to New Releases  

    pdNR = pd.read_csv(NEW_RELEASES_DB, sep=";")
    pdCS = pd.read_csv(CS_RELEASES_DB, sep=";")
    pdCSNR = pd.DataFrame(columns=['artist', 'album', 'link', 'image'])

    for index, row in pdCS.iterrows():
        if datetime.datetime.strptime(row.iloc[6], "%Y-%m-%d %H:%M:%S") <= datetime.datetime.now():
            if len(pdNR.loc[pdNR['link'] == row.iloc[2]]) == 0:
                CS2_request = session.get(row.iloc[2])
                CS2_request.encoding = 'UTF-8'
                CS2_res = CS2_request.text
                bigstring = 'data-testid="tracklist-footer-description">'
                ul2_r = CS2_res.find(bigstring)
                ul2_p = CS2_res.find('\n', ul2_r)
                ul2_string = CS2_res[ul2_r + len(bigstring):ul2_p]
                date_time2 = datetime.datetime.strptime(ul2_string, '%B %d, %Y')
                if row.iloc[6] != date_time2 and date_time2 > datetime.datetime.now():
                    pdCS.loc[index, 'release__date'] = date_time2
                    pdCS.loc[index, 'release__date_text'] = ul2_string
                else:
                    pdCSNR.loc[len(pdCSNR.index)] = [row.iloc[5], row.iloc[3], row.iloc[2], row.iloc[1]]

    # !!! ЗАПИСЬ В БД !!!
    pdCS.to_csv(CS_RELEASES_DB, sep=';', index=False)
    pdNR = pd.DataFrame()
    pdCS = pd.DataFrame()

    if len(pdCSNR) > 0:
        category_abbr = 'CS'
        category_name = 'METAL - CS'
        category_color = '#81BB98, #9AD292'

        update_date = str(datetime.datetime.now())[0:10]
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
  <hr>
"""

        htmlStart = """  <table border="1">
    <tr id=""" + ('\"' + update_date + '_' + category_name + '\"').lower().replace(' ','_') +  """><th colspan="2" style="background: linear-gradient(to right, """ + category_color + """);">""" + update_date + """ | """ + category_name + """</th></tr>
    <tr><th width="100px">Cover</th><th width="600px">Album</th></tr>
"""

        html_text = ''

        HTML_END = """  </table>
  <hr>
"""



        fieldNames = ['date', 'category', 'artist', 'album', 'Best_Fav_New_OK', 'rec_send2TG', 'link', 'link_ym', 'link_zv', 'imga', 'send2TG', 'TGmsgID']
        csvfile = open(NEW_RELEASES_DB, 'a+', newline='')
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldNames)

        for index, row in pdCSNR.iterrows():
            aralname = row.iloc[0] + ' - ' + row.iloc[1]
            # YM & Zvuk search --------------
            ym_zv_search_string = f'{row.iloc[0].replace('&amp;','&')} - {row.iloc[1].replace('&amp;','&')}' 
            ym_year = update_date[0:4]
            ym_result = ''
            zv_result = ''
            ym_result = search_album_ym(ym_zv_search_string, ym_year)
            if ZVUK_ERROR == '':
                zv_result = search_album_zv(ym_zv_search_string)
            else:
                zv_result = ''
            # -------------------------------
            aralinsert = aralname.replace(row.iloc[0], row.iloc[0] + '</b>') if len(aralname) < 80 else aralname[:aralname[:80].rfind(' ') + 1].replace(row.iloc[0], row.iloc[0] + '</b>') + '<br>' + aralname[aralname[:80].rfind(' ') + 1:]
            writer.writerow({'date': update_date, 
                          'category': category_abbr, 
                          'artist': row.iloc[0], 
                          'album': row.iloc[1], 
                          'Best_Fav_New_OK': '', 
                          'rec_send2TG': '', 
                          'link': row.iloc[2], 
                          'link_ym': ym_result if ym_result is not None else '', # YM & Zvuk search
                          'link_zv': zv_result if zv_result is not None else '', # YM & Zvuk search
                          'imga': row.iloc[3], 
                          'send2TG': '', 
                          'TGmsgID': ''})

            # !!! CHANGE names TO row.iloc[#] !!!
            html_text += make_html_text(artist, album, imga, link, aralinsert, ym_result, zv_result)
#             html_text += f"""  <!-- {row.iloc[0]} - {row.iloc[1]} -->
#     <tr style="display:;" id=''>
#       <td><a href="{row.iloc[3].replace('296x296bb.webp', '100000x100000-999.jpg').replace('296x296bf.webp', '100000x100000-999.jpg').replace('296x296bf-60.jpg', '100000x100000-999.jpg')}" target="_blank"><img src="{row.iloc[3]}" height="100px"></a></td>
#       <td class="album_name"><a href="{row.iloc[2]}" target="_blank"><b>{aralinsert}</a><br><br><button data-frame-load="{row.iloc[2][row.iloc[2].rfind('/') + 1:]}">Preview</button>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href="{ym_result if ym_result is not None else ''}" target="_blank"><button{' disabled' if ym_result is None or ym_result == '' else ''}>Яндекс.Музыка</button></a>&nbsp;<a href="{zv_result if zv_result is not None else ''}" target="_blank"><button{' disabled' if zv_result is None or zv_result == '' else ''}>Звук</button></a></td>
#     </tr> 
#     <tr style="display:none;" id="show{row.iloc[2][row.iloc[2].rfind('/') + 1:]}_"><td colspan="2"><iframe id="embedPlayer" data-frame-group="{row.iloc[2][row.iloc[2].rfind('/') + 1:]}" data-frame-src="{row.iloc[2].replace('://', '://embed.')}?app=music&amp;itsct=music_box_player&amp;itscg=30200&amp;ls=1&amp;theme=light" height="450px" frameborder="0" sandbox="allow-forms allow-popups allow-same-origin allow-scripts allow-top-navigation-by-user-activation" allow="autoplay *; encrypted-media *; clipboard-write" style="width: 100%; overflow: hidden; border-radius: 10px; transform: translateZ(0px); animation: 2s ease 0s 6 normal none running loading-indicator; background-color: rgb(228, 228, 228);"></iframe></td></tr>
# """

#     html_text = f"""  <!-- {artist.replace('&amp;','&')} - {album.replace('&amp;','&')} -->
#     <tr style="display:;" id=''>
#       <td><a href="{imga.replace('296x296bb.webp', '100000x100000-999.jpg').replace('296x296bf.webp', '100000x100000-999.jpg')}" target="_blank"><img src="{imga}" height="100px"></a></td>
#       <td class="album_name"><a href="{link}" target="_blank"><b>{aralinsert}</a><br><br><button data-frame-load="{link[link.rfind('/') + 1:]}">Preview</button>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href="{ym_result if ym_result is not None else ''}" target="_blank"><button{' disabled' if ym_result is None or ym_result == '' else ''}>Яндекс.Музыка</button></a>&nbsp;<a href="{zv_result if zv_result is not None else ''}" target="_blank"><button{' disabled' if zv_result is None or zv_result == '' else ''}>Звук</button></a></td>
#     </tr> 
#     <tr style="display:none;" id="show{link[link.rfind('/') + 1:]}_"><td colspan="2"><iframe id="embedPlayer" data-frame-group="{link[link.rfind('/') + 1:]}" data-frame-src="{link.replace('://', '://embed.')}?app=music&amp;itsct=music_box_player&amp;itscg=30200&amp;ls=1&amp;theme=light" height="450px" frameborder="0" sandbox="allow-forms allow-popups allow-same-origin allow-scripts allow-top-navigation-by-user-activation" allow="autoplay *; encrypted-media *; clipboard-write" style="width: 100%; overflow: hidden; border-radius: 10px; transform: translateZ(0px); animation: 2s ease 0s 6 normal none running loading-indicator; background-color: rgb(228, 228, 228);"></iframe></td></tr>
# """
        csvfile.close()

        yearNOW = update_date[0:4]
        monthNOW = update_date[0:7]
        monthTextNOW = datetime.datetime.strptime(update_date, '%Y-%m-%d').strftime('%B')    
        HTMLFile = open(ROOT_FOLDER + "index.html", "r")
        index = HTMLFile.read()
        monthDBslice = index[index.find('<a href="AMRs'):index.find('</a><br>')] # THIS
        monthDB = monthDBslice[monthDBslice.rfind(' ') + 1:monthDBslice.rfind('.html">')] # THIS
        HTMLFile.close()
        monthTextDB = datetime.datetime.strptime(monthDB, '%Y-%m').strftime('%B')
        yearDB = monthDB[0:4]
        newMonth = 0
        newYear = 0

        if yearNOW != yearDB:
            newYear = 1
            with open(ROOT_FOLDER + 'index.html', 'r+') as idx:
                idxContent = idx.read()
                idxContent = idxContent.replace(f'\n    <h2 class="title svelte-hprj71" data-testid="header-title">{yearDB}:</h2>',
                                                f'\n    <h2 class="title svelte-hprj71" data-testid="header-title">{yearNOW}:</h2>\n        <a href="AMRs/{yearNOW}/AMR {monthNOW}.html">{monthTextNOW}</a><br>\n    <h2 class="title svelte-hprj71" data-testid="header-title">{yearDB}:</h2>')
                idx.seek(0, 0)
                idx.write(idxContent)
            idx.close()
        else:
            if monthNOW != monthDB:
                newMonth = 1
                with open(ROOT_FOLDER + 'index.html', 'r+') as idx:
                    idxContent = idx.read()
                    idxContent = idxContent.replace(f'\n        <a href="AMRs/{yearDB}/AMR {monthDB}.html">{monthTextDB}</a><br>',
                                                    f'\n        <a href="AMRs/{yearDB}/AMR {monthDB}.html">{monthTextDB}</a> | \n        <a href="AMRs/{yearNOW}/AMR {monthNOW}.html">{monthTextNOW}</a><br>')
                    idx.seek(0, 0)
                    idx.write(idxContent)
                idx.close()

        if html_text != '':
            if newMonth == 1 or newYear == 1:
                with open(f'{AMR_FOLDER}{yearNOW}/AMR {monthNOW}.html', 'w') as h2r:
                    h2r.write(HTML_HEAD + '\n' + htmlStart + html_text + HTML_END + '\n' + HTML_FINAL)
                h2r.close()            
            else:
                with open(f'{AMR_FOLDER}{yearNOW}/AMR {monthNOW}.html', 'r+') as h2r:
                    h2rContent = h2r.read()
                    h2rContent = h2rContent.replace(HTML_HEAD, '')
                    h2r.seek(0, 0)
                    h2r.write(HTML_HEAD + '\n' + htmlStart + html_text + HTML_END + '\n' + h2rContent)
                h2r.close()

def nextWeekReleases_sender():
    pdR = pd.read_csv(RELEASES_DB, sep=";")

    msg2snd = ''
    msg2snd_nw = ''
    nowDate = str(datetime.datetime.now())[0:10]

    msg2snd += '\U0001F50E This week releases:'
    if len(pdR[(pdR['downloadedRelease'] == 'd') & (pdR['releaseDate'] <= nowDate)]) > 0:
        for index, row in pdR[(pdR['downloadedRelease'] == 'd') & (pdR['releaseDate'] <= nowDate)].sort_values(by=['releaseDate','mainArtist'], ascending=[True, True]).iterrows():
            msg2snd += f'\n*{amr.replace_symbols_markdown_v2(row.iloc[3].replace('&amp;','&'))}* \\- {amr.replace_symbols_markdown_v2(row.iloc[4].replace('&amp;','&'))}'
    else:
        msg2snd += '\n\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F'

    week_date = '0000-00-00'
    msg2snd_nw += '\U000023F3 Next weeks releases:'
    if len(pdR[(pdR['downloadedRelease'] == 'd') & (pdR['releaseDate'] > nowDate)]) > 0:
        for index, row in pdR[(pdR['downloadedRelease'] == 'd') & (pdR['releaseDate'] > nowDate)].sort_values(by=['releaseDate','mainArtist'], ascending=[True, True]).iterrows():
            if week_date != row.iloc[6]:
                week_date = row.iloc[6]
                msg2snd_nw += f'\n\n__{amr.replace_symbols_markdown_v2(week_date)}__'
            msg2snd_nw += f'\n*{amr.replace_symbols_markdown_v2(row.iloc[3].replace('&amp;','&'))}* \\- {amr.replace_symbols_markdown_v2(row.iloc[4].replace('&amp;','&'))}'
    else:
        msg2snd_nw += '\n\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F'


    amr.send_message('Next Week Releases', msg2snd_nw, TOKEN, CHAT_ID)
    amr.send_message('Next Week Releases', msg2snd, TOKEN, CHAT_ID)    

    pdR = pd.DataFrame()

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

# ---------------N_E_W-------------------------------------------------------------
    # album_categories = [
    #     {
    #         "category_type": 'New Releases',
    #         "category_link": 'https://music.apple.com/us/room/993297832',
    #         "category_name": 'METAL',
    #         "category_color": '#81BB98, #9AD292',
    #         "category_abbr": 'M'
    #     },
    #     {
    #         "category_type": 'New Releases',
    #         "category_link": 'https://music.apple.com/us/room/1184023815',
    #         "category_name": 'ALTERNATIVE & HARD ROCK',
    #         "category_color": '#EE702E, #F08933',
    #         "category_abbr": 'HR'
    #     },
    #     {
    #         "category_type": 'New Releases',
    #         "category_link": 'https://music.apple.com/ru/room/1118077423',
    #         "category_name": 'METAL - RU',
    #         "category_color": '#81BB98, #9AD292',
    #         "category_abbr": 'MRU'
    #     },
    #     {
    #         "category_type": 'New Releases',
    #         "category_link": 'https://music.apple.com/ru/room/1532200949',
    #         "category_name": 'ALTERNATIVE & HARD ROCK - RU',
    #         "category_color": '#EE702E, #F08933',
    #         "category_abbr": 'HRRU'
    #     },
    #     {
    #         "category_type": 'Coming Soon',
    #         "category_link": 'https://music.apple.com/ru/room/1532200949',
    #         "category_name": 'METAL - CS',
    #         "category_color": '#81BB98, #9AD292',
    #         "category_abbr": 'MCS'
    #     }
    # ]

    # for category in album_categories:
    #     collect_albums(category["category_link"], category["category_name"], category["category_color"], category["category_abbr"])
    #     print(category["category_name"])
# ---------------------------------------------------------------------------------

    category_link = find_room_link('https://music.apple.com/us/curator/apple-music-metal/976439543', 'New Releases')
    category_name = 'METAL'
    category_color = '#81BB98, #9AD292'
    collect_new_releases(category_link, category_name, category_color)
    print('Metal [US]     - OK')

    category_link = find_room_link('https://music.apple.com/us/curator/apple-music-hard-rock/979231690', 'New Releases')
    category_name = 'HARD ROCK'
    category_color = '#EE702E, #F08933'
    collect_new_releases(category_link, category_name, category_color)
    print('Hard Rock [US] - OK')

    category_link = 'https://music.apple.com/ru/room/1118077423'
    category_name = 'METAL - RU'
    category_color = '#81BB98, #9AD292'
    collect_new_releases(category_link, category_name, category_color)
    print('Metal [RU]     - OK')

    category_link = 'https://music.apple.com/ru/room/1532200949'
    category_name = 'HARD ROCK - RU'
    category_color = '#EE702E, #F08933'
    collect_new_releases(category_link, category_name, category_color)
    print('Hard Rock [RU] - OK')

    category_link = find_room_link('https://music.apple.com/us/curator/apple-music-metal/976439543', 'Coming Soon')
    coming_soon(category_link)
    print('Comming Soon   - OK')

    CS2NR()
    print('Metal [CS]     - OK')

    if TOKEN == '' or CHAT_ID == '':
        print('Message not sent! No TOKEN or CHAT_ID')
    else:
        if message_new_releases == '':
            amr.send_message('New Releases', '\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F', TOKEN, CHAT_ID)
        if message_cs_releases == '':
            amr.send_message('Coming Soon', '\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F', TOKEN, CHAT_ID)

    if ZVUK_ERROR:
        amr.logger(f'{ZVUK_ERROR}', LOG_FILE, SCRIPT_NAME)    

    nextWeekReleases_sender()

    amr.logger(f'▼ DONE', LOG_FILE, SCRIPT_NAME) # End

if __name__ == "__main__":
    main()

