#!/usr/bin/env bash
export PYTHONUNBUFFERED=1
export PORT="${PORT:-10000}"
export HOST="${HOST:-0.0.0.0}"
export TZ="Asia/Tashkent"

echo "=================================================="
echo "👑 GRAMORA + UZB STARS BUY — RENDER MULTI-BOT 👑"
echo "PORT: $PORT | HOST: $HOST | TZ: $TZ"
echo "=================================================="

# C-Native dvigatel mavjudligini tekshirish
if [ ! -f "libgodmode_engine.so" ] && [ -f "godmode_engine.c" ]; then
    echo "⚙️ C-Native GodMode dvigateli kompilyatsiya qilinmoqda..."
    gcc -O3 -fopenmp -shared -fPIC godmode_engine.c -o libgodmode_engine.so || gcc -O3 -shared -fPIC godmode_engine.c -o libgodmode_engine.so || true
fi

# 1. UzbStarsBuy Bot (@uzstarsbuybot) fon jarayonida ishga tushirish
if [ -d "uzstarsbuy" ] && [ -f "uzstarsbuy/bot.py" ]; then
    (
        cd uzstarsbuy
        while true; do
            echo "⭐️ [$(date '+%Y-%m-%d %H:%M:%S')] UzbStarsBuy Bot (@uzstarsbuybot) ishga tushirilmoqda..."
            python3 bot.py || true
            echo "⚠️ [$(date '+%Y-%m-%d %H:%M:%S')] UzbStarsBuy Bot to'xtadi. 5 soniyadan so'ng qayta tiklanadi..."
            sleep 5
        done
    ) &
fi

# 2. Gramora Shashka Bot & Web Visualizer (Asosiy jarayon)
while true; do
    echo "👑 [$(date '+%Y-%m-%d %H:%M:%S')] Gramora Auto Runner ishga tushirilmoqda..."
    python3 gramora_auto_runner.py || true
    echo "⚠️ [$(date '+%Y-%m-%d %H:%M:%S')] Gramora to'xtadi. 5 soniyadan so'ng qayta tiklanadi..."
    sleep 5
done
