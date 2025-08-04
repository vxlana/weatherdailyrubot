from aiogram import Bot, types
from aiogram.types import (ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup,
                           InlineKeyboardButton, WebAppInfo)

from config import donat

# инлайн кнопки с командой старт
start_inline = InlineKeyboardMarkup(row_width=1)
start_inline.add(
    InlineKeyboardButton("📍 Прогноз по выбранному городу", callback_data='weather_saved'),
    InlineKeyboardButton("✏️ Ввести другой город", callback_data='temp_city_menu')
)


# клавиатура после кнопки старт
today = KeyboardButton('Погода на сегодня')
tomorrow = KeyboardButton('Погода на завтра')
week = KeyboardButton('Погода на неделю')
support_developer = KeyboardButton('Поддержать разработчика')
settings = KeyboardButton('Настройки')

start = ReplyKeyboardMarkup(resize_keyboard=True)
start.add(today, tomorrow).add(week).add(support_developer, settings)


# клавиатура для меню Настройки
default_city = KeyboardButton('Город по умолчанию')
notifications = KeyboardButton('Уведомления')
back = KeyboardButton('Назад')


settings_kb = ReplyKeyboardMarkup(resize_keyboard=True)
settings_kb.add(default_city, notifications)
settings_kb.add(back)



def get_notify_main_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Настроить утренние уведомления"))
    kb.add(KeyboardButton("Настроить вечерние уведомления"))
    kb.add(KeyboardButton("Назад"))
    return kb

def get_morning_time_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    times = ['6:00', '7:00', '8:00', '9:00', '10:00', '11:00']
    kb.add(KeyboardButton("Назад"))
    kb.row(*[KeyboardButton(t) for t in times[:3]])
    kb.row(*[KeyboardButton(t) for t in times[3:]])
    kb.add(KeyboardButton("Отключить утренние уведомления"))
    return kb

def get_evening_time_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    times = ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00']
    kb.add(KeyboardButton("Назад"))
    kb.row(*[KeyboardButton(t) for t in times[:3]])
    kb.row(*[KeyboardButton(t) for t in times[3:]])
    kb.add(KeyboardButton("Отключить вечерние уведомления"))
    return kb


def get_support_kb():
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton("🍩 Поддержать разработчика", url=donat)
    )
