import os
import shutil

originalRootFolder = '/Users/viktorgribov/Downloads/_Фото/_COVERS/_BIG'
rootFolder = input(f'Type me some path (Enter -> {originalRootFolder}): ')
if rootFolder == '':
    rootFolder = originalRootFolder
for checkFile in os.listdir(rootFolder):
    if checkFile[len(checkFile)-3:] == 'jpg':
        nBand, nAlbum, nOther = checkFile.split(' - ')
        nBandLetter = str(nBand[0])
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