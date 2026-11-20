#!/usr/bin/env python3
"""
UZB STARS BUY BOT — 1-GA-1 ANIQ KLON BOTI
Asl manba: @UzbStarsbuybot
Dasturlash tili: Python 3 (aiogram 3.x + aiosqlite)

Xususiyatlari:
1. Majburiy obuna tizimi (kanallarga a'zo bo'lmaguncha bot ochilmaydi)
2. Asl 1:1 fotosurat, matn va formatlash (Markdown/HTML)
3. ⭐️ Stars sotib olish — Mini App WebApp integratsiyasi
4. 🛍 Video qo'llanma havolasi
5. Do'stlarni taklif qilish va referal bonusi tizimi
6. Foydalanuvchi profili va balansi (/profile)
7. Administratorlar uchun boshqaruv paneli (/admin):
   - Statistika (Jami va bugungi foydalanuvchilar)
   - Barcha foydalanuvchilarga xabar tarqatish (Broadcast)
   - Majburiy obuna kanallarini boshqarish
   - Narxlar va sozlamalarni o'zgartirish
8. Avtomatik BotFather sozlamalari (Menyu tugmasi, tavsif, buyruqlar)
"""

import os
import sys
import asyncio
import logging
from typing import Optional, List

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    FSInputFile,
    BotCommand,
    MenuButtonWebApp
)
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import config
import database as db

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s"
)
logger = logging.getLogger("UzbStarsBuy")

# FSM States
class AdminStates(StatesGroup):
    waiting_broadcast_msg = State()
    waiting_channel_title = State()
    waiting_channel_url = State()
    waiting_channel_id = State()
    waiting_star_price = State()
    waiting_ref_price = State()

# ------------------- MATNLAR VA XABARLAR -------------------

SUB_REQUIRED_TEXT = "**❌ Botdan foydalanishdan oldin ushbu kanallarga obuna bo‘ling:**"

START_TEXT = """⭐️ **UzbStarsBuy** botiga xush kelibsiz!

⭐️ Bu yerda siz **Telegram Stars** va **Premiumni** __tezkor, ishonchli va xavfsiz__ xarid qilishingiz mumkin.

⚡️ **Bizning afzalliklarimiz:**
💳 **Tezkor to‘lovlar** — Humo yoki Uzcard orqali ilovadan tez va oson to‘lovlar.
🎁 **Sovg'alar tizimi** — har bir Stars xarididan sovg'alar oling.
👥 **Do‘stlarni taklif qiling** — do'stlaringizni taklif qiling va xaridlaridan siz ham foyda oling.

👇 **Boshlash uchun quyidagi tugmani bosing:**"""

HELP_TEXT = """☎️ **Qo'llab-quvvatlash xizmati:** {support_admin}
📣 **Bot yangiliklar kanali:** {channel_news}
🛍 **Video qo'llanma:** {video_url}"""

# ------------------- TUGMALARNI YASASH -------------------

async def get_subscription_keyboard() -> InlineKeyboardMarkup:
    channels = await db.get_active_channels()
    buttons = []
    
    for ch in channels:
        title = ch.get("title", "Kanal")
        url = ch.get("url", "https://t.me/UZBStarsbuy")
        buttons.append([InlineKeyboardButton(text=title, url=url)])
        
    insta_url = await db.get_setting("instagram_url", config.DEFAULT_INSTAGRAM_URL)
    buttons.append([InlineKeyboardButton(text="📸 Instagram", url=insta_url)])
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="result")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    render_base = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("APP_URL")
    if render_base:
        webapp_url = f"{render_base.rstrip('/')}/stars"
    else:
        webapp_url = await db.get_setting("webapp_url", config.DEFAULT_WEBAPP_URL)
        tunnel_file = os.path.join(config.BASE_DIR, "tunnel_url.txt")
        if os.path.exists(tunnel_file):
            try:
                with open(tunnel_file, "r", encoding="utf-8") as f:
                    t_url = f.read().strip()
                    if t_url.startswith("https://"):
                        webapp_url = t_url
            except Exception:
                pass
    video_url = await db.get_setting("video_guide_url", config.DEFAULT_VIDEO_GUIDE_URL)
    
    buttons = [
        [
            InlineKeyboardButton(
                text="⭐️ Stars sotib olish",
                web_app=WebAppInfo(url=webapp_url)
            )
        ],
        [
            InlineKeyboardButton(
                text="🛍 Video qo'llanma",
                url=video_url
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin:stats"),
            InlineKeyboardButton(text="✉️ Xabar yuborish", callback_data="admin:broadcast")
        ],
        [
            InlineKeyboardButton(text="📢 Kanallar", callback_data="admin:channels"),
            InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin:settings")
        ],
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin:refresh")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ------------------- OBUNA TEKSHIRUVCHI FUNKSIYA -------------------

async def check_user_subscriptions(bot: Bot, user_id: int) -> bool:
    channels = await db.get_active_channels()
    if not channels:
        return True
        
    for ch in channels:
        chat_id = ch.get("chat_id")
        if not chat_id:
            continue
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                return False
        except (TelegramBadRequest, TelegramForbiddenError):
            # Agar bot kanalda admin bo'lmasa yoki kanal topilmasa, o'tkazib yuborish
            continue
        except Exception as e:
            logger.warning(f"Error checking sub for {chat_id}: {e}")
            continue
            
    return True

# ------------------- HANDLERLAR -------------------

bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

@dp.message(CommandStart())
async def handle_start(message: Message, command: CommandStart):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Referal parametrini olish
    referred_by = None
    args = command.args
    if args and args.isdigit():
        ref_candidate = int(args)
        if ref_candidate != user_id:
            referred_by = ref_candidate

    # Foydalanuvchini ro'yxatga olish / yangilash
    is_new = await db.add_or_update_user(user_id, username, first_name, referred_by)
    
    # Agar yangi foydalanuvchi bo'lsa va taklif qiluvchi mavjud bo'lsa
    if is_new and referred_by:
        try:
            ref_bonus = await db.get_setting("referal_price", "100")
            await bot.send_message(
                chat_id=referred_by,
                text=f"🎉 **Yangi do'stingiz qo'shildi!**\n\n"
                     f"👤 [{first_name}](tg://user?id={user_id}) sizning taklifingiz orqali botga kirdi.\n"
                     f"💰 Balansingizga +{ref_bonus} so'm qo'shildi!",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass

    # Obunani tekshirish
    is_subscribed = await check_user_subscriptions(bot, user_id)
    if not is_subscribed:
        kb = await get_subscription_keyboard()
        await message.answer(SUB_REQUIRED_TEXT, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # Asl Start menyusi (rasm va matn bilan)
    kb = await get_main_menu_keyboard()
    if os.path.exists(config.START_PHOTO):
        photo = FSInputFile(config.START_PHOTO)
        await message.answer_photo(
            photo=photo,
            caption=START_TEXT,
            reply_markup=kb,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer(
            text=START_TEXT,
            reply_markup=kb,
            parse_mode=ParseMode.MARKDOWN
        )

@dp.callback_query(F.data == "result")
async def handle_check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_user_subscriptions(bot, user_id)
    
    if not is_subscribed:
        await callback.answer(
            "❌ Siz hali kanallarga to'liq a'zo bo'lmadingiz! Iltimos, obuna bo'ling va qayta tekshiring.",
            show_alert=True
        )
        return

    await callback.answer("✅ Obunangiz tasdiqlandi. Bosh menyudasiz.", show_alert=False)
    
    # Xabarni o'chirish va bosh menyuni yuborish
    try:
        await callback.message.delete()
    except Exception:
        pass

    kb = await get_main_menu_keyboard()
    if os.path.exists(config.START_PHOTO):
        photo = FSInputFile(config.START_PHOTO)
        await callback.message.answer_photo(
            photo=photo,
            caption=START_TEXT,
            reply_markup=kb,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await callback.message.answer(
            text=START_TEXT,
            reply_markup=kb,
            parse_mode=ParseMode.MARKDOWN
        )

@dp.message(Command("profile"))
@dp.message(Command("me"))
async def handle_profile(message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        await message.answer("Siz ro'yxatdan o'tmagansiz. /start ni bosing.")
        return
        
    ref_count = await db.get_referral_count(user_id)
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    profile_text = f"""👤 **Sizning profilingiz:**

🆔 **ID:** `{user['user_id']}`
👤 **Ism:** {user.get('first_name') or 'Noma\'lum'}
🔗 **Username:** @{user.get('username') or 'yo\'q'}
💰 **Hisobingiz:** {user.get('balance', 0):,.0f} so'm
⭐️ **Xarid qilingan stars:** {user.get('stars_purchased', 0)}
👥 **Taklif qilgan do'stlaringiz:** {ref_count} ta

🔗 **Sizning referal havolangiz:**
`{ref_link}`

💡 *Do'stlaringizni taklif qiling va har bir do'stingiz uchun sovg'alarga ega bo'ling!*"""

    await message.answer(profile_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("help"))
async def handle_help(message: Message):
    support_admin = await db.get_setting("support_admin", config.SUPPORT_ADMIN)
    channel_news = await db.get_setting("channel_news", config.DEFAULT_NEWS_CHANNEL)
    video_url = await db.get_setting("video_guide_url", config.DEFAULT_VIDEO_GUIDE_URL)
    
    text = HELP_TEXT.format(
        support_admin=support_admin,
        channel_news=channel_news,
        video_url=video_url
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

# ------------------- ADMIN PANEL -------------------

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@dp.message(Command("admin"))
async def handle_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
        
    total_users = await db.get_total_users()
    today_users = await db.get_today_users()
    star_price = await db.get_setting("star_price", "220")
    
    text = f"""👑 **Administrator Boshqaruv Paneli**

📊 **Foydalanuvchilar:**
• Jami: **{total_users}** ta
• Bugun qo'shilgan: **{today_users}** ta

⭐️ **Yulduz narxi:** {star_price} so'm
👇 Kerakli bo'limni tanlang:"""

    await message.answer(text, reply_markup=get_admin_keyboard(), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data == "admin:stats")
async def handle_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    
    total = await db.get_total_users()
    today = await db.get_today_users()
    channels = await db.get_active_channels()
    star_price = await db.get_setting("star_price", "220")
    ref_price = await db.get_setting("referal_price", "100")
    
    text = f"""📊 **Bot Statistikasi:**

👥 Jami a'zolar: **{total}**
📈 Bugungi yangi a'zolar: **{today}**
📢 Majburiy kanallar soni: **{len(channels)}** ta

⚙️ **Joriy kurslar:**
• 1 Star = **{star_price}** so'm
• 1 Referal bonusi = **{ref_price}** so'm"""

    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data == "admin:channels")
async def handle_admin_channels(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    
    channels = await db.get_active_channels()
    text = "📢 **Majburiy obuna kanallari ro'yxati:**\n\n"
    buttons = []
    
    for ch in channels:
        text += f"• **{ch['title']}** ({ch['chat_id']})\nHavola: {ch['url']}\n\n"
        buttons.append([
            InlineKeyboardButton(text=f"🗑 O'chirish: {ch['title'][:20]}", callback_data=f"del_channel:{ch['id']}")
        ])
        
    buttons.append([InlineKeyboardButton(text="➕ Yangi kanal qo'shish", callback_data="admin:add_channel")])
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:back")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data.startswith("del_channel:"))
async def handle_delete_channel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    ch_id = int(callback.data.split(":")[1])
    await db.delete_channel(ch_id)
    await callback.answer("✅ Kanal muvaffaqiyatli o'chirildi!", show_alert=True)
    await handle_admin_channels(callback)

@dp.callback_query(F.data == "admin:add_channel")
async def handle_add_channel_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_channel_title)
    await callback.message.answer("📝 Kanal nomini kiriting (masalan: `𝙐𝙕𝘽 | 𝙎𝙏𝘼𝙍𝙎 - 𝙉𝙀𝙒𝙎`):")

@dp.message(AdminStates.waiting_channel_title)
async def handle_channel_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AdminStates.waiting_channel_url)
    await message.answer("🔗 Kanalga taklif havolasini kiriting (masalan: `https://t.me/UZBStarsbuy`):")

@dp.message(AdminStates.waiting_channel_url)
async def handle_channel_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text)
    await state.set_state(AdminStates.waiting_channel_id)
    await message.answer("🆔 Kanal username yoki ID sini kiriting (masalan: `@UZBStarsbuy` yoki `-100123456789`):\n\n*Eslatma: Bot kanalda admin bo'lishi kerak!*")

@dp.message(AdminStates.waiting_channel_id)
async def handle_channel_id(message: Message, state: FSMContext):
    data = await state.get_data()
    title = data.get("title")
    url = data.get("url")
    chat_id = message.text.strip()
    
    await db.add_channel(title, url, chat_id)
    await state.clear()
    await message.answer(f"✅ **Kanal muvaffaqiyatli qo'shildi!**\n\nNom: {title}\nID: {chat_id}\nURL: {url}", parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data == "admin:broadcast")
async def handle_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_broadcast_msg)
    await callback.message.answer(
        "✉️ **Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring:**\n\n"
        "(Matn, rasm, video yoki post yuborishingiz mumkin. Bekor qilish uchun /cancel yozing)",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(AdminStates.waiting_broadcast_msg)
async def handle_do_broadcast(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Xabar tarqatish bekor qilindi.")
        return
        
    user_ids = await db.get_all_user_ids()
    total = len(user_ids)
    await state.clear()
    
    status_msg = await message.answer(f"🚀 Xabar tarqatish boshlandi... (0/{total})")
    
    sent = 0
    blocked = 0
    
    for i, u_id in enumerate(user_ids):
        try:
            await message.copy_to(chat_id=u_id)
            sent += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            blocked += 1
        except Exception as e:
            logger.error(f"Failed to send to {u_id}: {e}")
            
        if (i + 1) % 50 == 0 or (i + 1) == total:
            try:
                await status_msg.edit_text(f"🚀 Xabar yuborilmoqda: {i+1}/{total}\n✅ Yuborildi: {sent}\n🚫 Bloklagan: {blocked}")
            except Exception:
                pass
        await asyncio.sleep(0.04) # Telegram chekloviga mos
        
    await message.answer(
        f"✅ **Xabar tarqatish yakunlandi!**\n\n"
        f"👥 Jami foydalanuvchilar: {total}\n"
        f"✅ Yetkazildi: {sent}\n"
        f"🚫 Bloklaganlar: {blocked}",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query(F.data == "admin:settings")
async def handle_admin_settings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    
    star_price = await db.get_setting("star_price", "220")
    ref_price = await db.get_setting("referal_price", "100")
    support_admin = await db.get_setting("support_admin", config.SUPPORT_ADMIN)
    
    text = f"""⚙️ **Bot Sozlamalari:**

• ⭐️ 1 Star narxi: **{star_price}** so'm
• 👥 Referal taklif narxi: **{ref_price}** so'm
• ☎️ Admin aloqasi: **{support_admin}**"""

    buttons = [
        [InlineKeyboardButton(text="✏️ Star narxini o'zgartirish", callback_data="admin:set_star_price")],
        [InlineKeyboardButton(text="✏️ Referal narxini o'zgartirish", callback_data="admin:set_ref_price")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:back")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data == "admin:set_star_price")
async def handle_set_star_price(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_star_price)
    await callback.message.answer("⭐️ 1 dona Star uchun yangi narxni so'mda kiriting (masalan: `220`):")

@dp.message(AdminStates.waiting_star_price)
async def handle_save_star_price(message: Message, state: FSMContext):
    price = message.text.strip()
    await db.set_setting("star_price", price)
    await state.clear()
    await message.answer(f"✅ Star narxi **{price} so'm** qilib belgilandi!", parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data == "admin:set_ref_price")
async def handle_set_ref_price(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_ref_price)
    await callback.message.answer("👥 1 ta referal taklifi uchun yangi bonus narxini kiriting (masalan: `100`):")

@dp.message(AdminStates.waiting_ref_price)
async def handle_save_ref_price(message: Message, state: FSMContext):
    price = message.text.strip()
    await db.set_setting("referal_price", price)
    await state.clear()
    await message.answer(f"✅ Referal bonusi **{price} so'm** qilib belgilandi!", parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data == "admin:back")
@dp.callback_query(F.data == "admin:refresh")
async def handle_admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    total_users = await db.get_total_users()
    today_users = await db.get_today_users()
    star_price = await db.get_setting("star_price", "220")
    
    text = f"""👑 **Administrator Boshqaruv Paneli**

📊 **Foydalanuvchilar:**
• Jami: **{total_users}** ta
• Bugun qo'shilgan: **{today_users}** ta

⭐️ **Yulduz narxi:** {star_price} so'm
👇 Kerakli bo'limni tanlang:"""

    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode=ParseMode.MARKDOWN)

# ------------------- BOT SETUP VA STARTUP -------------------

async def setup_bot():
    logger.info("Initializing database...")
    await db.init_db()
    
    bot_info = await bot.get_me()
    logger.info(f"Bot connected: @{bot_info.username} (ID: {bot_info.id})")
    
    # 1. Bot commands
    try:
        await bot.set_my_commands([
            BotCommand(command="start", description="🔄 Botni Yangilash"),
            BotCommand(command="profile", description="👤 Mening profilim"),
            BotCommand(command="help", description="☎️ Qo'llab-quvvatlash")
        ])
        logger.info("Bot commands set successfully.")
    except Exception as e:
        logger.warning(f"Could not set commands: {e}")

    # 2. Chat menu button (Mini App)
    try:
        render_base = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("APP_URL")
        if render_base:
            webapp_url = f"{render_base.rstrip('/')}/stars"
            await db.set_setting("webapp_url", webapp_url)
        else:
            webapp_url = await db.get_setting("webapp_url", config.DEFAULT_WEBAPP_URL)
            tunnel_file = os.path.join(config.BASE_DIR, "tunnel_url.txt")
            if os.path.exists(tunnel_file):
                try:
                    with open(tunnel_file, "r", encoding="utf-8") as f:
                        t_url = f.read().strip()
                        if t_url.startswith("https://"):
                            webapp_url = t_url
                except Exception:
                    pass
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="⭐️ Xarid qilish",
                web_app=WebAppInfo(url=webapp_url)
            )
        )
        logger.info(f"Chat menu button set successfully: {webapp_url}")
    except Exception as e:
        logger.warning(f"Could not set chat menu button: {e}")

async def sync_webapp_url_loop():
    last_url = None
    tunnel_file = os.path.join(config.BASE_DIR, "tunnel_url.txt")
    while True:
        try:
            current_url = None
            if os.path.exists(tunnel_file):
                with open(tunnel_file, "r", encoding="utf-8") as f:
                    u = f.read().strip()
                    if u.startswith("https://"):
                        current_url = u
            if current_url and current_url != last_url:
                await bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(
                        text="⭐️ Xarid qilish",
                        web_app=WebAppInfo(url=current_url)
                    )
                )
                last_url = current_url
                logger.info(f"Auto-synced menu button with: {current_url}")
        except Exception as e:
            logger.debug(f"sync_webapp_url_loop error: {e}")
        await asyncio.sleep(30)

async def main():
    await setup_bot()
    asyncio.create_task(sync_webapp_url_loop())
    logger.info("Starting long polling...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
