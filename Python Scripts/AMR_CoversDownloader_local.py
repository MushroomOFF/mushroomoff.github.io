ver = "v.2.024 [Local]"
# Python 3.12 & Pandas 2.2 ready

import requests
import os
import pandas as pd
import datetime

# Инициализация переменных================================================

rootFolder = '/Users/viktorgribov/GitHub/mushroomoff.github.io/'
dbFolder = 'Databases/'
releasesDB = rootFolder + dbFolder + 'AMR_releases_DB.csv'
userDataFolder = rootFolder + 'Covers/Fresh Covers to Check/'

# Инициализация функций===================================================

## Замена неиспользуемых символов в имени файла и пути к папке
def ReplaceSymbols(rsTxt):
    rsTmplt = '\\/*:?<>|`"'
    for rsf in range(len(rsTmplt)):
        rsTxt=rsTxt.replace(rsTmplt[rsf],'_')
    return rsTxt

## Загрузка изображения
def ImgDownload(idName, idFolder, idLink):
    idName=ReplaceSymbols(idName)
    idFolder=ReplaceSymbols(idFolder)
    try:
        os.mkdir(userDataFolder+idFolder)
    except OSError:
        pass
    idImage = requests.get(idLink)
    out = open(userDataFolder+idFolder+"/"+idName+".jpg", "wb")
    out.write(idImage.content)
    out.close()
    
# ========================================================================

ses = requests.Session() 
ses.headers.update({'Referer': 'https://itunes.apple.com',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'})

print("###########################################################")
print("""     _                _        __  __           _         
    / \\   _ __  _ __ | | ___  |  \\/  |_   _ ___(_) ___    
   / _ \\ | '_ \\| '_ \\| |/ _ \\ | |\\/| | | | / __| |/ __|   
  / ___ \\| |_) | |_) | |  __/ | |  | | |_| \\__ \\ | (__    
 /_/   \\_\\ .__/| .__/|_|\\___| |_|  |_|\\__,_|___/_|\\___|   
         |_|   |_|  _ \\ ___| | ___  __ _ ___  ___  ___    
                 | |_) / _ \\ |/ _ \\/ _` / __|/ _ \\/ __|   
   ____          |  _ <  __/ |  __/ (_| \\__ \\  __/\\__ \\   
  / ___|_____   _|_|_\\_\\___|_|\\___|\\__,_|___/\\___||___/   
 | |   / _ \\ \\ / / _ \\ '__/ __|                           
 | |__| (_) \\ V /  __/ |  \\__ \\                           
  \\____\\___/ \\_/ \\___|_|  |___/               _           
 |  _ \\  _____      ___ __ | | ___   __ _  __| | ___ _ __ 
 | | | |/ _ \\ \\ /\\ / / '_ \\| |/ _ \\ / _` |/ _` |/ _ \\ '__|
 | |_| | (_) \\ V  V /| | | | | (_) | (_| | (_| |  __/ |   
 |____/ \\___/ \\_/\\_/ |_| |_|_|\\___/ \\__,_|\\__,_|\\___|_|   
""")
print(" "+ver+"                                    ")
print(" (c)&(p) 2022-" + str(datetime.datetime.now())[0:4] + " by Viktor 'MushroomOFF' Gribov")
print("###########################################################")
print('')

pd.set_option('display.max_rows', None)

returner=''
while returner=='':
    pdiTunesDB = pd.read_csv(releasesDB, sep=";")
    if len(pdiTunesDB['artworkUrlD'].loc[pdiTunesDB['downloadedCover'].isna()])==0:
        pdiTunesDB = pd.DataFrame()
        returner='x'
        print("")
        print("Всё скачано, качать нечего...")
    else:
        coverToDownload = pdiTunesDB.loc[pdiTunesDB['downloadedCover'].isna()].head(1)
        curRow = coverToDownload.index[0]
        # curRow -> позиция строки в таблице без учета шапки и с порядковым номером первой строки данных - 0
        # curRow + 2 -> позиция строки в текстовом файле с учетом шапки и порядковым номером первой строки данных - 2  
        # curRow + 2 -> только для вывода

        ImgDownload(coverToDownload['artistName'].loc[curRow] + " - " + \
                    coverToDownload['collectionName'].loc[curRow][:100] + " - " + \
                    coverToDownload['releaseDate'].loc[curRow] + " [" + \
                    str(curRow + 2) + "]", \
                    coverToDownload['mainArtist'].loc[curRow], \
                    coverToDownload['artworkUrlD'].loc[curRow])
        
        print("ID: " + str(curRow + 2) + ". " \
              + coverToDownload['mainArtist'].loc[curRow] + " | " \
              + coverToDownload['artistName'].loc[curRow] + " - " \
              + coverToDownload['collectionName'].loc[curRow] + " - " \
              + coverToDownload['releaseDate'].loc[curRow] \
              + ". (Covers left: " + str(len(pdiTunesDB['artworkUrlD'].loc[pdiTunesDB['downloadedCover'].isna()])) + ")")

        pdiTunesDB.iloc[curRow,17] = str(datetime.datetime.now())[0:19]
        pdiTunesDB.to_csv(releasesDB, sep=';', index=False)        
        pdiTunesDB = pd.DataFrame()

pd.set_option('display.max_rows', 10)

print('')
print('[V] All Done!')
