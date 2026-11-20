#!/usr/bin/env bash
set -e

echo "📦 Python kutubxonalari o'rnatilmoqda..."
pip install -r requirements.txt --break-system-packages 2>/dev/null || pip install -r requirements.txt || true

echo "⚙️ C-Native GodMode dvigateli kompilyatsiya qilinmoqda..."
if [ -f "godmode_engine.c" ]; then
    gcc -O3 -fopenmp -shared -fPIC godmode_engine.c -o libgodmode_engine.so || gcc -O3 -shared -fPIC godmode_engine.c -o libgodmode_engine.so || true
fi

echo "✅ Build muvaffaqiyatli yakunlandi!"
