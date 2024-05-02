from decouple import config
import modules
import os
import pickle
import pytz
import telebot
from telebot import types
from datetime import datetime, timedelta
import locale

locale.setlocale(locale.LC_ALL, ("uk_UA", "UTF-8"))

admin = config("TG_CHAT_ADMIN")
token = config("TG_BOT_TOKEN")
bot = telebot.TeleBot(token)
kiev_timezone = pytz.timezone("Europe/Kiev")


def help_menu():
    help_message = "🤖 Коротенька допомога по кнопкам бота:\n\n"
    help_message += "🔎 /start - Початок роботи з ботом та головне меню.\n"
    help_message += "🔍 Пошук - Здійснення пошуку розкладу автобусів за назвою зупинки. Можна писати не повну назву\n"
    help_message += "📖 Список - Перегляд списку всіх доступних зупинок.\n"
    help_message += "🔼 Попередній - Перехід до попереднього результата пошуку.\n"
    help_message += (
        "▶️ Оновити - Оновлення результатів пошуку відносно поточного часу.\n"
    )
    help_message += "🔽 Наступний - Перехід до наступного результату пошуку.\n"
    help_message += "👉Основне меню👈 - Повернення до головного меню.\n"
    help_message += "💬 Допомога - Повна інформація про користування ботом.\n"
    return help_message


def generate_keyboard(button_texts):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    rows = [button_texts[i : i + 3] for i in range(0, len(button_texts), 3)]
    for row in rows:
        markup.add(*[types.KeyboardButton(text) for text in row])
    return markup


# Обробник команди /start
@bot.message_handler(commands=["start"])
def start(message):
    user_name = (
        message.from_user.first_name if message.from_user.first_name else "друже"
    )
    button_texts = ["Пошук 🔎", "Список 📖", "Допомога 🙋"]
    markup = generate_keyboard(button_texts)
    bot.send_message(
        message.chat.id,
        f"Привіт, {user_name}! 👋 \nЯ бот для  пошуку графіку руху міських автобусів  в місті Могилів-Подільський",
        reply_markup=markup,
    )


# Визначення обробника текстових повідомлень
@bot.message_handler(content_types=["text"])
def func(message):
    # Перевірка, чи є користувач в користуватському словнику
    if message.chat.id not in user_data:
        username = message.from_user.first_name
        if message.from_user.last_name is not None:
            username += f" {message.from_user.last_name}"
        bot.send_message(admin, f"Ура-а-а! У нас новий користувач {username}.")
        user_data[message.chat.id] = Searcher(username=username)
    user_data[message.chat.id].last_visit = datetime.now(kiev_timezone)

    # Обробка певних текстових повідомлень
    if message.text == "Звіт":
        current_time = datetime.now(kiev_timezone)
        sorted_user_list = sorted(
            user_data.items(), key=lambda item: item[1].last_visit, reverse=True
        )[:10]
        sum_interaction_count = sum(
            map(lambda item: item[1].interaction_count, user_data.items())
        )
        for user_id, user_Searcher in sorted_user_list:
            if user_Searcher.last_visit.date() == current_time.date():
                formatted_time = (
                    f"сьогодні о {user_Searcher.last_visit.strftime('%H:%M')}"
                )
            elif user_Searcher.last_visit.date() == current_time.date() - timedelta(
                days=1
            ):
                formatted_time = f"вчора о {user_Searcher.last_visit.strftime('%H:%M')}"
            else:
                formatted_time = f"{user_Searcher.last_visit.strftime('%d %B')}, о {user_Searcher.last_visit.strftime('%H:%M')}"

            bot.send_message(
                message.chat.id,
                f"{user_Searcher.username},\nЗапит : {user_Searcher.search_query}.\nДата : {formatted_time}",
            )
        bot.send_message(
            message.chat.id,
            f"Всього користувачів {len(user_data)}, загальна кількість запитів від останнього перезавантаження {sum_interaction_count}",
        )

    elif message.text == "Список 📖":
        message.text, button_texts = user_data[message.chat.id].find(bus_stop_name="")
        markup = generate_keyboard(button_texts)
        bot.send_message(
            message.chat.id, "Оберіть потрібну зупинку із списку!", reply_markup=markup
        )

    elif message.text == "Пошук 🔎":
        bot.send_message(
            message.chat.id,
            "Введіть назву зупинки! \nНе обов'язково писати повну назву",
        )

    elif message.text == "Допомога 🙋":
        bot.send_message(message.chat.id, help_menu())

    elif message.text == "🔼 Попередній":
        user_data[message.chat.id].offset -= 1
        message.text, button_texts = user_data[message.chat.id].find()
        markup = generate_keyboard(button_texts)
        bot.send_message(message.chat.id, message.text, reply_markup=markup)

    elif message.text == "▶\nОновити":
        user_data[message.chat.id].offset = 0
        message.text, button_texts = user_data[message.chat.id].find()
        markup = generate_keyboard(button_texts)
        bot.send_message(message.chat.id, message.text, reply_markup=markup)

    elif message.text == "🔽 Наступний":
        user_data[message.chat.id].offset += 1
        message.text, button_texts = user_data[message.chat.id].find()
        markup = generate_keyboard(button_texts)
        bot.send_message(message.chat.id, message.text, reply_markup=markup)

    elif message.text == "👉Основне меню👈":
        button_texts = ["Пошук 🔎", "Список 📖", "Допомога 🙋"]
        markup = generate_keyboard(button_texts)
        bot.send_message(
            message.chat.id, "Ви повернулись до головного меню!", reply_markup=markup
        )
    else:
        # Якщо повідомлення не було перехоплено, виконується пошук автобусної зупинки
        user_data[message.chat.id].offset = 0
        message.text, buttons_texts = user_data[message.chat.id].find(
            bus_stop_name=message.text
        )
        markup = generate_keyboard(buttons_texts)
        bot.send_message(message.chat.id, message.text, reply_markup=markup)

    # Збереження користувацьких даних в файл
    with open("user_data.pickle", "wb") as f:
        pickle.dump(user_data, f)


bot.send_message(admin, "Бот перезавантажено!")
# Відновлення даних з файлу
if os.path.exists("user_data.pickle"):
    with open("user_data.pickle", "rb") as file:
        user_data = pickle.load(file)

    current_time = datetime.now(kiev_timezone)
    inactive_users = []

    for user_id, user in user_data.items():
        if (current_time - user.last_visit).days > 30:
            inactive_users.append(user_id)

    for user_id in inactive_users:
        del user_data[user_id]

    with open("user_data.pickle", "wb") as file:
        pickle.dump(user_data, file)

    if inactive_users:
        deleted_users_message = "Видалені користувачі:\n"
        for user_id in inactive_users:
            deleted_users_message += f"- Користувач з ID {user_id}\n"
        bot.send_message(admin, deleted_users_message)
else:
    user_data = {}

# Processing other commands and text messages
bot.polling(none_stop=True)
