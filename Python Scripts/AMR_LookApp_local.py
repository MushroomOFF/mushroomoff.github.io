SCRIPT_NAME = "Apple Music Releases LookApp"
VERSION = "v.2.025.10 [Local]"
# Python 3.12 & Pandas 2.2 ready
# Multiparameters

import requests
import os
import pandas as pd
import csv
import time
import json
import datetime
from math import nan

# Инициализация переменных================================================

root_folder = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io'
db_folder = 'Databases'
releases_db = os.path.join(root_folder, db_folder, 'AMR_releases_DB.csv')
artist_id_db = os.path.join(root_folder, db_folder, 'AMR_artisitIDs.csv')
log_file = os.path.join(root_folder, 'status.log')
field_names = ['dateUpdate', 'downloadedRelease', 'mainArtist', 'artistName', 'collectionName', 
               'trackCount', 'releaseDate', 'releaseYear', 'mainId', 'artistId', 'collectionId', 
               'country', 'artworkUrlD', 'downloadedCover', 'updReason']
#---------------------v  отрезал JP
countries = input("Какие страны проверить?\nEnter: [us, ru, jp]\n2:     [us, ru]\njp:    [jp]\n")
if countries == 'jp':
    countries = ['jp']
elif countries == '2':
    countries = ['us', 'ru']
else:
    countries = ['us', 'ru', 'jp']
print(countries)

emojis = {'us': '\U0001F1FA\U0001F1F8', 'ru': '\U0001F1F7\U0001F1FA', 'jp': '\U0001F1EF\U0001F1F5', 'no': '\U0001F3F3\U0000FE0F', 'wtf': '\U0001F914', 
          'album': '\U0001F4BF', 'cover': '\U0001F3DE\U0000FE0F', 'error': '\U00002757\U0000FE0F', 'empty': '\U0001F6AB', 'badid': '\U0000274C'}
# Telegram -------------------------------
PARAMS = input("IMPORTANT! TOKEN chat_id YM_TOKEN ZV_TOKEN: ").split(' ')
TOKEN = ''
CHAT_ID = ''
if len(PARAMS) > 1:
    TOKEN = PARAMS[0] # input("Telegram Bot TOKEN: ")
    CHAT_ID = PARAMS[1] # input("Telegram Bot CHAT_ID: ")
URL = 'https://api.telegram.org/bot'
thread_id = {'New Updates': 6, 'Top Releases': 10, 'Coming Soon': 3, 'New Releases': 2, 'Next Week Releases': 80}
#CHAT_ID = '-1001939128351' #Test channel
#-----------------------------------------

# establishing session
session = requests.Session() 
session.headers.update({'Referer': 'https://itunes.apple.com', 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'})

# Инициализация функций===================================================

# Процедура Замены символов для Markdown v2
def ReplaceSymbols(rsTxt):
    rsTmplt = """'_*[]",()~`>#+-=|{}.!"""
    for rsf in range(len(rsTmplt)):
        rsTxt = rsTxt.replace(rsTmplt[rsf], '\\' + rsTmplt[rsf])
    return rsTxt

# Процедура Отправки сообщения ботом в канал
def send_message(topic, text):
    method = URL + TOKEN + "/sendMessage"
    r = requests.post(method, data={"message_thread_id": thread_id[topic], "chat_id": CHAT_ID, "parse_mode": 'MarkdownV2', "text": text})
    json_response = json.loads(r.text)
    rmi = json_response['result']['message_id']   
    return rmi

# Процедура логирования
def logger(script_name, log_line):
    with open(log_file, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(str(datetime.datetime.now()) + ' - ' + script_name + ' - ' + log_line.rstrip('\r\n') + '\n' + content)

# Процедура Загрузки библиотеки
def CreateDB():
    if not os.path.exists(releases_db):
        with open(releases_db, 'a+', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=field_names)
            writer.writeheader()
        print('[V] Database created')
    else:
        print('[V] Database exists')
    print('')

# Процедура Поиска релизов исполнителя в базе iTunes  
def FindReleases(artistID, cRow, artistPrintName):
    global message2send, messageEmpty, messageError, messageBadID
    allDataFrame = pd.DataFrame()
    dfExport = pd.DataFrame()
    check_ers = 0
    for country in countries:
        url = 'https://itunes.apple.com/lookup?id=' + str(artistID) + '&country=' + country + '&entity=album&limit=200'
        request = session.get(url)
        if request.status_code == 200:     
            dJSON = json.loads(request.text)
            if dJSON['resultCount'] > 1:
                dfTemp = pd.DataFrame(dJSON['results'])
                allDataFrame = pd.concat([allDataFrame, dfTemp[['artistName', 'artistId', 'collectionId', 'collectionName', 'artworkUrl100', 'trackCount', 'country', 'releaseDate']]], ignore_index=True)
            else:
                if check_ers == 0:
                    print('\n', end='')
                print(' ' + country + ' - EMPTY |', sep=' ', end='', flush=True)
                logger(f'[{SCRIPT_NAME}]', f'{artistPrintName} - {artistID} - {country} - EMPTY')
                messageEmpty += '\n' + emojis[country] + ' *' + ReplaceSymbols(artistPrintName.replace('&amp;','and')) + '*'
                check_ers = 1
        else:
            if check_ers == 0:
                print('\n', end='')
            print(' ' + country + ' - ERROR (' + str(request.status_code) + ') |', sep=' ', end='', flush=True)
            logger(f'[{SCRIPT_NAME}]', f'{artistPrintName} - {artistID} - {country} - ERROR ({request.status_code})')
            messageError += '\n' + emojis[country] + ' *' + ReplaceSymbols(artistPrintName.replace('&amp;','and')) + '*'
            check_ers = 1
        time.sleep(1) # обход блокировки
    allDataFrame.drop_duplicates(subset='artworkUrl100', keep='first', inplace=True, ignore_index=True)
    if len(allDataFrame) > 0:
        dfExport = allDataFrame.loc[allDataFrame['collectionName'].notna()]
    elif len(countries) > 1:
        if check_ers == 0:
            print('\n', end='')
        print(' Bad ID: ' + str(artistID), sep=' ', end='', flush=True)
        logger(f'[{SCRIPT_NAME}]', f'{artistPrintName} - {artistID} - Bad ID')
        messageBadID += '\n' + emojis['no'] + ' *' + ReplaceSymbols(artistPrintName.replace('&amp;','and')) + '*'
        check_ers = 1

    if check_ers == 1:
        print ('') 

    if len(dfExport) > 0:
        pdiTunesDB = pd.read_csv(releases_db, sep=";")
        #Открываем файл лога для проверки скаченных файлов и записи новых скачиваний
        csvfile = open(releases_db, 'a+', newline='')
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=field_names)

        dateUpdate = str(datetime.datetime.now())[0:19]
        # mainArtist = allDataFrame['artistName'].loc[0]
        mainArtist = artistPrintName
        mainId = artistID
        updReason = ''
        newRelCounter = 0
        newCovCounter = 0
        #Cкачиваем обложки
        for index, row in dfExport.iterrows():
            artistName = row.iloc[0]
            artistId = row.iloc[1]
            collectionId = row.iloc[2]
            collectionName = row.iloc[3]
            artworkUrl100 = row.iloc[4]
            trackCount = row.iloc[5]
            country = row.iloc[6]
            releaseDate = row.iloc[7][:10]
            releaseYear = row.iloc[7][:4]
            artworkUrlD = row.iloc[4].replace('100x100bb', '100000x100000-999')
            downloadedCover = ''
            downloadedRelease = ''
            updReason = ''
            if len(pdiTunesDB.loc[pdiTunesDB['collectionId']  == dfExport.iloc[index-1]['collectionId']])  == 0:
                updReason = 'New release'
                newRelCounter += 1
            elif len(pdiTunesDB[pdiTunesDB['artworkUrlD'].str[40:] == dfExport.iloc[index-1]['artworkUrl100'].replace('100x100bb', '100000x100000-999')[40:]]) == 0:
                updReason = 'New cover'
                newCovCounter += 1
                #.str[40] -------------------------------V
                #https://is2-ssl.mzstatic.com/image/thumb/Music/v4/b2/cc/64/b2cc645c-9f18-db02-d0ab-69e296ea4d70/source/100000x100000-999.jpg

            #Это проверка - нужно ли сверяться с логом
            if updReason != '':
                writer.writerow({
                    'dateUpdate': dateUpdate[:10], 'downloadedRelease': downloadedRelease, 
                    'mainArtist': mainArtist,
                    'artistName': artistName, 'collectionName': collectionName, 
                    'trackCount': trackCount, 'releaseDate': releaseDate, 
                    'releaseYear': releaseYear, 'mainId': mainId, 'artistId': artistId, 
                    'collectionId': collectionId, 'country': country, 'artworkUrlD': artworkUrlD, 
                    'downloadedCover': downloadedCover, 'updReason': updReason
                    })

        csvfile.close()

        artistIDlist.iloc[cRow, 2] = dateUpdate
        artistIDlist.to_csv(artist_id_db, sep=';', index=False)

        pdiTunesDB = pd.DataFrame() 
        if (newRelCounter + newCovCounter) > 0:
            print('\n^ ' + str(newRelCounter + newCovCounter) + ' new records: ' + str(newRelCounter) + ' releases, ' + str(newCovCounter) + ' covers')
            logger(f'[{SCRIPT_NAME}]', f'{artistPrintName} - {artistID} - {newRelCounter + newCovCounter} new records: {newRelCounter} releases, {newCovCounter} covers')
            if newRelCounter > 0 :
                iconka = 'album'
            else:
                iconka = 'cover'
            message2send += '\n' + emojis[iconka] + ' *' + ReplaceSymbols(artistPrintName.replace('&amp;','and')) + '*: ' + str(newRelCounter + newCovCounter)

    else:
        artistIDlist.iloc[cRow, 2] = str(datetime.datetime.now())[0:19]
        artistIDlist.to_csv(artist_id_db, sep=';', index=False)
# Инициализация функций===================================================

print("########################################################")
print("""     _                _        __  __           _      
    / \\   _ __  _ __ | | ___  |  \\/  |_   _ ___(_) ___ 
   / _ \\ | '_ \\| '_ \\| |/ _ \\ | |\\/| | | | / __| |/ __|
  / ___ \\| |_) | |_) | |  __/ | |  | | |_| \\__ \\ | (__ 
 /_/   \\_\\ .__/| .__/|_|\\___| |_|  |_|\\__,_|___/_|\\___|
         |_|   |_|  _ \\ ___| | ___  __ _ ___  ___  ___ 
                 | |_) / _ \\ |/ _ \\/ _` / __|/ _ \\/ __|
                 |  _ <  __/ |  __/ (_| \\__ \\  __/\\__ \\
  _              |_| \\_\\___|_|\\___|\\__,_|___/\\___||___/
 | |    ___   ___ | | __   / \\   _ __  _ __            
 | |   / _ \\ / _ \\| |/ /  / _ \\ | '_ \\| '_ \\           
 | |__| (_) | (_) |   <  / ___ \\| |_) | |_) |          
 |_____\\___/ \\___/|_|\\_\\/_/   \\_\\ .__/| .__/           
                                |_|   |_|              
""")
print(f' {VERSION}')
print(f" (c)&(p) 2022-{datetime.datetime.now().strftime('%Y')} by Viktor 'MushroomOFF' Gribov")
print("########################################################")
print('')

logger(f'[{SCRIPT_NAME}]', f"{VERSION} (c)&(p) 2022-{datetime.datetime.now().strftime('%Y')} by Viktor 'MushroomOFF' Gribov")
message2send = ''
# message2send = ReplaceSymbols('====== ' + str(datetime.datetime.now())[:10] + ' ======')
messageErPrt = ReplaceSymbols('======== ERRORS ========')
messageError = emojis['error'] + ' 503 Service Unavailable ' + emojis['error']
messageEmpty = emojis['empty'] + ' Not available in country ' + emojis['empty']
messageBadID = emojis['badid'] + '               Bad ID                ' + emojis['badid']
checkMesSnd = len(message2send)
checkMesErr = len(messageError)
checkMesEmp = len(messageEmpty)
checkMesBad = len(messageBadID)

CreateDB()

pd.set_option('display.max_rows', None)

# Определяем на каком Артисте остановились в прошлый раз. При желании начинаем сначала
starter = 0
while starter == 0:
    artistIDlist = pd.read_csv(artist_id_db, sep=';')
    artID = artistIDlist['mainArtist'].loc[artistIDlist['downloaded'].isna()].head(1)
    if len(artID) != 0:
        curRow = artID.index[0]
        artID.reset_index(drop=True, inplace=True)
        curArt= artID[0]
    else:
        keyLoger = input("Всё закончили. Начнём с начала. Продолжить (Enter) ")
        curRow = 0
        artistIDlist.drop('downloaded', axis=1, inplace=True)
        artistIDlist.insert(2, "downloaded", nan)
        artistIDlist.to_csv(artist_id_db, sep=';', index=False)
    if curRow == 0:
        keyLoger = input("Начнём с начала. Продолжить (Enter) ")
        starter = 1
    else:
        keyLoger = input("Остановились на '" + str(curArt) + "'. Продолжить (Enter) или начать сначала? ")
        if keyLoger == '':
            starter = 1
        else:
            artistIDlist.drop('downloaded', axis=1, inplace=True)
            artistIDlist.insert(2, "downloaded", nan)
            artistIDlist.to_csv(artist_id_db, sep=';', index=False)

print('')
# Эта часть будет крутиться по кургу, пока не откажешься качать новые обложки
returner = ''
while returner == '':
    artID = artistIDlist['mainId'].loc[artistIDlist['downloaded'].isna()].head(1)
    if len(artID) == 0:
        returner = 'x'
    else:
        curRow = artID.index[0]
        artID.reset_index(drop=True, inplace=True)
        curArt= artID[0]

        printArtID = artistIDlist['mainArtist'].loc[artistIDlist['downloaded'].isna()].head(1)
        printArtID.reset_index(drop=True, inplace=True)
        printArtist = printArtID[0]
        print(f'{(printArtist + ' - ' + str(curArt)):55}', end='\r')

        FindReleases(curArt, curRow, printArtist)

#------------------V  Изменил с 2 на 1
        time.sleep(1) # обход блокировки

pd.set_option('display.max_rows', 10)

print(f'{'':55}')

if TOKEN == '' or CHAT_ID == '':
    print('Message not sent! No TOKEN or CHAT_ID')
else:
    if checkMesSnd == len(message2send):
        message2send += '\n' + emojis['wtf']

    if checkMesErr != len(messageError) or checkMesEmp != len(messageEmpty) or checkMesBad != len(messageBadID):
        message2send += '\n\n' + messageErPrt
        if checkMesBad != len(messageBadID):
            message2send += '\n\n' + messageBadID
        if checkMesErr != len(messageError):
            message2send += '\n\n' + messageError
        if checkMesEmp != len(messageEmpty):
            message2send += '\n\n' + messageEmpty
    
    send_message('New Updates', message2send)

print('[V] All Done!')
logger(f'[{SCRIPT_NAME}]', '[V] Done!')
