ver = "v.2.025.10 [GitHub]"
# Python 3.12 & Pandas 2.2 ready
# Zvuk availability check & multiparameters
## comment will mark the specific code for GitHub

import os
import json
import datetime
import requests
import pandas as pd
import csv
import sys # for Zvuk
from yandex_music import Client # for YM

rootFolder = '' ## root is root
amrsFolder = rootFolder + 'AMRs/'
dbFolder = rootFolder + 'Databases/'
newReleasesDB = dbFolder + 'AMR_newReleases_DB.csv'
csReleasesDB = dbFolder + 'AMR_csReleases_DB.csv'
artistIDsDB = dbFolder + 'AMR_artisitIDs.csv'
ReleasesDB = dbFolder + 'AMR_releases_DB.csv'
logFile = rootFolder + 'status.log' # path to log file
# Telegram -------------------------------
URL = 'https://api.telegram.org/bot'
TOKEN = os.environ['tg_token'] ## GitHub Secrets
chat_id = os.environ['tg_channel_id'] ## GitHub Secrets
thread_id = {'New Updates': 6, 'Top Releases': 10, 'Coming Soon': 3, 'New Releases': 2, 'Next Week Releases': 80}
# Yandex.Music ---------------------------
YM_TOKEN = os.environ['ym_token'] ## GitHub Secrets
search_result = ''
client = Client(YM_TOKEN).init()
type_to_name = {'track': 'трек', 'artist': 'исполнитель', 'album': 'альбом', 'playlist': 'плейлист', 'video': 'видео', 'user': 'пользователь', 'podcast': 'подкаст', 'podcast_episode': 'эпизод подкаста'}

# Zvuk -----------------------------------
BASE_URL = "https://zvuk.com"
API_ENDPOINTS = {"lyrics": f"{BASE_URL}/api/tiny/lyrics", "stream": f"{BASE_URL}/api/tiny/track/stream", "graphql": f"{BASE_URL}/api/v1/graphql", "profile": f"{BASE_URL}/api/tiny/profile"}
ZVUK_TOKEN = os.environ['zv_token'] ## GitHub Secrets
# ZVUK_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36", "Content-Type": "application/json",}

# Establishing session -------------------
HEADERS = {'Referer':'https://music.apple.com', 'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'}
s = requests.Session() 
s.headers.update(HEADERS)
#-----------------------------------------

## This logger is only for GitHub --------------------------------------------------------------------
def amnr_logger(pyScript, logLine):
    with open(logFile, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        ## GitHub server time is UTC (-3 from Moscow), so i add +3 hours to log actions in Moscow time. Only where time matters
        f.write(str(datetime.datetime.now() + datetime.timedelta(hours=3)) + ' - ' + pyScript + ' - ' + logLine.rstrip('\r\n') + '\n' + content)
##----------------------------------------------------------------------------------------------------

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
            return
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
        print(f"Error: {e}")
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
        ZVUK_ERROR = f'Zvuk {releases}' # if search_command_zv return Error
#-----------------------------------------

# Процедура Замены символов для Markdown v2
def ReplaceSymbols(rsTxt):
    rsTmplt = """'_*[]",()~`>#+-=|{}.!"""
    for rsf in range(len(rsTmplt)):
        rsTxt = rsTxt.replace(rsTmplt[rsf], '\\' + rsTmplt[rsf])
    return rsTxt

# Процедура Отправки сообщения ботом в канал
def send_message(topic, text):
    method = URL + TOKEN + "/sendMessage"
    r = requests.post(method, data={"message_thread_id": thread_id[topic], "chat_id": chat_id, "parse_mode": 'MarkdownV2', "text": text})
    json_response = json.loads(r.text)
    rmi = json_response['result']['message_id']   
    return rmi

# Процедура Отправки изображения ботом в канал
def send_photo_url(topic, img_url, img_caption):
    method = URL + TOKEN + "/sendPhoto"
    r = requests.post(method, data={"message_thread_id": thread_id[topic], "chat_id": chat_id, "photo": img_url, "parse_mode": 'MarkdownV2', "caption": img_caption})
    json_response = json.loads(r.text)
    rmi = json_response['result']['message_id']    
    return rmi

# Процедура поиска актуальной ссылки на раздел
def find_link(catLink, catName):
    request = s.get(catLink)
    request.encoding = 'UTF-8'
    res = request.text
    strt = res.find('{"title":"' + catName + '"')
    pos_id_0 = res.find('"id":"', strt) + len('"id":"')
    pos_id_1 = res.find('"', pos_id_0)
    catID = res[pos_id_0:pos_id_1].strip()
    roomLink = catLink[:catLink.find('/curator')] + '/room/' + str(catID)
    return roomLink

def collect_albums(caLink, caText, caGrad):
    global message2send
    request = s.get(caLink)
    request.encoding = 'UTF-8'

    if caText == 'METAL':
        dldCategory = 'M'
    elif caText == 'HARD ROCK':
        dldCategory = 'HR'
    elif caText == 'METAL - RU':
        dldCategory = 'MRU'
    elif caText == 'HARD ROCK - RU':
        dldCategory = 'HRRU'
    
    dldDate = str(datetime.datetime.now())[0:10]
    htmlHead = """<head>
  <meta charset="utf-8">
  <title>Apple Music Releases</title>
  <link rel="stylesheet" type="text/css" href="../Resources/styles.css" />
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
  <input type="button" onclick="location.href='../index.html';" value="Index"  class="bI"/>
  <hr>
"""

    htmlStart = """  <table border="1">
    <tr id=""" + ('\"' + dldDate + '_' + caText + '\"').lower().replace(' ','_') +  """><th colspan="2" style="background: linear-gradient(to right, """ + caGrad + """);">""" + dldDate + """ | """ + caText + """</th></tr>
    <tr><th width="100px">Cover</th><th width="600px">Album</th></tr>
"""

    htmlText = ''

    htmlEnd = """  </table>
  <hr>
"""

    htmlFinal = """  <!-- End of File -->
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

    fieldNames = ['date', 'category', 'artist', 'album', 'Best_Fav_New_OK', 'rec_send2TG', 'link', 'link_ym', 'link_zv', 'imga', 'send2TG', 'TGmsgID']
    pdDB = pd.read_csv(newReleasesDB, sep=";")
    pdAIDDB = pd.read_csv(artistIDsDB, sep=";")
    csvfile = open(newReleasesDB, 'a+', newline='')
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
                            ym_year = dldDate[0:4]
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
                                img_caption = f'*{ReplaceSymbols(artist.replace('&amp;','&'))}* \\- [{ReplaceSymbols(album.replace('&amp;','&'))}]({link.replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({link}){f'\n\U0001F4A5 [Яндекс\\.Музыка]({ym_result})' if ym_result is not None and ym_result != '' else ''}{f'\n\U0001F50A [Звук]({zv_result})' if zv_result is not None and zv_result != '' else ''}'
                                message2send = send_photo_url('New Releases', img_url, img_caption)

                            writer.writerow({'date': dldDate, 
                                             'category': dldCategory, 
                                             'artist': artist.replace('&amp;','&'), 
                                             'album': album.replace('&amp;','&'), 
                                             'Best_Fav_New_OK': '', 
                                             'rec_send2TG': '', 
                                             'link': link, 
                                             'link_ym': ym_result if ym_result is not None else '', # YM & Zvuk search
                                             'link_zv': zv_result if zv_result is not None else '', # YM & Zvuk search
                                             'imga': imga, 
                                             'send2TG': '', 
                                             'TGmsgID': message2send if message2send > 1 else ''})
                            message2send = 1 if message2send > 0 else 0
                            htmlText += f"""  <!-- {artist.replace('&amp;','&')} - {album.replace('&amp;','&')} -->
    <tr style="display:;" id=''>
      <td><a href="{imga.replace('296x296bb.webp', '100000x100000-999.jpg').replace('296x296bf.webp', '100000x100000-999.jpg')}" target="_blank"><img src="{imga}" height="100px"></a></td>
      <td class="album_name"><a href="{link}" target="_blank"><b>{aralinsert}</a><br><br><button data-frame-load="{link[link.rfind('/') + 1:]}">Preview</button>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href="{ym_result if ym_result is not None else ''}" target="_blank"><button{' disabled' if ym_result is None or ym_result == '' else ''}>Яндекс.Музыка</button></a>&nbsp;<a href="{zv_result if zv_result is not None else ''}" target="_blank"><button{' disabled' if zv_result is None or zv_result == '' else ''}>Звук</button></a></td>
    </tr> 
    <tr style="display:none;" id="show{link[link.rfind('/') + 1:]}_"><td colspan="2"><iframe id="embedPlayer" data-frame-group="{link[link.rfind('/') + 1:]}" data-frame-src="{link.replace('://', '://embed.')}?app=music&amp;itsct=music_box_player&amp;itscg=30200&amp;ls=1&amp;theme=light" height="450px" frameborder="0" sandbox="allow-forms allow-popups allow-same-origin allow-scripts allow-top-navigation-by-user-activation" allow="autoplay *; encrypted-media *; clipboard-write" style="width: 100%; overflow: hidden; border-radius: 10px; transform: translateZ(0px); animation: 2s ease 0s 6 normal none running loading-indicator; background-color: rgb(228, 228, 228);"></iframe></td></tr>
"""
                    i += 1
                i += 1
        i += 1

    csvfile.close()

    yearNOW = dldDate[0:4]
    monthNOW = dldDate[0:7]
    monthTextNOW = datetime.datetime.strptime(dldDate, '%Y-%m-%d').strftime('%B')    
    HTMLFile = open(rootFolder + "index.html", "r")
    index = HTMLFile.read()
    monthDB = index[index.find('<a href="AMRs/AMR ') + len('<a href="AMRs/AMR '):index.find('.html">')]
    HTMLFile.close()
    monthTextDB = datetime.datetime.strptime(monthDB, '%Y-%m').strftime('%B')
    yearDB = monthDB[0:4]
    newMonth = 0
    newYear = 0

    if yearNOW != yearDB:
        newYear = 1
        with open(rootFolder + 'index.html', 'r+') as idx:
            idxContent = idx.read()
            idxContent = idxContent.replace('\n    <h2 class="title svelte-hprj71" data-testid="header-title">' + yearDB + ':</h2>',
                                            '\n    <h2 class="title svelte-hprj71" data-testid="header-title">' + yearNOW + ':</h2>\n        <a href="AMRs/AMR ' + monthNOW + '.html">' + monthTextNOW + '</a><br>\n    <h2 class="title svelte-hprj71" data-testid="header-title">' + yearDB + ':</h2>')
            idx.seek(0, 0)
            idx.write(idxContent)
        idx.close()
    else:
        if monthNOW != monthDB:
            newMonth = 1
            with open(rootFolder + 'index.html', 'r+') as idx:
                idxContent = idx.read()
                idxContent = idxContent.replace('\n        <a href="AMRs/AMR ' + monthDB + '.html">' + monthTextDB + '</a>',
                                                '\n        <a href="AMRs/AMR ' + monthNOW + '.html">' + monthTextNOW + '</a> | \n        <a href="AMRs/AMR ' + monthDB + '.html">' + monthTextDB + '</a>')
                idx.seek(0, 0)
                idx.write(idxContent)
            idx.close()

    if htmlText != '':
        if newMonth == 1 or newYear == 1:
            with open(amrsFolder + 'AMR ' + monthNOW + '.html', 'w') as h2r:
                h2r.write(htmlHead + '\n' + htmlStart + htmlText + htmlEnd + '\n' + htmlFinal)
            h2r.close()            
        else:
            with open(amrsFolder + 'AMR '+monthNOW + '.html', 'r+') as h2r:
                h2rContent = h2r.read()
                h2rContent = h2rContent.replace(htmlHead, '')
                h2r.seek(0, 0)
                h2r.write(htmlHead + '\n' + htmlStart + htmlText + htmlEnd + '\n' + h2rContent)
            h2r.close()
#----------------------------------------------------------------------------------------------------

def coming_soon(caLink):
    global messageCS
    CS_request = s.get(caLink)
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

            CS2_request = s.get(a_product_lockup__title_href)
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

        i += 1
    
    AMRelDate = 'Date 0, 9999'
    for index, row in pdNR.sort_values(by=['amReleaseDate', 'amSort'], ascending=[True, True]).iterrows():
        #here must be <li> building construction!
        if row.iloc[11] <= datetime.datetime.now() + datetime.timedelta(hours=3): ## GitHub server time is UTC (-3 from Moscow), so i add +3 hours to log actions in Moscow time. Only where time matters
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

        pdCS = pd.read_csv(csReleasesDB, sep=";")
        pdAIDDB = pd.read_csv(artistIDsDB, sep=";")
        if len(pdCS.loc[pdCS['album__href'] == row.iloc[7]]) == 0:
            row.iloc[13] = 1

            fieldNamesCS = ['update__date', 'album_cover__jpeg', 'album__href', 'album__name', 'artist__href', 'artist__name', 'release__date', 'release__date_text']
            csvCS = open(csReleasesDB, 'a+', newline='') 
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
                img_caption = f'*{ReplaceSymbols(row.iloc[10].replace('&amp;','&'))}* \\- [{ReplaceSymbols(row.iloc[8].replace('&amp;','&'))}]({row.iloc[7].replace('://','://embed.')})\n{ReplaceSymbols(str(row.iloc[11])[0:10])}'
                messageCS = send_photo_url('Coming Soon', img_url, img_caption)

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

## GitHub server time is UTC (-3 from Moscow), so i add +3 hours to log actions in Moscow time. Only where time matters
    html_li += '''
      </ul>
    </div> 
  </div>   
</div>
<div class="main">
  <i>Updated: ''' + str(datetime.datetime.now() + datetime.timedelta(hours=3)) + '''</i>
</div>
</body>
'''

    with open(rootFolder + 'index.html', 'r+') as idx2:
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

    pdNR = pd.read_csv(newReleasesDB, sep=";")
    pdCS = pd.read_csv(csReleasesDB, sep=";")
    pdCSNR = pd.DataFrame(columns=['artist', 'album', 'link', 'image'])

    for index, row in pdCS.iterrows():
        if datetime.datetime.strptime(row.iloc[6], "%Y-%m-%d %H:%M:%S") <= datetime.datetime.now():
            if len(pdNR.loc[pdNR['link'] == row.iloc[2]]) == 0:
                CS2_request = s.get(row.iloc[2])
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
    pdCS.to_csv(csReleasesDB, sep=';', index=False)
    pdNR = pd.DataFrame()
    pdCS = pd.DataFrame()

    if len(pdCSNR) > 0:
        dldCategory = 'CS'
        caText = 'METAL - CS'
        caGrad = '#81BB98, #9AD292'

        dldDate = str(datetime.datetime.now())[0:10]
        htmlHead = """<head>
  <meta charset="utf-8">
  <title>Apple Music Releases</title>
  <link rel="stylesheet" type="text/css" href="../Resources/styles.css" />
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
  <input type="button" onclick="location.href='../index.html';" value="Index"  class="bI"/>
  <hr>
"""

        htmlStart = """  <table border="1">
    <tr id=""" + ('\"' + dldDate + '_' + caText + '\"').lower().replace(' ','_') +  """><th colspan="2" style="background: linear-gradient(to right, """ + caGrad + """);">""" + dldDate + """ | """ + caText + """</th></tr>
    <tr><th width="100px">Cover</th><th width="600px">Album</th></tr>
"""

        htmlText = ''

        htmlEnd = """  </table>
  <hr>
"""

        htmlFinal = """  <!-- End of File -->
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

        fieldNames = ['date', 'category', 'artist', 'album', 'Best_Fav_New_OK', 'rec_send2TG', 'link', 'link_ym', 'link_zv', 'imga', 'send2TG', 'TGmsgID']
        csvfile = open(newReleasesDB, 'a+', newline='')
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldNames)

        for index, row in pdCSNR.iterrows():
            aralname = row.iloc[0] + ' - ' + row.iloc[1]
            # YM & Zvuk search --------------
            ym_zv_search_string = f'{row.iloc[0].replace('&amp;','&')} - {row.iloc[1].replace('&amp;','&')}' 
            ym_year = dldDate[0:4]
            ym_result = ''
            zv_result = ''
            ym_result = search_album_ym(ym_zv_search_string, ym_year)
            if ZVUK_ERROR == '':
                zv_result = search_album_zv(ym_zv_search_string)
            else:
                zv_result = ''
            # -------------------------------
            aralinsert = aralname.replace(row.iloc[0], row.iloc[0] + '</b>') if len(aralname) < 80 else aralname[:aralname[:80].rfind(' ') + 1].replace(row.iloc[0], row.iloc[0] + '</b>') + '<br>' + aralname[aralname[:80].rfind(' ') + 1:]
            writer.writerow({'date': dldDate, 
                          'category': dldCategory, 
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

            htmlText += f"""  <!-- {row.iloc[0]} - {row.iloc[1]} -->
    <tr style="display:;" id=''>
      <td><a href="{row.iloc[3].replace('296x296bb.webp', '100000x100000-999.jpg').replace('296x296bf.webp', '100000x100000-999.jpg').replace('296x296bf-60.jpg', '100000x100000-999.jpg')}" target="_blank"><img src="{row.iloc[3]}" height="100px"></a></td>
      <td class="album_name"><a href="{row.iloc[2]}" target="_blank"><b>{aralinsert}</a><br><br><button data-frame-load="{row.iloc[2][row.iloc[2].rfind('/') + 1:]}">Preview</button>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<a href="{ym_result if ym_result is not None else ''}" target="_blank"><button{' disabled' if ym_result is None or ym_result == '' else  ''}>Яндекс.Музыка</button></a>&nbsp;<a href="{zv_result if zv_result is not None else ''}" target="_blank"><button{' disabled' if zv_result is None or zv_result == '' else ''}>Звук</button></a></td>
    </tr> 
    <tr style="display:none;" id="show{row.iloc[2][row.iloc[2].rfind('/') + 1:]}_"><td colspan="2"><iframe id="embedPlayer" data-frame-group="{row.iloc[2][row.iloc[2].rfind('/') + 1:]}" data-frame-src="{row.iloc[2].replace('://', '://embed.')}?app=music&amp;itsct=music_box_player&amp;itscg=30200&amp;ls=1&amp;theme=light" height="450px" frameborder="0" sandbox="allow-forms allow-popups allow-same-origin allow-scripts allow-top-navigation-by-user-activation" allow="autoplay *; encrypted-media *; clipboard-write" style="width: 100%; overflow: hidden; border-radius: 10px; transform: translateZ(0px); animation: 2s ease 0s 6 normal none running loading-indicator; background-color: rgb(228, 228, 228);"></iframe></td></tr>
"""

        csvfile.close()

        yearNOW = dldDate[0:4]
        monthNOW = dldDate[0:7]
        monthTextNOW = datetime.datetime.strptime(dldDate, '%Y-%m-%d').strftime('%B')    
        HTMLFile = open(rootFolder + "index.html", "r")
        index = HTMLFile.read()
        monthDB = index[index.find('<a href="AMRs/AMR ') + len('<a href="AMRs/AMR '):index.find('.html">')]
        HTMLFile.close()
        monthTextDB = datetime.datetime.strptime(monthDB, '%Y-%m').strftime('%B')
        yearDB = monthDB[0:4]
        newMonth = 0
        newYear = 0

        if yearNOW != yearDB:
            newYear = 1
            with open(rootFolder + 'index.html', 'r+') as idx:
                idxContent = idx.read()
                idxContent = idxContent.replace('\n    <h2 class="title svelte-hprj71" data-testid="header-title">' + yearDB + ':</h2>',
                                              '\n    <h2 class="title svelte-hprj71" data-testid="header-title">' + yearNOW + ':</h2>\n        <a href="AMRs/AMR ' + monthNOW + '.html">' + monthTextNOW + '</a><br>\n    <h2 class="title svelte-hprj71" data-testid="header-title">' + yearDB + ':</h2>')
                idx.seek(0, 0)
                idx.write(idxContent)
            idx.close()
        else:
            if monthNOW != monthDB:
                newMonth = 1
                with open(rootFolder + 'index.html', 'r+') as idx:
                    idxContent = idx.read()
                    idxContent = idxContent.replace('\n        <a href="AMRs/AMR ' + monthDB + '.html">' + monthTextDB + '</a>',
                                                    '\n        <a href="AMRs/AMR ' + monthNOW + '.html">' + monthTextNOW + '</a> | \n        <a href="AMRs/AMR ' + monthDB + '.html">' + monthTextDB + '</a>')
                    idx.seek(0, 0)
                    idx.write(idxContent)
                idx.close()

        if htmlText != '':
            if newMonth == 1 or newYear == 1:
                with open(amrsFolder + 'AMR ' + monthNOW + '.html', 'w') as h2r:
                    h2r.write(htmlHead + '\n' + htmlStart + htmlText + htmlEnd + '\n' + htmlFinal)
                h2r.close()            
            else:
                with open(amrsFolder + 'AMR '+monthNOW + '.html', 'r+') as h2r:
                    h2rContent = h2r.read()
                    h2rContent = h2rContent.replace(htmlHead, '')
                    h2r.seek(0, 0)
                    h2r.write(htmlHead + '\n' + htmlStart + htmlText + htmlEnd + '\n' + h2rContent)
                h2r.close()

def nextWeekReleases_sender():
    pdR = pd.read_csv(ReleasesDB, sep=";")

    msg2snd = ''
    msg2snd_nw = ''
    nowDate = str(datetime.datetime.now())[0:10]

    msg2snd += '\U0001F50E This week releases:'
    if len(pdR[(pdR['downloadedRelease'] == 'd') & (pdR['releaseDate'] <= nowDate)]) > 0:
        for index, row in pdR[(pdR['downloadedRelease'] == 'd') & (pdR['releaseDate'] <= nowDate)].sort_values(by=['releaseDate','mainArtist'], ascending=[True, True]).iterrows():
            msg2snd += f'\n*{ReplaceSymbols(row.iloc[3].replace('&amp;','&'))}* \\- {ReplaceSymbols(row.iloc[4].replace('&amp;','&'))}'
    else:
        msg2snd += '\n\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F'

    week_date = '0000-00-00'
    msg2snd_nw += '\U000023F3 Next weeks releases:'
    if len(pdR[(pdR['downloadedRelease'] == 'd') & (pdR['releaseDate'] > nowDate)]) > 0:
        for index, row in pdR[(pdR['downloadedRelease'] == 'd') & (pdR['releaseDate'] > nowDate)].sort_values(by=['releaseDate','mainArtist'], ascending=[True, True]).iterrows():
            if week_date != row.iloc[6]:
                week_date = row.iloc[6]
                msg2snd_nw += f'\n\n__{ReplaceSymbols(week_date)}__'
            msg2snd_nw += f'\n*{ReplaceSymbols(row.iloc[3].replace('&amp;','&'))}* \\- {ReplaceSymbols(row.iloc[4].replace('&amp;','&'))}'
    else:
        msg2snd_nw += '\n\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F'


    send_message('Next Week Releases', msg2snd_nw)
    send_message('Next Week Releases', msg2snd)    

    pdR = pd.DataFrame()
#----------------------------------------------------------------------------------------------------

amnr_logger('[Apple Music New Releases]', ver + " (c)&(p) 2022-" + str(datetime.datetime.now())[0:4] + " by Viktor 'MushroomOFF' Gribov")

message2send = 0
messageCS = 0

caLink = find_link('https://music.apple.com/us/curator/apple-music-metal/976439543', 'New Releases')
caText = 'METAL'
caGrad = '#81BB98, #9AD292'
collect_albums(caLink, caText, caGrad)
amnr_logger('[Apple Music New Releases]', 'Metal [US]     - OK')

caLink = find_link('https://music.apple.com/us/curator/apple-music-hard-rock/979231690', 'New Releases')
caText = 'HARD ROCK'
caGrad = '#EE702E, #F08933'
collect_albums(caLink, caText, caGrad)
amnr_logger('[Apple Music New Releases]', 'Hard Rock [US] - OK')

# caLink = 'https://music.apple.com/ru/room/1118077423'
# caText = 'METAL - RU'
# caGrad = '#81BB98, #9AD292'
# collect_albums(caLink, caText, caGrad)
# amnr_logger('[Apple Music New Releases]', 'Metal [RU]     - OK')

# caLink = 'https://music.apple.com/ru/room/1532200949'
# caText = 'HARD ROCK - RU'
# caGrad = '#EE702E, #F08933'
# collect_albums(caLink, caText, caGrad)
# amnr_logger('[Apple Music New Releases]', 'Hard Rock [RU] - OK')

caLink = find_link('https://music.apple.com/us/curator/apple-music-metal/976439543', 'Coming Soon')
coming_soon(caLink)
amnr_logger('[Apple Music New Releases]', 'Comming Soon   - OK')

CS2NR()
amnr_logger('[Apple Music New Releases]', 'Metal [CS]     - OK')

if message2send == 0:
    send_message('New Releases', '\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F')
if messageCS == 0:
    send_message('Coming Soon', '\U0001F937\U0001F3FB\U0000200D\U00002642\U0000FE0F')

if ZVUK_ERROR != '':
    amnr_logger('[Apple Music New Releases]', f'{ZVUK_ERROR}')

nextWeekReleases_sender()

amnr_logger('[Apple Music New Releases]', '[V] Done!')
