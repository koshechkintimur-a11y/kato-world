@echo off
REM Запуск Telegram бота Kato World
REM Загружает .env и запускает python скрипт

REM Загрузка переменных из .env
for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
    if not "%%a"=="" (
        if not "%%a:~0,1"=="#" (
            set "%%a=%%b"
        )
    )
)

REM Запуск бота
python python\telegram_bot.py
