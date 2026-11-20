#!/usr/bin/env bash
cd "$(dirname "$0")"

echo "=== UzbStarsBuy Botni Ishga Tushirish ==="

if command -v pm2 >/dev/null 2>&1; then
    echo "PM2 orqali ishga tushirilmoqda..."
    pm2 start ecosystem.config.js
    pm2 save
    echo "Bot muvaffaqiyatli ishga tushirildi!"
    pm2 status uzbstarsbuy-bot
else
    echo "Python orqali orqa fonda (nohup) ishga tushirilmoqda..."
    nohup python3 bot.py > bot.log 2>&1 &
    nohup python3 web_server.py > web.log 2>&1 &
    echo "Bot PID: $!"
fi
