ver = "v.2.024.8 [GitHub]"
# Python 3.12 & Pandas 2.2 ready
# Added status sender via Telegram Bot
# Add ID to log
# comment will mark the specific code for GitHub
# GitHub version will always run complete list of artists

import requests
import os
import pandas as pd
import csv
import time
import json
import datetime
from math import nan

# Инициализация переменных================================================

userDataFolder = '' # root is root
dbFolder = 'Databases/'
releasesDB = userDataFolder + dbFolder + 'AMR_releases_DB.csv'
artistIDDB = userDataFolder + dbFolder + 'AMR_artisitIDs.csv'
fieldNames = ['mainArtist', 'mainId', 'artistName', 'artistId', 'primaryGenreName', 
              'collectionId', 'collectionName', 'collectionCensoredName', 'artworkUrl100', 
              'collectionExplicitness', 'trackCount', 'copyright', 'country', 'releaseDate', 'releaseYear', 
              'dateUpdate', 'artworkUrlD', 'downloadedCover', 'downloadedRelease', 'updReason']
#---------------------v  отрезал JP
lCountry = ['us', 'ru'] #, 'jp']
emojis = {'us': '\U0001F1FA\U0001F1F8', 'ru': '\U0001F1F7\U0001F1FA', 'jp': '\U0001F1EF\U0001F1F5', 'no': '\U0001F3F3\U0000FE0F', 'wtf': '\U0001F914', 
          'album': '\U0001F4BF', 'cover': '\U0001F3DE\U0000FE0F', 'error': '\U00002757\U0000FE0F', 'empty': '\U0001F6AB', 'badid': '\U0000274C'}
logFile = userDataFolder + 'status.log' # path to log file
# Telegram -------------------------------
URL = 'https://api.telegram.org/bot'
TOKEN = os.environ['tg_token']
CHAT_ID = os.environ['tg_channel_id']
#-----------------------------------------

# establishing session
ses = requests.Session() 
ses.headers.update({'Referer': 'https://itunes.apple.com', 
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'})

# Инициализация функций===================================================

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

# Процедура Отправки сообщения ботом в канал
def send_message(text):
    method = URL + TOKEN + "/sendMessage"
    r = requests.post(method, data={"chat_id": CHAT_ID, "parse_mode": 'MarkdownV2', "text": text})
    json_response = json.loads(r.text)
    rmi = json_response['result']['message_id']   
    return rmi

# Процедура Загрузки библиотеки
def CreateDB():
    if not os.path.exists(releasesDB):
        with open(releasesDB, 'a+', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldNames)
            writer.writeheader()

# Процедура Поиска релизов исполнителя в базе iTunes  
def FindReleases(artistID, cRow, artistPrintName):
    global message2send, messageEmpty, messageError, messageBadID
    allDataFrame = pd.DataFrame()
    dfExport = pd.DataFrame()
    for country in lCountry:
        url = 'https://itunes.apple.com/lookup?id=' + str(artistID) + '&country=' + country + '&entity=album&limit=200'
        request = ses.get(url)
        if request.status_code == 200:     
            dJSON = json.loads(request.text)
            if dJSON['resultCount']>1:
                dfTemp = pd.DataFrame(dJSON['results'])
                allDataFrame = pd.concat([allDataFrame, dfTemp[['artistName', 'artistId', 'primaryGenreName', 'collectionId', 'collectionName', 'collectionCensoredName', 'artworkUrl100', 'collectionExplicitness', 'trackCount', 'copyright', 'country', 'releaseDate']]], ignore_index=True)
            else:
                amnr_logger('[Apple Music Releases LookApp]', artistPrintName + ' - ' + str(artistID) + ' - ' + country + ' - EMPTY')
                messageEmpty += '\n' + emojis[country] + ' *' + ReplaceSymbols(artistPrintName.replace('&amp;','and')) + '*'
        else:
            amnr_logger('[Apple Music Releases LookApp]', artistPrintName + ' - ' + str(artistID) + ' - ' + country + ' - ERROR (' + str(request.status_code) + ')')
            messageError += '\n' + emojis[country] + ' *' + ReplaceSymbols(artistPrintName.replace('&amp;','and')) + '*'
        time.sleep(1) # обход блокировки
    allDataFrame.drop_duplicates(subset='artworkUrl100', keep='first', inplace=True, ignore_index=True)
    if len(allDataFrame) > 0:
        dfExport = allDataFrame.loc[allDataFrame['collectionName'].notna()]
    else:
        amnr_logger('[Apple Music Releases LookApp]', artistPrintName + ' - ' + str(artistID) + ' - Bad ID')
        messageBadID += '\n' + emojis['no'] + ' *' + ReplaceSymbols(artistPrintName.replace('&amp;','and')) + '*'

    if len(dfExport) > 0:
        pdiTunesDB = pd.read_csv(releasesDB, sep=";")
        #Открываем файл лога для проверки скаченных файлов и записи новых скачиваний
        csvfile = open(releasesDB, 'a+', newline='')
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldNames)

        dateUpdate = str(datetime.datetime.now() + datetime.timedelta(hours=3))[0:19] # GitHub server time is UTC (-3 from Moscow), so i add +3 hours to log actions in Moscow time. Only where time matters
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
            if len(pdiTunesDB.loc[pdiTunesDB['collectionId']  == dfExport.iloc[index - 1]['collectionId']])  == 0:
                updReason = 'New release'
                newRelCounter += 1
            elif len(pdiTunesDB[pdiTunesDB['artworkUrl100'].str[40:] == dfExport.iloc[index - 1]['artworkUrl100'][40:]]) == 0:
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
        artistIDlist.to_csv(artistIDDB, sep=';', index=False)

        pdiTunesDB = pd.DataFrame() 
        if (newRelCounter + newCovCounter) > 0:
            amnr_logger('[Apple Music Releases LookApp]', 
                        artistPrintName + ' - ' + str(artistID) + ' - ' + str(newRelCounter + newCovCounter) + ' new records: ' + str(newRelCounter) + ' releases, ' + str(newCovCounter) + ' covers')
            if newRelCounter > 0 :
                iconka = 'album'
            else:
                iconka = 'cover'
            message2send += '\n' + emojis[iconka] + ' *' + ReplaceSymbols(artistPrintName.replace('&amp;','and')) + '*: ' + str(newRelCounter + newCovCounter)
    
    else:
        artistIDlist.iloc[cRow, 2] = str(datetime.datetime.now() + datetime.timedelta(hours=3))[0:19] # GitHub server time is UTC (-3 from Moscow), so i add +3 hours to log actions in Moscow time. Only where time matters
        artistIDlist.to_csv(artistIDDB, sep=';', index=False)
# Инициализация функций===================================================

amnr_logger('[Apple Music Releases LookApp]', ver + " (c)&(p) 2022-" + str(datetime.datetime.now())[0:4] + " by Viktor 'MushroomOFF' Gribov")
message2send = ReplaceSymbols('====== ' + str(datetime.datetime.now())[:10] + ' ======')
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

artistIDlist = pd.read_csv(artistIDDB, sep=';')
artistIDlist.drop('downloaded', axis=1, inplace=True)
artistIDlist.insert(2, "downloaded", nan)
artistIDlist.to_csv(artistIDDB, sep=';', index=False)

returner = ''
while returner == '':
    artID = artistIDlist['mainId'].loc[artistIDlist['downloaded'].isna()].head(1)
    if len(artID) == 0:
        returner = 'x'
    else:
        curRow = artID.index[0]
        artID.reset_index(drop=True, inplace=True)
        curArt = artID[0]

        printArtID = artistIDlist['mainArtist'].loc[artistIDlist['downloaded'].isna()].head(1)
        printArtID.reset_index(drop=True, inplace=True)
        printArtist = printArtID[0]
        print(f'{(printArtist + ' - ' + str(curArt)):50}', end='\r')

        FindReleases(curArt, curRow, printArtist)

#------------------V  Изменил с 2 на 1
        time.sleep(1.5) # обход блокировки

pd.set_option('display.max_rows', 10)
print(f'{'':50}')

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

send_message(message2send)

amnr_logger('[Apple Music Releases LookApp]', '[V] Done!')
