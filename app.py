import psycopg2
from flask import Flask, request
import os
import telebot
import logging
from config import *
from db import *

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

db_connection = psycopg2.connect(**db_params)
db_object = db_connection.cursor()

menu_stack = [] # Стек меню
selected_course = ""
selected_group = ""
selected_day = ""

@bot.message_handler(commands=['start'])
def start(message):
    global id
    id = message.from_user.id
    username = message.from_user.username
    # сохраняем message_id
    message_id = message.message_id
    chat_id = message.chat.id
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)

    markup.add(telebot.types.InlineKeyboardButton(text='Абитуриент', callback_data='abitur'))
    markup.add(telebot.types.InlineKeyboardButton(text='Студент', callback_data='stud'))
    bot.send_message(chat_id, 'Welcome to UIB bot!', reply_markup=markup)
    bot.delete_message(message.chat.id, message_id)  # удаление предыдущего сообщения
    menu_stack.append(markup)
    db_object.execute(f"SELECT user_id FROM users WHERE user_id={id}")
    result = db_object.fetchone()

    if not result:
        db_object.execute("INSERT INTO users (user_id, telegram_id) VALUES (%s, %s)", (id, username))
        db_connection.commit()


@bot.callback_query_handler(func=lambda call: call.data == 'stud')
def student_menu(call):
    global selected_course
    sql = "SELECT name FROM course"
    print(f"Executing SQL: {sql}")
    db_object.execute(sql)
    rows = db_object.fetchall()
    buttons = []
    for row in rows:
        buttons.append(telebot.types.InlineKeyboardButton(text=row[0], callback_data=row[0]))
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(*buttons)
    print(rows)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Выберите курс')
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
    # bot.answer_callback_query(call.message.message_id, text='sdas')
    menu_stack.append(keyboard)
    course_names = [row[0] for row in rows]
    selected_course = course_names  # присваиваем значение переменной selected_course

@bot.callback_query_handler(func=lambda call: call.data in selected_course)
def course_menu(call):
    global selected_group
    course_id_data = call.data
    sql_course_id_select = "SELECT course_id FROM course WHERE name = %s"
    db_object.execute(sql_course_id_select, (course_id_data,))
    print(f"Executing SQL: {sql_course_id_select}")
    course_id = db_object.fetchone()[0]
    print(course_id)

    db_object.execute(f"SELECT user_id FROM users WHERE user_id={id}")
    result = db_object.fetchone()
    if result:
        sql_course_id_insert = f"UPDATE users SET course_id = %s WHERE user_id = {id}"
        db_object.execute(sql_course_id_insert, (course_id,))
        print(f"Executing SQL: {sql_course_id_insert}")
        db_connection.commit()
    sql_group_id_select = "SELECT g.name FROM groups as g JOIN course as c ON c.course_id = g.course_id WHERE g.course_id = %s"
    print(f"Executing SQL: {sql_group_id_select}")
    db_object.execute(sql_group_id_select, (course_id,))
    rows = db_object.fetchall()
    buttons = []
    for row in rows:
        buttons.append(telebot.types.InlineKeyboardButton(text=row[0], callback_data=row[0]))
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(*buttons)
    print(rows)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Выберите группу')
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  reply_markup=keyboard)
    menu_stack.append(keyboard)
    group_names = [row[0] for row in rows]
    selected_group = group_names  # присваиваем значение переменной selected_group
    print(selected_group)

@bot.callback_query_handler(func=lambda call: call.data in selected_group)
def group_menu(call):
    group_id_data = call.data
    sql_group_id_select = "SELECT group_id FROM groups WHERE name = %s"
    db_object.execute(sql_group_id_select, (group_id_data,))
    print(f"Executing SQL: {sql_group_id_select}")
    group_id = db_object.fetchone()[0]
    print(group_id)

    db_object.execute(f"SELECT user_id FROM users WHERE user_id={id}")
    result = db_object.fetchone()
    if result:
        sql_group_id_insert = f"UPDATE users SET group_id = %s WHERE user_id = {id}"
        db_object.execute(sql_group_id_insert, (group_id,))
        print(f"Executing SQL: {sql_group_id_insert}")
        db_connection.commit()
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(telebot.types.KeyboardButton('Расписание'))
    keyboard.add(telebot.types.KeyboardButton('Офисные часы'))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='_')
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    bot.send_message(chat_id=call.message.chat.id, text= "Главное меню", reply_markup=keyboard)
    menu_stack.append(keyboard)

@bot.message_handler(func=lambda message: message.text == "Расписание")
def days_menu(message):
    global selected_day
    sql_day_select = "SELECT name FROM days"
    db_object.execute(sql_day_select)
    rows = db_object.fetchall()
    buttons = []
    for row in rows:
        button = telebot.types.InlineKeyboardButton(text=row[0], callback_data=row[0])
        buttons.append(button)
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(*buttons)
    keyboard.add(telebot.types.InlineKeyboardButton(text='Скрыть', callback_data='hide_days'))
    bot.send_message(message.chat.id, 'Выберите день недели', reply_markup=keyboard)
    menu_stack.append(keyboard)
    days = [row[0] for row in rows]
    selected_day = days

@bot.message_handler(func=lambda message: message.text == 'Офисные часы')
def office_hours(message):
    db_object.execute(f"SELECT user_id FROM users WHERE user_id={id}")
    result = db_object.fetchone()
    if result:
        sql_office_select = f"SELECT o.text FROM ofhours AS o " \
                            f"JOIN users as u ON u.group_id = o.group_id " \
                            f"WHERE u.user_id = {id}"
        print(f"Executing SQL: {sql_office_select}")
        db_object.execute(sql_office_select)
        office_message = db_object.fetchall()
        if office_message:
            office_text = '\n'.join([row[0] for row in office_message])
            print(office_message)
            bot.send_message(message.chat.id, text=office_text)
        else:
            bot.send_message(message.chat.id, text="Пусто")

@bot.callback_query_handler(func=lambda call: call.data in selected_day)
def schedule_menu(call):
    day_name = call.data
    sql = f"SELECT days_id FROM days WHERE name = %s"
    print(f"Executing SQL: {sql}")
    db_object.execute(sql, (day_name,))
    day_id = db_object.fetchone()[0]
    print(day_id)
    sql_schedule = f"SELECT s.text " \
                   f"FROM schedule AS s " \
                   f"JOIN users AS u ON u.group_id = s.group_id " \
                   f"JOIN days AS d ON d.days_id = s.days_id " \
                   f"WHERE u.user_id = {id} AND d.days_id = {day_id}"
    print(f"Executing SQL: {sql_schedule}")
    db_object.execute(sql_schedule)
    schedule_mess = db_object.fetchall()
    print(schedule_mess)
    if schedule_mess:
        schedule_text = '\n'.join([row[0] for row in schedule_mess])
        print(schedule_text)
        bot.send_message(chat_id=call.message.chat.id, text=schedule_text)
    else:
        bot.send_message(chat_id=call.message.chat.id, text="No schedule found for selected day.")

@bot.callback_query_handler(func=lambda call: call.data == "hide_days")
def hide_days(call):
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.message_handler(func=lambda message: message.text == 'Назад')
def back(message):
    if len(menu_stack) > 1:
        menu_stack.pop()  # Удаление текущего меню из стека
        bot.delete_message(message.chat.id, message.message_id)
        prev_menu = menu_stack[-1]  # Получение предыдущего меню из стека
        bot.send_message(message.chat.id, 'Вы вернулись назад', reply_markup=prev_menu)
    else:
        bot.send_message(message.chat.id, 'Вы вернулись в начало')



@server.route('/', methods=["POST"])
def redirect_message():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL)
    server.run()