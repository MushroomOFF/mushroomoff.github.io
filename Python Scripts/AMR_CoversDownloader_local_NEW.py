import requests
import os
import pandas as pd
import datetime

VERSION = "v.2.024.12 [Local]"
# Python 3.12 & Pandas 2.2 ready

# Инициализация переменных
root_folder = '/Users/viktorgribov/GitHub/mushroomoff.github.io/'
db_folder = 'Databases/'
releases_db = os.path.join(root_folder, db_folder, 'AMR_releases_DB.csv')
user_data_folder = os.path.join(root_folder, 'Covers/Fresh Covers to Check/')

# Функции
def replace_symbols(text):
    """Замена неиспользуемых символов в имени файла и пути к папке"""
    symbols = '\\/*:?<>|`"'
    for symbol in symbols:
        text = text.replace(symbol,'_')
    return text

def image_download(name, folder, link):
    """Загрузка изображения"""
    name = replace_symbols(name)
    folder = replace_symbols(folder)
    folder_path = os.path.join(user_data_folder, folder)

    os.makedirs(folder_path, exist_ok=True)

    response = requests.get(link)
    if response.status_code == 200:
        with open(os.path.join(folder_path, f"{name}.jpg"), "wb") as file:
            file.write(response.content)
    
# Основой код main():
session = requests.Session() 
session.headers.update({
    'Referer': 'https://itunes.apple.com',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
})

print(f"""
###########################################################
     _                _        __  __           _         
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

 {VERSION}
 (c)&(p) 2022-{datetime.datetime.now().strftime("%Y")} by Viktor 'MushroomOFF' Gribov
###########################################################
""")

returner=''
while returner=='':
    pdiTunesDB = pd.read_csv(releases_db, sep=";")
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

        image_download(coverToDownload['artistName'].loc[curRow] + " - " + \
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
        pdiTunesDB.to_csv(releases_db, sep=';', index=False)        
        pdiTunesDB = pd.DataFrame()

print('')
print('[V] All Done!')
