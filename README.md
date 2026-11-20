# 👑 GRAMORA SHASHKA GRANDMASTER AI — RENDER.COM DEPLOY 🚀

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/muhammadjon1505f-dot/gramora-bot-render)

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

## 🚀 1-KLIK BILAN RENDERGA JOYLASHTIRISH:

Quyidagi havolani bosing:  
👉 **[RENDERGA 1-BOSISHDA JOYLASHTIRISH (DEPLOY TO RENDER)](https://render.com/deploy?repo=https://github.com/muhammadjon1505f-dot/gramora-bot-render)**

Barcha sozlamalar (`TG_SESSION_STRING`, `BOT_TOKEN`, `PORT`) `render.yaml` orqali **avtomatik to'ldirilgan**. Sizdan faqat **Apply** tugmasini bosish talab qilinadi!

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
