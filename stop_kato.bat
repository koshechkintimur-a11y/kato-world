@echo off
chcp 65001 >nul
title Kato World — остановить
echo Останавливаю мозг и Telegram-бота...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='python.exe' or name='pythonw.exe'\" | Where-Object { $_.CommandLine -match 'brain_server\.py|telegram_bot\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo Готово. Zapret не трогаю (нужен для других сайтов).
pause
