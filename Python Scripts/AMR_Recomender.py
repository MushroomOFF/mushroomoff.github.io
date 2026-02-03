import os
import json
import datetime
import requests
import pandas as pd
import csv

# CONSTANTS
SCRIPT_NAME = "Recommender"
VERSION = "2.026.02"
ENV = 'Local'
if os.getenv("GITHUB_ACTIONS") == "true":
    ENV = 'GitHub'

if ENV == 'Local':
    ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
elif ENV == 'GitHub':
    ROOT_FOLDER = ''
AMR_FOLDER = os.path.join(ROOT_FOLDER, 'AMRs/')
DB_FOLDER = os.path.join(ROOT_FOLDER, 'Databases/')
NEW_RELEASES_DB = os.path.join(DB_FOLDER, 'AMR_newReleases_DB.csv')
LOG_FILE = os.path.join(ROOT_FOLDER, 'status.log')

# Telegram -------------------------------
TOKEN = ''
CHAT_ID = ''
URL = 'https://api.telegram.org/bot'
THREAD_ID_DICT = {'New Updates': 6, 'Top Releases': 10, 'Coming Soon': 3, 'New Releases': 2, 'Next Week Releases': 80}
#-----------------------------------------

# functions
def replace_symbols_markdown_v2(text_line):
    """Replacing Markdown v2 unused characters 
    in Telegram message text line 
    """
    symbols_to_replace = """'_*[]",()~`>#+-=|{}.!"""
    for symbol in symbols_to_replace:
        text_line = text_line.replace(symbol, f'\\{symbol}')
    return text_line

def send_photo(topic, text, image_url):
    """Sending Telegram message with photo"""
    global TOKEN, CHAT_ID
    method = f"{URL}{TOKEN}/sendPhoto"
    response = requests.post(method, data={"message_thread_id": THREAD_ID_DICT[topic], "chat_id": CHAT_ID, "photo": image_url, "parse_mode": 'MarkdownV2', "caption": text})
    json_response = json.loads(response.text)
    result_message_id = json_response['result']['message_id']    
    return result_message_id

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

def main():
    global TOKEN, CHAT_ID

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

    new_releases_df = pd.read_csv(NEW_RELEASES_DB, sep=";")

    # Check AMR files for recomendations
    ok_counter = 0
    error_counter = 0
    empty_counter = 0

    for index, row in new_releases_df[new_releases_df['Best_Fav_New_OK'].isna()].iterrows():
        amr_link = f'{AMR_FOLDER}{row.loc['date'][0:4]}/AMR {row.loc['date'][0:7]}.html'
        with open(amr_link, 'r', encoding='utf-8') as html_file:
            source_code = html_file.read()
            release_position = source_code.find(f'<!-- {row['artist']} - {row['album']} -->')
            begin_position = source_code.find("id='", release_position) + len("id='")
            end_position = source_code.find("'>", begin_position)
            release_record = source_code[begin_position:end_position].strip()
            if len(release_record) == 1:
                new_releases_df.loc[index,'Best_Fav_New_OK'] = release_record
                ok_counter += 1
            elif len(release_record) == 0:
                empty_counter += 1
            else:
                new_releases_df.loc[index,'Best_Fav_New_OK'] = 'E'
                error_counter += 1

    logger(f'OK: {ok_counter}; Emptys: {empty_counter}; Errors: {error_counter}')

    top_release_counter = 0
    # Sending to Top Releases (O)
    for index, row in new_releases_df[(new_releases_df['Best_Fav_New_OK'] == 'o') & (new_releases_df['TGmsgID'].isna())].iterrows():
        image_url = row.loc['imga'].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
        text = f'*{replace_symbols_markdown_v2(row.loc['artist'].replace('&amp;','&'))}* \\- [{replace_symbols_markdown_v2(row.loc['album'].replace('&amp;','&'))}]({row.loc['link'].replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({row.loc['link']}){'' if pd.isna(row.loc['link_ym']) else f'\n\U0001F4A5 [Яндекс\\.Музыка]({row.loc['link_ym']})'}{'' if pd.isna(row.loc['link_zv']) else f'\n\U0001F50A [Звук]({row.loc['link_zv']})'}'
        message_to_send = send_photo('Top Releases', text, image_url)
        if TOKEN and CHAT_ID:
            new_releases_df.loc[index,'TGmsgID'] = message_to_send
        top_release_counter += 1

    new_release_counter = 0
    # Sending to New Releases (V, D)
    for index, row in new_releases_df[(new_releases_df['Best_Fav_New_OK'].isin(['v','d'])) & (new_releases_df['TGmsgID'].isna())].iterrows():
        image_url = row.loc['imga'].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
        text = f'*{replace_symbols_markdown_v2(row.loc['artist'].replace('&amp;','&'))}* \\- [{replace_symbols_markdown_v2(row.loc['album'].replace('&amp;','&'))}]({row.loc['link'].replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({row.loc['link']}){'' if pd.isna(row.loc['link_ym']) else f'\n\U0001F4A5 [Яндекс\\.Музыка]({row.loc['link_ym']})'}{'' if pd.isna(row.loc['link_zv']) else f'\n\U0001F50A [Звук]({row.loc['link_zv']})'}'
        message_to_send = send_photo('New Releases', text, image_url)
        if TOKEN and CHAT_ID:
            new_releases_df.loc[index,'TGmsgID'] = message_to_send
        new_release_counter += 1

    # Attenition: Write to file (!)
    new_releases_df.to_csv(NEW_RELEASES_DB, sep=';', index=False)
    del new_releases_df
    logger(f'New Releases: {new_release_counter}; Top Releases: {top_release_counter}')

    if not TOKEN or not CHAT_ID:
        logger('Message not sent! No TOKEN or CHAT_ID')

    logger(f'▼ DONE') # End

if __name__ == "__main__":
    main()
