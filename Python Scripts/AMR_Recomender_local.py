SCRIPT_NAME = "Apple Music Releases LookApp Errors"
VERSION = "v.2.025.10 [Local]"
# Python 3.12 & Pandas 2.2 ready
# Multiparameters

import os
import json
import datetime
import requests
import pandas as pd
import csv

rootFolder = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
amrsFolder = rootFolder + 'AMRs/'
dbFolder = rootFolder + 'Databases/'
newReleasesDB = dbFolder + 'AMR_newReleases_DB.csv' # This Week New Releases 
log_file = os.path.join(rootFolder, 'status.log')
# Telegram -------------------------------
PARAMS = input("IMPORTANT! TOKEN chat_id YM_TOKEN ZV_TOKEN: ").split(' ')
TOKEN = ''
chat_id = ''
if len(PARAMS) > 1:
    TOKEN = PARAMS[0] # input("Telegram Bot TOKEN: ")
    chat_id = PARAMS[1] # input("Telegram Bot CHAT_ID: ")
URL = 'https://api.telegram.org/bot'
thread_id = {'New Updates': 6, 'Top Releases': 10, 'Coming Soon': 3, 'New Releases': 2, 'Next Week Releases': 80}
#-----------------------------------------
# Логирование
def logger(script_name, log_line):
    """Запись лога в файл."""
    with open(log_file, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(str(datetime.datetime.now()) + ' - ' + script_name + ' - ' + log_line.rstrip('\r\n') + '\n' + content)

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

print("##############################################################")
print("""                       _      __  __           _            
     /\\               | |    |  \\/  |         (_)           
    /  \\   _ __  _ __ | | ___| \\  / |_   _ ___ _  ___       
   / /\\ \\ | '_ \\| '_ \\| |/ _ \\ |\\/| | | | / __| |/ __|      
  / ____ \\| |_) | |_) | |  __/ |  | | |_| \\__ \\ | (__       
 /_/___ \\_\\ .__/| .__/|_|\\___|_|  |_|\\__,_|___/_|\\___|      
 |  __ \\  | | | | |                                         
 | |__) |_|_| | |_|  __ _ ___  ___  ___                     
 |  _  // _ \\ |/ _ \\/ _` / __|/ _ \\/ __|                    
 | | \\ \\  __/ |  __/ (_| \\__ \\  __/\\__ \\                    
 |_|__\\_\\___|_|\\___|\\__,_|___/\\___||___/        _           
 |  __ \\                                       | |          
 | |__) |___  ___ ___  _ __ ___   ___ _ __   __| | ___ _ __ 
 |  _  // _ \\/ __/ _ \\| '_ ` _ \\ / _ \\ '_ \\ / _` |/ _ \\ '__|
 | | \\ \\  __/ (_| (_) | | | | | |  __/ | | | (_| |  __/ |   
 |_|  \\_\\___|\\___\\___/|_| |_| |_|\\___|_| |_|\\__,_|\\___|_|   
""")
print(" " + VERSION)
print(" (c)&(p) 2022-" + str(datetime.datetime.now())[0:4] + " by Viktor 'MushroomOFF' Gribov")
print("##############################################################")
print('')

logMes = f"{VERSION} (c)&(p) 2022-{str(datetime.datetime.now())[0:4]} by Viktor 'MushroomOFF' Gribov"
logger(f'[{SCRIPT_NAME}]', logMes)

pdNR = pd.read_csv(newReleasesDB, sep=";")

# Check AMR files for recomendations
oks = 0
ers = 0
emp = 0
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
    elif len(relRec) == 0:
        emp += 1
    else:
        pdNR.loc[index,'Best_Fav_New_OK'] = 'E'
        ers += 1
    htmlFile.close()
logMes = f'OK: {oks}; Emptys: {emp}; Errors: {ers}'
logger(f'[{SCRIPT_NAME}]', logMes)
print(logMes)

trs = 0
# Send to Top Releases (O)
for index, row in pdNR[(pdNR['Best_Fav_New_OK'] == 'o') & (pdNR['TGmsgID'].isna())].iterrows():
    img_url = row.loc['imga'].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
    img_caption = f'*{ReplaceSymbols(row.loc['artist'].replace('&amp;','&'))}* \\- [{ReplaceSymbols(row.loc['album'].replace('&amp;','&'))}]({row.loc['link'].replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({row.loc['link']}){'' if pd.isna(row.loc['link_ym']) else f'\n\U0001F4A5 [Яндекс\\.Музыка]({row.loc['link_ym']})'}{'' if pd.isna(row.loc['link_zv']) else f'\n\U0001F50A [Звук]({row.loc['link_zv']})'}'
    message2send = send_photo_url('Top Releases', img_url, img_caption)
    if TOKEN != '' and chat_id != '':
        pdNR.loc[index,'TGmsgID'] = message2send
    trs += 1

nrs = 0
# Send to New Releases (V, D)
for index, row in pdNR[(pdNR['Best_Fav_New_OK'].isin(['v','d'])) & (pdNR['TGmsgID'].isna())].iterrows():
    img_url = row.loc['imga'].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
    img_caption = f'*{ReplaceSymbols(row.loc['artist'].replace('&amp;','&'))}* \\- [{ReplaceSymbols(row.loc['album'].replace('&amp;','&'))}]({row.loc['link'].replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({row.loc['link']}){'' if pd.isna(row.loc['link_ym']) else f'\n\U0001F4A5 [Яндекс\\.Музыка]({row.loc['link_ym']})'}{'' if pd.isna(row.loc['link_zv']) else f'\n\U0001F50A [Звук]({row.loc['link_zv']})'}'
    message2send = send_photo_url('New Releases', img_url, img_caption)
    if TOKEN != '' and chat_id != '':
        pdNR.loc[index,'TGmsgID'] = message2send
    nrs += 1

# WRITE to FILE !!!
pdNR.to_csv(newReleasesDB, sep=';', index=False)
pdNR = pd.DataFrame()
logMes = f'New Releases: {nrs}; Top Releases: {trs}'
logger(f'[{SCRIPT_NAME}]', logMes)
print(logMes)

if TOKEN == '' or chat_id == '':
    logMes = 'Message not sent! No TOKEN or CHAT_ID'
    logger(f'[{SCRIPT_NAME}]', logMes)
    print(logMes)

logMes = '[V] Done!'
logger(f'[{SCRIPT_NAME}]', logMes)
print(logMes)
