import asyncio
import os
import aiohttp
from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, \
    InlineKeyboardButton, Message
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Command
import logging
import config
import keyboard
import json
from aiogram import types
from aiogram.dispatcher import FSMContext
import json, os


class SettingsStates(StatesGroup):
    waiting_for_city = State()

class NotificationStates(StatesGroup):
    waiting_for_morning_time = State()
    waiting_for_evening_time = State()

class NotifyState(StatesGroup):
    choosing_morning_time = State()
    choosing_evening_time = State()

class TempStates(StatesGroup):
    waiting_for_temp_city = State()

class TempCityChoiceState(StatesGroup):
    waiting_for_city = State()

class CityInput(StatesGroup):
    input = State()

storage = MemoryStorage()
bot = Bot(token=config.botkey)
dp = Dispatcher(bot, storage=storage)



# ========================= ОБРАБОТЧИК КОМАНДЫ START =========================

@dp.message_handler(Command('start'), state=None)
async def welcome(message: types.Message):
    if not os.path.exists('user.txt'):
        open('user.txt', 'w').close()

    with open('user.txt', 'r') as joinedFile:
        joinedUsers = set(line.strip() for line in joinedFile)

    if str(message.chat.id) not in joinedUsers:
        with open('user.txt', 'a') as joinedFile:
            joinedFile.write(str(message.chat.id) + '\n')

    await bot.send_message(
        message.chat.id,
        f'Добро пожаловать, {message.from_user.first_name}! Какая погода вас интересует?',
        reply_markup=keyboard.start_inline,
        parse_mode='Markdown'
    )

    await bot.send_message(
        message.chat.id,
        "Главное меню:",
        reply_markup=keyboard.start
    )



# ========================= ПОГОДА НА СЕГОДНЯ =========================

# --- получение прогноз погоды по API ---
async def get_today_weather(city: str) -> str:
    api_key = config.weather_api_key
    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days=1&lang=ru"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()

                location = data['location']['name']
                country = data['location']['country']
                current = data['current']
                forecast = data['forecast']['forecastday'][0]['day']

                condition = current['condition']['text']
                temp = current['temp_c']
                feels_like = current['feelslike_c']
                wind = current['wind_kph']
                humidity = current['humidity']
                max_temp = forecast['maxtemp_c']
                min_temp = forecast['mintemp_c']

                return (
                    f"📍 Погода в {location}, {country} на сегодня:\n"
                    f"🌤 Состояние: {condition}\n"
                    f"🌡 Температура: {temp}°C (ощущается как {feels_like}°C)\n"
                    f"🔺 Макс: {max_temp}°C, 🔻 Мин: {min_temp}°C\n"
                    f"💧 Влажность: {humidity}%\n"
                    f"💨 Ветер: {wind} км/ч"
                )
            else:
                return "❌ Не удалось получить прогноз. Проверьте город или повторите позже."

# --- отправка прогноза пользователю ---
async def send_today_forecast(user_id: int, send_func):
    if not os.path.exists('user_cities.json'):
        await send_func("⚠ У вас не выбран город по умолчанию. Установите его в настройках.")
        return

    with open('user_cities.json', 'r') as f:
        cities = json.load(f)

    city = cities.get(str(user_id))
    if city:
        forecast = await get_today_weather(city)

        # инлайн кнопка "Подробнее"
        inline_kb = InlineKeyboardMarkup()
        inline_kb.add(InlineKeyboardButton("🔍 Подробнее (почасовая)", callback_data=f"hourly_{city}"))

        await send_func(forecast, reply_markup=inline_kb)
    else:
        await send_func("⚠ Город по умолчанию не выбран. Установите его через настройки.")


# --- обработчик нажатия кнопки "Погода на сегодня" ---
@dp.message_handler(lambda message: message.text == "Погода на сегодня")
async def handle_today_weather_message(message: types.Message):
    await send_today_forecast(
        user_id=message.from_user.id,
        send_func=message.answer
    )

# --- почасовой прогноз ---
@dp.callback_query_handler(lambda c: c.data.startswith("hourly_") and not c.data.startswith("hourly_tomorrow_"))
async def handle_hourly_today(callback_query: types.CallbackQuery):
    city = callback_query.data.replace("hourly_", "")
    api_key = config.weather_api_key
    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days=1&lang=ru"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                await bot.send_message(callback_query.from_user.id, "❌ Не удалось получить почасовой прогноз.")
                await callback_query.answer()
                return

            data = await resp.json()
            hours = data['forecast']['forecastday'][0]['hour']

            text = f"🕒 Почасовой прогноз в {city} на сегодня:\n\n"
            for hour in hours:
                time = hour['time'].split(" ")[1]
                condition = hour['condition']['text']
                temp = hour['temp_c']
                feels = hour['feelslike_c']
                wind = hour['wind_kph']
                text += f"🕓 {time} — {condition}, 🌡 {temp}°C, ощ. {feels}°C, 💨 {wind} км/ч\n"

            for i in range(0, len(text), 4000):
                await bot.send_message(callback_query.from_user.id, text[i:i+4000])

    await callback_query.answer()



# ========================= ПОГОДА НА ЗАВТРА =========================

# --- получение прогноза погоды по API ---
async def get_tomorrow_weather(city: str) -> str:
    api_key = config.weather_api_key
    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days=2&lang=ru"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()

                location = data['location']['name']
                country = data['location']['country']
                forecast = data['forecast']['forecastday'][1]['day']  # Завтрашний день

                condition = forecast['condition']['text']
                max_temp = forecast['maxtemp_c']
                min_temp = forecast['mintemp_c']
                avg_temp = forecast['avgtemp_c']
                wind = forecast['maxwind_kph']
                humidity = forecast['avghumidity']

                return (
                    f"📍 Погода в {location}, {country} на завтра:\n"
                    f"🌤 Состояние: {condition}\n"
                    f"🌡 Средняя температура: {avg_temp}°C\n"
                    f"🔺 Макс: {max_temp}°C, 🔻 Мин: {min_temp}°C\n"
                    f"💧 Влажность: {humidity}%\n"
                    f"💨 Ветер: {wind} км/ч"
                )
            else:
                return "❌ Не удалось получить прогноз. Проверьте город или повторите позже."


# --- обработчик нажатия кнопки "Погода на завтра" ---
@dp.message_handler(lambda message: message.text == "Погода на завтра")
async def handle_tomorrow_weather_message(message: types.Message):
    user_id = str(message.from_user.id)

    if not os.path.exists('user_cities.json'):
        await message.answer("⚠ У вас не выбран город по умолчанию. Установите его в настройках.")
        return

    with open('user_cities.json', 'r') as f:
        cities = json.load(f)

    city = cities.get(user_id)
    if city:
        forecast = await get_tomorrow_weather(city)

        # Инлайн-кнопка "Почасовой"
        inline_kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔍 Подробнее (почасовая)", callback_data=f"hourly_tomorrow_{city}")
        )

        await message.answer(forecast, reply_markup=inline_kb)
    else:
        await message.answer("⚠ Город по умолчанию не выбран. Установите его через настройки.")


# --- почасовой прогноз ---
@dp.callback_query_handler(lambda c: c.data.startswith("hourly_tomorrow_"))
async def handle_hourly_tomorrow(callback_query: types.CallbackQuery):
    city = callback_query.data.replace("hourly_tomorrow_", "")
    api_key = config.weather_api_key
    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days=2&lang=ru"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                await bot.send_message(callback_query.from_user.id, "❌ Не удалось получить почасовой прогноз.")
                await callback_query.answer()
                return

            data = await resp.json()
            hours = data['forecast']['forecastday'][1]['hour']  # завтрашний день

            text = f"🕒 Почасовой прогноз в {city} на завтра:\n\n"
            for hour in hours:
                time = hour['time'].split(" ")[1]
                condition = hour['condition']['text']
                temp = hour['temp_c']
                feels = hour['feelslike_c']
                wind = hour['wind_kph']
                text += f"🕓 {time} — {condition}, 🌡 {temp}°C, ощ. {feels}°C, 💨 {wind} км/ч\n"

            for i in range(0, len(text), 4000):
                await bot.send_message(callback_query.from_user.id, text[i:i+4000])

    await callback_query.answer()



# ========================= ПОГОДА НА НЕДЕЛЮ =========================

# --- получение прогноза погоды по API ---
async def get_week_weather(city: str) -> str:
    api_key = config.weather_api_key
    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days=7&lang=ru"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                location = data['location']['name']
                country = data['location']['country']
                forecast_days = data['forecast']['forecastday']

                result = f"📅 Прогноз погоды на неделю в {location}, {country}:\n\n"

                for day in forecast_days:
                    date = day['date']
                    condition = day['day']['condition']['text']
                    max_temp = day['day']['maxtemp_c']
                    min_temp = day['day']['mintemp_c']
                    avg_temp = day['day']['avgtemp_c']

                    result += (
                        f"📆 *{date}*\n"
                        f"🌤 {condition}\n"
                        f"🌡 Средняя: {avg_temp}°C\n"
                        f"🔺 Макс: {max_temp}°C, 🔻 Мин: {min_temp}°C\n\n"
                    )

                return result
            else:
                return "❌ Не удалось получить недельный прогноз. Попробуйте позже."


# --- обработчик нажатия кнопки "Погода на неделю" ---
@dp.message_handler(lambda message: message.text == "Погода на неделю")
async def handle_week_weather_message(message: types.Message):
    user_id = str(message.from_user.id)

    if not os.path.exists('user_cities.json'):
        await message.answer("⚠ У вас не выбран город по умолчанию. Установите его в настройках.")
        return

    with open('user_cities.json', 'r') as f:
        cities = json.load(f)

    city = cities.get(user_id)
    if city:
        forecast = await get_week_weather(city)
        await message.answer(forecast, parse_mode='Markdown')
    else:
        await message.answer("⚠ Город по умолчанию не выбран. Установите его через настройки.")



# ========================= НАСТРОЙКИ =========================

# --- обработчик нажатия кнопки "Настройки" ---
# открывает меню настроек с клавиатурой (Город по умолчанию, Уведомления, Назад)
@dp.message_handler(lambda m: m.text == "Настройки")
async def open_settings(message: types.Message):
    await message.answer("⚙️ Настройки:", reply_markup=keyboard.settings_kb)

# --- обработчик кнопки "Назад" ---
# возвращает пользователя в главное меню из любого подменю
@dp.message_handler(lambda message: message.text == "Назад")
async def on_back(message: types.Message):
    await message.answer("Главное меню:", reply_markup=keyboard.start)

# --- обработчик кнопки "Город по умолчанию" ---
# запрашивает у пользователя ввод города, переводит в состояние ожидания ввода
@dp.message_handler(lambda message: message.text == "Город по умолчанию")
async def ask_for_city(message: types.Message):
    await message.answer("Введите ваш основной город (на латинице):")
    await SettingsStates.waiting_for_city.set()

# --- обработка введённого города пользователем ---
# проверяет валидность города, сохраняет в JSON и завершает состояние
@dp.message_handler(state=SettingsStates.waiting_for_city)
async def save_default_city(message: types.Message, state: FSMContext):
    if message.text.lower() == "назад":
        await state.finish()
        await message.answer("Вы вернулись в меню настроек.", reply_markup=keyboard.settings_kb)
        return

    city = message.text.strip()
    api_key = config.weather_api_key

    async with aiohttp.ClientSession() as session:
        url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}&lang=ru"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                city_name = data['location']['name']
                country = data['location']['country']
                lat = data['location']['lat']
                lon = data['location']['lon']

                user_id = str(message.from_user.id)

                if os.path.exists('user_cities.json'):
                    with open('user_cities.json', 'r') as f:
                        cities = json.load(f)
                else:
                    cities = {}

                cities[user_id] = city_name
                with open('user_cities.json', 'w') as f:
                    json.dump(cities, f)

                await message.answer(f"✅ Город установлен: {city_name}, {country}")
                await bot.send_location(chat_id=message.chat.id, latitude=lat, longitude=lon)
                await message.answer(f"⚙ Ваши настройки:\nГород — {city_name}")
            else:
                await message.answer("❌ Не удалось найти город. Попробуйте снова.")

    await state.finish()


# --- обработчик inline-кнопки ---
# получает город пользователя из файла и отправляет прогноз на сегодня
@dp.callback_query_handler(lambda c: c.data == 'weather_saved')
async def handle_saved_city(callback_query: types.CallbackQuery):
    await send_today_forecast(
        user_id=callback_query.from_user.id,
        send_func=lambda *args, **kwargs: bot.send_message(callback_query.from_user.id, *args, **kwargs)
    )

# --- обработчик inline-кнопки "Установить город по умолчанию" ---
# просит пользователя ввести город вручную и переводит в состояние FSM ожидания ввода
@dp.callback_query_handler(lambda c: c.data == 'set_default_city')
async def handle_set_default_city_inline(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.send_message(callback_query.from_user.id, "Введите ваш основной город (на латинице):")
    await SettingsStates.waiting_for_city.set()


# --- обработчик inline-кнопки "Ввести другой город" ---
@dp.callback_query_handler(lambda c: c.data == 'weather_other')
async def handle_other_city(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "Введите город (на латинице), чтобы получить прогноз на сегодня:")
    await TempStates.waiting_for_temp_city.set()


# --- обрабатывает ввод города пользователем ---
@dp.message_handler(state=TempStates.waiting_for_temp_city)
async def handle_temp_city(message: types.Message, state: FSMContext):
    city = message.text.strip()
    forecast = await get_today_weather(city)
    await message.answer(forecast)
    await state.finish()


# --- прогноз на сегодня / на завтра / на неделю - выбор ---
@dp.callback_query_handler(lambda c: c.data == 'temp_city_menu')
async def show_temp_city_options(callback_query: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("Сегодня", callback_data='temp_city_today'),
        InlineKeyboardButton("Завтра", callback_data='temp_city_tomorrow'),
        InlineKeyboardButton("На неделю", callback_data='temp_city_week')
    )
    await bot.send_message(callback_query.from_user.id, "Выберите, на какой период хотите прогноз:", reply_markup=kb)


# --- сохраняет период прогноза и ожидает ввод города ---
@dp.callback_query_handler(lambda c: c.data.startswith('temp_city_'))
async def ask_temp_city(callback_query: types.CallbackQuery, state: FSMContext):
    period = callback_query.data.split('_')[-1]  # today / tomorrow / week
    await state.update_data(temp_period=period)
    await bot.send_message(callback_query.from_user.id, "Введите город (на латинице):")
    await TempCityChoiceState.waiting_for_city.set()


# --- отправляет прогноз ---
@dp.message_handler(state=TempCityChoiceState.waiting_for_city)
async def handle_temp_city(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    period = user_data.get("temp_period")
    city = message.text.strip()

    forecast = ""
    inline_kb = None

    if period == 'today':
        forecast = await get_today_weather(city)
        inline_kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔍 Подробнее (почасовая)", callback_data=f"hourly_{city}")
        )
    elif period == 'tomorrow':
        forecast = await get_tomorrow_weather(city)
        inline_kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔍 Подробнее (почасовая)", callback_data=f"hourly_tomorrow_{city}")
        )
    elif period == 'week':
        forecast = await get_week_weather(city)

    if inline_kb:
        await message.answer(forecast, reply_markup=inline_kb, parse_mode="Markdown")
    else:
        await message.answer(forecast, parse_mode="Markdown")

    await state.finish()


# --- обрабатываем ввод города - почасовая ---
@dp.message_handler(state=CityInput.input)
async def process_city_input(message: types.Message, state: FSMContext):
    city = message.text.strip()

    forecast = await get_today_weather(city)

    inline_kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔍 Подробнее (почасовая)", callback_data=f"hourly_{city}")
    )

    await message.answer(forecast, reply_markup=inline_kb)

    await state.clear()


# --- обрабатывает нажатие Почасовая погода ---
@dp.callback_query_handler(lambda c: c.data.startswith("hourly_"))
async def handle_hourly_forecast(callback_query: types.CallbackQuery):
    city = callback_query.data.replace("hourly_", "")

    api_key = config.weather_api_key
    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days=1&lang=ru"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                hours = data['forecast']['forecastday'][0]['hour']

                text = f"🕒 Почасовой прогноз в {city} на сегодня:\n\n"
                for hour in hours:
                    time = hour['time'].split(" ")[1]
                    condition = hour['condition']['text']
                    temp = hour['temp_c']
                    feels = hour['feelslike_c']
                    wind = hour['wind_kph']
                    text += f"🕓 {time} — {condition}, 🌡 {temp}°C, ощ. {feels}°C, 💨 {wind} км/ч\n"

                if len(text) > 4000:
                    for i in range(0, len(text), 4000):
                        await bot.send_message(callback_query.from_user.id, text[i:i+4000])
                else:
                    await bot.send_message(callback_query.from_user.id, text)
            else:
                await bot.send_message(callback_query.from_user.id, "❌ Не удалось получить почасовой прогноз.")

    await callback_query.answer()



# ========================= УВЕДОМЛЕНИЯ =========================

# --- Обработчик кнопки "Уведомления" в настройках ---
# Показывает меню для выбора типа уведомлений (утро/вечер)
@dp.message_handler(lambda m: m.text == "Уведомления")
async def notifications_menu(message: types.Message):
    await message.answer("Выберите настройки уведомлений:", reply_markup=keyboard.get_notify_main_kb())

# --- Обработчик кнопки "Настроить утренние уведомления" ---
# Показывает клавиатуру с вариантами времени на утро
@dp.message_handler(lambda m: m.text == "Настроить утренние уведомления")
async def choose_morning_time(message: types.Message):
    await message.answer("Выберите время утреннего уведомления:", reply_markup=keyboard.get_morning_time_kb())
    await NotifyState.choosing_morning_time.set()

# --- Обработка выбора времени для утренних уведомлений ---
@dp.message_handler(state=NotifyState.choosing_morning_time)
async def handle_morning_time(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)

    if message.text == "Назад":
        await message.answer("Меню уведомлений", reply_markup=keyboard.get_notify_main_kb())
        return await state.finish()

    elif message.text == "Отключить утренние уведомления":
        save_notify(user_id, "morning", None)
        await message.answer("⛔ Утренние уведомления отключены.", reply_markup=keyboard.get_notify_main_kb())
        return await state.finish()

    elif message.text in ['6:00', '7:00', '8:00', '9:00', '10:00', '11:00']:
        hour, minute = map(int, message.text.split(":"))
        save_notify(user_id, "morning", {"enabled": True, "hour": hour, "minute": minute})
        await message.answer(f"✅ Утренние уведомления установлены на {message.text}", reply_markup=keyboard.get_notify_main_kb())
        return await state.finish()

    else:
        await message.answer("Пожалуйста, выберите время с клавиатуры.")

# --- Обработчик кнопки "Настроить вечерние уведомления" ---
@dp.message_handler(lambda m: m.text == "Настроить вечерние уведомления")
async def choose_evening_time(message: types.Message):
    await message.answer("Выберите время вечернего уведомления:", reply_markup=keyboard.get_evening_time_kb())
    await NotifyState.choosing_evening_time.set()

# --- Обработка выбора времени для вечерних уведомлений ---
@dp.message_handler(state=NotifyState.choosing_evening_time)
async def handle_evening_time(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)

    if message.text == "Назад":
        await message.answer("Меню уведомлений", reply_markup=keyboard.get_notify_main_kb())
        return await state.finish()

    elif message.text == "Отключить вечерние уведомления":
        save_notify(user_id, "evening", None)
        await message.answer("⛔ Вечерние уведомления отключены.", reply_markup=keyboard.get_notify_main_kb())
        return await state.finish()

    elif message.text in ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00']:
        hour, minute = map(int, message.text.split(":"))
        save_notify(user_id, "evening", {"enabled": True, "hour": hour, "minute": minute})
        await message.answer(f"✅ Вечерние уведомления установлены на {message.text}", reply_markup=keyboard.get_notify_main_kb())
        return await state.finish()

    else:
        await message.answer("Пожалуйста, выберите время с клавиатуры.")

# --- Функция сохранения уведомлений в файл ---
# user_id — идентификатор пользователя
# period — "morning" или "evening"
# data — словарь с данными уведомления или None, если нужно отключить
def save_notify(user_id, period, data):
    path = 'user_notify.json'
    if os.path.exists(path):
        with open(path, 'r') as f:
            notify_data = json.load(f)
    else:
        notify_data = {}

    notify_data[user_id] = notify_data.get(user_id, {})
    if data:
        notify_data[user_id][period] = data
    else:
        notify_data[user_id][period] = {"enabled": False}

    with open(path, 'w') as f:
        json.dump(notify_data, f)


# ========================= поддержать разработчика =========================
from aiogram.types import LabeledPrice

@dp.message_handler(lambda message: message.text == "Поддержать разработчика")
async def support_handler(message: types.Message):
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🍩 Донат — 100 ⭐", callback_data="donate_100"),
        InlineKeyboardButton("🍩 Донат — 200 ⭐", callback_data="donate_200")
    )
    await message.answer("Выберите количество звёзд для поддержки:", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith("donate_"))
async def handle_donate(callback_query: types.CallbackQuery):
    amount = int(callback_query.data.split('_')[1])

    prices = [LabeledPrice(label=f"{amount} звёзд", amount=amount * 100)]  # Telegram работает в копейках

    await bot.send_invoice(
        chat_id=callback_query.from_user.id,
        title="Поддержка разработчика",
        description=f"Благодарность за {amount} звёзд ⭐",
        payload=f"donate_{amount}",
        provider_token=config.provider_token,  # токен от платежной системы (например, Test)
        currency="USD",
        prices=prices,
        start_parameter="donation",
        need_name=True,
        need_email=False,
        need_phone_number=False,
        is_flexible=False
    )
    await callback_query.answer()


@dp.pre_checkout_query_handler(lambda query: True)
async def checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def got_payment(message: types.Message):
    amount = message.successful_payment.total_amount // 100
    await message.answer(f"Спасибо за поддержку на {amount} ⭐! ✨")



if __name__ == '__main__':
    print("Бот запущен")
    executor.start_polling(dp, skip_updates=True)
