#!/bin/bash
# Запуск Telegram бота Kato World

# Загрузка .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Запуск бота
python python/telegram_bot.py
