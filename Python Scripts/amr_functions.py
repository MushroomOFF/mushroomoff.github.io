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


def mdv2(text):
    """
    Экранирует спецсимволы для Telegram MarkdownV2.
    Уже экранированные символы не экранируются повторно
    """
    SPECIAL = '_*[]()~`>#+-=|{}.!'
    
    def escape_special(s):
        """Экранирует спецсимволы, кроме уже экранированных"""
        result = []
        for i, c in enumerate(s):
            # Не экранируем, если перед символом уже есть обратный слэш
            if c in SPECIAL and (i == 0 or s[i-1] != '\\'):
                result.append('\\' + c)
            else:
                result.append(c)
        return ''.join(result)
    
    result = []
    i = 0
    
    is_bold_link = False

    while i < len(text):
        # Code block: `...` — сохраняем как есть, без экранирования
        if text[i] == '`':
            end = text.find('`', i + 1)
            if end != -1:
                result.append(text[i:end+1])
                i = end + 1
                continue
        
        # Link: [text](url) — экранируем контент внутри, но не структурные скобки
        if text[i] == '[':
            bracket_end = text.find(']', i + 1)
            if bracket_end != -1 and bracket_end + 1 < len(text) and text[bracket_end+1] == '(':
                paren_end = text.find(')', bracket_end + 2)
                if paren_end != -1:
                    link_text = text[i+1:bracket_end]
                    url = text[bracket_end+2:paren_end]
                    if is_bold_link:
                        result.append(f'*[{escape_special(link_text)}]({escape_special(url)})*')
                        is_bold_link = False
                        i = paren_end + 2
                    else:
                        result.append(f'[{escape_special(link_text)}]({escape_special(url)})')
                        i = paren_end + 1
                    continue
        
        # Bold/italic/strike: *...*, _..._, ~...~ — экранируем контент внутри, учитываем наличие ссылки внутри
        if text[i] in '*_~':
            marker = text[i]
            end = text.find(marker, i + 1)
            if end != -1:
                content = text[i+1:end]
                if content[0] != '[' and content[len(content)-1] != ')':
                    result.append(f'{marker}{escape_special(content)}{marker}')
                    i = end + 1
                else:
                    is_bold_link = True
                    i += 1
                continue
        
        # Обычный символ: экранируем, если это спецсимвол и он ещё не экранирован
        c = text[i]
        if c in SPECIAL and (i == 0 or text[i-1] != '\\'):
            result.append('\\' + c)
        else:
            result.append(c)
        i += 1
    
    final_text = ''.join(result)
    
    return final_text


def send_message(text, token, chat_id, image, topic):
    """Отправка сообщения в Telegram с обработкой ошибок и отладочным выводом"""
    
    # Экранируем текст перед отправкой
    escaped_text = mdv2(text)

    send_method = 'sendMessage'
    data_arguments = {
        "text": escaped_text,
        "chat_id": chat_id,
        "parse_mode": 'MarkdownV2'
    }
    if image:
        send_method = 'sendPhoto'
        data_arguments.update({"photo": image, "caption": escaped_text})
    if topic:
        data_arguments.update({"message_thread_id": THREAD_ID_DICT[topic]})
    url = f"https://api.telegram.org/bot{token}/{send_method}"

    try:
        response = requests.post(url, data=data_arguments)
        json_response = json.loads(response.text)
        # Если API вернул ошибку, ключа 'result' не будет — вызовется KeyError
        return json_response['result']['message_id']
        
    except KeyError:
        # Telegram вернул ответ без ключа 'result' — сообщение не отправлено
        # 🔍 ОТЛАДКА: выводим полный ответ API для диагностики
        print(f"🔍 Telegram API error response: {response.text}")
        print("❌ Ошибка отправки сообщения")
        
    except TypeError:
        # На случай, если json_response не является словарём
        print(f"🔍 Telegram API unexpected response: {response.text}")
        print("❌ Ошибка отправки сообщения (некорректный формат ответа)")
        
    except requests.exceptions.RequestException as e:
        # Ошибка сети, таймаут, недоступность API
        print(f"❌ Ошибка сети при отправке: {e}")
        
    except json.JSONDecodeError as e:
        # Ответ не является валидным JSON
        print(f"❌ Ошибка парсинга JSON-ответа: {e}")
        print(f"🔍 Сырой ответ: {response.text if 'response' in locals() else 'N/A'}")    

    print(f"📄 Отправляемый текст: {escaped_text}")
    print('')
    # 🔽 Попытка отправить уведомление об ошибке
    try:
        logger_chat_id = os.environ['tg_logger_id']
        error_msg = "Ошибка: сообщение отправить не удалось!"
        error_url = f"https://api.telegram.org/bot{token}/sendMessage"
        # Отправляем как plain text (без parse_mode), чтобы избежать циклических ошибок парсинга
        error_data = {"chat_id": logger_chat_id, "text": error_msg}
        requests.post(error_url, data=error_data, timeout=10)
    except Exception as notif_err:
        print(f"⚠️ Не удалось отправить уведомление об ошибке")

    return None


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


