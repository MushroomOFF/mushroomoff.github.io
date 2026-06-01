import datetime
import os
import pandas as pd
import requests
import amr_functions as amr

# ================= CONSTANTS & VARIABLES =================
SCRIPT_NAME = "Covers Downloader"
VERSION = "2.026.06"
# ENV = 'Local'
# if os.getenv("GITHUB_ACTIONS") == "true":
#     ENV = 'GitHub'

ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
DB_FOLDER = 'Databases/'
COVERS_FOLDER = os.path.join(ROOT_FOLDER, 'Covers/Fresh Covers to Check/')
RELEASES_DB = os.path.join(ROOT_FOLDER, DB_FOLDER, 'AMR_releases_DB.csv')
# LOG_FILE = os.path.join(ROOT_FOLDER, 'status.log')


# ================= FUNCTIONS =================
def clean_folder_name(text: str) -> str:
    forbidden = set('()/:.')
    result = []
    # Проходим по исходному тексту, чтобы соседи не "съехали" во время обработки
    for i, char in enumerate(text):
        if char in forbidden:
            left = text[i-1] if i > 0 else None
            right = text[i+1] if i < len(text) - 1 else None
            
            # Заменяем на пробел только если символ окружён не-пробелами с обеих сторон
            if left is not None and right is not None and left != ' ' and right != ' ':
                result.append(' ')
            # В противном случае (начало/конец строки или рядом уже есть пробел) символ просто удаляется
        else:
            result.append(char)
    # Собираем строку, схлопываем множественные пробелы в один и убираем пробелы по краям
    return ' '.join(''.join(result).split())


def is_jp_chars(text: str):
    # Проверяем каждый символ по его Unicode-коду
    if any(0x3040 <= ord(ch) <= 0x309F or  # Хирагана
           0x30A0 <= ord(ch) <= 0x30FF or  # Катакана
           0x4E00 <= ord(ch) <= 0x9FFF     # Кандзи (CJK Unified Ideographs)
           for ch in text):
        return True
    return False


def replace_symbols(text_line):
    """Replacing unused characters in file names and folder paths"""
    symbols_to_replace = '\\/*:?<>|`"'
    for symbol in symbols_to_replace:
        text_line = text_line.replace(symbol, '_')
    return text_line


def image_download(file_name, folder, link):
    """Image downloading"""
    file_name = replace_symbols(file_name)
    folder = replace_symbols(folder)
    folder_path = os.path.join(COVERS_FOLDER, folder)

    os.makedirs(folder_path, exist_ok=True)

    response = requests.get(link)
    if response.status_code == 200:
        with open(os.path.join(folder_path, f"{file_name}.jpg"), "wb") as file:
            file.write(response.content)
    else:
        with open(os.path.join(folder_path, f"{file_name}.txt"), "wb") as file:
            file.write(response.content)


def main():
    amr.print_name(SCRIPT_NAME, VERSION)

    session = requests.Session() 
    session.headers.update({
        'Referer': 'https://itunes.apple.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
    })

    while True:
        releases_df = pd.read_csv(RELEASES_DB, sep=";")
        
        cover_to_download = releases_df[releases_df['downloadedCover'].isna()].head(1)
        if cover_to_download.empty:
            print("\nВсё скачано, качать нечего...")
            break
        
        row_index = cover_to_download.index[0]
        # row_index -> позиция строки в таблице без учета шапки и с порядковым номером первой строки данных - 0
        # row_index + 2 -> позиция строки в текстовом файле с учетом шапки и порядковым номером первой строки данных - 2  
        # row_index + 2 -> только для вывода    

        # Убираем из имени Исполнителя символы, которые недопустимы в имени папки ('/', ':', '(', ')', '.' в конце)
        artist_folder_name = clean_folder_name(cover_to_download['mainArtist'].loc[row_index])
        # Проверяем на наличие японских символов. Если находим, мяеняем на "неочищенное" mainArtist
        non_JP_artist_name = cover_to_download['artistName'].loc[row_index]
        if is_jp_chars(non_JP_artist_name):
            non_JP_artist_name = cover_to_download['mainArtist'].loc[row_index]

        image_download(
            f"{non_JP_artist_name} - "
            f"{cover_to_download['collectionName'].loc[row_index][:100]} - "
            f"{cover_to_download['releaseDate'].loc[row_index]} [{row_index + 2}]",
            artist_folder_name,
            cover_to_download['artworkUrlD'].loc[row_index]
        )
        
        print(f"ID: {row_index + 2}. {cover_to_download['mainArtist'].loc[row_index]} | "
              f"{cover_to_download['artistName'].loc[row_index]} - "
              f"{cover_to_download['collectionName'].loc[row_index]} - "
              f"{cover_to_download['releaseDate'].loc[row_index]}. "
              f"(Covers left: {releases_df['downloadedCover'].isna().sum() - 1})")
        
        releases_df.at[row_index, 'downloadedCover'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        releases_df.to_csv(RELEASES_DB, sep=';', index=False)

    print("\nDONE")


if __name__ == "__main__":
    main()