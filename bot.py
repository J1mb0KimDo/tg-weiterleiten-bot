import os
import requests
import time

# 🔑 HIER DEIN BOT TOKEN EINTRAGEN
TOKEN = os.getenv("TOKEN")

# 📢 DEIN KANAL
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# 💬 DEINE GRUPPE
GROUP_ID = int(os.getenv("GROUP_ID"))

# 🧵 DEIN TOPIC ("Events")
TOPIC_ID = int(os.getenv("TOPIC_ID"))


def forward_to_topic(from_chat_id, message_id):
    url = f"https://api.telegram.org/bot{TOKEN}/forwardMessage"
    data = {
        "chat_id": GROUP_ID,
        "from_chat_id": from_chat_id,
        "message_id": message_id,
        "message_thread_id": TOPIC_ID
    }

    response = requests.post(url, data=data)
    print("Weitergeleitet:", response.json())


def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {
        "timeout": 30,
        "offset": offset
    }
    return requests.get(url, params=params).json()


def main():
    print("🤖 Bot läuft... wartet auf neue Kanal-Posts")
    offset = None

    while True:
        updates = get_updates(offset)

        for update in updates.get("result", []):
            offset = update["update_id"] + 1

            if "channel_post" in update:
                post = update["channel_post"]

                # Nur dein Kanal
                if post["chat"]["id"] == CHANNEL_ID:
                    message_id = post["message_id"]

                    print("📨 Neuer Kanal-Post erkannt → leite weiter")
                    forward_to_topic(CHANNEL_ID, message_id)

        time.sleep(1)


if __name__ == "__main__":
    main()
