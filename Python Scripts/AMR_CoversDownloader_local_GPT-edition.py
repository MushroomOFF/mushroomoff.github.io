import os
import requests
import pandas as pd
import datetime

VERSION = "v.2.024 [Local]"

# Инициализация переменных
root_folder = '/Users/viktorgribov/GitHub/mushroomoff.github.io/'
db_folder = 'Databases/'
releases_db = os.path.join(root_folder, db_folder, 'AMR_releases_DB.csv')
user_data_folder = os.path.join(root_folder, 'Covers/Fresh Covers to Check/')

# Функции

def replace_symbols(text):
    """Замена неиспользуемых символов в имени файла и пути к папке."""
    symbols = '\\/*:?<>|`"\''
    for symbol in symbols:
        text = text.replace(symbol, '_')
    return text

def img_download(name, folder, link):
    """Загрузка изображения."""
    name = replace_symbols(name)
    folder = replace_symbols(folder)
    folder_path = os.path.join(user_data_folder, folder)

    os.makedirs(folder_path, exist_ok=True)
    
    response = requests.get(link)
    if response.status_code == 200:
        with open(os.path.join(folder_path, f"{name}.jpg"), "wb") as file:
            file.write(response.content)

# Основной код

session = requests.Session()
session.headers.update({
    'Referer': 'https://itunes.apple.com',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
})

print("###########################################################")
print("""
     _                _        __  __           _         
    / \   _ __  _ __ | | ___  |  \/  |_   _ ___(_) ___    
   / _ \ | '_ \| '_ \| |/ _ \ | |\/| | | | / __| |/ __|   
  / ___ \| |_) | |_) | |  __/ | |  | | |_| \__ \ | (__    
 /_/   \_\ .__/| .__/|_|\___| |_|  |_|\__,_|___/_|\___|   
         |_|   |_|  _ \ ___| | ___  __ _ ___  ___  ___    
                 | |_) / _ \ |/ _ \/ _` / __|/ _ \/ __|   
   ____          |  _ <  __/ |  __/ (_| \__ \  __/ (__    
  |_  /___ _ __  |_| \_\___|_|\___|\__,_|___/\___|\___|   
   / // _ \ '__| / __|/ _ \ '__| |/ / _ \| '_ ` _ \ / _ \  
  / /|  __/ |    \__ \  __/ |  |   < (_) | | | | | |  __/  
 /___\___|_|    |___/\___|_|  |_|\_\___/|_| |_| |_|\___|  
""")
print("###########################################################")
print("Script by Viktor 'CoffeOFF' Gribov")
print("###########################################################")
print('')

pd.set_option('display.max_rows', None)

while True:
    releases_df = pd.read_csv(releases_db, sep=";")
    
    if releases_df['artworkUrlD'].isna().all():
        print("\nВсё скачано, качать нечего...")
        break
    
    cover_to_download = releases_df[releases_df['downloadedCover'].isna()].head(1)
    if cover_to_download.empty:
        break
    
    row_index = cover_to_download.index[0]

    img_download(
        f"{cover_to_download['artistName'].loc[row_index]} - "
        f"{cover_to_download['collectionName'].loc[row_index][:100]} - "
        f"{cover_to_download['releaseDate'].loc[row_index]} [{row_index + 2}]",
        cover_to_download['mainArtist'].loc[row_index],
        cover_to_download['artworkUrlD'].loc[row_index]
    )
    
    print(f"ID: {row_index + 2}. {cover_to_download['mainArtist'].loc[row_index]} | "
          f"{cover_to_download['artistName'].loc[row_index]} - "
          f"{cover_to_download['collectionName'].loc[row_index]} - "
          f"{cover_to_download['releaseDate'].loc[row_index]}. "
          f"(Covers left: {releases_df['artworkUrlD'].isna().sum()})")
    
    releases_df.at[row_index, 'downloadedCover'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    releases_df.to_csv(releases_db, sep=';', index=False)

print("\n[V] All Done!")
