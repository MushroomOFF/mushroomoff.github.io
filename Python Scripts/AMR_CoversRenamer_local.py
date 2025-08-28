SCRIPT_NAME = "Apple Music Releases Cover Renamer"
VERSION = "v.2.025.08 [Local]"

import os
import shutil
import datetime

# Логирование
def logger(script_name, log_line):
    """Запись лога в файл."""
    with open(log_file, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(str(datetime.datetime.now()) + ' - ' + script_name + ' - ' + log_line.rstrip('\r\n') + '\n' + content)

rootFolder = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
log_file = os.path.join(rootFolder, 'status.log')

# Original root folder path
originalRootFolder = '/Users/mushroomoff/Yandex.Disk.localized/Проекты/_Covers/_BIG'

logMes = f"{VERSION} (c)&(p) 2022-{str(datetime.datetime.now())[0:4]} by Viktor 'MushroomOFF' Gribov"
logger(f'[{SCRIPT_NAME}]', logMes)

# Prompt user for a path, if nothing is entered, use the original root folder
rootFolder = input(f'Type me some path (Enter -> {originalRootFolder}): ')
if rootFolder == '':
    rootFolder = originalRootFolder

# Loop through all files in the root folder
for checkFile in os.listdir(rootFolder):
    # Check if the file is a JPG
    if checkFile[len(checkFile)-3:] == 'jpg':
        errorMark = 0
        textBlockCount = checkFile.count(' - ')

        # If the file name contains 2 or 3 ' - ' split the file name into band, album, and other parts
        if textBlockCount == 2:
            nBand, nAlbum, nOther = checkFile.split(' - ')
        elif textBlockCount == 3:
            nBand, nAlbum, nType, nOther = checkFile.split(' - ')
            nAlbum = nAlbum + ' [' + nType + ']'
        else:
            errorMark = 1
            logMes = f'ERROR: {checkFile}'
            logger(f'[{SCRIPT_NAME}]', logMes)  
            print(f'{logMes}\n')

        # If no errors were found, proceed with the file renaming and moving
        if errorMark == 0:
            nBandLetter = str(nBand[0]).upper()

            # If the band name starts with a Cyrillic letter, set the band letter to 'Русское'
            if ord(nBandLetter) >= 1025 and ord(nBandLetter) <= 1105:
                nBandLetter = 'Русское'
            # If the band name starts with a non-alphabetical character, set the band letter to '0'
            elif ord(nBandLetter) < 65:
                nBandLetter = '0'

            nOutput = str(nOther[:4]) + ' ' + str(nAlbum) + '.jpg'
            nDirectory = os.path.join(rootFolder, nBandLetter, nBand)
            cFile = os.path.join(rootFolder, checkFile)
            nFile = os.path.join(nDirectory, nOutput)

            # If the directory does not exist, create it
            if not os.path.exists(nDirectory):
                os.makedirs(nDirectory)

            # Move the file to the new directory
            shutil.move(cFile, nFile)
            logMes = f'FILE: {checkFile} -> GOTO: {nBandLetter}/{nBand}/{nOutput}'
            logger(f'[{SCRIPT_NAME}]', logMes)  
            print(f'FILE: {checkFile}\nGOTO: {nBandLetter}/{nBand}/{nOutput}\n')

logMes = '[V] Done!'
logger(f'[{SCRIPT_NAME}]', logMes)
print(logMes)