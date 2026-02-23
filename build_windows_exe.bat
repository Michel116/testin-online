@echo off
chcp 65001 > nul

echo [1/3] Устанавливаем зависимости...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo [2/3] Собираем online.exe...
pyinstaller --noconfirm --onefile --windowed --name online main.py

echo [3/3] Готово.
echo Файл находится: dist\online.exe
pause
