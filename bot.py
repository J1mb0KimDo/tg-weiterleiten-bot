import os
import requests
from flask import Flask, request, abort

TOKEN = os.getenv("TOKEN")
BASE_URL = os.getenv("BASE_URL")

app = Flask(__name__)

# 🧠 Speicher pro User
user_states = {}
user_configs = {}

# 🔗 Webhook setzen
def set_webhook():
    if BASE_URL:
        url = f"{BASE_URL}/{TOKEN}"
        requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={url}")

# 📤 Nachricht senden
def send_message(chat_id, text, buttons=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if buttons:
        data["reply_markup"] = buttons

    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json=data)

# 🔁 Forward Funktion
def forward_message(config, message_id):
    if not all([config.get("channel_id"), config.get("group_id")]):
        print("❌ Config unvollständig:", config)
        return

    data = {
        "chat_id": config["group_id"],
        "from_chat_id": config["channel_id"],
        "message_id": message_id
    }

    if config.get("topic_id"):
        data["message_thread_id"] = config["topic_id"]

    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/forwardMessage",
        data=data
    )

    print("➡️ Forward:", r.json())

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        return abort(403)

    update = request.get_json()
    print("📨", update)

    # 👤 USER INTERACTION (Privatchat)
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        # init config
        if chat_id not in user_configs:
            user_configs[chat_id] = {}

        # START
        if text == "/start":
            buttons = {
                "keyboard": [
                    ["📢 Kanal setzen"],
                    ["💬 Gruppe setzen"],
                    ["🧵 Topic setzen"],
                    ["📊 Status"]
                ],
                "resize_keyboard": True
            }
            send_message(chat_id, "⚙️ Setup starten:", buttons)

        elif text == "📢 Kanal setzen":
            user_states[chat_id] = "channel"
            send_message(chat_id, "➡️ Leite eine Nachricht aus deinem KANAL weiter")

        elif text == "💬 Gruppe setzen":
            user_states[chat_id] = "group"
            send_message(chat_id, "➡️ Leite eine Nachricht aus deiner GRUPPE weiter")

        elif text == "🧵 Topic setzen":
            user_states[chat_id] = "topic"
            send_message(chat_id, "➡️ Schreibe eine Nachricht IM gewünschten Topic")

        elif text == "📊 Status":
            cfg = user_configs.get(chat_id, {})
            send_message(chat_id, f"📊 Deine Config:\n{cfg}")

        # 📢 Kanal speichern
        elif "forward_from_chat" in msg and user_states.get(chat_id) == "channel":
            user_configs[chat_id]["channel_id"] = msg["forward_from_chat"]["id"]
            send_message(chat_id, f"✅ Kanal gespeichert")
            user_states[chat_id] = None

        # 💬 Gruppe speichern
        elif "forward_from_chat" in msg and user_states.get(chat_id) == "group":
            user_configs[chat_id]["group_id"] = msg["forward_from_chat"]["id"]
            send_message(chat_id, f"✅ Gruppe gespeichert")
            user_states[chat_id] = None

        # 🧵 Topic speichern
        elif user_states.get(chat_id) == "topic":
            if "message_thread_id" in msg:
                user_configs[chat_id]["topic_id"] = msg["message_thread_id"]
                user_configs[chat_id]["group_id"] = msg["chat"]["id"]

                send_message(chat_id, f"✅ Topic gespeichert (ID: {msg['message_thread_id']})")
                user_states[chat_id] = None
            else:
                send_message(chat_id, "❌ Bitte IM Topic schreiben!")

    # 📢 CHANNEL POSTS
    if "channel_post" in update:
        post = update["channel_post"]
        channel_id = post["chat"]["id"]

        for user_id, config in user_configs.items():
            if config.get("channel_id") == channel_id:
                print(f"🎯 Weiterleitung für User {user_id}")
                forward_message(config, post["message_id"])

    return "", 200

@app.route("/")
def index():
    return "Bot läuft ✅"

if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
