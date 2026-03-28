import os
import json
from flask import Flask, request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

TOKEN = os.getenv("TOKEN")
app = Flask(__name__)

# User‑Datenbank (in Memory, später DB)
users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 Kanäle auswählen", callback_data="select_source")],
        [InlineKeyboardButton("👥 Gruppen auswählen", callback_data="select_target")],
        [InlineKeyboardButton("⚙️ Konfiguration anzeigen", callback_data="show_config")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🤖 **Forward Bot Setup**\n\n"
        "Wähle Quelle und Ziel für Nachrichten‑Weiterleitung:", 
        reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "select_source":
        keyboard = [
            [InlineKeyboardButton("ID eingeben", callback_data="source_manual")],
            [InlineKeyboardButton("Eigene Kanäle", callback_data="source_list")],
            [InlineKeyboardButton("🔙 Zurück", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📱 **Quell‑Kanal wählen:**", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "source_manual":
        await query.edit_message_text(
            "📝 **Kanal‑ID eingeben:**\n\n"
            "Nachricht an @userinfobot forwarden oder:\n"
            "`/set_source -1001234567890`\n\n"
            "Beispiel: `/set_source -1003815675351`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("set_source_"):
        channel_id = data.replace("set_source_", "")
        users[user_id] = users.get(user_id, {})
        users[user_id]['source'] = channel_id
        await query.edit_message_text(f"✅ **Quell‑Kanal:** `{channel_id}`\n\nNächster Schritt?", parse_mode=ParseMode.MARKDOWN)
    
    # Target ähnlich...
    
    elif data == "show_config":
        config = users.get(user_id, {})
        text = "⚙️ **Aktuelle Konfiguration:**\n\n"
        text += f"📱 Quelle: `{config.get('source', '❌ Nicht gesetzt')}`\n"
        text += f"👥 Ziel: `{config.get('target', '❌ Nicht gesetzt')}`\n\n"
        text += "Button zum Ändern:"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Konfig ändern", callback_data="main_menu")],
            [InlineKeyboardButton("▶️ Start Weiterleitung", callback_data="start_forward")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Webhook
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()
