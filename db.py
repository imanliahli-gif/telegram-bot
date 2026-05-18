 
import json
import os
from datetime import datetime, timedelta

USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def get_user(user_id):
    users = load_users()
    user_id_str = str(user_id)
    return users.get(user_id_str, {})

def add_user(user_id):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {
            "downloads_today": 0,
            "last_download_date": None,
            "premium_expiry": None
        }
        save_users(users)

def is_premium(user_id):
    user = get_user(user_id)
    premium_expiry = user.get('premium_expiry')
    if premium_expiry:
        expiry_date = datetime.fromisoformat(premium_expiry)
        if expiry_date > datetime.now():
            return True
    return False

def add_premium(user_id, days=30):
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        add_user(user_id)
    
    current_expiry = users[user_id_str].get('premium_expiry')
    if current_expiry:
        new_expiry = datetime.fromisoformat(current_expiry) + timedelta(days=days)
    else:
        new_expiry = datetime.now() + timedelta(days=days)
    
    users[user_id_str]['premium_expiry'] = new_expiry.isoformat()
    save_users(users)

def increment_downloads(user_id):
    users = load_users()
    user_id_str = str(user_id)
    today = datetime.now().date().isoformat()
    
    if user_id_str not in users:
        add_user(user_id)
    
    if users[user_id_str].get('last_download_date') != today:
        users[user_id_str]['downloads_today'] = 0
        users[user_id_str]['last_download_date'] = today
    
    users[user_id_str]['downloads_today'] += 1
    save_users(users)

def get_today_downloads(user_id):
    user = get_user(user_id)
    today = datetime.now().date().isoformat()
    
    if user.get('last_download_date') != today:
        return 0
    return user.get('downloads_today', 0)