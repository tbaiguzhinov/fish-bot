import os
from functools import partial

# import logging
import redis
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, Filters, MessageHandler, Updater)

from store import authenticate, get_all_products, get_product, get_file, get_photo


def start(moltin_token, update: Update, context: CallbackContext):
    products = get_all_products(moltin_token)
    keyboard = []
    for product in products:
        button = [
            InlineKeyboardButton(
                product['name'],
                callback_data=product['id'],
            )
        ]
        keyboard.append(button)
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text='Please choose:', reply_markup=reply_markup)
    return "HANDLE_MENU"


def echo(update: Update, context: CallbackContext):
    users_reply = update.message.text
    update.message.reply_text(users_reply)
    return "ECHO"


def handle_menu(moltin_token, update: Update, context: CallbackContext):
    product_id = update.callback_query.data
    product = get_product(product_id, moltin_token)
    file = get_file(
        file_id=product['relationships']['main_image']['data']['id'],
        access_token=moltin_token
    )
    photo = get_photo(link=file['link']['href'])
    
    name = product['name']
    price = product['meta']['display_price']['with_tax']['formatted']
    stock = product['meta']['stock']['level']
    description = product['description']
    text = f'{name}\n\n{price} per kg\n\n{stock}kg on stock\n\n{description}'

    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo,
        caption=text,
    )
    return "ECHO"


def handle_users_reply(moltin_token, update: Update, context: CallbackContext):
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start,
        'ECHO': echo,
        'HANDLE_MENU': handle_menu,
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(moltin_token, update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


def get_database_connection():
    database_password = os.getenv("DATABASE_PASSWORD")
    database_host = os.getenv("DATABASE_HOST")
    database_port = os.getenv("DATABASE_PORT")
    return redis.Redis(
        host=database_host,
        port=database_port,
        password=database_password
    )


def main():
    load_dotenv()
    client_id = os.getenv('MOLTIN_CLIENT_ID')
    moltin_token = authenticate(client_id)
    handle_users_reply_partial = partial(handle_users_reply, moltin_token)
    
    tg_token = os.getenv("TELEGRAM_TOKEN")
    updater = Updater(tg_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply_partial))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply_partial))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply_partial))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
