ver = "v.2.025.06 [GitHub]"
# Python 3.12 & Pandas 2.2 ready
# comment will mark the specific code for GitHub

import os
import json
import datetime
import requests
import pandas as pd
import csv

rootFolder = '' # root is root
amrsFolder = rootFolder + 'AMRs/'
dbFolder = rootFolder + 'Databases/'
newReleasesDB = dbFolder + 'AMR_newReleases_DB.csv' # This Week New Releases 
logFile = rootFolder + 'status.log' # path to log file
# Telegram -------------------------------
URL = 'https://api.telegram.org/bot'
TOKEN = os.environ['tg_token'] # GitHub Secrets
chat_id = os.environ['tg_channel_id'] # GitHub Secrets
thread_id = {'New Updates': 6, 'Top Releases': 10, 'Coming Soon': 3, 'New Releases': 2}
#-----------------------------------------

# This logger is only for GitHub --------------------------------------------------------------------
def amnr_logger(pyScript, logLine):
    with open(logFile, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        # GitHub server time is UTC (-3 from Moscow), so i add +3 hours to log actions in Moscow time. Only where time matters
        f.write(str(datetime.datetime.now() + datetime.timedelta(hours=3)) + ' - ' + pyScript + ' - ' + logLine.rstrip('\r\n') + '\n' + content)
#----------------------------------------------------------------------------------------------------

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
#----------------------------------------------------------------------------------------------------

amnr_logger('[Apple Music Releases Recomender]', f"{ver} (c)&(p) 2022-{str(datetime.datetime.now())[0:4]} by Viktor 'MushroomOFF' Gribov")

pdNR = pd.read_csv(newReleasesDB, sep=";")

# Check AMR files for recomendations
oks = 0
ers = 0
for index, row in pdNR[pdNR['Best_Fav_New_OK'].isna()].iterrows():
    amrLink = f'{amrsFolder}AMR {row.iloc[0][0:7]}.html'
    htmlFile = open(amrLink, 'r', encoding='utf-8')
    source_code = htmlFile.read()
    str2find = f'<!-- {row.iloc[2]} - {row.iloc[3]} -->'
    strt = source_code.find(str2find)
    pos_id_0 = source_code.find("id='", strt) + len("id='")
    pos_id_1 = source_code.find("'>", pos_id_0)
    relRec = source_code[pos_id_0:pos_id_1].strip()
    if len(relRec) == 1:
        pdNR.loc[index,'Best_Fav_New_OK'] = relRec
        oks += 1
    else:
        pdNR.loc[index,'Best_Fav_New_OK'] = 'E'
        ers += 1
amnr_logger('[Apple Music Releases Recomender]', f'OK: {oks}; Errors: {ers}')

trs = 0
# Send to Top Releases (O)
for index, row in pdNR[(pdNR['Best_Fav_New_OK'] == 'o') & (pdNR['TGmsgID'].isna())].iterrows():
    img_url = row.iloc[7].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
    img_caption = f'*{ReplaceSymbols(row.iloc[2].replace('&amp;','&'))}* \\- [{ReplaceSymbols(row.iloc[3].replace('&amp;','&'))}]({row.iloc[6].replace('://','://embed.')})'
    message2send = send_photo_url('Top Releases', img_url, img_caption)
    pdNR.loc[index,'TGmsgID'] = message2send
    trs += 1

nrs = 0
# Send to New Releases (V, D)
for index, row in pdNR[(pdNR['Best_Fav_New_OK'].isin(['v','d'])) & (pdNR['TGmsgID'].isna())].iterrows():
    img_url = row.iloc[7].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
    img_caption = f'*{ReplaceSymbols(row.iloc[2].replace('&amp;','&'))}* \\- [{ReplaceSymbols(row.iloc[3].replace('&amp;','&'))}]({row.iloc[6].replace('://','://embed.')})'
    message2send = send_photo_url('New Releases', img_url, img_caption)
    pdNR.loc[index,'TGmsgID'] = message2send
    nrs += 1

# WRITE to FILE !!!
pdNR.to_csv(newReleasesDB, sep=';', index=False)
pdNR = pd.DataFrame()
amnr_logger('[Apple Music Releases Recomender]', f'New Releases: {nrs}; Top Releases: {trs}')
amnr_logger('[Apple Music Releases Recomender]', '[V] Done!')
