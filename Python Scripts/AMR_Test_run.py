import os
import platform

def main():
    # Проверяем, запущено ли в GitHub Actions
    if os.getenv("GITHUB_ACTIONS") == "true":
        print("Я онлайн")
    # Проверяем, запущено ли локально на macOS
    elif platform.system() == "Darwin":
        print("Я оффлайн")
    else:
        print("Я запущен где-то ещё")

if __name__ == "__main__":
    main()
