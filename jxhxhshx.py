# DofaminovSearch_bot.py - ПОЛНАЯ ВЕРСИЯ

import sys
import os
import re
import time
import json
import sqlite3
import requests
import hashlib
import urllib.parse
import httpx
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, Any, List, Dict
from bs4 import BeautifulSoup
import phonenumbers
from phonenumbers import parse, is_valid_number, format_number, PhoneNumberFormat, number_type, PhoneNumberType

import telebot
from telebot import types

# ================== КОНФИГ ==================
BOT_TOKEN = "8837359960:AAFl2lGLjkKSktxICJ8rGDocLzDuLVIQ7gE"
OWNER_ID = 8408746678,8557521484
ADMIN_IDS = [8408746678]

# BIGBASE API
BIGBASE_KEY = "rAo71SvGXKunusk4ePrWdcnBPYbVcka1"
BIGBASE_URL = "https://bigbase.top/api"

# DEPSEARCH API
DEPSEARCH_TOKEN = "WDTHx2vqZGE38gchBe7oAewzB9ZPNpxU"
DEPSEARCH_URL = "https://api.depsearch.sbs"

# ЦЕНЫ
PRICES = {
    "requests_3": 49,
    "requests_5": 149,
    "requests_25": 349,
    "requests_50": 499,
    "requests_100": 699,
    "subscription_day": 70,
    "subscription_week": 200,
    "subscription_month": 310,
    "subscription_forever": 399,
    "account_india": 30,
    "account_usa": 100,
    "proxy": 100
}

# Пути
DB_PATH = "dofaminov_bot.db"
BANNER_PATH = "/storage/emulated/0/Download/AyuGram/Telegram/banner.jpg"
PAYMENT_LINK = "https://pay.cloudtips.ru/p/01d7a932"

# Константы
DAILY_BONUS = 7
DAILY_LIMIT = 10
SIGNATURE = "\n\n🌊 DofaminovSearch"

# ================== ЛОГГИРОВАНИЕ ==================
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ================== ИНИЦИАЛИЗАЦИЯ БОТА ==================
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    session = requests.Session()
    session.timeout = (30, 60)
    session.verify = False
    
    bot = telebot.TeleBot(BOT_TOKEN)
    bot.session = session
    logger.info("✅ Бот инициализирован с увеличенными таймаутами")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации бота: {e}")
    bot = telebot.TeleBot(BOT_TOKEN)

# ================== БАЗА ДАННЫХ ==================
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                requests_balance INTEGER DEFAULT 7,
                requests_total INTEGER DEFAULT 0,
                daily_requests INTEGER DEFAULT 0,
                last_request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_daily_bonus TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_admin INTEGER DEFAULT 0,
                is_owner INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                is_muted INTEGER DEFAULT 0,
                muted_until TIMESTAMP,
                warns INTEGER DEFAULT 0,
                subscription_type TEXT DEFAULT 'none',
                subscription_until TIMESTAMP,
                ref_code TEXT,
                ref_invited_by INTEGER,
                ref_earned INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL,
                referred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                purchase_made INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS request_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                admin_id INTEGER,
                action TEXT,
                amount INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ref_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                action TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                requests_amount INTEGER DEFAULT 0,
                subscription_days INTEGER DEFAULT 0,
                created_by INTEGER,
                used_count INTEGER DEFAULT 0,
                max_uses INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promo_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                promo_id INTEGER,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ref_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                clicker_id INTEGER,
                clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ БД инициализирована")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {e}")
        return False

# ================== РАБОТА С БД ==================
def get_user(telegram_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'id': row[0],
                'telegram_id': row[1],
                'username': row[2] or "",
                'first_name': row[3] or "",
                'last_name': row[4] or "",
                'registered_at': row[5],
                'requests_balance': row[6] or 7,
                'requests_total': row[7] or 0,
                'daily_requests': row[8] or 0,
                'last_request_date': row[9],
                'last_daily_bonus': row[10],
                'is_admin': row[11] or 0,
                'is_owner': row[12] or 0,
                'is_banned': row[13] or 0,
                'is_muted': row[14] or 0,
                'muted_until': row[15],
                'warns': row[16] or 0,
                'subscription_type': row[17] or 'none',
                'subscription_until': row[18],
                'ref_code': row[19],
                'ref_invited_by': row[20],
                'ref_earned': row[21] or 0
            }
        return None
    except Exception as e:
        logger.error(f"Ошибка get_user: {e}")
        return None

def get_or_create_user(telegram_id, username="", first_name="", last_name=""):
    user = get_user(telegram_id)
    if user:
        return user
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        is_owner = 1 if telegram_id == OWNER_ID else 0
        is_admin = 1 if telegram_id in ADMIN_IDS else 0
        ref_code = hashlib.md5(f"{telegram_id}{time.time()}".encode()).hexdigest()[:8]
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO users (
                telegram_id, username, first_name, last_name, 
                is_owner, is_admin, ref_code, last_daily_bonus
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (telegram_id, username[:50] or "", first_name[:50] or "", last_name[:50] or "", 
              is_owner, is_admin, ref_code, now))
        conn.commit()
        conn.close()
        return get_user(telegram_id)
    except Exception as e:
        logger.error(f"❌ Ошибка create_user: {e}")
        return None

def check_daily_bonus(telegram_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT last_daily_bonus, requests_balance FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        last_bonus_str = row[0]
        current_balance = row[1] or 0
        today = datetime.now().date()
        try:
            last_bonus_date = datetime.fromisoformat(last_bonus_str).date()
        except:
            last_bonus_date = today - timedelta(days=1)
        if last_bonus_date < today and current_balance < DAILY_BONUS:
            new_balance = DAILY_BONUS
            cursor.execute('''
                UPDATE users 
                SET requests_balance = ?, last_daily_bonus = ?, daily_requests = 0
                WHERE telegram_id = ?
            ''', (new_balance, datetime.now().isoformat(), telegram_id))
            conn.commit()
            conn.close()
            return True
        conn.close()
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка check_daily_bonus: {e}")
        return False

def has_subscription(telegram_id):
    user = get_user(telegram_id)
    if not user:
        return False
    if user.get('subscription_type') == 'none':
        return False
    until = user.get('subscription_until')
    if until:
        try:
            until_date = datetime.fromisoformat(until)
            if until_date > datetime.now():
                return True
        except:
            pass
    return False

def can_use_search(telegram_id):
    user = get_user(telegram_id)
    if not user:
        return False, "Пользователь не найден"
    if user.get('is_banned'):
        return False, "🚫 Вы забанены"
    if has_subscription(telegram_id):
        return True, "Подписка активна"
    balance = user.get('requests_balance', 0)
    if balance > 0:
        return True, f"Осталось {balance} запросов"
    return False, "🚫 Недостаточно запросов! Купите пакет или подписку."

def deduct_request(telegram_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    check_daily_bonus(telegram_id)
    cursor.execute("SELECT requests_balance FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    if not row or row[0] <= 0:
        conn.close()
        return False
    cursor.execute('''
        UPDATE users 
        SET requests_balance = requests_balance - 1, 
            requests_total = requests_total + 1,
            daily_requests = daily_requests + 1
        WHERE telegram_id = ?
    ''', (telegram_id,))
    conn.commit()
    conn.close()
    return True

def add_requests(telegram_id, amount):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET requests_balance = requests_balance + ? WHERE telegram_id = ?", (amount, telegram_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка add_requests: {e}")
        return False

def set_subscription(telegram_id, sub_type, days):
    try:
        until = (datetime.now() + timedelta(days=days)).isoformat()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET subscription_type = ?, subscription_until = ? 
            WHERE telegram_id = ?
        ''', (sub_type, until, telegram_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка set_subscription: {e}")
        return False

def add_warn(telegram_id):
    user = get_user(telegram_id)
    if not user:
        return None
    warns = user.get('warns', 0) + 1
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if warns >= 3:
        cursor.execute("UPDATE users SET warns = 3, is_banned = 1 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        conn.close()
        return "ban"
    else:
        cursor.execute("UPDATE users SET warns = ? WHERE telegram_id = ?", (warns, telegram_id))
        conn.commit()
        conn.close()
        return warns

def remove_warn(telegram_id):
    user = get_user(telegram_id)
    if not user:
        return None
    warns = max(0, user.get('warns', 0) - 1)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET warns = ? WHERE telegram_id = ?", (warns, telegram_id))
    conn.commit()
    conn.close()
    return warns

def log_action(user_id, action, details=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO action_logs (user_id, action, details) VALUES (?, ?, ?)", 
                       (user_id, action, details[:500]))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка log_action: {e}")

def log_request(user_id, admin_id, action, amount):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO request_logs (user_id, admin_id, action, amount) VALUES (?, ?, ?, ?)",
                       (user_id, admin_id, action, amount))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка log_request: {e}")

def get_all_users():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        conn.close()
        return [{
            'id': r[0],
            'telegram_id': r[1],
            'username': r[2] or "",
            'first_name': r[3] or "",
            'last_name': r[4] or "",
            'registered_at': r[5],
            'requests_balance': r[6] or 7,
            'requests_total': r[7] or 0,
            'daily_requests': r[8] or 0,
            'last_request_date': r[9],
            'last_daily_bonus': r[10],
            'is_admin': r[11] or 0,
            'is_owner': r[12] or 0,
            'is_banned': r[13] or 0,
            'is_muted': r[14] or 0,
            'muted_until': r[15],
            'warns': r[16] or 0,
            'subscription_type': r[17] or 'none',
            'subscription_until': r[18],
            'ref_code': r[19],
            'ref_invited_by': r[20],
            'ref_earned': r[21] or 0
        } for r in rows]
    except Exception as e:
        logger.error(f"❌ Ошибка get_all_users: {e}")
        return []

# ================== РЕФЕРАЛЬНАЯ СИСТЕМА ==================
def get_ref_link(telegram_id):
    user = get_user(telegram_id)
    if not user:
        return None
    return f"https://t.me/DofaminovSearchBot?start=ref_{user['ref_code']}"

# ================== ПОЛНЫЙ ПАРСИНГ API ==================

def extract_all_fields(data, prefix=""):
    """Извлекает все поля из JSON-ответа рекурсивно"""
    results = {}
    
    if isinstance(data, dict):
        for key, value in data.items():
            field_name = f"{prefix}{key}" if prefix else key
            if isinstance(value, dict):
                results.update(extract_all_fields(value, f"{field_name}."))
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    for i, item in enumerate(value):
                        results.update(extract_all_fields(item, f"{field_name}[{i}]."))
                else:
                    results[field_name] = str(value)[:500]
            else:
                if value is not None and value != "":
                    results[field_name] = str(value)[:500]
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                results.update(extract_all_fields(item, f"{prefix}[{i}]."))
            else:
                results[f"{prefix}[{i}]"] = str(item)[:500]
    
    return results

def get_field_label(key):
    """Возвращает человекочитаемое название поля"""
    labels = {
        # Основные
        "fio": "👤 ФИО",
        "name": "👤 Имя",
        "first_name": "👤 Имя",
        "last_name": "👤 Фамилия",
        "full_name": "👤 Полное имя",
        "username": "📛 Username",
        "nick": "📛 Никнейм",
        "login": "🔑 Логин",
        "phone": "📱 Телефон",
        "phone_number": "📱 Телефон",
        "mobile": "📱 Мобильный",
        "email": "📧 Email",
        "mail": "📧 Почта",
        
        # Паспортные данные
        "passport": "📄 Паспорт",
        "passport_number": "📄 Номер паспорта",
        "passport_series": "📄 Серия паспорта",
        "passport_date": "📅 Дата выдачи паспорта",
        "issued_by": "🏛️ Кем выдан",
        "birth_date": "🎂 Дата рождения",
        "birth_place": "📍 Место рождения",
        "birthday": "🎂 День рождения",
        "dob": "🎂 Дата рождения",
        
        # Адрес
        "address": "📍 Адрес",
        "full_address": "📍 Полный адрес",
        "city": "🏙️ Город",
        "region": "📍 Регион",
        "country": "🌍 Страна",
        "street": "🏠 Улица",
        "house": "🏠 Дом",
        "flat": "🏠 Квартира",
        "apartment": "🏠 Квартира",
        "postal_code": "📮 Индекс",
        
        # СНИЛС, ИНН
        "snils": "🆔 СНИЛС",
        "inn": "🔢 ИНН",
        "tax_id": "🔢 ИНН",
        
        # Прочее
        "source": "📂 Источник",
        "date": "📅 Дата",
        "created_at": "📅 Создано",
        "updated_at": "📅 Обновлено",
        "ip": "🌐 IP",
        "ip_address": "🌐 IP-адрес",
        "operator": "📱 Оператор",
        "carrier": "📱 Оператор",
        "bank": "🏦 Банк",
        "card": "💳 Карта",
        "password": "🔐 Пароль",
        "hash": "🔑 Хеш",
        "domain": "🌐 Домен",
        "site": "🌐 Сайт",
        "url": "🔗 URL",
        "status": "📊 Статус",
        "type": "📋 Тип",
        "rating": "⭐ Рейтинг",
        "reviews": "💬 Отзывы",
        "comment": "💬 Комментарий",
        "description": "📝 Описание",
        "title": "📝 Заголовок",
        "notes": "📝 Заметки",
        "prepaid": "💳 Prepaid",
        "scheme": "💳 Платёжная система",
        "brand": "🏷️ Бренд",
        "country_code": "🌍 Код страны",
        "city_code": "🏙️ Код города"
    }
    
    # Ищем точное совпадение
    if key in labels:
        return labels[key]
    
    # Ищем частичное совпадение
    key_lower = key.lower()
    for k, label in labels.items():
        if k in key_lower or key_lower in k:
            return label
    
    # Если ничего не найдено
    return f"📌 {key.replace('_', ' ').title()}"

def generate_detailed_html_report(data, query, search_type="", source_name=""):
    """Генерирует детальный HTML-отчет со всей информацией"""
    
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    # Извлекаем все поля
    all_fields = {}
    if isinstance(data, dict):
        all_fields = extract_all_fields(data)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                fields = extract_all_fields(item, f"Запись {i+1}.")
                all_fields.update(fields)
            else:
                all_fields[f"Запись {i+1}"] = str(item)[:500]
    
    # Группируем поля по категориям
    categories = {
        "Личные данные": ["фИО", "имя", "фамилия", "полное имя", "fio", "name", "first_name", "last_name", "full_name", "username", "nick", "login"],
        "Контактные данные": ["телефон", "phone", "mobile", "email", "mail", "address", "адрес"],
        "Паспортные данные": ["паспорт", "passport", "серия", "номер", "выдан", "issued_by", "birth_date", "рождения", "birth_place"],
        "Идентификаторы": ["снилс", "snils", "инн", "inn", "tax_id"],
        "Финансовая информация": ["карта", "card", "банк", "bank", "prepaid", "scheme"],
        "Техническая информация": ["ip", "domain", "url", "hash", "password", "пароль"],
        "Дополнительная информация": ["source", "источник", "date", "дата", "status", "статус", "type", "тип", "rating", "рейтинг", "reviews", "отзывы", "comment", "комментарий"]
    }
    
    grouped = {}
    for key, value in all_fields.items():
        if not value or value in ["", "None", "null", "N/A"]:
            continue
        
        key_lower = key.lower()
        categorized = False
        
        for cat_name, keywords in categories.items():
            for keyword in keywords:
                if keyword in key_lower or key_lower in keyword:
                    if cat_name not in grouped:
                        grouped[cat_name] = []
                    grouped[cat_name].append((key, value))
                    categorized = True
                    break
            if categorized:
                break
        
        if not categorized:
            if "Другое" not in grouped:
                grouped["Другое"] = []
            grouped["Другое"].append((key, value))
    
    # Строим HTML
    html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DofaminovSearch — Отчет</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, 'Segoe UI', Roboto, system-ui, sans-serif;
            background: #0a0e17;
            color: #c8d8f0;
            min-height: 100vh;
            padding: 16px;
        }}
        .container {{
            max-width: 520px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(145deg, #0f1a2e, #162033);
            border-radius: 20px;
            padding: 20px 24px;
            margin-bottom: 16px;
            border: 1px solid #1a2a42;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }}
        .header .logo {{
            font-size: 24px;
            font-weight: 700;
            color: #4fc3f7;
            letter-spacing: 0.5px;
        }}
        .header .logo span {{ color: #81d4fa; }}
        .header .sub {{
            font-size: 12px;
            color: #5a7a9a;
            margin-top: 4px;
        }}
        .header .query {{
            font-size: 14px;
            color: #81d4fa;
            margin-top: 8px;
            background: #0a1628;
            padding: 8px 14px;
            border-radius: 10px;
            display: inline-block;
            border: 1px solid #1a2a4a;
            word-break: break-all;
        }}
        .info-box {{
            background: #0f1a2e;
            border-radius: 16px;
            padding: 16px 20px;
            margin-bottom: 12px;
            border: 1px solid #1a2a42;
        }}
        .info-box .title {{
            font-size: 13px;
            font-weight: 600;
            color: #4fc3f7;
            margin-bottom: 10px;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #1a2a42;
            padding-bottom: 8px;
        }}
        .info-item {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid #0a1628;
            gap: 10px;
        }}
        .info-item:last-child {{ border-bottom: none; }}
        .info-item .label {{
            color: #4a7aaa;
            font-size: 12px;
            font-weight: 500;
            flex-shrink: 0;
            max-width: 45%;
        }}
        .info-item .value {{
            color: #c8d8f0;
            font-size: 12px;
            text-align: right;
            word-break: break-word;
            max-width: 55%;
        }}
        .info-item .value.highlight {{ color: #81d4fa; }}
        .info-item .value.email {{ color: #66bb6a; }}
        .info-item .value.phone {{ color: #4fc3f7; }}
        .info-item .value.password {{ color: #ffa726; font-family: monospace; }}
        .info-item .value.snils {{ color: #ffd54f; }}
        .info-item .value.passport {{ color: #ff8a65; }}
        .info-item .value.address {{ color: #aed581; }}
        .info-item .value.birth {{ color: #ce93d8; }}
        .footer {{
            text-align: center;
            padding: 16px;
            font-size: 11px;
            color: #3a5a7a;
            border-top: 1px solid #0d1a30;
            margin-top: 16px;
        }}
        .footer .brand {{ color: #4fc3f7; font-weight: 600; }}
        .badge {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 9px;
            font-weight: 600;
            margin: 2px;
        }}
        .badge.green {{ background: #0d2a1a; color: #66bb6a; }}
        .badge.blue {{ background: #0d2a4a; color: #4fc3f7; }}
        .badge.orange {{ background: #2a1a0d; color: #ffa726; }}
        .badge.red {{ background: #2a0d0d; color: #ef5350; }}
        .badge.purple {{ background: #1a0d2a; color: #ce93d8; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 12px;
        }}
        .stat-card {{
            background: #0f1a2e;
            border-radius: 12px;
            padding: 12px 8px;
            text-align: center;
            border: 1px solid #1a2a42;
        }}
        .stat-card .num {{
            font-size: 20px;
            font-weight: 700;
            color: #4fc3f7;
        }}
        .stat-card .label {{
            font-size: 8px;
            color: #4a6a8a;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 2px;
        }}
        @media (max-width: 400px) {{
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="logo">🌊 <span>DofaminovSearch</span></div>
        <div class="sub">Детальный отчет по запросу</div>
        <div class="query">🔍 {query[:50]}</div>
        <div class="sub" style="font-size: 10px; color: #3a5a7a; margin-top: 6px;">
            {search_type} • {source_name} • {timestamp}
        </div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="num">{len(all_fields)}</div>
            <div class="label">Всего полей</div>
        </div>
        <div class="stat-card">
            <div class="num">{len(grouped)}</div>
            <div class="label">Категорий</div>
        </div>
        <div class="stat-card">
            <div class="num">{len([v for v in all_fields.values() if v])}</div>
            <div class="label">Заполнено</div>
        </div>
    </div>
    
    <div class="info-box">
        <div class="title">📋 ИНФОРМАЦИЯ О ЗАПРОСЕ</div>
        <div class="info-item">
            <span class="label">Запрос</span>
            <span class="value highlight">{query}</span>
        </div>
        <div class="info-item">
            <span class="label">Тип поиска</span>
            <span class="value">{search_type}</span>
        </div>
        <div class="info-item">
            <span class="label">Источник</span>
            <span class="value">{source_name}</span>
        </div>
        <div class="info-item">
            <span class="label">Дата отчета</span>
            <span class="value">{timestamp}</span>
        </div>
        <div class="info-item">
            <span class="label">Всего записей</span>
            <span class="value">{len(data) if isinstance(data, list) else 1}</span>
        </div>
    </div>
    
    <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px;">
        <span class="badge blue">DofaminovSearch</span>
        <span class="badge green">OSINT</span>
        <span class="badge orange">Отчет</span>
        <span class="badge purple">Детально</span>
    </div>
'''
    
    # Категории
    category_order = ["Личные данные", "Контактные данные", "Паспортные данные", "Идентификаторы", "Финансовая информация", "Техническая информация", "Дополнительная информация", "Другое"]
    
    for cat_name in category_order:
        if cat_name in grouped and grouped[cat_name]:
            items = grouped[cat_name]
            html += f'''
    <div class="info-box">
        <div class="title">📂 {cat_name}</div>'''
            
            for key, value in items:
                value_class = ""
                label = get_field_label(key)
                
                key_lower = key.lower()
                if any(k in key_lower for k in ["email", "mail"]):
                    value_class = "email"
                elif any(k in key_lower for k in ["phone", "mobile", "телефон"]):
                    value_class = "phone"
                elif any(k in key_lower for k in ["password", "пароль"]):
                    value_class = "password"
                elif any(k in key_lower for k in ["snils", "снилс"]):
                    value_class = "snils"
                elif any(k in key_lower for k in ["passport", "паспорт"]):
                    value_class = "passport"
                elif any(k in key_lower for k in ["address", "адрес"]):
                    value_class = "address"
                elif any(k in key_lower for k in ["birth", "рожд", "dob"]):
                    value_class = "birth"
                elif any(k in key_lower for k in ["fio", "name", "имя", "фамилия"]):
                    value_class = "highlight"
                
                display_value = value
                if len(display_value) > 150:
                    display_value = display_value[:150] + "..."
                
                html += f'''
        <div class="info-item">
            <span class="label">{label}</span>
            <span class="value {value_class}">{display_value}</span>
        </div>'''
            
            html += '''
    </div>'''
    
    if not any(grouped.values()):
        html += '''
    <div class="info-box">
        <div class="title">ℹ️ Информация</div>
        <div style="color: #4a6a8a; text-align: center; padding: 12px 0; font-size: 13px;">
            Нет данных для отображения
        </div>
    </div>'''
    
    html += f'''
    <div style="text-align: center; color: #3a5a7a; padding: 8px 0; font-size: 10px;">
        Полный дамп данных доступен в исходном JSON
    </div>
    
    <div class="footer">
        <span class="brand">🌊 DofaminovSearch</span> • OSINT отчет<br>
        <span style="color: #2a4a6a;">{timestamp}</span>
    </div>
    
</div>
</body>
</html>'''
    
    return html

# ================== ПОИСКОВЫЕ ФУНКЦИИ ==================

def search_bigbase(query):
    try:
        headers = {
            "Authorization": BIGBASE_KEY,
            "Content-Type": "application/json"
        }
        payload = {"search": query, "page": 0}
        response = requests.post(f"{BIGBASE_URL}/search", headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def search_depsearch(query, lang="ru"):
    try:
        encoded = urllib.parse.quote(query)
        url = f"{DEPSEARCH_URL}/quest={encoded}&token={DEPSEARCH_TOKEN}&lang={lang}"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            return {"error": "Превышен лимит запросов (70/мин)"}
        elif response.status_code == 403:
            return {"error": "Неверный токен DepSearch"}
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def combined_search(query):
    results = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "sources": {}
    }
    try:
        results["sources"]["bigbase"] = search_bigbase(query)
    except Exception as e:
        results["sources"]["bigbase"] = {"error": str(e)}
    try:
        results["sources"]["depsearch"] = search_depsearch(query)
    except Exception as e:
        results["sources"]["depsearch"] = {"error": str(e)}
    return results

# ================== ФУНКЦИИ ДЛЯ ОТПРАВКИ ОТЧЕТОВ ==================

def send_detailed_report(chat_id, data, query, search_type, source_name):
    """Отправляет детальный HTML-отчет"""
    try:
        html_content = generate_detailed_html_report(data, query, search_type, source_name)
        
        filename = f"report_{chat_id}_{int(time.time())}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        with open(filename, "rb") as f:
            bot.send_document(
                chat_id, 
                f, 
                caption=f"🌊 DofaminovSearch — Детальный отчет\n📝 Запрос: {query}\n📊 Полная информация"
            )
        
        os.remove(filename)
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки отчета: {e}")
        return False

def send_text_report(chat_id, data, query, search_type):
    """Отправляет текстовый отчет с основной информацией"""
    try:
        all_fields = {}
        if isinstance(data, dict):
            all_fields = extract_all_fields(data)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    all_fields.update(extract_all_fields(item))
        
        output = []
        output.append(f"🔍 *РЕЗУЛЬТАТЫ ПОИСКА*")
        output.append("=" * 30)
        output.append(f"📝 Запрос: `{query}`")
        output.append(f"📋 Тип: {search_type}")
        output.append("")
        
        priority_keys = ["fio", "name", "full_name", "phone", "phone_number", "email", "snils", "inn", "passport", "address", "birth_date", "birth_place"]
        
        for key in priority_keys:
            if key in all_fields and all_fields[key]:
                label = get_field_label(key)
                output.append(f"{label}: `{all_fields[key][:100]}`")
        
        for key, value in all_fields.items():
            if key not in priority_keys and value:
                label = get_field_label(key)
                if len(value) > 100:
                    value = value[:100] + "..."
                output.append(f"{label}: `{value}`")
        
        if len(all_fields) == 0:
            output.append("❌ Данные не найдены")
        
        text = "\n".join(output)
        safe_send(chat_id, text + SIGNATURE)
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки текстового отчета: {e}")
        return False

# ================== ОТПРАВКА СООБЩЕНИЙ ==================

last_menu_msg = {}

def safe_send(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    if not text:
        return None
    if len(text) > 4096:
        text = text[:4096] + "\n\n...(обрезано)"
    try:
        return bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup, timeout=30)
    except:
        clean_text = re.sub(r'[_*[\]()~`>#+\-=|{}.!]', '', text)
        try:
            return bot.send_message(chat_id, clean_text, reply_markup=reply_markup, timeout=30)
        except:
            return bot.send_message(chat_id, clean_text[:4000], reply_markup=reply_markup, timeout=30)

def send_banner_with_menu(chat_id, user_id=None, status=None):
    if chat_id in last_menu_msg:
        try:
            bot.delete_message(chat_id, last_menu_msg[chat_id])
        except:
            pass
        del last_menu_msg[chat_id]
    
    caption = "🌊 *DofaminovSearch*\n\n"
    if status:
        caption += f"{status}\n\n"
    caption += "Выберите действие:"
    
    try:
        if os.path.exists(BANNER_PATH):
            with open(BANNER_PATH, 'rb') as f:
                m = bot.send_photo(chat_id, f, caption=caption, parse_mode="Markdown", reply_markup=get_main_menu(user_id), timeout=30)
        else:
            m = bot.send_message(chat_id, caption, parse_mode="Markdown", reply_markup=get_main_menu(user_id), timeout=30)
        last_menu_msg[chat_id] = m.message_id
        return m
    except Exception as e:
        logger.error(f"Ошибка отправки баннера: {e}")
        m = bot.send_message(chat_id, caption, parse_mode="Markdown", reply_markup=get_main_menu(user_id), timeout=30)
        last_menu_msg[chat_id] = m.message_id
        return m

# ================== КЛАВИАТУРЫ ==================

def get_main_menu(user_id=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("🔍 Пробив", callback_data="menu_search"),
        types.InlineKeyboardButton("📦 Пакеты", callback_data="menu_packages")
    )
    markup.row(
        types.InlineKeyboardButton("🎫 Подписка", callback_data="menu_subscription"),
        types.InlineKeyboardButton("👤 Профиль", callback_data="menu_profile")
    )
    markup.row(
        types.InlineKeyboardButton("🧑‍💻 Админ-панель", callback_data="menu_admin"),
        types.InlineKeyboardButton("📋 Лог-панель", callback_data="menu_logs")
    )
    markup.row(
        types.InlineKeyboardButton("🎁 Промокод", callback_data="menu_promo"),
        types.InlineKeyboardButton("🛒 Аккаунты", callback_data="menu_accounts")
    )
    return markup

def get_search_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        ("📱 По номеру", "search_phone"),
        ("📧 По почте", "search_email"),
        ("📛 По юзернейму", "search_username"),
        ("🔍 BigBase", "search_bigbase"),
        ("🔍 DepSearch", "search_depsearch"),
        ("🔍 Комбо", "search_combined"),
        ("💳 По карте (BIN)", "search_card"),
        ("📱 Проверка соц.сетей", "search_social"),
        ("📊 Репутация", "search_reputation"),
        ("📞 CallApp", "search_callapp"),
        ("👁️ Eyecon", "search_eyecon"),
        ("📞 Zvonili", "search_zvonili")
    ]
    for text, callback in buttons:
        markup.add(types.InlineKeyboardButton(text, callback_data=callback))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    return markup

def get_packages_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("3 запроса - 49₽", callback_data="package_3"),
        types.InlineKeyboardButton("5 запросов - 149₽", callback_data="package_5")
    )
    markup.row(
        types.InlineKeyboardButton("25 запросов - 349₽", callback_data="package_25"),
        types.InlineKeyboardButton("50 запросов - 499₽", callback_data="package_50")
    )
    markup.row(
        types.InlineKeyboardButton("100 запросов - 699₽", callback_data="package_100")
    )
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    return markup

def get_subscription_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("1 день - 70₽", callback_data="sub_day"),
        types.InlineKeyboardButton("Неделя - 200₽", callback_data="sub_week")
    )
    markup.row(
        types.InlineKeyboardButton("Месяц - 310₽", callback_data="sub_month"),
        types.InlineKeyboardButton("Навсегда - 399₽", callback_data="sub_forever")
    )
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    return markup

def get_admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.row(types.InlineKeyboardButton("📥 Выдать запросы", callback_data="admin_give"))
    markup.row(types.InlineKeyboardButton("📤 Забрать запросы", callback_data="admin_take"))
    markup.row(types.InlineKeyboardButton("🎫 Выдать подписку", callback_data="admin_sub"))
    markup.row(types.InlineKeyboardButton("🛒 Выдать аккаунт", callback_data="admin_account"))
    markup.row(types.InlineKeyboardButton("📊 Список пользователей", callback_data="admin_users"))
    markup.row(types.InlineKeyboardButton("💰 Изменить цену", callback_data="admin_price"))
    markup.row(types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_mail"))
    markup.row(types.InlineKeyboardButton("🚫 Бан пользователя", callback_data="admin_ban"))
    markup.row(types.InlineKeyboardButton("🔇 Мут", callback_data="admin_mute"))
    markup.row(types.InlineKeyboardButton("⚠️ Выдать варн", callback_data="admin_warn"))
    markup.row(types.InlineKeyboardButton("✅ Снять варн", callback_data="admin_unwarn"))
    markup.row(types.InlineKeyboardButton("🔓 Разбан", callback_data="admin_unban"))
    markup.row(types.InlineKeyboardButton("🔊 Снять мут", callback_data="admin_unmute"))
    markup.row(types.InlineKeyboardButton("🔗 Реф. ссылка", callback_data="admin_ref_link"))
    markup.row(types.InlineKeyboardButton("📊 Реф. статистика", callback_data="admin_ref_stats"))
    markup.row(types.InlineKeyboardButton("🏆 Топ рефералов", callback_data="admin_ref_top"))
    markup.row(types.InlineKeyboardButton("📝 Личное сообщение", callback_data="admin_msg"))
    markup.row(types.InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    return markup

def get_logs_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.row(types.InlineKeyboardButton("📊 Лог выдач запросов", callback_data="log_requests"))
    markup.row(types.InlineKeyboardButton("⏱️ Действия за 24 часа", callback_data="log_time"))
    markup.row(types.InlineKeyboardButton("📋 Полный лог", callback_data="log_all"))
    markup.row(types.InlineKeyboardButton("🔗 Лог рефералов", callback_data="log_ref"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    return markup

def get_accounts_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.row(
        types.InlineKeyboardButton("🇮🇳 Индия - 30₽ (80% риск)", callback_data="account_india"),
        types.InlineKeyboardButton("🇺🇸 США - 100₽ (0% риск)", callback_data="account_usa")
    )
    markup.row(
        types.InlineKeyboardButton("🛒 Прокси - 100₽", callback_data="account_proxy")
    )
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    return markup

def get_profile_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📊 Реферальная статистика", callback_data="profile_ref_stats"))
    markup.add(types.InlineKeyboardButton("🔗 Моя реферальная ссылка", callback_data="profile_ref_link"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    return markup

# ================== ОСНОВНЫЕ ХЕНДЛЕРЫ ==================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    ref_code = None
    if message.text and "ref_" in message.text:
        try:
            ref_code = message.text.split("ref_")[1].strip()
        except:
            pass
    
    user = get_or_create_user(user_id, message.from_user.username or "", message.from_user.first_name or "", message.from_user.last_name or "")
    
    if not user:
        safe_send(chat_id, "❌ Ошибка создания пользователя. Попробуйте позже.")
        return
    
    if user.get('is_banned'):
        safe_send(chat_id, "🚫 Вы забанены")
        return
    
    # Обработка реферала
    if ref_code:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id FROM users WHERE ref_code = ?", (ref_code,))
            row = cursor.fetchone()
            if row:
                referrer_id = row[0]
                if referrer_id != user_id:
                    cursor.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, user_id))
                    cursor.execute("UPDATE users SET requests_balance = requests_balance + 1, ref_earned = ref_earned + 1 WHERE telegram_id = ?", (referrer_id,))
                    cursor.execute("INSERT INTO ref_clicks (referrer_id, clicker_id) VALUES (?, ?)", (referrer_id, user_id))
                    cursor.execute("INSERT INTO ref_logs (referrer_id, referred_id, action) VALUES (?, ?, 'registration')", (referrer_id, user_id))
                    conn.commit()
                    try:
                        bot.send_message(referrer_id, f"🎉 По вашей реферальной ссылке зарегистрировался новый пользователь!\n📊 Вы получили +1 запрос")
                    except:
                        pass
            conn.close()
        except Exception as e:
            logger.error(f"Ошибка реферала: {e}")
    
    check_daily_bonus(user_id)
    user = get_user(user_id)
    
    welcome_text = (
        "🌊 *Добро пожаловать в DofaminovSearch!*\n\n"
        "🔍 *Мощный OSINT-инструмент для поиска информации*\n\n"
        "📝 *Доступные услуги:*\n"
        "🔍 Пробив — по номеру/почте/юзеру\n"
        "📦 Пакеты запросов — 3, 5, 25, 50, 100 запросов\n"
        "🎫 Подписка — день/неделя/месяц/навсегда\n"
        "🛒 Аккаунты — Индия/США, прокси\n\n"
        f"📊 *Ваш баланс:* {user.get('requests_balance', 0)} запросов\n"
        f"📅 *Ежедневный бонус:* +{DAILY_BONUS} запросов\n\n"
        "👤 Для заказа аккаунтов обращайтесь к @xam1m"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✧ Открыть меню", callback_data="menu_enter"))
    
    safe_send(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "menu_enter")
def handle_menu_enter(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    send_banner_with_menu(chat_id, user_id=user_id)

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def handle_back_main(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    send_banner_with_menu(chat_id, user_id=user_id)

# ================== МЕНЮ ПОИСКА ==================

@bot.callback_query_handler(func=lambda call: call.data == "menu_search")
def handle_menu_search(call):
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    caption = "🔍 *Выберите тип поиска:*"
    m = safe_send(chat_id, caption, parse_mode="Markdown", reply_markup=get_search_menu())
    if m:
        last_menu_msg[chat_id] = m.message_id

# ================== ОБРАБОТЧИКИ ПОИСКА ==================

@bot.callback_query_handler(func=lambda call: call.data.startswith("search_"))
def handle_search_callbacks(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    search_type = call.data.replace("search_", "")
    
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    can, msg = can_use_search(user_id)
    if not can:
        safe_send(chat_id, msg)
        send_banner_with_menu(chat_id, user_id=user_id)
        return
    
    special_handlers = {
        "bigbase": ("🔍 *Поиск в BigBase*\n\nВведите запрос:", "BigBase", process_bigbase_search),
        "depsearch": ("🔍 *Поиск в DepSearch*\n\nПоддерживает: ФИО, телефон, email, никнейм, СНИЛС, ИНН, IP, VIN, адрес\n\nВведите запрос:", "DepSearch", process_depsearch_search),
        "combined": ("🔍 *Комбинированный поиск (BigBase + DepSearch)*\n\nВведите запрос:", "Combined", process_combined_search),
    }
    
    if search_type in special_handlers:
        prompt, source, handler = special_handlers[search_type]
        msg = safe_send(
            chat_id, 
            prompt,
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("⬅️ Назад", callback_data="menu_search")
            )
        )
        bot.register_next_step_handler(msg, lambda m: handler(m, source))
        return
    
    prompts = {
        "phone": "📱 *Введите номер телефона:*\n\nПример: 79281234567",
        "email": "📧 *Введите Email:*\n\nПример: example@mail.ru",
        "username": "📛 *Введите юзернейм:*\n\nПример: @username или username"
    }
    
    msg = safe_send(
        chat_id, 
        prompts.get(search_type, "Введите запрос:"),
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_main")
        )
    )
    bot.register_next_step_handler(msg, lambda m: process_simple_search(m, search_type))

def process_simple_search(message, search_type):
    chat_id = message.chat.id
    user_id = message.from_user.id
    query = message.text.strip()
    
    if query in ["⬅️ Назад в меню", "⬅️ Назад"]:
        send_banner_with_menu(chat_id, user_id=user_id)
        return
    
    if not query:
        safe_send(chat_id, "❌ Введите запрос")
        return
    
    can, msg = can_use_search(user_id)
    if not can:
        safe_send(chat_id, msg)
        send_banner_with_menu(chat_id, user_id=user_id)
        return
    
    if not has_subscription(user_id):
        if not deduct_request(user_id):
            safe_send(chat_id, "🚫 Не удалось списать запрос")
            return
    
    status_msg = safe_send(chat_id, f"⏳ *Поиск по запросу:* `{query}`\n\nЭто может занять некоторое время...")
    
    try:
        result = search_bigbase(query)
        
        if result and "error" not in result:
            send_detailed_report(chat_id, result, query, search_type, "BigBase")
            send_text_report(chat_id, result, query, search_type)
        else:
            safe_send(chat_id, f"❌ Данные не найдены: {result.get('error', 'Нет результатов')}")
        
        log_action(user_id, "search", f"{search_type}: {query}")
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        safe_send(chat_id, f"❌ Ошибка: {str(e)}")
    
    try:
        bot.delete_message(chat_id, status_msg.message_id)
    except:
        pass

def process_bigbase_search(message, source):
    chat_id = message.chat.id
    user_id = message.from_user.id
    query = message.text.strip()
    
    if query in ["⬅️ Назад в меню", "⬅️ Назад"]:
        send_banner_with_menu(chat_id, user_id=user_id)
        return
    
    if not query:
        safe_send(chat_id, "❌ Введите запрос")
        return
    
    can, msg = can_use_search(user_id)
    if not can:
        safe_send(chat_id, msg)
        send_banner_with_menu(chat_id, user_id=user_id)
        return
    
    if not has_subscription(user_id):
        if not deduct_request(user_id):
            safe_send(chat_id, "🚫 Не удалось списать запрос")
            return
    
    status_msg = safe_send(chat_id, f"⏳ *Поиск в BigBase:* `{query}`")
    
    try:
        result = search_bigbase(query)
        
        if result and "error" not in result:
            send_detailed_report(chat_id, result, query, "BigBase", "BigBase")
            send_text_report(chat_id, result, query, "BigBase")
        else:
            safe_send(chat_id, f"❌ Данные не найдены: {result.get('error', 'Нет результатов')}")
        
        log_action(user_id, "search_bigbase", query)
    except Exception as e:
        logger.error(f"Ошибка BigBase: {e}")
        safe_send(chat_id, f"❌ Ошибка: {str(e)}")
    
    try:
        bot.delete_message(chat_id, status_msg.message_id)
    except:
        pass

def process_depsearch_search(message, source):
    chat_id = message.chat.id
    user_id = message.from_user.id
    query = message.text.strip()
    
    if query in ["⬅️ Назад в меню", "⬅️ Назад"]:
        send_banner_with_menu(chat_id, user_id=user_id)
        return
    
    if not query:
        safe_send(chat_id, "❌ Введите запрос")
        return
    
    can, msg = can_use_search(user_id)
    if not can:
        safe_send(chat_id, msg)
        send_banner_with_menu(chat_id, user_id=user_id)
        return
    
    if not has_subscription(user_id):
        if not deduct_request(user_id):
            safe_send(chat_id, "🚫 Не удалось списать запрос")
            return
    
    status_msg = safe_send(chat_id, f"⏳ *Поиск в DepSearch:* `{query}`")
    
    try:
        result = search_depsearch(query)
        
        if result and "error" not in result:
            send_detailed_report(chat_id, result, query, "DepSearch", "DepSearch")
            send_text_report(chat_id, result, query, "DepSearch")
        else:
            safe_send(chat_id, f"❌ Данные не найдены: {result.get('error', 'Нет результатов')}")
        
        log_action(user_id, "search_depsearch", query)
    except Exception as e:
        logger.error(f"Ошибка DepSearch: {e}")
        safe_send(chat_id, f"❌ Ошибка: {str(e)}")
    
    try:
        bot.delete_message(chat_id, status_msg.message_id)
    except:
        pass

def process_combined_search(message, source):
    chat_id = message.chat.id
    user_id = message.from_user.id
    query = message.text.strip()
    
    if query in ["⬅️ Назад в меню", "⬅️ Назад"]:
        send_banner_with_menu(chat_id, user_id=user_id)
        return
    
    if not query:
        safe_send(chat_id, "❌ Введите запрос")
        return
    
    can, msg = can_use_search(user_id)
    if not can:
        safe_send(chat_id, msg)
        send_banner_with_menu(chat_id, user_id=user_id)
        return
    
    if not has_subscription(user_id):
        if not deduct_request(user_id):
            safe_send(chat_id, "🚫 Не удалось списать запрос")
            return
    
    status_msg = safe_send(chat_id, f"⏳ *Комбинированный поиск:* `{query}`\n\nBigBase + DepSearch...")
    
    try:
        result = combined_search(query)
        
        if "sources" in result:
            for source_name, data in result["sources"].items():
                if data and "error" not in data:
                    send_detailed_report(chat_id, data, query, source_name, source_name)
                    send_text_report(chat_id, data, query, source_name)
        
        log_action(user_id, "search_combined", query)
    except Exception as e:
        logger.error(f"Ошибка комбинированного поиска: {e}")
        safe_send(chat_id, f"❌ Ошибка: {str(e)}")
    
    try:
        bot.delete_message(chat_id, status_msg.message_id)
    except:
        pass

# ================== ПАКЕТЫ ЗАПРОСОВ ==================

@bot.callback_query_handler(func=lambda call: call.data == "menu_packages")
def handle_menu_packages(call):
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    text = (
        "📦 *Пакеты запросов*\n\n"
        "Выберите пакет:\n\n"
        "📊 3 запроса — 49₽ (16.3₽/запрос)\n"
        "📊 5 запросов — 149₽ (29.8₽/запрос)\n"
        "📊 25 запросов — 349₽ (13.96₽/запрос) 💰 -39%\n"
        "📊 50 запросов — 499₽ (9.98₽/запрос) 💰 -71%\n"
        "📊 100 запросов — 699₽ (6.99₽/запрос) 💰 -85%\n\n"
        f"💳 *Оплата:* {PAYMENT_LINK}\n\n"
        "После оплаты отправьте чек @xam1m"
    )
    
    m = safe_send(chat_id, text, parse_mode="Markdown", reply_markup=get_packages_menu())
    if m:
        last_menu_msg[chat_id] = m.message_id

@bot.callback_query_handler(func=lambda call: call.data.startswith("package_"))
def handle_package(call):
    chat_id = call.message.chat.id
    amount = call.data.replace("package_", "")
    price = PRICES.get(f"requests_{amount}", 0)
    
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    text = (
        f"📦 *Пакет {amount} запросов*\n\n"
        f"💰 Цена: {price}₽\n\n"
        "📝 *Инструкция:*\n"
        "1. Перейдите по ссылке для оплаты\n"
        "2. Оплатите указанную сумму\n"
        "3. Отправьте скриншот/чек @xam1m\n"
        "4. После подтверждения вам будут начислены запросы\n\n"
        f"💳 *Ссылка для оплаты:* {PAYMENT_LINK}"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 Оплатить", url=PAYMENT_LINK))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="menu_packages"))
    
    safe_send(chat_id, text, parse_mode="Markdown", reply_markup=markup)

# ================== ПОДПИСКА ==================

@bot.callback_query_handler(func=lambda call: call.data == "menu_subscription")
def handle_menu_subscription(call):
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    text = (
        "🎫 *Подписка*\n\n"
        "💰 Цены:\n"
        "📅 1 день — 70₽\n"
        "📅 Неделя — 200₽ (-28%)\n"
        "📅 Месяц — 310₽ (-66%)\n"
        "📅 Навсегда — 399₽ (-84%)\n\n"
        "✨ *Преимущества подписки:*\n"
        "🔓 Безлимитный доступ к пробивам\n"
        "🎁 Ежедневный бонус +7 запросов\n"
        "⚡ Приоритетная обработка\n\n"
        f"💳 *Оплата:* {PAYMENT_LINK}\n\n"
        "После оплаты отправьте чек @xam1m"
    )
    
    m = safe_send(chat_id, text, parse_mode="Markdown", reply_markup=get_subscription_menu())
    if m:
        last_menu_msg[chat_id] = m.message_id

@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_"))
def handle_subscription(call):
    chat_id = call.message.chat.id
    sub_type = call.data.replace("sub_", "")
    
    sub_names = {
        "day": "1 день",
        "week": "Неделя",
        "month": "Месяц",
        "forever": "Навсегда"
    }
    
    price = PRICES.get(f"subscription_{sub_type}", 0)
    
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    text = (
        f"🎫 *Подписка: {sub_names.get(sub_type, sub_type)}*\n\n"
        f"💰 Цена: {price}₽\n\n"
        "📝 *Инструкция:*\n"
        "1. Перейдите по ссылке для оплаты\n"
        "2. Оплатите указанную сумму\n"
        "3. Отправьте скриншот/чек @xam1m\n"
        "4. После подтверждения подписка будет активирована\n\n"
        f"💳 *Ссылка для оплаты:* {PAYMENT_LINK}"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 Оплатить", url=PAYMENT_LINK))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="menu_subscription"))
    
    safe_send(chat_id, text, parse_mode="Markdown", reply_markup=markup)

# ================== ПРОФИЛЬ ==================

@bot.callback_query_handler(func=lambda call: call.data == "menu_profile")
def handle_menu_profile(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    user = get_user(user_id)
    if not user:
        safe_send(chat_id, "❌ Ошибка получения профиля")
        return
    
    sub_status = "❌ Нет"
    sub_until = "—"
    if has_subscription(user_id):
        sub_status = "✅ Активна"
        until = user.get('subscription_until')
        if until:
            try:
                until_date = datetime.fromisoformat(until)
                sub_until = until_date.strftime("%d.%m.%Y")
            except:
                sub_until = until
    
    warns = user.get('warns', 0)
    if warns >= 3:
        warn_status = "🔴 БАН (3/3)"
    elif warns == 2:
        warn_status = "🟠 Последнее предупреждение (2/3)"
    elif warns == 1:
        warn_status = "🟡 Предупреждение (1/3)"
    else:
        warn_status = "🟢 Без нарушений (0/3)"
    
    ref_link = get_ref_link(user_id)
    
    text = (
        f"👤 *ТВОЙ ПРОФИЛЬ*\n\n"
        f"🆔 ID: `{user['telegram_id']}`\n"
        f"📛 Ник: @{user['username'] or 'Не указан'}\n"
        f"📅 Регистрация: {user['registered_at'][:10] if user['registered_at'] else '—'}\n\n"
        f"📦 Запросов: {user['requests_balance']}\n"
        f"📊 Всего запросов: {user['requests_total']}\n"
        f"🎫 Подписка: {sub_status}\n"
        f"📅 До: {sub_until}\n\n"
        f"⚠️ Варны: {warn_status}\n"
        f"🔄 Рефералов: {user.get('ref_earned', 0)} бонусов\n\n"
        f"📎 Реферальная ссылка:\n`{ref_link}`"
    )
    
    m = safe_send(chat_id, text, parse_mode="Markdown", reply_markup=get_profile_menu())
    if m:
        last_menu_msg[chat_id] = m.message_id

# ================== АДМИН-ПАНЕЛЬ ==================

@bot.callback_query_handler(func=lambda call: call.data == "menu_admin")
def handle_menu_admin(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    text = "🧑‍💻 *Админ-панель*\n\nВыберите действие:"
    m = safe_send(chat_id, text, parse_mode="Markdown", reply_markup=get_admin_menu())
    if m:
        last_menu_msg[chat_id] = m.message_id

@bot.callback_query_handler(func=lambda call: call.data == "admin_give")
def handle_admin_give(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "📥 *Выдать запросы*\n\nВведите ID пользователя и количество через пробел:\nПример: `123456789 10`",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
        )
    )
    bot.register_next_step_handler(msg, lambda m: admin_give_process(m, "give"))

@bot.callback_query_handler(func=lambda call: call.data == "admin_take")
def handle_admin_take(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "📤 *Забрать запросы*\n\nВведите ID пользователя и количество через пробел:\nПример: `123456789 5`",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
        )
    )
    bot.register_next_step_handler(msg, lambda m: admin_give_process(m, "take"))

def admin_give_process(message, action):
    chat_id = message.chat.id
    admin_id = message.from_user.id
    
    if message.text == "🔙 Назад в меню":
        send_banner_with_menu(chat_id)
        return
    
    try:
        parts = message.text.strip().split()
        target_id = int(parts[0])
        amount = int(parts[1])
        
        if amount <= 0:
            safe_send(chat_id, "❌ Количество должно быть больше 0")
            return
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        target = cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (target_id,)).fetchone()
        
        if not target:
            safe_send(chat_id, "❌ Пользователь не найден")
            conn.close()
            return
        
        if action == "give":
            cursor.execute("UPDATE users SET requests_balance = requests_balance + ? WHERE telegram_id = ?", 
                         (amount, target_id))
            log_request(target_id, admin_id, "give", amount)
            safe_send(chat_id, f"✅ +{amount} запросов пользователю {target_id}")
            try:
                bot.send_message(target_id, f"📥 Вам начислено {amount} запросов!\n📊 Ваш баланс: {target[6] + amount}")
            except:
                pass
        else:
            if target[6] >= amount:
                cursor.execute("UPDATE users SET requests_balance = requests_balance - ? WHERE telegram_id = ?", 
                             (amount, target_id))
                log_request(target_id, admin_id, "take", amount)
                safe_send(chat_id, f"✅ -{amount} запросов у {target_id}")
            else:
                safe_send(chat_id, f"❌ Недостаточно запросов (доступно: {target[6]})")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Ошибка admin_give_process: {e}")
        safe_send(chat_id, "❌ Неверный формат. Используйте: ID и количество через пробел")

@bot.callback_query_handler(func=lambda call: call.data == "admin_sub")
def handle_admin_sub(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "🎫 *Выдать подписку*\n\nВведите ID пользователя и количество дней через пробел:\nПример: `123456789 30`",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
        )
    )
    bot.register_next_step_handler(msg, admin_sub_process)

def admin_sub_process(message):
    chat_id = message.chat.id
    
    if message.text == "🔙 Назад в меню":
        send_banner_with_menu(chat_id)
        return
    
    try:
        parts = message.text.strip().split()
        target_id = int(parts[0])
        days = int(parts[1])
        
        if days <= 0:
            safe_send(chat_id, "❌ Количество дней должно быть больше 0")
            return
        
        if set_subscription(target_id, "admin", days):
            safe_send(chat_id, f"✅ Подписка на {days} дней выдана пользователю {target_id}")
            try:
                bot.send_message(target_id, f"🎫 Вам выдана подписка на {days} дней!\n✨ Теперь у вас безлимитный доступ к пробивам")
            except:
                pass
        else:
            safe_send(chat_id, "❌ Ошибка выдачи подписки")
            
    except Exception as e:
        logger.error(f"Ошибка admin_sub_process: {e}")
        safe_send(chat_id, "❌ Неверный формат. Используйте: ID и количество дней через пробел")

@bot.callback_query_handler(func=lambda call: call.data == "admin_ban")
def handle_admin_ban(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "🚫 *Бан пользователя*\n\nВведите ID пользователя и количество дней через пробел:\nПример: `123456789 7`",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
        )
    )
    bot.register_next_step_handler(msg, admin_ban_process)

def admin_ban_process(message):
    chat_id = message.chat.id
    admin_id = message.from_user.id
    
    if message.text == "🔙 Назад в меню":
        send_banner_with_menu(chat_id)
        return
    
    try:
        parts = message.text.strip().split()
        target_id = int(parts[0])
        days = int(parts[1]) if len(parts) > 1 else 0
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        target = cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (target_id,)).fetchone()
        if not target:
            safe_send(chat_id, "❌ Пользователь не найден")
            conn.close()
            return
        
        if target[12] == 1:
            safe_send(chat_id, "❌ Нельзя забанить владельца")
            conn.close()
            return
        
        cursor.execute("UPDATE users SET is_banned = 1 WHERE telegram_id = ?", (target_id,))
        conn.commit()
        conn.close()
        
        log_action(admin_id, "ban", f"{target_id} на {days if days > 0 else 'навсегда'} дней")
        
        text = f"🚫 Пользователь {target_id} забанен"
        if days > 0:
            text += f" на {days} дней"
        
        safe_send(chat_id, text)
        
        try:
            msg = f"🚫 Вы забанены"
            if days > 0:
                msg += f" на {days} дней"
            msg += "\n\nПо всем вопросам обращайтесь к @xam1m"
            bot.send_message(target_id, msg)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Ошибка admin_ban_process: {e}")
        safe_send(chat_id, "❌ Неверный формат. Используйте: ID [дни]")

@bot.callback_query_handler(func=lambda call: call.data == "admin_unban")
def handle_admin_unban(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "🔓 *Разбан пользователя*\n\nВведите ID пользователя:",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
        )
    )
    bot.register_next_step_handler(msg, admin_unban_process)

def admin_unban_process(message):
    chat_id = message.chat.id
    admin_id = message.from_user.id
    
    if message.text == "🔙 Назад в меню":
        send_banner_with_menu(chat_id)
        return
    
    try:
        target_id = int(message.text.strip())
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 0, warns = 0 WHERE telegram_id = ?", (target_id,))
        conn.commit()
        conn.close()
        
        log_action(admin_id, "unban", str(target_id))
        safe_send(chat_id, f"✅ Пользователь {target_id} разбанен")
        
        try:
            bot.send_message(target_id, "🔓 Вы были разбанены!")
        except:
            pass
            
    except Exception as e:
        logger.error(f"Ошибка admin_unban_process: {e}")
        safe_send(chat_id, "❌ Введите корректный ID")

@bot.callback_query_handler(func=lambda call: call.data == "admin_mute")
def handle_admin_mute(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "🔇 *Мут пользователя*\n\nВведите ID пользователя и количество часов через пробел:\nПример: `123456789 24`",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
        )
    )
    bot.register_next_step_handler(msg, admin_mute_process)

def admin_mute_process(message):
    chat_id = message.chat.id
    admin_id = message.from_user.id
    
    if message.text == "🔙 Назад в меню":
        send_banner_with_menu(chat_id)
        return
    
    try:
        parts = message.text.strip().split()
        target_id = int(parts[0])
        hours = int(parts[1])
        
        if hours <= 0:
            safe_send(chat_id, "❌ Количество часов должно быть больше 0")
            return
        
        until = (datetime.now() + timedelta(hours=hours)).isoformat()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_muted = 1, muted_until = ? WHERE telegram_id = ?", (until, target_id))
        conn.commit()
        conn.close()
        
        log_action(admin_id, "mute", f"{target_id} на {hours} часов")
        safe_send(chat_id, f"✅ Пользователь {target_id} замучен на {hours} часов")
        
        try:
            bot.send_message(target_id, f"🔇 Вы замучены на {hours} часов\n\nПо всем вопросам обращайтесь к @xam1m")
        except:
            pass
            
    except Exception as e:
        logger.error(f"Ошибка admin_mute_process: {e}")
        safe_send(chat_id, "❌ Неверный формат. Используйте: ID часы")

@bot.callback_query_handler(func=lambda call: call.data == "admin_unmute")
def handle_admin_unmute(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "🔊 *Снять мут*\n\nВведите ID пользователя:",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
        )
    )
    bot.register_next_step_handler(msg, admin_unmute_process)

def admin_unmute_process(message):
    chat_id = message.chat.id
    admin_id = message.from_user.id
    
    if message.text == "🔙 Назад в меню":
        send_banner_with_menu(chat_id)
        return
    
    try:
        target_id = int(message.text.strip())
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_muted = 0, muted_until = NULL WHERE telegram_id = ?", (target_id,))
        conn.commit()
        conn.close()
        
        log_action(admin_id, "unmute", str(target_id))
        safe_send(chat_id, f"✅ Снят мут с пользователя {target_id}")
        
        try:
            bot.send_message(target_id, "🔊 С вас снят мут!")
        except:
            pass
            
    except Exception as e:
        logger.error(f"Ошибка admin_unmute_process: {e}")
        safe_send(chat_id, "❌ Введите корректный ID")

@bot.callback_query_handler(func=lambda call: call.data == "admin_warn")
def handle_admin_warn(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "⚠️ *Выдать варн*\n\nВведите ID пользователя:",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
        )
    )
    bot.register_next_step_handler(msg, admin_warn_process)

def admin_warn_process(message):
    chat_id = message.chat.id
    admin_id = message.from_user.id
    
    if message.text == "🔙 Назад в меню":
        send_banner_with_menu(chat_id)
        return
    
    try:
        target_id = int(message.text.strip())
        
        result = add_warn(target_id)
        
        if result == "ban":
            safe_send(chat_id, f"⚠️ Пользователь {target_id} получил 3/3 варнов и забанен на 7 дней!")
            try:
                bot.send_message(target_id, "⚠️ Вы получили 3/3 варнов и забанены на 7 дней!\n\nПо всем вопросам обращайтесь к @xam1m")
            except:
                pass
        elif result is not None:
            safe_send(chat_id, f"⚠️ Пользователю {target_id} выдан варн ({result}/3)")
            try:
                bot.send_message(target_id, f"⚠️ Вы получили варн! ({result}/3)\nПри 3/3 — бан на 7 дней")
            except:
                pass
        
        log_action(admin_id, "warn", f"{target_id} -> {result}")
            
    except Exception as e:
        logger.error(f"Ошибка admin_warn_process: {e}")
        safe_send(chat_id, "❌ Введите корректный ID")

@bot.callback_query_handler(func=lambda call: call.data == "admin_unwarn")
def handle_admin_unwarn(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "✅ *Снять варн*\n\nВведите ID пользователя:",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
        )
    )
    bot.register_next_step_handler(msg, admin_unwarn_process)

def admin_unwarn_process(message):
    chat_id = message.chat.id
    admin_id = message.from_user.id
    
    if message.text == "🔙 Назад в меню":
        send_banner_with_menu(chat_id)
        return
    
    try:
        target_id = int(message.text.strip())
        
        result = remove_warn(target_id)
        
        if result is not None:
            safe_send(chat_id, f"✅ Снят варн с пользователя {target_id} (осталось: {result}/3)")
            try:
                bot.send_message(target_id, f"✅ С вас снят варн! (осталось: {result}/3)")
            except:
                pass
        
        log_action(admin_id, "unwarn", str(target_id))
            
    except Exception as e:
        logger.error(f"Ошибка admin_unwarn_process: {e}")
        safe_send(chat_id, "❌ Введите корректный ID")

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def handle_admin_users(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    users = get_all_users()
    total = len(users)
    banned = sum(1 for u in users if u.get('is_banned'))
    admins = sum(1 for u in users if u.get('is_admin'))
    owners = sum(1 for u in users if u.get('is_owner'))
    with_sub = sum(1 for u in users if has_subscription(u.get('telegram_id')))
    
    text = (
        "📊 *Список пользователей*\n\n"
        f"👤 Всего: {total}\n"
        f"🚫 Забанено: {banned}\n"
        f"⚙️ Админов: {admins}\n"
        f"👑 Владельцев: {owners}\n"
        f"🎫 С подпиской: {with_sub}\n\n"
        "📋 *Последние 10 пользователей:*\n"
    )
    
    for u in users[-10:]:
        status = "🚫" if u.get('is_banned') else "✅"
        name = f"@{u['username']}" if u.get('username') else f"ID:{u['telegram_id']}"
        text += f"{status} {name} — {u.get('requests_balance', 0)} зап.\n"
    
    m = safe_send(chat_id, text, parse_mode="Markdown", 
                  reply_markup=types.InlineKeyboardMarkup().add(
                      types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
                  ))
    if m:
        last_menu_msg[chat_id] = m.message_id

@bot.callback_query_handler(func=lambda call: call.data == "admin_mail")
def handle_admin_mail(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "📢 *Рассылка*\n\nВведите текст рассылки:",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
        )
    )
    bot.register_next_step_handler(msg, admin_mail_process)

def admin_mail_process(message):
    chat_id = message.chat.id
    admin_id = message.from_user.id
    
    if message.text == "🔙 Назад в меню":
        send_banner_with_menu(chat_id)
        return
    
    text = message.text
    users = get_all_users()
    
    if not users:
        safe_send(chat_id, "❌ Нет пользователей для рассылки")
        return
    
    safe_send(chat_id, f"🔄 Рассылка {len(users)} пользователям...")
    
    sent = 0
    for user in users:
        try:
            if not user.get('is_banned'):
                bot.send_message(user['telegram_id'], f"📢 *Рассылка*\n\n{text}", parse_mode="Markdown")
                sent += 1
                time.sleep(0.05)
        except:
            pass
    
    log_action(admin_id, "mail", f"Отправлено {sent} сообщений")
    safe_send(chat_id, f"✅ Отправлено: {sent} из {len(users)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_account")
def handle_admin_account(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "🛒 *Выдать аккаунт*\n\nВведите ID пользователя и страну через пробел:\nДоступные страны: Индия, США\nПример: `123456789 Индия`",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
        )
    )
    bot.register_next_step_handler(msg, admin_account_process)

def admin_account_process(message):
    chat_id = message.chat.id
    admin_id = message.from_user.id
    
    if message.text == "🔙 Назад в меню":
        send_banner_with_menu(chat_id)
        return
    
    try:
        parts = message.text.strip().split()
        target_id = int(parts[0])
        country = " ".join(parts[1:])
        
        log_action(admin_id, "give_account", f"{target_id} - {country}")
        
        safe_send(chat_id, f"✅ Аккаунт ({country}) выдан пользователю {target_id}")
        try:
            bot.send_message(target_id, f"🛒 Вам выдан аккаунт: {country}!\n📝 Для получения данных обратитесь к @xam1m")
        except:
            pass
            
    except Exception as e:
        logger.error(f"Ошибка admin_account_process: {e}")
        safe_send(chat_id, "❌ Неверный формат. Используйте: ID и страну через пробел")

@bot.callback_query_handler(func=lambda call: call.data == "admin_price")
def handle_admin_price(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    text = "💰 *Изменение цен*\n\n"
    for key, value in PRICES.items():
        name = key.replace("_", " ").title()
        text += f"• {name}: {value}₽\n"
    
    text += "\n📝 Введите название услуги и новую цену через пробел:\nПример: `requests_3 99`"
    
    msg = safe_send(chat_id, text, parse_mode="Markdown",
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
                    ))
    bot.register_next_step_handler(msg, admin_price_process)

def admin_price_process(message):
    chat_id = message.chat.id
    
    if message.text == "🔙 Назад в меню":
        send_banner_with_menu(chat_id)
        return
    
    try:
        parts = message.text.strip().split()
        service = parts[0]
        price = int(parts[1])
        
        if service in PRICES:
            PRICES[service] = price
            safe_send(chat_id, f"✅ Цена для {service} изменена на {price}₽")
        else:
            safe_send(chat_id, f"❌ Услуга '{service}' не найдена")
            
    except Exception as e:
        logger.error(f"Ошибка admin_price_process: {e}")
        safe_send(chat_id, "❌ Неверный формат. Используйте: услуга цена")

@bot.callback_query_handler(func=lambda call: call.data == "admin_ref_link")
def handle_admin_ref_link(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "🔗 *Реферальная ссылка пользователя*\n\nВведите ID пользователя:",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
        )
    )
    bot.register_next_step_handler(msg, admin_ref_link_process)

def admin_ref_link_process(message):
    chat_id = message.chat.id
    
    if message.text == "🔙 Назад в меню":
        send_banner_with_menu(chat_id)
        return
    
    try:
        target_id = int(message.text.strip())
        user = get_user(target_id)
        
        if not user:
            safe_send(chat_id, "❌ Пользователь не найден")
            return
        
        ref_link = get_ref_link(target_id)
        safe_send(chat_id, f"🔗 Реферальная ссылка пользователя {target_id}:\n`{ref_link}`")
        
    except Exception as e:
        logger.error(f"Ошибка admin_ref_link_process: {e}")
        safe_send(chat_id, "❌ Введите корректный ID")

@bot.callback_query_handler(func=lambda call: call.data == "admin_ref_stats")
def handle_admin_ref_stats(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM referrals")
        total_refs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM referrals WHERE purchase_made = 1")
        purchases = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(ref_earned) FROM users WHERE ref_earned > 0")
        total_bonuses = cursor.fetchone()[0] or 0
        
        conn.close()
        
        text = (
            "📊 *Реферальная статистика*\n\n"
            f"👤 Всего рефералов: {total_refs}\n"
            f"💳 Совершили покупку: {purchases}\n"
            f"🎁 Выдано бонусов: {total_bonuses}\n"
        )
        
        safe_send(chat_id, text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка admin_ref_stats: {e}")
        safe_send(chat_id, "❌ Ошибка получения статистики")

@bot.callback_query_handler(func=lambda call: call.data == "admin_ref_top")
def handle_admin_ref_top(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT telegram_id, username, ref_earned 
            FROM users 
            WHERE ref_earned > 0 
            ORDER BY ref_earned DESC 
            LIMIT 10
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            safe_send(chat_id, "📊 Нет данных о рефералах")
            return
        
        text = "🏆 *Топ-10 пользователей по рефералам*\n\n"
        for i, row in enumerate(rows, 1):
            name = f"@{row[1]}" if row[1] else f"ID:{row[0]}"
            text += f"{i}. {name} — {row[2]} бонусов\n"
        
        safe_send(chat_id, text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка admin_ref_top: {e}")
        safe_send(chat_id, "❌ Ошибка получения топа")

@bot.callback_query_handler(func=lambda call: call.data == "admin_msg")
def handle_admin_msg(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "📝 *Личное сообщение*\n\nВведите ID пользователя и текст через пробел:\nПример: `123456789 Привет!`",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="menu_admin")
        )
    )
    bot.register_next_step_handler(msg, admin_msg_process)

def admin_msg_process(message):
    chat_id = message.chat.id
    admin_id = message.from_user.id
    
    if message.text == "🔙 Назад в меню":
        send_banner_with_menu(chat_id)
        return
    
    try:
        parts = message.text.strip().split(maxsplit=1)
        target_id = int(parts[0])
        text = parts[1] if len(parts) > 1 else ""
        
        if not text:
            safe_send(chat_id, "❌ Введите текст сообщения")
            return
        
        bot.send_message(target_id, f"📝 *Сообщение от администратора:*\n\n{text}", parse_mode="Markdown")
        log_action(admin_id, "msg", f"{target_id}: {text[:50]}...")
        safe_send(chat_id, f"✅ Сообщение отправлено пользователю {target_id}")
        
    except Exception as e:
        logger.error(f"Ошибка admin_msg_process: {e}")
        safe_send(chat_id, "❌ Неверный формат. Используйте: ID и текст через пробел")

# ================== ЛОГ-ПАНЕЛЬ ==================

@bot.callback_query_handler(func=lambda call: call.data == "menu_logs")
def handle_menu_logs(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    text = "📋 *Лог-панель*\n\nВыберите действие:"
    m = safe_send(chat_id, text, parse_mode="Markdown", reply_markup=get_logs_menu())
    if m:
        last_menu_msg[chat_id] = m.message_id

@bot.callback_query_handler(func=lambda call: call.data == "log_requests")
def handle_log_requests(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM request_logs 
            ORDER BY timestamp DESC 
            LIMIT 50
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            safe_send(chat_id, "📊 Нет записей в логе")
            return
        
        text = "📊 *Лог выдач запросов (последние 50)*\n\n"
        for row in rows:
            text += f"🕐 {row[4]} | {row[2]} | {row[1]} | {row[3]}\n"
        
        safe_send(chat_id, text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка log_requests: {e}")
        safe_send(chat_id, "❌ Ошибка получения лога")

@bot.callback_query_handler(func=lambda call: call.data == "log_time")
def handle_log_time(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    try:
        day_ago = (datetime.now() - timedelta(hours=24)).isoformat()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM action_logs 
            WHERE timestamp > ? 
            ORDER BY timestamp DESC 
            LIMIT 100
        ''', (day_ago,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            safe_send(chat_id, "📊 Нет действий за последние 24 часа")
            return
        
        text = "⏱️ *Действия за 24 часа (последние 100)*\n\n"
        for row in rows:
            text += f"🕐 {row[3]} | {row[1]} | {row[2]}\n"
        
        safe_send(chat_id, text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка log_time: {e}")
        safe_send(chat_id, "❌ Ошибка получения лога")

@bot.callback_query_handler(func=lambda call: call.data == "log_all")
def handle_log_all(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM action_logs 
            ORDER BY timestamp DESC 
            LIMIT 100
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            safe_send(chat_id, "📊 Нет записей в логе")
            return
        
        text = "📋 *Полный лог (последние 100)*\n\n"
        for row in rows:
            text += f"🕐 {row[3]} | {row[1]} | {row[2]}\n"
        
        safe_send(chat_id, text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка log_all: {e}")
        safe_send(chat_id, "❌ Ошибка получения лога")

@bot.callback_query_handler(func=lambda call: call.data == "log_ref")
def handle_log_ref(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS and user_id != OWNER_ID:
        safe_answer_callback(call, "🚫 У вас нет прав!", show_alert=True)
        return
    
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM ref_logs 
            ORDER BY timestamp DESC 
            LIMIT 50
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            safe_send(chat_id, "📊 Нет записей в логе рефералов")
            return
        
        text = "🔗 *Лог рефералов (последние 50)*\n\n"
        for row in rows:
            text += f"🕐 {row[3]} | {row[1]} -> {row[2]} | {row[4]}\n"
        
        safe_send(chat_id, text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка log_ref: {e}")
        safe_send(chat_id, "❌ Ошибка получения лога")

# ================== ПРОМОКОДЫ ==================

@bot.callback_query_handler(func=lambda call: call.data == "menu_promo")
def handle_menu_promo(call):
    chat_id = call.message.chat.id
    
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    msg = safe_send(
        chat_id,
        "🎁 *Введите промокод:*\n\n"
        "💡 Тестовый промокод: `WAVEDATA2026`\n"
        "Введите код и отправьте сообщение:",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main")
        )
    )
    bot.register_next_step_handler(msg, process_promo)

def process_promo(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    code = message.text.strip().upper()
    
    if code == "⬅️ НАЗАД":
        send_banner_with_menu(chat_id, user_id=user_id)
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM promocodes WHERE upper(code) = ? AND is_active = 1", (code,))
        promo = cursor.fetchone()
        
        if not promo:
            safe_send(chat_id, f"❌ Промокод `{code}` не найден или неактивен")
            send_banner_with_menu(chat_id, user_id=user_id)
            conn.close()
            return
        
        cursor.execute("SELECT * FROM promo_usage WHERE user_id = ? AND promo_id = ?", (user_id, promo[0]))
        if cursor.fetchone():
            safe_send(chat_id, "❌ Вы уже использовали этот промокод")
            send_banner_with_menu(chat_id, user_id=user_id)
            conn.close()
            return
        
        used_count = int(promo[4]) if promo[4] is not None else 0
        max_uses = int(promo[5]) if promo[5] is not None else 1
        
        if used_count >= max_uses:
            safe_send(chat_id, f"❌ Промокод исчерпан (использован {used_count} из {max_uses} раз)")
            send_banner_with_menu(chat_id, user_id=user_id)
            conn.close()
            return
        
        requests_amount = int(promo[2]) if promo[2] is not None else 0
        sub_days = int(promo[3]) if promo[3] is not None else 0
        
        cursor.execute("INSERT INTO promo_usage (user_id, promo_id) VALUES (?, ?)", (user_id, promo[0]))
        
        if requests_amount > 0:
            cursor.execute("UPDATE users SET requests_balance = requests_balance + ? WHERE telegram_id = ?", 
                         (requests_amount, user_id))
        
        if sub_days > 0:
            set_subscription(user_id, "promo", sub_days)
        
        cursor.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE id = ?", (promo[0],))
        conn.commit()
        conn.close()
        
        user = get_user(user_id)
        balance = user.get('requests_balance', 0) if user else 0
        
        text = "✅ *Промокод активирован!*\n\n"
        if requests_amount > 0:
            text += f"➕ +{requests_amount} запросов\n"
        if sub_days > 0:
            text += f"🎫 +{sub_days} дней подписки\n"
        text += f"\n📊 *Ваш баланс:* {balance} запросов"
        
        safe_send(chat_id, text, parse_mode="Markdown")
        send_banner_with_menu(chat_id, user_id=user_id)
        
    except Exception as e:
        logger.error(f"Ошибка активации промокода: {e}")
        safe_send(chat_id, "❌ Ошибка активации промокода")

# ================== АККАУНТЫ ==================

@bot.callback_query_handler(func=lambda call: call.data == "menu_accounts")
def handle_menu_accounts(call):
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    text = (
        "🛒 *Аккаунты и прокси*\n\n"
        "🇮🇳 *Индия / Мьянма* — 30₽ (80% риск слета)\n"
        "🇺🇸 *США* — 100₽ (0% риск)\n\n"
        "🛒 *Прокси для Telegram* — 100₽ (без ВПН, навсегда)\n\n"
        "📝 *Для получения обращайтесь к @xam1m*"
    )
    
    m = safe_send(chat_id, text, parse_mode="Markdown", reply_markup=get_accounts_menu())
    if m:
        last_menu_msg[chat_id] = m.message_id

@bot.callback_query_handler(func=lambda call: call.data.startswith("account_"))
def handle_account(call):
    chat_id = call.message.chat.id
    acc_type = call.data.replace("account_", "")
    
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    names = {
        "india": "🇮🇳 Индия / Мьянма (80% риск)",
        "usa": "🇺🇸 США (0% риск)",
        "proxy": "🛒 Прокси для Telegram"
    }
    
    price = PRICES.get(f"account_{acc_type}", 0) if acc_type != "proxy" else PRICES.get("proxy", 0)
    
    text = (
        f"🛒 *{names.get(acc_type, acc_type)}*\n\n"
        f"💰 Цена: {price}₽\n\n"
        "📝 *Для заказа обращайтесь к @xam1m*\n\n"
        f"💳 *Оплата:* {PAYMENT_LINK}"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 Оплатить", url=PAYMENT_LINK))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="menu_accounts"))
    
    safe_send(chat_id, text, parse_mode="Markdown", reply_markup=markup)

# ================== ЗАПУСК ==================

if __name__ == "__main__":
    print("🌊 DofaminovSearch Bot запускается...")
    print("📦 Инициализация базы данных...")
    
    if not init_db():
        print("❌ Ошибка инициализации БД!")
        sys.exit(1)
    
    print("✅ База данных готова")
    print("🤖 Бот запущен!")
    print(f"👑 Владелец: {OWNER_ID}")
    print(f"⚙️ Админы: {ADMIN_IDS}")
    print("=" * 50)
    print("📦 Модули поиска:")
    print("  • BigBase API")
    print("  • DepSearch API")
    print("  • Комбинированный поиск")
    print("  • Детальные HTML-отчеты")
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)