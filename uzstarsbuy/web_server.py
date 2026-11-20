#!/usr/bin/env python3
"""
UzbStarsBuy Mini App Backend & Dynamic Web Server
- Serves Telegram Mini App static frontend
- Dynamic Subscription Check (/uzbstar/check_subscription.php):
  Directly synchronized with bot SQLite database (channels table) & Telegram Bot API
  When admin deletes a channel in bot, Web App immediately reflects it without modal!
  When channels exist, validates user subscription in real-time via Telegram Bot API
- Dynamic Settings Endpoint (/uzbstar/settings.php):
  Directly synchronized with bot SQLite database (prices, cards, admin, stats)
- Transparent reverse proxy for external APIs (lucky, events, etc.)
- 24/7 Auto-Healing Cloudflare Tunnel Manager with Active HTTP Watchdog
"""

import os
import sys
import time
import json
import asyncio
import logging
import urllib.parse
import urllib.request
import subprocess
import threading
import re
import pty
from typing import Optional, Dict, Any, List

import aiohttp
from aiohttp import web
from aiohttp.web_middlewares import middleware

import database as db
import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBAPP_DIR = os.path.join(BASE_DIR, "web_app")
TUNNEL_URL_FILE = os.path.join(BASE_DIR, "tunnel_url.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] [web_server] %(message)s"
)
logger = logging.getLogger("web_server")

active_cloudflared_proc = None
current_active_url = None

# ----------------- CORS MIDDLEWARE -----------------

@middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        response = web.Response(status=200)
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex
        except Exception as e:
            logger.error(f"Handler error on {request.path}: {e}")
            response = web.json_response({"ok": False, "error": str(e)}, status=500)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


# ----------------- SUBSCRIPTION CHECK -----------------

def parse_user_from_init_data(init_data: str) -> Optional[int]:
    if not init_data:
        return None
    try:
        parsed = urllib.parse.parse_qs(init_data)
        user_raw = parsed.get("user", [None])[0]
        if user_raw:
            user_dict = json.loads(user_raw)
            return user_dict.get("id")
    except Exception as e:
        logger.debug(f"Error parsing initData: {e}")
    return None


async def handle_check_subscription(request: web.Request):
    """
    Kanal tekshirish endpointi:
    /uzbstar/check_subscription.php
    /check_subscription.php
    """
    init_data = ""
    user_id = None

    if request.method == "POST":
        try:
            data = await request.json()
            if isinstance(data, dict):
                init_data = str(data.get("initData", ""))
                if "user_id" in data:
                    try:
                        user_id = int(data["user_id"])
                    except (ValueError, TypeError):
                        pass
        except Exception:
            try:
                post_data = await request.post()
                init_data = str(post_data.get("initData", ""))
                if "user_id" in post_data:
                    try:
                        user_id = int(post_data["user_id"])
                    except (ValueError, TypeError):
                        pass
            except Exception:
                pass
    elif request.method == "GET":
        init_data = str(request.query.get("initData", ""))
        if "user_id" in request.query:
            try:
                user_id = int(request.query["user_id"])
            except (ValueError, TypeError):
                pass

    if not user_id and init_data:
        user_id = parse_user_from_init_data(init_data)

    # 1. Bazadagi barcha faol majburiy obuna kanallarini olish
    channels = await db.get_active_channels()

    # Agar admin barcha kanallarni o'chirgan bo'lsa (yoki kanal yo'q bo'lsa)
    # WebApp da obuna so'ralmaydi, darhol kirishga ruxsat beriladi!
    if not channels:
        logger.info(f"Sub check: kanallar ro'yxati bo'sh, ruxsat berildi (user_id={user_id})")
        return web.json_response({
            "ok": True,
            "subscribed": True,
            "channels": [],
            "message": "Majburiy obuna kanallari mavjud emas."
        })

    # Agar kanallar bor, lekin user_id topilmasa (masalan to'g'ridan-to'g'ri brauzerdan ochilsa)
    first_ch = channels[0]
    first_name = first_ch.get("chat_id") or first_ch.get("title") or "@UZBStarsbuy"
    if not first_name.startswith("@") and "t.me/" in first_ch.get("url", ""):
        first_name = "@" + first_ch["url"].split("t.me/")[1].split("/")[0]

    if not user_id:
        return web.json_response({
            "ok": True,
            "subscribed": False,
            "channel": first_name,
            "url": first_ch.get("url", f"https://t.me/{first_name.replace('@', '')}"),
            "message": "Foydalanuvchi aniqlanmadi (initData kerak)"
        })

    # 2. Telegram Bot API orqali har bir kanalni tekshirish
    unsubscribed_ch = None
    bot_token = config.BOT_TOKEN

    async with aiohttp.ClientSession() as session:
        for ch in channels:
            chat_id = ch.get("chat_id")
            if not chat_id:
                continue
            api_url = f"https://api.telegram.org/bot{bot_token}/getChatMember"
            try:
                async with session.get(api_url, params={"chat_id": chat_id, "user_id": user_id}, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    res = await resp.json()
                    if res.get("ok"):
                        status = res.get("result", {}).get("status")
                        if status in ["left", "kicked"]:
                            unsubscribed_ch = ch
                            break
                    else:
                        err_desc = res.get("description", "")
                        logger.warning(f"getChatMember failed for {chat_id}: {err_desc}")
            except Exception as e:
                logger.error(f"Error calling getChatMember: {e}")

    if unsubscribed_ch:
        ch_target = unsubscribed_ch.get("chat_id") or ""
        if not ch_target.startswith("@") and "t.me/" in unsubscribed_ch.get("url", ""):
            ch_target = "@" + unsubscribed_ch["url"].split("t.me/")[1].split("/")[0]
        elif not ch_target.startswith("@"):
            ch_target = unsubscribed_ch.get("title", "@UZBStarsbuy")

        logger.info(f"Sub check: user {user_id} kanalga obuna emas: {ch_target}")
        return web.json_response({
            "ok": True,
            "subscribed": False,
            "channel": ch_target,
            "url": unsubscribed_ch.get("url", f"https://t.me/{ch_target.replace('@', '')}"),
            "title": unsubscribed_ch.get("title", "")
        })

    # Barcha kanallarga a'zo bo'lgan
    logger.info(f"Sub check: user {user_id} barcha kanallarga a'zo!")
    return web.json_response({
        "ok": True,
        "subscribed": True
    })


# ----------------- SOZLAMALAR ENDPOINTI -----------------

async def handle_settings(request: web.Request):
    """
    /uzbstar/settings.php
    /settings.php
    """
    star_price = await db.get_setting("star_price", "220")
    referal_price = await db.get_setting("referal_price", "100")
    card_humo = await db.get_setting("card_humo", "4067070028729676")
    card_uzcard = await db.get_setting("card_uzcard", "5614687307720079")
    humo_name = await db.get_setting("humo_name", "M/A")
    uzcard_name = await db.get_setting("uzcard_name", "M/A")
    channel_news = await db.get_setting("channel_news", "@UZBStarsbuy")
    support_admin = await db.get_setting("support_admin", "@legenda_adminn")
    total_users = await db.get_total_users()

    return web.json_response({
        "ok": True,
        "settings": {
            "referal_price": str(referal_price),
            "bot_status": "on",
            "proof": channel_news,
            "card": card_humo,
            "uzcard": card_uzcard,
            "humo_name": humo_name,
            "uzcard_name": uzcard_name,
            "admin_user": support_admin,
            "price": str(star_price),
            "postss": "200",
            "3oylik": "155000",
            "6oylik": "209000",
            "12oylik": "375000",
            "12_oylik": "295000",
            "api_key": "511a6dd9390b0c9c761bb8ea5fd93f1e",
            "tonkurs": "18800",
            "pay_status": "on",
            "users": total_users
        }
    })


# ----------------- PROXY QOLGAN ENDPOINTLAR UCHUN -----------------

async def handle_proxy(request: web.Request):
    path = request.path
    target_url = f"https://tezpremium.uz{path}"
    if request.query_string:
        target_url += f"?{request.query_string}"

    body = await request.read()
    headers = dict(request.headers)
    headers.pop("Host", None)
    headers.pop("Content-Length", None)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=body if body else None,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                resp_data = await resp.read()
                return web.Response(
                    body=resp_data,
                    status=resp.status,
                    content_type=resp.content_type
                )
    except Exception as e:
        logger.error(f"Proxy error for {target_url}: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=502)


# ----------------- STATIK FAYLLAR -----------------

async def handle_index(request: web.Request):
    index_file = os.path.join(WEBAPP_DIR, "index.html")
    if os.path.exists(index_file):
        return web.FileResponse(index_file)
    return web.Response(text="WebApp not found", status=404)


# ----------------- TUNNEL MANAGER & ACTIVE WATCHDOG -----------------

async def update_webapp_url_in_bot(tunnel_url: str):
    await db.set_setting("webapp_url", tunnel_url)
    logger.info(f"Bazada webapp_url yangilandi: {tunnel_url}")

    # Telegram bot menyu tugmasini yangilash
    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/setChatMenuButton"
        payload = {
            "menu_button": {
                "type": "web_app",
                "text": "⭐️ Xarid qilish",
                "web_app": {
                    "url": tunnel_url
                }
            }
        }
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                res = await resp.json()
                if res.get("ok"):
                    logger.info("Telegram chat menu button muvaffaqiyatli yangilandi!")
                else:
                    logger.warning(f"setChatMenuButton javobi: {res}")
        except Exception as e:
            logger.error(f"setChatMenuButton API xatosi: {e}")


def run_tunnel_watchdog():
    """
    Faol Watchdog: Har 20 soniyada joriy havola javob berayotganini tekshiradi.
    Agar havola o'chgan bo'lsa (Cloudflare seansni bekor qilgan bo'lsa),
    darhol cloudflared ni o'ldirib yangisini olishni ta'minlaydi.
    """
    global active_cloudflared_proc, current_active_url
    logger.info("Tunnel Watchdog ishga tushdi...")
    failed_count = 0
    time.sleep(15)  # Dastlabki DNS tarqalishini kutish

    while True:
        time.sleep(20)
        url = current_active_url
        if not url or not url.startswith("https://"):
            continue

        is_healthy = False
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (HealthWatchdog)"}
            )
            with urllib.request.urlopen(req, timeout=7) as resp:
                if resp.status < 500:
                    is_healthy = True
        except Exception as e:
            logger.warning(f"[WATCHDOG] Havola tekshirishda xatolik ({url}): {e}")
            is_healthy = False

        if is_healthy:
            if failed_count > 0:
                logger.info(f"[WATCHDOG] ✅ Havola sog'lom holatga qaytdi: {url}")
            failed_count = 0
        else:
            failed_count += 1
            logger.warning(f"[WATCHDOG] Muvaffaqiyatsiz tekshiruvlar: {failed_count}/3")
            if failed_count >= 3:
                logger.error(f"[WATCHDOG] 🚨 Havola ishlamayapti ({url})! Cloudflared qayta yuklanmoqda...")
                if active_cloudflared_proc:
                    try:
                        active_cloudflared_proc.kill()
                    except Exception:
                        pass
                subprocess.run(["pkill", "-9", "-f", "cloudflared tunnel"], stderr=subprocess.DEVNULL)
                failed_count = 0
                time.sleep(10)


def run_tunnel_worker():
    """
    Cloudflare Quick Tunnel (trycloudflare.com) ni orqa fonda 24/7 yurgizish.
    PTY orqali buferlash to'xtatiladi va jonli xatolar ushlanadi.
    """
    global active_cloudflared_proc, current_active_url
    logger.info("Tunnel worker ishga tushirildi...")
    time.sleep(2)

    while True:
        try:
            # Eski jarayonlarni tozalash
            try:
                subprocess.run(["pkill", "-9", "-f", "cloudflared tunnel"], stderr=subprocess.DEVNULL)
                time.sleep(0.5)
            except Exception:
                pass

            logger.info("Cloudflare tunnel ochilmoqda (port: 8088)...")
            cmd = [
                "cloudflared",
                "tunnel",
                "--no-autoupdate",
                "--url", "http://127.0.0.1:8088"
            ]

            master, slave = pty.openpty()
            proc = subprocess.Popen(
                cmd,
                stdout=slave,
                stderr=slave,
                stdin=subprocess.DEVNULL,
                close_fds=True
            )
            os.close(slave)
            active_cloudflared_proc = proc
            f = os.fdopen(master, "r", encoding="utf-8", errors="ignore")

            while True:
                line = f.readline()
                if not line:
                    if proc.poll() is not None:
                        logger.warning(f"Cloudflared to'xtadi (kod: {proc.poll()})")
                        break
                    time.sleep(0.5)
                    continue

                line_str = line.strip()

                # Xatolik aniqlansa DARHOL jarayonni o'ldirib, yangi tunnel olamiz
                if any(err_kw in line_str for err_kw in ("Tunnel not found", "Register tunnel error", "Connection terminated", "Unauthorized")):
                    logger.warning(f"Tunnel uzildi: {line_str}. 2 soniyada yangi tunnel olinmoqda...")
                    break

                # Quick tunnel URL aniqlash
                match = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", line_str)
                if match:
                    candidate = match.group(0)
                    if "api.trycloudflare.com" not in candidate and "pkg.trycloudflare.com" not in candidate:
                        if candidate != current_active_url:
                            current_active_url = candidate
                            logger.info(f"🌐 YANGI TUNNEL HAVOLASI: {candidate}")
                            # 1. Faylga yozish
                            try:
                                with open(TUNNEL_URL_FILE, "w", encoding="utf-8") as uf:
                                    uf.write(candidate)
                                    uf.flush()
                            except Exception as e:
                                logger.error(f"Faylga yozish xatosi: {e}")

                            # 2. Bazaga yozish va bot tugmasini yangilash
                            try:
                                asyncio.run(update_webapp_url_in_bot(candidate))
                            except Exception as e:
                                logger.error(f"Bot tugmasini yangilash xatosi: {e}")

            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            try:
                f.close()
            except Exception:
                pass

            logger.warning("Cloudflared qayta ulanishga tayyorlanmoqda (3 soniya)...")
        except Exception as e:
            logger.error(f"Tunnel worker xatosi: {e}")
        time.sleep(3)


def create_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])

    # API routes (aniq endpointlar)
    for p in ["/uzbstar/check_subscription.php", "/check_subscription.php", "/api/check_subscription"]:
        app.router.add_get(p, handle_check_subscription)
        app.router.add_post(p, handle_check_subscription)

    for p in ["/uzbstar/settings.php", "/settings.php", "/api/settings"]:
        app.router.add_get(p, handle_settings)
        app.router.add_post(p, handle_settings)

    # Static assets routes
    app.router.add_get("/", handle_index)
    app.router.add_static("/assets", os.path.join(WEBAPP_DIR, "assets"))

    # Proxy routes (catch-all dan oldin)
    for prefix in ["/uzbstar/{subpath:.*}", "/starsapi/{subpath:.*}", "/StarsBot/{subpath:.*}"]:
        app.router.add_route("*", prefix, handle_proxy)

    # Catch-all statik fayllar
    app.router.add_static("/", WEBAPP_DIR)

    return app


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8088"))
    logger.info(f"Starting UzbStarsBuy WebApp server on port {port}...")

    # Tunnel worker thread
    tunnel_thread = threading.Thread(target=run_tunnel_worker, daemon=True)
    tunnel_thread.start()

    # Active Watchdog thread
    watchdog_thread = threading.Thread(target=run_tunnel_watchdog, daemon=True)
    watchdog_thread.start()

    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)
