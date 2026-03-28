import os
import requests
from flask import Flask, request, abort

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
GROUP_ID = int(os.getenv("GROUP_ID"))
TOPIC_ID = int(os.getenv("TOPIC_ID"))

app = Flask(__name__)

def copy_to_topic(from_chat_id, message_id):
    url = f"https://api.telegram.org/bot{TOKEN}/copyMessage"
    data = {
        "chat_id": GROUP_ID,
        "from_chat_id": from_chat_id,
        "message_id": message_id,
        "message_thread_id": TOPIC_ID
    }
    response = requests.post(url, data=data)
    print("✅ Kopiert:", response.json())
    return response.json()

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = request.get_json()
        print("📨 Update:", update)
        
        if 'channel_post' in update:
            post = update['channel_post']
            if post['chat']['id'] == CHANNEL_ID:
                print("🎯 Kanal-Post erkannt!")
                copy_to_topic(CHANNEL_ID, post['message_id'])
        
        return '', 200
    abort(403)

@app.route('/')
def index():
    return "🚀 Telegram Copy Bot läuft! Webhook ready."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
