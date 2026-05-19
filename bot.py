import logging
import os
import glob
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import config
import json

logging.basicConfig(level=logging.INFO)
USER_DATA_FILE = "users.json"

def load_users():
    try:
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def get_user(user_id):
    users = load_users()
    return users.get(str(user_id), {"downloads": 0})

def increment_download(user_id):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"downloads": 0}
    users[uid]["downloads"] = users[uid].get("downloads", 0) + 1
    save_users(users)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("❤️ Support the bot", callback_data="donate")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("""🎵 YouTube Audio Downloader Bot

100% FREE — No limits, no registration!

Just paste any YouTube link and get the MP3 instantly!

Supported:
- YouTube videos
- YouTube Music
- YouTube Shorts

/help - How to use
/donate - Support the bot ❤️""", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""How to Use:

1. Copy any YouTube link
2. Paste it here
3. Get MP3 instantly — FREE!

This bot is completely free.
If you find it useful, /donate to keep it running! ❤️""")

async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⭐ Send 50 Stars", callback_data="stars_50")],
        [InlineKeyboardButton("⭐ Send 100 Stars", callback_data="stars_100")],
        [InlineKeyboardButton("⭐ Send 250 Stars", callback_data="stars_250")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("""❤️ Support the Bot

This bot is free for everyone!
If you find it useful, please consider donating Telegram Stars to keep the servers running.

Every donation helps! Thank you 🙏""", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "donate":
        await donate(update, context)
    elif query.data.startswith("stars_"):
        amount = query.data.split("_")[1]
        await query.message.reply_text(f"Thank you for wanting to donate {amount} Stars! ⭐\n\nPlease send {amount} Stars directly to this bot via Telegram.\n\nThank you for supporting the bot! ❤️")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.OWNER_ID:
        return
    users = load_users()
    total = len(users)
    total_downloads = sum(u.get("downloads", 0) for u in users.values())
    await update.message.reply_text(f"📊 Bot Statistics\n\nTotal users: {total}\nTotal downloads: {total_downloads}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text.strip()

    if not url.startswith(('http://', 'https://')):
        return

    if "youtu" not in url:
        await update.message.reply_text("Please send a YouTube link!\n\nExample: https://youtube.com/watch?v=...")
        return

    status_msg = await update.message.reply_text("⏳ Downloading... please wait (30-60 seconds)")

    try:
        import yt_dlp

        output_path = f"/tmp/{user_id}_%(id)s.%(ext)s"

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'audio')[:50]

        files = glob.glob(f"/tmp/{user_id}_*.mp3")
        if not files:
            raise Exception("File not found")

        audio_file = files[0]

        keyboard = [[InlineKeyboardButton("❤️ Support the bot", callback_data="donate")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        with open(audio_file, 'rb') as f:
            await update.message.reply_audio(
                f,
                title=title,
                caption=f"🎵 {title}\n\n❤️ This bot is free! Support it with /donate",
                reply_markup=reply_markup
            )

        os.remove(audio_file)
        increment_download(user_id)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(
            f"❌ Download failed.\n\nPossible reasons:\n- Video is age restricted\n- Video is private\n- Video is too long\n\nContact {config.SUPPORT_CONTACT}"
        )
        print(f"Error: {e}")

def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("donate", donate))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("BOT IS RUNNING!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
