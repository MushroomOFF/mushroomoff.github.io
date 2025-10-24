import datetime
import os
import shutil

# CONSTANTS
SCRIPT_NAME = "Covers Renamer"
VERSION = "v.2.025.10 [Local]"

ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
LOG_FILE = os.path.join(ROOT_FOLDER, 'status.log')
ORIGINAL_COVERS_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/Проекты/_Covers/_BIG'

# functions
def logger(log_line, *args):
    """Writing log line into log file
    * For GitHub Actions:
      - add +3 hours to datetime
      - no print()
    * For Local scripts:
      - print() without '▲','▼' and leading spaces
      - additional conditions for print() without logging
    """
    if log_line[0] not in ['▲','▼']:
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
        if not os.getenv("GITHUB_ACTIONS"):
            if 'covers_renamer' in args:
                log_line = f'{log_line.replace(' >>> ', '\n')}\n'
            print(log_line[2:])

def main():
    logger(f'▲ {VERSION}') # Begin

    # Prompt user for a path, if nothing is entered, use the original covers folder
    covers_folder = input(f'Path to big covers folder\nEnter -> {ORIGINAL_COVERS_FOLDER}:\n')
    if covers_folder == '':
        covers_folder = ORIGINAL_COVERS_FOLDER

    # Loop through all files in the root folder
    for check_file in os.listdir(covers_folder):
        # Check if the file is a JPG or JPEG
        is_jpg = '.jpg' in check_file.lower()
        is_jpeg = '.jpeg' in check_file.lower()
        if is_jpg or is_jpeg:
            error_mark = False
            text_block_count = check_file.count(' - ')

            # If the file name contains 2 or 3 ' - ' split the file name into band, album, and other parts
            if text_block_count == 2:
                name_band, name_album, name_year = check_file.split(' - ')
            elif text_block_count == 3:
                name_band, name_album, name_type, name_year = check_file.split(' - ')
                name_album = f'{name_album} [{name_type}]'
            else:
                error_mark = True
                logger(f'ERROR: {check_file}')

            # If no errors were found, proceed with the file renaming and moving
            if not error_mark:
                name_band_folder = str(name_band[0]).upper()

                # If the band name starts with a Cyrillic letter, set the band letter to 'Русское'
                if 1025 <= ord(name_band_folder) <= 1105:
                    name_band_folder = 'Русское'
                # If the band name starts with a non-alphabetical character, set the band letter to '0'
                elif ord(name_band_folder) < 65:
                    name_band_folder = '0'

                if is_jpg:
                    new_filename_extension = '.jpg'
                elif is_jpeg:
                    new_filename_extension = '.jpeg'

                new_filename = f'{name_year[:4]} {name_album}{new_filename_extension}'
                new_directory = os.path.join(covers_folder, name_band_folder, name_band)
                current_file = os.path.join(covers_folder, check_file)
                new_file = os.path.join(new_directory, new_filename)

                # If the directory does not exist, create it
                if not os.path.exists(new_directory):
                    os.makedirs(new_directory)

                # Move the file to the new directory
                shutil.move(current_file, new_file)
                logger(f'FILE: {check_file} >>> GOTO: {name_band_folder}/{name_band}/{new_filename}', 'covers_renamer')

    logger(f'▼ DONE') # End

if __name__ == "__main__":
    main()