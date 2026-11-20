# UzbStarsBuy Bot — 1-ga-1 To'liq Klon Loyihasi

Ushbu repozitoriy **@UzbStarsbuybot** botining barcha matnlari, tugmalari, Mini App (WebApp) integratsiyasi, rasmlari, majburiy obuna va to'liq administratorlik paneli bilan **1-ga-1 qilib klonlangan** to'liq loyihasi.

## 🚀 Ishga tushirilgan bot ma'lumotlari:
- **Bot username:** [@uzstarsbuybot](https://t.me/uzstarsbuybot)
- **Bot Token:** `9201777867:AAFGPMm-qx96DP8pAQH691FmUjzZvjIvg1A`
- **Holati:** PM2 orqali 24/7 aktiv ishlab turibdi

---

## 📁 Loyiha tarkibi:
- `bot.py` — Asosiy bot kodi (aiogram 3.15 + aiosqlite)
- `database.py` — SQLite asinxron ma'lumotlar bazasi boshqaruvi
- `config.py` — Bot sozlamalari, tokenlar va admin ID lari
- `web_server.py` — Mini App WebApp uchun mahalliy aiohttp veb-server
- `web_app/` — Telegram WebApp (React frontend) ning to'liq statik fayllari
- `start_photo.jpg` — Botning asl start fotosurati
- `avatar.jpg` — Bot avatari
- `desc_photo.jpg` — Bot tavsif fotosurati
- `ecosystem.config.js` — PM2 konfiguratsiyasi
- `start.sh` — Avtomatik ishga tushirish skripti
- `requirements.txt` — Kerakli kutubxonalar ro'yxati

---

## ✨ Imkoniyatlari:
1. **Majburiy obuna nazorati (Kanallarga a'zolik):**
   - Foydalanuvchi ko'rsatilgan kanallarga (`@UZBStarsbuy`) va Instagramga obuna bo'lmaguncha bot ochilmaydi.
   - `✅ Tekshirish` bosilganda bot obunani avtomatik tekshiradi.
2. **Asl 1:1 Dizayn va Formatlash:**
   - Asl start rasmi va barcha matnlar 100% bir xil.
3. **Mini App WebApp Integratsiyasi:**
   - `⭐️ Stars sotib olish` tugmasi bosilganda to'g'ridan-to'g'ri Telegram WebApp ochiladi.
   - Menu Button (`⭐️ Xarid qilish`) bot chap burchagida o'rnatilgan.
4. **Referal tizimi:**
   - Har bir foydalanuvchi uchun shaxsiy referal havolasi.
   - Taklif qilingan har bir yangi do'st uchun hisobga avtomatik bonus qo'shiladi.
5. **Foydalanuvchi profili (`/profile`):**
   - Foydalanuvchi ID si, ismi, balansi, referallari va havolasi.
6. **Administrator Boshqaruv Paneli (`/admin`):**
   - 📊 **Statistika:** Jami va bugungi yangi a'zolar soni.
   - ✉️ **Xabar yuborish (Broadcast):** Barcha foydalanuvchilarga xabar/post tarqatish.
   - 📢 **Kanallarni boshqarish:** Yangi majburiy obuna kanalini qo'shish va o'chirish.
   - ⚙️ **Sozlamalar:** Star narxi, referal narxi va admin kontaktlarini o'zgartirish.

---

## 🛠 Boshqarish buyruqlari:

### Bot holatini tekshirish:
```bash
pm2 status uzbstarsbuy-bot
pm2 logs uzbstarsbuy-bot
```

### Botni qayta ishga tushirish:
```bash
pm2 restart uzbstarsbuy-bot
```

### Botni to'xtatish:
```bash
pm2 stop uzbstarsbuy-bot
```
