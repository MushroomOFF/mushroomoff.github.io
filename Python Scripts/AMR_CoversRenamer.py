import datetime
import os
import shutil
import amr_functions as amr

# CONSTANTS
SCRIPT_NAME = "Covers Renamer"
VERSION = "2.026.02"
ENV = 'Local'
if os.getenv("GITHUB_ACTIONS") == "true":
    ENV = 'GitHub'

ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
LOG_FILE = os.path.join(ROOT_FOLDER, 'status.log')
ORIGINAL_COVERS_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/Проекты/_Covers/_BIG'

def main():
    if ENV == 'Local': 
        amr.print_name(SCRIPT_NAME, VERSION)
    amr.logger(f'▲ v.{VERSION} [{ENV}]', LOG_FILE, SCRIPT_NAME, 'noprint') # Begin

    # Prompt user for a path, if nothing is entered, use the original covers folder
    covers_folder = input(f'Path to big covers folder:\nEnter -> {ORIGINAL_COVERS_FOLDER}\n')
    if not covers_folder:
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
                amr.logger(f'ERROR: {check_file}', LOG_FILE, SCRIPT_NAME)

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
                amr.logger(f'FILE: {check_file} >>> GOTO: {name_band_folder}/{name_band}/{new_filename}', LOG_FILE, SCRIPT_NAME, 'covers_renamer')

    amr.logger(f'▼ DONE', LOG_FILE, SCRIPT_NAME) # End

if __name__ == "__main__":
    main()
