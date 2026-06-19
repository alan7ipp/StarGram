
from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib, time, requests, re, os, sqlite3

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8940904434:AAHrKr9LfI5t-Kf6LPM42A3LjnyoQV26Yi0"
WALLET_ADDRESS = "UQBoaCWXtSkgoygDPUns7vHUZFOuwDRzdZ5upaGXsavWzHc9"
ADMIN_IDS = [5312114620, 8310460385]

# Turso конфигурация
TURSO_URL = "libsql://stargram-alan7ipp.aws-ap-northeast-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODE4ODc2MDksImlkIjoiMDE5ZWUwYzUtN2MwMS03NDYyLWJmMmUtYTU3NDc5NWU4MjkyIiwicmlkIjoiMjUzOGQ2YzUtODk0Yy00YjhlLWFhNjAtYjI0ZGI2MDkwMzQzIn0.XRc4lkvdyyB3qCwiwqTArpugZhfm2Bcrmc1gwopRq1UAtgs6BO60aKq2qgj4oWVnjhYNcDgN9K-3OgBoqw3lDg"

# Подключение к Turso через HTTP
def turso_query(sql, params=()):
    """Выполняет SQL запрос к Turso через HTTP API"""
    url = f"{TURSO_URL}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json"
    }
    # Формируем statements
    statements = []
    if isinstance(sql, str):
        statements = [{"sql": sql, "args": list(params)}]
    elif isinstance(sql, list):
        statements = sql
    
    body = {"requests": [{"type": "execute", "stmt": s["sql"], "args": s.get("args", [])} for s in statements]}
    
    try:
        resp = requests.post(url, headers=headers, json=body)
        return resp.json()
    except Exception as e:
        print(f"Turso error: {e}")
        return {"error": str(e)}

def turso_query_all(sql, params=()):
    """Выполняет SELECT и возвращает все строки"""
    url = f"{TURSO_URL}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {"requests": [{"type": "execute", "stmt": sql, "args": list(params)}]}
    try:
        resp = requests.post(url, headers=headers, json=body)
        data = resp.json()
        if "results" in data and data["results"]:
            result = data["results"][0]
            if result.get("type") == "ok" and "response" in result:
                response = result["response"]
                if response.get("type") == "results" and "rows" in response:
                    cols = response["results"]["columns"]
                    rows = response["results"]["rows"]
                    return [dict(zip(cols, row)) for row in rows]
        return []
    except Exception as e:
        print(f"Turso error: {e}")
        return []

def turso_execute(sql, params=()):
    """Выполняет INSERT/UPDATE/DELETE"""
    turso_query(sql, params)

def turso_fetchone(sql, params=()):
    """Выполняет SELECT и возвращает одну строку"""
    rows = turso_query_all(sql, params)
    return rows[0] if rows else None

# Инициализация базы данных
def init_db():
    turso_execute("CREATE TABLE IF NOT EXISTS users (tg_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0, total_spent REAL DEFAULT 0, banned INTEGER DEFAULT 0, ban_reason TEXT DEFAULT '', ban_until REAL DEFAULT 0, ref_id INTEGER DEFAULT 0, ref_earned REAL DEFAULT 0, created_at REAL DEFAULT 0)")
    turso_execute("CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, tg_id INTEGER, order_type TEXT, item_name TEXT, quantity INTEGER, recipient TEXT, amount REAL, status TEXT DEFAULT 'pending', created_at REAL DEFAULT 0)")
    turso_execute("CREATE TABLE IF NOT EXISTS deposits (id TEXT PRIMARY KEY, tg_id INTEGER, amount REAL, tx_hash TEXT, status TEXT DEFAULT 'pending', created_at REAL DEFAULT 0)")
    print("Turso DB initialized!")

init_db()

# Премиум эмодзи
E = {
    "star": '<tg-emoji emoji-id="4983748881977181112">⭐</tg-emoji>',
    "diamond": '<tg-emoji emoji-id="5280922999241859582">💎</tg-emoji>',
    "crown": '<tg-emoji emoji-id="5217822164362739968">👑</tg-emoji>',
    "user": '<tg-emoji emoji-id="5373012449597335010">👤</tg-emoji>',
    "money": '<tg-emoji emoji-id="5375296873982604963">💰</tg-emoji>',
    "coin": '<tg-emoji emoji-id="5886568200350472339">🪙</tg-emoji>',
    "check": '<tg-emoji emoji-id="5427009714745517609">✅</tg-emoji>',
    "lightning": '<tg-emoji emoji-id="5456140674028019486">⚡</tg-emoji>',
    "gift": '<tg-emoji emoji-id="5280615440928758599">🎁</tg-emoji>',
    "msg": '<tg-emoji emoji-id="5253742260054409879">📩</tg-emoji>',
    "clock": '<tg-emoji emoji-id="5382194935057372936">⏱</tg-emoji>',
    "id_icon": '🆔',
}

def send_telegram(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": chat_id, "text": text, "parse_mode": "HTML"
        }, timeout=5)
    except: pass

@app.route("/")
def home():
    return "StarGram API OK"

@app.route("/api/balance/<int:tg_id>")
def balance(tg_id):
    turso_execute("INSERT OR IGNORE INTO users (tg_id, username, balance, total_spent, banned, created_at) VALUES (?, '', 0, 0, 0, ?)", (tg_id, time.time()))
    user = turso_fetchone("SELECT balance FROM users WHERE tg_id = ?", (tg_id,))
    return jsonify({"balance": user["balance"] if user else 0})

@app.route("/api/deposit/confirm", methods=["POST"])
def deposit_confirm():
    data = request.json
    tg_id = data.get("tg_id")
    amount = float(data.get("amount", 0))
    tx_hash = data.get("tx_hash", "")
    if amount < 0.1: return jsonify({"error": "min 0.1"}), 400
    did = hashlib.md5(f"{tg_id}{time.time()}{tx_hash}".encode()).hexdigest()[:8]
    
    turso_execute("INSERT OR IGNORE INTO users (tg_id, username, balance, total_spent, banned, created_at) VALUES (?, '', 0, 0, 0, ?)", (tg_id, time.time()))
    turso_execute("INSERT INTO deposits (id, tg_id, amount, tx_hash, status, created_at) VALUES (?, ?, ?, ?, 'completed', ?)", (did, tg_id, amount, tx_hash, time.time()))
    turso_execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (amount, tg_id))
    
    user = turso_fetchone("SELECT balance FROM users WHERE tg_id = ?", (tg_id,))
    new_balance = user["balance"] if user else amount

    # Красивое уведомление покупателю
    send_telegram(tg_id,
        f"{E['coin']} <b>Баланс пополнен!</b>\n\n"
        f"{E['money']} Сумма: <b>+{amount} GRAM</b>\n"
        f"{E['coin']} Новый баланс: <b>{new_balance} GRAM</b>\n\n"
        f"{E['check']} Средства зачислены и доступны для покупок!"
    )

    # Уведомление админам
    for aid in ADMIN_IDS:
        send_telegram(aid,
            f"{E['money']} <b>Пополнение баланса!</b>\n\n"
            f"{E['user']} ID: <b>{tg_id}</b>\n"
            f"{E['money']} Сумма: <b>+{amount} GRAM</b>\n"
            f"{E['coin']} Новый баланс: <b>{new_balance} GRAM</b>"
        )

    return jsonify({"status": "ok", "balance": new_balance})

@app.route("/api/order", methods=["POST"])
def order():
    data = request.json
    tg_id = data.get("tg_id")
    otype = data.get("type")
    price = float(data.get("price", 0))
    qty = data.get("quantity")
    rec = data.get("recipient")
    name = data.get("name")
    pfb = data.get("paid_from_balance", False)
    oid = hashlib.md5(f"{tg_id}{time.time()}".encode()).hexdigest()[:8]

    turso_execute("INSERT OR IGNORE INTO users (tg_id, username, balance, total_spent, banned, created_at) VALUES (?, '', 0, 0, 0, ?)", (tg_id, time.time()))

    if pfb:
        user = turso_fetchone("SELECT balance FROM users WHERE tg_id = ?", (tg_id,))
        if user and user["balance"] >= price:
            turso_execute("UPDATE users SET balance = balance - ?, total_spent = total_spent + ? WHERE tg_id = ?", (price, price, tg_id))
            turso_execute("INSERT INTO orders (id, tg_id, order_type, item_name, quantity, recipient, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', ?)", (oid, tg_id, otype, name, qty, rec, price, time.time()))
            
            user_updated = turso_fetchone("SELECT balance FROM users WHERE tg_id = ?", (tg_id,))
            new_balance = user_updated["balance"] if user_updated else 0

            item_icon = E['star'] if otype == 'stars' else E['crown']
            item_text = f"{qty} звёзд" if otype == 'stars' else f"Premium на {qty} мес."

            # Уведомление покупателю
            send_telegram(tg_id,
                f"{E['check']} <b>Покупка совершена!</b>\n\n"
                f"{E['id_icon']} Заказ <b>#{oid}</b>\n"
                f"{item_icon} Товар: <b>{item_text}</b>\n"
                f"{E['msg']} Получатель: <b>{rec}</b>\n"
                f"{E['money']} Списано с баланса: <b>{price} GRAM</b>\n"
                f"{E['coin']} Остаток: <b>{new_balance} GRAM</b>\n\n"
                f"{E['clock']} Ожидайте — мы отправим товар в ближайшее время!"
            )

            # Уведомление админам
            for aid in ADMIN_IDS:
                send_telegram(aid,
                    f"{E['diamond']} <b>Новая покупка!</b>\n\n"
                    f"{E['id_icon']} Заказ <b>#{oid}</b>\n"
                    f"{E['user']} Покупатель: <b>ID:{tg_id}</b>\n"
                    f"{item_icon} Товар: <b>{item_text}</b>\n"
                    f"{E['msg']} Получатель: <b>{rec}</b>\n"
                    f"{E['money']} Сумма: <b>{price} GRAM</b> (с баланса)\n\n"
                    f"{E['lightning']} <b>Зайди на Fragment и отправь товар!</b>"
                )

            return jsonify({"status": "ok", "balance": new_balance})
        else:
            return jsonify({"error": "insufficient"}), 400

    return jsonify({"status": "ok", "order_id": oid})

@app.route("/api/orders/<int:tg_id>")
def user_orders(tg_id):
    orders = turso_query_all("SELECT * FROM orders WHERE tg_id = ? ORDER BY created_at DESC LIMIT 20", (tg_id,))
    return jsonify([{"id": o["id"], "item_name": o["item_name"], "recipient": o["recipient"], "amount": o["amount"], "status": o["status"], "created_at": o["created_at"]} for o in orders])

@app.route("/api/telegram/user/<username>")
def telegram_user(username):
    try:
        headers = {"User-Agent": "TelegramBot"}
        resp = requests.get(f"https://t.me/{username}", headers=headers, timeout=10)
        if "tgme_page_title" in resp.text:
            name_match = re.search(r'<meta property="og:title" content="([^"]+)"', resp.text)
            photo_match = re.search(r'<meta property="og:image" content="([^"]+)"', resp.text)
            return jsonify({"username": username, "name": name_match.group(1) if name_match else username, "photo": photo_match.group(1) if photo_match else None})
        return jsonify({"error": "not found"}), 404
    except: return jsonify({"error": "request failed"}), 500

@app.route("/api/admin/<action>", methods=["POST"])
def admin_action(action):
    data = request.json
    admin_id = data.get("admin_id")
    if admin_id not in ADMIN_IDS: return jsonify({"error": "forbidden"}), 403
    uid = int(data.get("user_id", 0))
    
    if action == "userinfo":
        u = turso_fetchone("SELECT * FROM users WHERE tg_id = ?", (uid,))
        if u: return jsonify({"tg_id": u["tg_id"], "username": u["username"], "balance": u["balance"], "banned": u["banned"]})
        return jsonify({"error": "not found"}), 404
    elif action == "ban":
        reason = data.get("reason", ""); hours = float(data.get("hours", 0))
        until = time.time() + hours * 3600 if hours > 0 else 0
        turso_execute("UPDATE users SET banned=1, ban_reason=?, ban_until=? WHERE tg_id=?", (reason, until, uid))
    elif action == "unban":
        turso_execute("UPDATE users SET banned=0 WHERE tg_id=?", (uid,))
    elif action == "give":
        turso_execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (float(data.get("amount", 0)), uid))
    elif action == "take":
        turso_execute("UPDATE users SET balance = balance - ? WHERE tg_id = ?", (float(data.get("amount", 0)), uid))
    
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)