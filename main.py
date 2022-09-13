import logging
import os
import textwrap
import time
from functools import partial

import redis
import telegram
from dotenv import load_dotenv
from email_validator import (validate_email, EmailNotValidError,
                             EmailSyntaxError)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, Filters, MessageHandler, Updater)

from get_logger import TelegramLogsHandler
from store import (add_to_cart, authenticate, create_customer,
                   get_all_products, get_cart, get_cart_items, get_file,
                   get_photo, get_product, remove_product_from_cart)

logger = logging.getLogger('Logger')


def token_update(function):
    """Check token expiration - decorator function."""
    def update(moltin_token, update: Update, context: CallbackContext):
        if moltin_token['expires'] < time.time():
            moltin_token = authenticate(os.getenv('MOLTIN_CLIENT_ID'))
            logger.error('Token updated')
        return function(moltin_token, update, context)
    return update


def get_product_keyboard(products):
    keyboard = []
    for product in products:
        button = [
            InlineKeyboardButton(
                product['name'],
                callback_data=product['id'],
            )
        ]
        keyboard.append(button)
    keyboard.append([InlineKeyboardButton(
        'Корзина', callback_data='cart')])
    return InlineKeyboardMarkup(keyboard)


def start(moltin_token, update: Update, context: CallbackContext):
    """Start bot."""
    products = get_all_products(moltin_token['token'])
    reply_markup = get_product_keyboard(products)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Please choose:',
        reply_markup=reply_markup,
    )
    return "HANDLE_MENU"


def handle_menu(moltin_token, update: Update, context: CallbackContext):
    """Handle menu."""
    context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=update.callback_query.message.message_id,
    )
    callback = update.callback_query.data
    if callback == 'cart':
        return 'HANDLE_CART'
    product_id = callback
    product = get_product(product_id, moltin_token['token'])
    file = get_file(
        file_id=product['relationships']['main_image']['data']['id'],
        access_token=moltin_token['token'],
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
    """Handle description of product."""
    callback = update.callback_query.data
    if callback == 'cart':
        client_id = update.effective_chat.id
        cart_items = get_cart_items(client_id, moltin_token['token'])
        grand_total = get_cart(client_id, moltin_token['token'])[
            'meta']['display_price']['with_tax']['formatted']
        text = []
        keyboard = []
        for item in cart_items:
            name = item['name']
            product_id = item['id']
            description = item['description']
            price = item['meta']['display_price'][
                'with_tax']['unit']['formatted']
            amount = item['quantity']
            total = item['meta']['display_price'][
                'with_tax']['value']['formatted']
            text.append(textwrap.dedent(
                f'''
                {name}
                {description}
                {price} per kg
                {amount}kg in cart for {total}
                '''))
            keyboard.append([InlineKeyboardButton(
                f'Убрать из корзины {name}', callback_data=f'{product_id}')])
        text.append(f'\nTotal: {grand_total}')
        keyboard.append([InlineKeyboardButton(
            'Оплатить', callback_data='pay')])
        keyboard.append([InlineKeyboardButton('В меню', callback_data='back')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=''.join(text),
            reply_markup=reply_markup,
        )
        return 'HANDLE_CART'
    elif callback != 'back':
        quantity, product_id = callback.split(',')
        client_id = update.effective_chat.id
        add_to_cart(client_id, product_id,
                    int(quantity), moltin_token['token'])
        return "HANDLE_DESCRIPTION"
    else:
        context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.callback_query.message.message_id,
        )
        products = get_all_products(moltin_token['token'])
        reply_markup = get_product_keyboard(products)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Please choose:',
            reply_markup=reply_markup,
        )
        return "HANDLE_MENU"


def handle_cart(moltin_token, update: Update, context: CallbackContext):
    """Handle user cart."""
    callback = update.callback_query.data
    if callback == 'back':
        products = get_all_products(moltin_token['token'])
        keyboard = []
        for product in products:
            button = [
                InlineKeyboardButton(
                    product['name'],
                    callback_data=product['id'],
                )
            ]
            keyboard.append(button)
        keyboard.append([InlineKeyboardButton(
            'Корзина', callback_data='cart')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Please choose:',
            reply_markup=reply_markup,
        )
        return "HANDLE_MENU"
    elif callback == 'pay':
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Пожалуйста, укажите Вашу почту:',
        )
        return 'OBTAIN_EMAIL'
    else:
        remove_product_from_cart(
            product_id=callback,
            cart_id=update.effective_chat.id,
            access_token=moltin_token['token'],
        )
        return 'HANDLE_CART'


def obtain_email(moltin_token, update: Update, context: CallbackContext):
    """Get user email."""
    email = update.message.text
    try:
        email = validate_email(email, timeout=5).email
        text = f'Вы прислали мне эту почту: {email}'
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
        )
        create_customer(email, moltin_token['token'])
        text = 'Спасибо! С Вами свяжется менеждер по поводу Вашего заказа.'
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
        )
        return 'START'
    except (EmailSyntaxError, EmailNotValidError) as text:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=str(text),
        )
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Пожалуйста, укажите Вашу почту:',
        )
        return 'OBTAIN_EMAIL'


@token_update
def handle_users_reply(
        moltin_token,
        db,
        update: Update,
        context: CallbackContext
):
    """Handle user replies."""
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
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'OBTAIN_EMAIL': obtain_email,
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(moltin_token, update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


def error_handler(update: Update, context: CallbackContext):
    """Handle errors."""
    logger.error(msg="Телеграм бот упал с ошибкой:", exc_info=context.error)


def main():
    """Main function."""
    load_dotenv()
    logger_bot_token = os.getenv('LOGGER_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    logger_bot = telegram.Bot(logger_bot_token)
    logger.addHandler(TelegramLogsHandler(logger_bot, chat_id))
    logger.warning("Fish бот запущен")

    database_password = os.getenv("DATABASE_PASSWORD")
    database_host = os.getenv("DATABASE_HOST")
    database_port = os.getenv("DATABASE_PORT")
    db = redis.Redis(
        host=database_host,
        port=database_port,
        password=database_password
    )

    client_id = os.getenv('MOLTIN_CLIENT_ID')
    moltin_token = authenticate(client_id)
    expiration = moltin_token['expires']
    logger.error(f'Token updated until {expiration}')
    handle_users_reply_partial = partial(handle_users_reply, moltin_token, db)

    tg_token = os.getenv("TELEGRAM_TOKEN")
    updater = Updater(tg_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply_partial))
    dispatcher.add_handler(MessageHandler(
        Filters.text, handle_users_reply_partial))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply_partial))
    dispatcher.add_error_handler(error_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
