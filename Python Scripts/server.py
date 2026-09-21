#!/usr/bin/env python3
"""
Сервер для страницы музыкальных релизов (локальная разработка).
Изменение типа релиза: JSON + SQLite + очередь отправки в Telegram.
Очередь хранит только row_id (UNIQUE): новая правка заменяет неотправленную
старую, текст сообщения строится в момент отправки из актуального JSON.

Запуск:  python "Python Scripts/server.py"
Адрес:   http://localhost:8000/index.html
"""
import http.server
import socketserver
import json
import os
import sys
import sqlite3
import threading
import urllib.parse
import requests
from dotenv import load_dotenv
from datetime import datetime
import amr_functions as amr

PORT = 8000
ROOT_FOLDER = '/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io/'
load_dotenv(os.path.join(ROOT_FOLDER, '.env'))
WEBSITE_DIR = os.path.join(ROOT_FOLDER, 'Website/')
HTML_FILE = 'index.html'
JSON_FILE = os.path.join(WEBSITE_DIR, 'new_releases.json')
DB_FOLDER = os.path.join(ROOT_FOLDER, 'Databases/')
DB_FILE = os.path.join(DB_FOLDER, 'music_releases.db')

TOKEN = os.environ.get('tg_token')
CHAT_ID = os.environ.get('tg_channel_id')
LOGGER_ID = os.environ.get('tg_logger_id')
ADMIN_TOKEN = os.environ.get('admin_token')

STOP_EVENT = threading.Event()


# ====== SQLite ======
def db_connect():
    return sqlite3.connect(DB_FILE)


def init_tg_queue():
    """Создаёт очередь; при необходимости мигрирует со старой схемы (с колонкой text)."""
    conn = db_connect()
    cols = [r[1] for r in conn.execute('PRAGMA table_info(tg_queue)')]
    if cols and 'row_id' not in cols:
        conn.execute('DROP TABLE tg_queue')
        cols = []
    if not cols:
        conn.execute('''CREATE TABLE tg_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            row_id INTEGER NOT NULL UNIQUE,
            attempts INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    elif 'text' in cols:
        conn.execute('''CREATE TABLE tg_queue_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            row_id INTEGER NOT NULL UNIQUE,
            attempts INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        conn.execute('''INSERT OR IGNORE INTO tg_queue_new (row_id, attempts, created_at)
                        SELECT row_id, attempts, created_at FROM tg_queue''')
        conn.execute('DROP TABLE tg_queue')
        conn.execute('ALTER TABLE tg_queue_new RENAME TO tg_queue')
    conn.commit()
    conn.close()


def update_empty_new_release(row_id, new_type):
    """Обновить вид релиза в БД"""
    try:
        conn = db_connect()
        conn.execute('UPDATE new_releases SET my_type = ? WHERE row_id = ?', (new_type, row_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'Error updating release type in {row_id}: {e}')
        return False


def update_tg_message_id(row_id, tg_message_id):
    conn = db_connect()
    conn.execute('UPDATE new_releases SET tg_message_id = ? WHERE row_id = ?', (tg_message_id, row_id))
    conn.commit()
    conn.close()


def enqueue_tg(row_id):
    """Дедупликация: если для row_id уже есть неотправленная запись — она заменяется новой."""
    conn = db_connect()
    conn.execute('''INSERT OR REPLACE INTO tg_queue (row_id, attempts, created_at)
                    VALUES (?, 0, CURRENT_TIMESTAMP)''', (row_id,))
    conn.commit()
    conn.close()


# ====== Чтение актуального состояния релиза ======
def get_field(r, name):
    """Ключи в JSON могут быть с пробелом на конце — учитываем оба варианта."""
    if name in r:
        return r[name]


def find_release_in_json(row_id):
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            for r in json.load(f):
                if str(get_field(r, 'row_id')) == str(row_id):
                    return r
    except Exception as e:
        print(f'⚠️ Не удалось прочитать JSON для row_id={row_id}: {e}')
    return None


def telegram_available(timeout=5):
    try:
        r = requests.get(f'https://api.telegram.org/bot{TOKEN}/getMe', timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def build_tg_text(artist, album, album_link, album_link_ym, album_link_zv):
    artist = (artist or '').replace('&amp;', '&')
    album = (album or '').replace('&amp;', '&')
    embed_link = (album_link or '').replace('://', '://embed.')
    text = f'*{artist}* \\- [{album}]({embed_link})'
    text += f'\n\n\U0001F3B5 [Apple Music]({album_link})'
    if album_link_ym:
        text += f'\n\U0001F4A5 [Яндекс\\.Музыка]({album_link_ym})'
    if album_link_zv:
        text += f'\n\U0001F50A [Звук]({album_link_zv})'
    return text


# ====== Фоновый отправитель очереди ======
def tg_sender_loop(stop_event):
    print('📨 TG sender thread запущен')
    while not stop_event.is_set():
        delay = 5
        try:
            conn = db_connect()
            row = conn.execute('SELECT id, row_id, attempts FROM tg_queue ORDER BY id LIMIT 1').fetchone()
            conn.close()

            if row:
                qid, row_id, attempts = row
                release = find_release_in_json(row_id)
                current_type = (get_field(release, 'my_type') or '') if release else ''

                if release is None or current_type not in ('v', 'd', 'o'):
                    # Релиз удалён или больше не требует анонса — убираем из очереди
                    conn = db_connect()
                    conn.execute('DELETE FROM tg_queue WHERE id = ?', (qid,))
                    conn.commit()
                    conn.close()
                    print(f'🗑 row_id={row_id}: удалено из очереди без отправки')
                    continue

                topic = 'Top Releases' if current_type == 'o' else 'New Releases'
                image_url = (get_field(release, 'cover_link') or '') \
                    .replace('296x296bb.webp', '632x632bb.webp') \
                    .replace('296x296bf.webp', '632x632bf.webp')
                text = build_tg_text(
                    get_field(release, 'artist'), get_field(release, 'album'),
                    get_field(release, 'album_link'), get_field(release, 'album_link_ym'),
                    get_field(release, 'album_link_zv'))

                msg_id = amr.send_message(text, TOKEN, CHAT_ID, image_url, topic)
                conn = db_connect()
                if msg_id:
                    conn.execute('UPDATE new_releases SET tg_message_id = ? WHERE row_id = ?',
                                 (msg_id, row_id))
                    conn.execute('DELETE FROM tg_queue WHERE id = ?', (qid,))
                    conn.commit()
                    amr.db_backup(DB_FILE)
                    print(f'✅ TG отправлено для row_id={row_id} (message_id={msg_id})')
                else:
                    conn.execute('UPDATE tg_queue SET attempts = ? WHERE id = ?',
                                 (attempts + 1, qid))
                    conn.commit()
                    delay = min(600, 15 * (2 ** min(attempts, 4)))
                    print(f'⏳ TG недоступен, повтор через {delay} c (попытка {attempts + 1})')
                conn.close()
        except Exception as e:
            print(f'⚠️ Ошибка цикла отправки TG: {e}')
            delay = 30
        stop_event.wait(delay)


# ====== HTTP ======
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEBSITE_DIR, **kwargs)

    def do_GET(self):
        if self.path in ('/', ''):
            self.send_response(302)
            self.send_header('Location', f'/{HTML_FILE}')
            self.end_headers()
            return
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/verify':
            self.handle_verify()
        elif parsed.path == '/api/update_my_type':
            self.handle_update_my_type()
        elif parsed.path == '/api/tg_check':
            self.handle_tg_check()
        else:
            self.send_error(404)

    def handle_verify(self):
        try:
            data = self.read_body()
            ok = data.get('token') == ADMIN_TOKEN

            self.send_json(
                {'success': ok, 'message': 'OK' if ok else 'Неверный токен'},
                200 if ok else 403
            )
        except Exception as e:
            self.send_json({'success': False, 'message': str(e)}, 400)

    def handle_tg_check(self):
        try:
            conn = db_connect()
            pending = conn.execute('SELECT COUNT(*) FROM tg_queue').fetchone()[0]
            conn.close()
        except Exception:
            pending = 0
        self.send_json({
            'success': True,
            'telegram_available': telegram_available(),
            'tg_pending': pending
        })

    def handle_update_my_type(self):
        try:
            data = self.read_body()
            token = data.get('token', '')
            row_id = data.get('row_id')
            new_type = data.get('new_type', '').strip()

            if token != ADMIN_TOKEN:
                self.send_json({'success': False, 'message': 'Неверный токен'}, 403)
                return
            if row_id is None or new_type not in ('v', 'd', 'o', 'x'):
                self.send_json({'success': False, 'message': 'Некорректные данные'}, 400)
                return
            if not os.path.exists(JSON_FILE):
                self.send_json({'success': False, 'message': 'JSON не найден'}, 404)
                return

            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                releases = json.load(f)

            updated = 0
            old_type = None
            tg_queued = False

            for r in releases:
                rid = r.get('row_id')
                if str(rid) == str(row_id):
                    old_type = r.get('my_type')
                    r['my_type'] = new_type
                    update_empty_new_release(row_id, new_type)

                    # В очередь попадает только row_id; дубликаты заменяются
                    if new_type in ('v', 'd', 'o'):
                        enqueue_tg(row_id)
                        tg_queued = True
                    updated += 1

            if updated == 0:
                self.send_json({'success': False, 'message': f'row_id={row_id} не найден'}, 404)
                return

            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(releases, f, ensure_ascii=False, indent=4)

            ts = datetime.now().strftime('%H:%M:%S')
            print(f"[{ts}] ✅ row_id={row_id}: '{old_type}' → '{new_type}' "
                  f"({updated} записей, в очереди TG: {tg_queued})")

            self.send_json({
                'success': True,
                'message': f'Обновлено: {updated} записей',
                'old_type': old_type,
                'new_type': new_type,
                'tg_queued': tg_queued
            })
        except Exception as e:
            self.send_json({'success': False, 'message': f'Ошибка: {e}'}, 500)

    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length).decode('utf-8'))

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.address_string()} - {fmt % args}")


def main():
    print("=" * 60)
    print("🎵 AMR Server — локальная разработка")
    print("=" * 60)
    if not os.path.isdir(WEBSITE_DIR):
        print("❌ ОШИБКА: папка 'Website' не найдена!")
        sys.exit(1)
    print(f"📁 Сайт:    {WEBSITE_DIR}")
    print(f"📄 JSON:    {JSON_FILE}")
    print(f"🗄  БД:      {DB_FILE}")
    print(f"🌐 Страница: http://localhost:{PORT}/{HTML_FILE}")
    print("=" * 60)

    init_tg_queue()
    threading.Thread(target=tg_sender_loop, args=(STOP_EVENT,), daemon=True).start()

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            STOP_EVENT.set()
            print("\n🛑 Остановлено.")


if __name__ == '__main__':
    main()