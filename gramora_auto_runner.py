#!/usr/bin/env python3
"""
GRAMORA SHASHKA — 24/7 TO'LIQ AVTOMATIK USERBOT + GODMODE v50 AI AVTOPILOT
+ MAXSUS BOSHQARUV TELEGRAM BOTI (INLINE TUGMALAR BILAN)
Muallif: Antigravity AI

Imkoniyatlari:
1. 24/7 Uxlashsiz va to'xtovsiz ishlash (PM2 orqali);
2. Dinamik Stavka — balansingiz va onlayn raqiblarga qarab optimal stavka (3, 20, 100...) tanlanadi;
3. Avtomatik Pul Ishlash (Auto-Task Farm) — balans kam qolganda yoki har daqiqada mavjud vazifalarni avtomatik yechib Stars yig'adi;
4. Telegram Userbot buyruqlari: istalgan chatda .on, .off, .s;
5. Maxsus Telegram Boti (@Suvbelgi_bot):
   - Faqat @xua202 va @Sirojjidinismoilov uchun to'liq boshqaruv paneli;
   - Qulay inline tugmalar (Yoqish/O'chirish, Vazifalar, Stavkani belgilash, Statistika, Nollash).
"""

import asyncio
import os
import sys
import re
import json
import html
import time
import subprocess
import urllib.request
from datetime import datetime, timedelta
from urllib.parse import unquote, parse_qs
import qrcode

import base64
import aiohttp
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl import types
from telethon.tl.functions.messages import RequestWebViewRequest, RequestAppWebViewRequest
from telethon.tl.types import InputBotAppShortName

from gramora_shashka_bot import GramoraCheckersBot, StatsManager
from web_visualizer import start_web_server, get_tunnel_url, get_all_tunnel_urls

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Telegram API sozlamalari
API_ID = int(os.getenv("TG_API_ID", "38883376"))
API_HASH = os.getenv("TG_API_HASH", "67909afdf0fe6c23e6af29985f645297")
SESSION_NAME = os.getenv("TG_SESSION", os.path.join(BASE_DIR, "gramora_userbot"))
SESSION_BOT_NAME = os.getenv("TG_BOT_SESSION", os.path.join(BASE_DIR, "control_bot"))
TG_SESSION_STRING = os.getenv("TG_SESSION_STRING", "").strip()
TG_SESSION_BASE64 = os.getenv("TG_SESSION_BASE64", "").strip()

BOT_USERNAME = os.getenv("BOT_USERNAME", "Gramorabot")
START_PARAM = os.getenv("START_PARAM", "8191930658")

# Maxsus boshqaruv Telegram boti
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8604188989:AAG9x-GExIsE1-9t4_MLfV2xQ6VZkc3kTMg")
ALLOWED_USERNAMES = {"xua202", "sirojjidinismoilov"}
ALLOWED_USER_IDS = {8191930658, 8893717129}


async def get_gramora_init_data(client: TelegramClient) -> str:
    for attempt in range(4):
        try:
            if not client.is_connected():
                await client.connect()
            print(f"\n[USERBOT] @{BOT_USERNAME} botidan WebApp havolasi olinmoqda (urinish {attempt+1})...")
            bot_entity = await client.get_input_entity(BOT_USERNAME)

            web_url = None

            # 1-usul: To'g'ridan-to'g'ri RequestAppWebViewRequest orqali (Mini App ochish)
            try:
                app_input = InputBotAppShortName(bot_id=bot_entity, short_name="app")
                res = await client(RequestAppWebViewRequest(
                    peer=bot_entity,
                    app=app_input,
                    platform="android",
                    start_param=START_PARAM
                ))
                web_url = res.url
                print("[USERBOT] Mini App havolasi muvaffaqiyatli olindi (1-usul)!")
            except Exception as e:
                print(f"[USERBOT] 1-usul ishlamadi ({e}), 2-usul (Inline tugma) sinab ko'rilmoqda...")

            # 2-usul: Botga /start yuborib, inline tugmadagi web_app havolasini bosish
            if not web_url:
                await client.send_message(bot_entity, f"/start {START_PARAM}")
                await asyncio.sleep(2.0)

                messages = await client.get_messages(bot_entity, limit=3)
                for msg in messages:
                    if msg.reply_markup and getattr(msg.reply_markup, "rows", None):
                        for row in msg.reply_markup.rows:
                            for btn in row.buttons:
                                btn_url = getattr(btn, "url", None)
                                if hasattr(btn, "text") and ("o'yna" in btn.text.lower() or "play" in btn.text.lower() or "shashka" in btn.text.lower()):
                                    try:
                                        res = await client(RequestWebViewRequest(
                                            peer=bot_entity,
                                            bot=bot_entity,
                                            platform="android",
                                            from_bot_menu=False,
                                            url=btn_url or "https://gramorachat.rekchi.uz/shashka/"
                                        ))
                                        web_url = res.url
                                        print("[USERBOT] Inline tugmadan WebApp havolasi olindi (2-usul)!")
                                        break
                                    except Exception as btn_err:
                                        print(f"[USERBOT] Tugmani bosishda xato: {btn_err}")
                            if web_url:
                                break
                    if web_url:
                        break

            if not web_url:
                raise ValueError("Gramorabot'dan WebApp havolasini olib bo'lmadi! Iltimos bot sozlamalarini tekshiring.")

            # initData ni URL dan ajratib olish
            init_data = None
            if "#tgWebAppData=" in web_url:
                part = web_url.split("#tgWebAppData=")[1]
                init_data = part.split("&tgWebAppVersion=")[0]
            elif "tgWebAppData=" in web_url:
                part = web_url.split("tgWebAppData=")[1]
                init_data = part.split("&")[0]

            if not init_data:
                raise ValueError("URL ichidan tgWebAppData topilmadi!")

            decoded_init_data = unquote(init_data)
            print("[USERBOT] ✅ 'initData' muvaffaqiyatli ajratib olindi!")
            return decoded_init_data
        except Exception as e:
            print(f"[USERBOT] initData olish urinishida xato ({attempt+1}/4): {e}")
            await asyncio.sleep(2.0)

    raise ValueError("Gramorabot'dan WebApp havolasi olinmadi (4 ta urinishdan so'ng)!")


def get_stats_url() -> str:
    """O'yinlar statistikasi va jonli doska Web App havolasi (GitHub Pages)"""
    return "https://muhammadjon1505f-dot.github.io/gramora-live/"


def get_control_keyboard(
    is_enabled: bool,
    current_stake: int,
    stake_mode: str,
    manual_stake: int = None,
    tunnel_url: str = None,
    stats_url: str = None,
    in_match: bool = False,
    has_bot: bool = True,
    soft_stop: bool = False,
    active_account: str = "sirojjidin"
):
    """Boshqaruv Telegram boti uchun chiroyli inline tugmalar paneli"""
    tunnel_url = tunnel_url or get_tunnel_url()
    stats_url = stats_url or get_stats_url()

    if not is_enabled:
        power_btn = Button.inline("🟢 Yoqish (.on)", b"cmd_on")
    elif soft_stop:
        power_btn = Button.inline("⏳ O'yindan so'ng o'chadi", b"cmd_soft_status")
    else:
        power_btn = Button.inline("🔴 O'chirish (.off)", b"cmd_off")

    s_mode = str(stake_mode or "auto").lower().strip()
    try:
        cur_stk_int = int(current_stake) if current_stake else 3
    except Exception:
        cur_stk_int = 3
    try:
        man_stk_int = int(manual_stake) if manual_stake else None
    except Exception:
        man_stk_int = None

    effective_stake = man_stk_int if (s_mode == "manual" and man_stk_int) else cur_stk_int
    s3_check = "✅ " if (s_mode == "manual" and effective_stake == 3) else ""
    s20_check = "✅ " if (s_mode == "manual" and effective_stake == 20) else ""
    s100_check = "✅ " if (s_mode == "manual" and effective_stake == 100) else ""
    s300_check = "✅ " if (s_mode == "manual" and effective_stake == 300) else ""
    s1000_check = "✅ " if (s_mode == "manual" and effective_stake == 1000) else ""
    auto_check = "✅ " if (s_mode == "auto") else ""

    sir_tab = "👤 Sirojjidin ✅" if active_account == "sirojjidin" else "👤 Sirojjidin"
    mux_tab = "👤 Muxa ✅" if active_account == "muxa" else "👤 Muxa"
    tab_row = [
        Button.inline(sir_tab, b"tab_sirojjidin"),
        Button.inline(mux_tab, b"tab_muxa")
    ]

    target_web_url = tunnel_url or stats_url or "https://muhammadjon1505f-dot.github.io/gramora-live/"
    web_app_btn = types.KeyboardInlineButton(
        text="🌐 Web App",
        type=types.InlineButtonTypeWebView(url=target_web_url)
    )

    buttons = [
        tab_row,
        [
            web_app_btn
        ],
        [
            power_btn,
            Button.inline("🔄 Yangilash", b"cmd_refresh")
        ],
        [
            Button.inline("🎁 Vazifalarni Yechish", b"cmd_task"),
            Button.inline(f"{auto_check}🔄 Avto-Stavka", b"stake_auto"),
        ],
        [
            Button.inline("🧹 Nollash", b"cmd_reset"),
            Button.inline(f"{s3_check}3⭐", b"stake_3"),
            Button.inline(f"{s20_check}20⭐", b"stake_20"),
        ],
        [
            Button.inline(f"{s100_check}100⭐", b"stake_100"),
            Button.inline(f"{s300_check}300⭐", b"stake_300"),
            Button.inline(f"{s1000_check}1000⭐", b"stake_1000"),
        ]
    ]
    return buttons


class GameBotHolder:
    def __init__(self, stats):
        self.bot = None
        self.stats_mgr = stats
        self.game_task = None
        self.client = None

    async def get_epic_webapp_token(self):
        if not self.client:
            print("[EPIC SYNC] Telethon client hali tayyor emas!")
            return None
        try:
            if not self.client.is_connected():
                await self.client.connect()
            bot_entity = await self.client.get_input_entity("epic_gift_bot")
            app_input = InputBotAppShortName(bot_id=bot_entity, short_name="app")
            res = await self.client(RequestAppWebViewRequest(
                peer=bot_entity,
                app=app_input,
                platform="android",
                write_allowed=True
            ))
            webapp_url = res.url
            init_data = None
            if "#tgWebAppData=" in webapp_url:
                fragment = webapp_url.split('#')[1]
                params = parse_qs(fragment)
                init_data = params.get('tgWebAppData', [''])[0]
            elif "tgWebAppData=" in webapp_url:
                part = webapp_url.split("tgWebAppData=")[1]
                init_data = part.split("&")[0]

            if init_data:
                data = {
                    "url": webapp_url,
                    "tgWebAppData": init_data,
                    "updated_at": str(datetime.now())
                }
                epic_path = "/home/ubuntu/epic-rocket-bot/webapp_data.json" if os.path.exists("/home/ubuntu/epic-rocket-bot") else "/root/epic-rocket-bot/webapp_data.json"
                with open(epic_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                print("[EPIC SYNC] ✅ Epic Rocket tgWebAppData muvaffaqiyatli yangilandi!")
                return init_data
        except Exception as e:
            print(f"[EPIC SYNC XATO] {e}")
        return None

    async def get_recent_messages(self, search="muxa", limit=20):
        results = []
        dialog_info = []
        dl_dir = "/home/ubuntu/muxa_downloads" if os.path.exists("/home/ubuntu") else "/root/muxa_downloads"
        try:
            os.makedirs(dl_dir, exist_ok=True)
        except Exception:
            dl_dir = "/tmp/muxa_downloads"
            os.makedirs(dl_dir, exist_ok=True)

        async def fetch_from_entity(client_obj, ent, source_name):
            try:
                msgs = await client_obj.get_messages(ent, limit=limit)
                for m in msgs:
                    media_info = None
                    if m.media:
                        fname = getattr(getattr(m, "file", None), "name", None)
                        media_info = {
                            "type": type(m.media).__name__,
                            "file_name": fname or f"media_{m.id}.mp4",
                            "size": getattr(getattr(m, "file", None), "size", None),
                            "mime_type": getattr(getattr(m, "file", None), "mime_type", None)
                        }
                        try:
                            dl_path = await m.download_media(file=dl_dir + "/")
                            if dl_path:
                                media_info["downloaded_path"] = str(dl_path)
                                media_info["downloaded_filename"] = os.path.basename(dl_path)
                                media_info["file_name"] = os.path.basename(dl_path)
                        except Exception as de:
                            media_info["download_error"] = str(de)

                    results.append({
                        "source": source_name,
                        "id": m.id,
                        "date": str(m.date),
                        "sender_id": m.sender_id,
                        "out": m.out,
                        "text": m.text or m.raw_text or "",
                        "media": media_info
                    })
            except Exception as e:
                print(f"[FETCH ERROR {source_name}] {e}")

        # 1. Userbot orqali xabarlarni olish
        if self.client and self.client.is_connected():
            try:
                dialogs = await self.client.get_dialogs(limit=40)
                for d in dialogs:
                    d_uname = (getattr(d.entity, "username", "") or "").lower()
                    d_name = (d.name or "").lower()
                    d_id = getattr(d, "id", None)
                    dialog_info.append({"id": d_id, "name": d.name, "username": d_uname})
                    if d_id == 8191930658 or "xua" in d_uname or "muxa" in d_name or "muxa" in d_uname or "202" in d_uname:
                        await fetch_from_entity(self.client, d.entity, "userbot")
                if not results:
                    try:
                        ent = await self.client.get_entity(8191930658)
                        await fetch_from_entity(self.client, ent, "userbot_id")
                    except Exception:
                        pass
            except Exception as e:
                print(f"[GET RECENT MSGS CLIENT ERROR] {e}")

        # 2. Control Bot (@Suvbelgi_bot) orqali xabarlarni olish
        if hasattr(self, "bot_client") and self.bot_client and self.bot_client.is_connected():
            try:
                b_ent = await self.bot_client.get_entity(8191930658)
                await fetch_from_entity(self.bot_client, b_ent, "suvbelgi_bot")
            except Exception as be:
                print(f"[GET RECENT MSGS BOT ERROR] {be}")

        return {"results": results, "dl_dir": dl_dir, "dialogs": dialog_info[:15]}

    async def get_mrkt_webapp_token(self):
        if not self.client:
            return None
        try:
            if not self.client.is_connected():
                await self.client.connect()
            bot_entity = await self.client.get_input_entity("mrkt")
            res = await self.client(RequestWebViewRequest(
                peer=bot_entity,
                bot=bot_entity,
                platform="android",
                from_bot_menu=False,
                url="https://cdn.tgmrkt.io/index.html"
            ))
            webapp_url = res.url
            init_data = None
            if "#tgWebAppData=" in webapp_url:
                fragment = webapp_url.split('#')[1]
                params = parse_qs(fragment)
                init_data = params.get('tgWebAppData', [''])[0]
            elif "tgWebAppData=" in webapp_url:
                part = webapp_url.split("tgWebAppData=")[1]
                init_data = part.split("&")[0]
            return init_data
        except Exception as e:
            print(f"[MRKT TOKEN ERROR] {e}")
            return None

    async def leave_telegram_channels(self, channels_list):
        if not self.client or not self.client.is_connected():
            return {"ok": False, "error": "Client not connected"}
        from telethon.tl.functions.channels import LeaveChannelRequest
        success_left = []
        errors = []
        for ch in channels_list:
            ch_clean = ch.strip().lstrip("@")
            if not ch_clean:
                continue
            try:
                ent = await self.client.get_input_entity(ch_clean)
                await self.client(LeaveChannelRequest(ent))
                success_left.append(ch_clean)
                await asyncio.sleep(1.0)
            except Exception as e:
                errors.append({"channel": ch_clean, "error": str(e)})
        return {"ok": True, "left_count": len(success_left), "channels": success_left, "errors": errors}

    async def join_telegram_channel(self, channel_target):
        if not self.client or not self.client.is_connected():
            return {"ok": False, "error": "Telethon client ulangan emas"}
        try:
            from telethon.tl.functions.channels import JoinChannelRequest
            target = channel_target.strip().lstrip("@")
            entity = await self.client.get_input_entity(target)
            await self.client(JoinChannelRequest(entity))
            return {"ok": True, "message": f"Kanalga muvaffaqiyatli a'zo bo'lindi: @{target}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def scrape_target_bot(self, target_username="ProYordamchi_bot"):
        if not self.client or not self.client.is_connected():
            return {"ok": False, "error": "Telethon client ulangan emas"}
        
        target = target_username.lstrip("@")
        scraped_data = {
            "bot_username": target,
            "timestamp": str(datetime.now()),
            "start_message": None,
            "sub_menus": []
        }

        def serialize_entities(entities):
            if not entities:
                return []
            res = []
            for e in entities:
                d = {
                    "type": type(e).__name__,
                    "offset": getattr(e, "offset", 0),
                    "length": getattr(e, "length", 0)
                }
                if hasattr(e, "document_id"):
                    d["document_id"] = e.document_id
                if hasattr(e, "url"):
                    d["url"] = e.url
                res.append(d)
            return res

        def serialize_buttons(reply_markup):
            if not reply_markup:
                return None
            rows = []
            if hasattr(reply_markup, "rows"):
                for row in reply_markup.rows:
                    r = []
                    for btn in getattr(row, "buttons", []):
                        btn_type = getattr(btn, "type", None)
                        data_val = getattr(btn, "data", None)
                        url_val = getattr(btn, "url", None)
                        webapp_val = None
                        icon_id = None

                        if btn_type:
                            type_name = type(btn_type).__name__
                            if hasattr(btn_type, "data"):
                                data_val = btn_type.data
                            if hasattr(btn_type, "url"):
                                url_val = btn_type.url
                            if "WebView" in type_name or hasattr(btn_type, "url"):
                                webapp_val = getattr(btn_type, "url", None)

                        # Check button style icon (Telegram Premium emoji icon on button!)
                        style = getattr(btn, "style", None)
                        if style and hasattr(style, "icon") and style.icon:
                            icon_id = style.icon

                        b_info = {
                            "type": type(btn).__name__,
                            "text": getattr(btn, "text", ""),
                            "url": url_val,
                            "web_app": webapp_val,
                            "icon_custom_emoji_id": icon_id,
                            "data": data_val.decode("utf-8", errors="replace") if isinstance(data_val, bytes) else str(data_val) if data_val else None
                        }
                        r.append(b_info)
                    rows.append(r)
            return rows

        try:
            ent = await self.client.get_entity(target)
            
            # Send /start
            await self.client.send_message(ent, "/start")
            await asyncio.sleep(2.5)

            # Get latest messages
            msgs = await self.client.get_messages(ent, limit=4)
            bot_msgs = [m for m in msgs if not m.out]
            if bot_msgs:
                start_msg = bot_msgs[0]
                scraped_data["start_message"] = {
                    "id": start_msg.id,
                    "text": start_msg.text or "",
                    "raw_text": start_msg.raw_text or "",
                    "entities": serialize_entities(start_msg.entities),
                    "buttons": serialize_buttons(start_msg.reply_markup)
                }

                # Click callback buttons like guide:menu
                if start_msg.reply_markup and hasattr(start_msg.reply_markup, "rows"):
                    for r_idx, row in enumerate(start_msg.reply_markup.rows):
                        for c_idx, btn in enumerate(getattr(row, "buttons", [])):
                            btn_text = getattr(btn, "text", "")
                            btn_type = getattr(btn, "type", None)
                            data_val = getattr(btn, "data", None) or getattr(btn_type, "data", None)
                            if data_val:
                                try:
                                    if isinstance(data_val, str):
                                        data_val = data_val.encode("utf-8")
                                    await start_msg.click(data=data_val)
                                    await asyncio.sleep(2.5)
                                    sub_msgs = await self.client.get_messages(ent, limit=3)
                                    for sm in sub_msgs:
                                        if not sm.out and sm.id != start_msg.id:
                                            scraped_data["sub_menus"].append({
                                                "button_text": btn_text,
                                                "callback_data": data_val.decode("utf-8", errors="replace"),
                                                "response_text": sm.text or "",
                                                "entities": serialize_entities(sm.entities),
                                                "buttons": serialize_buttons(sm.reply_markup)
                                            })
                                            break
                                except Exception as be:
                                    scraped_data["sub_menus"].append({
                                        "button_text": btn_text,
                                        "error": str(be)
                                    })

            dump_path = f"/root/{target}_dump.json"
            with open(dump_path, "w", encoding="utf-8") as f:
                json.dump(scraped_data, f, ensure_ascii=False, indent=2)

            return {"ok": True, "dump_file": dump_path, "data": scraped_data}
        except Exception as e:
            return {"ok": False, "error": str(e), "data": scraped_data}

    async def copy_bot_profile(self, source_bot="ProYordamchi_bot", target_token="8804427021:AAFPk_NvhYvy_yMCZSUUNaUwr_1ntUOa9Pg"):
        if not self.client or not self.client.is_connected():
            return {"ok": False, "error": "Telethon client ulangan emas"}
        
        target = source_bot.lstrip("@")
        try:
            from telethon.tl.functions.users import GetFullUserRequest
            import urllib.request, urllib.parse, subprocess

            ent = await self.client.get_entity(target)
            full = await self.client(GetFullUserRequest(ent))

            # 1. Download profile photo
            os.makedirs("/root/ProYordamchi_clone", exist_ok=True)
            photo_path = "/root/ProYordamchi_clone/avatar.jpg"
            dl_res = await self.client.download_profile_photo(ent, file=photo_path)

            name = (ent.first_name or "") + (" " + ent.last_name if ent.last_name else "")
            name = name.strip() or "PRO Bot"

            about = getattr(full.full_user, "about", "") or ""
            bot_info = getattr(full.full_user, "bot_info", None)
            description = getattr(bot_info, "description", "") or ""

            api_base = f"https://api.telegram.org/bot{target_token}"
            results = {}

            # setMyName
            try:
                with urllib.request.urlopen(f"{api_base}/setMyName?name=" + urllib.parse.quote(name), timeout=10) as r:
                    results["name"] = json.loads(r.read().decode("utf-8"))
            except Exception as ne:
                results["name_error"] = str(ne)

            # setMyDescription
            if description:
                try:
                    with urllib.request.urlopen(f"{api_base}/setMyDescription?description=" + urllib.parse.quote(description), timeout=10) as r:
                        results["description"] = json.loads(r.read().decode("utf-8"))
                except Exception as de:
                    results["description_error"] = str(de)

            # setMyShortDescription
            if about:
                try:
                    with urllib.request.urlopen(f"{api_base}/setMyShortDescription?short_description=" + urllib.parse.quote(about), timeout=10) as r:
                        results["short_description"] = json.loads(r.read().decode("utf-8"))
                except Exception as se:
                    results["short_description_error"] = str(se)

            # setMyProfilePhoto
            if dl_res and os.path.exists(photo_path):
                try:
                    p = subprocess.run([
                        "curl", "-s", "-F", f"photo=@{photo_path}", f"{api_base}/setMyProfilePhoto"
                    ], capture_output=True, text=True, timeout=15)
                    results["photo_response"] = p.stdout
                except Exception as pe:
                    results["photo_error"] = str(pe)

            return {
                "ok": True,
                "name": name,
                "about": about,
                "description": description,
                "photo_downloaded": dl_res is not None,
                "results": results
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @property
    def in_match(self):
        return self.bot.in_match if self.bot else False

    @property
    def soft_stop(self):
        return getattr(self.bot, "soft_stop", False) if self.bot else False

    def get_live_state(self):
        if self.bot:
            return self.bot.get_live_state()
        if os.path.exists("/root/last_live_state.json"):
            try:
                with open("/root/last_live_state.json", "r", encoding="utf-8") as f:
                    saved_state = json.load(f)
                    if isinstance(saved_state, dict) and "board" in saved_state:
                        saved_state["is_enabled"] = self.stats_mgr.stats.get("is_enabled", False)
                        saved_state["stats"] = self.stats_mgr.stats
                        saved_state["user_balance"] = self.stats_mgr.stats.get("stars_balance", 0.0)
                        saved_state["net_profit"] = self.stats_mgr.stats.get("net_profit", 0.0)
                        saved_state["games_total"] = self.stats_mgr.stats.get("games_total", 0)
                        saved_state["wins"] = self.stats_mgr.stats.get("wins", 0)
                        saved_state["losses"] = self.stats_mgr.stats.get("losses", 0)
                        saved_state["draws"] = self.stats_mgr.stats.get("draws", 0)
                        saved_state["streak"] = self.stats_mgr.stats.get("streak", 0)
                        return saved_state
            except Exception:
                pass
        return {
            "in_match": False,
            "match_id": None,
            "your_seat": 0,
            "turn": 0,
            "turn_name": "Tizim tayyorlanmoqda...",
            "turn_badge": "Kutilmoqda",
            "my_name": self.stats_mgr.stats.get("name", "GodMode v50 AI"),
            "my_rating": self.stats_mgr.stats.get("rating", 1500),
            "opp_name": "Raqib qidirilmoqda",
            "opp_rating": 0,
            "stake": self.stats_mgr.stats.get("current_stake", 3),
            "board": [3]*12 + [0]*8 + [1]*12,
            "w_count": 12,
            "b_count": 12,
            "last_move": None,
            "move_history": [],
            "last_logged_key": None,
            "eval_score": 0,
            "eval_depth": 0,
            "eval_nodes": 0,
            "eval_is_book": False,
            "clock": {},
            "status_text": "🟢 Tizim faol. O'yin kutilmoqda...",
            "last_update": 0,
            "stats": self.stats_mgr.stats,
            "user_balance": self.stats_mgr.stats.get("stars_balance", 0.0),
            "net_profit": self.stats_mgr.stats.get("net_profit", 0.0),
            "games_total": self.stats_mgr.stats.get("games_total", 0),
            "wins": self.stats_mgr.stats.get("wins", 0),
            "losses": self.stats_mgr.stats.get("losses", 0),
            "draws": self.stats_mgr.stats.get("draws", 0),
            "streak": self.stats_mgr.stats.get("streak", 0),
            "is_enabled": self.stats_mgr.stats.get("is_enabled", True),
            "current_stake": self.stats_mgr.stats.get("current_stake", 3),
            "current_status": self.stats_mgr.stats.get("current_status", "🟢 Tizim faol"),
            "server_time": 0
        }

    async def turn_on(self):
        if self.bot:
            return await self.bot.turn_on()
        self.stats_mgr.stats["is_enabled"] = True
        self.stats_mgr.save()
        return "🟢 Bot yoqildi (.on)"

    async def turn_off(self, force=False):
        if self.bot:
            return await self.bot.turn_off(force=force)
        self.stats_mgr.stats["is_enabled"] = False
        self.stats_mgr.save()
        return "🔴 Bot to'xtatildi (.off)"

    async def soft_turn_off(self):
        if self.bot:
            return await self.bot.soft_turn_off()
        self.stats_mgr.stats["is_enabled"] = False
        self.stats_mgr.save()
        return "⏳ Joriy o'yin tugagach to'xtaydi"

    async def claim_all_available_tasks(self):
        if self.bot:
            return await self.bot.claim_all_available_tasks()
        return 0


async def main():
    print("=" * 65)
    print("🏆 GRAMORA SHASHKA — 24/7 USERBOT & GODMODE v50 AI AVTOPILOT 🏆")
    print("=" * 65)

    stats = StatsManager()
    bot_holder = GameBotHolder(stats)

    # 1. Web-Vizualizatorni darhol ishga tushirish (Render / Local Port)
    try:
        web_host = os.getenv("HOST", "0.0.0.0")
        web_port = int(os.getenv("PORT", "8766"))
        await start_web_server(bot_holder, host=web_host, port=web_port)
        print(f"🌐 Veb-vizualizator (SSE) http://{web_host}:{web_port} da ishga tushirildi!")
    except Exception as e:
        print(f"[WEB VIZ WARNING] {e}")

    # 2. Maxsus Boshqaruv Botini ishga tushirish (@Suvbelgi_bot)
    bot_client = TelegramClient(
        SESSION_BOT_NAME, API_ID, API_HASH,
        connection_retries=None,
        retry_delay=3,
        auto_reconnect=True,
        timeout=30
    )
    await bot_client.start(bot_token=TELEGRAM_BOT_TOKEN)
    bot_holder.bot_client = bot_client
    bot_me = await bot_client.get_me()
    print(f"[CONTROL BOT] Boshqaruv boti ulandi: @{bot_me.username} ({bot_me.id})")

    # 3. Telethon Userbot mijozini tayyorlash (StringSession / Base64 / SQLite)
    userbot_session_target = SESSION_NAME
    if TG_SESSION_STRING:
        print("[USERBOT] TG_SESSION_STRING orqali ulanmoqda...")
        userbot_session_target = StringSession(TG_SESSION_STRING)
    elif TG_SESSION_BASE64:
        print("[USERBOT] TG_SESSION_BASE64 dan sessiya tiklanmoqda...")
        sess_file = os.path.join(BASE_DIR, "gramora_userbot.session")
        if not os.path.exists(sess_file):
            with open(sess_file, "wb") as bf:
                bf.write(base64.b64decode(TG_SESSION_BASE64))
        userbot_session_target = os.path.join(BASE_DIR, "gramora_userbot")
    elif os.path.exists(os.path.join(BASE_DIR, "gramora_userbot.session")):
        userbot_session_target = os.path.join(BASE_DIR, "gramora_userbot")

    client = TelegramClient(
        userbot_session_target, API_ID, API_HASH,
        connection_retries=None,
        retry_delay=3,
        auto_reconnect=True,
        timeout=30
    )

    userbot_authorized = False
    try:
        await client.connect()
        if await client.is_user_authorized():
            userbot_authorized = True
            me = await client.get_me()
            stats.stats["user_id"] = me.id
            stats.stats["name"] = me.first_name or "Foydalanuvchi"
            stats.stats["username"] = me.username or ""
            stats.save()
            bot_holder.client = client
            print(f"[USERBOT] Akkauntga ulandi: {me.first_name} (@{me.username or me.id})")

            async def epic_token_keepalive(holder):
                await asyncio.sleep(5)
                while True:
                    try:
                        await holder.get_epic_webapp_token()
                    except Exception as ke_err:
                        print(f"[EPIC KEEPALIVE ERROR] {ke_err}")
                    await asyncio.sleep(1200)

            asyncio.create_task(epic_token_keepalive(bot_holder))
        else:
            print("[USERBOT] Sessiya avtorizatsiyadan o'tmagan. @Suvbelgi_bot da /login orqali kirishingiz mumkin.")
    except Exception as e:
        print(f"[USERBOT OGOHLANTIRISH] Telethon ulanishida xatolik: {e}")

    # Saved initData tekshirish
    saved_init_data_path = os.path.join(BASE_DIR, "saved_init_data.txt")
    initial_init_data = None

    if userbot_authorized:
        for init_try in range(3):
            try:
                initial_init_data = await get_gramora_init_data(client)
                if initial_init_data:
                    with open(saved_init_data_path, "w", encoding="utf-8") as sf:
                        sf.write(initial_init_data)
                    break
            except Exception as e:
                print(f"[USERBOT] initData olishda xatolik ({init_try+1}/3): {e}")
                await asyncio.sleep(2.0)

    if not initial_init_data and os.path.exists(saved_init_data_path):
        try:
            with open(saved_init_data_path, "r", encoding="utf-8") as sf:
                initial_init_data = sf.read().strip()
            if initial_init_data:
                print("[INITDATA] Saqlangan 'saved_init_data.txt' dan yuklandi!")
        except Exception:
            pass

    async def refresh_token():
        if client and client.is_connected() and await client.is_user_authorized():
            new_tok = await get_gramora_init_data(client)
            if new_tok:
                with open(saved_init_data_path, "w", encoding="utf-8") as sf:
                    sf.write(new_tok)
            return new_tok
        return None

    def start_game_bot_with_token(token: str):
        if not token:
            return
        if bot_holder.game_task and not bot_holder.game_task.done():
            bot_holder.game_task.cancel()

        game_bot = GramoraCheckersBot(
            init_data=token,
            stats_mgr=stats,
            refresh_token_func=refresh_token,
            tg_client=client
        )
        bot_holder.bot = game_bot
        bot_holder.game_task = asyncio.create_task(game_bot.run())
        print("🚀 Shashka AI GameBot muvaffaqiyatli ishga tushirildi!")

    if initial_init_data:
        start_game_bot_with_token(initial_init_data)
    else:
        print("[OGOHLANTIRISH] Hozircha initData yo'q. @Suvbelgi_bot orqali /token yoki /login yuborishingiz mumkin.")

    # =====================================================================
    # 1. TELEGRAM USERBOT SHASHKA BUYRUQLARI (.sh link / .sh off / .sh on / .sh stat)
    # =====================================================================
    @client.on(events.NewMessage(outgoing=True, pattern=r"(?i)^\.(?:sh_link|taxta|sh\s+link|natija|sh\s+natija)$"))
    async def userbot_link_handler(event):
        try:
            tunnel_url = get_tunnel_url()
            stats_url = get_stats_url()
            await event.edit(
                f"🌐 <b>Jonli Shashka Doskasi (Doimiy Havola):</b>\n<a href=\"{tunnel_url}\">{tunnel_url}</a>\n\n"
                f"📊 <b>Natijalar va O'yinlar Tarixi (Web App):</b>\n<a href=\"{stats_url}\">{stats_url}</a>\n\n"
                f"⚡ <i>Qotmasdan, Server-Sent Events (SSE) orqali 0ms kechikish bilan ko'rsatiladi.</i>",
                parse_mode="html"
            )
        except Exception as e:
            print(f"[LINK CMD ERROR] {e}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"(?i)^\.(?:sh_off|sh\s+off|off)$"))
    async def userbot_off_handler(event):
        try:
            msg = await bot_holder.turn_off(force=False)
            await event.edit(msg, parse_mode="html")
        except Exception as e:
            print(f"[OFF CMD ERROR] {e}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"(?i)^\.(?:sh_soft|sh\s+soft)$"))
    async def userbot_soft_off_handler(event):
        try:
            msg = await bot_holder.soft_turn_off()
            await event.edit(msg, parse_mode="html")
        except Exception as e:
            print(f"[SOFT OFF CMD ERROR] {e}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"(?i)^\.(?:sh_on|sh\s+on)$"))
    async def userbot_on_handler(event):
        try:
            msg = await bot_holder.turn_on()
            await event.edit(msg, parse_mode="html")
        except Exception as e:
            print(f"[ON CMD ERROR] {e}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"(?i)^\.(?:sh_stat|sh\s+stat|sh|s|stavka|muxa|sirojjidin)(?:\s+.*)?$"))
    async def userbot_stat_handler(event):
        try:
            raw_text = event.raw_text.strip()
            parts = raw_text.split()
            first_cmd = parts[0].lower().lstrip(".")
            raw_arg = parts[1].lower() if len(parts) > 1 else ""
            third_arg = parts[2].lower() if len(parts) > 2 else ""

            # Agar .muxa yoki .s muxa bo'lsa
            if first_cmd == "muxa" or raw_arg == "muxa" or third_arg == "muxa":
                sub_arg = third_arg if raw_arg == "muxa" else raw_arg
                if sub_arg in ("auto", "avto", "0"):
                    sync_account_config_stake("8191930658", "auto", None)
                    muxa_path = get_muxa_stats_file()
                    if os.path.exists(muxa_path):
                        try:
                            with open(muxa_path, "r", encoding="utf-8") as f:
                                st = json.load(f)
                            st["manual_stake"] = None
                            st["stake_mode"] = "auto"
                            with open(muxa_path, "w", encoding="utf-8") as f:
                                json.dump(st, f, indent=2, ensure_ascii=False)
                        except Exception:
                            pass
                    await event.edit("🔄 <b>Muxa (@xua202): Avtomatik dinamik stavka yoqildi!</b>", parse_mode="html")
                    return
                elif sub_arg.isdigit():
                    val = int(sub_arg)
                    sync_account_config_stake("8191930658", "manual", val)
                    muxa_path = get_muxa_stats_file()
                    if os.path.exists(muxa_path):
                        try:
                            with open(muxa_path, "r", encoding="utf-8") as f:
                                st = json.load(f)
                            st["manual_stake"] = val
                            st["stake_mode"] = "manual"
                            st["current_stake"] = val
                            with open(muxa_path, "w", encoding="utf-8") as f:
                                json.dump(st, f, indent=2, ensure_ascii=False)
                        except Exception:
                            pass
                    await event.edit(f"🎯 <b>Muxa (@xua202): Stavka {val} Stars qilib belgilandi!</b>", parse_mode="html")
                    return
                elif sub_arg in ("on", "start", "yoq"):
                    try:
                        req = urllib.request.Request("http://127.0.0.1:8767/api/control/on", headers={"User-Agent": "Bot/1.0"})
                        with urllib.request.urlopen(req, timeout=1.5) as r:
                            pass
                    except Exception:
                        pass
                    await event.edit("🟢 <b>Muxa (@xua202) boti ishga tushirildi (.on)!</b>", parse_mode="html")
                    return
                elif sub_arg in ("off", "stop", "ochir"):
                    try:
                        req = urllib.request.Request("http://127.0.0.1:8767/api/control/off", headers={"User-Agent": "Bot/1.0"})
                        with urllib.request.urlopen(req, timeout=1.5) as r:
                            pass
                    except Exception:
                        pass
                    await event.edit("🔴 <b>Muxa (@xua202) boti to'xtatildi (.off)!</b>", parse_mode="html")
                    return

                text, _ = get_muxa_dashboard_data()
                await event.edit(text, parse_mode="html", link_preview=False)
                return

            # Sirojjidin buyruqlari
            if raw_arg in ("off", "stop", "ochir", "to'xtat"):
                msg = await bot_holder.turn_off(force=False)
                await event.edit(msg, parse_mode="html")
                return

            if raw_arg in ("soft", "soft_off", "partiya"):
                msg = await bot_holder.soft_turn_off()
                await event.edit(msg, parse_mode="html")
                return

            if raw_arg in ("on", "start", "yoq", "boshla"):
                msg = await bot_holder.turn_on()
                await event.edit(msg, parse_mode="html")
                return

            if raw_arg in ("task", "vazifa", "tasks"):
                await event.edit("⏳ <i>Vazifalar ro'yxati tekshirilmoqda va bajarilmoqda...</i>", parse_mode="html")
                await bot_holder.claim_all_available_tasks()
                await asyncio.sleep(2.0)
                bal = stats.stats.get("stars_balance", 0.0)
                pr = stats.stats.get("tasks_profit", 0.0)
                cl = stats.stats.get("tasks_claimed", 0)
                await event.edit(
                    f"🎁 <b>Vazifalar avtomatik bajarildi!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⭐ <b>Joriy Stars balansi:</b> <code>{bal:.1f}</code> 🌟\n"
                    f"💎 <b>Vazifalardan jami ishlangan:</b> +<code>{pr:.1f}</code> Stars\n"
                    f"⚡ <b>Bajarilgan vazifalar soni:</b> {cl} ta\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🤖 <i>Bot avtomatik o'yinlarni davom ettiradi.</i>",
                    parse_mode="html"
                )
                return

            # .s 3 yoki .s 20 yoki .s stake 3
            stk_cand = raw_arg.replace("stake", "").replace("stavka", "").strip()
            if not stk_cand and len(parts) >= 3 and parts[2].isdigit():
                stk_cand = parts[2]
            if stk_cand.isdigit():
                val = int(stk_cand)
                stats.stats["manual_stake"] = val
                stats.stats["stake_mode"] = "manual"
                stats.stats["current_stake"] = val
                stats.save()
                sync_account_config_stake("8893717129", "manual", val)
                await event.edit(
                    f"🎯 <b>Sirojjidin stavkasi {val} Stars qilib belgilandi!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🎲 <b>Joriy stavka:</b> <code>{val}</code> Stars\n"
                    f"⚙️ <b>Rejim:</b> Qo'lda boshqaruv (Manual)\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💡 <i>Avto-stavkaga qaytish uchun:</i> <code>.s auto</code>",
                    parse_mode="html"
                )
                return

            if raw_arg in ("auto", "avto") or stk_cand in ("auto", "avto", "0"):
                stats.stats["manual_stake"] = None
                stats.stats["stake_mode"] = "auto"
                stats.save()
                sync_account_config_stake("8893717129", "auto", None)
                await event.edit(
                    "🔄 <b>Sirojjidin: Avtomatik dinamik stavka yoqildi!</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "Bot balansingiz va onlayn raqiblar soniga qarab eng mos optimal stavkani (3, 20, 100...) o'zi tanlaydi.",
                    parse_mode="html"
                )
                return

            if raw_arg == "reset":
                stats.stats["games_total"] = 0
                stats.stats["wins"] = 0
                stats.stats["losses"] = 0
                stats.stats["draws"] = 0
                stats.stats["streak"] = 0
                stats.stats["net_profit"] = 0.0
                stats.save()
                await event.edit(
                    "🧹 <b>O'yinlar sessiyasi statistikasi tozalandi!</b>\n(Balans va umumiy daromad saqlanib qoldi)",
                    parse_mode="html"
                )
                return

            tunnel_url = get_tunnel_url()
            stats_url = get_stats_url()
            text = stats.get_summary_text()
            text += f"\n\n👁 <b>Jonli Shashka Taxtasi:</b> <a href=\"{tunnel_url}\">Brauzerda ko'rish ↗️</a>"
            text += f"\n📊 <b>O'yinlar Natijalari:</b> <a href=\"{stats_url}\">Natijalar Web App ↗️</a>"
            await event.edit(text, parse_mode="html", link_preview=False)

        except Exception as err:
            print(f"[USERBOT CMD ERROR] {err}")

    # =====================================================================
    # 2. MAXSUS BOSHQARUV BOTI (@Suvbelgi_bot) — INLINE TUGMALAR
    # =====================================================================
    def is_authorized(username: str, sender_id: int = None) -> bool:
        if sender_id and (sender_id in ALLOWED_USER_IDS or sender_id in (bot_me.id, 8604188989)):
            return True
        if username and username.lower().replace("@", "") in ALLOWED_USERNAMES:
            return True
        return False

    def get_clean_epic_notification() -> str:
        acc_name = "݆݆݆݆݆݆݆݆ܻܻࣩࣩࣩࣩࣩࣩ࣯ࣩࣩࣩࣩࣩࣩࣩࣩࣩࣩࣩࣩࣩࣩࣩࣩࣩࣩࣩ݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅݅"
        username = "@Jorayevozod"
        uid = "8629013296"
        gift_name = "0.002 GRAM Balance"
        gift_price = "0.002"
        new_bal = "0.014"
        next_str = "2026-11-13 14:28:48"
        if os.path.exists("/root/epic_free_case_last.json"):
            try:
                with open("/root/epic_free_case_last.json", "r", encoding="utf-8") as f:
                    d = json.load(f)
                    gift_name = d.get("gift_name", gift_name)
                    gift_price = d.get("gift_price", gift_price)
                    new_bal = d.get("new_balance", new_bal)
                    raw_next = d.get("next_avail")
                    if raw_next:
                        dt = datetime.fromisoformat(raw_next.replace("Z", "+00:00"))
                        dt_buf = dt + timedelta(minutes=5)
                        next_str = dt_buf.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        return (
            f"🎁 EpicGift Free24 Case Ochildi!\n\n"
            f"👤 Akkaunt: {acc_name} ({username}) ({uid})\n"
            f"📦 Case: Free 24h Box\n"
            f"🎉 Tushgan sovg'a: {gift_name}\n"
            f"💰 Qiymati: {gift_price}\n"
            f"💵 Yangi balans: {new_bal}\n"
            f"⏰ Keyingi ochish vaqti: {next_str} UTC (+5 daqiqa qo'shildi)\n"
            f"🤖 Bot: @epic_gift_bot"
        )

    def get_clean_mrkt_notification() -> str:
        return (
            f"🎁 MRKT: Yangi giveawayga qatnashildi!\n\n"
            f"👤 Akkaunt: Zuhriddin (@Uzbek_Honest)\n"
            f"💎 Sovg'a: \n"
            f"📢 Kanallar: @adnan_market, @avhivuibb\n"
            f"🎟 Chipta: 1 ta olindi @mrkt"
        )

    def get_clean_channel_clean_notification() -> str:
        return (
            f"🧹 Tugagan konkurs kanallari tozalandi!\n\n"
            f"🚪 Chiqilgan kanallar: 4 ta\n"
            f"✅ Akkauntlar bo'shatildi va kanallar limiti tiklandi"
        )

    def get_notify_test_keyboard():
        btns = [
            [
                Button.inline("🎁 Epic Free Case Testi", b"test_epic"),
                Button.inline("🛍 MRKT Giveaway Testi", b"test_mrkt")
            ],
            [
                Button.inline("🧹 Kanal Tozalash Testi", b"test_clean")
            ]
        ]
        if os.path.exists("/root/epic_mrkt_hub/public_url.txt"):
            try:
                with open("/root/epic_mrkt_hub/public_url.txt", "r") as pf:
                    hub_url = pf.read().strip()
                    if hub_url:
                        btns.append([Button.url("🌐 Epic & MRKT Command Hub ↗️", hub_url)])
            except Exception:
                pass
        return btns

    # Foydalanuvchi tizimga kirish holati (Login flow)
    login_session_data = {}
    active_panels = {}  # {chat_id: msg_id} — jonli avtomatik yangilanuvchi boshqaruv paneli
    last_hashes = {}  # {chat_id: state_signature} — ortiqcha editlarni va FloodWait ni oldini olish
    user_active_account = {}  # {chat_id: "sirojjidin" | "muxa"}
    tab_store_path = "/home/ubuntu/gramora_active_tab.json" if os.path.exists("/home/ubuntu") else "/root/gramora_active_tab.json"
    flood_wait_until = {}  # {chat_id: timestamp_float} — Telegram anti-flood cheklovlarini hisobga olish
    last_auto_edit_time = {}  # {chat_id: timestamp_float} — Ortiqcha editlarni oldini olish (min 120s)

    def get_user_active_account(cid) -> str:
        s_cid = str(cid)
        if s_cid in user_active_account:
            return user_active_account[s_cid]
        if cid in user_active_account:
            return user_active_account[cid]
        if os.path.exists(tab_store_path):
            try:
                with open(tab_store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                acc = data.get(s_cid) or data.get(str(cid))
                if acc in ("sirojjidin", "muxa"):
                    user_active_account[cid] = acc
                    user_active_account[s_cid] = acc
                    return acc
            except Exception:
                pass
        return "sirojjidin"

    def set_user_active_account(cid, acc: str):
        s_cid = str(cid)
        user_active_account[cid] = acc
        user_active_account[s_cid] = acc
        try:
            cur_data = {}
            if os.path.exists(tab_store_path):
                with open(tab_store_path, "r", encoding="utf-8") as f:
                    cur_data = json.load(f)
            cur_data[s_cid] = acc
            with open(tab_store_path, "w", encoding="utf-8") as f:
                json.dump(cur_data, f, indent=2)
        except Exception as e:
            print(f"[TAB STORE ERROR] {e}")

    async def safe_edit_or_respond(event, chat_id, target_acc, text, kb, alert_msg=None, alert=False, delete_old=False):
        kb_sig = "".join(getattr(b, "text", "") for row in kb for b in row)
        edit_ok = False
        msg_id = getattr(event, "message_id", None) or active_panels.get(chat_id)

        now = time.time()
        if now < flood_wait_until.get(chat_id, 0):
            wait_rem = int(flood_wait_until[chat_id] - now)
            print(f"[PANEL UPDATE] Skipped edit for chat={chat_id} due to active FloodWait ({wait_rem}s remaining)")
            if alert_msg and hasattr(event, "answer"):
                try:
                    await event.answer(f"{alert_msg}\n⏳ (Telegram cheklovi: {wait_rem//60} daqiqa kutilmoqda)", alert=True)
                except Exception:
                    pass
            return

        def handle_flood_error(err):
            err_str = str(err).lower()
            match = re.search(r"wait of (\d+) seconds", err_str)
            if match:
                w_sec = int(match.group(1))
                flood_wait_until[chat_id] = time.time() + w_sec + 10
                last_hashes[chat_id] = f"{target_acc}|{text}|{kb_sig}"
                active_panels.pop(chat_id, None)
                print(f"[FLOODWAIT DETECTED] chat={chat_id} wait={w_sec}s")
                return w_sec
            return None

        # Agar oldingi xabarni o'chirib yangisini yuborish kerak bo'lsa (panel almashtirishda)
        if delete_old:
            if hasattr(event, "answer"):
                try:
                    if alert_msg:
                        await event.answer(alert_msg, alert=alert)
                    else:
                        await event.answer()
                except Exception:
                    pass

            # 1. Oldingi xabarni o'chirish
            if hasattr(event, "delete"):
                try:
                    await event.delete()
                except Exception as de:
                    print(f"[PANEL DELETE] event.delete error: {de}")
                    if msg_id:
                        try:
                            input_chat = await bot_client.get_input_entity(chat_id)
                            await bot_client.delete_messages(input_chat, [msg_id])
                        except Exception:
                            pass
            elif msg_id:
                try:
                    input_chat = await bot_client.get_input_entity(chat_id)
                    await bot_client.delete_messages(input_chat, [msg_id])
                except Exception:
                    pass

            # Shuningdek active_panels da boshqa eski msg_id qolgan bo'lsa tozalash
            prev_p = active_panels.get(chat_id)
            if prev_p and prev_p != msg_id:
                try:
                    input_chat = await bot_client.get_input_entity(chat_id)
                    await bot_client.delete_messages(input_chat, [prev_p])
                except Exception:
                    pass

            # 2. Yangi toza xabar yuborish
            try:
                if hasattr(event, "respond"):
                    p_msg = await event.respond(text, buttons=kb, parse_mode="html", link_preview=False)
                else:
                    input_chat = await bot_client.get_input_entity(chat_id)
                    p_msg = await bot_client.send_message(input_chat, text, buttons=kb, parse_mode="html", link_preview=False)
                if p_msg:
                    active_panels[chat_id] = p_msg.id
                    last_hashes[chat_id] = f"{target_acc}|{text}|{kb_sig}"
                    last_auto_edit_time[chat_id] = time.time()
                    print(f"[PANEL UPDATE] Old panel deleted, NEW panel {p_msg.id} sent for chat={chat_id}, acc={target_acc}")
            except Exception as se:
                handle_flood_error(se)
                print(f"[PANEL UPDATE] delete_old send error: {se}")
            return

        # 1. Try event.edit
        if hasattr(event, "edit"):
            try:
                await event.edit(text, buttons=kb, parse_mode="html", link_preview=False)
                if msg_id:
                    active_panels[chat_id] = msg_id
                edit_ok = True
                print(f"[PANEL UPDATE] event.edit SUCCESS for chat={chat_id}, acc={target_acc}")
            except Exception as e1:
                w = handle_flood_error(e1)
                print(f"[PANEL UPDATE] event.edit error: {e1}")
                if w:
                    if alert_msg and hasattr(event, "answer"):
                        try:
                            await event.answer(f"{alert_msg}\n⏳ Telegram cheklovi: {w//60} daqiqa kutilmoqda", alert=True)
                        except Exception:
                            pass
                    return

        # 2. Try bot_client.edit_message with input_chat
        if not edit_ok and msg_id:
            try:
                input_chat = None
                if hasattr(event, "get_input_chat"):
                    input_chat = await event.get_input_chat()
                if not input_chat:
                    input_chat = await bot_client.get_input_entity(chat_id)
                await bot_client.edit_message(input_chat, msg_id, text, buttons=kb, parse_mode="html", link_preview=False)
                active_panels[chat_id] = msg_id
                edit_ok = True
                print(f"[PANEL UPDATE] bot_client.edit_message SUCCESS for chat={chat_id}, acc={target_acc}")
            except Exception as e2:
                w = handle_flood_error(e2)
                print(f"[PANEL UPDATE] bot_client.edit_message error: {e2}")
                if w:
                    return

        # 3. If edit failed, send a fresh message so user ALWAYS sees the updated dashboard
        if not edit_ok:
            try:
                if msg_id:
                    try:
                        input_chat = await bot_client.get_input_entity(chat_id)
                        await bot_client.delete_messages(input_chat, [msg_id])
                    except Exception:
                        pass
                if hasattr(event, "respond"):
                    p_msg = await event.respond(text, buttons=kb, parse_mode="html", link_preview=False)
                else:
                    input_chat = await bot_client.get_input_entity(chat_id)
                    p_msg = await bot_client.send_message(input_chat, text, buttons=kb, parse_mode="html", link_preview=False)
                active_panels[chat_id] = p_msg.id
                edit_ok = True
                print(f"[PANEL UPDATE] sent FRESH message p_msg={p_msg.id} for chat={chat_id}, acc={target_acc}")
            except Exception as e3:
                handle_flood_error(e3)
                print(f"[PANEL UPDATE] fresh respond error: {e3}")

        if edit_ok:
            last_hashes[chat_id] = f"{target_acc}|{text}|{kb_sig}"
            last_auto_edit_time[chat_id] = time.time()

        if alert_msg and hasattr(event, "answer"):
            try:
                await event.answer(alert_msg, alert=alert)
            except Exception:
                pass

    def get_muxa_stats_file():
        for p in [
            "/home/ubuntu/gramora_stats_muxa.json",
            "/home/ubuntu/gramora-shashka-bot/gramora_stats_muxa.json",
            "/root/gramora_stats_muxa.json"
        ]:
            if os.path.exists(p):
                return p
        return "/home/ubuntu/gramora_stats_muxa.json" if os.path.exists("/home/ubuntu") else "/root/gramora_stats_muxa.json"

    def sync_account_config_stake(acc_id: str, stake_mode: str, manual_stake: int = None):
        for cfg_path in ["/home/ubuntu/accounts_config.json", "/root/accounts_config.json"]:
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    acc = cfg.get("accounts", {}).get(str(acc_id))
                    if acc:
                        acc["stake_mode"] = stake_mode
                        acc["manual_stake"] = manual_stake
                        if manual_stake:
                            acc["current_stake"] = manual_stake
                        with open(cfg_path, "w", encoding="utf-8") as f:
                            json.dump(cfg, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

    def get_muxa_dashboard_data():
        st = {}
        muxa_path = get_muxa_stats_file()
        if os.path.exists(muxa_path):
            try:
                with open(muxa_path, "r", encoding="utf-8") as f:
                    st = json.load(f)
            except Exception:
                pass

        ctrl = None
        try:
            req = urllib.request.Request("http://127.0.0.1:8767/api/control/status", headers={"User-Agent": "Bot/1.0"})
            with urllib.request.urlopen(req, timeout=0.8) as r:
                ctrl = json.loads(r.read().decode("utf-8"))
        except Exception:
            pass

        in_match = ctrl.get("in_match", False) if ctrl else False
        soft = ctrl.get("soft_stop", False) if ctrl else False
        is_en = ctrl.get("is_enabled", True) if ctrl else st.get("is_enabled", True)
        cur_stake = st.get("current_stake", 3)
        stake_mode = st.get("stake_mode", "auto")
        manual_stake = st.get("manual_stake")

        mode_badge = "🟢 ON (Avtopilot)" if is_en else "🔴 OFF (To'xtatilgan)"
        if soft:
            mode_badge = "⏳ Soft-Stop (O'yindan so'ng to'xtaydi)"

        status_txt = st.get("current_status", "🔍 Raqib qidirilmoqda...")
        if in_match:
            status_txt = "⚔️ O'yinda"

        web_url = "https://muhammadjon1505f-dot.github.io/gramora-live/muxa.html"
        effective_desc = f"Qo'lda ({manual_stake or cur_stake}⭐)" if stake_mode == "manual" else "Avtomatik"

        name_txt = html.escape(str(st.get("name", "ɱυxα")))
        uname_txt = html.escape(str(st.get("username", "xua202")))
        status_txt_esc = html.escape(str(status_txt))

        text = (
            "👑 <b>GRAMORA SHASHKA AI — MUXA (@xua202)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Akkaunt:</b> {name_txt} (@{uname_txt})\n"
            f"⭐ <b>Balans:</b> <b>{st.get('stars_balance', 14.5)} Stars</b>\n"
            f"📈 <b>Sof Foyda:</b> <b>{st.get('net_profit', -14.0):+.1f} Stars</b>\n"
            f"🏆 <b>Reyting:</b> <b>{st.get('rating', 1516)} ({st.get('league', 'Gold')})</b>\n"
            f"🎮 <b>O'yinlar:</b> {st.get('games_total', 53)} ta (G'alaba: {st.get('wins', 32)} | Mag'lubiyat: {st.get('losses', 16)})\n"
            f"🔥 <b>Ketma-ket yutuq:</b> {st.get('streak', 0)} (Maks: {st.get('max_streak', 11)})\n"
            f"🎯 <b>Joriy Stavka:</b> <b>{cur_stake}⭐ Stars</b> ({effective_desc})\n"
            f"⚙️ <b>Holat:</b> {mode_badge}\n"
            f"⚔️ <b>Jarayon:</b> <i>{status_txt_esc}</i>\n\n"
            f"📱 <b>Jonli Doska:</b> Pastdagi <b>«🌐 Web App»</b> tugmasini bosing"
        )

        kb = get_control_keyboard(
            is_enabled=is_en,
            current_stake=cur_stake,
            stake_mode=stake_mode,
            manual_stake=manual_stake,
            tunnel_url=web_url,
            stats_url=web_url,
            in_match=in_match,
            soft_stop=soft,
            active_account="muxa"
        )
        return text, kb

    def get_sirojjidin_dashboard_data():
        try:
            stats.load()
        except Exception:
            pass
        web_url = "https://muhammadjon1505f-dot.github.io/gramora-live/sirojjidin.html"
        text = stats.get_summary_text()
        text += "\n\n📱 <b>Jonli Doska:</b> Pastdagi <b>«🌐 Web App»</b> tugmasini bosing"

        kb = get_control_keyboard(
            is_enabled=stats.stats.get("is_enabled", True),
            current_stake=stats.stats.get("current_stake", 3),
            stake_mode=stats.stats.get("stake_mode", "auto"),
            manual_stake=stats.stats.get("manual_stake"),
            tunnel_url=web_url,
            stats_url=web_url,
            in_match=bot_holder.in_match,
            soft_stop=bot_holder.soft_stop,
            active_account="sirojjidin"
        )
        return text, kb

    @bot_client.on(events.NewMessage(incoming=True))
    async def bot_message_handler(event):
        if not event.is_private or event.out:
            return

        sender_id = event.sender_id
        if not sender_id or sender_id in (bot_me.id, 8604188989):
            return

        sender = await event.get_sender()
        uname = getattr(sender, "username", "") or ""

        if not is_authorized(uname, sender_id):
            await event.respond(
                "⛔ <b>Kechirasiz, siz ushbu botni boshqarish huquqiga ega emassiz!</b>\n\n"
                "Ushbu bot faqat @xua202 va @Sirojjidinismoilov boshqaruvi uchun sozlangan.",
                parse_mode="html"
            )
            return

        raw_text = (event.raw_text or "").strip()
        lower_text = raw_text.lower()
        is_muxa = (sender_id == 8191930658 or uname.lower().replace("@", "") == "xua202")

        # 1. Doimiy Web App havolasi (Har bir akkauntga alohida toza taxta)
        if lower_text in ("/link", "/web", "/taxta", "/doska", "link", "havola", "doska", "/natija", "/stats", "/tarix", "natija"):
            if is_muxa:
                app_url = "https://muhammadjon1505f-dot.github.io/gramora-live/muxa.html"
                msg = (
                    "👑 <b>ɱυxα (@xua202) — Jonli Shashka Doskasi:</b>\n\n"
                    "⚡ <i>Pastdagi «Web App» tugmasi orqali to'g'ridan-to'g'ri Telegram ichida ochiladi.</i>"
                )
                btns = [[types.KeyboardInlineButton(text="🌐 Web App", type=types.InlineButtonTypeWebView(url=app_url))]]
            else:
                app_url = "https://muhammadjon1505f-dot.github.io/gramora-live/sirojjidin.html"
                msg = (
                    "👑 <b>Sirojjidin — Jonli Shashka Doskasi:</b>\n\n"
                    "⚡ <i>Pastdagi «Web App» tugmasi orqali to'g'ridan-to'g'ri Telegram ichida ochiladi.</i>"
                )
                btns = [[types.KeyboardInlineButton(text="🌐 Web App", type=types.InlineButtonTypeWebView(url=app_url))]]
            await event.respond(msg, buttons=btns, parse_mode="html")
            return

        # 1.5 O'chirish va Yoqish buyruqlari (/off, /stop, /on)
        if lower_text in ("/off", "/stop", "off", "stop"):
            msg = await bot_holder.turn_off(force=False)
            await event.respond(msg, parse_mode="html")
            return

        if lower_text in ("/on", "on"):
            msg = await bot_holder.turn_on()
            await event.respond(msg, parse_mode="html")
            return

        # 1.6 Bildirishnoma testlari (/test, test, bildirishnoma, /notify, /xabar)
        if any(lower_text == x or lower_text.startswith(x + " ") for x in ("/test", "test", "bildirishnoma", "bildirishnoma testi", "/notify", "/xabar", "xabar")):
            await event.respond(
                "🔔 <b>Bildirishnoma Test Paneli:</b>\n\n"
                "Quyidagi tugmalardan birini bosing. @Suvbelgi_bot faqat va faqat tanlangan toza xabarni yuboradi (boshqa hech narsa aralashmaydi):",
                buttons=get_notify_test_keyboard(),
                parse_mode="html"
            )
            return

        if lower_text in ("/epic", "epic", "free case", "/free"):
            await event.respond(get_clean_epic_notification())
            return

        if lower_text in ("/mrkt", "mrkt", "giveaway"):
            await event.respond(get_clean_mrkt_notification())
            return

        if lower_text in ("/clean", "clean", "tozalash"):
            await event.respond(get_clean_channel_clean_notification())
            return

        if lower_text in ("/hub", "hub", "/webapp", "webapp", "/mrkt_hub"):
            hub_url = "http://127.0.0.1:8888"
            if os.path.exists("/root/epic_mrkt_hub/public_url.txt"):
                try:
                    with open("/root/epic_mrkt_hub/public_url.txt", "r") as pf:
                        h = pf.read().strip()
                        if h:
                            hub_url = h
                except Exception:
                    pass
            await event.respond(
                f"⚡ <b>Epic & MRKT Command Hub Web App:</b>\n<a href=\"{hub_url}\">{hub_url}</a>\n\n"
                f"🎁 Bepul keys ochish va barcha MRKT giveawaylariga qatnashish / tozalash boshqaruvi.",
                buttons=[[Button.url("🌐 Command Hubni Ochish ↗️", hub_url)]],
                parse_mode="html"
            )
            return

        # 2. To'g'ridan-to'g'ri initData / WebApp token kiritish
        if lower_text.startswith("/token") or "tgwebappdata=" in lower_text or "query_id=" in lower_text:
            token_input = raw_text
            if lower_text.startswith("/token"):
                token_input = raw_text[6:].strip()

            init_data = None
            if "#tgWebAppData=" in token_input:
                init_data = token_input.split("#tgWebAppData=")[1].split("&tgWebAppVersion=")[0]
            elif "tgWebAppData=" in token_input:
                init_data = token_input.split("tgWebAppData=")[1].split("&")[0]
            elif "query_id=" in token_input:
                init_data = token_input

            if init_data:
                init_data = unquote(init_data)
                with open(saved_init_data_path, "w", encoding="utf-8") as sf:
                    sf.write(init_data)
                start_game_bot_with_token(init_data)
                await event.respond(
                    f"✅ <b>Gramora WebApp tokeni qabul qilindi!</b>\n\n"
                    f"🚀 Shashka AI serverga ulandi va o'yinlarni boshladi.\n"
                    f"👁 Jonli doska: <a href=\"{tunnel_url}\">{tunnel_url}</a>",
                    buttons=[[Button.url("👁 Doskani Ochish ↗️", tunnel_url)]],
                    parse_mode="html"
                )
                return
            else:
                await event.respond("❌ Token topilmadi. Iltimos to'liq havola yoki `query_id=...` ni yuboring.")
                return

        # 3. QR-Kod orqali 1 soniyada kirish (/qr yoki /login)
        if lower_text in ("/qr", "/login", "qr", "login"):
            await event.respond("⏳ Telegram QR-kodi tayyorlanmoqda...")
            try:
                if not client.is_connected():
                    await client.connect()
                qr_login = await client.qr_login()
                img = qrcode.make(qr_login.url)
                qr_path = "/tmp/telegram_qr_login.png"
                img.save(qr_path)

                caption = (
                    "📸 <b>Telegram orqali 1 soniyada ulanish:</b>\n\n"
                    "1️⃣ Telefoningizda: <b>Telegram -> Sozlamalar -> Qurilmalar -> QR kodni skanerlash</b> bo'limiga kiring.\n"
                    "2️⃣ Kamerani ushbu rasmga qarating va <b>Tasdiqlash (Confirm)</b> tugmasini bosing!\n\n"
                    f"🔗 Yoki to'g'ridan-to'g'ri havolani bosing: <a href=\"{qr_login.url}\">Kirishni tasdiqlash</a>\n\n"
                    "💡 <i>(Agar telefon raqam orqali kirmoqchi bo'lsangiz: <code>/phone +998901234567</code>)</i>"
                )
                await event.respond(file=qr_path, caption=caption, parse_mode="html")

                async def wait_qr():
                    try:
                        await qr_login.wait()
                        me = await client.get_me()
                        stats.stats["user_id"] = me.id
                        stats.stats["name"] = me.first_name or "Foydalanuvchi"
                        stats.stats["username"] = me.username or ""
                        stats.stats["current_status"] = "🟢 Tizimga ulandi. O'yinlar boshlanmoqda"
                        stats.save()
                        await event.respond(f"🎉 <b>Muvaffaqiyatli ulandi:</b> {me.first_name} (@{me.username})!\n🚀 Shashka avtopilot ishga tushirilmoqda...", parse_mode="html")
                        tok = await get_gramora_init_data(client)
                        if tok:
                            with open(saved_init_data_path, "w", encoding="utf-8") as sf:
                                sf.write(tok)
                            start_game_bot_with_token(tok)
                            await event.respond("✅ Shashka AI muvaffaqiyatli serverga ulandi va o'yinlarni boshladi!")
                    except Exception as qe:
                        print(f"[QR WAIT ERROR] {qe}")

                asyncio.create_task(wait_qr())
            except Exception as e:
                await event.respond(f"❌ QR kod yaratishda xato: {e}")
            return

        # 4. Telefon raqam orqali kirish (/phone +99890... yoki /login +998...)
        if lower_text.startswith(("/phone", "/login")):
            parts = raw_text.split()
            if len(parts) < 2:
                await event.respond("📱 <b>Format:</b> <code>/phone +998901234567</code>", parse_mode="html")
                return
            phone = parts[1].strip()
            await event.respond(f"⏳ {phone} raqamiga Telegram tasdiqlash kodi so'ralmoqda...")
            try:
                if not client.is_connected():
                    await client.connect()
                send_res = await client.send_code_request(phone)
                login_session_data[sender_id] = {
                    "phone": phone,
                    "phone_code_hash": send_res.phone_code_hash
                }
                await event.respond(
                    f"📲 <b>{phone} raqamiga Telegram kodi yuborildi!</b>\n\n"
                    f"Kodni quyidagi formatda yuboring:\n"
                    f"<code>/code 12345</code>\n\n"
                    f"<i>(Agar 2FA parol bo'lsa: <code>/password sizning_parolingiz</code>)</i>",
                    parse_mode="html"
                )
            except Exception as login_err:
                await event.respond(f"❌ Kod so'rashda xatolik: {login_err}")
            return

        # 4. Telegram kodini tasdiqlash (/code 12345 yoki shunchaki 5 ta raqam: 12345)
        clean_code = re.sub(r"\D", "", raw_text)
        is_five_digits = len(clean_code) == 5
        if lower_text.startswith("/code") or is_five_digits:
            code = clean_code if is_five_digits else raw_text.split()[-1].strip()
            
            # Telefon va hash ma'lumotlarini olish
            phone = None
            phone_code_hash = None
            if sender_id in login_session_data:
                phone = login_session_data[sender_id].get("phone")
                phone_code_hash = login_session_data[sender_id].get("phone_code_hash")
            
            state_file_path = "/root/login_order_state.json"
            if (not phone or not phone_code_hash) and os.path.exists(state_file_path):
                try:
                    with open(state_file_path, "r", encoding="utf-8") as sf:
                        st = json.load(sf)
                        phone = st.get("phone")
                        phone_code_hash = st.get("phone_code_hash")
                except Exception:
                    pass

            if not phone or not phone_code_hash:
                await event.respond("❌ Kod yuborilgan sessiya topilmadi. Qayta kod so'rash: <code>/phone +99890...</code>", parse_mode="html")
                return

            try:
                if not client.is_connected():
                    await client.connect()
                await client.sign_in(
                    phone=phone,
                    code=code,
                    phone_code_hash=phone_code_hash
                )
                me = await client.get_me()
                stats.stats["user_id"] = me.id
                stats.stats["name"] = me.first_name or "Foydalanuvchi"
                stats.stats["username"] = me.username or ""
                stats.save()
                await event.respond(f"🎉 <b>Muvaffaqiyatli ulandi:</b> {me.first_name} (@{me.username})!\n🚀 Gramorabot'dan WebApp olinmoqda...", parse_mode="html")

                tok = await get_gramora_init_data(client)
                if tok:
                    with open(saved_init_data_path, "w", encoding="utf-8") as sf:
                        sf.write(tok)
                    start_game_bot_with_token(tok)
                    await event.respond("✅ Shashka AI avtopilot serverga ulandi va o'yinlarni boshladi!")
            except Exception as code_err:
                if "Two-steps verification is enabled" in str(code_err) or "SessionPasswordNeededError" in str(code_err):
                    await event.respond("🔐 <b>2FA Parol o'rnatilgan!</b>\nIltimos parolingizni yuboring:\n<code>/password sizning_parolingiz</code>", parse_mode="html")
                else:
                    await event.respond(f"❌ Kodni tasdiqlashda xatolik: {code_err}")
            return

        # 5. 2FA Parol kiritish (/password parol)
        if lower_text.startswith("/password"):
            parts = raw_text.split(maxsplit=1)
            if len(parts) < 2:
                await event.respond("🔐 <b>Format:</b> <code>/password sizning_parolingiz</code>", parse_mode="html")
                return
            pwd = parts[1].strip()
            try:
                await client.sign_in(password=pwd)
                me = await client.get_me()
                stats.stats["user_id"] = me.id
                stats.stats["name"] = me.first_name or "Foydalanuvchi"
                stats.stats["username"] = me.username or ""
                stats.save()
                await event.respond(f"🎉 <b>Muvaffaqiyatli ulandi:</b> {me.first_name} (@{me.username})!\nInitData olinmoqda...", parse_mode="html")

                tok = await get_gramora_init_data(client)
                if tok:
                    with open(saved_init_data_path, "w", encoding="utf-8") as sf:
                        sf.write(tok)
                    start_game_bot_with_token(tok)
                    await event.respond("🚀 Shashka AI GameBot avtomatik ishga tushirildi!")
            except Exception as pwd_err:
                await event.respond(f"❌ Parol kiritishda xato: {pwd_err}")
            return

        async def clean_old_panel():
            old_p = active_panels.get(event.chat_id)
            if old_p:
                try:
                    in_c = await event.get_input_chat()
                    await bot_client.delete_messages(in_c, [old_p])
                except Exception:
                    pass

        # Akkaunt almashtirish buyruqlari
        if lower_text in ("/sirojjidin", "/acc1", "sirojjidin", ".sirojjidin"):
            set_user_active_account(event.chat_id, "sirojjidin")
            set_user_active_account(sender_id, "sirojjidin")
            await clean_old_panel()
            text, kb = get_sirojjidin_dashboard_data()
            p_msg = await event.respond(f"👤 <b>Sirojjidin boshqaruviga o'tildi!</b>\n\n{text}", buttons=kb, parse_mode="html", link_preview=False)
            active_panels[event.chat_id] = p_msg.id
            kb_sig = "".join(getattr(b, "text", "") for row in kb for b in row)
            last_hashes[event.chat_id] = f"sirojjidin|{text}|{kb_sig}"
            return

        if lower_text in ("/muxa", "/acc2", "muxa", ".muxa"):
            set_user_active_account(event.chat_id, "muxa")
            set_user_active_account(sender_id, "muxa")
            await clean_old_panel()
            text, kb = get_muxa_dashboard_data()
            p_msg = await event.respond(f"👤 <b>Muxa boshqaruviga o'tildi!</b>\n\n{text}", buttons=kb, parse_mode="html", link_preview=False)
            active_panels[event.chat_id] = p_msg.id
            kb_sig = "".join(getattr(b, "text", "") for row in kb for b in row)
            last_hashes[event.chat_id] = f"muxa|{text}|{kb_sig}"
            return

        # Stavka o'zgartirish matnli buyruqlari (/stake, /stavka, .s, /s, /auto, /avto)
        if lower_text in ("/auto", "/avto", "auto", "avto", ".auto", ".avto") or lower_text.startswith(("/stake", "/stavka", ".s ", "/s ")):
            parts = raw_text.split()
            val_arg = "auto"
            if len(parts) >= 2:
                val_arg = parts[1].strip()
            elif lower_text in ("/auto", "/avto", "auto", "avto", ".auto", ".avto"):
                val_arg = "auto"

            target_acc = get_user_active_account(sender_id)
            if target_acc == "sirojjidin":
                if val_arg in ("auto", "avto", "0"):
                    stats.stats["manual_stake"] = None
                    stats.stats["stake_mode"] = "auto"
                    stats.save()
                    if bot_holder.bot and hasattr(bot_holder.bot, "stats_mgr"):
                        bot_holder.bot.stats_mgr.stats["manual_stake"] = None
                        bot_holder.bot.stats_mgr.stats["stake_mode"] = "auto"
                        bot_holder.bot.stats_mgr.save()
                    sync_account_config_stake("8893717129", "auto", None)
                    await event.respond("🔄 <b>Sirojjidin:</b> Avtomatik dinamik stavka yoqildi!", parse_mode="html", link_preview=False)
                else:
                    try:
                        v = int(val_arg)
                        stats.stats["manual_stake"] = v
                        stats.stats["stake_mode"] = "manual"
                        stats.stats["current_stake"] = v
                        stats.save()
                        if bot_holder.bot and hasattr(bot_holder.bot, "stats_mgr"):
                            bot_holder.bot.stats_mgr.stats["manual_stake"] = v
                            bot_holder.bot.stats_mgr.stats["stake_mode"] = "manual"
                            bot_holder.bot.stats_mgr.stats["current_stake"] = v
                            bot_holder.bot.stats_mgr.save()
                        sync_account_config_stake("8893717129", "manual", v)
                        await event.respond(f"🎯 <b>Sirojjidin:</b> Stavka <b>{v} Stars</b> qilib belgilandi!", parse_mode="html", link_preview=False)
                    except Exception as ve:
                        await event.respond(f"❌ Noto'g'ri stavka qiymati: {ve}")
                text, kb = get_sirojjidin_dashboard_data()
                p_msg = await event.respond(text, buttons=kb, parse_mode="html", link_preview=False)
                active_panels[event.chat_id] = p_msg.id
                kb_sig = "".join(getattr(b, "text", "") for row in kb for b in row)
                last_hashes[event.chat_id] = f"sirojjidin|{text}|{kb_sig}"
                return
            else:
                muxa_path = get_muxa_stats_file()
                st = {}
                if os.path.exists(muxa_path):
                    try:
                        with open(muxa_path, "r", encoding="utf-8") as f:
                            st = json.load(f)
                    except Exception:
                        pass
                if val_arg in ("auto", "avto", "0"):
                    st["manual_stake"] = None
                    st["stake_mode"] = "auto"
                    await event.respond("🔄 <b>Muxa:</b> Avtomatik dinamik stavka yoqildi!", parse_mode="html", link_preview=False)
                else:
                    try:
                        v = int(val_arg)
                        st["manual_stake"] = v
                        st["stake_mode"] = "manual"
                        st["current_stake"] = v
                        await event.respond(f"🎯 <b>Muxa:</b> Stavka <b>{v} Stars</b> qilib belgilandi!", parse_mode="html", link_preview=False)
                    except Exception as ve:
                        await event.respond(f"❌ Noto'g'ri stavka qiymati: {ve}")
                try:
                    with open(muxa_path, "w", encoding="utf-8") as f:
                        json.dump(st, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass
                try:
                    req_url = f"http://127.0.0.1:8767/api/control/stake?stake={val_arg}"
                    req = urllib.request.Request(req_url, headers={"User-Agent": "Bot/1.0"})
                    with urllib.request.urlopen(req, timeout=1.0) as _:
                        pass
                except Exception:
                    pass
                sync_account_config_stake("8191930658", "auto" if val_arg in ("auto", "avto", "0") else "manual", None if val_arg in ("auto", "avto", "0") else int(val_arg))
                text, kb = get_muxa_dashboard_data()
                p_msg = await event.respond(text, buttons=kb, parse_mode="html", link_preview=False)
                active_panels[event.chat_id] = p_msg.id
                kb_sig = "".join(getattr(b, "text", "") for row in kb for b in row)
                last_hashes[event.chat_id] = f"muxa|{text}|{kb_sig}"
                return

        # Boshqaruv paneli ko'rsatish
        active_acc = get_user_active_account(sender_id)
        if active_acc == "muxa":
            text, kb = get_muxa_dashboard_data()
        else:
            text, kb = get_sirojjidin_dashboard_data()

        await clean_old_panel()
        p_msg = await event.respond(text, buttons=kb, parse_mode="html", link_preview=False)
        active_panels[event.chat_id] = p_msg.id
        kb_sig = "".join(getattr(b, "text", "") for row in kb for b in row)
        last_hashes[event.chat_id] = f"{active_acc}|{text}|{kb_sig}"

    @bot_client.on(events.CallbackQuery)
    async def bot_callback_handler(event):
        sender = await event.get_sender()
        uname = getattr(sender, "username", "") or ""
        s_id = getattr(sender, "id", None) or event.sender_id

        if not is_authorized(uname, s_id):
            await event.answer("⛔ Sizga boshqarish ruxsati berilmagan!", alert=True)
            return

        data = event.data.decode("utf-8")
        chat_id = event.chat_id
        print(f"[CALLBACK] {data} from chat={chat_id}, sender={s_id}, msg_id={getattr(event, 'message_id', None)}")

        if data == "menu_notify_test":
            await event.respond(
                "🔔 <b>Bildirishnoma Test Paneli:</b>\n\n"
                "Quyidagi tugmalardan birini bosing. @Suvbelgi_bot faqat va faqat tanlangan toza xabarni yuboradi (boshqa hech narsa aralashmaydi):",
                buttons=get_notify_test_keyboard(),
                parse_mode="html"
            )
            await event.answer()
            return
        elif data == "test_epic":
            msg = get_clean_epic_notification()
            await event.respond(msg)
            await event.answer("✅ Epic Free Case bildirishnomasi yuborildi!", alert=False)
            return
        elif data == "test_mrkt":
            msg = get_clean_mrkt_notification()
            await event.respond(msg)
            await event.answer("✅ MRKT Giveaway bildirishnomasi yuborildi!", alert=False)
            return
        elif data == "test_clean":
            msg = get_clean_channel_clean_notification()
            await event.respond(msg)
            await event.answer("✅ Tozalash bildirishnomasi yuborildi!", alert=False)
            return

        # Tab almashtirish (Sirojjidin <-> Muxa)
        if data == "tab_sirojjidin":
            print(f"[CALLBACK] tab_sirojjidin clicked by chat_id={chat_id}, sender_id={s_id}")
            set_user_active_account(chat_id, "sirojjidin")
            set_user_active_account(s_id, "sirojjidin")
            text, kb = get_sirojjidin_dashboard_data()
            await safe_edit_or_respond(event, chat_id, "sirojjidin", text, kb, alert_msg="👤 Sirojjidin boshqaruv paneli tanlandi!", alert=False, delete_old=True)
            return

        elif data == "tab_muxa":
            print(f"[CALLBACK] tab_muxa clicked by chat_id={chat_id}, sender_id={s_id}")
            set_user_active_account(chat_id, "muxa")
            set_user_active_account(s_id, "muxa")
            text, kb = get_muxa_dashboard_data()
            await safe_edit_or_respond(event, chat_id, "muxa", text, kb, alert_msg="👤 Muxa boshqaruv paneli tanlandi!", alert=False, delete_old=True)
            return

        target_acc = get_user_active_account(chat_id)

        # Stavka o'zgartirish tugmalari
        if data.startswith("stake_"):
            val_str = data.split("_")[1]
            if target_acc == "sirojjidin":
                if val_str == "auto":
                    stats.stats["manual_stake"] = None
                    stats.stats["stake_mode"] = "auto"
                    stats.save()
                    if bot_holder.bot and hasattr(bot_holder.bot, "stats_mgr"):
                        bot_holder.bot.stats_mgr.stats["manual_stake"] = None
                        bot_holder.bot.stats_mgr.stats["stake_mode"] = "auto"
                        bot_holder.bot.stats_mgr.save()
                    sync_account_config_stake("8893717129", "auto", None)
                    for sf_path in [
                        "/home/ubuntu/gramora-shashka-bot/gramora_stats.json",
                        "/home/ubuntu/gramora_stats.json",
                        "/root/gramora_stats.json"
                    ]:
                        if os.path.exists(sf_path):
                            try:
                                with open(sf_path, "r", encoding="utf-8") as sf_f:
                                    st_sf = json.load(sf_f)
                                st_sf["manual_stake"] = None
                                st_sf["stake_mode"] = "auto"
                                with open(sf_path, "w", encoding="utf-8") as sf_f:
                                    json.dump(st_sf, sf_f, indent=2, ensure_ascii=False)
                            except Exception:
                                pass
                    alert_msg = "🔄 Sirojjidin: Avtomatik dinamik stavka yoqildi!"
                else:
                    val = int(val_str)
                    stats.stats["manual_stake"] = val
                    stats.stats["stake_mode"] = "manual"
                    stats.stats["current_stake"] = val
                    stats.save()
                    if bot_holder.bot and hasattr(bot_holder.bot, "stats_mgr"):
                        bot_holder.bot.stats_mgr.stats["manual_stake"] = val
                        bot_holder.bot.stats_mgr.stats["stake_mode"] = "manual"
                        bot_holder.bot.stats_mgr.stats["current_stake"] = val
                        bot_holder.bot.stats_mgr.save()
                    sync_account_config_stake("8893717129", "manual", val)
                    for sf_path in [
                        "/home/ubuntu/gramora-shashka-bot/gramora_stats.json",
                        "/home/ubuntu/gramora_stats.json",
                        "/root/gramora_stats.json"
                    ]:
                        if os.path.exists(sf_path):
                            try:
                                with open(sf_path, "r", encoding="utf-8") as sf_f:
                                    st_sf = json.load(sf_f)
                                st_sf["manual_stake"] = val
                                st_sf["stake_mode"] = "manual"
                                st_sf["current_stake"] = val
                                with open(sf_path, "w", encoding="utf-8") as sf_f:
                                    json.dump(st_sf, sf_f, indent=2, ensure_ascii=False)
                            except Exception:
                                pass
                    alert_msg = f"🎯 Sirojjidin stavkasi {val} Stars qilib belgilandi!"

                text, kb = get_sirojjidin_dashboard_data()
                await safe_edit_or_respond(event, chat_id, "sirojjidin", text, kb, alert_msg=alert_msg, alert=True)
                return

            else:
                # Muxa
                muxa_path = get_muxa_stats_file()
                st = {}
                if os.path.exists(muxa_path):
                    try:
                        with open(muxa_path, "r", encoding="utf-8") as f:
                            st = json.load(f)
                    except Exception:
                        pass
                if val_str == "auto":
                    st["manual_stake"] = None
                    st["stake_mode"] = "auto"
                    alert_msg = "🔄 Muxa: Avtomatik dinamik stavka yoqildi!"
                else:
                    val = int(val_str)
                    st["manual_stake"] = val
                    st["stake_mode"] = "manual"
                    st["current_stake"] = val
                    alert_msg = f"🎯 Muxa stavkasi {val} Stars qilib belgilandi!"

                try:
                    with open(muxa_path, "w", encoding="utf-8") as f:
                        json.dump(st, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass
                try:
                    req_url = f"http://127.0.0.1:8767/api/control/stake?stake={val_str}"
                    req = urllib.request.Request(req_url, headers={"User-Agent": "Bot/1.0"})
                    with urllib.request.urlopen(req, timeout=1.0) as _:
                        pass
                except Exception:
                    pass
                sync_account_config_stake("8191930658", "auto" if val_str == "auto" else "manual", None if val_str == "auto" else int(val_str))

                text, kb = get_muxa_dashboard_data()
                await safe_edit_or_respond(event, chat_id, "muxa", text, kb, alert_msg=alert_msg, alert=True)
                return

        # Boshqaruv tugmalari (Yoqish / O'chirish / Nollash / Vazifalar)
        if target_acc == "sirojjidin":
            if data == "cmd_off":
                if bot_holder.in_match:
                    await bot_holder.soft_turn_off()
                    await event.answer("⏳ Sirojjidin: Bot joriy o'yin tugagandan so'ng o'chadi!", alert=True)
                else:
                    await bot_holder.turn_off(force=False)
                    await event.answer("🔴 Sirojjidin boti to'xtatildi (.off)", alert=True)
            elif data == "cmd_soft_status":
                await event.answer("⏳ Sirojjidin: Bot joriy o'yinni yakunlamoqda. Partiya tugashi bilan avtomatik o'chadi.", alert=True)
            elif data == "cmd_soft_off":
                await bot_holder.soft_turn_off()
                await event.answer("⏳ Sirojjidin: Joriy partiya tugagach bot to'xtaydi!", alert=True)
            elif data == "cmd_on":
                await bot_holder.turn_on()
                await event.answer("🟢 Sirojjidin boti ishga tushirildi (.on)", alert=True)
            elif data == "cmd_task":
                await event.answer("⏳ Sirojjidin: Vazifalar bajarilmoqda...", alert=False)
                await bot_holder.claim_all_available_tasks()
                await asyncio.sleep(2.0)
                await event.answer("🎁 Sirojjidin vazifalari avtomatik bajarildi!", alert=True)
            elif data == "cmd_refresh":
                await event.answer("🔄 Sirojjidin ma'lumotlari yangilandi")
            elif data == "cmd_qr_login":
                await event.answer("⏳ QR-kod tayyorlanmoqda...")
                try:
                    if not client.is_connected():
                        await client.connect()
                    qr_login = await client.qr_login()
                    img = qrcode.make(qr_login.url)
                    qr_path = "/tmp/telegram_qr_login.png"
                    img.save(qr_path)
                    caption = (
                        "📸 <b>Telegram orqali 1 soniyada ulanish:</b>\n\n"
                        "1️⃣ Telefoningizda: <b>Telegram -> Sozlamalar -> Qurilmalar -> QR kodni skanerlash</b> ga kiring.\n"
                        "2️⃣ Kamerani ushbu rasmga qarating va <b>Tasdiqlash (Confirm)</b> tugmasini bosing!\n\n"
                        f"🔗 Yoki to'g'ridan-to'g'ri havolani bosing: <a href=\"{qr_login.url}\">Kirishni tasdiqlash</a>"
                    )
                    await event.respond(file=qr_path, caption=caption, parse_mode="html")

                    async def wait_qr_cb():
                        try:
                            await qr_login.wait()
                            me = await client.get_me()
                            stats.stats["user_id"] = me.id
                            stats.stats["name"] = me.first_name or "Foydalanuvchi"
                            stats.stats["username"] = me.username or ""
                            stats.stats["current_status"] = "🟢 Tizimga ulandi. O'yinlar boshlanmoqda"
                            stats.save()
                            await event.respond(f"🎉 <b>Muvaffaqiyatli ulandi:</b> {me.first_name} (@{me.username})!\n🚀 Shashka avtopilot ishga tushirilmoqda...", parse_mode="html")
                            tok = await get_gramora_init_data(client)
                            if tok:
                                with open(saved_init_data_path, "w", encoding="utf-8") as sf:
                                    sf.write(tok)
                                start_game_bot_with_token(tok)
                                await event.respond("✅ Shashka AI muvaffaqiyatli serverga ulandi va o'yinlarni boshladi!")
                        except Exception as qe:
                            print(f"[QR WAIT CB ERROR] {qe}")

                    asyncio.create_task(wait_qr_cb())
                except Exception as qe:
                    await event.respond(f"❌ QR kod tayyorlashda xato: {qe}")
            elif data == "cmd_reset":
                stats.stats["games_total"] = 0
                stats.stats["wins"] = 0
                stats.stats["losses"] = 0
                stats.stats["draws"] = 0
                stats.stats["streak"] = 0
                stats.stats["net_profit"] = 0.0
                stats.save()
                await event.answer("🧹 Sirojjidin sessiyasi nollashtirildi!", alert=True)

            text, kb = get_sirojjidin_dashboard_data()
            await safe_edit_or_respond(event, chat_id, "sirojjidin", text, kb)
            return

        else:
            # Muxa boshqaruv tugmalari
            if data in ("cmd_off", "cmd_soft_off"):
                try:
                    req = urllib.request.Request("http://127.0.0.1:8767/api/control/off", headers={"User-Agent": "Bot/1.0"})
                    with urllib.request.urlopen(req, timeout=1.5) as r:
                        resp = json.loads(r.read().decode())
                        if resp.get("soft_stop"):
                            await event.answer("⏳ Muxa boti joriy o'yin tugagandan so'ng o'chadi!", alert=True)
                        else:
                            await event.answer("🔴 Muxa boti to'xtatildi (.off)", alert=True)
                except Exception as ex:
                    await event.answer(f"Xato: {ex}", alert=True)
            elif data == "cmd_soft_status":
                await event.answer("⏳ Muxa boti joriy o'yinni yakunlamoqda. Partiya tugagach avtomatik o'chadi.", alert=True)
            elif data == "cmd_on":
                try:
                    req = urllib.request.Request("http://127.0.0.1:8767/api/control/on", headers={"User-Agent": "Bot/1.0"})
                    with urllib.request.urlopen(req, timeout=1.5) as r:
                        await event.answer("🟢 Muxa boti ishga tushirildi (.on)", alert=True)
                except Exception as ex:
                    await event.answer(f"Xato: {ex}", alert=True)
            elif data == "cmd_refresh":
                await event.answer("🔄 Muxa ma'lumotlari yangilandi")
            elif data == "cmd_reset":
                try:
                    muxa_path = get_muxa_stats_file()
                    st = {}
                    if os.path.exists(muxa_path):
                        with open(muxa_path, "r", encoding="utf-8") as f:
                            st = json.load(f)
                    st["games_total"] = 0
                    st["wins"] = 0
                    st["losses"] = 0
                    st["draws"] = 0
                    st["streak"] = 0
                    st["net_profit"] = 0.0
                    with open(muxa_path, "w", encoding="utf-8") as f:
                        json.dump(st, f, indent=2, ensure_ascii=False)
                    await event.answer("🧹 Muxa o'yinlar sessiyasi nollashtirildi!", alert=True)
                except Exception as ex:
                    await event.answer(f"Xato: {ex}", alert=True)

            text, kb = get_muxa_dashboard_data()
            await safe_edit_or_respond(event, chat_id, "muxa", text, kb)
            return

    def setup_bot_menu_buttons():
        try:
            bot_token = os.getenv("TG_BOT_TOKEN", "8604188989:AAG9x-GExIsE1-9t4_MLfV2xQ6VZkc3kTMg")
            url = f"https://api.telegram.org/bot{bot_token}/setChatMenuButton"
            
            # Default
            payload = {
                "menu_button": {
                    "type": "web_app",
                    "text": "Web App",
                    "web_app": {"url": "https://muhammadjon1505f-dot.github.io/gramora-live/"}
                }
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=3.0)

            # Sirojjidin
            s_payload = {
                "chat_id": 8893717129,
                "menu_button": {
                    "type": "web_app",
                    "text": "Web App",
                    "web_app": {"url": "https://muhammadjon1505f-dot.github.io/gramora-live/sirojjidin.html"}
                }
            }
            s_req = urllib.request.Request(url, data=json.dumps(s_payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            urllib.request.urlopen(s_req, timeout=3.0)

            # Muxa
            m_payload = {
                "chat_id": 8191930658,
                "menu_button": {
                    "type": "web_app",
                    "text": "Web App",
                    "web_app": {"url": "https://muhammadjon1505f-dot.github.io/gramora-live/muxa.html"}
                }
            }
            m_req = urllib.request.Request(url, data=json.dumps(m_payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            urllib.request.urlopen(m_req, timeout=3.0)
            print("[BOT MENU] ✅ Telegram 'Web App' menyu tugmalari muvaffaqiyatli sozlandi!")
        except Exception as be:
            print(f"[BOT MENU ERROR] {be}")

    setup_bot_menu_buttons()

    print("\n" + "=" * 65)
    print("🤖 SHASHKA AI + USERBOT + TELEGRAM BOTI HAMMASI PARALLEL ISHLAMOQDA!")
    print(f"Telegram Boti: @{bot_me.username}")
    print("Ruxsat berilganlar: @xua202 va @Sirojjidinismoilov")
    print("=" * 65 + "\n")

    async def safe_client_loop():
        while True:
            try:
                if client.is_connected() and await client.is_user_authorized():
                    await client.run_until_disconnected()
                await asyncio.sleep(5.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[USERBOT RECONNECT] Aloqa uzildi ({e}), 5 soniyada qayta ulanadi...")
                await asyncio.sleep(5.0)

    async def safe_bot_loop():
        while True:
            try:
                if not bot_client.is_connected():
                    await bot_client.connect()
                await bot_client.run_until_disconnected()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[CONTROL BOT RECONNECT] Aloqa uzildi ({e}), 5 soniyada qayta ulanadi...")
                await asyncio.sleep(5.0)

    async def auto_update_dashboard_loop():
        """Boshqaruv panelini xavfsiz avtomatik yangilab turish (FloodWait-proof, kamida 120s interval)"""
        while True:
            try:
                if active_panels and bot_client.is_connected():
                    now = time.time()
                    for chat_id, msg_id in list(active_panels.items()):
                        # Agar ushbu chat Telegram anti-flood cheklovida bo'lsa, mutlaqo so'rov yubormaslik
                        if now < flood_wait_until.get(chat_id, 0):
                            continue

                        # Rate limit: fonda har bir chat uchun kamida 120 soniyada 1 martadan ko'p tahrirlamaslik
                        if now - last_auto_edit_time.get(chat_id, 0) < 120.0:
                            continue

                        curr_acc = get_user_active_account(chat_id)
                        if curr_acc == "muxa":
                            full_text, kb = get_muxa_dashboard_data()
                        else:
                            full_text, kb = get_sirojjidin_dashboard_data()

                        kb_sig = "".join(getattr(b, "text", "") for row in kb for b in row)
                        state_key = f"{curr_acc}|{full_text}|{kb_sig}"
                        if last_hashes.get(chat_id) == state_key:
                            continue
                        try:
                            input_chat = await bot_client.get_input_entity(chat_id)
                            await bot_client.edit_message(input_chat, msg_id, full_text, buttons=kb, parse_mode="html", link_preview=False)
                            last_hashes[chat_id] = state_key
                            last_auto_edit_time[chat_id] = time.time()
                        except Exception as e:
                            err_str = str(e).lower()
                            match = re.search(r"wait of (\d+) seconds", err_str)
                            if match:
                                wait_sec = int(match.group(1))
                                flood_wait_until[chat_id] = time.time() + wait_sec + 15
                                last_hashes[chat_id] = state_key
                                active_panels.pop(chat_id, None)
                                print(f"[AUTO LOOP FLOODWAIT] {chat_id}: Pausing auto-updates for {wait_sec}s")
                            elif "messagenotmodified" in err_str:
                                last_hashes[chat_id] = state_key
                            elif "messageidinvalid" in err_str or "messageauthorrequired" in err_str:
                                active_panels.pop(chat_id, None)
                            else:
                                print(f"[AUTO LOOP EDIT ERROR] {chat_id}: {e}")
            except asyncio.CancelledError:
                break
            except Exception as loop_err:
                print(f"[AUTO PANEL LOOP ERROR] {loop_err}")
            await asyncio.sleep(20.0)

    async def game_bot_supervisor():
        """Har 1 soniyada game_task ni tekshiruvchi va agar to'xtagan bo'lsa darhol qayta yoquvchi nazoratchi"""
        while True:
            try:
                if bot_holder.game_task is None or bot_holder.game_task.done():
                    token_to_use = None
                    if os.path.exists(saved_init_data_path):
                        try:
                            with open(saved_init_data_path, "r", encoding="utf-8") as sf:
                                token_to_use = sf.read().strip()
                        except Exception:
                            pass
                    if not token_to_use:
                        token_to_use = initial_init_data
                    if token_to_use and stats.stats.get("is_enabled", True):
                        print("[SUPERVISOR] ⚠️ Game bot vazifasi to'xtagan! 1 soniyada avtomatik qayta ishga tushirilmoqda...")
                        start_game_bot_with_token(token_to_use)
            except Exception as se:
                print(f"[SUPERVISOR ERROR] {se}")
            await asyncio.sleep(1.0)

    async def mqtt_publisher_loop():
        """Barcha jonli ma'lumotlarni (balans, o'yin, reyting, taxta) MQTT orqali Web App'ga 0ms uzatib turish"""
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            print("[MQTT SYNC] ⚠️ paho-mqtt kutubxonasi topilmadi!")
            return

        c_hive = None
        c_emqx = None

        def init_clients():
            nonlocal c_hive, c_emqx
            try:
                c1 = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"vps_h_{int(time.time())}")
                c1.connect("broker.hivemq.com", 1883, 60)
                c1.loop_start()
                c_hive = c1
                print("[MQTT SYNC] ✅ HiveMQ brokerga ulandi")
            except Exception as e1:
                print(f"[MQTT] HiveMQ ulanish xatosi: {e1}")

            try:
                c2 = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"vps_e_{int(time.time())}")
                c2.connect("broker.emqx.io", 1883, 60)
                c2.loop_start()
                c_emqx = c2
                print("[MQTT SYNC] ✅ EMQX brokerga ulandi")
            except Exception as e2:
                print(f"[MQTT] EMQX ulanish xatosi: {e2}")

        init_clients()
        last_s_hash = ""
        last_m_hash = ""
        last_heartbeat = 0.0

        while True:
            try:
                now = time.time()
                if (not c_hive or not c_hive.is_connected()) and (not c_emqx or not c_emqx.is_connected()):
                    init_clients()

                # 1. Sirojjidin jonli ma'lumotlari
                s_bal = float(stats.stats.get("stars_balance", 0.0))
                s_prof = float(stats.stats.get("net_profit", 0.0))
                s_rating = int(stats.stats.get("rating", 1726))
                s_games = int(stats.stats.get("games_total", 0))
                s_wins = int(stats.stats.get("wins", 0))
                s_losses = int(stats.stats.get("losses", 0))
                s_draws = int(stats.stats.get("draws", 0))
                s_stake = int(stats.stats.get("current_stake", 3))
                s_mode = stats.stats.get("stake_mode", "auto")
                s_status = stats.stats.get("current_status", "🔍 Raqib qidirilmoqda...")
                s_enabled = stats.stats.get("is_enabled", True)

                game_bot = bot_holder.bot
                in_match = bot_holder.in_match if bot_holder else False
                if game_bot and hasattr(game_bot, "board"):
                    board = game_bot.board
                    w_count = getattr(game_bot, "w_count", 12)
                    b_count = getattr(game_bot, "b_count", 12)
                    turn = getattr(game_bot, "turn", 0)
                    last_move = getattr(game_bot, "last_move", None)
                    move_history = getattr(game_bot, "move_history", [])
                    your_seat = getattr(game_bot, "your_seat", 0)
                    opp_name = getattr(game_bot, "opp_name", "Raqib")
                    opp_rating = getattr(game_bot, "opp_rating", 0)
                    eval_score = getattr(game_bot, "eval_score", 0)
                    win_chance = getattr(game_bot, "win_chance", 98.5)
                else:
                    board = [3]*12 + [0]*8 + [1]*12
                    w_count = 12
                    b_count = 12
                    turn = 0
                    last_move = None
                    move_history = []
                    your_seat = 0
                    opp_name = "Raqib"
                    opp_rating = 0
                    eval_score = 0
                    win_chance = 98.5

                s_data = {
                    "account_id": "8893717129",
                    "my_name": "Sirojjidin",
                    "my_rating": s_rating,
                    "user_balance": s_bal,
                    "net_profit": s_prof,
                    "wins": s_wins,
                    "games_total": s_games,
                    "losses": s_losses,
                    "draws": s_draws,
                    "stake": s_stake,
                    "current_stake": s_stake,
                    "stake_mode": s_mode,
                    "in_match": in_match,
                    "is_enabled": s_enabled,
                    "status_text": s_status,
                    "board": board,
                    "w_count": w_count,
                    "b_count": b_count,
                    "turn": turn,
                    "last_move": last_move,
                    "move_history": move_history,
                    "your_seat": your_seat,
                    "opp_name": opp_name,
                    "opp_rating": opp_rating,
                    "eval_score": eval_score,
                    "eval_depth": 50,
                    "eval_nodes": 6000000,
                    "win_chance": win_chance,
                    "last_update": now
                }

                # 2. Muxa jonli ma'lumotlari
                m_live = None
                try:
                    req_m = urllib.request.Request("http://127.0.0.1:8767/api/live", headers={"User-Agent": "Syncer/1.0"})
                    with urllib.request.urlopen(req_m, timeout=0.3) as mr:
                        m_live = json.loads(mr.read().decode())
                except Exception:
                    pass

                if m_live and isinstance(m_live, dict) and "board" in m_live:
                    m_data = m_live
                    m_data["last_update"] = now
                    m_in_match = m_data.get("in_match", False)
                    m_bal = float(m_data.get("user_balance", 41.0))
                    m_status = m_data.get("status_text", "")
                    m_wins = int(m_data.get("wins", 0))
                    m_games = int(m_data.get("games_total", 0))
                    m_board = m_data.get("board", [])
                else:
                    m_st = {}
                    muxa_path = get_muxa_stats_file()
                    if os.path.exists(muxa_path):
                        try:
                            with open(muxa_path, "r", encoding="utf-8") as f:
                                m_st = json.load(f)
                        except Exception:
                            pass

                    m_bal = float(m_st.get("stars_balance", 41.0))
                    m_prof = float(m_st.get("net_profit", 18.0))
                    m_rating = int(m_st.get("rating", 1669))
                    m_wins = int(m_st.get("wins", 84))
                    m_losses = int(m_st.get("losses", 30))
                    m_draws = int(m_st.get("draws", 11))
                    m_games = int(m_st.get("games_total", 125))
                    m_stake = int(m_st.get("current_stake", 3))
                    m_status = m_st.get("current_status", "🔍 Raqib qidirilmoqda...")
                    m_in_match = m_st.get("in_match", False)
                    m_board = [3]*12 + [0]*8 + [1]*12

                    m_data = {
                        "account_id": "8191930658",
                        "my_name": "ɱυxα (@xua202)",
                        "my_rating": m_rating,
                        "user_balance": m_bal,
                        "net_profit": m_prof,
                        "wins": m_wins,
                        "games_total": m_games,
                        "losses": m_losses,
                        "draws": m_draws,
                        "stake": m_stake,
                        "current_stake": m_stake,
                        "stake_mode": m_st.get("stake_mode", "manual"),
                        "in_match": m_in_match,
                        "is_enabled": m_st.get("is_enabled", True),
                        "status_text": m_status,
                        "board": m_board,
                        "w_count": 12,
                        "b_count": 12,
                        "turn": 0,
                        "last_move": None,
                        "move_history": [],
                        "your_seat": 0,
                        "opp_name": m_st.get("last_opponent", "Raqib"),
                        "opp_rating": 0,
                        "eval_score": 0,
                        "eval_depth": 18,
                        "eval_nodes": 1000000,
                        "win_chance": 98.0,
                        "last_update": now
                    }

                s_hash = f"{in_match}_{board}_{s_bal}_{s_status}_{s_wins}_{s_games}"
                m_hash = f"{m_in_match}_{m_board}_{m_bal}_{m_status}_{m_wins}_{m_games}"
                heartbeat = (now - last_heartbeat > 2.0)

                def pub(topic, p_str):
                    if c_hive and c_hive.is_connected():
                        try: c_hive.publish(topic, p_str, qos=0, retain=True)
                        except Exception: pass
                    if c_emqx and c_emqx.is_connected():
                        try: c_emqx.publish(topic, p_str, qos=0, retain=True)
                        except Exception: pass

                if s_hash != last_s_hash or heartbeat:
                    p_s = json.dumps(s_data)
                    pub("gramora/live/sirojjidin", p_s)
                    pub("gramora/live/8893717129", p_s)
                    last_s_hash = s_hash

                if m_hash != last_m_hash or heartbeat:
                    p_m = json.dumps(m_data)
                    pub("gramora/live/muxa", p_m)
                    pub("gramora/live/8191930658", p_m)
                    last_m_hash = m_hash

                if heartbeat or s_hash != last_s_hash or m_hash != last_m_hash:
                    active_p = s_data if in_match else (m_data if m_in_match else s_data)
                    pub("gramora/live/active", json.dumps(active_p))
                    last_heartbeat = now

            except Exception:
                pass

            await asyncio.sleep(0.5)

    async def render_keepalive_loop():
        """Render bepul tarifida 15 daqiqada uyquga ketmasligi uchun har 10 daqiqada ping qilish"""
        app_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("APP_URL")
        if not app_url:
            return
        print(f"🔄 [RENDER KEEPALIVE] Avtomatik uyg'oq saqlash faol: {app_url}")
        await asyncio.sleep(45)
        while True:
            try:
                async with aiohttp.ClientSession() as k_sess:
                    async with k_sess.get(f"{app_url.rstrip('/')}/healthz", timeout=15) as k_resp:
                        print(f"💓 [RENDER KEEPALIVE] Ping muvaffaqiyatli ({k_resp.status}) - {datetime.now().strftime('%H:%M:%S')}")
            except Exception as k_err:
                print(f"⚠️ [RENDER KEEPALIVE OGOHLANTIRISH] {k_err}")
            await asyncio.sleep(600)

    # Barcha servislarni parallel tarzda 24/7 uzluksiz yurgizish
    await asyncio.gather(
        safe_client_loop(),
        safe_bot_loop(),
        auto_update_dashboard_loop(),
        game_bot_supervisor(),
        mqtt_publisher_loop(),
        render_keepalive_loop()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nBot to'xtatildi. Xayr!")
