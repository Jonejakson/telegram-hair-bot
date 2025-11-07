# -*- coding: utf-8 -*-
import os
import logging
import asyncio
import datetime
import json
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ParseMode, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
import aiofiles

# =========================================
# CONFIG
# =========================================
load_dotenv()
BOT_TOKEN = "8469042166:AAGTV250nbgUTHe14CVba66tFXSIwcEGG7o"  # ← вставь свой токен
ADMIN_CHAT_ID = 680094245

PRODUCTS = {
    "free": {
        "name": "🎁 ДИАГНОСТИКА ВОЛОС",
        "file": "diagnostika_volosy.pdf",
        "price": 0,
        "caption": "🎁 *Ваш PDF-гид «Диагностика волос»*\n\nТеперь вы знаете о волосах больше, чем 90% людей ✨"
    },
    "seasonal": {
        "name": "🍂 ОСЕННЕ-ЗИМНИЙ УХОД",
        "file": "osenne-zimniy-uhod.pdf",
        "price": 200,
        "caption": "🍂 *Ваш гайд «Осенне-зимний уход за волосами»*\n\nИдеальный уход в холодное время года ☃️"
    },
    "consult": {
        "name": "👑 ИНДИВИДУАЛЬНАЯ КОНСУЛЬТАЦИЯ",
        "file": None,
        "price": 1500,
        "caption": "👑 *Спасибо за запись на консультацию!*"
    }
}

YOOMONEY_BASE = "https://yoomoney.ru/to/4100119396443411/"
LOGFILE = "bot_logs.txt"
PENDING_FILE = "pending_payments.json"
USERS_FILE = "users_sources.json"  # для хранения источников

# =========================================
# INIT
# =========================================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
pending = {}
users_sources = {}

# =========================================
# LOAD STORED DATA
# =========================================
for fname, target in [(PENDING_FILE, pending), (USERS_FILE, users_sources)]:
    if os.path.exists(fname):
        try:
            with open(fname, "r", encoding="utf-8") as f:
                data = json.load(f)
                target.update(data)
        except Exception:
            pass

# =========================================
# HELPERS
# =========================================
async def save_json(data, filename):
    try:
        async with aiofiles.open(filename, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, ensure_ascii=False))
    except Exception as e:
        print(f"Ошибка сохранения {filename}:", e)

async def log_action(user_id, username, first_name, action, extra=""):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"{ts} | {action} | {user_id} (@{username}) {first_name} {extra}\n"
    print("📝", text.strip())
    async with aiofiles.open(LOGFILE, "a", encoding="utf-8") as f:
        await f.write(text)
    try:
        await bot.send_message(ADMIN_CHAT_ID, f"📋 {action}\n👤 {user_id} (@{username}) {first_name}\n{extra}")
    except:
        pass

def get_yoomoney_link(amount):
    return f"{YOOMONEY_BASE}{amount}"

def main_menu_markup():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(PRODUCTS['free']['name'], PRODUCTS['seasonal']['name'])
    kb.add(PRODUCTS['consult']['name'])
    kb.add("ℹ️ Помощь")
    return kb

def inline_payment_markup(product_key: str, amount: int):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(f"💳 Оплатить {amount} ₽", url=get_yoomoney_link(amount)))
    kb.add(InlineKeyboardButton("✅ Я оплатил(а)", callback_data=f"confirm_payment:{product_key}"))
    return kb

# =========================================
# FOLLOW-UP (отложенные сообщения)
# =========================================
async def delayed_followup(user_id, follow_type, delay_hours=6):
    await asyncio.sleep(delay_hours * 3600)
    try:
        if follow_type == "offer_paid":
            txt = ("Как тебе гайд? 🌷\n\n"
                   "Хочешь получить *осенне-зимний уход* с конкретными схемами и рекомендациями?\n"
                   "Он стоит всего *200 ₽*.")
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("💳 Купить гайд (200 ₽)", url=get_yoomoney_link(PRODUCTS['seasonal']['price'])))
            kb.add(InlineKeyboardButton("✅ Я оплатил(а)", callback_data="confirm_payment:seasonal"))
            await bot.send_message(user_id, txt, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print("Ошибка followup:", e)

# =========================================
# TRACK переходов в бота
# =========================================
@dp.my_chat_member_handler()
async def track_join(event: types.ChatMemberUpdated):
    user = event.from_user
    if event.new_chat_member.status == "member":
        await log_action(user.id, user.username or "нет", user.first_name or "Неизвестно", "USER_ENTERED")

# =========================================
# START — фиксирует источник (UTM)
# =========================================
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    user = message.from_user
    args = message.get_args().strip() if message.get_args() else "direct"
    users_sources[str(user.id)] = args
    await save_json(users_sources, USERS_FILE)
    await log_action(user.id, user.username or "нет", user.first_name or "Неизвестно",
                     "START", f"Источник: {args}")
    await message.answer(
        "Привет 🌸 Я Лена, эксперт по уходу за волосами.\nВыбери, с чего начнём:",
        reply_markup=main_menu_markup()
    )

# =========================================
# FREE GUIDE
# =========================================
@dp.message_handler(lambda m: m.text == PRODUCTS['free']['name'])
async def handle_free(message: types.Message):
    user = message.from_user
    source = users_sources.get(str(user.id), "direct")
    await log_action(user.id, user.username or "нет", user.first_name, "DOWNLOAD_FREE_GUIDE", f"Источник: {source}")
    try:
        await message.answer_document(InputFile(PRODUCTS['free']['file']),
                                      caption=PRODUCTS['free']['caption'],
                                      parse_mode=ParseMode.MARKDOWN)
        await message.answer("🎉 Гайд отправлен! Через 6 часов пришлю дополнительный материал 💛")
        asyncio.create_task(delayed_followup(user.id, "offer_paid", 6))
    except Exception as e:
        await message.answer("❌ Файл недоступен. Свяжитесь с поддержкой.")
        print("Ошибка отправки файла:", e)

# =========================================
# ПЛАТНЫЕ ПРОДУКТЫ
# =========================================
@dp.message_handler(lambda m: m.text == PRODUCTS['seasonal']['name'])
async def seasonal_handler(message: types.Message):
    user = message.from_user
    source = users_sources.get(str(user.id), "direct")
    await log_action(user.id, user.username or "нет", user.first_name,
                     "REQUEST_SEASONAL", f"Источник: {source}")
    kb = inline_payment_markup("seasonal", PRODUCTS['seasonal']['price'])
    await message.answer(f"🍂 *{PRODUCTS['seasonal']['name']}*\nСтоимость: {PRODUCTS['seasonal']['price']} ₽",
                         parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

@dp.message_handler(lambda m: m.text == PRODUCTS['consult']['name'])
async def consult_handler(message: types.Message):
    user = message.from_user
    source = users_sources.get(str(user.id), "direct")
    await log_action(user.id, user.username or "нет", user.first_name,
                     "REQUEST_CONSULT", f"Источник: {source}")
    kb = inline_payment_markup("consult", PRODUCTS['consult']['price'])
    await message.answer(f"👑 {PRODUCTS['consult']['name']}\nСтоимость: {PRODUCTS['consult']['price']} ₽",
                         reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# =========================================
# CONFIRM PAYMENT + кнопка для выдачи
# =========================================
@dp.callback_query_handler(lambda c: c.data.startswith("confirm_payment:"))
async def confirm_payment(call: types.CallbackQuery):
    user = call.from_user
    product_key = call.data.split(":")[1]
    source = users_sources.get(str(user.id), "direct")
    pending[str(user.id)] = {
        "user_id": user.id,
        "product": product_key,
        "source": source,
        "time": datetime.datetime.utcnow().isoformat()
    }
    await save_json(pending, PENDING_FILE)
    await log_action(user.id, user.username or "нет", user.first_name,
                     "PAYMENT_PENDING", f"Продукт: {product_key} | Источник: {source}")
    await call.message.answer("✅ Мы отметили оплату. Администратор скоро подтвердит и пришлёт материал.")
    
    # кнопка "Выдать продукт" для админа
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Выдать продукт", callback_data=f"grant_user:{user.id}"))
    await bot.send_message(ADMIN_CHAT_ID,
        f"💰 Новый платёж ожидает проверки\n👤 {user.id} (@{user.username})\nПродукт: {product_key}\nИсточник: {source}",
        reply_markup=kb)

# =========================================
# ГРАНТ через кнопку
# =========================================
@dp.callback_query_handler(lambda c: c.data.startswith("grant_user:"))
async def grant_user(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_CHAT_ID:
        return await call.answer("Нет доступа.", show_alert=True)
    user_id = call.data.split(":")[1]
    if user_id not in pending:
        return await call.answer("Нет данных об ожидании.", show_alert=True)
    product_key = pending[user_id]["product"]
    prod = PRODUCTS[product_key]
    source = pending[user_id].get("source", "direct")
    try:
        if prod["file"]:
            await bot.send_document(int(user_id), InputFile(prod["file"]),
                                    caption=prod["caption"], parse_mode=ParseMode.MARKDOWN)
        else:
            await bot.send_message(int(user_id),
                                   "Спасибо! Ваша консультация подтверждена. Напишите удобное время 💬")
        await log_action(user_id, "unknown", "unknown",
                         "GRANT_ISSUED", f"Продукт: {product_key} | Источник: {source}")
        del pending[user_id]
        await save_json(pending, PENDING_FILE)
        await call.answer("✅ Продукт выдан", show_alert=True)
        await call.message.edit_text(f"✅ Продукт {product_key} выдан пользователю {user_id}.")
    except Exception as e:
        await call.answer(f"Ошибка: {e}", show_alert=True)

# =========================================
# START BOT
# =========================================
if __name__ == "__main__":
    print("Бот запущен ✅")
    executor.start_polling(dp, skip_updates=True)
