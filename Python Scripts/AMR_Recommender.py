import csv
import datetime
import json
import os
import pandas as pd
import requests
import amr_functions as amr

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

def main():
    global TOKEN, CHAT_ID

    if ENV == 'Local': 
        amr.print_name(SCRIPT_NAME, VERSION)
    amr.logger(f'▲ v.{VERSION} [{ENV}]', LOG_FILE, SCRIPT_NAME, 'noprint') # Begin

    if ENV == 'Local':
        PARAMS = input("[IMPORTANT!] TOKEN CHAT_ID YM_TOKEN ZV_TOKEN: ").split(' ')
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

    for index, row in new_releases_df[new_releases_df['best_fav_new_ok'].isna()].iterrows():
        amr_link = f'{AMR_FOLDER}{row.loc['date'][0:4]}/AMR {row.loc['date'][0:7]}.html'
        with open(amr_link, 'r', encoding='utf-8') as html_file:
            source_code = html_file.read()
            release_position = source_code.find(f'<!-- {row['artist']} - {row['album']} -->')
            begin_position = source_code.find("id='", release_position) + len("id='")
            end_position = source_code.find("'>", begin_position)
            release_record = source_code[begin_position:end_position].strip()
            if len(release_record) == 1:
                new_releases_df.loc[index,'best_fav_new_ok'] = release_record
                ok_counter += 1
            elif len(release_record) == 0:
                empty_counter += 1
            else:
                new_releases_df.loc[index,'best_fav_new_ok'] = 'E'
                error_counter += 1

    amr.logger(f'OK: {ok_counter}; Emptys: {empty_counter}; Errors: {error_counter}', LOG_FILE, SCRIPT_NAME)

    top_release_counter = 0
    # Sending to Top Releases (O)
    for index, row in new_releases_df[(new_releases_df['best_fav_new_ok'] == 'o') & (new_releases_df['tg_message_id'] == 0)].iterrows():
        image_url = row.loc['image_link'].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
        text = f'*{amr.replace_symbols_markdown_v2(row.loc['artist'].replace('&amp;','&'))}* \\- [{amr.replace_symbols_markdown_v2(row.loc['album'].replace('&amp;','&'))}]({row.loc['link'].replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({row.loc['link']}){'' if pd.isna(row.loc['link_ym']) else f'\n\U0001F4A5 [Яндекс\\.Музыка]({row.loc['link_ym']})'}{'' if pd.isna(row.loc['link_zv']) else f'\n\U0001F50A [Звук]({row.loc['link_zv']})'}'
        message_to_send = amr.send_photo('Top Releases', text, image_url, TOKEN, CHAT_ID)
        if TOKEN and CHAT_ID:
            new_releases_df.loc[index,'tg_message_id'] = message_to_send
        top_release_counter += 1

    new_release_counter = 0
    # Sending to New Releases (V, D)
    for index, row in new_releases_df[(new_releases_df['best_fav_new_ok'].isin(['v','d'])) & (new_releases_df['tg_message_id'] == 0)].iterrows():
        image_url = row.loc['image_link'].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
        text = f'*{amr.replace_symbols_markdown_v2(row.loc['artist'].replace('&amp;','&'))}* \\- [{amr.replace_symbols_markdown_v2(row.loc['album'].replace('&amp;','&'))}]({row.loc['link'].replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({row.loc['link']}){'' if pd.isna(row.loc['link_ym']) else f'\n\U0001F4A5 [Яндекс\\.Музыка]({row.loc['link_ym']})'}{'' if pd.isna(row.loc['link_zv']) else f'\n\U0001F50A [Звук]({row.loc['link_zv']})'}'
        message_to_send = amr.send_photo('New Releases', text, image_url, TOKEN, CHAT_ID)
        if TOKEN and CHAT_ID:
            new_releases_df.loc[index,'tg_message_id'] = message_to_send
        new_release_counter += 1

    # Attenition: Write to file (!)
    new_releases_df.to_csv(NEW_RELEASES_DB, sep=';', index=False)
    del new_releases_df
    amr.logger(f'New Releases: {new_release_counter}; Top Releases: {top_release_counter}', LOG_FILE, SCRIPT_NAME)

    if not TOKEN or not CHAT_ID:
        amr.logger('Message not sent! No TOKEN or CHAT_ID', LOG_FILE, SCRIPT_NAME)

    amr.logger(f'▼ DONE', LOG_FILE, SCRIPT_NAME) # End

if __name__ == "__main__":
    main()
