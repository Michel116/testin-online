# Online — мессенджер в стиле Telegram

Desktop-приложение на Python/PySide6 с русским интерфейсом:
- авторизация по логину и паролю;
- регистрация по логину и паролю;
- список диалогов;
- отправка и хранение сообщений в SQLite;
- современный плавный интерфейс в розово-фиолетовой палитре Online (Telegram-like layout).

## Как пользователю скачать готовый `.exe` с GitHub

### Вариант 1: через Releases (рекомендуется)
1. Перейдите во вкладку **Releases** вашего репозитория на GitHub.
2. Откройте последний релиз.
3. В блоке **Assets** скачайте файл `online.exe`.

### Вариант 2: через Actions Artifacts
1. Перейдите во вкладку **Actions**.
2. Откройте последний успешный запуск workflow **Build online.exe (Windows)**.
3. В секции **Artifacts** скачайте `online-windows-exe`.

## Быстрый запуск из исходников
```bash
python main.py
```


## Требования к Python для Windows-сборки
- Для локальной сборки `online.exe` используйте Python **3.10 / 3.11 / 3.12**.
- Python 3.14 может не поддерживаться частью зависимостей (`PySide6`/`PyInstaller`) на момент установки.
- Обновлённый `build_windows_exe.bat` автоматически пытается выбрать 3.12 -> 3.11 -> 3.10.
- Если скрипт пишет `No suitable Python runtime found`, выполните `py -0p` и проверьте, что установлен Python 3.10/3.11/3.12.

## Локальная сборка `online.exe` на Windows
Запустите:

```bat
build_windows_exe.bat
```

Результат:

```text
dist\online.exe
```

## Важно (исправления для Windows)
- `build_windows_exe.bat` сделан в ASCII и без русских команд, чтобы не было ошибок вида
  `is not recognized as an internal or external command` из-за кодировки `.bat`.
- База данных хранится в пользовательской папке:
  - Windows: `%APPDATA%\Online\online.db`
  - Linux/macOS: `~/.online/online.db`
  Это убирает проблемы запуска из папок без прав на запись.
- При критической ошибке приложение сохраняет лог:
  - Windows: `%APPDATA%\Online\online_error.log`

## Примечание
- Чтобы проверить переписку, создайте минимум два аккаунта.
