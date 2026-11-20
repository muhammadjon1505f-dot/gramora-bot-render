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

# Gramora Shashka Bot + UzbStarsBuy Bot + Web Visualizer (Unified Master Process)
while true; do
    echo "🚀 [$(date '+%Y-%m-%d %H:%M:%S')] Multi-Bot Master Runner ishga tushirilmoqda..."
    python3 gramora_auto_runner.py || true
    echo "⚠️ [$(date '+%Y-%m-%d %H:%M:%S')] Runner to'xtadi. 5 soniyadan so'ng qayta tiklanadi..."
    sleep 5
done
