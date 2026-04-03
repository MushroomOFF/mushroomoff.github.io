""" 
# How to import from the same directory:
import amr_functions as amr

# functions usage example:
amr.print_name(SCRIPT_NAME, VERSION)

amr.mdv2(text_line)

amr.send_message(text, token, chat_id, image, topic)

amr.logger(log_line, LOG_FILE, SCRIPT_NAME, *args)
"""

import datetime
import json
import os
import requests

THREAD_ID_DICT = {'New Updates': 6, 'Top Releases': 10, 'Coming Soon': 3, 'New Releases': 2, 'Next Week Releases': 80, 'General': 0}

def print_name(script_name, version):
    print_line = f'{script_name} v.{version}'
    print_line_len = 30
    if len(print_line) > 28:
        print_line_len = len(print_line) + 2
    print(f"\n{'':{'='}^{print_line_len}}")
    print(f"{'\033[1m'}{'Alternative & Metal Releases':{' '}^{print_line_len}}{'\033[0m'}")
    print(f"{print_line:{' '}^{print_line_len}}")
    print(f"{'':{'='}^{print_line_len}}\n")


def mdv2(text_line):
    """Replacing Markdown v2 unused characters 
    in Telegram message text line 
    """
    symbols_to_replace = """'_*[]",()~`>#+-=|{}.!"""
    for symbol in symbols_to_replace:
        text_line = text_line.replace(symbol, f'\\{symbol}')
    return text_line


def send_message(text, token, chat_id, image, topic):
    """Sending Telegram message""" 
    send_method = 'sendMessage'
    data_arguments = {"text": text, "chat_id": chat_id, "parse_mode": 'MarkdownV2'}
    if image:
        send_method = 'sendPhoto'
        data_arguments.update({"photo": image})
    if topic:
        data_arguments.update({"message_thread_id": THREAD_ID_DICT[topic]})
    method = f"https://api.telegram.org/bot{token}/{send_method}"
    response = requests.post(method, data=data_arguments)
    json_response = json.loads(response.text)
    result_message_id = json_response['result']['message_id']   
    return result_message_id


def logger(log_line, log_file, script_name, *args):
    """Writing log line into log file
    * For GitHub Actions:
      - add +3 hours to datetime
    * For Local scripts:
      - print() without '▲','▼' and leading spaces
      - additional conditions for print() without logging
      
      example - begin message:  logger(f'▲ v.{VERSION} [{ENV}]', 'noprint') # Begin
      example - normal message: logger(f'ERROR: {check_file}')
      example - end message:    logger(f'▼ DONE') # End
    """
    if log_line[0] not in ['▲', '▼']:
        log_line = f'  {log_line}'
    with open(log_file, 'r+') as log_file:
        log_file_content = log_file.read()
        log_file.seek(0, 0)
        log_date = datetime.datetime.now()
        if os.getenv("GITHUB_ACTIONS") == "true":
            log_date = log_date + datetime.timedelta(hours=3)
        log_file.write(f'{log_date.strftime('%Y-%m-%d %H:%M:%S')} [{script_name}] {log_line.rstrip('\r\n')}\n{log_file_content}')
    # print() for Local scripts only, if there's no 'noprint' parameter
    if not os.getenv("GITHUB_ACTIONS"):
        if 'noprint' not in args:
            print(log_line[2:])


