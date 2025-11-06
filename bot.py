# -*- coding: utf-8 -*-
import os
import logging
import asyncio
import datetime
import json
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ParseMode, InputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from dotenv import load_dotenv
import aiofiles

# Загрузка конфигов
load_dotenv()
BOT_TOKEN = 8469042166:AAGTV250nbgUTHe14CVba66tFXSIwcEGG7o
ADMIN_CHAT_ID = 680094245

# Параметры продуктов (ключи используются в логике)
PRODUCTS = {
    "free": {
        "name": "🎁 ДИАГНОСТИКА ВОЛОС",
        "file": "diagnostika_volosy.pdf",
        "price": 0,
        "description": "Бесплатный гайд «Диагностика волос»",
        "caption": "🎁 *Ваш PDF-гид «Диагностика волос»*\n\n_Изучайте и применяйте! Теперь вы знаете о волосах больше, чем 90% людей_ ✨"
    },
    "seasonal": {
        "name": "🍂 ОСЕННЕ-ЗИМНИЙ УХОД",
        "file": "osenne-zimniy-uhod.pdf",
        "price": 200,
        "description": "Платный гайд «Осенне-зимний уход за волосами»",
        "caption": "🍂 *Ваш гайд «Осенне-зимний уход за волосами»*\n\n*Идеальный уход в холодное время года!*"
    },
    "consult": {
        "name": "👑 ИНДИВИДУАЛЬНАЯ КОНСУЛЬТАЦИЯ",
        "file": None,
        "price": 1500,
        "description": "Персональная консультация (30 минут)",
        "caption": "👑 *Спасибо за запись на консультацию!*"
    }
}

YOOMONEY_BASE = "https://yoomoney.ru/to/4100119396443411/"

# Логи
LOGFILE = "bot_logs.txt"
PENDING_FILE = "pending_payments.json"  # чтобы хранить pending-момент между рестартами

# Инициализация бота
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

scheduler = AsyncIOScheduler()
scheduler.start()

# В памяти: храним pending платежи {user_id: {product, amount, time, source}}
pending = {}

# Загрузить pending из файла (если есть)
if os.path.exists(PENDING_FILE):
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            pending = json.load(f)
    except Exception:
        pending = {}

# ======================================
# Утилиты
# ======================================
async def log_action(user_id, username, first_name, action, source='direct', product_type='free', amount=0):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_info = f"{user_id} (@{username}, {first_name})"
    log_message = f"{timestamp} - {action} от {user_info}"
    if source and source != 'direct':
        log_message += f" | Источник: {source}"
    if product_type and product_type != 'free':
        log_message += f" | Продукт: {product_type}"
    if amount and amount > 0:
        log_message += f" | Сумма: {amount} руб"
    print("📝", log_message)
    async with aiofiles.open(LOGFILE, 'a', encoding='utf-8') as f:
        await f.write(log_message + "\n")

    # админ оповещение для покупок/оплаты
    if action in ['ПОКУПКА_ЗАПРОС', 'PENDING_PAYMENT']:
        try:
            admin_msg = f"💰 {action}\n👤 {user_info}\nПродукт: {product_type}\nСумма: {amount} руб\nИсточник: {source}\n\nКоманда для выдачи: /grant {user_id} {product_type}"
            await bot.send_message(ADMIN_CHAT_ID, admin_msg)
        except Exception as e:
            print("Ошибка отправки админу:", e)

def get_yoomoney_link(amount: int):
    # динамически формируем ссылку — YooMoney принимает сумму в конце
    return f"{YOOMONEY_BASE}{amount}"

async def save_pending():
    # сохраняем pending в файл (json)
    try:
        async with aiofiles.open(PENDING_FILE, "w", encoding="utf-8") as f:
            await f.write(json.dumps(pending, ensure_ascii=False))
    except Exception as e:
        print("Ошибка сохранения pending:", e)

# ======================================
# Helpers: keyboard builders
# ======================================
def main_menu_markup():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton(PRODUCTS['free']['name']), types.KeyboardButton(PRODUCTS['seasonal']['name']))
    kb.add(types.KeyboardButton(PRODUCTS['consult']['name']))
    kb.add(types.KeyboardButton("ℹ️ Помощь"))
    return kb

def inline_payment_markup(product_key: str, amount: int):
    markup = types.InlineKeyboardMarkup()
    pay_url = get_yoomoney_link(amount)
    markup.add(types.InlineKeyboardButton(f"💳 Оплатить {amount} ₽", url=pay_url))
    markup.add(types.InlineKeyboardButton("✅ Я оплатил(а)", callback_data=f"confirm_payment:{product_key}"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))
    return markup

def post_buy_markup(product_key: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🌟 Подписаться на канал", url="https://t.me/volosy_v_fokuse"))
    kb.add(types.InlineKeyboardButton("💬 Заказать консультацию", callback_data="ask_consult"))
    return kb

# ======================================
# Scheduling helpers
# ======================================
def schedule_followup(user_id: int, when_datetime: datetime.datetime, follow_type: str, source='bot'):
    """
    follow_type: 'offer_paid' (после free), 'offer_consult' (после paid)
    """
    job_id = f"{user_id}_{follow_type}_{int(when_datetime.timestamp())}"
    def job_func():
        asyncio.create_task(send_followup_message(user_id, follow_type, source))
    # используем DateTrigger
    trigger = DateTrigger(run_date=when_datetime)
    scheduler.add_job(job_func, trigger=trigger, id=job_id, replace_existing=False)
    return job_id

async def send_followup_message(user_id: int, follow_type: str, source='bot'):
    try:
        if follow_type == 'offer_paid':
            text = ("Как тебе гайд? 🌷\n\n"
                    "Если хочешь, я подготовила *осенне-зимний план ухода* — "
                    "с готовыми схемами и подборкой средств. Он стоит всего *200 ₽* и позволяет сразу адаптировать уход.")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💳 Купить гайд (200 ₽)", url=get_yoomoney_link(PRODUCTS['seasonal']['price'])))
            markup.add(types.InlineKeyboardButton("✅ Я оплатил(а)", callback_data=f"confirm_payment:seasonal"))
            await bot.send_message(user_id, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
            await log_action(user_id, "unknown", "unknown", "FOLLOWUP_OFFER_PAID", source=source, product_type='seasonal', amount=PRODUCTS['seasonal']['price'])
        elif follow_type == 'offer_consult':
            text = ("Уже попробовала советы из гайда? 💕\n\n"
                    "Если хочешь, я могу подобрать тебе *персональную схему ухода* — под твой тип, бюджет и цели.\n\n"
                    "Консультация занимает 30 минут и даёт чёткий план. Стоимость — *1500 ₽*.\n\nНапиши: *Хочу консультацию*")
            await bot.send_message(user_id, text, parse_mode=ParseMode.MARKDOWN)
            await log_action(user_id, "unknown", "unknown", "FOLLOWUP_OFFER_CONSULT", source=source, product_type='consult', amount=PRODUCTS['consult']['price'])
    except Exception as e:
        print("Ошибка при отправке followup:", e)

# ======================================
# Handlers
# ======================================
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    # parse utm/source if provided: /start source_campaign
    args = message.get_args()
    source = args.strip() if args else 'direct'
    user = message.from_user
    await log_action(user.id, user.username or "нет", user.first_name or "Неизвестно", "START", source=source)
    await message.answer(
        "Привет 🌸\nЯ Лена, эксперт по уходу за волосами. Выбери, с чего начнём:",
        reply_markup=main_menu_markup()
    )

@dp.message_handler(lambda message: message.text and message.text == PRODUCTS['free']['name'])
async def handle_free(message: types.Message):
    user = message.from_user
    await log_action(user.id, user.username or "нет", user.first_name or "Неизвестно", "REQUEST_FREE", source='menu')
    # Отправляем файл
    file_name = PRODUCTS['free']['file']
    if not os.path.exists(file_name):
        await message.answer("❌ Файл временно недоступен. Свяжитесь с поддержкой.")
        return
    try:
        await message.answer_document(InputFile(file_name), caption=PRODUCTS['free']['caption'], parse_mode=ParseMode.MARKDOWN)
        await log_action(user.id, user.username or "нет", user.first_name or "Неизвестно", "SENT_FREE", source='bot', product_type='free')
        # подписка на канал кнопкой
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🌟 Подписаться на канал", url="https://t.me/volosy_v_fokuse"))
        await message.answer("🎉 Гайд отправлен! Я пришлю через пару часов оповещение с предложением платного гайда.", reply_markup=kb)
        # schedule followup in 6 hours
        when = datetime.datetime.utcnow() + datetime.timedelta(hours=6)
        schedule_followup(user.id, when, 'offer_paid', source='bot')
    except Exception as e:
        await message.answer("Ошибка при отправке файла.")
        print("send free error:", e)

@dp.message_handler(lambda message: message.text and message.text == PRODUCTS['seasonal']['name'])
async def handle_seasonal_request(message: types.Message):
    user = message.from_user
    await log_action(user.id, user.username or "нет", user.first_name or "Неизвестно", "REQUEST_SEASONAL", source='menu', product_type='seasonal', amount=PRODUCTS['seasonal']['price'])
    # show payment instructions
    markup = inline_payment_markup('seasonal', PRODUCTS['seasonal']['price'])
    payment_text = (f"🍂 *{PRODUCTS['seasonal']['description'].upper()}*\n\n"
                    f"*Стоимость:* {PRODUCTS['seasonal']['price']} рублей\n\n"
                    "Нажмите оплатить, затем — «Я оплатил(а)»")
    await message.answer(payment_text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(lambda message: message.text and message.text == PRODUCTS['consult']['name'])
async def handle_consult_request(message: types.Message):
    user = message.from_user
    await log_action(user.id, user.username or "нет", user.first_name or "Неизвестно", "REQUEST_CONSULT", source='menu', product_type='consult', amount=PRODUCTS['consult']['price'])
    markup = inline_payment_markup('consult', PRODUCTS['consult']['price'])
    consult_text = (f"👑 *{PRODUCTS['consult']['description']}*\n\n"
                    f"*Стоимость:* {PRODUCTS['consult']['price']} рублей\n\n"
                    "После оплаты напиши здесь «✅ Я оплатил(а)», и мы договоримся о времени.")
    await message.answer(consult_text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)

@dp.callback_query_handler(lambda c: c.data == "back_to_menu")
async def cb_back_to_menu(call: types.CallbackQuery):
    user = call.from_user
    await log_action(user.id, user.username or "нет", user.first_name or "Неизвестно", "NAV_BACK", source='callback')
    await bot.edit_message_text("Возвращаю меню.", call.message.chat.id, call.message.message_id)
    await bot.send_message(call.message.chat.id, "Главное меню:", reply_markup=main_menu_markup())

@dp.callback_query_handler(lambda c: c.data.startswith("confirm_payment:"))
async def cb_confirm_payment(call: types.CallbackQuery):
    user = call.from_user
    data = call.data.split(":")
    if len(data) < 2:
        await call.answer("Ошибка данных.")
        return
    product_key = data[1]
    amount = PRODUCTS.get(product_key, {}).get('price', 0)
    # помечаем pending
    pending_key = str(user.id)
    pending[pending_key] = {
        "user_id": user.id,
        "username": user.username or "нет",
        "first_name": user.first_name or "Неизвестно",
        "product": product_key,
        "amount": amount,
        "time": datetime.datetime.utcnow().isoformat()
    }
    await save_pending()
    await log_action(user.id, user.username or "нет", user.first_name or "Неизвестно", "PENDING_PAYMENT", source='bot', product_type=product_key, amount=amount)
    # уведомить пользователя и админа
    await bot.edit_message_text("✅ Мы отмечаем оплату как «Ожидающая проверка». Администратор проверит и выдаст доступ в ближайшее время.", call.message.chat.id, call.message.message_id)
    await bot.send_message(user.id, "Спасибо! Мы получили запрос на проверку оплаты. Как только админ подтвердит — получите гайд/доступ.")
    # отправляем админу сообщение (логика в log_action уже уведомляет, но добавлю подробное)
    await bot.send_message(ADMIN_CHAT_ID, f"📌 Платёж ожидает проверки:\nПользователь: {user.id} (@{user.username})\nПродукт: {product_key}\nСумма: {amount} руб\nВыдать: /grant {user.id} {product_key}")

@dp.message_handler(commands=['grant'])
async def cmd_grant(message: types.Message):
    # только админ
    if message.from_user.id != ADMIN_CHAT_ID:
        await message.reply("❌ Доступ запрещён.")
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("Использование: /grant <user_id> <product_key>")
        return
    try:
        user_id = int(parts[1])
        product_key = parts[2]
        if product_key not in PRODUCTS:
            await message.reply("Неверный product_key.")
            return
        # выдаём продукт (если pdf)
        if PRODUCTS[product_key]['file']:
            file_path = PRODUCTS[product_key]['file']
            if not os.path.exists(file_path):
                await message.reply("Файл не найден.")
                return
            await bot.send_document(user_id, InputFile(file_path), caption=PRODUCTS[product_key]['caption'], parse_mode=ParseMode.MARKDOWN)
        else:
            # для консультации — отправляем инструкцию по записи
            await bot.send_message(user_id, "Спасибо! Ваша оплата подтверждена. Напишите, пожалуйста, удобное время для консультации — и мы согласуем встречу.")
        await log_action(user_id, "unknown", "unknown", "GRANT", product_type=product_key, amount=PRODUCTS[product_key]['price'])
        # удалить из pending, если был
        pending_key = str(user_id)
        if pending_key in pending:
            pending.pop(pending_key)
            await save_pending()
        await message.reply("Готово — доступ выдан.")
    except Exception as e:
        await message.reply(f"Ошибка: {e}")

@dp.message_handler(lambda message: message.text and message.text.lower().strip() in ["я оплатил", "я оплатила", "оплатил", "оплатила", "✅ я оплатил(а)"])
async def user_confirm_paid_text(message: types.Message):
    user = message.from_user
    # если есть pending — уведомим админа
    pending_key = str(user.id)
    if pending_key in pending:
        await message.reply("Спасибо! Мы передали информацию администратору на проверку. Скоро всё подтвердим.")
        await bot.send_message(ADMIN_CHAT_ID, f"Пользователь {user.id} подтвердил оплату — проверьте: /grant {user.id} {pending[pending_key]['product']}")
    else:
        await message.reply("Если вы оплатили — нажмите кнопку «Я оплатил(а)» в оплатном меню, или пришлите скрин чека, и админ проверит оплату.")

@dp.message_handler(lambda message: message.text and message.text.lower().strip() == "хочу консультацию")
async def want_consult(message: types.Message):
    user = message.from_user
    # предложим оплату/инструкцию
    markup = inline_payment_markup('consult', PRODUCTS['consult']['price'])
    await message.answer("Чтобы записаться на консультацию, оплатите, пожалуйста:", reply_markup=markup)

@dp.message_handler(lambda message: message.text and message.text.lower().strip() == "меню")
async def show_menu_cmd(message: types.Message):
    await message.answer("Главное меню:", reply_markup=main_menu_markup())

@dp.message_handler(content_types=types.ContentTypes.ANY)
async def fallback(message: types.Message):
    # если пользователь пишет что-то неизвестное — показываем меню
    if message.text and message.text.lower().strip() in ['старт', 'start', 'начать', 'меню', 'главная']:
        await message.answer("Главное меню:", reply_markup=main_menu_markup())
        return
    # не обрабатываем файлы и т.п. иначе
    await message.answer("Я могу помочь с диагностикой, гайдом и консультацией. Нажми кнопку в меню.", reply_markup=main_menu_markup())

# ======================================
# При запуске - восстановим планировщик для уже сохранённых pending, если нужно
# ======================================
def restore_followups_from_pending():
    # для каждого pending можем переотправить followup через небольшой промежуток,
    # но обычно followups уже запланированы при выдаче free. Здесь - ничего не делаем.
    # (опционально можно реализовать восстановление по таймеру)
    pass

# ======================================
# Запуск
# ======================================
if __name__ == "__main__":
    print("Бот запускается...")
    restore_followups_from_pending()
    executor.start_polling(dp, skip_updates=True)
