import csv
import datetime
import json
import os
import pandas as pd
import requests
from dotenv import load_dotenv
import amr_functions as amr

# ================= CONSTANTS & VARIABLES =================
SCRIPT_NAME = "Recommender"
VERSION = "2.026.04"
ENV = 'Local'
if os.getenv("GITHUB_ACTIONS") == "true":
    ENV = 'GitHub'

if ENV == 'Local':
    ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
    load_dotenv(os.path.join(ROOT_FOLDER, '.env'))
elif ENV == 'GitHub':
    ROOT_FOLDER = ''

TOKEN = os.environ['tg_token']
CHAT_ID = os.environ['tg_channel_id']
LOGGER_ID = os.environ['tg_logger_id']
YM_TOKEN = os.environ['ym_token']
ZVUK_TOKEN = os.environ['zv_token']

AMR_FOLDER = os.path.join(ROOT_FOLDER, 'AMRs/')
DB_FOLDER = os.path.join(ROOT_FOLDER, 'Databases/')
NEW_RELEASES_DB = os.path.join(DB_FOLDER, 'AMR_newReleases_DB.csv')
# LOG_FILE = os.path.join(ROOT_FOLDER, 'status.log')


# ================= FUNCTIONS =================
def main():
    if ENV == 'Local': 
        amr.print_name(SCRIPT_NAME, VERSION)
    # amr.logger(f'▲ v.{VERSION} [{ENV}]', LOG_FILE, SCRIPT_NAME, 'noprint') # Begin

    app_version = amr.replace_symbols_markdown_v2(f'v.{VERSION} [{ENV}]')
    welcome_message = f'🚀 *{SCRIPT_NAME}*\n{app_version}'
    amr.send_message(welcome_message, TOKEN, LOGGER_ID, None, None)

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

    # amr.logger(f'OK: {ok_counter}; Emptys: {empty_counter}; Errors: {error_counter}', LOG_FILE, SCRIPT_NAME)
    logger_message = f'🟢 OK: {ok_counter}\n⭕️ Emptys: {empty_counter}\n❌ Errors: {error_counter}'
    amr.send_message(logger_message, TOKEN, LOGGER_ID, None, None)

    top_release_counter = 0
    # Sending to Top Releases (O)
    for index, row in new_releases_df[(new_releases_df['best_fav_new_ok'] == 'o') & (new_releases_df['tg_message_id'] == 0)].iterrows():
        image_url = row.loc['image_link'].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
        text = f'*{amr.replace_symbols_markdown_v2(row.loc['artist'].replace('&amp;','&'))}* \\- [{amr.replace_symbols_markdown_v2(row.loc['album'].replace('&amp;','&'))}]({row.loc['link'].replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({row.loc['link']}){'' if pd.isna(row.loc['link_ym']) else f'\n\U0001F4A5 [Яндекс\\.Музыка]({row.loc['link_ym']})'}{'' if pd.isna(row.loc['link_zv']) else f'\n\U0001F50A [Звук]({row.loc['link_zv']})'}'
        message_to_send = amr.send_message(text, TOKEN, CHAT_ID, image_url, 'Top Releases')
        if TOKEN and CHAT_ID:
            new_releases_df.loc[index,'tg_message_id'] = message_to_send
        top_release_counter += 1

    new_release_counter = 0
    # Sending to New Releases (V, D)
    for index, row in new_releases_df[(new_releases_df['best_fav_new_ok'].isin(['v','d'])) & (new_releases_df['tg_message_id'] == 0)].iterrows():
        image_url = row.loc['image_link'].replace('296x296bb.webp', '632x632bb.webp').replace('296x296bf.webp', '632x632bf.webp')
        text = f'*{amr.replace_symbols_markdown_v2(row.loc['artist'].replace('&amp;','&'))}* \\- [{amr.replace_symbols_markdown_v2(row.loc['album'].replace('&amp;','&'))}]({row.loc['link'].replace('://','://embed.')})\n\n\U0001F3B5 [Apple Music]({row.loc['link']}){'' if pd.isna(row.loc['link_ym']) else f'\n\U0001F4A5 [Яндекс\\.Музыка]({row.loc['link_ym']})'}{'' if pd.isna(row.loc['link_zv']) else f'\n\U0001F50A [Звук]({row.loc['link_zv']})'}'
        message_to_send = amr.send_message(text, TOKEN, CHAT_ID, image_url, 'New Releases')
        if TOKEN and CHAT_ID:
            new_releases_df.loc[index,'tg_message_id'] = message_to_send
        new_release_counter += 1

    # Attenition: Write to file (!)
    new_releases_df.to_csv(NEW_RELEASES_DB, sep=';', index=False)
    del new_releases_df
    # amr.logger(f'New Releases: {new_release_counter}; Top Releases: {top_release_counter}', LOG_FILE, SCRIPT_NAME)
    logger_message = f'🔥 New Releases: {new_release_counter}\n🔝 Top Releases: {top_release_counter}\n\n📥 Fetch and Pull'
    amr.send_message(logger_message, TOKEN, LOGGER_ID, None, None)

    # amr.logger(f'▼ DONE', LOG_FILE, SCRIPT_NAME) # End

if __name__ == "__main__":
    main()
