import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

# Daily limits - 3 free videos per day
DAILY_LIMIT_FREE = 3

# File size limit (Telegram max is 50MB)
MAX_FILE_SIZE_MB = 50

# Price for unlimited (in Telegram Stars)
UNLIMITED_PRICE_STARS = 500

# Your support contact
SUPPORT_CONTACT = "@ahli_imanli"