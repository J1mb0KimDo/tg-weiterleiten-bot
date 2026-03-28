import os
import json
import threading
from pathlib import Path

import requests
from flask import Flask, request, abort

TOKEN = os.getenv("TOKEN")
BASE_URL = os.getenv("BASE_URL")

if not TOKEN:
    raise RuntimeError("TOKEN fehlt")
if not BASE_URL:
    raise RuntimeError("BASE_URL fehlt, z. B. https://dein-service.onrender.com")

app = Flask(__name__)

API_BASE = f"https://api.telegram.org/bot{TOKEN}"
DATA_FILE = Path("user_configs.json")
LOCK = threading.Lock()

# user_states:
# {
#   "<user_id>": "channel" | "group" | "topic"
# }
#
# user_configs:
# {
#   "<user_id>": {
#       "channel_id": -100...,
#       "group_id": -100...,
#       "topic_id": 3 | None
#   }
# }

user_states = {}
user_configs = {}


def load_data():
    global user_states, user_configs
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            user_states = data.get("user_states", {})
            user_configs = data.get("user_configs", {})
            print("✅ Konfiguration geladen")
        except Exception as e:
            print("❌ Fehler beim Laden:", e)
            user_states = {}
            user_configs = {}
    else:
        user_states = {}
        user_configs = {}
        print("ℹ️ Keine vorhandene Konfiguration gefunden")


def save_data():
    with LOCK:
        data = {
            "user_states": user_states,
            "user_configs": user_configs
        }
        with DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_user_config(user_id: int):
    key = str(user_id)
    if key not in user_configs:
        user_configs[key] = {
            "channel_id": None,
            "group_id": None,
            "topic_id": None
        }
        save_data()
    return user_configs[key]


def set_user_state(user_id: int, state):
    user_states[str(user_id)] = state
    save_data()


def clear_user_state(user_id: int):
    user_states[str(user_id)] = None
    save_data()


def get_user_state(user_id: int):
    return user_states.get(str(user_id))


def set_webhook():
    webhook_url = f"{BASE_URL.rstrip('/')}/{TOKEN}"
    r = requests.get(
        f"{API_BASE}/setWebhook",
        params={"url": webhook_url},
        timeout=20
    )
    print("🔗 setWebhook:", r.json())


def send_message(chat_id: int, text: str, buttons=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if buttons:
        payload["reply_markup"] = buttons

    r = requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=20)
    try:
        print("✉️ sendMessage:", r.json())
    except Exception:
        print("✉️ sendMessage: Antwort nicht lesbar")


def get_main_keyboard():
    return {
        "keyboard": [
            [{"text": "📢 Kanal setzen"}],
            [{"text": "💬 Gruppe setzen"}],
            [{"text": "🧵 Topic setzen"}],
            [{"text": "📊 Status"}]
        ],
        "resize_keyboard": True
    }


def format_status(user_id: int) -> str:
    cfg = ensure_user_config(user_id)
    topic_display = "general" if cfg["topic_id"] is None else str(cfg["topic_id"])

    return (
        "📊 Deine aktuelle Konfiguration:\n\n"
        f"Channel ID: {cfg['channel_id']}\n"
        f"Group ID: {cfg['group_id']}\n"
        f"Topic ID: {topic_display}\n\n"
        "Hinweis:\n"
        "- Topic ID = general bedeutet: Weiterleitung ohne spezielles Topic\n"
        "- Für ein bestimmtes Topic z. B.: /settopic 3\n"
        "- Für General: /settopic general"
    )


def extract_forward_chat_id(msg: dict):
    """
    Unterstützt alte und neuere Telegram-Strukturen.
    """
    # Ältere Felder
    if "forward_from_chat" in msg and isinstance(msg["forward_from_chat"], dict):
        return msg["forward_from_chat"].get("id")

    # Neuere Struktur
    forward_origin = msg.get("forward_origin")
    if isinstance(forward_origin, dict):
        if forward_origin.get("type") == "chat":
            chat = forward_origin.get("chat", {})
            return chat.get("id")

    return None


def forward_to_target(channel_id: int, group_id: int, topic_id, message_id: int):
    payload = {
        "chat_id": group_id,
        "from_chat_id": channel_id,
        "message_id": message_id
    }

    # Für "general" senden wir bewusst OHNE message_thread_id
    if topic_id is not None:
        payload["message_thread_id"] = topic_id

    r = requests.post(f"{API_BASE}/forwardMessage", data=payload, timeout=30)
    try:
        result = r.json()
    except Exception:
        result = {"ok": False, "description": "Antwort nicht lesbar"}

    print("➡️ forwardMessage:", result)
    return result


def handle_start(chat_id: int):
    send_message(
        chat_id,
        (
            "Willkommen.\n\n"
            "So funktioniert das Setup:\n"
            "1. '📢 Kanal setzen' drücken und dann eine Nachricht aus dem Kanal an den Bot weiterleiten\n"
            "2. '💬 Gruppe setzen' drücken und dann eine Nachricht aus der Gruppe an den Bot weiterleiten\n"
            "3. Topic manuell setzen mit /settopic 3 oder /settopic general\n"
            "4. Mit '📊 Status' IDs prüfen"
        ),
        buttons=get_main_keyboard()
    )


def handle_settopic_command(chat_id: int, user_id: int, text: str):
    cfg = ensure_user_config(user_id)
    parts = text.strip().split(maxsplit=1)

    if len(parts) < 2:
        send_message(
            chat_id,
            "Bitte nutze:\n"
            "/settopic 3\n"
            "oder\n"
            "/settopic general"
        )
        return

    value = parts[1].strip().lower()

    if value == "general":
        cfg["topic_id"] = None
        save_data()
        send_message(
            chat_id,
            "✅ Topic gesetzt:\nTopic ID: general"
        )
        return

    try:
        topic_id = int(value)
        if topic_id <= 0:
            raise ValueError
    except ValueError:
        send_message(
            chat_id,
            "❌ Ungültige Topic-ID.\n"
            "Beispiel: /settopic 3\n"
            "Oder: /settopic general"
        )
        return

    cfg["topic_id"] = topic_id
    save_data()
    send_message(
        chat_id,
        f"✅ Topic gesetzt:\nTopic ID: {topic_id}"
    )


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        return abort(403)

    update = request.get_json(silent=True)
    if not update:
        return "", 200

    print("📨 Update:", update)

    # Private User-Interaktion
    if "message" in update:
        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        chat_type = chat.get("type")
        user = msg.get("from", {})
        user_id = user.get("id")
        text = msg.get("text", "")

        if not chat_id or not user_id:
            return "", 200

        # Setup nur im Privatchat steuern
        if chat_type != "private":
            return "", 200

        ensure_user_config(user_id)

        if text == "/start":
            handle_start(chat_id)
            return "", 200

        if text == "📊 Status":
            send_message(chat_id, format_status(user_id), buttons=get_main_keyboard())
            return "", 200

        if text == "📢 Kanal setzen":
            set_user_state(user_id, "channel")
            send_message(
                chat_id,
                "➡️ Bitte leite jetzt eine Nachricht aus deinem Kanal an mich weiter.\n\n"
                "Danach antworte ich dir wieder mit der erkannten Channel ID.",
                buttons=get_main_keyboard()
            )
            return "", 200

        if text == "💬 Gruppe setzen":
            set_user_state(user_id, "group")
            send_message(
                chat_id,
                "➡️ Bitte leite jetzt eine Nachricht aus deiner Gruppe an mich weiter.\n\n"
                "Danach antworte ich dir wieder mit der erkannten Group ID.",
                buttons=get_main_keyboard()
            )
            return "", 200

        if text == "🧵 Topic setzen":
            set_user_state(user_id, "topic")
            send_message(
                chat_id,
                "➡️ Setze das Topic manuell.\n\n"
                "Beispiele:\n"
                "/settopic 3\n"
                "/settopic general\n\n"
                "Ich antworte dir danach wieder mit der gesetzten Topic ID.",
                buttons=get_main_keyboard()
            )
            return "", 200

        if text.startswith("/settopic"):
            handle_settopic_command(chat_id, user_id, text)
            clear_user_state(user_id)
            return "", 200

        state = get_user_state(user_id)
        forward_chat_id = extract_forward_chat_id(msg)

        if state == "channel":
            if forward_chat_id is None:
                send_message(
                    chat_id,
                    "❌ Ich konnte keine Channel ID erkennen.\n"
                    "Bitte leite wirklich eine Nachricht aus dem Kanal weiter."
                )
                return "", 200

            cfg = ensure_user_config(user_id)
            cfg["channel_id"] = forward_chat_id
            save_data()
            clear_user_state(user_id)

            send_message(
                chat_id,
                f"✅ Kanal erkannt und gespeichert.\nChannel ID: {forward_chat_id}",
                buttons=get_main_keyboard()
            )
            return "", 200

        if state == "group":
            if forward_chat_id is None:
                send_message(
                    chat_id,
                    "❌ Ich konnte keine Group ID erkennen.\n"
                    "Bitte leite wirklich eine Nachricht aus der Gruppe weiter."
                )
                return "", 200

            cfg = ensure_user_config(user_id)
            cfg["group_id"] = forward_chat_id
            save_data()
            clear_user_state(user_id)

            send_message(
                chat_id,
                f"✅ Gruppe erkannt und gespeichert.\nGroup ID: {forward_chat_id}",
                buttons=get_main_keyboard()
            )
            return "", 200

        if state == "topic":
            send_message(
                chat_id,
                "➡️ Bitte setze das Topic mit:\n"
                "/settopic 3\n"
                "oder\n"
                "/settopic general"
            )
            return "", 200

    # Kanalbeiträge weiterleiten
    if "channel_post" in update:
        post = update["channel_post"]
        post_chat = post.get("chat", {})
        post_channel_id = post_chat.get("id")
        message_id = post.get("message_id")

        if not post_channel_id or not message_id:
            return "", 200

        # Für alle User-Konfigurationen prüfen
        for user_id_str, cfg in user_configs.items():
            channel_id = cfg.get("channel_id")
            group_id = cfg.get("group_id")
            topic_id = cfg.get("topic_id")

            if channel_id == post_channel_id and group_id:
                result = forward_to_target(
                    channel_id=channel_id,
                    group_id=group_id,
                    topic_id=topic_id,
                    message_id=message_id
                )

                print(
                    f"🎯 Weiterleitung für User {user_id_str}: "
                    f"channel_id={channel_id}, group_id={group_id}, topic_id={topic_id}, result={result}"
                )

    return "", 200


@app.route("/", methods=["GET"])
def index():
    return "Bot läuft ✅"


if __name__ == "__main__":
    load_data()
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
