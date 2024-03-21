ver = "v.2.024 [GitHub]"
# comment will mark the specific code for GitHub
# GitHub version will always run complete list of artists

import requests
import os
import pandas as pd
import csv
import time
import json
import datetime
import math
from math import nan

# Инициализация переменных================================================

userDataFolder = '' # root is root
dbFolder = 'Databases/'
releasesDB = userDataFolder + dbFolder + 'AMR_releases_DB.csv'
artistIDs = userDataFolder + dbFolder + 'AMR_artisitIDs.csv'
fieldNames = ['mainArtist','mainId','artistName','artistId','primaryGenreName',
              'collectionId','collectionName','collectionCensoredName','artworkUrl100',
              'collectionExplicitness','trackCount','copyright','country','releaseDate','releaseYear',
              'dateUpdate','artworkUrlD','downloadedCover','downloadedRelease','updReason']
#--------------------v  отрезал JP
lCountry = ['us','ru','jp']
logFile = userDataFolder + 'status.log' # path to log file

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

# Процедура Загрузки библиотеки
def CreateDB():
    if not os.path.exists(releasesDB):
        with open(releasesDB, 'a+', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldNames)
            writer.writeheader()

# Процедура Поиска релизов исполнителя в базе iTunes  
def FindReleases(artistID, cRow, artistPrintName):
    allDataFrame=pd.DataFrame()
    dfExport=pd.DataFrame()
    for country in lCountry:
        url = 'https://itunes.apple.com/lookup?id='+str(artistID)+'&country='+country+'&entity=album&limit=200'
        request = ses.get(url)
        if request.status_code == 200:     
            dJSON = json.loads(request.text)
            if dJSON['resultCount']>1:
                dfTemp = pd.DataFrame(dJSON['results'])
                allDataFrame=allDataFrame.append(dfTemp[['artistName','artistId','primaryGenreName','collectionId','collectionName','collectionCensoredName','artworkUrl100','collectionExplicitness','trackCount','copyright','country','releaseDate']],ignore_index=True)
            else:
                amnr_logger('[Apple Music Releases LookApp]', artistPrintName + ' - ' + country + ' - EMPTY')
        else:
            amnr_logger('[Apple Music Releases LookApp]', artistPrintName + ' - ' + country + ' - ERROR (' + str(request.status_code) + ')')
        time.sleep(1) # обход блокировки
    allDataFrame.drop_duplicates(subset='artworkUrl100', keep='first', inplace=True, ignore_index=True)
    dfExport = allDataFrame.loc[allDataFrame['collectionName'].notna()]

    if len(dfExport)>0:        
        pdiTunesDB = pd.read_csv(releasesDB, sep=";")

        csvfile = open(releasesDB, 'a+', newline='')
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldNames)

        dateUpdate=str(datetime.datetime.now() + datetime.timedelta(hours=3))[0:19] # GitHub server time is UTC (-3 from Moscow), so i add +3 hours to log actions in Moscow time. Only where time matters
        mainArtist=allDataFrame['artistName'].loc[0]
        mainId=artistID
        updReason=''
        newRelCounter=0
        newCovCounter=0
        #Cкачиваем обложки
        for index, row in dfExport.iterrows():
            artistName=row[0]
            artistId=row[1]
            primaryGenreName=row[2]
            collectionId=row[3]
            collectionName=row[4]
            collectionCensoredName=row[5]
            artworkUrl100=row[6]
            collectionExplicitness=row[7]
            trackCount=row[8]
            copyright=row[9]
            country=row[10]
            releaseDate=row[11][:10]
            releaseYear=row[11][:4]
            artworkUrlD=row[6].replace('100x100bb','100000x100000-999')
            downloadedCover=''
            downloadedRelease=''
            updReason=''
            if len(pdiTunesDB.loc[pdiTunesDB['collectionId']  == dfExport.iloc[index-1]['collectionId']])  == 0:
                updReason='New release'
                newRelCounter+=1
            elif len(pdiTunesDB[pdiTunesDB['artworkUrl100'].str[40:] == dfExport.iloc[index-1]['artworkUrl100'][40:]]) == 0:
                updReason='New cover'
                newCovCounter+=1
                #.str[40] -------------------------------V
                #https://is2-ssl.mzstatic.com/image/thumb/Music/v4/b2/cc/64/b2cc645c-9f18-db02-d0ab-69e296ea4d70/source/100x100bb.jpg

            #Это проверка - нужно ли сверяться с логом
            if updReason != '':
                writer.writerow({'mainArtist': mainArtist,'mainId': mainId,'artistName': artistName, 
                                 'artistId': artistId, 'primaryGenreName': primaryGenreName, 
                                 'collectionId': collectionId, 'collectionName': collectionName, 
                                 'collectionCensoredName': collectionCensoredName, 'artworkUrl100': artworkUrl100, 
                                 'collectionExplicitness': collectionExplicitness, 'trackCount': trackCount, 
                                 'copyright': copyright, 'country': country, 'releaseDate': releaseDate, 
                                 'releaseYear': releaseYear, 'dateUpdate': dateUpdate[:10], 
                                 'artworkUrlD': artworkUrlD, 'downloadedCover': downloadedCover, 
                                 'downloadedRelease': downloadedRelease, 'updReason': updReason})

        csvfile.close()

        artistIDlist.iloc[cRow,2] = dateUpdate
        artistIDlist.to_csv(artistIDs, sep=';', index=False)

        pdiTunesDB = pd.DataFrame() 
        if (newRelCounter + newCovCounter) > 0:
            amnr_logger('[Apple Music Releases LookApp]', 
                        artistPrintName + ' - ' + str(newRelCounter + newCovCounter) + ' new records: ' + str(newRelCounter) + ' releases, ' + str(newCovCounter) + ' covers')
        return "v" 
    
    else:
        amnr_logger('[Apple Music Releases LookApp]', "[!] Didn't find " + artistPrintName + "on ID " + artistID) 
        return "x"
# Инициализация функций===================================================

amnr_logger('[Apple Music Releases LookApp]', ver + " (c)&(p) 2022-" + str(datetime.datetime.now())[0:4] + " by Viktor 'MushroomOFF' Gribov")

CreateDB()

pd.set_option('display.max_rows', None)

artistIDlist = pd.read_csv(artistIDs, sep=';')
artistIDlist.drop('downloaded', axis=1, inplace=True)
artistIDlist.insert(2, "downloaded", nan)
artistIDlist.to_csv(artistIDs, sep=';', index=False)

returner=''
while returner=='':
    artID = artistIDlist['mainId'].loc[artistIDlist['downloaded'].isna()].head(1)
    if len(artID) == 0:
        returner='x'
    else:
        curRow = artID.index[0]
        artID.reset_index(drop=True,inplace=True)
        curArt= artID[0]

        printArtID = artistIDlist['mainArtist'].loc[artistIDlist['downloaded'].isna()].head(1)
        printArtID.reset_index(drop=True,inplace=True)
        printArtist = printArtID[0]
        print(f'{printArtist:50}', end='\r')

        findMark=FindReleases(curArt, curRow, printArtist)

#------------------V  Изменил с 2 на 1
        time.sleep(1) # обход блокировки

pd.set_option('display.max_rows', 10)
fspace=' '
print(f'{fspace:50}')

amnr_logger('[Apple Music Releases LookApp]', '[V] Done!')
