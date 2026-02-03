import csv
import datetime
import os
import pandas as pd
import requests
import time

# CONSTANTS
SCRIPT_NAME = "LookApp Errors"
VERSION = "2.026.02"
ENV = 'Local'
if os.getenv("GITHUB_ACTIONS") == "true":
    ENV = 'GitHub'

if ENV == 'Local':
    ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
elif ENV == 'GitHub':
    ROOT_FOLDER = ''
DB_FOLDER = os.path.join(ROOT_FOLDER, 'Databases/')
RELEASES_DB = os.path.join(DB_FOLDER, 'AMR_releases_DB.csv')
ARTIST_ID_DB = os.path.join(DB_FOLDER, 'AMR_artisitIDs.csv')
LOG_FILE = os.path.join(ROOT_FOLDER, 'status.log')
FIELDNAMES_DICT = ['dateUpdate', 'downloadedRelease', 'mainArtist', 'artistName', 'collectionName', 
               'trackCount', 'releaseDate', 'releaseYear', 'mainId', 'artistId', 'collectionId', 
               'country', 'artworkUrlD', 'downloadedCover', 'updReason']

session = requests.Session() 
session.headers.update({'Referer': 'https://itunes.apple.com', 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'})

# functions
def print_name():
    print_line = f'{SCRIPT_NAME} v.{VERSION}'
    print_line_len = 30
    if len(print_line) > 28:
        print_line_len = len(print_line) + 2
    print(f"\n{'':{'='}^{print_line_len}}")
    print(f"{'\033[1m'}{'Alternative & Metal Releases':{' '}^{print_line_len}}{'\033[0m'}")
    print(f"{print_line:{' '}^{print_line_len}}")
    print(f"{'':{'='}^{print_line_len}}\n")

def logger(log_line, *args):
    """Writing log line into log file
    * For GitHub Actions:
      - add +3 hours to datetime
      - no print()
    * For Local scripts:
      - print() without '▲','▼' and leading spaces
      - additional conditions for print() without logging
      - arguments is optional
      
      example - begin message:  logger(f'▲ v.{VERSION} [{ENV}]', 'noprint') # Begin
      example - normal message: logger(f'ERROR: {check_file}')
      example - end message:    logger(f'▼ DONE') # End
    """
    if log_line[0] not in ['▲', '▼']:
        log_line = f'  {log_line}'
    with open(LOG_FILE, 'r+') as log_file:
        log_file_content = log_file.read()
        log_file.seek(0, 0)
        log_date = datetime.datetime.now()
        if os.getenv("GITHUB_ACTIONS") == "true":
            log_date = log_date + datetime.timedelta(hours=3)
        log_file.write(f'{log_date.strftime('%Y-%m-%d %H:%M:%S')} [{SCRIPT_NAME}] {log_line.rstrip('\r\n')}\n{log_file_content}')
        # print() for Local scripts only
        # Additional conditions for print() without logging
        # 'noprint' parameter if no need to print() 
        if not os.getenv("GITHUB_ACTIONS"):
            if 'covers_renamer' in args:
                log_line = f'{log_line.replace(' >>> ', '\n')}\n'
            if 'noprint' not in args:
                print(log_line[2:])

def find_errors():
    """Finding errors in the AMR LookApp last run log"""
    with open(LOG_FILE, 'r') as lf:
        log_lines = lf.readlines()

    # Looking for the indexes of the first and last recording of AMR LookApp run
    begin_idx = next((i for i, line in enumerate(log_lines) 
                      if '[LookApp] ▼' in line), None)

    end_idx = next((i for i, line in enumerate(log_lines) 
                    if '[LookApp] ▲' in line), None)
    
    if begin_idx is None or end_idx is None or begin_idx >= end_idx:
        print("There's no errors in last AMR LookApp run")
        return []

    suffix = ('ERROR (503)\n', 'ERROR (502)\n')
    # List of Artists, IDs and Countries to check
    error_list = [
        line.split(' - ')[0:3]
        for line in log_lines[begin_idx:end_idx]
        if line.endswith(suffix)
    ]
    for error_line in error_list:
        error_line[0] = error_line[0].split('   ')[1]

    print(f'Errors found: {len(error_list)}')
    return error_list

def find_releases(find_artist_id, artist_print_name, country):
    # All releases of one Artist (all countries)
    all_releases_df = pd.DataFrame()
    # Unique releases of one Artist
    export_df = pd.DataFrame()

    url = f'https://itunes.apple.com/lookup?id={find_artist_id}&country={country}&entity=album&limit=200'
    response = session.get(url)

    if response.status_code == 200:
        json_parsed = response.json()
        if json_parsed['resultCount'] > 1:
            temp_df = pd.DataFrame(json_parsed['results'])
            all_releases_df = pd.concat([all_releases_df, temp_df[[
                'artistName', 'artistId', 'collectionId', 'collectionName',
                'artworkUrl100', 'trackCount', 'country', 'releaseDate'
            ]]], ignore_index=True)
        else:
            logger(f'{artist_print_name} - {find_artist_id} - {country} - EMPTY')
    else:
        logger(f'{artist_print_name} - {find_artist_id} - {country} - ERROR ({response.status_code})')

    # Pause to bypass iTunes server blocking
    time.sleep(1)

    # Remove duplicates via 'artworkUrl100'
    all_releases_df.drop_duplicates(subset='artworkUrl100', keep='first', inplace=True, ignore_index=True)

    # Select the rows with the filled 'collectionName'
    if not all_releases_df.empty:
        export_df = all_releases_df.loc[all_releases_df['collectionName'].notna()]

    if not export_df.empty:
        itunes_db_df = pd.read_csv(RELEASES_DB, sep=";")

        with open(RELEASES_DB, 'a+', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, delimiter=';', fieldnames=FIELDNAMES_DICT)

            date_update = datetime.datetime.now().strftime('%Y-%m-%d')
            new_release_counter = 0
            new_cover_counter = 0

            for _, row in export_df.iterrows():
                collection_id = row['collectionId']
                artwork_url_d = row['artworkUrl100'].replace('100x100bb', '100000x100000-999')

                if itunes_db_df[itunes_db_df['collectionId'] == collection_id].empty:
                    update_reason = 'New release'
                    new_release_counter += 1
                elif itunes_db_df[itunes_db_df['artworkUrlD'].str[40:] == artwork_url_d[40:]].empty:
                    # .str[40:] ------------------------------V The link matching check will start from here, since identical covers can be located on different servers
                    # https://is2-ssl.mzstatic.com/image/thumb/Music/v4/b2/cc/64/b2cc645c-9f18-db02-d0ab-69e296ea4d70/source/100000x100000-999.jpg            
                    update_reason = 'New cover'
                    new_cover_counter += 1
                else:
                    continue

                writer.writerow({
                    'dateUpdate': update_date, 'downloadedRelease': '', 'mainArtist': artist_print_name,
                    'artistName': row['artistName'], 'collectionName': row['collectionName'], 
                    'trackCount': row['trackCount'], 'releaseDate': row['releaseDate'][:10], 
                    'releaseYear': row['releaseDate'][:4], 'mainId': find_artist_id, 'artistId': row['artistId'], 
                    'collectionId': collectionId, 'country': row['country'], 'artworkUrlD': artwork_url_d, 
                    'downloadedCover': '', 'updReason': update_reason
                    })

        del itunes_db_df
        
        if (new_release_counter + new_cover_counter) > 0:
            logger(f'{artist_print_name} - {find_artist_id} - {new_release_counter + new_cover_counter} new records: {new_release_counter} releases, {new_cover_counter} covers')

def main():

    if ENV == 'Local': 
        print_name()
    logger(f'▲ v.{VERSION} [{ENV}]', 'noprint') # Begin

    artist_list = find_errors()
    key_logger = input("[Enter] to continue: ")

    if key_logger == '':
        for artist_print_name, find_artist_id, country in artist_list:
            print(f'{f'{artist_print_name} - {find_artist_id} - {country}':55}', end='\r')
            find_releases(find_artist_id, artist_print_name, country)

    print(f'{'':55}')
     
    if key_logger == '':
        logger(f'▼ DONE') # Good end
    else:
        logger(f'▼ DONE [canceled]') # Bad end

if __name__ == "__main__":
    main()
