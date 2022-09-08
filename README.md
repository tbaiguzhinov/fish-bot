# Бот для продажи рыбы

Бот создан для продажи рыбы по уроку 5 "Продаем рыбу в Telegram" курса [Devman](https://dvmn.org).

Код задеплоен в Телеграмме [здесь](https://t.me/fish_devman_btu_bot).

## Запуск

- Скачайте код
- Установите зависимости командой  
```pip install -r requirements.txt```
- Запустите бот в Телеграмме командой  
```python3 main.py```

## Переменные окружения

Для корректной работы кода, необходимы переменные окружения. Чтобы их определить, создайте файл `.env` рядом с `main.py` и запишите туда данные в таком формате: `ПЕРЕМЕННАЯ=значение`.

* `MOLTIN_CLIENT_ID` - ID клиента в API сервисе [Elastic Path](https://www.elasticpath.com/) (бывший Moltin).
* `LOGGER_BOT_TOKEN` - токен Telegram бота для отображения логов.
* `TELEGRAM_CHAT_ID`- ваш ID в Телеграм. Чтобы его получить, напишите в Telegram боту @userinfobot.
* `TELEGRAM_TOKEN` - токен Telegram бота, в котором будет работать бот для викторин.
* `DATABASE_PASSWORD` - пароль для входа в базу данных Redis.
* `DATABASE_HOST` - ссылка на базу данных Redis.
* `DATABASE_PORT` - порт базы данных Redis.

## Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).