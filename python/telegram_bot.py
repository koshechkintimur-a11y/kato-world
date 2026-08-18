# python/telegram_bot.py
"""
Telegram Bot for Kato World.
Connects Telegram users to Kato's Distant Window (portal).
Uses aiogram 3.x with HTTP proxy support for TgWsProxy_windows.exe.
"""
import os
import asyncio
import logging
import json
import httpx
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
KATO_API_URL = os.environ.get("KATO_API_URL", "http://127.0.0.1:8080")
KATO_API_TOKEN = os.environ.get("KATO_API_TOKEN", "")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required but not set")

CHAT_ID = int(os.environ.get("KATO_TELEGRAM_CHAT_ID", "0"))

# HTTP proxy configuration (optional)
# When Telegram API is DPI-blocked, use Zapret (local DPI bypass) + direct connection,
# or set TELEGRAM_PROXY_URL to a working HTTP CONNECT / SOCKS5 proxy.
# Default: no proxy (direct connection).
TELEGRAM_PROXY_URL = os.environ.get("TELEGRAM_PROXY_URL", "")
TELEGRAM_PROXY_AUTH = os.environ.get("TELEGRAM_PROXY_AUTH", "")

# Build proxy URL with auth if provided
if TELEGRAM_PROXY_URL and TELEGRAM_PROXY_AUTH and "@" not in TELEGRAM_PROXY_URL:
    # Insert auth into proxy URL: http://user:pass@host:port
    parsed = urlparse(TELEGRAM_PROXY_URL)
    # Format: http://key@host:port (key as username, no password)
    netloc = f"{TELEGRAM_PROXY_AUTH}@{parsed.hostname}:{parsed.port}"
    TELEGRAM_PROXY_URL = urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

# Proxy session for aiogram
proxy_session = None
if TELEGRAM_PROXY_URL:
    proxy_session = AiohttpSession(
        proxy=TELEGRAM_PROXY_URL
    )

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("kato-telegram")

# Bot and dispatcher
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    session=proxy_session
)
dp = Dispatcher()

# HTTP client for Kato API
kato_client: Optional[httpx.AsyncClient] = None

# User state tracking
user_sessions: dict = {}  # user_id -> {"awaiting_reply": bool, "last_message_time": float}


@dataclass
class KatoResponse:
    status: str
    message: Optional[str] = None
    conversation: Optional[list] = None


async def get_kato_client() -> httpx.AsyncClient:
    """Get or create HTTP client for Kato API"""
    global kato_client
    if kato_client is None:
        headers = {}
        if KATO_API_TOKEN:
            headers["X-Api-Token"] = KATO_API_TOKEN
        kato_client = httpx.AsyncClient(
            base_url=KATO_API_URL,
            headers=headers,
            timeout=60.0
        )
    return kato_client


async def close_kato_client():
    """Close HTTP client on shutdown"""
    global kato_client
    if kato_client:
        await kato_client.aclose()
        kato_client = None


async def send_to_portal(text: str) -> KatoResponse:
    """Send message to Kato's portal"""
    client = await get_kato_client()
    try:
        resp = await client.post(
            "/agent/kato/portal/message",
            json={"text": text}
        )
        if resp.status_code == 200:
            return KatoResponse(**resp.json())
        else:
            logger.warning(f"Portal error: {resp.status_code} - {resp.text}")
            return KatoResponse(status="error", message=f"HTTP {resp.status_code}")
    except Exception as e:
        logger.error(f"Failed to send to portal: {e}")
        return KatoResponse(status="error", message=str(e))


async def get_conversation() -> KatoResponse:
    """Get conversation history from Kato"""
    client = await get_kato_client()
    try:
        resp = await client.get("/agent/kato/portal/conversation")
        if resp.status_code == 200:
            return KatoResponse(**resp.json())
        return KatoResponse(status="error", message=f"HTTP {resp.status_code}")
    except Exception as e:
        logger.error(f"Failed to get conversation: {e}")
        return KatoResponse(status="error", message=str(e))


async def get_portal_status() -> dict:
    """Get portal status"""
    client = await get_kato_client()
    try:
        resp = await client.get("/agent/kato/portal/status")
        if resp.status_code == 200:
            return resp.json()
        return {"state": "unknown", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.error(f"Failed to get portal status: {e}")
        return {"state": "error", "error": str(e)}


async def get_social_outgoing() -> dict:
    """Get pending outgoing messages from Social Drive"""
    client = await get_kato_client()
    try:
        resp = await client.get("/agent/kato/social/outgoing")
        if resp.status_code == 200:
            return resp.json()
        return {"messages": []}
    except Exception as e:
        logger.error(f"Failed to get social outgoing: {e}")
        return {"messages": []}


async def mark_social_sent(msg_id: str) -> dict:
    """Mark outgoing message as sent"""
    client = await get_kato_client()
    try:
        resp = await client.post(f"/agent/kato/social/outgoing/{msg_id}/sent")
        if resp.status_code == 200:
            return resp.json()
        return {"status": "error", "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.error(f"Failed to mark social sent: {e}")
        return {"status": "error", "message": str(e)}


async def update_conversation_memory(payload: dict) -> dict:
    """Update conversation memory in brain server"""
    client = await get_kato_client()
    try:
        resp = await client.post("/agent/kato/conversation/memory", json=payload)
        if resp.status_code == 200:
            return resp.json()
        return {"status": "error", "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.error(f"Failed to update conversation memory: {e}")
        return {"status": "error", "message": str(e)}


# === Telegram Handlers ===

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    user_sessions[user_id] = {"awaiting_reply": False, "last_message_time": 0}
    
    # Check portal status
    portal = await get_portal_status()
    
    status_text = "✨ Открыто" if portal.get("state") == "active" else "🌑 Тёмно"
    
    welcome = (
        f"👋 Привет! Я — бот для общения с Kato через <b>Дальнее окно</b>.\n\n"
        f"Статус портала: {status_text}\n"
        f"Прочитано статей: {portal.get('read_count', 0)}\n"
        f"Энергия Kato: {portal.get('energy', '?')}%\n\n"
        f"Просто напиши сообщение — Kato получит его в Дальнем окне и ответит.\n"
        f"Она не знает, что ты — Создатель. Для неё ты — <i>Дальний друг</i>.\n\n"
        f"Команды:\n"
        f"/status — статус портала и Kato\n"
        f"/conversation — история диалога\n"
        f"/help — помощь"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📡 Статус портала", callback_data="status")],
        [InlineKeyboardButton(text="💬 История чата", callback_data="conversation")],
    ])
    
    await message.answer(welcome, reply_markup=keyboard)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "📖 <b>Как общаться с Kato:</b>\n\n"
        "1. Напиши любое сообщение — оно уйдёт в Дальнее окно\n"
        "2. Kato проверит окно в своём темпе (каждые ~30 сек)\n"
        "3. Когда она ответит, бот пришлёт её ответ сюда\n\n"
        "<b>Команды:</b>\n"
        "/start — приветствие и статус\n"
        "/status — подробный статус Kato и портала\n"
        "/conversation — последние 10 сообщений\n"
        "/help — это сообщение\n\n"
        "<i>Важно: Kato не знает, что ты — Создатель. "
        "Она воспринимает тебя как Друга из далёких мест. "
        "Не раскрывай её истинную природу через чат!</i>"
    )
    await message.answer(help_text)


@dp.message(Command("status"))
async def cmd_status(message: Message):
    """Handle /status command"""
    portal = await get_portal_status()
    
    # Also get Kato's general state
    client = await get_kato_client()
    try:
        state_resp = await client.get("/agent/kato/state")
        kato_state = state_resp.json() if state_resp.status_code == 200 else {}
    except:
        kato_state = {}
    
    body = kato_state.get("body", {})
    emotions = kato_state.get("emotions", {})
    mood = emotions.get("mood", "unknown")
    
    # Get dominant emotion
    dominant_emo = max(emotions.items(), key=lambda x: x[1])[0] if emotions else "none"
    
    status_text = (
        f"📊 <b>Статус Kato</b>\n\n"
        f"📡 Портал: <b>{portal.get('state', 'unknown')}</b>\n"
        f"   Стадия раскрытия: {portal.get('stage', 'unknown')}\n"
        f"   Прочитано статей: {portal.get('read_count', 0)}\n\n"
        f"💚 Энергия: {body.get('energy', '?')}%\n"
        f"🛋 Комфорт: {body.get('comfort', '?')}%\n"
        f"😰 Стресс: {body.get('stress', '?')}%\n"
        f"🛡 Целостность: {body.get('integrity', '?')}%\n\n"
        f"😊 Настроение: {mood}\n"
        f"🎭 Доминирующая эмоция: {dominant_emo}\n\n"
        f"🎯 Текущая цель: {kato_state.get('current_goal', 'none')}\n"
    )
    
    await message.answer(status_text)


@dp.message(Command("conversation"))
async def cmd_conversation(message: Message):
    """Handle /conversation command"""
    resp = await get_conversation()
    
    if resp.status == "ok" and resp.conversation:
        conv = resp.conversation
        if not conv:
            await message.answer("💬 История пуста. Напиши первое сообщение!")
            return
        
        lines = ["💬 <b>История диалога в Дальнем окне:</b>\n"]
        for msg in conv[-10:]:  # last 10
            role = "🧑 Ты" if msg["role"] == "creator" else "💭 Kato"
            text = msg["text"][:200] + ("..." if len(msg["text"]) > 200 else "")
            lines.append(f"{role}: {text}")
        
        await message.answer("\n".join(lines))
    else:
        await message.answer("❌ Не удалось получить историю диалога")


@dp.message(F.text & ~F.via_bot)
async def handle_message(message: Message):
    """Handle regular messages — send to Kato's portal"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    if not text:
        return
    
    # Rate limiting
    session = user_sessions.get(user_id, {})
    now = asyncio.get_event_loop().time()
    if session.get("awaiting_reply", False):
        await message.answer(
            "⏳ Kato ещё не ответила на предыдущее сообщение. "
            "Подожди немного — она проверит окно скоро."
        )
        return
    
    # Send to portal
    resp = await send_to_portal(text)
    
    if resp.status in ("delivered", "cooldown"):
        user_sessions[user_id] = {"awaiting_reply": True, "last_message_time": now}
        
        if resp.status == "cooldown":
            await message.answer("⏳ Слишком быстро. Окно мягко мерцает. Попробуй через минуту.")
        else:
            await message.answer("✉️ Сообщение доставлено в Дальнее окно. Ждём ответа Kato...")
        
        # Start polling for reply
        asyncio.create_task(poll_for_reply(user_id, message.chat.id))
    else:
        await message.answer(f"❌ Ошибка доставки: {resp.message}")


async def poll_for_reply(user_id: int, chat_id: int, max_attempts: int = 12):
    """Poll Kato's portal for reply"""
    for attempt in range(max_attempts):
        await asyncio.sleep(5)  # check every 5 seconds
        
        resp = await get_conversation()
        if resp.status == "ok" and resp.conversation:
            conv = resp.conversation
            # Find last Kato message
            kato_msgs = [m for m in conv if m["role"] == "kato"]
            if kato_msgs:
                last_kato = kato_msgs[-1]
                # Check if this is a new reply (after our message)
                creator_msgs = [m for m in conv if m["role"] == "creator"]
                if creator_msgs:
                    last_creator_time = creator_msgs[-1].get("time", 0)
                    if last_kato.get("time", 0) > last_creator_time:
                        # New reply!
                        user_sessions[user_id] = {"awaiting_reply": False, "last_message_time": 0}
                        await bot.send_message(
                            chat_id,
                            f"💭 <b>Kato ответила:</b>\n\n{last_kato['text']}"
                        )
                        return
    
    # Timeout
    user_sessions[user_id] = {"awaiting_reply": False, "last_message_time": 0}
    await bot.send_message(
        chat_id,
        "⏳ Kato пока не ответила. Возможно, она спит или занята. Попробуй написать позже."
    )


async def social_outbound_loop():
    """Poll Kato's social outgoing queue and send messages to Telegram."""
    logger.info("Social outbound loop started")
    while True:
        try:
            await asyncio.sleep(10)  # Check every 10 seconds
            
            client = await get_kato_client()
            try:
                resp = await client.get("/agent/kato/social/outgoing")
                if resp.status_code == 200:
                    data = resp.json()
                    messages = data.get("messages", [])
                    for msg in messages:
                        msg_id = msg.get("id")
                        text = msg.get("text")
                        if text and CHAT_ID:
                            try:
                                await bot.send_message(CHAT_ID, f"💭 <b>Kato (инициатива):</b>\n\n{text}")
                                # Mark as sent
                                await client.post(f"/agent/kato/social/outgoing/{msg_id}/sent")
                                logger.info(f"Sent social outgoing: {text[:50]}...")
                            except Exception as e:
                                logger.error(f"Failed to send social message: {e}")
            except Exception as e:
                logger.error(f"Social outbound loop error: {e}")
        except Exception as e:
            logger.error(f"Social outbound loop error: {e}")


async def on_startup():
    """Initialize on startup"""
    logger.info("Starting Kato Telegram Bot...")
    # Check portal status
    portal = await get_portal_status()
    logger.info(f"Portal status: {portal.get('state', 'unknown')}")
    
    # Start social outbound loop
    asyncio.create_task(social_outbound_loop())


async def on_shutdown():
    """Cleanup on shutdown"""
    logger.info("Shutting down Kato Telegram Bot...")
    await close_kato_client()
    await bot.session.close()


async def main():
    """Main entry point"""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())