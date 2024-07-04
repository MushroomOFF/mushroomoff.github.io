import os
import shutil

originalRootFolder = '/Users/viktorgribov/Downloads/_Фото/_COVERS/_BIG'
rootFolder = input(f'Type me some path (Enter -> {originalRootFolder}): ')
if rootFolder == '':
    rootFolder = originalRootFolder
for checkFile in os.listdir(rootFolder):
    if checkFile[len(checkFile)-3:] == 'jpg':
        errorMark = 0
        textBlockCount = checkFile.count(' - ')
        if textBlockCount == 2:
            nBand, nAlbum, nOther = checkFile.split(' - ')
        elif textBlockCount == 3:
            nBand, nAlbum, nType, nOther = checkFile.split(' - ')
            nAlbum = nAlbum + ' [' + nType + ']'
        else:
            errorMark = 1
            print(f'ERROR: {checkFile}\n')
        if errorMark == 0:
            nBandLetter = str(nBand[0]).upper()
            if ord(nBandLetter) >= 1025 and ord(nBandLetter) <= 1105:
                nBandLetter = 'Русское'
            elif ord(nBandLetter) < 65:
                nBandLetter = '0'
            nOutput = str(nOther[:4]) + ' ' + str(nAlbum) + '.jpg'
            nDirectory = os.path.join(rootFolder, nBandLetter, nBand)
            cFile = os.path.join(rootFolder, checkFile)
            nFile = os.path.join(nDirectory, nOutput)
            if not os.path.exists(nDirectory):
                os.makedirs(nDirectory)
            shutil.move(cFile, nFile)
            print(f'FILE: {checkFile}\nGOTO: {nBandLetter}/{nBand}/{nOutput}\n')

print('Done!')