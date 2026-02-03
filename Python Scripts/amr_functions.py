import datetime
import json
import os
import requests

# functions
def print_name(script_name, version):
    print_line = f'{script_name} v.{version}'
    print_line_len = 30
    if len(print_line) > 28:
        print_line_len = len(print_line) + 2
    print(f"\n{'':{'='}^{print_line_len}}")
    print(f"{'\033[1m'}{'Alternative & Metal Releases':{' '}^{print_line_len}}{'\033[0m'}")
    print(f"{print_line:{' '}^{print_line_len}}")
    print(f"{'':{'='}^{print_line_len}}\n")
    
def logger(log_line, log_file, script_name, *args):
    """Writing log line into log file
    * For GitHub Actions:
      - add +3 hours to datetime
      - no print()
    * For Local scripts:
      - print() without '▲','▼' and leading spaces
      - additional conditions for print() without logging
      - arguments is optional
      
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
        # print() for Local scripts only
        # Additional conditions for print() without logging
        # 'noprint' parameter if no need to print() 
        if not os.getenv("GITHUB_ACTIONS"):
            if 'covers_renamer' in args:
                log_line = f'{log_line.replace(' >>> ', '\n')}\n'
            if 'noprint' not in args:
                print(log_line[2:])

def replace_symbols_markdown_v2(text_line):
    """Replacing Markdown v2 unused characters 
    in Telegram message text line 
    """
    symbols_to_replace = """'_*[]",()~`>#+-=|{}.!"""
    for symbol in symbols_to_replace:
        text_line = text_line.replace(symbol, f'\\{symbol}')
    return text_line

def send_message(topic, text, token, chat_id):
    """Sending Telegram message""" 
    thread_id_dict = {'New Updates': 6, 'Top Releases': 10, 'Coming Soon': 3, 'New Releases': 2, 'Next Week Releases': 80}
    method = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(method, data={"message_thread_id": thread_id_dict[topic], "chat_id": chat_id, "parse_mode": 'MarkdownV2', "text": text})
    json_response = json.loads(response.text)
    result_message_id = json_response['result']['message_id']   
    return result_message_id

def send_photo(topic, text, image_url, token, chat_id):
    """Sending Telegram message with photo"""
    thread_id_dict = {'New Updates': 6, 'Top Releases': 10, 'Coming Soon': 3, 'New Releases': 2, 'Next Week Releases': 80}
    method = f"https://api.telegram.org/bot{token}/sendPhoto"
    response = requests.post(method, data={"message_thread_id": thread_id_dict[topic], "chat_id": chat_id, "photo": image_url, "parse_mode": 'MarkdownV2', "caption": text})
    json_response = json.loads(response.text)
    result_message_id = json_response['result']['message_id']    
    return result_message_id

