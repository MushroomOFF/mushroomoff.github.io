ver = "v.2.024 [Local]"

import pandas as pd
import datetime
from pandasql import sqldf

# Переменные ----------------------------------
rootFolder = '/Users/viktorgribov/GitHub/mushroomoff.github.io/'
dbFolder = 'Databases/'
releasesDB = rootFolder + dbFolder + 'AMR_releases_DB.csv'
pdiTunesDB = pd.read_csv(releasesDB, sep=";")
where_block = ""
# ---------------------------------------------

# Функции -------------------------------------
def ShowReleases(dateFrom,dateTo):
    """Функция поиска релизов в БД
    dateFrom:          0             -> no condition           
                       "2022-01-01"  -> AND "releaseDate" > {dateFrom}
                       "2022-01-01+" -> AND "releaseDate" >= {dateFrom}
    dateTo:            0             -> no condition           
                       "2022-01-01"  -> AND "releaseDate" < {dateTo}
                       "2022-01-01+" -> AND "releaseDate" <= {dateTo}
    """
    whereBlock = ''
    
    if len(dateFrom) == 10: whereBlock += ' AND SUBSTRING("releaseDate",1,10) > "'+dateFrom+'"'
    elif len(dateFrom) == 11: whereBlock += ' AND SUBSTRING("releaseDate",1,10) >= "'+dateFrom[:10]+'"'
    
    if len(dateTo) == 10: whereBlock += ' AND SUBSTRING("releaseDate",1,10) < "'+dateTo+'"'
    elif len(dateTo) == 11: whereBlock += ' AND SUBSTRING("releaseDate",1,10) <= "'+dateTo[:10]+'"'
    
    selectSection = 'SELECT DISTINCT "mainArtist","artistName","collectionName",SUBSTRING("releaseDate",1,10) AS "releaseDate"'
    
    resultDF = sqldf(f'''{selectSection} FROM pdiTunesDB WHERE 1=1 {whereBlock} AND "downloadedRelease" is NULL ORDER BY "mainArtist" ASC, SUBSTRING("releaseDate",1,10) DESC, "collectionName" ASC''')
    return resultDF
# --------------------------------------------

print("###################################################################")
print("""     _                _        __  __           _                 
    / \\   _ __  _ __ | | ___  |  \\/  |_   _ ___(_) ___            
   / _ \\ | '_ \\| '_ \\| |/ _ \\ | |\\/| | | | / __| |/ __|           
  / ___ \\| |_) | |_) | |  __/ | |  | | |_| \\__ \\ | (__            
 /_/   \\_\\ .__/| .__/|_|\\___| |_|  |_|\\__,_|___/_|\\___|           
         |_|   |_|  _ \\ ___| | ___  __ _ ___  ___  ___            
                 | |_) / _ \\ |/ _ \\/ _` / __|/ _ \\/ __|           
                 |  _ <  __/ |  __/ (_| \\__ \\  __/\\__ \\           
  ____           |_| \\_\\___|_|\\___|\\__,_|___/\\___||___/ _     _   
 |  _ \\  _____      ___ __ | | ___   __ _  __| | | |   (_)___| |_ 
 | | | |/ _ \\ \\ /\\ / / '_ \\| |/ _ \\ / _` |/ _` | | |   | / __| __|
 | |_| | (_) \\ V  V /| | | | | (_) | (_| | (_| | | |___| \\__ \\ |_ 
 |____/ \\___/ \\_/\\_/ |_| |_|_|\\___/ \\__,_|\\__,_| |_____|_|___/\\__|
""")
print(" "+ver+"                                    ")
print(" (c)&(p) 2022-" + str(datetime.datetime.now())[0:4] + " by Viktor 'MushroomOFF' Gribov")
print("###################################################################")

print("")
print("Все релизы к скачиванию")
print("")
dt = datetime.datetime.today().strftime('%Y-%m-%d')
resDF = ShowReleases("",dt+"+")
print(resDF)

print("")
print("Предстоящие релизы")
print("")
dt = (datetime.datetime.now() + datetime.timedelta(days = 1)).strftime('%Y-%m-%d')
resDF = ShowReleases(dt+"+","")
print(resDF)