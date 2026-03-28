import os
import requests
from flask import Flask, request, abort

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
GROUP_ID = int(os.getenv("GROUP_ID"))
TOPIC_ID = int(os.getenv("TOPIC_ID"))
BASE_URL = os.getenv("BASE_URL")  # z.B. https://dein-bot.onrender.com

app = Flask(__name__)

def set_webhook():
    url = f"{BASE_URL}/{TOKEN}"
    webhook_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={url}"
    r = requests.get(webhook_url)
    print("🔗 Webhook gesetzt:", r.json())


def forward_to_topic(from_chat_id, message_id):
    url = f"https://api.telegram.org/bot{TOKEN}/forwardMessage"
    data = {
        "chat_id": GROUP_ID,
        "from_chat_id": from_chat_id,
        "message_id": message_id,
        "message_thread_id": TOPIC_ID
    }

    try:
        r = requests.post(url, data=data)
        res = r.json()

        if not res.get("ok"):
            print("❌ Fehler:", res)
        else:
            print(f"✅ Weitergeleitet: {message_id}")

    except Exception as e:
        print("🔥 Exception:", e)


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        update = request.get_json()

        if "channel_post" in update:
            post = update["channel_post"]

            if post["chat"]["id"] == CHANNEL_ID:
                print("📨 Neuer Kanal-Post erkannt")

                message_id = post["message_id"]
                forward_to_topic(CHANNEL_ID, message_id)

        return "", 200

    return abort(403)


@app.route("/")
def index():
    return "🤖 Bot läuft stabil!"


if __name__ == "__main__":
    set_webhook()  # 🔥 automatisch beim Start
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
