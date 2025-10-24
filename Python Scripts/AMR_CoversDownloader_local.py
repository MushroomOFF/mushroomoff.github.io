import datetime
import os
import pandas as pd
import requests

# CONSTANTS
SCRIPT_NAME = "Covers Downloader"
VERSION = "v.2.025.10 [Local]"

ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
DB_FOLDER = 'Databases/'
COVERS_FOLDER = os.path.join(ROOT_FOLDER, 'Covers/Fresh Covers to Check/')
RELEASES_DB = os.path.join(ROOT_FOLDER, DB_FOLDER, 'AMR_releases_DB.csv')
LOG_FILE = os.path.join(ROOT_FOLDER, 'status.log')

# functions
def replace_symbols(text_line):
    """Replacing unused characters 
    in file names and folder paths
    """
    symbols_to_replace = '\\/*:?<>|`"'
    for symbol in symbols_to_replace:
        text_line = text_line.replace(symbol, '_')
    return text_line

def image_download(file_name, folder, link):
    """Image downloading"""
    file_name = replace_symbols(file_name)
    folder = replace_symbols(folder)
    folder_path = os.path.join(COVERS_FOLDER, folder)

    os.makedirs(folder_path, exist_ok=True)

    response = requests.get(link)
    if response.status_code == 200:
        with open(os.path.join(folder_path, f"{file_name}.jpg"), "wb") as file:
            file.write(response.content)

def main():
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

    while True:
        releases_df = pd.read_csv(RELEASES_DB, sep=";")
        
        cover_to_download = releases_df[releases_df['downloadedCover'].isna()].head(1)
        if cover_to_download.empty:
            print("\nВсё скачано, качать нечего...")
            break
        
        row_index = cover_to_download.index[0]
        # row_index -> позиция строки в таблице без учета шапки и с порядковым номером первой строки данных - 0
        # row_index + 2 -> позиция строки в текстовом файле с учетом шапки и порядковым номером первой строки данных - 2  
        # row_index + 2 -> только для вывода    

        image_download(
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
              f"(Covers left: {releases_df['downloadedCover'].isna().sum() - 1})")
        
        releases_df.at[row_index, 'downloadedCover'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        releases_df.to_csv(RELEASES_DB, sep=';', index=False)

    print("\n[V] All Done!")

if __name__ == "__main__":
    main()