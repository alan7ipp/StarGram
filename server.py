from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3, hashlib, time, requests, re

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8940904434:AAHrKr9LfI5t-Kf6LPM42A3LjnyoQV26Yi0"
WALLET_ADDRESS = "UQBoaCWXtSkgoygDPUns7vHUZFOuwDRzdZ5upaGXsavWzHc9"
ADMIN_IDS = [5312114620, 8310460385]

def get_db():
    conn = sqlite3.connect("/opt/render/project/src/database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS users (tg_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0, total_spent REAL DEFAULT 0, banned INTEGER DEFAULT 0, ban_reason TEXT DEFAULT '', ban_until REAL DEFAULT 0, ref_id INTEGER DEFAULT 0, ref_earned REAL DEFAULT 0, created_at REAL DEFAULT 0)")
    conn.execute("CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, tg_id INTEGER, order_type TEXT, item_name TEXT, quantity INTEGER, recipient TEXT, amount REAL, status TEXT DEFAULT 'pending', created_at REAL DEFAULT 0)")
    conn.execute("CREATE TABLE IF NOT EXISTS deposits (id TEXT PRIMARY KEY, tg_id INTEGER, amount REAL, tx_hash TEXT, status TEXT DEFAULT 'pending', created_at REAL DEFAULT 0)")
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    return "StarGram API OK"

@app.route("/api/balance/<int:tg_id>")
def balance(tg_id):
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO users (tg_id, username, balance, total_spent, banned, created_at) VALUES (?, '', 0, 0, 0, ?)", (tg_id, time.time()))
    conn.commit()
    user = conn.execute("SELECT balance FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
    conn.close()
    return jsonify({"balance": user["balance"] if user else 0})

@app.route("/api/deposit/confirm", methods=["POST"])
def deposit_confirm():
    data = request.json
    tg_id = data.get("tg_id")
    amount = float(data.get("amount", 0))
    tx_hash = data.get("tx_hash", "")
    if amount < 0.1: return jsonify({"error": "min 0.1"}), 400
    did = hashlib.md5(f"{tg_id}{time.time()}{tx_hash}".encode()).hexdigest()[:8]
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO users (tg_id, username, balance, total_spent, banned, created_at) VALUES (?, '', 0, 0, 0, ?)", (tg_id, time.time()))
    conn.execute("INSERT INTO deposits (id, tg_id, amount, tx_hash, status, created_at) VALUES (?, ?, ?, ?, 'completed', ?)", (did, tg_id, amount, tx_hash, time.time()))
    conn.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (amount, tg_id))
    new_balance = conn.execute("SELECT balance FROM users WHERE tg_id = ?", (tg_id,)).fetchone()["balance"]
    # Реферальный бонус
    ref = conn.execute("SELECT ref_id FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
    if ref and ref["ref_id"]:
        bonus = round(amount * 0.05, 2)
        conn.execute("UPDATE users SET balance = balance + ?, ref_earned = ref_earned + ? WHERE tg_id = ?", (bonus, bonus, ref["ref_id"]))
    conn.commit()
    conn.close()
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": tg_id, "text": f"✅ Баланс пополнен на {amount} GRAM\n💰 Баланс: {new_balance} GRAM"})
    except: pass
    for aid in ADMIN_IDS:
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": aid, "text": f"💰 Пополнение!\n👤 ID:{tg_id}\n+{amount} GRAM"})
        except: pass
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
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO users (tg_id, username, balance, total_spent, banned, created_at) VALUES (?, '', 0, 0, 0, ?)", (tg_id, time.time()))
    if pfb:
        user = conn.execute("SELECT balance FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        if user and user["balance"] >= price:
            conn.execute("UPDATE users SET balance = balance - ?, total_spent = total_spent + ? WHERE tg_id = ?", (price, price, tg_id))
            conn.execute("INSERT INTO orders (id, tg_id, order_type, item_name, quantity, recipient, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', ?)", (oid, tg_id, otype, name, qty, rec, price, time.time()))
            new_balance = conn.execute("SELECT balance FROM users WHERE tg_id = ?", (tg_id,)).fetchone()["balance"]
            conn.commit()
            conn.close()
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": tg_id, "text": f"✅ Заказ #{oid}\n🛍 {name}\n📩 {rec}\n💰 -{price} GRAM\nБаланс: {new_balance} GRAM"})
            except: pass
            for aid in ADMIN_IDS:
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": aid, "text": f"🔔 Заказ #{oid}!\n👤 ID:{tg_id}\n🛍 {name}\n📩 {rec}\n💰 {price} GRAM\n⚡ Отправь!"})
                except: pass
            return jsonify({"status": "ok", "balance": new_balance})
        else: conn.close(); return jsonify({"error": "insufficient"}), 400
    conn.close()
    return jsonify({"status": "ok", "order_id": oid})

@app.route("/api/orders/<int:tg_id>")
def user_orders(tg_id):
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE tg_id = ? ORDER BY created_at DESC LIMIT 20", (tg_id,)).fetchall()
    conn.close()
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
    conn = get_db()
    if action == "userinfo":
        u = conn.execute("SELECT * FROM users WHERE tg_id = ?", (uid,)).fetchone()
        conn.close()
        if u: return jsonify({"tg_id": u["tg_id"], "username": u["username"], "balance": u["balance"], "banned": u["banned"]})
        return jsonify({"error": "not found"}), 404
    elif action == "ban":
        reason = data.get("reason", ""); hours = float(data.get("hours", 0))
        until = time.time() + hours * 3600 if hours > 0 else 0
        conn.execute("UPDATE users SET banned=1, ban_reason=?, ban_until=? WHERE tg_id=?", (reason, until, uid))
    elif action == "unban": conn.execute("UPDATE users SET banned=0 WHERE tg_id=?", (uid,))
    elif action == "give": conn.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (float(data.get("amount", 0)), uid))
    elif action == "take": conn.execute("UPDATE users SET balance = balance - ? WHERE tg_id = ?", (float(data.get("amount", 0)), uid))
    conn.commit(); conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/ref/<int:tg_id>")
def ref_link(tg_id):
    return jsonify({"ref_link": f"https://t.me/StarGramBot?start={tg_id}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)