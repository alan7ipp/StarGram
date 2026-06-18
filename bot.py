import asyncio, logging, os, json, aiohttp, hashlib, time, sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from aiogram.enums import ParseMode
from dotenv import load_dotenv
load_dotenv()
TOKEN=os.getenv("BOT_TOKEN")
ADMIN_IDS=list(map(int,os.getenv("ADMIN_IDS").split(",")))
WALLET_ADDRESS="UQBoaCWXtSkgoygDPUns7vHUZFOuwDRzdZ5upaGXsavWzHc9"
logging.basicConfig(level=logging.INFO)
bot=Bot(token=TOKEN)
dp=Dispatcher()
conn=sqlite3.connect("database.db",check_same_thread=False)
cursor=conn.cursor()
def init_db():
    cursor.execute("CREATE TABLE IF NOT EXISTS users (tg_id INTEGER PRIMARY KEY,username TEXT,balance REAL DEFAULT 0,total_spent REAL DEFAULT 0,banned INTEGER DEFAULT 0,ban_reason TEXT DEFAULT '',ban_until REAL DEFAULT 0,created_at REAL DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY,tg_id INTEGER,order_type TEXT,item_name TEXT,quantity INTEGER,recipient TEXT,amount REAL,status TEXT DEFAULT 'pending',created_at REAL DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS deposits (id TEXT PRIMARY KEY,tg_id INTEGER,amount REAL,status TEXT DEFAULT 'pending',created_at REAL DEFAULT 0)")
    conn.commit()
init_db()
def get_user(tg_id:int):cursor.execute("SELECT * FROM users WHERE tg_id=?",(tg_id,));return cursor.fetchone()
def create_user(tg_id:int,username:str):cursor.execute("INSERT OR IGNORE INTO users(tg_id,username,balance,total_spent,banned,created_at)VALUES(?,?,0,0,0,?)",(tg_id,username,time.time()));conn.commit()
def get_balance(tg_id:int)->float:u=get_user(tg_id);return u[2]if u else 0
def is_banned(tg_id:int)->bool:
    u=get_user(tg_id)
    if not u:return False
    if u[4]==1:
        if u[6]>0 and time.time()>u[6]:cursor.execute("UPDATE users SET banned=0,ban_reason='',ban_until=0 WHERE tg_id=?",(tg_id,));conn.commit();return False
        return True
    return False
def add_balance(tg_id:int,amount:float):cursor.execute("UPDATE users SET balance=balance+?WHERE tg_id=?",(amount,tg_id));conn.commit()
def subtract_balance(tg_id:int,amount:float)->bool:
    u=get_user(tg_id)
    if u and u[2]>=amount:cursor.execute("UPDATE users SET balance=balance-?,total_spent=total_spent+?WHERE tg_id=?",(amount,amount,tg_id));conn.commit();return True
    return False
def ban_user(tg_id:int,reason:str,until:float=0):cursor.execute("UPDATE users SET banned=1,ban_reason=?,ban_until=?WHERE tg_id=?",(reason,until,tg_id));conn.commit()
def unban_user(tg_id:int):cursor.execute("UPDATE users SET banned=0,ban_reason='',ban_until=0 WHERE tg_id=?",(tg_id,));conn.commit()
def create_order(oid:str,tg_id:int,otype:str,iname:str,qty:int,rec:str,amt:float):cursor.execute("INSERT INTO orders(id,tg_id,order_type,item_name,quantity,recipient,amount,status,created_at)VALUES(?,?,?,?,?,?,?,'pending',?)",(oid,tg_id,otype,iname,qty,rec,amt,time.time()));conn.commit()
def create_deposit(did:str,tg_id:int,amt:float):cursor.execute("INSERT INTO deposits(id,tg_id,amount,status,created_at)VALUES(?,?,?,'completed',?)",(did,tg_id,amt,time.time()));conn.commit()
PRICES_USDT={"stars":{50:0.75,100:1.5,250:3.75,500:7.5,750:11.25,1000:15,2500:37.5,5000:75,10000:150,50000:750,100000:1500,1000000:15000},"premium":{3:11.99,6:15.99,12:28.99}}
ton_price_cache={"price":0,"updated":0}
async def get_ton_price()->float:
    global ton_price_cache
    now=asyncio.get_event_loop().time()
    if now-ton_price_cache["updated"]<300:return ton_price_cache["price"]
    try:
        async with aiohttp.ClientSession()as s:
            async with s.get("https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd")as r:
                data=await r.json();ton_price_cache={"price":data["the-open-network"]["usd"],"updated":now};return data["the-open-network"]["usd"]
    except:return ton_price_cache["price"]if ton_price_cache["price"]>0 else 3.5
def usdt_to_gram(usdt:float,tp:float)->float:return round(usdt/tp*1.02,2)
def fmt(t:str)->str:
    reps={
        "⚠️":'<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji>',
        "💡":'<tg-emoji emoji-id="5422439311196834318">💡</tg-emoji>',
        "🔙":'<tg-emoji emoji-id="5253997076169115797">🔙</tg-emoji>',
        "🏠":'<tg-emoji emoji-id="5416041192905265756">🏠</tg-emoji>',
        "✏️":'<tg-emoji emoji-id="5956143844457189176">✏️</tg-emoji>',
        "💬":'<tg-emoji emoji-id="5443038326535759644">💬</tg-emoji>',
        "📢":'<tg-emoji emoji-id="5278256077954105203">📢</tg-emoji>',
        "📜":'<tg-emoji emoji-id="5857288029609135806">📜</tg-emoji>',
        "🏆":'<tg-emoji emoji-id="5280769763398671636">🏆</tg-emoji>',
        "💎":'<tg-emoji emoji-id="5280922999241859582">💎</tg-emoji>',
        "💰":'<tg-emoji emoji-id="5375296873982604963">💰</tg-emoji>',
        "🎯":'<tg-emoji emoji-id="5310278924616356636">🎯</tg-emoji>',
        "🎮":'<tg-emoji emoji-id="5467583879948803288">🎮</tg-emoji>',
        "🪙":'<tg-emoji emoji-id="5886568200350472339">🪙</tg-emoji>',
        "👤":'<tg-emoji emoji-id="5373012449597335010">👤</tg-emoji>',
        "👇":'<tg-emoji emoji-id="5470177992950946662">👇</tg-emoji>',
        "📌":'<tg-emoji emoji-id="5397782960512444700">📌</tg-emoji>',
        "⚡":'<tg-emoji emoji-id="5456140674028019486">⚡</tg-emoji>',
        "🎁":'<tg-emoji emoji-id="5280615440928758599">🎁</tg-emoji>',
        "🧸":'<tg-emoji emoji-id="5280598054901145762">🧸</tg-emoji>',
        "🚀":'<tg-emoji emoji-id="5283080528818360566">🚀</tg-emoji>',
        "💳":'<tg-emoji emoji-id="5454134258580877567">💳</tg-emoji>',
        "✉️":'<tg-emoji emoji-id="5253742260054409879">✉️</tg-emoji>',
        "💵":'<tg-emoji emoji-id="5197434882321567830">💵</tg-emoji>',
        "💸":'<tg-emoji emoji-id="5472030678633684592">💸</tg-emoji>',
        "✅":'<tg-emoji emoji-id="5427009714745517609">✅</tg-emoji>',
        "⭐":'<tg-emoji emoji-id="4983748881977181112">⭐</tg-emoji>',
        "🎉":'<tg-emoji emoji-id="5461151367559141950">🎉</tg-emoji>',
        "🔑":'<tg-emoji emoji-id="5330115548900501467">🔑</tg-emoji>',
        "🌹":'<tg-emoji emoji-id="5280947338821524402">🌹</tg-emoji>',
        "🐸":'<tg-emoji emoji-id="5447410216696047103">🐸</tg-emoji>',
        "📊":'<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji>',
        "🥈":'<tg-emoji emoji-id="5447203607294265305">🥈</tg-emoji>',
        "🥇":'<tg-emoji emoji-id="5440539497383087970">🥇</tg-emoji>',
        "🥉":'<tg-emoji emoji-id="5453902265922376865">🥉</tg-emoji>',
        "📤":'<tg-emoji emoji-id="5445355530111437729">📤</tg-emoji>',
        "⚙️":'<tg-emoji emoji-id="5341715473882955310">⚙️</tg-emoji>',
        "🧾":'<tg-emoji emoji-id="5444856076954520455">🧾</tg-emoji>',
        "🗓":'<tg-emoji emoji-id="5274055917766202507">🗓</tg-emoji>',
        "⏱":'<tg-emoji emoji-id="5382194935057372936">⏱</tg-emoji>',
        "👥":'<tg-emoji emoji-id="5258513401784573443">👥</tg-emoji>',
        "🎫":'<tg-emoji emoji-id="5388752744527966897">🎫</tg-emoji>',
        "❌":'<tg-emoji emoji-id="5447644880824181073">❌</tg-emoji>',
        "📥":'<tg-emoji emoji-id="5443127283898405358">📥</tg-emoji>',
        "⚔️":'<tg-emoji emoji-id="5454014806950429357">⚔️</tg-emoji>',
        "🌀":'<tg-emoji emoji-id="5454014806950429357">🌀</tg-emoji>',
        "🔄":'<tg-emoji emoji-id="5375338737028841420">🔄</tg-emoji>',
        "💫":'<tg-emoji emoji-id="4963511421280192936">💫</tg-emoji>',
        "🍀":'<tg-emoji emoji-id="5305699699204837855">🍀</tg-emoji>',
        "👑":'<tg-emoji emoji-id="5217822164362739968">👑</tg-emoji>',
        "➕":'<tg-emoji emoji-id="5397916757333654639">➕</tg-emoji>',
        "➖":'<tg-emoji emoji-id="5388585245098391617">➖</tg-emoji>',
        "🏟️":'<tg-emoji emoji-id="5388908213754149872">🏟️</tg-emoji>',
        "🎨":'<tg-emoji emoji-id="5431456208487716895">🎨</tg-emoji>',
        "💪":'<tg-emoji emoji-id="5471883477219549006">💪</tg-emoji>',
        "◀️":'<tg-emoji emoji-id="5253997076169115797">◀️</tg-emoji>',
        "▶️":'<tg-emoji emoji-id="5253997076169115798">▶️</tg-emoji>',
    }
    for k,v in reps.items():t=t.replace(k,v)
    return t
@dp.message(Command("start"))
async def start(msg:types.Message):
    create_user(msg.from_user.id,msg.from_user.username or msg.from_user.full_name)
    await msg.answer(fmt("⭐ Добро пожаловать в StarGram — маркетплейс Telegram-активов.\n\n💎 Звёзды, Premium, юзернеймы, подарки, крипта и многое другое — без верификации по самым низким ценам."),reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Перейти в StarGram",web_app=WebAppInfo(url="https://alan7ipp.github.io/StarGram/"),icon_custom_emoji_id="5283080528818360566")],[InlineKeyboardButton(text="Сообщество StarGram",url="https://t.me/StarGramX",icon_custom_emoji_id="5278256077954105203")],[InlineKeyboardButton(text="Чат StarGram",url="https://t.me/StarGramChat",icon_custom_emoji_id="5443038326535759644")]]),parse_mode=ParseMode.HTML)
@dp.message(Command("admin"))
async def admin(msg:types.Message):
    if msg.from_user.id in ADMIN_IDS:await msg.answer(fmt("👑 Админ-панель\n\n/ban ID причина [часы]\n/unban ID\n/give ID сумма\n/take ID сумма\n/userinfo ID"),parse_mode=ParseMode.HTML)
    else:await msg.answer(fmt("❌ Нет доступа"),parse_mode=ParseMode.HTML)
@dp.message(Command("userinfo"))
async def userinfo(msg:types.Message):
    if msg.from_user.id not in ADMIN_IDS:return
    a=msg.text.split()
    if len(a)<2:await msg.answer("/userinfo ID");return
    uid=int(a[1])if a[1].lstrip('-').isdigit()else None
    if not uid:await msg.answer("Неверный ID");return
    u=get_user(uid)
    if not u:await msg.answer("Пользователь не найден");return
    await msg.answer(fmt(f"👤 ID:{uid}\n📛 @{u[1]or'нет'}\n💰 Баланс:{u[2]}GRAM\n💸 Потрачено:{u[3]}GRAM\n🚫 Бан:{'Да'if u[4]else'Нет'}\n📝 Причина:{u[5]or'нет'}\n⏰ До:{datetime.fromtimestamp(u[6]).strftime('%d.%m.%Y %H:%M')if u[6]else'навсегда'}"),parse_mode=ParseMode.HTML)
@dp.message(Command("ban"))
async def ban(msg:types.Message):
    if msg.from_user.id not in ADMIN_IDS:return
    a=msg.text.split(maxsplit=3)
    if len(a)<3:await msg.answer("/ban ID причина [часы]");return
    uid=int(a[1])if a[1].isdigit()else None
    if not uid:await msg.answer("Неверный ID");return
    reason=a[2]if len(a)>2 else''
    until=float(a[3])*3600+time.time()if len(a)>3 else 0
    ban_user(uid,reason,until);await msg.answer(fmt(f"🚫 {uid} забанен\n📝 {reason}"))
@dp.message(Command("unban"))
async def unban(msg:types.Message):
    if msg.from_user.id not in ADMIN_IDS:return
    a=msg.text.split()
    if len(a)<2:await msg.answer("/unban ID");return
    uid=int(a[1])if a[1].isdigit()else None
    if not uid:await msg.answer("Неверный ID");return
    unban_user(uid);await msg.answer(fmt(f"✅ {uid} разбанен"))
@dp.message(Command("give"))
async def give(msg:types.Message):
    if msg.from_user.id not in ADMIN_IDS:return
    a=msg.text.split()
    if len(a)<3:await msg.answer("/give ID сумма");return
    uid=int(a[1])if a[1].isdigit()else None
    if not uid:await msg.answer("Неверный ID");return
    amt=float(a[2]);add_balance(uid,amt);await msg.answer(fmt(f"💰 +{amt} GRAM → {uid}"))
@dp.message(Command("take"))
async def take(msg:types.Message):
    if msg.from_user.id not in ADMIN_IDS:return
    a=msg.text.split()
    if len(a)<3:await msg.answer("/take ID сумма");return
    uid=int(a[1])if a[1].isdigit()else None
    if not uid:await msg.answer("Неверный ID");return
    amt=float(a[2]);subtract_balance(uid,amt);await msg.answer(fmt(f"💸 -{amt} GRAM ← {uid}"))
@dp.message(F.content_type=="web_app_data")
async def webapp(msg:types.Message):
    d=json.loads(msg.web_app_data.data)
    act=d.get("action","order")
    buyer=msg.from_user
    create_user(buyer.id,buyer.username or buyer.full_name)
    if is_banned(buyer.id):await msg.answer(fmt("🚫 Вы заблокированы."),parse_mode=ParseMode.HTML);return
    if act=="deposit":
        amt=float(d.get("amount",0))
        if amt<0.1:await msg.answer(fmt("❌ Минимум 0.1 GRAM"),parse_mode=ParseMode.HTML);return
        did=hashlib.md5(f"{buyer.id}{time.time()}".encode()).hexdigest()[:8]
        create_deposit(did,buyer.id,amt);add_balance(buyer.id,amt)
        await msg.answer(fmt(f"✅ Пополнено +{amt} GRAM\n💰 Баланс: {get_balance(buyer.id)} GRAM"),parse_mode=ParseMode.HTML)
        for aid in ADMIN_IDS:
            try:await bot.send_message(aid,fmt(f"💰 Пополнение!\n👤 @{buyer.username or buyer.full_name} (ID:{buyer.id})\n+{amt} GRAM\nБаланс: {get_balance(buyer.id)} GRAM"),parse_mode=ParseMode.HTML)
            except:pass
        return
    if act=="order":
        otype=d.get("type");price=float(d.get("price",0));qty=d.get("quantity");rec=d.get("recipient");pfb=d.get("paid_from_balance",False)
        ic="⭐"if otype=="stars"else"👑"if otype=="premium"else"🎁"
        it=f"{qty} звёзд"if otype=="stars"else f"Premium на {qty} мес."if otype=="premium"else d.get("name")
        oid=hashlib.md5(f"{buyer.id}{time.time()}".encode()).hexdigest()[:8]
        if pfb:
            if subtract_balance(buyer.id,price):
                create_order(oid,buyer.id,otype,it,qty,rec,price)
                await msg.answer(fmt(f"✅ Заказ #{oid}\n🛍 {ic} {it}\n📩 {rec}\n💰 -{price} GRAM\nОстаток: {get_balance(buyer.id)} GRAM\n⏳ Ожидайте отправки!"),parse_mode=ParseMode.HTML)
                for aid in ADMIN_IDS:
                    try:await bot.send_message(aid,fmt(f"🔔 Заказ #{oid}!\n👤 @{buyer.username or buyer.full_name} (ID:{buyer.id})\n🛍 {ic} {it}\n📩 {rec}\n💰 {price} GRAM (с баланса)\n⚡ Отправь товар!"),parse_mode=ParseMode.HTML)
                    except:pass
            else:await msg.answer(fmt("❌ Недостаточно средств"),parse_mode=ParseMode.HTML)
        else:
            create_order(oid,buyer.id,otype,it,qty,rec,price)
            nano=int(price*1e9);link=f"ton://transfer/{WALLET_ADDRESS}?amount={nano}&text=StarGram-{oid}"
            await msg.answer(fmt(f"🛒 Заказ #{oid}\n🛍 {ic} {it}\n📩 {rec}\n💰 {price} GRAM\n👇 Оплатите:"),reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💳 Оплатить",url=link)]]),parse_mode=ParseMode.HTML)
            for aid in ADMIN_IDS:
                try:await bot.send_message(aid,fmt(f"🔔 Заказ #{oid}\n👤 @{buyer.username or buyer.full_name}\n🛍 {ic} {it}\n📩 {rec}\n💰 {price} GRAM\n⏳ Ждёт оплаты"),parse_mode=ParseMode.HTML)
                except:pass
        return
    if act in["admin_ban","admin_unban","admin_give","admin_take","admin_userinfo"]:
        if buyer.id not in ADMIN_IDS:return
        uid=int(d.get("user_id",0))
        if act=="admin_userinfo":
            u=get_user(uid)
            await msg.answer(fmt(f"👤 ID:{uid}\n📛 @{u[1]if u else'нет'}\n💰 {u[2]if u else 0} GRAM\n🚫 {'Да'if u and u[4]else'Нет'}"),parse_mode=ParseMode.HTML)
        elif act=="admin_ban":ban_user(uid,d.get("reason",""),float(d.get("hours",0))*3600+time.time());await msg.answer(fmt(f"🚫 {uid} забанен"))
        elif act=="admin_unban":unban_user(uid);await msg.answer(fmt(f"✅ {uid} разбанен"))
        elif act=="admin_give":add_balance(uid,float(d.get("amount",0)));await msg.answer(fmt(f"💰 +{d.get('amount')} GRAM → {uid}"))
        elif act=="admin_take":subtract_balance(uid,float(d.get("amount",0)));await msg.answer(fmt(f"💸 -{d.get('amount')} GRAM ← {uid}"))
async def main():print("Бот запущен!");await dp.start_polling(bot)
if __name__=="__main__":asyncio.run(main())