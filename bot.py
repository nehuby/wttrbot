import logging
from io import BytesIO
from pathlib import Path

from aiopywttr import Wttr
import pywttr_models
import warnings
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.files import PickleStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiohttp.client_exceptions import ClientResponseError
from PIL import Image, ImageDraw, ImageFont
from prettytable import PrettyTable
from config import API_TOKEN

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=PickleStorage(Path("states.json")))
warnings.simplefilter("ignore", DeprecationWarning)

def get_sizes(tablica: str, font: ImageFont) -> tuple:
    spl = tablica.splitlines()
    w = sum(font.getsize(letter)[0] for letter in spl[0]) 
    h = sum(font.getsize(line[0])[1] for line in spl)
    return w, h


def picture(text: str):
    font = ImageFont.truetype(
        "LiberationMono-Regular.ttf", size=25
    )
    img = Image.new("RGBA", get_sizes(text, font), "#0e1621")
    idraw = ImageDraw.Draw(img)
    idraw.text((0, 0), text, "white", font=font)
    with BytesIO() as buf:
        img.save(buf, format="PNG")
        return buf.getvalue()


def dayweather(i: int, day: pywttr_models.ru.WeatherItem):
    days = day.hourly[i]
    return f"""Статус: {days.lang_ru[0].value}
Температура, С: {days.temp_c}
По ощущению, С: {days.feels_like_c}
Скорость ветра, м/с: {int(round(int(days.windspeed_kmph) / 3.6, 0))}
Направление ветра: {days.winddir16_point}
Видимость, км: {days.visibility}
Влажность, %: {days.humidity}"""


class Data(StatesGroup):
    place = State()
    weather = State()


@dp.message_handler(commands="start", state="*")
async def date_start(message: types.Message):
    await Data.place.set()
    await message.answer("Введите населенный пункт")


@dp.message_handler(text="Изменить населенный пункт", state=Data.weather)
async def enter_city(message: types.Message, state: FSMContext):
    name = await state.get_data()
    if name is None:
        return
    await Data.previous()
    await message.answer("Введите населенный пункт")


@dp.message_handler(state=Data.place)
async def load_place(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            data["place"] = await Wttr(message.text).ru()
    except ClientResponseError:
        await message.answer("Населенный пункт не найден, попробуйте заново")
        return
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("Сейчас", "Сегодня").add("Завтра", "Послезавтра").add(
        "Изменить населенный пункт"
    )
    await message.answer("Когда?", reply_markup=keyboard)
    await Data.next()


@dp.message_handler(text="Сейчас", state=Data.weather)
async def now_weather(message: types.Message, state: FSMContext):
    name = await state.get_data()
    gm: pywttr_models.ru.Model = name["place"]
    now = gm.current_condition[0]
    x = PrettyTable()
    x.add_rows(
        [
            ["Статус", now.lang_ru[0].value],
            ["Температура, С", now.temp_c],
            ["По ощущению, С", now.feels_like_c],
            ["Скорость ветра, м/с", int(round(int(now.windspeed_kmph) / 3.6, 0))],
            ["Направление ветра", now.winddir16_point],
            ["Видимость, км", now.visibility],
            ["Влажность, %", now.humidity],
        ]
    )
    x.align = "l"
    text = "\n".join(x.get_string().splitlines()[2:])
    await message.answer_photo(picture(text))


@dp.message_handler(text="Сегодня", state=Data.weather)
async def now_weather(message: types.Message, state: FSMContext):
    name = await state.get_data()
    gm: pywttr_models.ru.Model = name["place"]
    today = gm.weather[0]
    x = PrettyTable()
    x.add_rows(
        [
            ["Ночь", dayweather(0, today)],
            ["Утро", dayweather(2, today)],
            ["День", dayweather(4, today)],
            ["Вечер", dayweather(6, today)],
        ]
    )
    splitted = x.get_string().splitlines()[3].split("|")
    length1 = len(splitted[1])
    length2 = len(splitted[2])
    x = PrettyTable()
    x.add_rows(
        [
            ["Ночь", dayweather(0, today)],
            ["-" * length1, "-" * length2],
            ["Утро", dayweather(2, today)],
            ["-" * length1, "-" * length2],
            ["День", dayweather(4, today)],
            ["-" * length1, "-" * length2],
            ["Вечер", dayweather(6, today)],
        ]
    )
    x.align = "l"
    text = "\n".join(x.get_string().splitlines()[2:])
    await message.answer_photo(picture(text))


@dp.message_handler(text="Завтра", state=Data.weather)
async def now_weather(message: types.Message, state: FSMContext):
    name = await state.get_data()
    gm: pywttr_models.ru.Model = name["place"]
    tomorrow = gm.weather[1]
    x = PrettyTable()
    x.add_rows(
        [
            ["Ночь", dayweather(0, tomorrow)],
            ["Утро", dayweather(2, tomorrow)],
            ["День", dayweather(4, tomorrow)],
            ["Вечер", dayweather(6, tomorrow)],
        ]
    )
    splitted = x.get_string().splitlines()[3].split("|")
    length1 = len(splitted[1])
    length2 = len(splitted[2])
    x = PrettyTable()
    x.add_rows(
        [
            ["Ночь", dayweather(0, tomorrow)],
            ["-" * length1, "-" * length2],
            ["Утро", dayweather(2, tomorrow)],
            ["-" * length1, "-" * length2],
            ["День", dayweather(4, tomorrow)],
            ["-" * length1, "-" * length2],
            ["Вечер", dayweather(6, tomorrow)],
        ]
    )
    x.align = "l"
    text = "\n".join(x.get_string().splitlines()[2:])
    await message.answer_photo(picture(text))


@dp.message_handler(text="Послезавтра", state=Data.weather)
async def now_weather(message: types.Message, state: FSMContext):
    name = await state.get_data()
    gm: pywttr_models.ru.Model = name["place"]
    day_after_tomorrow = gm.weather[2]
    x = PrettyTable()
    x.add_rows(
        [
            ["Ночь", dayweather(0, day_after_tomorrow)],
            ["Утро", dayweather(2, day_after_tomorrow)],
            ["День", dayweather(4, day_after_tomorrow)],
            ["Вечер", dayweather(6, day_after_tomorrow)],
        ]
    )
    splitted = x.get_string().splitlines()[3].split("|")
    length1 = len(splitted[1])
    length2 = len(splitted[2])
    x = PrettyTable()
    x.add_rows(
        [
            ["Ночь", dayweather(0, day_after_tomorrow)],
            ["-" * length1, "-" * length2],
            ["Утро", dayweather(2, day_after_tomorrow)],
            ["-" * length1, "-" * length2],
            ["День", dayweather(4, day_after_tomorrow)],
            ["-" * length1, "-" * length2],
            ["Вечер", dayweather(6, day_after_tomorrow)],
        ]
    )
    x.align = "l"
    text = "\n".join(x.get_string().splitlines()[2:])
    await message.answer_photo(picture(text))


async def on_shutdown(dp):
    await dp.storage.close()
    await dp.storage.wait_closed()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_shutdown=on_shutdown)
