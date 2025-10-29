# -*- coding: utf-8 -*-
import telebot
from telebot import types
import requests
import re
import os
import time
import datetime

# Конфигурация
BOT_TOKEN = "8469042166:AAGTV250nbgUTHe14CVba66tFXSIwcEGG7o"
CHANNEL_USERNAME = "volosy_v_fokuse"
CHANNEL_CHAT_ID = -1002194057942
ADMIN_CHAT_ID = "680094245"

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_CHAT_ID, user_id)
        return member.status in ['creator', 'administrator', 'member']
    except:
        return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # ЛОГИРОВАНИЕ UTM-МЕТОК
    source = message.text.replace('/start ', '').strip()
    if not source:
        source = 'direct'
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_info = f"{user_id} (@{message.from_user.username}, {message.from_user.first_name})"
    
    # Логируем в консоль
    print(f"🎯 {timestamp} - /start от {user_info} | Источник: {source}")
    
    # Логируем в файл
    with open('bot_logs.txt', 'a', encoding='utf-8') as f:
        f.write(f"{timestamp} - /start от {user_info} | Источник: {source}\n")
    
    # СРАЗУ отправляем файл без проверок
    send_file_immediately(message.chat.id, user_id, source)
    
    # Через 2 секунды предлагаем подписаться
    time.sleep(2)
    offer_subscription(message.chat.id)

# Обработчик для текстового сообщения "Старт"
@bot.message_handler(func=lambda message: message.text and message.text.lower() in ['старт', 'start', 'начать'])
def handle_start_text(message):
    # Просто вызываем ту же функцию, что и для /start
    send_welcome(message)

def send_file_immediately(chat_id, user_id, source='unknown'):
    try:
        file_path = 'diagnostika_volosy.pdf'
        
        if not os.path.exists(file_path):
            bot.send_message(chat_id, "❌ Файл временно недоступен.")
            return
            
        with open(file_path, 'rb') as file:
            bot.send_document(
                chat_id, 
                file, 
                caption="🎁 **Ваш PDF-гид «Диагностика волос»**\n\n_Изучайте и применяйте! Теперь вы знаете о волосах больше, чем 90% людей_ ✨",
                parse_mode='Markdown'
            )
        
        # Логирование для админа с указанием источника
        user_info = {
            'username': f"@{user_id}" if not user_id else str(user_id),
            'first_name': user_id if user_id else "Не указано"
        }
        
        try:
            admin_message = f"📥 Новый скачивание!\n👤 Пользователь: {user_info['first_name']}\n🆔 ID: {user_id}\n📊 Источник: {source}"
            bot.send_message(ADMIN_CHAT_ID, admin_message)
        except Exception as admin_error:
            print(f"Ошибка отправки админу: {admin_error}")
            
    except Exception as e:
        bot.send_message(chat_id, "❌ Произошла ошибка при отправке файла.")
        print(f"Ошибка отправки файла: {e}")

def offer_subscription(chat_id):
    markup = types.InlineKeyboardMarkup()
    subscribe_btn = types.InlineKeyboardButton(
        "🌟 ПОДПИСАТЬСЯ НА КАНАЛ", 
        url="https://t.me/volosy_v_fokuse"
    )
    markup.add(subscribe_btn)
    
    subscription_text = """🎉 **Вот и всё! Гайд у вас**

Но это только начало! В канале я каждый день даю:

✨ **Чего НЕТ в гайде:**
• Разборы новых средств (состав, эффективность)
• Ответы на ваши личные вопросы
• Обзоры косметики, которая реально работает
• Лайфхаки для вашего типа волос
• Личный опыт восстановления

💎 **Подпишитесь - там всё самое ценное!**
Канал - это 80% полезного контента, гайд - только 20%!"""
    
    bot.send_message(
        chat_id,
        subscription_text,
        reply_markup=markup,
        parse_mode='Markdown'
    )

# Обработчик для описания бота (когда пользователь открывает бота впервые)
@bot.message_handler(commands=['help', 'info'])
@bot.message_handler(func=lambda message: message.text and message.text.lower() in ['помощь', 'инфо', 'info', 'что ты умеешь'])
def show_bot_info(message):
    info_text = """🤖 **Что умеет этот бот?**

Добро пожаловать в мой телеграм-бот! Я создала его, чтобы нам было проще взаимодействовать.

✨ **Основные функции:**
• 🎁 Выдать бесплатный PDF-гид «Диагностика волос»
• 📱 Принять заявку на персональную консультацию
• 💎 Пригласить в полезный канал о волосах

🚀 **Чтобы начать, просто напишите «Старт» или нажмите /start**

С заботой о ваших волосах,
Елена 💫"""
    
    # Добавляем кнопку "Старт" под описанием
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    start_btn = types.KeyboardButton("🚀 Старт")
    markup.add(start_btn)
    
    bot.send_message(
        message.chat.id,
        info_text,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == "already_subscribed")
def handle_already_subscribed(call):
    user_id = call.from_user.id
    
    if check_subscription(user_id):
        bot.edit_message_text(
            "🎉 **Спасибо за поддержку!**\n\nРада, что вы с нами! В канале каждый день ждут новые полезные материалы 💫",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
    else:
        bot.answer_callback_query(
            call.id, 
            "🤔 Не вижу вашей подписки... Попробуйте подписаться и нажать снова", 
            show_alert=False
        )

# Обработчик для консультации
@bot.message_handler(func=lambda message: message.text and 'консультация' in message.text.lower())
def handle_consultation(message):
    consultation_text = """💎 **Персональная консультация**

Давайте составим систему ухода именно для ВАШИХ волос!

За 30 минут мы:
• Проведем полную диагностику
• Разберем текущий уход и найдем ошибки  
• Подберем косметику под ваш тип и бюджет
• Составим пошаговый план действий

💬 **Напишите мне в личные сообщения:** @belka1233

Укажите «Консультация из бота» для быстрого ответа ✨"""
    
    bot.send_message(
        message.chat.id,
        consultation_text,
        parse_mode='Markdown'
    )

# Обработчик для любого сообщения, которое не подошло под другие хендлеры
@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    if message.text.lower() not in ['старт', 'start', 'начать', 'помощь', 'инфо', 'info', 'что ты умеешь']:
        # Показываем описание бота и предлагаем начать
        show_bot_info(message)

if __name__ == "__main__":
    print("🤖 Бот запущен по новой схеме!")
    print("📊 Логирование UTM-меток активировано")
    print("🎯 Добавлены текстовые команды: Старт, Помощь")
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("🔄 Перезапуск через 10 секунд...")
            time.sleep(10)