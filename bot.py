# -*- coding: utf-8 -*-
import telebot
from telebot import types
import requests
import re
import os
import time

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
    
    # СРАЗУ отправляем файл без проверок
    send_file_immediately(message.chat.id, user_id)
    
    # Через 2 секунды предлагаем подписаться
    time.sleep(2)
    offer_subscription(message.chat.id)

def send_file_immediately(chat_id, user_id):
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
        
        # Логирование для админа
        user_info = {
            'username': f"@{user_id}" if not user_id else str(user_id),
            'first_name': user_id if user_id else "Не указано"
        }
        
        try:
            admin_message = f"📥 Новый скачивание!\n👤 Пользователь: {user_info['first_name']}\n🆔 ID: {user_id}"
            bot.send_message(ADMIN_CHAT_ID, admin_message)
        except Exception as admin_error:
            print(f"Ошибка отправки админу: {admin_error}")
            
    except Exception as e:
        bot.send_message(chat_id, "❌ Произошла ошибка при отправке файла.")
        print(f"Ошибка отправки файла: {e}")

def offer_subscription(chat_id):
    markup = types.InlineKeyboardMarkup()
    subscribe_btn = types.InlineKeyboardButton(
        "🌟 Подписаться на канал", 
        url="https://t.me/+fOyv1FQvih4wNGY6"  # Ваша пригласительная ссылка
    )
    already_btn = types.InlineKeyboardButton(
        "✅ Я уже подписан", 
        callback_data="already_subscribed"
    )
    markup.add(subscribe_btn)
    markup.add(already_btn)
    
    subscription_text = """💫 **Понравился гайд?**

В моем канале **«Волосы в фокусе»** я каждый день делюсь:

• 🧪 Разборами составов косметики
• 💡 Лайфхаками для разных типов волос  
• 🔎 Анализом популярных средств
• 📚 Системой ухода, которая реально работает

**Подпишитесь — там еще много полезного!** 👇"""
    
    bot.send_message(
        chat_id,
        subscription_text,
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

if __name__ == "__main__":
    print("🤖 Бот запущен по новой схеме!")
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("🔄 Перезапуск через 10 секунд...")
            time.sleep(10)