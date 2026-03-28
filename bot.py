import os
import requests
from flask import Flask, request, abort

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
GROUP_ID = int(os.getenv("GROUP_ID"))
TOPIC_ID = int(os.getenv("TOPIC_ID"))

app = Flask(__name__)

def forward_to_topic(from_chat_id, message_id):
    url = f"https://api.telegram.org/bot{TOKEN}/forwardMessage"
    data = {
        "chat_id": GROUP_ID,
        "from_chat_id": from_chat_id,
        "message_id": message_id,
        "message_thread_id": TOPIC_ID
    }

    try:
        response = requests.post(url, data=data)
        result = response.json()

        if not result.get("ok"):
            print("❌ Fehler:", result)
        else:
            print("✅ Weitergeleitet:", message_id)

    except Exception as e:
        print("🔥 Exception:", e)


@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = request.get_json()

        if 'channel_post' in update:
            post = update['channel_post']

            if post['chat']['id'] == CHANNEL_ID:
                message_id = post['message_id']
                print("📨 Neuer Kanal-Post:", message_id)

                forward_to_topic(CHANNEL_ID, message_id)

        return '', 200

    return abort(403)


@app.route('/')
def index():
    return "Bot läuft ✅"


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
