# Online — мессенджер в стиле Telegram

Desktop-приложение на Python/Tkinter с русским интерфейсом:
- авторизация по логину и паролю;
- регистрация по логину и паролю;
- список диалогов;
- отправка и хранение сообщений в SQLite;
- тёмный интерфейс в стиле Telegram.

## Как пользователю скачать готовый `.exe` с GitHub

### Вариант 1: через Releases (рекомендуется)
1. Перейдите во вкладку **Releases** вашего репозитория на GitHub.
2. Откройте последний релиз.
3. В блоке **Assets** скачайте файл `online.exe`.

> `online.exe` автоматически прикрепляется к релизу через GitHub Actions workflow
> `.github/workflows/windows-build.yml`.

### Вариант 2: через Actions Artifacts
1. Перейдите во вкладку **Actions**.
2. Откройте последний успешный запуск workflow **Build online.exe (Windows)**.
3. В секции **Artifacts** скачайте `online-windows-exe`.

## Быстрый запуск из исходников
```bash
python main.py
```

## Локальная сборка `online.exe` на Windows
На Windows запустите файл:

```bat
build_windows_exe.bat
```

После завершения получите:

```text
dist\online.exe
```

## Примечание
- Данные сохраняются в локальную базу `online.db` рядом с приложением.
- Чтобы проверить переписку, создайте минимум два аккаунта.
