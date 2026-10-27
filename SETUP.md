# ⚙️ Инструкция по установке, настройке и запуску

Документ описывает два способа запуска проекта **AMR**:

1. **Локально на ПК** — все скрипты, локальный сервер разработки `server.py`.
2. **GitHub Actions** — автоматический запуск по расписанию и деплой сайта на GitHub Pages.

> Оглавление: [1. Подготовка](#-1-подготовка-рабочего-места) →
> [2. Секреты `.env`](#-2-настройка-секретов-файл-env) →
> [3. Локальный запуск](#-3-запуск-скриптов-локально) →
> [4. GitHub Actions](#-4-github-actions--автоматизация-в-облаке) →
> [5. GitHub Pages](#-5-деплой-сайта-github-pages) →
> [6. server.py](#-6-локальный-сервер-разработки-serverpy) →
> [7. FAQ](#-7-частые-проблемы-faq)

---

## 📋 0. Требования

| Компонент | Версия | Примечание |
|---|---|---|
| Python | **3.12+** (рекомендуется 3.12–3.14) | код использует вложенные кавычки в f-строках (PEP 701), на 3.10/3.11 будет SyntaxError |
| Git | любая современная | |
| ОС | macOS / Linux / Windows | пути в скриптах строятся относительно корня репозитория |
| Telegram-бот | — | админ канала с тематами, право публикации |
| Аккаунты | Яндекс.Музыка, Звук | токены для `new_releases.py` и `zvym_links.py` |

---

## 💻 1. Подготовка рабочего места

### 1.1. Установка Python

* **macOS:** `brew install python@3.12` (или новее)
* **Ubuntu/Debian:** `sudo apt install python3 python3-venv`
* **Windows:** скачать установщик с [python.org](https://www.python.org/downloads/)
  и отметить галочку **«Add Python to PATH»**.

Проверка:

```bash
python3 --version   # Windows: py --version
```

### 1.2. Клонирование репозитория

```bash
git clone https://github.com/MushroomOFF/mushroomoff.github.io.git
cd mushroomoff.github.io
```

### 1.3. Виртуальное окружение и зависимости

```bash
python3 -m venv .venv

# macOS / Linux:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd):
.venv\Scripts\activate.bat

pip install --upgrade pip
pip install -r scripts/requirements.txt
```

Содержимое `scripts/requirements.txt`: `requests`, `pandas`, `python-dotenv`, `yandex-music`.

> **Совет:** работайте из корня репозитория (`cd mushroomoff.github.io`) — все скрипты сами
> вычисляют пути к `databases/`, `website/` и `.env` относительно своего расположения.

### 1.4. Проверка установки

```bash
python scripts/db_backup.py
```

Скрипт должен вывести список экспортированных таблиц в JSON — значит Python,
зависимости и база данных `databases/music_releases.db` в порядке.

---

## 🔑 2. Настройка секретов (файл `.env`)

Локальные скрипты читают секреты из файла **`.env`** в корне репозитория
(через `python-dotenv`). Файл добавлен в `.gitignore` — **никогда не коммитьте его**.

Создайте `.env` по образцу `.env.example`:

```bash
cp .env.example .env    # Windows: copy .env.example .env
```

Шаблон `.env`:

```ini
# Telegram
tg_token=1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
tg_channel_id=-1001234567890
tg_logger_id=-1001234567890

# Стриминги
ym_token=ymusic.v1.xxxxxxxxxxxxxxxx
zv_token=eyJhbGciOiJIUzI1NiIsInR5cCI6...

# Только для server.py (пароль режима редактирования на localhost)
admin_token=придуманный-пароль
```

### Как получить значения

| Переменная | Как получить |
|---|---|
| `tg_token` | [@BotFather](https://t.me/BotFather) → `/newbot` → выданный токен |
| `tg_channel_id` | Добавить бота в канал **администратором** (с правом публикации в темы), затем открыть `https://api.telegram.org/bot<Токен>/getUpdates` и найти `chat.id` канала (для каналов начинается с `-100…`). Можно переслать сообщение из канала боту-логгеру и посмотреть ID в логах |
| `tg_logger_id` | ID служебного чата/темы, куда бот пишет технические логи (получается так же через `getUpdates`) |
| `ym_token` | Авторизоваться на [music.yandex.ru](https://music.yandex.ru) → DevTools браузера (F12) → Application/Хранилище → Cookies → значение `ymex`/токена из заголовков API; либо через сервис [oauth.yandex.ru](https://oauth.yandex.ru) (приложение → токен с доступом к Музыке). Используется библиотекой `yandex-music` (`Client(YM_TOKEN).init()`) |
| `zv_token` | Авторизоваться на [zvuk.com](https://zvuk.com) → DevTools (F12) → Network → любой запрос к API → скопировать значение токена из заголовка `Authorization`. Без токена `zvym_links.py` работает в анонимном режиме (ограниченно) и сообщает об этом в лог |
| `admin_token` | Придумать самостоятельно; нужен только `server.py` для входа в режим правок на странице |

⚠️ Токены действуют ограниченное время — при ошибках авторизации (401) обновите их.

---

## ▶️ 3. Запуск скриптов локально

Все команды — из корня репозитория, при активированном виртуальном окружении.

### 3.1. `lookapp.py` — поиск новых релизов артистов в Apple Music

```bash
python scripts/lookapp.py
```

Интерактивно запрашивает:
* страны проверки: `Enter` = us+ru+jp, `2` = us+ru, `jp` = только jp;
* группу артистов: `Enter` = группы 2 и 1, `2`/`1` = только группа, `0` = все;
* после прохода — `[Enter]` продолжить с того же места или ввести что-то, чтобы начать заново.

Результат: новые строки в таблице `new_releases` БД + отчёт в лог-чат Telegram.

### 3.2. `new_releases.py` — подборки New Releases / Coming Soon

```bash
python scripts/new_releases.py
```

Собирает релизы из кураторских плейлистов Apple Music (Metal, Hard Rock, RU-версии,
Coming Soon), обновляет БД, делает JSON-экспорт и публикует посты в канал Telegram.
В локальном режиме может попросить прокрутить страницу Safari до конца
(для получения полных списков через веб-вью).

### 3.3. `zvym_links.py` — ссылки на Яндекс.Музыку и Звук

```bash
python scripts/zvym_links.py
```

Неинтерактивный. Для релизов за последние 15 дней ищет отсутствующие ссылки YM/ZV,
обновляет БД и редактирует/репостит сообщения в канале. Итог — в лог-чат.

### 3.4. `lookapp_errors.py` — разбор ошибок LookApp

```bash
python scripts/lookapp_errors.py
```

Показывает релизы со статусом ERROR, проверяет их наличие/обложки в iTunes API.
Нажатие `[Enter]` — следующий шаг.

### 3.5. `covers_downloader.py` — скачивание обложек

```bash
python scripts/covers_downloader.py
```

Скачивает большие обложки для неотмеченных релизов в папку `covers/fresh-covers-to-check/`
(папка `covers/` в `.gitignore`) и отмечает прогресс в БД. Остановка — `Ctrl+C`.

### 3.6. `covers_renamer.py` — переименование обложек

```bash
python scripts/covers_renamer.py
```

Запрашивает путь к папке с большими обложками (по умолчанию — путь автора, введите свой)
и приводит имена файлов к виду `Исполнитель - Альбом - Год [ID в БД].jpg`, раскладывая по папкам.

### 3.7. `db_backup.py` — экспорт SQLite → JSON

```bash
python scripts/db_backup.py
```

Экспортирует таблицы `artists`, `my_releases` → `databases/backups/*.json`,
`new_releases`, `soon_releases` → `website/*.json`. Вызывается автоматически другими скриптами.

### 3.8. `db_sync.py` — синхронизация JSON → SQLite

```bash
# Сначала dry-run без изменений:
python scripts/db_sync.py --db databases/music_releases.db --json-dir databases/backups website --dry-run

# Полный цикл: dry-run -> вопрос -> применение (с бэкапом БД):
python scripts/db_sync.py --db databases/music_releases.db --json-dir databases/backups website
```

Правила: имя JSON = имя таблицы; сопоставление по `row_id`; изменённые ячейки обновляются,
новых строк в БД не удаляется. Применения происходит **только** после ответа `y`.

### 3.9. Рекомендуемый порядок «полной недели» локально

```bash
python scripts/lookapp.py            # нашли новые релизы
python scripts/new_releases.py       # собрали подборки, опубликовали
python scripts/zvym_links.py         # добавили ссылки YM/ZV
python scripts/covers_downloader.py  # докачали обложки
python scripts/lookapp_errors.py     # разобрали ошибки
python scripts/db_backup.py          # финальный экспорт JSON
git add -A && git commit -m "AMR local update" && git push   # синхронизация с репо
```

---

## 🤖 4. GitHub Actions — автоматизация в облаке

Расписание и запуск скриптов в облаке без вашего ПК. Код workflows лежит в
`.github/workflows/`, секреты берутся из настроек репозитория.

### 4.1. Добавление secrets в репозиторий

**Repository → Settings → Secrets and variables → Actions → New repository secret**

| Secret | Значение |
|---|---|
| `TG_TOKEN` | токен бота (как `tg_token` в `.env`) |
| `TG_CHANNEL_ID` | ID канала |
| `TG_LOGGER_ID` | ID чата логов |
| `YM_TOKEN` | токен Яндекс.Музыки |
| `ZV_TOKEN` | токен Звука |

### 4.2. Разрешения Actions (важно!)

**Settings → Actions → General → Workflow permissions → Read and write permissions** —
это нужно, чтобы workflow могли делать `git push` изменений в `main`
(используется `secrets.GITHUB_TOKEN`).

Также убедитесь, что в **Actions → General → Allow all actions and reusable workflows**
(или хотя бы разрешены `actions/*` и `ad-m/github-push-action`).

### 4.3. Список workflows

| Workflow | Файл | Запуск | Шаги |
|---|---|---|---|
| **AMR Weekly Update** | `amr-weekly-update.yml` | cron `0 4 * * 5` (пятница 04:00 UTC ≈ 07:00 МСК) | checkout → Python 3.14 → `pip install -r scripts/requirements.txt` → `python scripts/lookapp.py` → `python scripts/new_releases.py` → коммит всех изменений → push в `main` |
| **AMR YM & Zvuk Lookup** | `amr-zvym.yml` | cron `9 6 * * *` (ежедневно 06:09 UTC ≈ 09:09 МСК) | setup → `python scripts/zvym_links.py` → коммит → push в `main` |
| **AMR Deploy Webpage** | `amr-deploy.yml` | push в `main` с изменениями `website/**` + ручной запуск | configure-pages → upload artifact `./website` → deploy на GitHub Pages |
| **Manual run** | `amr_manual-run.yml` | только вручную (Actions → Manual run → Run workflow) | setup зависимостей → запуск скрипта **без** коммита и push |

Особенности:

* Скрипты определяют окружение по `GITHUB_ACTIONS=true` и работают в неинтерактивном
  GitHub-режиме (фиксированные страны `us, ru`, группа артистов `2`).
* Push из scheduled-workflow повторно триггерит `amr-deploy.yml` → сайт обновляется сам.
* Расписание cron GitHub может выполняться с задержкой в часы пик — это нормально.

### 4.4. Ручной запуск workflow

1. Вкладка **Actions** → выберите workflow (например, *Manual run*).
2. **Run workflow** → **Run workflow** (зелёная кнопка).
3. Следите за логом выполнения; результат скриптов придёт в Telegram-логгер.

---

## 🌐 5. Деплой сайта (GitHub Pages)

1. **Settings → Pages → Build and deployment → Source: GitHub Actions**
   (не «Deploy from a branch» — деплой делает workflow).
2. Workflow `amr-deploy.yml` публикует содержимое папки `website/`.
3. Адрес сайта: `https://<username>.github.io/<repo>/` (появится в логе шага
   *Deploy to GitHub Pages* и на вкладке Actions после первого успешного деплоя).
4. Обновление сайта происходит автоматически при любом push в `main`,
   затронувшем `website/` (в т.ч. из scheduled-workflows). Можно запустить и вручную:
   Actions → *AMR Deploy Webpage* → Run workflow.

---

## 🖥 6. Локальный сервер разработки (`server.py`)

Сервер раздаёт страницу из `website/` и поднимает API для правки типов релизов
(`my_type`) с записью в JSON + SQLite и очередью отправки сообщений в Telegram
(таблица `tg_queue` в БД).

```bash
python scripts/server.py
# открывать: http://localhost:8000/index.html
# остановка: Ctrl+C
```

Требуемые переменные в `.env`: `tg_token`, `tg_channel_id`, `tg_logger_id`, `admin_token`.

Как пользоваться:

1. Запустить сервер, открыть <http://localhost:8000/index.html>.
2. Войти в режим редактирования, указав `admin_token`.
3. Менять тип релиза — изменения сразу пишутся в `website/new_releases.json` и БД;
   фоновый поток отправляет обновлённое сообщение в Telegram (повторы с экспоненциальной
   паузой, очередь хранит только `row_id`, новая правка заменяет неотправленную).
4. После работы — сделать `db_backup.py`/коммит, чтобы JSON попал в репозиторий и на Pages.

> Вне `localhost` страница работает в «сетевом» режиме: читает и пишет JSON
> напрямую через GitHub API (нужен персональный токен с доступом к репозиторию,
> вводится на самой странице). Сервер `server.py` при этом не используется.

---

## ❓ 7. Частые проблемы (FAQ)

**`SyntaxError` при запуске скриптов**
У вас Python < 3.12. Проверьте `python3 --version`, создайте venv из новой версии.

**`ModuleNotFoundError: No module named 'dotenv'` (или `pandas`, `yandex_music`)**
Не установлены зависимости или не активировано виртуальное окружение:
`source .venv/bin/activate && pip install -r scripts/requirements.txt`.

**`ModuleNotFoundError: No module named 'amr_functions'`**
Запускайте скрипты из корня репозитория командой `python scripts/<имя>.py`
(не `python ./scripts/amr_functions.py` и не из папки `scripts`).

**«Message not sent! No TOKEN or CHAT_ID» / пустые посты**
`.env` не найден или не заполнен. Убедитесь, что файл лежит **в корне репозитория**
(рядом с папкой `scripts`), имена переменные совпадают (`tg_token`, а не `TG_TOKEN`).

**Telegram: 401 Unauthorized**
Бот удалён из администраторов канала/чата логов либо токен отозван — проверьте через @BotFather.

**Яндекс.Музыка: ошибка инициализации клиента / 403**
Протух `ym_token` — получите новый (см. п. 2). Библиотека `yandex-music` чувствительна
к смене API, иногда требуется обновление версии.

**Звук: «⚠️ Zvuk token disabled»**
`zv_token` не задан или протух — скрипты продолжат работу в анонимном режиме,
но часть функционала недоступна. Обновите токен (п. 2).

**Scheduled workflow не запустился**
Проверьте: workflow включён (Actions → ⋮ → *Enable workflow*), push был в ветку `main`,
cron указан в UTC. GitHub может задерживать запуски в периоды нагрузки.

**Workflow не может сделать push (Permission denied)**
Settings → Actions → General → Workflow permissions → **Read and write**.

**Нужно очистить прогресс/переписать БД из JSON**
Используйте `db_sync.py` сначала с `--dry-run`, затем с `--backup` (п. 3.8).
