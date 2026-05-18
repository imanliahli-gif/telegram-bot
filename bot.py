import logging
import re
from datetime import datetime, date
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import config
import json
import os

# Setup
logging.basicConfig(level=logging.INFO)

# File to store user data
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
    user_id_str = str(user_id)
    return users.get(user_id_str, {"downloads_today": 0, "last_date": None, "unlimited": False})

def update_user(user_id, downloads_today, last_date, unlimited=False):
    users = load_users()
    user_id_str = str(user_id)
    users[user_id_str] = {
        "downloads_today": downloads_today,
        "last_date": last_date,
        "unlimited": unlimited
    }
    save_users(users)

def can_download(user_id):
    user = get_user(user_id)
    today = date.today().isoformat()
    
    if user.get("unlimited", False):
        return True, -1
    
    if user.get("last_date") != today:
        return True, config.DAILY_LIMIT_FREE
    
    used = user.get("downloads_today", 0)
    remaining = config.DAILY_LIMIT_FREE - used
    return remaining > 0, remaining

def increment_download(user_id):
    user = get_user(user_id)
    today = date.today().isoformat()
    
    if user.get("unlimited", False):
        return
    
    if user.get("last_date") != today:
        update_user(user_id, 1, today)
    else:
        update_user(user_id, user.get("downloads_today", 0) + 1, today)

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    remaining = config.DAILY_LIMIT_FREE - user.get("downloads_today", 0)
    
    if user.get("last_date") != date.today().isoformat():
        remaining = config.DAILY_LIMIT_FREE
    
    status = "UNLIMITED" if user.get("unlimited") else f"Free ({remaining}/{config.DAILY_LIMIT_FREE} today)"
    
    message = f"""
Video Downloader Bot

Status: {status}

Supported Platforms:
- YouTube
- TikTok
- Instagram
- Twitter/X
- Facebook
- Reddit
- SoundCloud

Free Tier:
- {config.DAILY_LIMIT_FREE} videos per day
- No login required
- Just paste any link!

Unlimited Access:
- No daily limits
- Priority downloads
- Support development

/unlimited - Remove limits
/help - How to use
    """
    await update.message.reply_text(message)

# Command: /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = """
How to Use:

1. Copy any video link from:
   - YouTube, TikTok, Instagram
   - Twitter, Facebook, Reddit

2. Paste the link here

3. I send the video back!

Tips:
- Works best with public videos
- Large videos may take 10-15 seconds

/unlimited - Remove daily limits
    """
    await update.message.reply_text(message)

# Command: /unlimited (remove limits)
async def unlimited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    user = get_user(user_id)
    if user.get("unlimited", False):
        await update.message.reply_text("You already have Unlimited Access! Keep downloading as much as you want!")
        return
    
    await update.message.reply_text(
        f"Upgrade to Unlimited Access\n\nPrice: {config.UNLIMITED_PRICE_STARS} Telegram Stars (~$5)\n\nBenefits:\n- No daily limits (unlimited videos!)\n- Priority processing\n- Support the bot development\n\nHow to upgrade:\n1. Send /buy\n2. Send Stars to this bot\n3. Send /confirm after sending\n\nQuestions? Contact {config.SUPPORT_CONTACT}"
    )

# Command: /buy (payment)
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Upgrade to Unlimited - {config.UNLIMITED_PRICE_STARS} Stars\n\nHow to pay with Telegram Stars:\n\n1. Click the menu button (or type @username)\n2. Select Send Stars\n3. Send {config.UNLIMITED_PRICE_STARS} Stars to this bot\n4. After sending, type: /confirm YOUR_TX_ID\n\nHow to pay with TON (Crypto):\n- Contact {config.SUPPORT_CONTACT} for TON address\n\nManual Upgrade:\n- Contact {config.SUPPORT_CONTACT} for bank transfer\n\nAfter payment, type /confirm YOUR_TRANSACTION_ID\nYou'll be upgraded instantly!"
    )

# Command: /confirm (after payment)
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    user = get_user(user_id)
    if user.get("unlimited", False):
        await update.message.reply_text("You already have Unlimited Access!")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            "Please provide your transaction ID.\n\nExample: /confirm TX123456\n\nContact support if you need help."
        )
        return
    
    tx_id = args[0]
    
    update_user(user_id, 0, date.today().isoformat(), unlimited=True)
    
    await update.message.reply_text(
        "UPGRADED TO UNLIMITED!\n\nYou now have:\n- No daily limits\n- Unlimited YouTube downloads\n- Priority processing\n\nThank you for supporting the bot!\n\nJust paste any YouTube link and enjoy!"
    )
    
    owner_id = config.OWNER_ID
    await context.bot.send_message(
        chat_id=owner_id,
        text=f"NEW PAYMENT!\n\nUser: {user_id}\nTX ID: {tx_id}\nAmount: {config.UNLIMITED_PRICE_STARS} Stars\n\nUser upgraded to Unlimited!"
    )

# Command: /status
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if user.get("unlimited"):
        await update.message.reply_text("Status: Unlimited - No limits! Keep downloading.")
        return
    
    today = date.today().isoformat()
    if user.get("last_date") != today:
        remaining = config.DAILY_LIMIT_FREE
    else:
        remaining = config.DAILY_LIMIT_FREE - user.get("downloads_today", 0)
    
    await update.message.reply_text(
        f"Status: Free Tier\n\nRemaining today: {remaining}/{config.DAILY_LIMIT_FREE}\n\n/unlimited - Remove limits for {config.UNLIMITED_PRICE_STARS} Stars"
    )

# Command: /stats (owner only)
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != config.OWNER_ID:
        await update.message.reply_text("Only bot owner can use this.")
        return
    
    users = load_users()
    total_users = len(users)
    unlimited_users = sum(1 for u in users.values() if u.get("unlimited", False))
    
    await update.message.reply_text(
        f"Bot Statistics\n\nTotal users: {total_users}\nUnlimited users: {unlimited_users}\nPotential earnings: ${unlimited_users * 5} USD\n\nKeep growing!"
    )

# Main download handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        return
    
    allowed, remaining = can_download(user_id)
    if not allowed:
        await update.message.reply_text(
            f"Daily limit reached!\n\nYou've used {config.DAILY_LIMIT_FREE} downloads today.\n\n/unlimited - Remove limits for {config.UNLIMITED_PRICE_STARS} Stars"
        )
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
    
    status_msg = await update.message.reply_text(f"Downloading from {platform}... (30-60 seconds)")
    
    try:
        ydl_opts = {
            'format': 'best[height<=720]',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
            'no_check_certificate': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            video_url = None
            if 'url' in info:
                video_url = info['url']
            elif 'entries' in info and info['entries']:
                video_url = info['entries'][0].get('url')
            elif 'requested_formats' in info:
                video_url = info['requested_formats'][0].get('url')
            
            if not video_url:
                raise Exception("No video URL found")
            
            title = info.get('title', 'video')[:50]
            
            await update.message.reply_video(
                video_url,
                caption=f"Downloaded: {title}\nFrom: {platform}\n\n/unlimited - Remove limits",
                supports_streaming=True
            )
            
            increment_download(user_id)
            await status_msg.delete()
            
            if not get_user(user_id).get("unlimited"):
                _, remaining = can_download(user_id)
                if remaining > 0:
                    await update.message.reply_text(f"{remaining}/{config.DAILY_LIMIT_FREE} downloads remaining today. /unlimited to remove limits!")
            
    except Exception as e:
        await status_msg.edit_text(
            f"Download failed\n\nCould not download from {platform}.\n\nPossible reasons:\n- Video is private\n- Link is invalid\n- Platform blocked the download\n\nTry a different video or contact {config.SUPPORT_CONTACT}"
        )
        print(f"Error for user {user_id}: {e}")

# Main function
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
    
    print("=" * 50)
    print("BOT IS RUNNING!")
    print("=" * 50)
    print("Supported: YouTube, TikTok, Instagram, Twitter, Facebook, Reddit")
    print("No login required - just paste links!")
    print("=" * 50)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()