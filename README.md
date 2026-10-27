# 🎵 AMR — Alternative & Metal Releases

Автоматизация для Telegram-канала и веб-страницы с музыкальными релизами:
сбор новых релизов из Apple Music, поиск ссылок на Яндекс.Музыке и Звуке,
скачивание обложек, локальная БД (SQLite) с JSON-бэкапами в Git и автодеплой
веб-страницы через **GitHub Actions** / **GitHub Pages**.

## 📁 Структура проекта

```text
mushroomoff.github.io/
├── .github/workflows/        # CI/CD: GitHub Actions (автоматизация в облаке)
│   ├── amr-weekly-update.yml # еженедельный сбор новых релизов (пятница)
│   ├── amr-zvym.yml          # ежедневный поиск ссылок Яндекс.Музыка / Звук
│   ├── amr-deploy.yml        # деплой website/ на GitHub Pages
│   └── amr_manual-run.yml    # ручной запуск скриптов из вкладки Actions
├── scripts/                  # Python-скрипты автоматизации
│   ├── amr_functions.py      # общая библиотека (Telegram, логгер, БД, MarkdownV2)
│   ├── lookapp.py            # парсинг Apple Music по артистам -> таблица my_releases
│   ├── lookapp_errors.py     # проверка релизов с ошибками (только локально)
│   ├── new_releases.py       # подборки New Releases/Coming Soon из кураторских плейлистов Apple Music
│   ├── zvym_links.py         # поиск ссылок Яндекс.Музыка / Звук + репост в TG
│   ├── covers_downloader.py  # скачивание больших обложек (только локально)
│   ├── covers_renamer.py     # переименование файлов обложек (только локально)
│   ├── db_backup.py          # экспорт таблиц SQLite -> JSON
│   ├── db_sync.py            # синхронизация JSON -> SQLite (dry-run + подтверждение)
│   ├── server.py             # локальный веб-сервер разработки (http://localhost:8000)
│   └── requirements.txt      # зависимости Python
├── databases/
│   ├── music_releases.db     # основная база данных (SQLite)
│   └── backups/              # JSON-бэкапы таблиц artists, my_releases
├── website/                  # публика GitHub Pages (index.html, coming_soon.html, JSON)
├── status.log                # журнал работы скриптов
└── .env                      # секреты (НЕ в git, создаётся локально, см. SETUP.md)
```

## 🚀 Быстрый старт

| Что нужно | Где описано |
|---|---|
| Установка Python, зависимостей, `.env` | [SETUP.md](SETUP.md#-1-подготовка-рабочего-места) |
| Запуск скриптов локально на своём ПК | [SETUP.md](SETUP.md#-3-запуск-скриптов-локально) |
| Настройка GitHub Actions и Secrets | [SETUP.md](SETUP.md#-4-github-actions--автоматизация-в-облаке) |
| Деплой сайта на GitHub Pages | [SETUP.md](SETUP.md#-5-деплой-сайта-github-pages) |
| Локальный сервер разработки `server.py` | [SETUP.md](SETUP.md#-6-локальный-сервер-разработки-serverpy) |
| Частые проблемы (FAQ) | [SETUP.md](SETUP.md#-7-частые-проблемы-faq) |

Коротко:

```bash
git clone https://github.com/MushroomOFF/mushroomoff.github.io.git
cd mushroomoff.github.io
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r scripts/requirements.txt
cp .env.example .env    # и заполнить значения (см. SETUP.md)
python scripts/db_backup.py                       # проверка, что всё работает
```

## 🧰 Скрипты (`scripts/`)

| Скрипт | Назначение | Где запускается | Интерактивный |
|---|---|---|---|
| `amr_functions.py` | Общая библиотека: отправка в Telegram (MarkdownV2), логгер в `status.log`, `db_backup()` | импортируется, не запускается напрямую | — |
| `lookapp.py` | Обход артистов из таблицы `artists`, поиск альбомов в Apple Music (us/ru/jp), новые записи в `my_releases` | GitHub Actions (Fri) + локально | да (локально) |
| `new_releases.py` | Сбор New Releases и Coming Soon из кураторских плейлистов Apple Music, посты в канал TG | GitHub Actions (Fri) + локально | частично |
| `zvym_links.py` | Поиск ссылок на релизы в Яндекс.Музыке и Звуке, обновление БД и репост сообщений в TG | GitHub Actions (ежедневно) + локально | нет |
| `lookapp_errors.py` | Разбор релизов со статусом ERROR (проверка существования/обложек) | только локально | да ([Enter]) |
| `covers_downloader.py` | Скачивание больших обложек (6000×6000) в папку `covers/` | только локально | нет |
| `covers_renamer.py` | Переименование обложек в формат `Исполнитель - Альбом - Год.jpg` | только локально | да (ввод пути) |
| `db_backup.py` | Экспорт таблиц SQLite → JSON (`databases/backups/`, `website/*.json`) | локально / вызывается скриптами | нет |
| `db_sync.py` | Обратная синхронизация JSON → SQLite: dry-run, затем подтверждение `y/n` | только локально | да (y/n) |
| `server.py` | Локальный HTTP-сервер разработки: страница + API правок (`/api/update_my_type`), очередь отправки в TG | только локально | нет (Ctrl+C — стоп) |

Большинство скриптов определяют окружение по переменной `GITHUB_ACTIONS`:
в **Local**-режиме читают `.env` и работают с путями внутри репозитория,
в **GitHub**-режиме переменные приходят из workflow, а данные коммитятся обратно в репозиторий.

## 🤖 GitHub Actions (`.github/workflows/`)

| Workflow | Файл | Триггер | Что делает |
|---|---|---|---|
| AMR Weekly Update | `amr-weekly-update.yml` | cron: пятница 04:00 UTC | `lookapp.py` → `new_releases.py` → коммит изменений → push в `main` |
| AMR YM & Zvuk Lookup | `amr-zvym.yml` | cron: ежедневно 06:09 UTC | `zvym_links.py` → коммит изменений → push в `main` |
| AMR Deploy Webpage | `amr-deploy.yml` | push в `main` (изменения в `website/**`) или вручную | деплой папки `website/` на GitHub Pages |
| Manual run | `amr_manual-run.yml` | только вручную (workflow_dispatch) | установка зависимостей + запуск выбранного скрипта без коммита |

Push-изменений из Actions автоматически триггерит `amr-deploy.yml`,
если обновился `website/` — сайт на GitHub Pages всегда актуален.

## 🔐 Секреты и переменные окружения

Локально — файл `.env` в корне (в `.gitignore`), в GitHub — repository secrets.
Полное описание получения каждого токена — в [SETUP.md](SETUP.md).

| Переменная (`.env`) | Secret (GitHub) | Обязательная | Описание |
|---|---|---|---|
| `tg_token` | `TG_TOKEN` | ✅ | токен Telegram-бота |
| `tg_channel_id` | `TG_CHANNEL_ID` | ✅ | ID канала (бот — админ с правом публикации в темы) |
| `tg_logger_id` | `TG_LOGGER_ID` | ✅ | ID служебного чата/темы для логов |
| `ym_token` | `YM_TOKEN` | ✅ | токен Яндекс.Музыки (для `new_releases.py`, `zvym_links.py`) |
| `zv_token` | `ZV_TOKEN` | ✅ | токен Звука (без него скрипты работают в анонимном режиме) |
| `admin_token` | — | только `server.py` | пароль для входа в режим редактирования на локальной странице |

## 🌐 Сайт

* Живой сайт: папка `website/` деплоится на GitHub Pages workflow `amr-deploy.yml`.
* Данные: `website/new_releases.json` и `website/soon_releases.json` — экспортируются
  скриптами из SQLite и коммитятся Actions.
* Вне `localhost` страница умеет читать/писать JSON напрямую через GitHub API
  (нужен токен с правами на репозиторий — вводится на странице).

## 🛠 Требования

* **Python 3.12+** (CI использует 3.14; код требует ≥3.12 из-за f-строк с вложенными кавычками)
* Git
* Зависимости: `requests`, `pandas`, `python-dotenv`, `yandex-music` (`scripts/requirements.txt`)

## 📄 Лицензия

Личный некоммерческий проект. Все права на собранные данные принадлежат их правообладателям.
