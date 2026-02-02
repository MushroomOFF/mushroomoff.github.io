import requests
import os
import pandas as pd
import csv
import time
import json
import datetime
from math import nan

# CONSTANTS
SCRIPT_NAME = "LookApp"
VERSION = "2.026.02"
ENV = 'Local'
if os.getenv("GITHUB_ACTIONS") == "true":
    ENV = 'GitHub'
    # GitHub version will always run complete list of artists

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
EMOJI_DICT = {'us': '\U0001F1FA\U0001F1F8', 'ru': '\U0001F1F7\U0001F1FA', 'jp': '\U0001F1EF\U0001F1F5', 'no': '\U0001F3F3\U0000FE0F', 
              'wtf': '\U0001F914', 'album': '\U0001F4BF', 'cover': '\U0001F3DE\U0000FE0F', 'error': '\U00002757\U0000FE0F', 
              'empty': '\U0001F6AB', 'badid': '\U0000274C'}
countries_list = []
message_to_send = '' 
message_empty = '' 
message_error = '' 
message_bad_id = '' 

session = requests.Session() 
session.headers.update({'Referer': 'https://itunes.apple.com', 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'})

# Telegram -------------------------------
TOKEN = ''
CHAT_ID = ''
URL = 'https://api.telegram.org/bot'
THREAD_ID_DICT = {'New Updates': 6, 'Top Releases': 10, 'Coming Soon': 3, 'New Releases': 2, 'Next Week Releases': 80}
#-----------------------------------------

# functions
def replace_symbols_markdown_v2(text_line):
    """Replacing Markdown v2 unused 
    characters in Telegram message 
    text line 
    """
    symbols_to_replace = """'_*[]",()~`>#+-=|{}.!"""
    for symbol in symbols_to_replace:
        text_line = text_line.replace(symbol, f'\\{symbol}')
    return text_line

def send_message(topic, text):
    global TOKEN, CHAT_ID
    """Sending Telegram message 
    """    
    method = f"{URL}{TOKEN}/sendMessage"
    request = requests.post(method, data={"message_thread_id": THREAD_ID_DICT[topic], "chat_id": CHAT_ID, "parse_mode": 'MarkdownV2', "text": text})
    json_response = json.loads(request.text)
    result_message_id = json_response['result']['message_id']   
    return result_message_id

def create_db():
    """Creating database 
    (if there's no database)
    """
    if not os.path.exists(RELEASES_DB):
        with open(RELEASES_DB, 'a+', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, delimiter=';', fieldnames=FIELDNAMES_DICT)
            writer.writeheader()
        print('New database created\n')

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

# Процедура Поиска релизов исполнителя в базе iTunes  
def find_releases(find_artist_id, artist_print_name):
    global message_to_send, message_empty, message_error, message_bad_id, session, countries_list
    all_releases_df = pd.DataFrame() #All releases of one Artist (all countries)
    export_df = pd.DataFrame() #Unique releases of one Artist
    is_error = False
    for country in countries_list:
        url = f'https://itunes.apple.com/lookup?id={find_artist_id}&country={country}&entity=album&limit=200'
        request = session.get(url)
        if request.status_code == 200:     
            json_parsed = json.loads(request.text)
            if json_parsed['resultCount'] > 1:
                temp_df = pd.DataFrame(json_parsed['results'])
                all_releases_df = pd.concat([all_releases_df, temp_df[['artistName', 'artistId', 'collectionId', 'collectionName', 'artworkUrl100', 'trackCount', 'country', 'releaseDate']]], ignore_index=True)
            else:
                if not is_error and ENV == 'Local':
                    print('\n', end='')
                print(f' {country} - EMPTY |', sep=' ', end='', flush=True)
                logger(f'{artist_print_name} - {find_artist_id} - {country} - EMPTY', 'noprint')
                message_empty += f'\n{EMOJI_DICT[country]} *{replace_symbols_markdown_v2(artist_print_name.replace('&amp;','and'))}*'
                is_error = True
        else:
            if not is_error and ENV == 'Local':
                print('\n', end='')
            print(f' {country} - ERROR ({request.status_code}) |', sep=' ', end='', flush=True)
            logger(f'{artist_print_name} - {find_artist_id} - {country} - ERROR ({request.status_code})', 'noprint')
            message_error += f'\n{EMOJI_DICT[country]} *{replace_symbols_markdown_v2(artist_print_name.replace('&amp;','and'))}*'
            is_error = True
        time.sleep(1) # anti-blocking
    all_releases_df.drop_duplicates(subset='artworkUrl100', keep='first', inplace=True, ignore_index=True)
    if not all_releases_df.empty:
        export_df = all_releases_df.loc[all_releases_df['collectionName'].notna()]
    elif len(countries_list) > 1:
        if not is_error and ENV == 'Local':
            print('\n', end='')
        print(f' Bad ID: {find_artist_id}', sep=' ', end='', flush=True)
        logger(f'{artist_print_name} - {find_artist_id} - Bad ID', 'noprint')
        message_bad_id += f'\n{EMOJI_DICT['no']} *{replace_symbols_markdown_v2(artist_print_name.replace('&amp;','and'))}*'
        is_error = True

    if is_error and ENV == 'Local':
        print ('') 

    if not export_df.empty:
        itunes_db_df = pd.read_csv(RELEASES_DB, sep=";")
        csv_file = open(RELEASES_DB, 'a+', newline='')
        writer = csv.DictWriter(csv_file, delimiter=';', fieldnames=FIELDNAMES_DICT)

        dateUpdate = datetime.datetime.now().strftime('%Y-%m-%d')        
        mainArtist = artist_print_name
        mainId = find_artist_id
        updReason = ''
        new_release_counter = 0
        new_cover_counter = 0

        for index, row in export_df.iterrows():
            artistName = row.iloc[0]
            artistId = row.iloc[1]
            collectionId = row.iloc[2]
            collectionName = row.iloc[3]
            artworkUrl100 = row.iloc[4]
            trackCount = row.iloc[5]
            countryCode = row.iloc[6]
            releaseDate = row.iloc[7][:10]
            releaseYear = row.iloc[7][:4]
            artworkUrlD = row.iloc[4].replace('100x100bb', '100000x100000-999')
            downloadedCover = ''
            downloadedRelease = ''
            updReason = ''
            if len(itunes_db_df.loc[itunes_db_df['collectionId']  == export_df.iloc[index-1]['collectionId']]) == 0:
                updReason = 'New release'
                new_release_counter += 1
            elif len(itunes_db_df[itunes_db_df['artworkUrlD'].str[40:] == export_df.iloc[index-1]['artworkUrl100'].replace('100x100bb', '100000x100000-999')[40:]]) == 0:
                updReason = 'New cover'
                new_cover_counter += 1
                #.str[40] -------------------------------V
                #https://is2-ssl.mzstatic.com/image/thumb/Music/v4/b2/cc/64/b2cc645c-9f18-db02-d0ab-69e296ea4d70/source/100000x100000-999.jpg

            if updReason:
                writer.writerow({
                    'dateUpdate': dateUpdate, 'downloadedRelease': downloadedRelease, 'mainArtist': mainArtist,
                    'artistName': artistName, 'collectionName': collectionName, 'trackCount': trackCount, 
                    'releaseDate': releaseDate, 'releaseYear': releaseYear, 'mainId': mainId, 'artistId': artistId, 
                    'collectionId': collectionId, 'country': countryCode, 'artworkUrlD': artworkUrlD, 
                    'downloadedCover': downloadedCover, 'updReason': updReason
                    })

        csv_file.close()
        itunes_db_df = pd.DataFrame()
        
        if (new_release_counter + new_cover_counter) > 0:
            print(f'\n^ {new_release_counter + new_cover_counter} new records: {new_release_counter} releases, {new_cover_counter} covers')
            logger(f'{artist_print_name} - {find_artist_id} - {new_release_counter + new_cover_counter} new records: {new_release_counter} releases, {new_cover_counter} covers', 'noprint')
            if new_release_counter > 0 :
                iconka = 'album'
            else:
                iconka = 'cover'
            message_to_send += f'\n{EMOJI_DICT[iconka]} *{replace_symbols_markdown_v2(artist_print_name.replace('&amp;','and'))}*: {new_release_counter + new_cover_counter}'

def main():
    global TOKEN, CHAT_ID, message_to_send, message_empty, message_error, message_bad_id, session, countries_list

    if ENV == 'Local': 
        print_name()
    logger(f'▲ v.{VERSION} [{ENV}]', 'noprint') # Begin

    if ENV == 'Local':
        PARAMS = input("(optional) TOKEN CHAT_ID YM_TOKEN ZV_TOKEN: ").split(' ')
        if len(PARAMS) > 1:
            TOKEN = PARAMS[0] # input("Telegram Bot TOKEN: ")
            CHAT_ID = PARAMS[1] # input("Telegram Bot CHAT_ID: ")
        else:
            print('Not enough parameters! Message will not be sent!\n')
    elif ENV == 'GitHub': 
        TOKEN = os.environ['tg_token']
        CHAT_ID = os.environ['tg_channel_id']

    if ENV == 'Local':
        countries_input = input("\nChoose countries to check:\nEnter: [us, ru, jp]\n2:     [us, ru]\njp:    [jp]\n")
        if countries_input == 'jp':
            countries_list = ['jp']
        elif countries_input == '2':
            countries_list = ['us', 'ru']
        else:
            countries_list = ['us', 'ru', 'jp']
        print(f'{countries_list}\n')
    elif ENV == 'GitHub':
        countries_list = ['us', 'ru']

    message_to_send = ''
    message_error_part = replace_symbols_markdown_v2('======== ERRORS ========')
    message_error = EMOJI_DICT['error'] + ' 503 Service Unavailable ' + EMOJI_DICT['error']
    message_empty = EMOJI_DICT['empty'] + ' Not available in country ' + EMOJI_DICT['empty']
    message_bad_id = EMOJI_DICT['badid'] + '               Bad ID                ' + EMOJI_DICT['badid']
    check_mes_send_len = len(message_to_send)
    check_mes_error_len = len(message_error)
    check_mes_empty_len = len(message_empty)
    check_mes_badid_len = len(message_bad_id)

    create_db()

    artist_id_df = pd.read_csv(ARTIST_ID_DB, sep=';')
    if ENV == 'Local':
        artist_to_find = artist_id_df['mainArtist'][artist_id_df['downloaded'].isna() & artist_id_df['mainId'] > 0].head(1)
        if artist_to_find.empty:
            key_logger = input("All done. [Enter] to start over: ")
            if not key_logger:
                artist_id_df.drop('downloaded', axis=1, inplace=True)
                artist_id_df.insert(4, "downloaded", nan)
                artist_id_df.to_csv(ARTIST_ID_DB, sep=';', index=False)
        else:
            key_logger = input(f"Stopped at {artist_to_find[artist_to_find.index[0]]}. [Enter] to continue. Anything else to start over: ")
            if key_logger:
                artist_id_df.drop('downloaded', axis=1, inplace=True)
                artist_id_df.insert(4, "downloaded", nan)
                artist_id_df.to_csv(ARTIST_ID_DB, sep=';', index=False)
        print('')
    elif ENV == 'GitHub':
        artist_id_df.drop('downloaded', axis=1, inplace=True)
        artist_id_df.insert(4, "downloaded", nan)
        artist_id_df.to_csv(ARTIST_ID_DB, sep=';', index=False)

    while True:
        artist_id_df = pd.read_csv(ARTIST_ID_DB, sep=';')
        artist_to_find = artist_id_df[artist_id_df['downloaded'].isna() & artist_id_df['mainId'] > 0].head(1)
        if artist_to_find.empty:
            break
        
        row_index = artist_to_find.index[0]
        # row_index -> natural index without header, straing with 0
        # row_index + 2 -> index for line in csv file with header, starting with 1. For print() only

        artist_id = int(artist_to_find.at[row_index, 'mainId'])
        artist_print_name = artist_to_find.at[row_index, 'mainArtist']
        print(f'{f'{artist_print_name} - {artist_id}':55}', end='\r')

        find_releases(artist_id, artist_print_name)
        
        if ENV == 'Local':
            date_of_update = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elif ENV == 'GitHub':
            date_of_update = (datetime.datetime.now() + datetime.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        artist_id_df.at[row_index, 'downloaded'] = date_of_update
        artist_id_df.to_csv(ARTIST_ID_DB, sep=';', index=False)

        time.sleep(1.5) # anti-blocking

    print(f'{'':55}')

    if not TOKEN or not CHAT_ID:
        print('Message not sent! No TOKEN or CHAT_ID')
    else:
        if check_mes_send_len == len(message_to_send):
            message_to_send += '\n' + EMOJI_DICT['wtf']

        if check_mes_error_len != len(message_error) or check_mes_empty_len != len(message_empty) or check_mes_badid_len != len(message_bad_id):
            message_to_send += '\n\n' + message_error_part
            if check_mes_badid_len != len(message_bad_id):
                message_to_send += '\n\n' + message_bad_id
            if check_mes_error_len != len(message_error):
                message_to_send += '\n\n' + message_error
            if check_mes_empty_len != len(message_empty):
                message_to_send += '\n\n' + message_empty
        
        send_message('New Updates', message_to_send)

    logger(f'▼ DONE') # End

if __name__ == "__main__":
    main()
