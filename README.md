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

### Вариант 2: через Actions Artifacts
1. Перейдите во вкладку **Actions**.
2. Откройте последний успешный запуск workflow **Build online.exe (Windows)**.
3. В секции **Artifacts** скачайте `online-windows-exe`.

## Быстрый запуск из исходников
```bash
python main.py
```

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

## Как загрузить изменения в GitHub (если вы новичок)
Ошибка `fatal: not a git repository` означает, что команда `git push` запущена не в папке проекта.

1. Откройте PowerShell.
2. Перейдите в папку проекта (пример):

```powershell
cd C:\Users\<ВАШЕ_ИМЯ>\Downloads\testin-online
```

3. Проверьте, что вы в Git-репозитории:

```powershell
git status
```

Если команда показывает статус файлов, всё хорошо.

4. Выполните push в `main`:

```powershell
git push origin work:main
```

Если нужен push через токен, используйте его только временно и после этого удалите из переменной:

```powershell
$env:GITHUB_TOKEN="<ВАШ_ТОКЕН>"
git push https://Michel116:$env:GITHUB_TOKEN@github.com/Michel116/testin-online work:main
Remove-Item Env:\GITHUB_TOKEN
```

⚠️ Если токен уже был отправлен в чат/скриншот, обязательно удалите старый токен и создайте новый в GitHub Settings → Developer settings → Personal access tokens.
