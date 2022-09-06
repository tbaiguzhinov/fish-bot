import os
from functools import partial

# import logging
import redis
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, Filters, MessageHandler, Updater)
from store import (authenticate, get_all_products, get_product, get_file, get_photo, add_to_cart, get_cart, get_cart_items)


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
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Please choose:',
        reply_markup=reply_markup
    )
    return "HANDLE_MENU"


def echo(update: Update, context: CallbackContext):
    users_reply = update.message.text
    update.message.reply_text(users_reply)
    return "ECHO"


def handle_menu(moltin_token, update: Update, context: CallbackContext):
    context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=update.callback_query.message.message_id,
    )
    callback = update.callback_query.data
    if callback == 'cart':
        return 'HANDLE_CART'
    product_id = callback
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

    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('1 кг', callback_data=f'1,{product_id}'),
                InlineKeyboardButton('5 кг', callback_data=f'5,{product_id}'),
                InlineKeyboardButton('10 кг', callback_data=f'10,{product_id}')
            ],
            [InlineKeyboardButton('Корзина', callback_data='cart')],
            [InlineKeyboardButton('Назад', callback_data='back')]]
    )

    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo,
        caption=text,
        reply_markup=reply_markup,
    )
    return "HANDLE_DESCRIPTION"


def handle_description(moltin_token, update: Update, context: CallbackContext):
    callback = update.callback_query.data
    if callback == 'cart':
        client_id = update.effective_chat.id
        cart_items = get_cart_items(client_id, moltin_token)
        grand_total = get_cart(client_id, moltin_token)['meta']['display_price']['with_tax']['formatted']
        text = []
        for item in cart_items:    
            name = item['name']
            description = item['description']
            price = item['meta']['display_price']['with_tax']['unit']['formatted']
            amount = item['quantity']
            total = item['meta']['display_price']['with_tax']['value']['formatted']
            text.append(f'{name}\n{description}\n{price} per kg\n{amount}kg in cart for {total}')
        text.append(f'Total: {grand_total}')
        keyboard = [
            [InlineKeyboardButton('Оплатить', callback_data='payment')],
            [InlineKeyboardButton('Назад', callback_data='back')],
            ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='\n\n'.join(text),
            reply_markup=reply_markup,
        )
        return 'HANDLE_CART'
    elif callback != 'back':
        quantity, product_id = callback.split(',')
        client_id = update.effective_chat.id
        add_to_cart(client_id, product_id, int(quantity), moltin_token)
        return "HANDLE_DESCRIPTION"
    else:
        context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.callback_query.message.message_id,
        )
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
        keyboard.append([InlineKeyboardButton('Корзина', callback_data='cart')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Please choose:',
            reply_markup=reply_markup,
        )
        return "HANDLE_MENU"


def handle_cart(moltin_token, update: Update, context: CallbackContext):
    return 'ECHO'


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
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
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
    dispatcher.add_handler(MessageHandler(
        Filters.text, handle_users_reply_partial))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply_partial))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
