import os
import requests
from flask import Flask, request, abort

TOKEN = os.getenv("TOKEN")
BASE_URL = os.getenv("BASE_URL")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROUP_ID = os.getenv("GROUP_ID")
TOPIC_ID_RAW = os.getenv("TOPIC_ID", "general").strip().lower()

if not TOKEN:
    raise RuntimeError("TOKEN fehlt")
if not BASE_URL:
    raise RuntimeError("BASE_URL fehlt, z. B. https://dein-service.onrender.com")
if not CHANNEL_ID:
    raise RuntimeError("CHANNEL_ID fehlt")
if not GROUP_ID:
    raise RuntimeError("GROUP_ID fehlt")

try:
    CHANNEL_ID = int(CHANNEL_ID)
except ValueError:
    raise RuntimeError("CHANNEL_ID muss eine Zahl sein, z. B. -1001234567890")

try:
    GROUP_ID = int(GROUP_ID)
except ValueError:
    raise RuntimeError("GROUP_ID muss eine Zahl sein, z. B. -1001234567890")

if TOPIC_ID_RAW == "general":
    TOPIC_ID = None
else:
    try:
        TOPIC_ID = int(TOPIC_ID_RAW)
        if TOPIC_ID <= 0:
            raise ValueError
    except ValueError:
        raise RuntimeError("TOPIC_ID muss 'general' oder eine positive Zahl sein, z. B. 3")

app = Flask(__name__)
API_BASE = f"https://api.telegram.org/bot{TOKEN}"


def set_webhook():
    webhook_url = f"{BASE_URL.rstrip('/')}/{TOKEN}"
    r = requests.get(
        f"{API_BASE}/setWebhook",
        params={"url": webhook_url},
        timeout=20
    )
    try:
        print("🔗 setWebhook:", r.json())
    except Exception:
        print("🔗 setWebhook: Antwort nicht lesbar")


def send_message(chat_id: int, text: str):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    r = requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=20)
    try:
        print("✉️ sendMessage:", r.json())
    except Exception:
        print("✉️ sendMessage: Antwort nicht lesbar")


def format_status() -> str:
    topic_display = "general" if TOPIC_ID is None else str(TOPIC_ID)
    return (
        "📊 Aktuelle Konfiguration:\n\n"
        f"Channel ID: {CHANNEL_ID}\n"
        f"Group ID: {GROUP_ID}\n"
        f"Topic ID: {topic_display}\n"
    )


def forward_to_target(message_id: int):
    payload = {
        "chat_id": GROUP_ID,
        "from_chat_id": CHANNEL_ID,
        "message_id": message_id
    }

    # Für general bewusst ohne message_thread_id
    if TOPIC_ID is not None:
        payload["message_thread_id"] = TOPIC_ID

    r = requests.post(f"{API_BASE}/forwardMessage", data=payload, timeout=30)
    try:
        result = r.json()
    except Exception:
        result = {"ok": False, "description": "Antwort nicht lesbar"}

    print("➡️ forwardMessage:", result)
    return result


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        return abort(403)

    update = request.get_json(silent=True)
    if not update:
        return "", 200

    print("📨 Update:", update)

    # Optional: Status im Privatchat abrufbar
    if "message" in update:
        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        chat_type = chat.get("type")
        text = msg.get("text", "")

        if chat_id and chat_type == "private":
            if text == "/start":
                send_message(
                    chat_id,
                    "Willkommen.\n\n"
                    "Dieser Bot ist fest konfiguriert.\n\n"
                    f"{format_status()}"
                )
                return "", 200

            if text == "📊 Status" or text == "/status":
                send_message(chat_id, format_status())
                return "", 200

    # Kanalbeiträge weiterleiten
    if "channel_post" in update:
        post = update["channel_post"]
        post_chat = post.get("chat", {})
        post_channel_id = post_chat.get("id")
        message_id = post.get("message_id")

        if not post_channel_id or not message_id:
            return "", 200

        if post_channel_id == CHANNEL_ID:
            result = forward_to_target(message_id)
            print(
                f"🎯 Weiterleitung ausgeführt: "
                f"channel_id={CHANNEL_ID}, group_id={GROUP_ID}, topic_id={TOPIC_ID}, result={result}"
            )

    return "", 200


@app.route("/", methods=["GET"])
def index():
    return "Bot läuft ✅"


if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
