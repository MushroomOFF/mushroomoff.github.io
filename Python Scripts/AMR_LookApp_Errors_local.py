import requests
import os
import pandas as pd
import csv
import time
import datetime

SCRIPT_NAME = "Apple Music Releases LookApp Errors"
VERSION = "v.2.024.8 [Local]"

# Инициализация переменных
root_folder = '/Users/viktorgribov/GitHub/mushroomoff.github.io'
db_folder = 'Databases'
releases_db = os.path.join(root_folder, db_folder, 'AMR_releases_DB.csv')
artist_id_db = os.path.join(root_folder, db_folder, 'AMR_artisitIDs.csv')
log_file = os.path.join(root_folder, 'status.log')
field_names = ['mainArtist', 'mainId', 'artistName', 'artistId', 'primaryGenreName', 
               'collectionId', 'collectionName', 'collectionCensoredName', 'artworkUrl100',
               'collectionExplicitness', 'trackCount', 'copyright', 'country', 
               'releaseDate', 'releaseYear', 'dateUpdate', 'artworkUrlD', 'downloadedCover', 
               'downloadedRelease', 'updReason']
session = requests.Session() 
session.headers.update({
    'Referer': 'https://itunes.apple.com',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
})
key_logger = ''

# Функции
def logger(script_name, log_line):
    """Запись лога в файл."""
    with open(log_file, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(str(datetime.datetime.now()) + ' - ' + script_name + ' - ' + log_line.rstrip('\r\n') + '\n' + content)

def find_errors(log_file):
    """Поиск в логе ошибок последнего запуска Apple Music Releases LookApp через GitHub Actions."""
    with open(log_file, 'r') as lf:
        log_lines = lf.readlines()

    # Ищем индексы первой и последней записи свежей отработки Apple Music Releases LookApp
    start_idx = next((i for i, line in enumerate(log_lines) 
                      if '[Apple Music Releases LookApp] - [V] Done!' in line), None)

    end_idx = next((i for i, line in enumerate(log_lines) 
                    if '[Apple Music Releases LookApp] - v.' in line), None)
    
    if start_idx is None or end_idx is None or start_idx >= end_idx:
        print("При последнем запуске Apple Music Releases LookApp ошибок не возникало.")
        return []

    # Собираем группы и страны, которые необходимо повторно проверить
    error_list = [
        line.split(' - ')[2:5] # режем строку лога и берём 2, 3 и 4 куски
        for line in log_lines[start_idx:end_idx] # смотрим только строки между начальным и конечным индексами
        if line.endswith('ERROR (503)\n') # берём только строки, где есть ошибка 503
    ]

    print(f'Найдено ошибок: {len(error_list)}')
    return error_list

def find_releases(artist_id, country, artist_print_name):
    """
    Собирает релизы определенных Исполнителей в конкретных Странах из базы iTunes.

    :param artist_id: ID Исполнителя для поиска.
    :param country: Текстовый код страны для поиска.
    :param artist_print_name: Название Исполнителя для отображения и логирования.
    """
    all_data = pd.DataFrame()
    df_export = pd.DataFrame()
    # errors_found = False

    url = f'https://itunes.apple.com/lookup?id={artist_id}&country={country}&entity=album&limit=200'
    response = session.get(url)

    if response.status_code == 200:
        data = response.json()
        if data['resultCount'] > 1:
            df_temp = pd.DataFrame(data['results'])
            all_data = pd.concat([all_data, df_temp[[
                'artistName', 'artistId', 'primaryGenreName', 'collectionId', 'collectionName',
                'collectionCensoredName', 'artworkUrl100', 'collectionExplicitness', 'trackCount',
                'copyright', 'country', 'releaseDate'
            ]]], ignore_index=True)
        else:
            print(f'\n {country} - EMPTY |', end='', flush=True)
            logger(f'[{SCRIPT_NAME}]', f'{artist_print_name} - {artist_id} - {country} - EMPTY')
            # errors_found = True
    else:
        print(f'\n {country} - ERROR ({response.status_code}) |', end='', flush=True)
        logger(f'[{SCRIPT_NAME}]', f'{artist_print_name} - {artist_id} - {country} - ERROR ({response.status_code})')
        # errors_found = True

    # Пауза для обхода блокировки сервера iTunes
    time.sleep(1)

    # Убираем дубликаты по ссылке на обложку 'artworkUrl100'
    all_data.drop_duplicates(subset='artworkUrl100', keep='first', inplace=True, ignore_index=True)

#     # Отбираем для сохранения записи с заполненным 'collectionName'
    if not all_data.empty:
        df_export = all_data.loc[all_data['collectionName'].notna()]
#     else:
#         print(f'\n Bad ID: {artist_id}', end='', flush=True)
#         logger(f'[{SCRIPT_NAME}]', f'{artist_print_name} - {artist_id} - Bad ID')
#         errors_found = True
    
#     # ! ПРОВЕРЬ нужно ли это?
#     if errors_found:
#         print('')

    if not df_export.empty:
        pdi_tunes_db = pd.read_csv(releases_db, sep=";")

        with open(releases_db, 'a+', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=field_names)

            date_update = datetime.datetime.now().strftime('%Y-%m-%d')
            new_rel_counter = 0
            new_cov_counter = 0

            for _, row in df_export.iterrows():
                collection_id = row['collectionId']
                artwork_url = row['artworkUrl100']
                artwork_url_d = artwork_url.replace('100x100bb', '100000x100000-999')

                if pdi_tunes_db[pdi_tunes_db['collectionId'] == collection_id].empty:
                    upd_reason = 'New release'
                    new_rel_counter += 1
                elif pdi_tunes_db[pdi_tunes_db['artworkUrl100'].str[40:] == artwork_url[40:]].empty:
                    # .str[40:] ------------------------------V проверка ссылок на совпадение пойдет отсюда, т.к. одиннаковые обложки могут лежать на разных серверах
                    # https://is2-ssl.mzstatic.com/image/thumb/Music/v4/b2/cc/64/b2cc645c-9f18-db02-d0ab-69e296ea4d70/source/100x100bb.jpg            
                    upd_reason = 'New cover'
                    new_cov_counter += 1
                else:
                    continue

                writer.writerow({
                    'mainArtist': artist_print_name, 'mainId': artist_id, 'artistName': row['artistName'],
                    'artistId': row['artistId'], 'primaryGenreName': row['primaryGenreName'],
                    'collectionId': collection_id, 'collectionName': row['collectionName'],
                    'collectionCensoredName': row['collectionCensoredName'], 'artworkUrl100': artwork_url,
                    'collectionExplicitness': row['collectionExplicitness'], 'trackCount': row['trackCount'],
                    'copyright': row['copyright'], 'country': row['country'],
                    'releaseDate': row['releaseDate'][:10], 'releaseYear': row['releaseDate'][:4],
                    'dateUpdate': date_update, 'artworkUrlD': artwork_url_d,
                    'downloadedCover': '', 'downloadedRelease': '', 'updReason': upd_reason
                })

        del pdi_tunes_db
        
        if new_rel_counter + new_cov_counter > 0:
            print(f'\n^ {new_rel_counter + new_cov_counter} new records: {new_rel_counter} releases, {new_cov_counter} covers')
            logger(f'[{SCRIPT_NAME}]', f'{artist_print_name} - {artist_id} - {country} - {new_rel_counter + new_cov_counter} new records: {new_rel_counter} releases, {new_cov_counter} covers')

# Основной код
print("########################################################")
print("""     _    __  __ ____                        
    / \\  |  \\/  |  _ \\                       
   / _ \\ | |\\/| | |_) |                      
  / ___ \\| |  | |  _ <                       
 /_/   \\_\\_|  |_|_|_\\_\\     _                
 | |    ___   ___ | | __   / \\   _ __  _ __  
 | |   / _ \\ / _ \\| |/ /  / _ \\ | '_ \\| '_ \\ 
 | |__| (_) | (_) |   <  / ___ \\| |_) | |_) |
 |_____\\___/ \\___/|_|\\_\\/_/   \\_\\ .__/| .__/ 
 | ____|_ __ _ __ ___  _ __ ___ |_|   |_|    
 |  _| | '__| '__/ _ \\| '__/ __|             
 | |___| |  | | | (_) | |  \\__ \\             
 |_____|_|  |_|  \\___/|_|  |___/""")
print(f" {VERSION}")
print(f" (c)&(p) 2022-{datetime.datetime.now().strftime('%Y')} by Viktor 'MushroomOFF' Gribov")
print("########################################################")
print('')
logger(f'[{SCRIPT_NAME}]', f"{VERSION} (c)&(p) 2022-{datetime.datetime.now().strftime('%Y')} by Viktor 'MushroomOFF' Gribov")

artist_list = find_errors(log_file)
key_logger = input("Продолжить - Enter ")

if key_logger == '':
    for artist_name, artist_id, country in artist_list:
        print(f'{(artist_name + ' - ' + str(artist_id) + ' - ' + country):55}', end='\r')
        find_releases(artist_id, country, artist_name)

print(f'{'':55}')

if key_logger == '':
    logger(f'[{SCRIPT_NAME}]', '[V] Done!')
else:
    logger(f'[{SCRIPT_NAME}]', '[X] Aborted!')