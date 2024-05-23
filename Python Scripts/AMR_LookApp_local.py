ver = "v.2.024.5 [Local]"
# Python 3.12 & Pandas 2.2 ready
# Added status sender via Telegram Bot

import requests
import os
import pandas as pd
import csv
import time
import json
import datetime
from math import nan

# Инициализация переменных================================================

userDataFolder = '/Users/viktorgribov/GitHub/mushroomoff.github.io/'
dbFolder = 'Databases/'
releasesDB = userDataFolder + dbFolder + 'AMR_releases_DB.csv'
artistIDs = userDataFolder + dbFolder + 'AMR_artisitIDs.csv'
fieldNames = ['mainArtist', 'mainId', 'artistName', 'artistId', 'primaryGenreName', 
              'collectionId', 'collectionName', 'collectionCensoredName', 'artworkUrl100', 
              'collectionExplicitness', 'trackCount', 'copyright', 'country', 'releaseDate', 'releaseYear', 
              'dateUpdate', 'artworkUrlD', 'downloadedCover', 'downloadedRelease', 'updReason']
#---------------------v  отрезал JP
lCountry = ['us', 'ru', 'jp']
emojis = {'us': '\U0001F1FA\U0001F1F8', 'ru': '\U0001F1F7\U0001F1FA', 'jp': '\U0001F1EF\U0001F1F5', 'wtf': '\U0001F914', 
          'album': '\U0001F4BF', 'cover': '\U0001F3DE\U0000FE0F', 'error': '\U00002757\U0000FE0F', 'empty': '\U0001F6AB'}
# Telegram -------------------------------
URL = 'https://api.telegram.org/bot'
TOKEN = input("Telegram Bot TOKEN: ")
chat_id = input("Telegram Bot chat_id: ")
#chat_id = '-1001939128351' #Test channel
#-----------------------------------------

# establishing session
ses = requests.Session() 
ses.headers.update({'Referer': 'https://itunes.apple.com', 
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'})

# Инициализация функций===================================================

# Процедура Замены символов для Markdown v2
def ReplaceSymbols(rsTxt):
    rsTmplt = """'_*[]",()~`>#+-=|{}.!"""
    for rsf in range(len(rsTmplt)):
        rsTxt = rsTxt.replace(rsTmplt[rsf], '\\' + rsTmplt[rsf])
    return rsTxt

# Процедура Отправки сообщения ботом в канал
def send_message(text):
    method = URL + TOKEN + "/sendMessage"
    r = requests.post(method, data={"chat_id": chat_id, "parse_mode": 'MarkdownV2', "text": text})
    json_response = json.loads(r.text)
    rmi = json_response['result']['message_id']   
    return rmi

# Процедура Загрузки библиотеки
def CreateDB():
    if not os.path.exists(releasesDB):
        with open(releasesDB, 'a+', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldNames)
            writer.writeheader()
        print('[V] Database created')
    else:
        print('[V] Database exists')
    print('')

# Процедура Поиска релизов исполнителя в базе iTunes  
def FindReleases(artistID, cRow):
    global message2send, messageEmpty, messageError
    allDataFrame = pd.DataFrame()
    dfExport = pd.DataFrame()
    check_ers = 0
    for country in lCountry:
        url = 'https://itunes.apple.com/lookup?id=' + str(artistID) + '&country=' + country + '&entity=album&limit=200'
        request = ses.get(url)
        if request.status_code == 200:     
            dJSON = json.loads(request.text)
            if dJSON['resultCount']>1:
                dfTemp = pd.DataFrame(dJSON['results'])
                allDataFrame = pd.concat([allDataFrame, dfTemp[['artistName', 'artistId', 'primaryGenreName', 'collectionId', 'collectionName', 'collectionCensoredName', 'artworkUrl100', 'collectionExplicitness', 'trackCount', 'copyright', 'country', 'releaseDate']]], ignore_index=True)
            else:
                if check_ers == 0:
                    print('\n', end='')
                print(' ' + country + ' - EMPTY |', sep=' ', end='', flush=True)
                messageEmpty += '\n' + emojis[country] + ' *' + ReplaceSymbols(artistPrintName.replace('&amp;','and')) + '*'
                check_ers = 1
        else:
            if check_ers == 0:
                print('\n', end='')
            print(' ' + country + ' - ERROR (' + str(request.status_code) + ') |', sep=' ', end='', flush=True)
            messageError += '\n' + emojis[country] + ' *' + ReplaceSymbols(artistPrintName.replace('&amp;','and')) + '*'
            check_ers = 1
        time.sleep(1) # обход блокировки
    allDataFrame.drop_duplicates(subset='artworkUrl100', keep='first', inplace=True, ignore_index=True)
    dfExport = allDataFrame.loc[allDataFrame['collectionName'].notna()]
    if check_ers == 1:
        print ('') 

    if len(dfExport) > 0:
        pdiTunesDB = pd.read_csv(releasesDB, sep=";")
        #Открываем файл лога для проверки скаченных файлов и записи новых скачиваний
        csvfile = open(releasesDB, 'a+', newline='')
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldNames)

        dateUpdate = str(datetime.datetime.now())[0:19]
        mainArtist = allDataFrame['artistName'].loc[0]
        mainId = artistID
        updReason = ''
        newRelCounter = 0
        newCovCounter = 0
        #Cкачиваем обложки
        for index, row in dfExport.iterrows():
            artistName = row.iloc[0]
            artistId = row.iloc[1]
            primaryGenreName = row.iloc[2]
            collectionId = row.iloc[3]
            collectionName = row.iloc[4]
            collectionCensoredName = row.iloc[5]
            artworkUrl100 = row.iloc[6]
            collectionExplicitness = row.iloc[7]
            trackCount = row.iloc[8]
            copyright = row.iloc[9]
            country = row.iloc[10]
            releaseDate = row.iloc[11][:10]
            releaseYear = row.iloc[11][:4]
            artworkUrlD = row.iloc[6].replace('100x100bb', '100000x100000-999')
            downloadedCover = ''
            downloadedRelease = ''
            updReason = ''
            if len(pdiTunesDB.loc[pdiTunesDB['collectionId']  == dfExport.iloc[index-1]['collectionId']])  == 0:
                updReason = 'New release'
                newRelCounter += 1
            elif len(pdiTunesDB[pdiTunesDB['artworkUrl100'].str[40:] == dfExport.iloc[index-1]['artworkUrl100'][40:]]) == 0:
                updReason = 'New cover'
                newCovCounter += 1
                #.str[40] -------------------------------V
                #https://is2-ssl.mzstatic.com/image/thumb/Music/v4/b2/cc/64/b2cc645c-9f18-db02-d0ab-69e296ea4d70/source/100x100bb.jpg

            #Это проверка - нужно ли сверяться с логом
            if updReason != '':
                writer.writerow({'mainArtist': mainArtist, 'mainId': mainId, 'artistName': artistName,  
                                 'artistId': artistId,  'primaryGenreName': primaryGenreName,  
                                 'collectionId': collectionId,  'collectionName': collectionName,  
                                 'collectionCensoredName': collectionCensoredName,  'artworkUrl100': artworkUrl100,  
                                 'collectionExplicitness': collectionExplicitness,  'trackCount': trackCount,  
                                 'copyright': copyright,  'country': country,  'releaseDate': releaseDate,  
                                 'releaseYear': releaseYear,  'dateUpdate': dateUpdate[:10],  
                                 'artworkUrlD': artworkUrlD,  'downloadedCover': downloadedCover,  
                                 'downloadedRelease': downloadedRelease,  'updReason': updReason})

        csvfile.close()

        artistIDlist.iloc[cRow, 2] = dateUpdate
        artistIDlist.to_csv(artistIDs, sep=';', index=False)

        pdiTunesDB = pd.DataFrame() 
        if (newRelCounter + newCovCounter) > 0:
            print('\n^ '+str(newRelCounter+newCovCounter)+' new records: '+str(newRelCounter)+' releases, '+str(newCovCounter)+' covers')
            if newRelCounter > 0 :
                iconka = 'album'
            else:
                iconka = 'cover'
            message2send += '\n' + emojis[iconka] + ' *' + ReplaceSymbols(artistPrintName.replace('&amp;','and')) + '*: ' + str(newRelCounter + newCovCounter)
        return "v" 
    
    else:
        print("Didn't find a thing!")
        print("")
        return "x"
# Инициализация функций===================================================

print("########################################################")
print("""     _                _        __  __           _      
    / \\   _ __  _ __ | | ___  |  \\/  |_   _ ___(_) ___ 
   / _ \\ | '_ \\| '_ \\| |/ _ \\ | |\\/| | | | / __| |/ __|
  / ___ \\| |_) | |_) | |  __/ | |  | | |_| \\__ \\ | (__ 
 /_/   \\_\\ .__/| .__/|_|\\___| |_|  |_|\\__,_|___/_|\\___|
         |_|   |_|  _ \\ ___| | ___  __ _ ___  ___  ___ 
                 | |_) / _ \\ |/ _ \\/ _` / __|/ _ \\/ __|
                 |  _ <  __/ |  __/ (_| \\__ \\  __/\\__ \\\\
  _              |_| \\_\\___|_|\\___|\\__,_|___/\\___||___/
 | |    ___   ___ | | __   / \\   _ __  _ __            
 | |   / _ \\ / _ \\| |/ /  / _ \\ | '_ \\| '_ \\           
 | |__| (_) | (_) |   <  / ___ \\| |_) | |_) |          
 |_____\\___/ \\___/|_|\\_\\/_/   \\_\\ .__/| .__/           
                                |_|   |_|              
""")
print(" " + ver + "                                    ")
print(" (c)&(p) 2022-" + str(datetime.datetime.now())[0:4] + " by Viktor 'MushroomOFF' Gribov")
print("########################################################")
print('')

message2send = ReplaceSymbols('====== ' + str(datetime.datetime.now())[:10] + ' ======')
messageErPrt = ReplaceSymbols('======== ERRORS ========') + '\n'
messageError = emojis['error'] + ' 503 Service Unavailable ' + emojis['error']
messageEmpty = emojis['empty'] + ' Not available in country ' + emojis['empty']
checkMesSnd = len(message2send)
checkMesErr = len(messageError)
checkMesEmp = len(messageEmpty)

CreateDB()

pd.set_option('display.max_rows', None)

# Определяем на каком Артисте остановились в прошлый раз. При желании начинаем сначала
starter = 0
while starter == 0:
    artistIDlist = pd.read_csv(artistIDs, sep=';')
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
        artistIDlist.to_csv(artistIDs, sep=';', index=False)
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
            artistIDlist.to_csv(artistIDs, sep=';', index=False)

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
        print(f'{printArtist:50}', end='\r')

        findMark = FindReleases(curArt, curRow)

#------------------V  Изменил с 2 на 1
        time.sleep(1) # обход блокировки

pd.set_option('display.max_rows', 10)

fspace = ' '
print(f'{fspace:50}')

if checkMesSnd == len(message2send):
    message2send += '\n' + emojis['wtf']

if checkMesErr == len(messageError) and checkMesEmp == len(messageEmpty):
    send_message(message2send)
elif checkMesErr != len(messageError) and checkMesEmp != len(messageEmpty):
    send_message(message2send + '\n\n' + messageErPrt + messageError + '\n\n' + messageEmpty)    
else:
    if checkMesEmp != len(messageEmpty):
        send_message(message2send + '\n\n' + messageErPrt + messageEmpty)
    elif checkMesErr != len(messageError):
        send_message(message2send + '\n\n' + messageErPrt + messageError)
    else:
        send_message(message2send + '\n\n' + messageErPrt + '\n' + emojis['wtf'])

print('[V] All Done!')
