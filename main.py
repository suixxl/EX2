import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.types import ParseMode

API_TOKEN = 'YOUR_BOT_TOKEN'

# Инициализация логирования
logging.basicConfig(level=logging.INFO)

# Создание экземпляров бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Команда /start
@dp.message_handler(commands="start")
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот, который поможет вам создать и управлять товаром.\n\n"
        "Чтобы начать, используйте команды:\n"
        "/info - узнать информацию о боте.\n"
        "/create - начать процесс создания товара."
    )

# Команда /info
@dp.message_handler(commands="info")
async def cmd_info(message: types.Message):
    await message.answer(
        "Этот бот поможет вам создать товар и управлять им.\n"
        "Вы можете добавить название товара, размер, категорию, цену и фото. После этого бот предоставит "
        "информацию о товаре и предложит подтвердить данные или изменить их.\n\n"
        "Команды, которые доступны в боте:\n"
        "/start - начать работу с ботом.\n"
        "/info - получить информацию о боте.\n"
        "/create - начать процесс создания нового товара."
    )

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import ContentType

API_TOKEN = 'YOUR_BOT_TOKEN'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


# Создаем FSM для добавления товара
class Store(StatesGroup):
    name = State()  # Название товара
    size = State()  # Размер товара
    category = State()  # Категория товара
    price = State()  # Стоимость товара
    photo = State()  # Фото товара
    confirmation = State()  # Подтверждение данных


# Стадия получения названия товара
@dp.message_handler(commands=["start"], state="*")
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я помогу тебе добавить товар. Напиши название товара.")
    await Store.name.set()


@dp.message_handler(state=Store.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Теперь выбери размер товара (например, XL, M, L, 3XL).")

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    sizes = ["XL", "3XL", "M", "L"]
    markup.add(*sizes)

    await Store.size.set()
    await message.answer("Выберите размер товара:", reply_markup=markup)


@dp.message_handler(state=Store.size)
async def process_size(message: types.Message, state: FSMContext):
    await state.update_data(size=message.text)
    await message.answer("Введите категорию товара (например, одежда, техника и т.д.)")
    await Store.category.set()


@dp.message_handler(state=Store.category)
async def process_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Введите стоимость товара (например, 1000 руб.)")
    await Store.price.set()


@dp.message_handler(state=Store.price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Отправьте фото товара.")
    await Store.photo.set()


@dp.message_handler(content_types=ContentType.PHOTO, state=Store.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1].file_id
    await state.update_data(photo=photo)

    user_data = await state.get_data()

    # Записываем товар в базу данных
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO products (name, size, category, price, photo)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_data['name'], user_data['size'], user_data['category'], user_data['price'], user_data['photo']))

    conn.commit()
    conn.close()

    await message.answer("Товар добавлен! Введите /products, чтобы увидеть все товары.")
    await state.finish()


# Команда для вывода всех товаров
@dp.message_handler(commands=['products'])
async def show_products(message: types.Message):
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    if not products:
        await message.answer("Нет товаров в базе.")
    else:
        for product in products:
            await message.answer(
                f"Название: {product[1]}\n"
                f"Размер: {product[2]}\n"
                f"Категория: {product[3]}\n"
                f"Цена: {product[4]}\n"
                f"Фото: {product[5]}"
            )

    conn.close()


# Функция для заказа товара через FSM
class Order(StatesGroup):
    article = State()  # Артикул товара
    size = State()  # Размер товара
    quantity = State()  # Количество товара
    contact = State()  # Контактные данные


@dp.message_handler(commands=['order'])
async def cmd_order(message: types.Message):
    await message.answer("Введите артикул товара, который хотите заказать.")
    await Order.article.set()


@dp.message_handler(state=Order.article)
async def process_article(message: types.Message, state: FSMContext):
    await state.update_data(article=message.text)
    await message.answer("Введите размер товара.")
    await Order.size.set()


@dp.message_handler(state=Order.size)
async def process_size(message: types.Message, state: FSMContext):
    await state.update_data(size=message.text)
    await message.answer("Введите количество товара.")
    await Order.quantity.set()


@dp.message_handler(state=Order.quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    await state.update_data(quantity=message.text)
    await message.answer("Введите ваш номер телефона.")
    await Order.contact.set()


@dp.message_handler(state=Order.contact)
async def process_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)

    user_data = await state.get_data()

    await message.answer(
        f"Ваш заказ:\n"
        f"Артикул: {user_data['article']}\n"
        f"Размер: {user_data['size']}\n"
        f"Количество: {user_data['quantity']}\n"
        f"Контакт: {user_data['contact']}"
    )

    await message.answer("Подтвердите заказ: Да/Нет.")
    await Order.contact.set()


@dp.message_handler(lambda message: message.text.lower() == 'да', state=Order.contact)
async def confirm_order(message: types.Message, state: FSMContext):
    await message.answer("Ваш заказ принят!")
    await state.finish()


@dp.message_handler(lambda message: message.text.lower() == 'нет', state=Order.contact)
async def cancel_order(message: types.Message, state: FSMContext):
    await message.answer("Ваш заказ отменен.")
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
