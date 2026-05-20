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
COOKIES_FILE = "cookies_www.youtube.com.txt"

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
    keyboard = [
        [InlineKeyboardButton("❤️ Support the bot", callback_data="donate")],
        [InlineKeyboardButton("📖 How to use", callback_data="help"),
         InlineKeyboardButton("📊 My stats", callback_data="mystats")]
    ]
    await update.message.reply_text(
        "🎵 *YouTube Audio Downloader*\n\n"
        "100% FREE — No limits, no registration!\n\n"
        "Just paste any YouTube link and get the MP3 instantly!\n\n"
        "✅ YouTube videos\n"
        "✅ YouTube Music\n"
        "✅ YouTube Shorts\n\n"
        "*/help* — How to use\n"
        "*/donate* — Support the bot ❤️",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *How to Use*\n\n"
        "1️⃣ Copy any YouTube link\n"
        "2️⃣ Paste it here\n"
        "3️⃣ Get MP3 instantly — FREE!\n\n"
        "💡 *Works with:*\n"
        "- YouTube videos\n"
        "- YouTube Music\n"
        "- YouTube Shorts\n\n"
        "This bot is completely free!\n"
        "If you find it useful, /donate to keep it running ❤️"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")

async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⭐ 50 Stars", callback_data="stars_50"),
         InlineKeyboardButton("⭐ 100 Stars", callback_data="stars_100")],
        [InlineKeyboardButton("⭐ 250 Stars", callback_data="stars_250"),
         InlineKeyboardButton("⭐ 500 Stars", callback_data="stars_500")],
    ]
    text = (
        "❤️ *Support the Bot*\n\n"
        "This bot is free for everyone!\n"
        "Donations help pay for servers and keep it running.\n\n"
        "Choose an amount to donate via Telegram Stars:\n\n"
        "Every donation helps! Thank you 🙏"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    downloads = user.get("downloads", 0)
    text = (
        f"📊 *Your Stats*\n\n"
        f"Total downloads: {downloads}\n\n"
        f"Keep enjoying free music! 🎵"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "donate":
        await donate(update, context)
    elif query.data == "help":
        await help_command(update, context)
    elif query.data == "mystats":
        await mystats_command(update, context)
    elif query.data.startswith("stars_"):
        amount = query.data.split("_")[1]
        await query.message.reply_text(
            f"⭐ *Thank you for donating {amount} Stars!*\n\n"
            f"Please send *{amount} Stars* directly to this bot via Telegram.\n\n"
            f"Your support keeps this bot alive! 🙏",
            parse_mode="Markdown"
        )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.OWNER_ID:
        return
    users = load_users()
    total = len(users)
    total_downloads = sum(u.get("downloads", 0) for u in users.values())
    await update.message.reply_text(
        f"📊 *Bot Statistics*\n\n"
        f"Total users: {total}\n"
        f"Total downloads: {total_downloads}",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text.strip()

    if not url.startswith(('http://', 'https://')):
        return

    if "youtu" not in url:
        await update.message.reply_text(
            "❌ Please send a YouTube link!\n\n"
            "Example: https://youtube.com/watch?v=..."
        )
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
            'cookiefile': COOKIES_FILE,
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

        with open(audio_file, 'rb') as f:
            await update.message.reply_audio(
                f,
                title=title,
                caption=f"🎵 {title}\n\n❤️ This bot is free! Support it with /donate",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        os.remove(audio_file)
        increment_download(user_id)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(
            f"❌ *Download failed*\n\n"
            f"Possible reasons:\n"
            f"- Video is age restricted\n"
            f"- Video is private\n"
            f"- Video is too long\n\n"
            f"Contact {config.SUPPORT_CONTACT}",
            parse_mode="Markdown"
        )
        print(f"Error: {e}")

def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("donate", donate))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("mystats", mystats_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("=" * 40)
    print("BOT IS RUNNING!")
    print("=" * 40)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
