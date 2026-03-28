import os
import requests
from flask import Flask, request, abort

TOKEN = os.getenv("TOKEN")
BASE_URL = os.getenv("BASE_URL")

app = Flask(__name__)

# Speicher
USER_STATE = {}
CONFIG = {
    "channel_id": None,
    "group_id": None,
    "topic_id": None
}

# Webhook setzen
def set_webhook():
    if BASE_URL:
        url = f"{BASE_URL}/{TOKEN}"
        requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={url}")

# Nachricht senden
def send_message(chat_id, text, buttons=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}

    if buttons:
        data["reply_markup"] = buttons

    requests.post(url, json=data)

# Weiterleiten
def forward_to_topic(message_id):
    if not all(CONFIG.values()):
        print("⚠️ Setup unvollständig:", CONFIG)
        return

    url = f"https://api.telegram.org/bot{TOKEN}/forwardMessage"
    data = {
        "chat_id": CONFIG["group_id"],
        "from_chat_id": CONFIG["channel_id"],
        "message_id": message_id,
        "message_thread_id": CONFIG["topic_id"]
    }

    r = requests.post(url, data=data)
    print("➡️ Forward:", r.json())

# Webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        return abort(403)

    update = request.get_json()
    print("📨", update)

    # 👤 PRIVATCHAT STEUERUNG
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        # START
        if text == "/start":
            buttons = {
                "keyboard": [
                    ["📢 Kanal setzen"],
                    ["💬 Gruppe setzen"],
                    ["🧵 Topic setzen"]
                ],
                "resize_keyboard": True
            }
            send_message(chat_id, "Setup starten:", buttons)

        elif text == "📢 Kanal setzen":
            USER_STATE[chat_id] = "channel"
            send_message(chat_id, "➡️ Bitte leite eine Nachricht aus deinem KANAL weiter")

        elif text == "💬 Gruppe setzen":
            USER_STATE[chat_id] = "group"
            send_message(chat_id, "➡️ Bitte leite eine Nachricht aus deiner GRUPPE weiter")

        elif text == "🧵 Topic setzen":
            USER_STATE[chat_id] = "topic"
            send_message(chat_id, "➡️ Bitte sende eine Nachricht DIREKT im gewünschten Topic")

        # 📢 Kanal erkennen
        elif "forward_from_chat" in msg and USER_STATE.get(chat_id) == "channel":
            CONFIG["channel_id"] = msg["forward_from_chat"]["id"]
            send_message(chat_id, f"✅ Kanal gesetzt:\n{CONFIG['channel_id']}")
            USER_STATE[chat_id] = None

        # 💬 Gruppe erkennen
        elif "forward_from_chat" in msg and USER_STATE.get(chat_id) == "group":
            CONFIG["group_id"] = msg["forward_from_chat"]["id"]
            send_message(chat_id, f"✅ Gruppe gesetzt:\n{CONFIG['group_id']}")
            USER_STATE[chat_id] = None

        # 🧵 Topic erkennen
        elif USER_STATE.get(chat_id) == "topic":
            if "message_thread_id" in msg:
                CONFIG["topic_id"] = msg["message_thread_id"]
                send_message(chat_id, f"✅ Topic gesetzt:\n{CONFIG['topic_id']}")
                USER_STATE[chat_id] = None
            else:
                send_message(chat_id, "❌ Bitte wirklich IM Topic schreiben!")

    # 📢 CHANNEL POSTS
    if "channel_post" in update:
        post = update["channel_post"]

        if post["chat"]["id"] == CONFIG["channel_id"]:
            print("🎯 Kanalpost erkannt")
            forward_to_topic(post["message_id"])

    return "", 200

@app.route("/")
def index():
    return "Bot läuft ✅"

if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
