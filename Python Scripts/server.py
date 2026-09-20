#!/usr/bin/env python3
"""
Сервер для страницы музыкальных релизов (только для локальной разработки).
В продакшене (на GitHub Pages) вместо него работает GitHub API — см. releases.js.

Структура проекта (server.py может лежать в любой подпапке):
    проект/
    ├── Python Scripts/
    │   └── server.py          <- этот файл
    └── Website/
        ├── index.html
        ├── releases.css
        ├── releases.js
        └── new_releases.json

Запуск:  python "Python Scripts/server.py"   (из корня проекта или откуда угодно)
Адрес:   http://localhost:8000/index.html
"""
import http.server
import socketserver
import json
import os
import sys
import urllib.parse
from datetime import datetime

PORT = 8000


def find_website_dir():
    """Ищет папку 'Website', поднимаясь вверх от папки с этим файлом."""
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(2):  # поднимаемся не более чем на 6 уровней
        candidate = os.path.join(d, 'Website')
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:  # дошли до корня файловой системы
            break
        d = parent
    return None


WEBSITE_DIR = find_website_dir()
HTML_FILE = 'index.html'                                   # относительно WEBSITE_DIR
JSON_FILE = os.path.join(WEBSITE_DIR, 'new_releases.json') if WEBSITE_DIR else None

ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'amr_admin_2026')


class Handler(http.server.SimpleHTTPRequestHandler):
    # Раздаём статику из найденной папки Website
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
            for r in releases:
                rid = r.get('row_id') if 'row_id' in r else r.get('row_id ')
                if str(rid) == str(row_id):
                    old_type = r.get('my_type') or r.get('my_type ')
                    # Обновляем оба варианта ключа (из-за бага с пробелами в ключах)
                    if 'my_type' in r:
                        r['my_type'] = new_type
                    if 'my_type ' in r:
                        r['my_type '] = new_type
                    updated += 1

            if updated == 0:
                self.send_json({'success': False, 'message': f'row_id={row_id} не найден'}, 404)
                return

            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(releases, f, ensure_ascii=False, indent=1)

            ts = datetime.now().strftime('%H:%M:%S')
            print(f"[{ts}] ✅ row_id={row_id}: '{old_type}' → '{new_type}' ({updated} записей)")

            self.send_json({
                'success': True,
                'message': f'Обновлено: {updated} записей',
                'old_type': old_type,
                'new_type': new_type
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

    if not WEBSITE_DIR:
        print("❌ ОШИБКА: папка 'Website' не найдена!")
        print("   Скрипт искал её, поднимаясь вверх от своей папки.")
        print("   Проверьте, что папка 'Website' есть в проекте.")
        sys.exit(1)

    print(f"📁 Сайт:    {WEBSITE_DIR}")
    print(f"📄 JSON:    {JSON_FILE}")
    print(f"🌐 Страница: http://localhost:{PORT}/{HTML_FILE}")
    print(f"🔐 Токен:   {ADMIN_TOKEN}")
    print("=" * 60)

    if not os.path.exists(JSON_FILE):
        print(f"❌ ВНИМАНИЕ: {JSON_FILE} не найден!")

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Остановлено.")


if __name__ == '__main__':
    main()