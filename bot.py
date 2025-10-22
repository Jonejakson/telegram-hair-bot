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
    
    if not check_subscription(user_id):
        markup = types.InlineKeyboardMarkup()
        subscribe_btn = types.InlineKeyboardButton(
            "🌟 Подписаться на канал и получить подарок", 
            url=f"https://t.me/{CHANNEL_USERNAME}"
        )
        check_btn = types.InlineKeyboardButton(
            "✅ Я подписался, дайте файл", 
            callback_data="check_subscription"
        )
        markup.add(subscribe_btn)
        markup.add(check_btn)
        
        bot.send_message(
            message.chat.id,
            "✨ <b>Добро пожаловать в мир ухоженных волос!</b>\n\nЧтобы получить <b>бесплатный PDF-гид</b> «Диагностика волос», нужно быть подписчиком нашего канала.\n\nВ канале вы найдете:\n• Экспертные советы по уходу за волосами\n• Разбор состава косметики \n• Личный опыт восстановления волос\n• Систему ухода, которая реально работает\n\n<b>Подпишитесь на канал и нажмите «Проверить подписку»</b> 👇",
            reply_markup=markup,
            parse_mode='HTML'
        )
        return
    
    bot.send_message(
        message.chat.id,
        "🎉 <b>Благодарим за доверие!</b>\n\nВидим, что вы из тех, кто готов разбираться в истинных причинах проблем с волосами.\n\n<b>Ваш PDF-гид «Диагностика волос» уже готов к отправке!</b>\n\n📧 <b>Введите ваш email</b> чтобы мы могли:\n• Сохранить ваш доступ к материалам\n• Присылать дополнительные советы по уходу\n• Уведомить о новых методиках диагностики",
        parse_mode='HTML'
    )
    bot.register_next_step_handler(message, process_email)

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_subscription_callback(call):
    user_id = call.from_user.id
    
    if check_subscription(user_id):
        bot.edit_message_text(
            "🎉 <b>Благодарим за доверие!</b>\n\nВидим, что вы из тех, кто готов разбираться в истинных причинах проблем с волосами.\n\n<b>Ваш PDF-гид «Диагностика волос» уже готов к отправке!</b>\n\n📧 <b>Введите ваш email</b> чтобы мы могли:\n• Сохранить ваш доступ к материалам\n• Присылать дополнительные советы по уходу\n• Уведомить о новых методиках диагностики",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
        bot.register_next_step_handler(call.message, process_email)
    else:
        bot.answer_callback_query(
            call.id, 
            "❌ Вы еще не подписались на канал! Подпишитесь и нажмите снова.", 
            show_alert=True
        )

def process_email(message):
    user_id = message.from_user.id
    email = message.text.strip()
    
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        bot.send_message(
            message.chat.id,
            "❌ Неверный формат email. Пожалуйста, введите корректный email:"
        )
        bot.register_next_step_handler(message, process_email)
        return
    
    user_data[user_id] = {
        'email': email,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name
    }
    
    send_file_and_info(message.chat.id, user_id, email)

def send_file_and_info(chat_id, user_id, email):
    try:
        file_path = 'diagnostika_volosy.pdf'
        
        if not os.path.exists(file_path):
            bot.send_message(chat_id, "❌ Файл временно недоступен.")
            return
            
        with open(file_path, 'rb') as file:
            bot.send_document(chat_id, file, caption="📎 Ваш PDF-гид «Диагностика волос»")
        
        user_info = user_data.get(user_id, {})
        admin_message = f"📈 Новый пользователь!\n\n👤 Имя: {user_info.get('first_name', 'Не указано')}\n📧 Email: {email}\n🆔 ID: {user_id}"
        
        try:
            bot.send_message(ADMIN_CHAT_ID, admin_message)
        except Exception as admin_error:
            print(f"Ошибка отправки админу: {admin_error}")
        
        final_text = f"""✅ <b>Ваш PDF-гид уже здесь!</b>

Изучайте материалы и начинайте диагностику прямо сегодня!

<b>Кстати, заметили?</b> Часто бывает, что:
• Не хватает времени разбираться во всех методиках
• Запутались в противоречивой информации  
• Хочется индивидуального подхода к ВАШИМ волосам

💎 <b>У меня есть решение:</b>

<b>30-минутная персональная консультация</b>, где мы:
• Проведем полную диагностику именно ВАШИХ волос
• Разберем ваш текущий уход и найдем ошибки
• Составим персональную систему ухода
• Подберем косметику под ваш тип волос и бюджет

<i>«После консультации я наконец-то поняла, что делать с моими волосами. Экономия на неподходящей косметике окупила консультацию в 3 раза!»</i> — Анастасия, 28 лет

📞 <b>Напишите «Консультация» в личные сообщения</b> @belka1233 для записи

А пока — успешной диагностики! Желаю красивых и здоровых волос! ✨"""
        
        bot.send_message(chat_id, final_text, parse_mode='HTML')
        
    except Exception as e:
        error_msg = f"❌ Произошла ошибка при отправке файла: {str(e)}"
        bot.send_message(chat_id, "❌ Произошла ошибка при отправке файла.")
        print(error_msg)

if __name__ == "__main__":
    print("🤖 Бот запущен на Railway!")
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("🔄 Перезапуск через 10 секунд...")
            time.sleep(10)