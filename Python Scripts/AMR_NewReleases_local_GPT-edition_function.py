import datetime
import requests
import pandas as pd
import csv


def fetch_page_content(url):
    response = requests.get(url)
    response.encoding = 'UTF-8'
    return response.text


def get_download_category(caText):
    categories = {
        'METAL - Classic. Black. Death. Speed. Prog. Sludge. Doom.': 'M',
        'HARD ROCK': 'HR',
        'METAL - RU - Classic. Black. Death. Speed. Prog. Sludge. Doom.': 'MRU',
        'HARD ROCK - RU': 'HRRU'
    }
    return categories.get(caText, '')


def init_html_head():
    return """<head>
  <meta charset="utf-8">
  <title>Apple Music Releases</title>
  <link rel="stylesheet" type="text/css" href="../../Resources/styles.css" />
  <script language="JavaScript" type="text/JavaScript">
    <!--
    function show(id) {
      var elem = document.getElementById("show" + id);
      elem.style.display = (elem.style.display === 'none') ? '' : 'none';
    }

    function show_tr(id) {
      var elms = document.querySelectorAll("[id='" + id + "']");
      for (var i = 0; i < elms.length; i++) {
        elms[i].style.display = (elms[i].style.display === 'none') ? '' : 'none';
      }
    }
    //-->
  </script>
</head>
<body>
  <input id="bV" type="button" value="V" onclick="show_tr('v');" class="bV" />
  <input id="bD" type="button" value="D" onclick="show_tr('d');" class="bD" />
  <input id="bO" type="button" value="O" onclick="show_tr('o');" class="bO" />
  <input id="bX" type="button" value="X" onclick="show_tr('x');" class="bX" />
  <input id="bE" type="button" value="  " onclick="show_tr('');" class="bE" />
  <input type="button" onclick="location.href='../../index.html';" value="Index"  class="bI"/>
  <hr>
"""


def init_html_start(caGrad, caText, dldDate):
    return f"""  <table border="1">
    <tr><th colspan="2" style="background: linear-gradient(to right, {caGrad});">{dldDate} | {caText}</th></tr>
    <tr><th width="100px">Cover</th><th width="600px">Album</th></tr>
"""


def init_html_end():
    return """  </table>
  <hr>
"""


def init_html_final():
    return """  <!-- End of File -->
  <script id="rendered-js">
    [...document.querySelectorAll('[data-frame-load]')].forEach(button => {
      button.addEventListener('click', () => {
        const group = button.getAttribute('data-frame-load');
        [...document.querySelectorAll(`[data-frame-group="${group}"]`)].forEach(frame => {
          show(frame.getAttribute('data-frame-group') + '_');
          frame.setAttribute('src', frame.getAttribute('data-frame-src'));
        });
      });
    });
  </script>
</body>
"""


def update_index_file(year_now, month_now, month_text_now, year_db, month_db, month_text_db, root_folder):
    index_file_path = f'{root_folder}index.html'
    with open(index_file_path, 'r+') as idx:
        idx_content = idx.read()
        if year_now != year_db:
            idx_content = idx_content.replace(f'\n    <h2 class="title svelte-hprj71" data-testid="header-title">{year_db}:</h2>',
                                              f'\n    <h2 class="title svelte-hprj71" data-testid="header-title">{year_now}:</h2>\n        <a href="AMRs/AMR {month_now}.html">{month_text_now}</a><br>\n    <h2 class="title svelte-hprj71" data-testid="header-title">{year_db}:</h2>')
        elif month_now != month_db:
            idx_content = idx_content.replace(f'\n        <a href="AMRs/AMR {month_db}.html">{month_text_db}</a>',
                                              f'\n        <a href="AMRs/AMR {month_now}.html">{month_text_now}</a> | \n        <a href="AMRs/AMR {month_db}.html">{month_text_db}</a>')
        idx.seek(0)
        idx.write(idx_content)


def save_html_file(file_path, html_content):
    with open(file_path, 'w') as html_file:
        html_file.write(html_content)


def append_html_content(file_path, html_head, html_start, html_text, html_end):
    with open(file_path, 'r+') as html_file:
        html_content = html_file.read()
        html_content = html_content.replace(html_head, '')
        html_file.seek(0)
        html_file.write(html_head + '\n' + html_start + html_text + html_end + '\n' + html_content)


def replace_symbols(text):
    return text.replace('&amp;', '&')


def process_album_entry(artist, album, link, imga, is_my_artist, writer, message2send):
    aralname = f'{artist} - {album}'
    aralinsert = aralname.replace(artist, f'{artist}</b>') if len(aralname) < 80 else aralname[:aralname[:80].rfind(' ') + 1].replace(artist, f'{artist}</b>') + '<br>' + aralname[aralname[:80].rfind(' ') + 1:]

    if is_my_artist > 0:
        message2send += f'\n*{replace_symbols(artist)}* \\- [{replace_symbols(album)}]({link.replace("://", "://embed.")})'

    writer.writerow({
        'date': dldDate,
        'category': dldCategory,
        'artist': replace_symbols(artist),
        'album': replace_symbols(album),
        'Best_Fav_New_OK': '',
        'rec_send2TG': '',
        'link': link,
        'imga': imga,
        'send2TG': '',
        'TGmsgID': ''
    })

    return f"""  <!-- {artist} - {album} -->
    <tr style="display:;" id=''>
      <td><a href="{imga.replace('296x296bb.webp', '100000x100000-999.jpg').replace('296x296bf.webp', '100000x100000-999.jpg')}" target="_blank"><img src="{imga}" height="100px"></a></td>
      <td class="album_name"><a href="{link}" target="_blank"><b>{aralinsert}</a><br><br><button data-frame-load="{link[link.rfind('/') + 1:]}">Preview</button></td>
    </tr>
    <tr style="display:none;" id="show{link[link.rfind('/') + 1:]}_"><td colspan="2"><iframe id="embedPlayer" data-frame-group="{link[link.rfind('/') + 1:]}" data-frame-src="{link.replace('://', '://embed.')}?app=music&amp;itsct=music_box_player&amp;itscg=30200&amp;ls=1&amp;theme=light" height="450px" frameborder="0" sandbox="allow-forms allow-popups allow-same-origin allow-scripts allow-top-navigation-by-user-activation" allow="autoplay *; encrypted-media *; clipboard-write" style="width: 100%; overflow: hidden; border-radius: 10px; transform: translateZ(0px); animation: 2s ease 0s 6 normal none running loading-indicator; background-color: rgb(228, 228, 228);"></iframe></td></tr>
"""


def collect_albums(caLink, caText, caGrad, root_folder, new_releases_db, artist_ids_db, amrs_folder, message2send):
    dldCategory = get_download_category(caText)
    dldDate = datetime.datetime.now().strftime('%Y-%m-%d')

    html_head = init_html_head()
    html_start = init_html_start(caGrad, caText, dldDate)
    html_end = init_html_end()
    html_final = init_html_final()

    pd_db = pd.read_csv(new_releases_db, sep=";")
    pd_aid_db = pd.read_csv(artist_ids_db, sep=";")
    
    res = fetch_page_content(caLink)

    html_text = ''
    full_card_0 = '<li class="grid-item '
    full_card_1 = '</li>'
    i = res.find('<div class="content-container ')
    pos = res.find('<footer ')

    with open(new_releases_db, 'a+', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=['date', 'category', 'artist', 'album', 'Best_Fav_New_OK', 'rec_send2TG', 'link', 'imga', 'send2TG', 'TGmsgID'])

        while i < pos:
            if res.find(full_card_0, i) > -1:
                pos_card_0 = res.find(full_card_0, i) + len(full_card_0)
                pos_card_1 = res.find(full_card_1, pos_card_0)
                i = pos_card_0

                while i < pos_card_1:
                    sstr = '<picture '
                    if res[i:i + len(sstr)] == sstr:
                        pos_pic_0 = res.find('srcset="', i) + len('srcset="')
                        pos_pic_1 = res.find(' ', pos_pic_0)
                        imga = res[pos_pic_0:pos_pic_1].strip()
                        i = res.find('</picture>', i)
                    
                    sstr = '<div class="product-lockup__title-link '
                    if res[i:i + len(sstr)] == sstr:
                        pos_link_0 = res.find('<a href="', i) + len('<a href="')
                        pos_link_1 = res.find('"', pos_link_0)
                        link = res[pos_link_0:pos_link_1].strip()
                        i = pos_link_1
                        pos_album_0 = res.find('>', i) + len('>')
                        pos_album_1 = res.find('<', pos_album_0)
                        album = res[pos_album_0:pos_album_1].strip()
                        i = pos_album_1

                        sstr = '<p data-testid="product-lockup-subtitles" '
                        i = res.find(sstr, i) + len(sstr)
                        p_end = res.find('</p>', i)
                        artist = ''
                        artist_id = ''
                        is_my_artist = 0

                        while i < p_end:
                            pos_art_id_1 = res.find('" class="product-lockup__subtitle link', i)
                            if pos_art_id_1 < p_end and pos_art_id_1 > -1:
                                pos_art_id_0 = res.rfind('/', i, pos_art_id_1) + len('/')
                                artist_id = res[pos_art_id_0:pos_art_id_1].strip()
                                if float(artist_id) in pd_aid_db['mainId'].values:
                                    is_my_artist += 1
                            pos_artist_0 = res.find('>', i) + len('>')
                            pos_artist_1 = res.find('<', pos_artist_0)
                            if res[pos_artist_0:pos_artist_1].strip() == ',':
                                artist += ';'
                            else:
                                artist += res[pos_artist_0:pos_artist_1].strip()
                            i = pos_artist_1
                            i += 1

                        artist = artist.replace('&amp;', '_&_').replace(';', '; ').replace('_&_', '&amp;')
                        check = 0

                        for index, row in pd_db.iterrows():
                            if row['link'][row['link'].rfind('/') + 1:] == link[link.rfind('/') + 1:]:
                                check = 1
                                break

                        if check == 0 and artist:
                            html_text += process_album_entry(artist, album, link, imga, is_my_artist, writer, message2send)

                        i += 1
                    i += 1
            i += 1

    year_now = dldDate[:4]
    month_now = dldDate[:7]
    month_text_now = datetime.datetime.strptime(dldDate, '%Y-%m-%d').strftime('%B')

    with open(f"{root_folder}index.html", "r") as html_file:
        index = html_file.read()
        month_db = index[index.find('<a href="AMRs/AMR ') + len('<a href="AMRs/AMR '):index.find('.html">')]
        month_text_db = datetime.datetime.strptime(month_db, '%Y-%m').strftime('%B')
        year_db = month_db[:4]

    if html_text:
        if year_now != year_db or month_now != month_db:
            update_index_file(year_now, month_now, month_text_now, year_db, month_db, month_text_db, root_folder)
            save_html_file(f"{amrs_folder}AMR {month_now}.html", html_head + '\n' + html_start + html_text + html_end + '\n' + html_final)
        else:
            append_html_content(f"{amrs_folder}AMR {month_now}.html", html_head, html_start, html_text, html_end)
