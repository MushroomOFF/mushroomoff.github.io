import datetime
import json
import os
import pandas as pd
import requests
import sqlite3
import time
import traceback
import amr_functions as amr

# ================= CONSTANTS & VARIABLES =================
SCRIPT_NAME = "LookApp Errors"
VERSION = "2.026.07"

ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
DB_FOLDER = os.path.join(ROOT_FOLDER, 'Databases/')
DB_FILE = os.path.join(DB_FOLDER, 'music_releases.db')
LOG_FILE = os.path.join(ROOT_FOLDER, 'status.log')

session = requests.Session() 
session.headers.update({'Referer': 'https://itunes.apple.com', 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'})

# ================= DATABASE FUNCTIONS =================
def check_collection_exists(album_id):
    """Проверить, существует ли релиз в БД"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM my_releases WHERE album_id = ?', (album_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] > 0
    except Exception as e:
        print(f'Error checking collection {album_id}: {e}')
        return False


def check_cover_exists(album_id, artwork_url):
    """Проверить, совпадает ли обложка (сравнение с 40-го символа)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT cover_link FROM my_releases WHERE album_id = ?', (album_id,))
        result = cursor.fetchone()
        conn.close()
        if result and result[0] and len(result[0]) > 40 and len(artwork_url) > 40:
            return result[0][40:] == artwork_url[40:]
        return False
    except Exception as e:
        print(f'Error checking cover for {album_id}: {e}')
        return False


def insert_release(release_data):
    """Вставить релиз в БД с явным преобразованием типов"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO my_releases
            (update_date, main_artist, artist, album, tracks, release_date, 
             release_year, main_artist_id, artist_id, album_id, country, 
             cover_link, update_reason)

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(release_data['dateUpdate']),
            str(release_data['mainArtist']),
            str(release_data['artistName']),
            str(release_data['collectionName']),
            int(release_data['trackCount']),
            str(release_data['releaseDate']),
            int(release_data['releaseYear']),
            int(release_data['mainId']),
            int(release_data['artistId']),
            int(release_data['collectionId']),
            str(release_data['country']),
            str(release_data['artworkUrlD']),
            str(release_data['updReason'])
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'Error inserting release {release_data.get("collectionId")}: {e}')
        traceback.print_exc()
        return False


# ================= MAIN FUNCTIONS =================
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
    """Поиск релизов одного артиста по всем странам"""
    # All releases of one Artist (all countries)
    all_releases_df = pd.DataFrame()
    # Unique releases of one Artist
    export_df = pd.DataFrame()

    try:
        url = f'https://itunes.apple.com/lookup?id={find_artist_id}&country={country}&entity=album&limit=200'
        response = session.get(url, timeout=30)

        if response.status_code == 200:
            try:
                json_parsed = response.json()
                if json_parsed.get('resultCount', 0) > 1:
                    temp_df = pd.DataFrame(json_parsed['results'])
                    temp_df = temp_df[['artistName', 'artistId', 'collectionId', 'collectionName',
                                        'artworkUrl100', 'trackCount', 'country', 'releaseDate']].copy()
                    all_releases_df = pd.concat([all_releases_df, temp_df], ignore_index=True)
                else:
                    print(f'{artist_print_name} - {find_artist_id} - {country} - EMPTY')
            except json.JSONDecodeError as e:
                print(f'JSON decode error for {artist_print_name} - {country}: {e}')
        else:
            print(f'{artist_print_name} - {find_artist_id} - {country} - ERROR ({response.status_code})')

    except requests.exceptions.RequestException as e:
        print(f'Request error for {artist_print_name} - {country}: {e}')
    except Exception as e:
        print(f'Unexpected error for {artist_print_name} - {country}: {e}')
        traceback.print_exc()

    # Pause to bypass iTunes server blocking
    time.sleep(1)

    # Remove duplicates via 'artworkUrl100'
    # Select the rows with the filled 'collectionName'
    if not all_releases_df.empty:
        all_releases_df.drop_duplicates(subset='artworkUrl100', keep='first', inplace=True, ignore_index=True)
        export_df = all_releases_df.loc[all_releases_df['collectionName'].notna()].copy()

    if not export_df.empty:
        update_date = datetime.datetime.now().strftime('%Y-%m-%d')
        new_release_counter = 0
        new_cover_counter = 0

        for _, row in export_df.iterrows():
            # Каждый релиз обрабатываем отдельно — если один упадет, продолжим со следующего
            try:
                collection_id = int(row['collectionId'])
                artwork_url_d = str(row['artworkUrl100']).replace('100x100bb', '10000x10000-999')

                # Безопасное преобразование типов
                track_count = int(row['trackCount']) if pd.notna(row.get('trackCount')) else 0
                artist_id = int(row['artistId']) if pd.notna(row.get('artistId')) else 0
                release_date_str = str(row.get('releaseDate', ''))

                if not check_collection_exists(collection_id):
                    update_reason = 'New release'
                    new_release_counter += 1
                elif not check_cover_exists(collection_id, artwork_url_d):
                    update_reason = 'New cover'
                    new_cover_counter += 1
                else:
                    continue

                release_data = {
                    'dateUpdate': update_date,
                    'mainArtist': artist_print_name,
                    'artistName': str(row.get('artistName', '')),
                    'collectionName': str(row.get('collectionName', '')),
                    'trackCount': track_count,
                    'releaseDate': release_date_str[:10] if len(release_date_str) >= 10 else release_date_str,
                    'releaseYear': int(release_date_str[:4]) if len(release_date_str) >= 4 else 0,
                    'mainId': find_artist_id,
                    'artistId': artist_id,
                    'collectionId': collection_id,
                    'country': str(row.get('country', '')),
                    'artworkUrlD': artwork_url_d,
                    'updReason': update_reason
                }

                if not insert_release(release_data):
                    print(f'  ✗ Failed to insert: {release_data["collectionName"]}')

            except Exception as e:
                print(f'  ✗ Error processing release row: {e}')
                traceback.print_exc()
                continue  # Продолжаем со следующего релиза

        if (new_release_counter + new_cover_counter) > 0:
            print(f'{artist_print_name} - {find_artist_id} - {new_release_counter + new_cover_counter} '
                  f'new records: {new_release_counter} releases, {new_cover_counter} covers')


def main():
    amr.print_name(SCRIPT_NAME, VERSION)

    artist_list = find_errors()
    key_logger = input("[Enter] to continue: ")

    if key_logger == '':
        for artist_print_name, find_artist_id, country in artist_list:
            print(f'{f'{artist_print_name} - {find_artist_id} - {country}':55}', end='\r')
            find_releases(find_artist_id, artist_print_name, country)

    print(f'{'':55}')


if __name__ == "__main__":
    main()
