import asyncio
import logging
import os
import json
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from aiogram.enums import ParseMode
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS").split(",")))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

PRICES_USDT = {
    "stars": {50: 0.75, 100: 1.50, 500: 7.50, 1000: 15.00},
    "premium": {1: 11.99, 6: 15.99, 12: 28.99}
}

ton_price_cache = {"price": 0, "updated": 0}

async def get_ton_price() -> float:
    global ton_price_cache
    now = asyncio.get_event_loop().time()
    if now - ton_price_cache["updated"] < 300:
        return ton_price_cache["price"]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd") as resp:
                data = await resp.json()
                price = data["the-open-network"]["usd"]
                ton_price_cache = {"price": price, "updated": now}
                return price
    except:
        return ton_price_cache["price"] if ton_price_cache["price"] > 0 else 3.5

def usdt_to_gram(usdt: float, ton_price: float) -> float:
    return round(usdt / ton_price * 1.02, 2)

def format_text(text: str) -> str:
    replacements = {
        "⚠️": '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji>',
        "💡": '<tg-emoji emoji-id="5422439311196834318">💡</tg-emoji>',
        "🔙": '<tg-emoji emoji-id="5253997076169115797">🔙</tg-emoji>',
        "🏠": '<tg-emoji emoji-id="5416041192905265756">🏠</tg-emoji>',
        "✏️": '<tg-emoji emoji-id="5956143844457189176">✏️</tg-emoji>',
        "💬": '<tg-emoji emoji-id="5443038326535759644">💬</tg-emoji>',
        "📢": '<tg-emoji emoji-id="5278256077954105203">📢</tg-emoji>',
        "📜": '<tg-emoji emoji-id="5857288029609135806">📜</tg-emoji>',
        "🏆": '<tg-emoji emoji-id="5280769763398671636">🏆</tg-emoji>',
        "💎": '<tg-emoji emoji-id="5280922999241859582">💎</tg-emoji>',
        "💰": '<tg-emoji emoji-id="5375296873982604963">💰</tg-emoji>',
        "🎯": '<tg-emoji emoji-id="5310278924616356636">🎯</tg-emoji>',
        "🎮": '<tg-emoji emoji-id="5467583879948803288">🎮</tg-emoji>',
        "🪙": '<tg-emoji emoji-id="5886568200350472339">🪙</tg-emoji>',
        "👤": '<tg-emoji emoji-id="5373012449597335010">👤</tg-emoji>',
        "👇": '<tg-emoji emoji-id="5470177992950946662">👇</tg-emoji>',
        "📌": '<tg-emoji emoji-id="5397782960512444700">📌</tg-emoji>',
        "⚡": '<tg-emoji emoji-id="5456140674028019486">⚡</tg-emoji>',
        "🎁": '<tg-emoji emoji-id="5280615440928758599">🎁</tg-emoji>',
        "🧸": '<tg-emoji emoji-id="5280598054901145762">🧸</tg-emoji>',
        "🚀": '<tg-emoji emoji-id="5283080528818360566">🚀</tg-emoji>',
        "💳": '<tg-emoji emoji-id="5454134258580877567">💳</tg-emoji>',
        "✉️": '<tg-emoji emoji-id="5253742260054409879">✉️</tg-emoji>',
        "💵": '<tg-emoji emoji-id="5197434882321567830">💵</tg-emoji>',
        "💸": '<tg-emoji emoji-id="5472030678633684592">💸</tg-emoji>',
        "✅": '<tg-emoji emoji-id="5427009714745517609">✅</tg-emoji>',
        "⭐": '<tg-emoji emoji-id="4983748881977181112">⭐</tg-emoji>',
        "🎉": '<tg-emoji emoji-id="5461151367559141950">🎉</tg-emoji>',
        "🔑": '<tg-emoji emoji-id="5330115548900501467">🔑</tg-emoji>',
        "🌹": '<tg-emoji emoji-id="5280947338821524402">🌹</tg-emoji>',
        "🐸": '<tg-emoji emoji-id="5447410216696047103">🐸</tg-emoji>',
        "📊": '<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji>',
        "🥈": '<tg-emoji emoji-id="5447203607294265305">🥈</tg-emoji>',
        "🥇": '<tg-emoji emoji-id="5440539497383087970">🥇</tg-emoji>',
        "🥉": '<tg-emoji emoji-id="5453902265922376865">🥉</tg-emoji>',
        "📤": '<tg-emoji emoji-id="5445355530111437729">📤</tg-emoji>',
        "⚙️": '<tg-emoji emoji-id="5341715473882955310">⚙️</tg-emoji>',
        "🧾": '<tg-emoji emoji-id="5444856076954520455">🧾</tg-emoji>',
        "🗓": '<tg-emoji emoji-id="5274055917766202507">🗓</tg-emoji>',
        "⏱": '<tg-emoji emoji-id="5382194935057372936">⏱</tg-emoji>',
        "👥": '<tg-emoji emoji-id="5258513401784573443">👥</tg-emoji>',
        "🎫": '<tg-emoji emoji-id="5388752744527966897">🎫</tg-emoji>',
        "❌": '<tg-emoji emoji-id="5447644880824181073">❌</tg-emoji>',
        "📥": '<tg-emoji emoji-id="5443127283898405358">📥</tg-emoji>',
        "⚔️": '<tg-emoji emoji-id="5454014806950429357">⚔️</tg-emoji>',
        "🌀": '<tg-emoji emoji-id="5454014806950429357">🌀</tg-emoji>',
        "🔄": '<tg-emoji emoji-id="5375338737028841420">🔄</tg-emoji>',
        "💫": '<tg-emoji emoji-id="4963511421280192936">💫</tg-emoji>',
        "🍀": '<tg-emoji emoji-id="5305699699204837855">🍀</tg-emoji>',
        "👑": '<tg-emoji emoji-id="5217822164362739968">👑</tg-emoji>',
        "➕": '<tg-emoji emoji-id="5397916757333654639">➕</tg-emoji>',
        "➖": '<tg-emoji emoji-id="5388585245098391617">➖</tg-emoji>',
        "🏟️": '<tg-emoji emoji-id="5388908213754149872">🏟️</tg-emoji>',
        "🎨": '<tg-emoji emoji-id="5431456208487716895">🎨</tg-emoji>',
        "💪": '<tg-emoji emoji-id="5471883477219549006">💪</tg-emoji>',
        "◀️": '<tg-emoji emoji-id="5253997076169115797">◀️</tg-emoji>',
        "▶️": '<tg-emoji emoji-id="5253997076169115798">▶️</tg-emoji>',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    text = format_text(
        "⭐ Добро пожаловать в StarGram — маркетплейс Telegram-активов.\n\n"
        "💎 Звёзды, Premium, юзернеймы, подарки, крипта и многое другое — без верификации по самым низким ценам."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Перейти в StarGram", web_app=WebAppInfo(url="https://alan7ipp.github.io/StarGram/"), icon_custom_emoji_id="5283080528818360566")],
        [InlineKeyboardButton(text="Сообщество StarGram", url="https://t.me/StarGramX", icon_custom_emoji_id="5278256077954105203")],
        [InlineKeyboardButton(text="Чат StarGram", url="https://t.me/StarGramChat", icon_custom_emoji_id="5443038326535759644")]
    ])
    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer(format_text(f"👑 Админ-панель\n\n👤 ID: {message.from_user.id}\n✅ Статус: Активен"), parse_mode=ParseMode.HTML)
    else:
        await message.answer(format_text("❌ Нет доступа"), parse_mode=ParseMode.HTML)


@dp.message(Command("prices"))
async def show_prices(message: types.Message):
    ton_price = await get_ton_price()
    text = f"💎 Актуальные цены\n\n🪙 1 TON = ${ton_price:.2f}\n\n⭐ Звёзды:\n"
    for qty, usdt in PRICES_USDT["stars"].items():
        text += f"{qty} звёзд — {usdt_to_gram(usdt, ton_price)} GRAM\n"
    text += "\n👑 Premium:\n"
    for months, usdt in PRICES_USDT["premium"].items():
        text += f"{months} мес. — {usdt_to_gram(usdt, ton_price)} GRAM\n"
    text += "\n💰 Наценка: +2%"
    await message.answer(format_text(text), parse_mode=ParseMode.HTML)


@dp.message(Command("course"))
async def show_course(message: types.Message):
    ton_price = await get_ton_price()
    await message.answer(format_text(f"🪙 Курс TON\n\n1 TON = ${ton_price:.2f}"), parse_mode=ParseMode.HTML)


@dp.message(F.content_type == "web_app_data")
async def handle_webapp(message: types.Message):
    data = json.loads(message.web_app_data.data)
    order_type = data.get("type")
    order_name = data.get("name")
    order_price = data.get("price")
    order_quantity = data.get("quantity")
    recipient = data.get("recipient")
    buyer = message.from_user

    if order_type == "premium":
        item_icon = "👑"
        item_text = f"Premium на {order_quantity} мес."
    elif order_type == "stars":
        item_icon = "⭐"
        item_text = f"{order_quantity} звёзд"
    else:
        item_icon = "🎁"
        item_text = order_name

    admin_text = format_text(
        f"💎 Новая покупка!\n\n"
        f"👤 Покупатель: @{buyer.username or buyer.full_name or 'нет'} (ID: {buyer.id})\n"
        f"🛍 Товар: {item_icon} {item_text}\n"
        f"📩 Получатель: {recipient}\n"
        f"💰 Сумма: {order_price} GRAM\n\n"
        f"✅ Зайди на Fragment и отправь товар!"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode=ParseMode.HTML)
        except:
            pass

    await message.answer(
        format_text(f"✅ Заказ принят!\n\n🛍 Товар: {item_icon} {item_text}\n📩 Получатель: {recipient}\n💰 Сумма: {order_price} GRAM\n\n⏳ Ожидайте — мы отправим товар в ближайшее время."),
        parse_mode=ParseMode.HTML
    )


async def main():
    print("Бот запущен!")
    ton_price = await get_ton_price()
    print(f"✅ Курс TON: ${ton_price:.2f}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())