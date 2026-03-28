import os
import requests
from flask import Flask, request, abort

# 🔑 ENV VARIABLEN
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
GROUP_ID = int(os.getenv("GROUP_ID", "0"))
TOPIC_ID = int(os.getenv("TOPIC_ID", "0"))
BASE_URL = os.getenv("BASE_URL")

app = Flask(__name__)

# 🧠 Speicher (einfach – ohne DB)
USER_STATE = {}
CONFIG = {
    "channel_id": CHANNEL_ID,
    "group_id": GROUP_ID,
    "topic_id": TOPIC_ID
}

# 🔗 Webhook setzen
def set_webhook():
    if BASE_URL:
        url = f"{BASE_URL}/{TOKEN}"
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={url}")
        print("🔗 Webhook:", r.json())

# 📤 Nachricht senden
def send_message(chat_id, text, buttons=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if buttons:
        data["reply_markup"] = buttons

    requests.post(url, json=data)

# 🔁 Weiterleiten ins Topic
def forward_to_topic(from_chat_id, message_id):
    if not CONFIG["group_id"] or not CONFIG["topic_id"]:
        print("⚠️ Gruppe oder Topic nicht gesetzt")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/forwardMessage"
    data = {
        "chat_id": CONFIG["group_id"],
        "from_chat_id": from_chat_id,
        "message_id": message_id,
        "message_thread_id": CONFIG["topic_id"]
    }

    try:
        r = requests.post(url, data=data)
        res = r.json()

        if res.get("ok"):
            print("✅ Weitergeleitet:", message_id)
        else:
            print("❌ Fehler:", res)

    except Exception as e:
        print("🔥 Exception:", e)

# 🌐 Webhook Endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        return abort(403)

    update = request.get_json()
    print("📨 Update:", update)

    # 🧠 USER INTERACTION
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        # START
        if text == "/start":
            buttons = {
                "keyboard": [
                    ["📢 Kanal setzen"],
                    ["💬 Gruppe setzen"]
                ],
                "resize_keyboard": True
            }
            send_message(chat_id, "⚙️ Setup starten:", buttons)

        elif text == "📢 Kanal setzen":
            USER_STATE[chat_id] = "set_channel"
            send_message(chat_id, "➡️ Bitte leite eine Nachricht aus deinem Kanal weiter")

        elif text == "💬 Gruppe setzen":
            USER_STATE[chat_id] = "set_group"
            send_message(chat_id, "➡️ Bitte sende eine Nachricht aus deiner Gruppe")

        # 📌 Kanal speichern
        elif "forward_from_chat" in msg:
            if USER_STATE.get(chat_id) == "set_channel":
                CONFIG["channel_id"] = msg["forward_from_chat"]["id"]
                send_message(chat_id, f"✅ Kanal gespeichert:\n{CONFIG['channel_id']}")
                USER_STATE[chat_id] = None

        # 📌 Gruppe speichern
        elif USER_STATE.get(chat_id) == "set_group":
            CONFIG["group_id"] = msg["chat"]["id"]
            send_message(chat_id, f"✅ Gruppe gespeichert:\n{CONFIG['group_id']}")
            USER_STATE[chat_id] = None

    # 📢 CHANNEL POSTS → FORWARD
    if "channel_post" in update:
        post = update["channel_post"]

        if post["chat"]["id"] == CONFIG["channel_id"]:
            print("🎯 Kanal-Post erkannt")

            message_id = post["message_id"]
            forward_to_topic(CONFIG["channel_id"], message_id)

    return "", 200

# 🌍 Root
@app.route("/")
def index():
    return "🤖 Bot läuft!"

# ▶️ Start
if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
