from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3, hashlib, time, os, requests

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8940904434:AAHrKr9LfI5t-Kf6LPM42A3LjnyoQV26Yi0"
WALLET_ADDRESS = "UQBoaCWXtSkgoygDPUns7vHUZFOuwDRzdZ5upaGXsavWzHc9"
ADMIN_IDS = [5312114620, 8310460385]

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS users (tg_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0, total_spent REAL DEFAULT 0, banned INTEGER DEFAULT 0, ban_reason TEXT DEFAULT '', ban_until REAL DEFAULT 0, created_at REAL DEFAULT 0)")
    conn.execute("CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, tg_id INTEGER, order_type TEXT, item_name TEXT, quantity INTEGER, recipient TEXT, amount REAL, status TEXT DEFAULT 'pending', created_at REAL DEFAULT 0)")
    conn.execute("CREATE TABLE IF NOT EXISTS deposits (id TEXT PRIMARY KEY, tg_id INTEGER, amount REAL, status TEXT DEFAULT 'pending', created_at REAL DEFAULT 0)")
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    return "StarGram API is running!"

@app.route("/api/user/<int:tg_id>")
def get_user(tg_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
    conn.close()
    if user:
        return jsonify({"tg_id": user["tg_id"], "username": user["username"], "balance": user["balance"], "banned": user["banned"]})
    return jsonify({"error": "not found"}), 404

@app.route("/api/balance/<int:tg_id>")
def balance(tg_id):
    conn = get_db()
    user = conn.execute("SELECT balance FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
    conn.close()
    return jsonify({"balance": user["balance"] if user else 0})

@app.route("/api/deposit", methods=["POST"])
def deposit():
    data = request.json
    tg_id = data.get("tg_id")
    amount = float(data.get("amount", 0))
    if amount < 0.1:
        return jsonify({"error": "min 0.1"}), 400
    did = hashlib.md5(f"{tg_id}{time.time()}".encode()).hexdigest()[:8]
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO users (tg_id, username, balance, total_spent, banned, created_at) VALUES (?, ?, 0, 0, 0, ?)", (tg_id, "", time.time()))
    conn.execute("INSERT INTO deposits (id, tg_id, amount, status, created_at) VALUES (?, ?, ?, 'completed', ?)", (did, tg_id, amount, time.time()))
    conn.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (amount, tg_id))
    conn.commit()
    new_balance = conn.execute("SELECT balance FROM users WHERE tg_id = ?", (tg_id,)).fetchone()["balance"]
    conn.close()
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": tg_id, "text": f"✅ Баланс пополнен на {amount} GRAM\n💰 Баланс: {new_balance} GRAM"})
    except: pass
    for aid in ADMIN_IDS:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": aid, "text": f"💰 Пополнение!\n👤 ID:{tg_id}\n+{amount} GRAM"})
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
    conn.execute("INSERT OR IGNORE INTO users (tg_id, username, balance, total_spent, banned, created_at) VALUES (?, ?, 0, 0, 0, ?)", (tg_id, "", time.time()))
    if pfb:
        user = conn.execute("SELECT balance FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        if user and user["balance"] >= price:
            conn.execute("UPDATE users SET balance = balance - ?, total_spent = total_spent + ? WHERE tg_id = ?", (price, price, tg_id))
            conn.execute("INSERT INTO orders (id, tg_id, order_type, item_name, quantity, recipient, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)", (oid, tg_id, otype, name, qty, rec, price, time.time()))
            conn.commit()
            conn.close()
            try:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": tg_id, "text": f"✅ Заказ #{oid}\n🛍 {name}\n📩 {rec}\n💰 -{price} GRAM"})
            except: pass
            for aid in ADMIN_IDS:
                try:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": aid, "text": f"🔔 Заказ #{oid}!\n👤 ID:{tg_id}\n🛍 {name}\n📩 {rec}\n💰 {price} GRAM\n⚡ Отправь товар!"})
                except: pass
            return jsonify({"status": "ok"})
        else:
            conn.close()
            return jsonify({"error": "insufficient"}), 400
    conn.execute("INSERT INTO orders (id, tg_id, order_type, item_name, quantity, recipient, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)", (oid, tg_id, otype, name, qty, rec, price, time.time()))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "order_id": oid})

@app.route("/api/telegram/user/<username>")
def telegram_user(username):
    try:
        resp = requests.get(f"https://t.me/{username}", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if "Telegram: Contact" in resp.text:
            return jsonify({"error": "not found"}), 404
        import re
        name_match = re.search(r'<meta property="og:title" content="([^"]+)"', resp.text)
        photo_match = re.search(r'<meta property="og:image" content="([^"]+)"', resp.text)
        return jsonify({"username": username, "name": name_match.group(1) if name_match else username, "photo": photo_match.group(1) if photo_match else None})
    except:
        return jsonify({"error": "request failed"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)