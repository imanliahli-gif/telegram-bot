import logging
import aiohttp
from datetime import date
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
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
    return users.get(str(user_id), {"downloads_today": 0, "last_date": None, "unlimited": False})

def update_user(user_id, downloads_today, last_date, unlimited=False):
    users = load_users()
    users[str(user_id)] = {"downloads_today": downloads_today, "last_date": last_date, "unlimited": unlimited}
    save_users(users)

def can_download(user_id):
    user = get_user(user_id)
    today = date.today().isoformat()
    if user.get("unlimited"):
        return True, -1
    if user.get("last_date") != today:
        return True, config.DAILY_LIMIT_FREE
    used = user.get("downloads_today", 0)
    remaining = config.DAILY_LIMIT_FREE - used
    return remaining > 0, remaining

def increment_download(user_id):
    user = get_user(user_id)
    today = date.today().isoformat()
    if user.get("unlimited"):
        return
    if user.get("last_date") != today:
        update_user(user_id, 1, today)
    else:
        update_user(user_id, user.get("downloads_today", 0) + 1, today)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    today = date.today().isoformat()
    remaining = config.DAILY_LIMIT_FREE if user.get("last_date") != today else config.DAILY_LIMIT_FREE - user.get("downloads_today", 0)
    status = "UNLIMITED" if user.get("unlimited") else f"Free ({remaining}/{config.DAILY_LIMIT_FREE} today)"
    await update.message.reply_text(f"""Video Downloader Bot

Status: {status}

Supported Platforms:
- YouTube
- TikTok
- Instagram
- Twitter/X
- Facebook
- Reddit

Free Tier:
- {config.DAILY_LIMIT_FREE} videos per day
- Just paste any link!

/unlimited - Remove limits
/help - How to use""")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""How to Use:

1. Copy any video link
2. Paste it here
3. I send the video back!

/unlimited - Remove daily limits""")

async def unlimited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if get_user(user_id).get("unlimited"):
        await update.message.reply_text("You already have Unlimited Access!")
        return
    await update.message.reply_text(f"Upgrade to Unlimited\n\nPrice: {config.UNLIMITED_PRICE_STARS} Telegram Stars\n\nSend /buy to upgrade!\n\nContact {config.SUPPORT_CONTACT}")

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Send {config.UNLIMITED_PRICE_STARS} Stars to this bot\nThen type: /confirm YOUR_TX_ID\n\nContact {config.SUPPORT_CONTACT} for help")

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if get_user(user_id).get("unlimited"):
        await update.message.reply_text("You already have Unlimited Access!")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /confirm YOUR_TX_ID")
        return
    update_user(user_id, 0, date.today().isoformat(), unlimited=True)
    await update.message.reply_text("UPGRADED TO UNLIMITED! No more daily limits!")
    await context.bot.send_message(chat_id=config.OWNER_ID, text=f"NEW PAYMENT!\nUser: {user_id}\nTX: {args[0]}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if user.get("unlimited"):
        await update.message.reply_text("Status: Unlimited!")
        return
    today = date.today().isoformat()
    remaining = config.DAILY_LIMIT_FREE if user.get("last_date") != today else config.DAILY_LIMIT_FREE - user.get("downloads_today", 0)
    await update.message.reply_text(f"Free Tier\nRemaining: {remaining}/{config.DAILY_LIMIT_FREE}\n\n/unlimited to remove limits")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.OWNER_ID:
        return
    users = load_users()
    unlimited_users = sum(1 for u in users.values() if u.get("unlimited"))
    await update.message.reply_text(f"Total users: {len(users)}\nUnlimited: {unlimited_users}\nEarnings: ${unlimited_users * 5}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text.strip()

    if not url.startswith(('http://', 'https://')):
        return

    allowed, remaining = can_download(user_id)
    if not allowed:
        await update.message.reply_text(f"Daily limit reached!\n\n/unlimited - Remove limits for {config.UNLIMITED_PRICE_STARS} Stars")
        return

    platform = "video"
    if "youtu" in url:
        platform = "YouTube"
    elif "tiktok" in url:
        platform = "TikTok"
    elif "instagram" in url:
        platform = "Instagram"
    elif "twitter" in url or "x.com" in url:
        platform = "Twitter"
    elif "facebook" in url:
        platform = "Facebook"
    elif "reddit" in url:
        platform = "Reddit"

    status_msg = await update.message.reply_text(f"Downloading from {platform}... please wait.")

    try:
        video_url = None
        title = "video"

        async with aiohttp.ClientSession() as session:
            # Try tikwm API (works for TikTok, Instagram, Twitter)
            if platform in ["TikTok", "Instagram", "Twitter"]:
                async with session.get(f"https://tikwm.com/api/?url={url}") as resp:
                    data = await resp.json()
                if data.get("code") == 0:
                    video_url = data["data"].get("play") or data["data"].get("wmplay")
                    title = data["data"].get("title", "video")[:50]

            # Try yt-dlp API proxy for YouTube
            if not video_url and platform == "YouTube":
                async with session.get(
                    f"https://api.vevioz.com/api/button/mp4/{url.split('v=')[-1].split('&')[0] if 'v=' in url else url.split('/')[-1]}"
                ) as resp:
                    pass

            # Fallback: try y2mate API
            if not video_url:
                async with session.post(
                    "https://www.y2mate.com/mates/analyzeV2/ajax",
                    data={"k_query": url, "k_page": "home", "hl": "en", "q_auto": 0}
                ) as resp:
                    data = await resp.json()
                    if data.get("status") == "Ok":
                        links = data.get("links", {}).get("mp4", {})
                        for key, val in links.items():
                            if val.get("f") == "mp4":
                                video_url = val.get("url")
                                title = data.get("title", "video")[:50]
                                break

        if video_url:
            await update.message.reply_video(
                video_url,
                caption=f"Downloaded: {title}\nFrom: {platform}\n\n/unlimited - Remove limits",
                supports_streaming=True
            )
            increment_download(user_id)
            await status_msg.delete()
            if not get_user(user_id).get("unlimited"):
                _, rem = can_download(user_id)
                if rem > 0:
                    await update.message.reply_text(f"{rem}/{config.DAILY_LIMIT_FREE} downloads remaining today.")
        else:
            raise Exception("No video URL found")

    except Exception as e:
        await status_msg.edit_text(f"Download failed from {platform}.\n\nTry a different link or contact {config.SUPPORT_CONTACT}")
        print(f"Error: {e}")

def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("unlimited", unlimited))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("BOT IS RUNNING!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
