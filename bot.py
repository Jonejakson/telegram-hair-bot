# -*- coding: utf-8 -*-
import telebot
from telebot import types
import os
import time
import datetime

# Конфигурация
BOT_TOKEN = "8469042166:AAGTV250nbgUTHe14CVba66tFXSIwcEGG7o"
CHANNEL_USERNAME = "volosy_v_fokuse"
CHANNEL_CHAT_ID = -1002194057942
ADMIN_CHAT_ID = "680094245"

# Продукты
PRODUCTS = {
    'free': {
        'name': '🎁 ДИАГНОСТИКА ВОЛОС',
        'file': 'diagnostika_volosy.pdf',
        'price': 0,
        'description': 'Бесплатный гайд «Диагностика волос»',
        'caption': "🎁 **Ваш PDF-гид «Диагностика волос»**\n\n_Изучайте и применяйте! Теперь вы знаете о волосах больше, чем 90% людей_ ✨"
    },
    'seasonal': {
        'name': '🍂 ОСЕННЕ-ЗИМНИЙ УХОД',
        'file': 'osenne-zimniy-uhod.pdf',
        'price': 200,
        'description': 'Платный гайд «Осенне-зимний уход за волосами»',
        'caption': "🍂 **Ваш гайд «Осенне-зимний уход за волосами»**\n\n*Идеальный уход в холодное время года!*\n\nСохраните красоту и здоровье волос зимой! ❄️"
    }
}

# Фиксированная ссылка оплаты для сезонного гайда
YOOMONEY_LINK = f"https://yoomoney.ru/to/4100119396443411/{PRODUCTS['seasonal']['price']}"

bot = telebot.TeleBot(BOT_TOKEN)

def log_action(user_id, username, first_name, action, source='direct', product_type='free', amount=0):
    """Универсальная функция логирования"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_info = f"{user_id} (@{username}, {first_name})"
    
    log_message = f"{timestamp} - {action} от {user_info}"
    if source != 'direct':
        log_message += f" | Источник: {source}"
    if product_type != 'free':
        log_message += f" | Продукт: {product_type}"
    if amount > 0:
        log_message += f" | Сумма: {amount} руб"
    
    print(f"📝 {log_message}")
    
    with open('bot_logs.txt', 'a', encoding='utf-8') as f:
        f.write(f"{log_message}\n")
    
    if action in ['ПОКУПКА', 'УСПЕШНАЯ ОПЛАТА']:
        try:
            admin_msg = f"💰 {action}\n👤 {user_info}"
            if amount > 0:
                admin_msg += f"\n💵 Сумма: {amount} руб"
            bot.send_message(ADMIN_CHAT_ID, admin_msg)
        except Exception as e:
            print(f"Ошибка отправки админу: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "нет"
    first_name = message.from_user.first_name or "Неизвестно"
    
    source = message.text.replace('/start ', '').strip()
    if not source:
        source = 'direct'
    
    log_action(user_id, username, first_name, 'START', source)
    show_main_menu(message.chat.id, user_id, username, first_name, source)

def show_main_menu(chat_id, user_id, username, first_name, source):
    """Показывает главное меню с выбором продуктов"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    
    free_btn = types.KeyboardButton(PRODUCTS['free']['name'])
    seasonal_btn = types.KeyboardButton(PRODUCTS['seasonal']['name'])
    consultation_btn = types.KeyboardButton("👑 КОНСУЛЬТАЦИЯ")
    info_btn = types.KeyboardButton("ℹ️ ПОМОЩЬ")
    
    markup.add(free_btn, seasonal_btn)
    markup.add(consultation_btn, info_btn)
    
    menu_text = f"""✨ *ДОБРО ПОЖАЛОВАТЬ В МОЙ БОТ!*

Здесь вы можете получить:

{PRODUCTS['free']['name']} - *БЕСПЛАТНО*
• Определение типа, пористости и потребностей волос
• 3 простых теста для диагностики
• Четкий план действий

{PRODUCTS['seasonal']['name']} - *{PRODUCTS['seasonal']['price']} руб*
• Уход в холодное время года
• Защита от мороза и сухости
• Борьба с электризацией и спутанностью
• Сезонные рекомендации

👑 *ПЕРСОНАЛЬНАЯ КОНСУЛЬТАЦИЯ*
• Индивидуальный разбор вашей ситуации

*Выберите нужный вариант ниже:* 👇"""

    bot.send_message(
        chat_id,
        menu_text,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text and 'диагностика' in message.text.lower())
def handle_free_product(message):
    user_id = message.from_user.id
    username = message.from_user.username or "нет"
    first_name = message.from_user.first_name or "Неизвестно"
    
    log_action(user_id, username, first_name, 'ЗАПРОС БЕСПЛАТНОГО ПРОДУКТА')
    send_product(message.chat.id, user_id, username, first_name, 'free')
    
    time.sleep(2)
    offer_subscription_and_seasonal(message.chat.id)

@bot.message_handler(func=lambda message: message.text and 'осенн' in message.text.lower())
def handle_seasonal_product(message):
    user_id = message.from_user.id
    username = message.from_user.username or "нет"
    first_name = message.from_user.first_name or "Неизвестно"
    
    log_action(user_id, username, first_name, 'ЗАПРОС ПЛАТНОГО ПРОДУКТА', product_type='seasonal')
    show_payment_instructions(message.chat.id, user_id, username, first_name)

def send_product(chat_id, user_id, username, first_name, product_type):
    """Отправляет продукт"""
    product = PRODUCTS[product_type]
    
    try:
        file_path = product['file']
        
        if not os.path.exists(file_path):
            bot.send_message(chat_id, "❌ Файл временно недоступен. Свяжитесь с поддержкой: @belka1233")
            return
            
        with open(file_path, 'rb') as file:
            bot.send_document(
                chat_id, 
                file, 
                caption=product['caption'],
                parse_mode='Markdown'
            )
        
        if product_type == 'free':
            log_action(user_id, username, first_name, 'СКАЧИВАНИЕ БЕСПЛАТНОГО ПРОДУКТА')
        else:
            log_action(user_id, username, first_name, 'УСПЕШНАЯ ОПЛАТА', 
                       product_type=product_type, amount=product['price'])
            
    except Exception as e:
        bot.send_message(chat_id, "❌ Произошла ошибка при отправке файла.")
        print(f"Ошибка отправки файла: {e}")

def show_payment_instructions(chat_id, user_id, username, first_name):
    """Показывает инструкцию по оплате"""
    product = PRODUCTS['seasonal']
    
    payment_text = f"""🍂 *{product['description'].upper()}*

*Стоимость:* {product['price']} рублей

*Что внутри:*
❄️ Особенности ухода в холодное время года
✨ Защита волос от мороза и сухости
💫 Борьба с электризацией и спутанностью
🌬️ Восстановление после зимних повреждений
🎯 Сезонные рекомендации по уходу

*Как получить:*
1. Нажмите кнопку *«ОПЛАТИТЬ {product['price']} РУБ»* ниже
2. *Сумма уже установлена!* Просто подтвердите платеж
3. После оплаты нажмите *«Я ОПЛАТИЛ(А)»*
4. Получите гайд мгновенно!"""

    markup = types.InlineKeyboardMarkup()
    
    # Кнопка с фиксированной оплатой
    pay_btn = types.InlineKeyboardButton(
        f"💳 ОПЛАТИТЬ {product['price']} РУБ", 
        url=YOOMONEY_LINK
    )
    confirm_btn = types.InlineKeyboardButton("✅ Я ОПЛАТИЛ(А)", callback_data=f"confirm_payment:{user_id}")
    back_btn = types.InlineKeyboardButton("⬅️ НАЗАД", callback_data="back_to_menu")
    
    markup.add(pay_btn)
    markup.add(confirm_btn)
    markup.add(back_btn)

    bot.send_message(
        chat_id,
        payment_text,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_payment:"))
def handle_confirm_payment(call):
    """Обработчик подтверждения оплаты"""
    user_id = call.data.split(":")[1]
    username = call.from_user.username or "нет"
    first_name = call.from_user.first_name or "Неизвестно"
    
    # Меняем текст сообщения
    bot.edit_message_text(
        "✅ *Проверяем оплату...*\n\nОбычно это занимает несколько секунд ⏱️",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    
    # Имитируем проверку (2 секунды)
    time.sleep(2)
    
    # Выдаем продукт
    send_product(call.message.chat.id, user_id, username, first_name, 'seasonal')

def offer_subscription_and_seasonal(chat_id):
    """Предлагает подписку и сезонный продукт после бесплатного"""
    markup = types.InlineKeyboardMarkup()
    channel_btn = types.InlineKeyboardButton("🌟 ПОДПИСАТЬСЯ НА КАНАЛ", url="https://t.me/volosy_v_fokuse")
    seasonal_btn = types.InlineKeyboardButton(PRODUCTS['seasonal']['name'], callback_data="seasonal_info")
    
    markup.add(channel_btn)
    markup.add(seasonal_btn)
    
    subscription_text = f"""🎉 **Вот и всё! Бесплатный гайд у вас**

Но это только начало! 

🍂 *Хотите получить сезонные рекомендации?*
{PRODUCTS['seasonal']['name']} всего за {PRODUCTS['seasonal']['price']} руб:
• Защита от мороза и сухости
• Борьба с электризацией
• Восстановление зимой

✨ *А также подпишитесь на канал - там много бесплатного полезного контента!*"""

    bot.send_message(
        chat_id,
        subscription_text,
        reply_markup=markup,
        parse_mode='Markdown'
    )

def offer_subscription(chat_id):
    """Просто предлагает подписку на канал"""
    markup = types.InlineKeyboardMarkup()
    subscribe_btn = types.InlineKeyboardButton("🌟 ПОДПИСАТЬСЯ НА КАНАЛ", url="https://t.me/volosy_v_fokuse")
    markup.add(subscribe_btn)
    
    bot.send_message(
        chat_id,
        "📚 *Ежедневно делюсь полезным контентом о волосах:*",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data in ["back_to_menu", "seasonal_info"])
def handle_navigation(call):
    user_id = call.from_user.id
    username = call.from_user.username or "нет"
    first_name = call.from_user.first_name or "Неизвестно"
    
    if call.data == "back_to_menu":
        show_main_menu(call.message.chat.id, user_id, username, first_name, 'callback')
    elif call.data == "seasonal_info":
        show_payment_instructions(call.message.chat.id, user_id, username, first_name)
    
    bot.answer_callback_query(call.id)

# Обработчик для консультации
@bot.message_handler(func=lambda message: message.text and 'консультация' in message.text.lower())
def handle_consultation(message):
    user_id = message.from_user.id
    username = message.from_user.username or "нет"
    first_name = message.from_user.first_name or "Неизвестно"
    
    log_action(user_id, username, first_name, 'ЗАПРОС КОНСУЛЬТАЦИИ')
    
    consultation_text = """👑 **Персональная консультация**

Давайте составим систему ухода именно для ВАШИХ волос!

За 30 минут мы:
• Проведем полную диагностику
• Разберем текущий уход и найдем ошибки  
• Подберем косметику под ваш тип и бюджет
• Составим пошаговый план действий

💬 **Напишите мне в личные сообщения:** @belka1233

Укажите «Консультация из бота» для быстрого ответа ✨"""
    
    bot.send_message(message.chat.id, consultation_text, parse_mode='Markdown')

# Обработчик для помощи
@bot.message_handler(func=lambda message: message.text and 'помощь' in message.text.lower())
def show_help(message):
    help_text = f"""ℹ️ *ПОМОЩЬ ПО БОТУ*

*Доступные продукты:*
{PRODUCTS['free']['name']} - бесплатная диагностика волос
{PRODUCTS['seasonal']['name']} - сезонный уход ({PRODUCTS['seasonal']['price']} руб)
👑 *Консультация* - персональный разбор

*Как оплатить:*
1. Нажмите «ОПЛАТИТЬ {PRODUCTS['seasonal']['price']} РУБ»
2. *Сумма уже установлена!* Просто подтвердите платеж
3. Нажмите «Я ОПЛАТИЛ(А)»
4. Получите гайд мгновенно!

*Проблемы с оплатой?* Напишите @belka1233"""

    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

# Команда для ручной выдачи доступа (для админа)
@bot.message_handler(commands=['grant'])
def handle_grant_access(message):
    """Ручная выдача доступа (только для админа)"""
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        bot.send_message(message.chat.id, "❌ Доступ запрещен")
        return
        
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.send_message(message.chat.id, "Использование: /grant <user_id>")
            return
            
        user_id = int(parts[1])
        send_product(user_id, "admin", "Manual", "manual_grant", 'seasonal')
        bot.send_message(message.chat.id, f"✅ Сезонный гайд выдан пользователю {user_id}")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

# Обработчик для любого сообщения, которое не подошло под другие хендлеры
@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    if message.text.lower() not in ['старт', 'start', 'начать', 'меню', 'главная', 'помощь', 'инфо']:
        # Показываем главное меню
        user_id = message.from_user.id
        username = message.from_user.username or "нет"
        first_name = message.from_user.first_name or "Неизвестно"
        show_main_menu(message.chat.id, user_id, username, first_name, 'unknown_command')

if __name__ == "__main__":
    print("🤖 Бот запущен с двумя продуктами!")
    print(f"🎁 Бесплатный: {PRODUCTS['free']['file']}")
    print(f"🍂 Платный: {PRODUCTS['seasonal']['file']} - {PRODUCTS['seasonal']['price']} руб")
    print(f"🔗 Ссылка оплаты: {YOOMONEY_LINK}")
    
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(10)