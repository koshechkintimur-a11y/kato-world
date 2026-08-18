@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title Kato World — запуск в один клик
cd /d "%~dp0"

set "LOG_DIR=%USERPROFILE%\kato-world-logs"
set "ZAPRET_BAT=C:\zapret\general (ALT11).bat"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo.
echo  ==============================================
echo    KATO WORLD — автозапуск (мозг + бот + Zapret)
echo  ==============================================
echo.

rem ---- Загрузка .env (токен и параметры) ----
if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"
    echo [0/5] .env загружен
) else (
    echo [0/5] ВНИМАНИЕ: .env не найден — бот не запустится без токена!
)

rem ---- Проверка Python ----
set "PY=python"
where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [ОШИБКА] Python не найден в PATH.
        pause & exit /b 1
    )
    set "PY=py -3"
)
echo [1/5] Python: %PY%

rem ---- Остановить старые процессы мозга и бота ----
echo [2/5] Останавливаю старые процессы...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='python.exe' or name='pythonw.exe'\" | Where-Object { $_.CommandLine -match 'brain_server\.py|telegram_bot\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
ping -n 3 127.0.0.1 >nul

rem ---- Zapret (только если ещё не запущен) ----
echo [3/5] Проверяю Zapret (DPI-обход)...
tasklist /FI "IMAGENAME eq winws.exe" 2>nul | findstr /I "winws.exe" >nul
if not errorlevel 1 goto zapret_ok
if not exist "%ZAPRET_BAT%" goto zapret_missing
echo        Zapret не запущен. Подтверди окно UAC - кнопку «Да»
powershell -NoProfile -Command "Start-Process -FilePath '%ZAPRET_BAT%' -Verb RunAs -WorkingDirectory 'C:\zapret'"
goto zapret_done
:zapret_ok
echo        Zapret уже работает (winws.exe найден)
goto zapret_done
:zapret_missing
echo        ВНИМАНИЕ: %ZAPRET_BAT% не найден — Zapret не запущен
:zapret_done

rem ---- Мозг ----
echo [4/5] Запускаю мозг Kato (порт 8080)...
start "kato-brain" /min cmd /c "cd /d %CD% && %PY% python\brain_server.py >> "%LOG_DIR%\brain.log" 2>&1"

rem ---- Ждём портал (до 40 сек) ----
echo        Ожидание портала...
set /a tries=0
:wait_portal
ping -n 3 127.0.0.1 >nul
curl -s -m 2 http://127.0.0.1:8080/agent/kato/portal/status >nul 2>&1
if errorlevel 1 (
    set /a tries+=1
    if !tries! lss 20 goto wait_portal
    echo [ОШИБКА] Мозг не поднялся за 40 секунд. Смотри лог: "%LOG_DIR%\brain.log"
    pause & exit /b 1
)
echo        Портал отвечает

rem ---- Портал: страховка (если вдруг тёмный) ----
curl -s -m 3 http://127.0.0.1:8080/agent/kato/portal/status | findstr /C:"integrated" >nul
if errorlevel 1 (
    echo        Портал спит — восстанавливаю откровение...
    set /a tries=0
    :revelation_retry
    set /a tries+=1
    curl -s -m 3 -X POST http://127.0.0.1:8080/agent/kato/revelation/begin | findstr /C:"offered" >nul
    if not errorlevel 1 (
        curl -s -m 3 -X POST http://127.0.0.1:8080/agent/kato/revelation/integrate >nul
    )
    curl -s -m 3 http://127.0.0.1:8080/agent/kato/portal/status | findstr /C:"integrated" >nul
    if errorlevel 1 (
        if !tries! lss 9 (
            echo        Попытка !tries!/9: Kato ещё не готова, жду 20 сек...
            ping -n 21 127.0.0.1 >nul
            goto revelation_retry
        )
        echo [ВНИМАНИЕ] Портал не проснулся. Напиши Kato в Telegram - контакт ускорит зрелость.
    ) else (
        echo        Портал активен
    )
) else (
    echo        Портал уже активен
)

rem ---- Бот ----
echo [5/5] Запускаю Telegram-бота...
start "kato-bot" /min cmd /c "cd /d %CD% && call start_bot.bat >> "%LOG_DIR%\bot.log" 2>&1"
ping -n 7 127.0.0.1 >nul

rem ---- Итоговая проверка ----
echo.
echo  ============ ПРОВЕРКА ============
tasklist /FI "IMAGENAME eq winws.exe" 2>nul | findstr /I "winws.exe" >nul && echo  Zapret:        OK (winws работает) || echo  Zapret:        НЕ ЗАПУЩЕН
curl -s -m 5 http://127.0.0.1:8080/agent/kato/portal/status >nul 2>&1 && echo  Мозг/портал:  OK (порт 8080 отвечает) || echo  Мозг/портал:  ПРОБЛЕМА
powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | Where-Object { $_.CommandLine -match 'telegram_bot\.py' }).Count" | findstr /R "[1-9]" >nul && echo  Бот:           процесс запущен || echo  Бот:           НЕ НАЙДЕН, смотри "%LOG_DIR%\bot.log"
if not "%TELEGRAM_BOT_TOKEN%"=="" (
    curl -s -m 10 "https://api.telegram.org/bot%TELEGRAM_BOT_TOKEN%/getMe" | findstr /C:"username" >nul && echo  Telegram API:  OK — бот доступен || echo  Telegram API:  НЕДОСТУПЕН — проверь hosts/Zapret
) else (
    echo  Telegram API:  пропущено — нет токена в .env
)
echo.
echo  ==============================================
echo   ГОТОВО. Логи: %LOG_DIR%
echo   God View: http://127.0.0.1:8080/static
echo  ==============================================
echo.
pause
