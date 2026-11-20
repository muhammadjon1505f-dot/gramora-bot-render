# 👑 GRAMORA SHASHKA GRANDMASTER AI — RENDER.COM DEPLOY 🚀

Ushbu repozitoriy **Gramora Shashka Bot** (GodMode v50 C-Native Engine + 24/7 Telethon Avtopilot + Jonli Web App Doskasi + @Suvbelgi_bot Boshqaruv Paneli) ni **Render.com** bulutli platformasiga 24/7 rejimda bepul joylashtirish (deploy) uchun to'liq optimallashtirilgan.

---

## ⚡ Asosiy Imkoniyatlari

1. **24/7 To'xtovsiz Avtopilot:** Render.com bulutli serverida kechayu-kunduz ishlaydi.
2. **C-Native Superhuman GodMode v50 Dvigateli:** Multi-threaded OpenMP va Alpha-Beta pruning orqali raqibga hech qanday imkoniyat qoldirmaydi.
3. **Jonli Veb-Doska & Health Check:** Render Web Service talab qiladigan `$PORT` da ishlovchi tezkor aiohttp server (`/`, `/healthz`, `/ping`).
4. **Cloud-Native Sessiya (StringSession):** Fayl saqlashga bog'liq bo'lmagan, muhit o'zgaruvchisi orqali xavfsiz ulanish.
5. **Avtomatik Uyg'oq Saqlash (Keep-Alive):** Render bepul tarifida 15 daqiqada uyquga ketishining oldini olish uchun ichki avtomatik ping mexanizmi.
6. **Maxsus Boshqaruv Boti:** [@Suvbelgi_bot](https://t.me/Suvbelgi_bot) orqali to'liq nazorat (Yoqish/O'chirish, Stavka, Statistika, Vazifalar).

---

## 🚀 RENDER.COM GA JOYLASHTIRISH (QADAMMA-QADAM)

### 1-Usul: Docker Web Service (TAVSIYA ETILADI — Eng oson va barqaror)

1. [render.com](https://render.com) saytiga kiring va kiring (Sign in via GitHub).
2. Asosiy sahifada **New +** tugmasini bosing va **Web Service** ni tanlang.
3. **Build and deploy from a Git repository** ni tanlab, **`gramora-bot-render`** repozitoriyingizni ulang (`Connect`).
4. Quyidagi parametrlarni kiriting:
   - **Name:** `gramora-bot` (yoki ixtiyoriy nom)
   - **Region:** `Frankfurt (EU Central)` yoki `Oregon (US West)`
   - **Language / Runtime:** `Docker`
   - **Instance Type:** `Free` (bepul)
5. **Environment Variables** (Muhit o'zgaruvchilari) bo'limiga kiring va quyidagilarni qo'shing:
   - `TG_SESSION_STRING` = `.env.example` dagi tayyor string session kodi
   - `TELEGRAM_BOT_TOKEN` = `8604188989:AAG9x-GExIsE1-9t4_MLfV2xQ6VZkc3kTMg`
   - `TG_API_ID` = `38883376`
   - `TG_API_HASH` = `67909afdf0fe6c23e6af29985f645297`
   - `PORT` = `10000`
   - `HOST` = `0.0.0.0`
   - `TZ` = `Asia/Tashkent`
6. Pastdagi **Deploy Web Service** tugmasini bosing!
7. Render avtomatik ravishda Docker konteynerini yig'adi, C dvigatelni kompilyatsiya qiladi va botni ishga tushiradi!

---

### 2-Usul: Python Native Environment (Docker ishlatmasdan)

Agar Docker o'rniga Python muhitini tanlasangiz:
- **Build Command:** `bash build.sh`
- **Start Command:** `bash start.sh`
- **Health Check Path:** `/healthz`

---

## ⏰ 24/7 HECH QACHON O'CHMASLIGI UCHUN (Render Free Sleep Fix)

Render bepul tarifida veb-servisga 15 daqiqa davomida so'rov kelmasa, u "uyqu"ga ketadi. Buni 100% bartaraf etish usullari:

1. **Ichki Keep-Alive (Avtomatik):**
   Render sizga bergan havolani (masalan: `https://gramora-bot.onrender.com`) nusxalang va Render Dashboard -> Environment Variables ga `RENDER_EXTERNAL_URL` yoki `APP_URL` nomi bilan qo'shing. Bot har 10 daqiqada o'zini o'zi ping qilib, uyg'oq saqlaydi!
2. **Tashqi Bepul Monitoring (100% kafolat):**
   - [cron-job.org](https://cron-job.org) yoki [uptimerobot.com](https://uptimerobot.com) saytiga bepul kiring.
   - Yangi monitor qo'shing: `https://gramora-bot.onrender.com/healthz`
   - Oraliq vaqt: Har **5 daqiqada**.
   - Natijada bot 24/7 rejimida bir soniya ham to'xtamasdan ishlaydi!

---

## 🎮 Telegram Boshqaruv Boti Buyruqlari

Bot ishga tushgach, [@Suvbelgi_bot](https://t.me/Suvbelgi_bot) ga kiring:
- `/start` — To'liq boshqaruv paneli (Inline tugmalar)
- `/on` — Avtopilotni yoqish
- `/off` — Avtopilotni to'xtatish
- `/stat` — Jonli g'alabalar va Stars statistikasi
- `/live` — Jonli veb-doska havolasi
- `/token <url>` — WebApp tokenini yangilash
- `/qr` yoki `/login` — Yangi sessiyaga kirish
