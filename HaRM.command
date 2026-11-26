#!/bin/bash
# === НАСТРОЙКИ ПУТЕЙ ===
BASE_DIR="/Users/mushroomoff/Yandex.Disk.localized/GitHub/mushroomoff.github.io"
SCRIPTS_DIR="$BASE_DIR/scripts"

# === МЕНЮ ===
# "" или строка, начинающаяся с "---" = разделитель/заголовок.
# Курсор на них не встаёт, номер им не выдаётся.
OPTIONS=(
    "--- HaRM Website -------------"
    "HaRM Website"
    ""
    "--- Weekly Update ------------"
    "New Releases"
    "LookApp"
    "LookApp Errors"
    "Zvuk & Yandex.Music Lookup"
    ""
    "--- Covers -------------------"
    "Covers Downloader"
    "Covers Renamer"
    ""
    "--- Database -----------------"
    "Database Sync"
    "Database Backup"    
    ""
    "Exit"
)

# Строка терминала, где начинается первый элемент (заголовок = 4 строки)
FIRST_ITEM_ROW=5
# Символы хоткеев по порядку: 1..9, 0, дальше буквы (если пунктов > 10)
HOTKEYS="1234567890abcdefghijklmnopqrstuvwxyz"
ACTION_EXIT=9   # номер действия "Exit" в case ниже

# Служебные массивы (заполняет build_menu)
NAV=()          # индексы выбираемых пунктов
ITEM_KEY=()     # индекс OPTIONS -> символ клавиши
ITEM_ACTION=()  # индекс OPTIONS -> номер действия (-1 у разделителя)

# === ФУНКЦИИ ===
full_clear() {
    printf '\033[2J\033[3J\033[H'
}

resize_term() {
    local rows=$1 cols=$2
    [ -n "$rows" ] && [ -n "$cols" ] && printf '\033[8;%s;%st' "$rows" "$cols"
}

close_terminal() {
    tput cnorm
    osascript -e 'tell application "Terminal" to close front window'
    exit 0
}

# Разделитель? (пустая строка или "---...")
is_separator() {
    [[ -z "$1" || "$1" == ---* ]]
}

# Разбор OPTIONS: нумеруем только выбираемые пункты
build_menu() {
    local i n=0
    NAV=(); ITEM_KEY=(); ITEM_ACTION=()
    for i in "${!OPTIONS[@]}"; do
        if is_separator "${OPTIONS[$i]}"; then
            ITEM_KEY[$i]=""
            ITEM_ACTION[$i]=-1
        else
            NAV+=("$i")
            ITEM_KEY[$i]="${HOTKEYS:$n:1}"
            ITEM_ACTION[$i]=$n
            n=$((n + 1))
        fi
    done
}

# Шаг по выбираемым пунктам: $1 — текущий индекс, $2 — +1/-1. Результат в REPLY
move_selection() {
    local cur=$1 dir=$2 count=${#NAV[@]} i p=0
        for ((i=0; i<count; i++)); do
            [ "${NAV[$i]}" -eq "$cur" ] && { p=$i; break; }
        done
        REPLY=${NAV[$(( (p + dir + count) % count ))]}
    }

# Поиск пункта по хоткею. Результат в REPLY, return 1 если нет такого
find_by_key() {
    local i
    for i in "${NAV[@]}"; do
        if [ "${ITEM_KEY[$i]}" = "$1" ]; then REPLY=$i; return 0; fi
    done
    return 1
}

# Перерисовка ОДНОГО элемента на нужной строке
redraw_item_at() {
    local row=$1 idx=$2 is_selected=$3
    local text="${OPTIONS[$idx]}"
    printf '\033[%d;1H' "$row"
    printf '\033[K'
    if is_separator "$text"; then
        # заголовок группы — серым, без номера и без курсора
        [ -n "$text" ] && printf '\033[90m    %s\033[0m' "$text"
    elif [ "$is_selected" -eq 1 ]; then
        printf '\033[7m  > [%s] %s\033[0m' "${ITEM_KEY[$idx]}" "$text"
    else
        printf '    [%s] %s' "${ITEM_KEY[$idx]}" "$text"
    fi
    printf '\033[1000;1H'
}

init_menu() {
    local selected=$1 i sel
    resize_term $(( ${#OPTIONS[@]} + 8 )) 45   # чтобы всё влезло и строки не «уехали»
    full_clear
    tput civis
    echo "╔═════════════════════════════════════╗"
    echo "║              HaRM Menu              ║"
    echo "╚═════════════════════════════════════╝"
    echo ""
    for i in "${!OPTIONS[@]}"; do
        sel=0
        [ "$i" -eq "$selected" ] && sel=1
        redraw_item_at $((FIRST_ITEM_ROW + i)) "$i" "$sel"
    done
    printf '\033[%d;1H\033[K' $((FIRST_ITEM_ROW + ${#OPTIONS[@]} + 1))
        printf '↑↓ / Цифры: навигация | Enter: выбор'
        printf '\033[1000;1H'
    }

# === ОСНОВНАЯ ФУНКЦИЯ ===
main() {
    build_menu
    local selected=${NAV[0]}          # стартуем с первого «живого» пункта
    local old_selected action
    trap 'close_terminal' INT TERM EXIT

    init_menu "$selected"

    while true; do
        IFS= read -rsn1 key
        case $key in
        $'\x1b')
            IFS= read -rsn1 -t 1 key2
            if [[ $key2 == "[" || $key2 == "O" ]]; then
                IFS= read -rsn1 -t 1 key3
                if [[ $key3 == "A" || $key3 == "B" ]]; then
                    old_selected=$selected
                    if [[ $key3 == "A" ]]; then
                        move_selection "$selected" -1
                    else
                        move_selection "$selected" 1
                    fi
                    selected=$REPLY
                    if [ "$selected" -ne "$old_selected" ]; then
                        redraw_item_at $((FIRST_ITEM_ROW + old_selected)) "$old_selected" 0
                        redraw_item_at $((FIRST_ITEM_ROW + selected)) "$selected" 1
                    fi
                fi
            fi
            ;;
        [0-9a-z])
            if find_by_key "$key"; then
                old_selected=$selected
                selected=$REPLY
                if [ "$selected" -ne "$old_selected" ]; then
                    redraw_item_at $((FIRST_ITEM_ROW + old_selected)) "$old_selected" 0
                    redraw_item_at $((FIRST_ITEM_ROW + selected)) "$selected" 1
                fi
            fi
            ;;
        "" | $'\r' | $'\n')
            action=${ITEM_ACTION[$selected]}
            tput cnorm
            full_clear
            case $action in
                0) resize_term 60 110
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
                1) resize_term 60 95
                echo "Запуск New Releases..."
                python3 "$SCRIPTS_DIR/new_releases.py" ;;
                2) resize_term 60 95
                echo "Запуск LookApp..."
                python3 "$SCRIPTS_DIR/lookapp.py" ;;
                3) resize_term 60 95
                echo "Запуск LookApp Errors..."
                python3 "$SCRIPTS_DIR/lookapp_errors.py" ;;
                4) resize_term 45 95
                echo "Запуск Zvuk & Yandex.Music Lookup..."
                python3 "$SCRIPTS_DIR/zvym_links.py" ;;
                5) resize_term 60 160
                echo "Запуск Covers Downloader..."
                python3 "$SCRIPTS_DIR/covers_downloader.py" ;;
                6) echo "Запуск Covers Renamer..."
                python3 "$SCRIPTS_DIR/covers_renamer.py" ;;
                7) resize_term 50 95
                echo "Запуск Database Sync..."
                cd "$BASE_DIR" || exit
                python3 "$SCRIPTS_DIR/db_sync.py" --db databases/music_releases.db --json-dir databases/backups website ;;
                8) resize_term 25 110
                echo "Запуск Database Backup..."
                python3 "$SCRIPTS_DIR/db_backup.py" ;; 
                9) close_terminal ;;
            esac
            if [ "$action" -ne "$ACTION_EXIT" ]; then
                echo ""
                echo "Нажмите любую клавишу для возврата в меню..."
                read -rsn1
                init_menu "$selected"
            fi
            ;;
        esac
    done
}

main