import datetime
import requests
import pandas as pd


def fetch_album_data(url):
    response = requests.get(url)
    response.encoding = 'UTF-8'
    return response.text


def parse_album_data(data, start_marker, end_marker):
    start_idx = data.find(start_marker) + len(start_marker)
    end_idx = data.find(end_marker, start_idx)
    return data[start_idx:end_idx].strip()


def parse_date(date_str):
    return datetime.datetime.strptime(date_str, '%B %d, %Y')


def collect_albums(link, text, grad):
    # Implement your logic for collecting albums here
    pass


def coming_soon(link):
    # Implement your logic for handling "coming soon" albums here
    pass


def send_message(message):
    # Implement your logic for sending a message here
    pass


def main():
    print("\nAMR New Releases\n")
    print("##############################################################\n")
    
    message2send = f'\U0001F4C0 New Releases *{datetime.datetime.now():%Y-%m-%d}*\\:'
    messageCS = '\n\U0001F5D3\U0000FE0F Coming soon\\:'
    
    checkMesSnd = len(message2send)
    checkMesCS = len(messageCS)
    
    album_categories = [
        {
            "link": 'https://music.apple.com/us/room/993297832',
            "text": 'METAL - Classic. Black. Death. Speed. Prog. Sludge. Doom.',
            "grad": '#81BB98, #9AD292',
            "print_message": 'Metal [US]     - OK'
        },
        {
            "link": 'https://music.apple.com/us/room/1184023815',
            "text": 'HARD ROCK',
            "grad": '#EE702E, #F08933',
            "print_message": 'Hard Rock [US] - OK'
        },
        {
            "link": 'https://music.apple.com/ru/room/1118077423',
            "text": 'METAL - RU - Classic. Black. Death. Speed. Prog. Sludge. Doom.',
            "grad": '#81BB98, #9AD292',
            "print_message": 'Metal [RU]     - OK'
        },
        {
            "link": 'https://music.apple.com/ru/room/1532200949',
            "text": 'HARD ROCK - RU',
            "grad": '#EE702E, #F08933',
            "print_message": 'Hard Rock [RU] - OK'
        }
    ]
    
    for category in album_categories:
        collect_albums(category["link"], category["text"], category["grad"])
        print(category["print_message"])
    
    coming_soon('https://music.apple.com/us/room/993297822')
    print('Coming Soon   - OK')
    
    if checkMesSnd == len(message2send):
        message2send += '\n\U0001F937\U0001F3FB\u200D\u2642\U0000FE0F'
    if checkMesCS == len(messageCS):
        messageCS += '\n\U0001F937\U0001F3FB\u200D\u2642\U0000FE0F'
    
    send_message(message2send + '\n' + messageCS)
    print('[V] All Done!')


if __name__ == "__main__":
    main()
