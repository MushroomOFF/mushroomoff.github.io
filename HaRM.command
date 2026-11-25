#!/bin/bash

# === НАСТРОЙКИ ПУТЕЙ ===
BASE_DIR="/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io"
SCRIPTS_DIR="$BASE_DIR/scripts"

# === МЕНЮ (глобальный массив) ===
OPTIONS=(
    "New Releases"
    "LookApp"
    "LookApp Errors"
    "Zvuk & Yandex.Music Lookup"
    "Covers Downloader"
    "Covers Renamer"
    "Database Backup"
    "Database Sync"
    "Open Website"
    "Exit"
)

# Строка в терминале, где начинается первый пункт (1-индексация для ANSI)
FIRST_ITEM_ROW=5

# === ФУНКЦИИ ===

# Полная очистка экрана + scrollback + курсор в начало
full_clear() {
    printf '\033[2J\033[3J\033[H'
}

# Изменение размера окна терминала
resize_term() {
    local rows=$1 cols=$2
    [ -n "$rows" ] && [ -n "$cols" ] && printf '\033[8;%s;%st' "$rows" "$cols"
}

# Закрытие окна терминала
close_terminal() {
    tput cnorm
    osascript -e 'tell application "Terminal" to close front window'
    exit 0
}

# Перерисовка ОДНОГО пункта по его индексу на нужной строке терминала
redraw_item_at() {
    local row=$1
    local idx=$2
    local is_selected=$3
    local num=$((idx + 1))
    [ $num -eq 10 ] && num=0
    local text="${OPTIONS[$idx]}"
    
    # Перемещаем курсор в начало нужной строки
    printf '\033[%d;1H' "$row"
    # Очищаем строку
    printf '\033[K'
    # Печатаем пункт с выделением или без
    if [ "$is_selected" -eq 1 ]; then
        printf '\033[7m  > [%d] %s\033[0m' "$num" "$text"
    else
        printf '    [%d] %s' "$num" "$text"
    fi
    # Уводим курсор в самый низ, чтобы не мешал
    printf '\033[1000;1H'
}

# Первичная полная отрисовка меню (вызывается при старте и после возврата из скриптов)
init_menu() {
    local selected=$1
    full_clear
    tput civis  # Скрываем курсор
    
    echo "╔═════════════════════════════════════╗"
    echo "║              HaRM Menu              ║"
    echo "╚═════════════════════════════════════╝"
    echo ""
    
    for i in "${!OPTIONS[@]}"; do
        if [ "$i" -eq "$selected" ]; then
            echo -e "\033[7m  > [$((i+1 == 10 ? 0 : i+1))] ${OPTIONS[$i]}\033[0m"
        else
            echo "    [$((i+1 == 10 ? 0 : i+1))] ${OPTIONS[$i]}"
        fi
    done
    echo ""
    echo "↑↓ / Цифры 0-9: навигация | Enter: выбор"
    
    # Уводим курсор вниз, чтобы он не мешал
    printf '\033[1000;1H'
}

# === ОСНОВНАЯ ФУНКЦИЯ ===
main() {
    local selected=0
    local max_options=9
    local old_selected
    
    trap 'close_terminal' INT TERM EXIT
    
    # Первичная отрисовка
    init_menu $selected
    
    while true; do
        IFS= read -rsn1 key
        
        case $key in
            $'\x1b')
                # Стрелки
                IFS= read -rsn1 -t 1 key2
                if [[ $key2 == "[" || $key2 == "O" ]]; then
                    IFS= read -rsn1 -t 1 key3
                    if [[ $key3 == "A" || $key3 == "B" ]]; then
                        old_selected=$selected
                        if [[ $key3 == "A" ]]; then
                            ((selected--))
                            [ $selected -lt 0 ] && selected=$max_options
                        else
                            ((selected++))
                            [ $selected -gt $max_options ] && selected=0
                        fi
                        
                        # Обновляем только 2 строки, без полной перерисовки
                        if [ $selected -ne $old_selected ]; then
                            redraw_item_at $((FIRST_ITEM_ROW + old_selected)) $old_selected 0
                            redraw_item_at $((FIRST_ITEM_ROW + selected)) $selected 1
                        fi
                    fi
                fi
                ;;
            [1-8]|9|0)
                # Цифры
                old_selected=$selected
                case $key in
                    [1-8]) selected=$((key - 1)) ;;
                    9)     selected=8 ;;
                    0)     selected=9 ;;
                esac
                
                # Обновляем только 2 строки
                if [ $selected -ne $old_selected ]; then
                    redraw_item_at $((FIRST_ITEM_ROW + old_selected)) $old_selected 0
                    redraw_item_at $((FIRST_ITEM_ROW + selected)) $selected 1
                fi
                ;;
            "" | $'\r' | $'\n')
                # Enter
                tput cnorm  # Показываем курсор для вывода Python
                full_clear  # Полная очистка перед запуском скрипта
                
                case $selected in
                    0) resize_term 60 95
                       echo "Запуск New Releases..."
                       python3 "$SCRIPTS_DIR/new_releases.py" ;;
                       # open "$BASE_DIR/Website/index.html" ;;
                    1) resize_term 60 95
                       echo "Запуск LookApp..."
                       python3 "$SCRIPTS_DIR/lookapp.py" ;;
                    2) resize_term 60 95
                       echo "Запуск LookApp Errors..."
                       python3 "$SCRIPTS_DIR/lookapp_errors.py" ;;
                    3) resize_term 45 95
                       echo "Запуск Zvuk & Yandex.Music Lookup..."
                       python3 "$SCRIPTS_DIR/zvym_links.py" ;;
                    4) resize_term 60 160
                       echo "Запуск Covers Downloader..."
                       python3 "$SCRIPTS_DIR/covers_downloader.py" ;;
                    5) echo "Запуск Covers Renamer..."
                       python3 "$SCRIPTS_DIR/covers_renamer.py" ;;
                    6) resize_term 25 110
                       echo "Запуск Database Backup..."
                       python3 "$SCRIPTS_DIR/db_backup.py" ;;
                    7) resize_term 50 95
                       echo "Запуск Database Sync..."
                       cd "$BASE_DIR" || exit
                       python3 "$SCRIPTS_DIR/db_sync.py" --db databases/music_releases.db --json-dir databases/backups website ;;
                    8) resize_term 60 110
                       echo "Освобождение порта 8000 (если занят)..."
                       kill -9 $(lsof -ti :8000) 2>/dev/null
                       echo "Запуск Website..."
                       cd "$SCRIPTS_DIR" || exit
                       python3 server.py &
                       SERVER_PID=$!
                       sleep 1
                       open 'http://localhost:8000/index.html'
                       echo "Сервер запущен (PID: $SERVER_PID)."
                       echo "Нажмите любую клавишу для остановки сервера и возврата в меню..."
                       read -rsn1
                       kill $SERVER_PID 2>/dev/null
                       echo "Сервер остановлен." ;;
                    9) close_terminal ;;
                esac
                
                # Возврат в меню (если не Exit)
                if [ $selected -ne 9 ]; then
                    echo ""
                    echo "Нажмите любую клавишу для возврата в меню..."
                    read -rsn1
                    init_menu $selected  # Полная перерисовка после скрипта
                fi
                ;;
        esac
    done
}

# Запуск
main