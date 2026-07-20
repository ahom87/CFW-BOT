"""
ربات مدیریت گروه تلگرام - نسخه تک‌فایلی (ادغام‌شده)
این فایل به‌صورت خودکار از پروژه‌ی چندفایلی ادغام شده است.
"""

from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime
import jdatetime
import pytz
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from telegram import Update, ChatMember
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import TelegramError
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from datetime import datetime, timedelta  # اضافه کردن این خط
import asyncio
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, MessageHandler, filters, Application
from telegram.error import BadRequest
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import sys
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import uuid
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
import io
from PIL import Image, ImageDraw, ImageFont
import random
from logging.handlers import RotatingFileHandler
from types import SimpleNamespace
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

load_dotenv()

# ======================================================================
# بخش: config.py
# ======================================================================
# Load environment variables

BOT_TOKEN = os.getenv("BOT_TOKEN")  # از Environment Variable در Railway خونده میشه
ADMIN_ID = 6443963679 # آیدی عددی ادمین اصلی را اینجا قرار دهید

# Group management settings
MAX_WARNINGS = 3

# Subscription settings
SUBSCRIPTION_CONTACT_ID = int(os.getenv("SUBSCRIPTION_CONTACT_ID", "987654321"))  # آیدی عددی خریدار اشتراک
SUBSCRIPTION_CONTACT_USERNAME = os.getenv("SUBSCRIPTION_CONTACT_USERNAME", "admin_username")  # نام کاربری برای نمایش

# Premium subscription plans (in Toman)
SUBSCRIPTION_PLANS = {
    "monthly": {"name": "ماهانه", "days": 30, "price": 50000},
    "quarterly": {"name": "سه ماهه", "days": 90, "price": 120000},
    "semi_annual": {"name": "شش ماهه", "days": 180, "price": 200000},
    "annual": {"name": "سالانه", "days": 365, "price": 350000}
}

# Commands that require premium subscription
PREMIUM_REQUIRED_COMMANDS = [
    "warn", "unwarn", "admin", "locktime", "unlocktime", "forcejoin", "unforcejoin"
]

# Features that require premium subscription
PREMIUM_FEATURES = {
    "welcome_message": True,     # پیام خوش‌آمدگویی
    "anti_link": True,           # ضد لینک
    "anti_profanity": True,      # ضد فحش
    "warning_system": True,      # سیستم اخطار
    "force_join": True,          # جوین اجباری
    "time_lock": True,           # قفل زمانی
    "broadcast": True            # ارسال پیام همگانی
}

# Time lock settings
TIME_LOCK_DURATIONS = {
    "5m": 300,      # 5 minutes
    "10m": 600,     # 10 minutes
    "30m": 1800,    # 30 minutes
    "1h": 3600,     # 1 hour
    "2h": 7200,     # 2 hours
    "6h": 21600,    # 6 hours
    "12h": 43200,   # 12 hours
    "24h": 86400    # 24 hours
}

# Database Configuration
DATABASE_NAME = "group_manager.db"

# Bot Settings
WELCOME_MESSAGE = "به گروه خوش آمدید! 👋"

# ======================================================================
# بخش: currency_api.py
# ======================================================================
class FullCurrencyAPI:
    """
    A class to fetch and provide currency exchange rates, cryptocurrency prices, and gold prices
    using free public APIs with proper conversion to Iranian Toman.
    """
    
    def __init__(self):
        """Initialize the FullCurrencyAPI with default values and settings."""
        self.last_update = datetime.now()
        self.cache_duration = 900  
        self.cached_data = None
        self.logger = self._setup_logger()
        self.api_sources = {
            "currencies": "https://open.er-api.com/v6/latest/USD",
            "crypto": "https://api.coingecko.com/api/v3/simple/price",
            "gold": "https://www.goldapi.io/api/XAU/USD"
        }

        self.usd_to_toman_rate = 83535  
        
    def _setup_logger(self):
        """Set up and configure logger for the class."""
        logger = logging.getLogger('FullCurrencyAPI')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _get_iran_datetime(self):
        """Get current date and time in Iran timezone."""
        tehran_tz = pytz.timezone('Asia/Tehran')
        now = datetime.now(tehran_tz)
        

        j_date = jdatetime.datetime.fromgregorian(datetime=now)
        persian_date = j_date.strftime("%A %d %B %Y")
        persian_time = now.strftime("%H:%M")
        
        return persian_date, persian_time

    def _fetch_usd_to_toman_rate(self):
        """Fetch the USD to Iranian Toman exchange rate from bonbast.com API-like sources."""
        try:
            response = requests.get("https://api.nobitex.ir/market/stats",
                                    headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            data = response.json()
            

            if 'stats' in data and 'USDT_IRR' in data['stats']:
                usdt_to_irr = float(data['stats']['USDT_IRR']['latest'])

                return int(usdt_to_irr / 10)
            
            return self.usd_to_toman_rate 
        except Exception as e:
            self.logger.error(f"Error fetching USD to Toman rate: {str(e)}")
            return self.usd_to_toman_rate

    def _fetch_currency_rates(self):
        """Fetch currency exchange rates and convert to Iranian Toman."""
        try:

            self.usd_to_toman_rate = self._fetch_usd_to_toman_rate()
            

            response = requests.get(self.api_sources["currencies"])
            response.raise_for_status()
            data = response.json()
            

            currencies = {
                "usd": {"name": "دلار آمریکا", "price": f"{self.usd_to_toman_rate:,}", "flag": "🇺🇸"},
                "eur": {"name": "یورو اروپا", 
                       "price": f"{int(self.usd_to_toman_rate / data['rates']['EUR']):,}", 
                       "flag": "🇪🇺"},
                "gbp": {"name": "پوند انگلیس", 
                       "price": f"{int(self.usd_to_toman_rate / data['rates']['GBP']):,}", 
                       "flag": "🇬🇧"},
                "chf": {"name": "فرانک سوئیس", 
                       "price": f"{int(self.usd_to_toman_rate / data['rates']['CHF']):,}", 
                       "flag": "🇨🇭"},
                "cad": {"name": "دلار کانادا", 
                       "price": f"{int(self.usd_to_toman_rate / data['rates']['CAD']):,}", 
                       "flag": "🇨🇦"},
                "try": {"name": "لیر ترکیه", 
                       "price": f"{int(self.usd_to_toman_rate / data['rates']['TRY']):,}", 
                       "flag": "🇹🇷"},
                "rub": {"name": "روبل روسیه", 
                       "price": f"{int(self.usd_to_toman_rate / data['rates']['RUB']):,}", 
                       "flag": "🇷🇺"},
                "cny": {"name": "یوان چین", 
                       "price": f"{int(self.usd_to_toman_rate / data['rates']['CNY']):,}", 
                       "flag": "🇨🇳"},
                "aed": {"name": "درهم امارات", 
                       "price": f"{int(self.usd_to_toman_rate / data['rates']['AED']):,}", 
                       "flag": "🇦🇪"},
                "iqd": {"name": "دینار عراق", 
                       "price": f"{int(self.usd_to_toman_rate / data['rates']['IQD']):,}", 
                       "flag": "🇮🇶"},
                "afn": {"name": "افغانی", 
                       "price": f"{int(self.usd_to_toman_rate / data['rates']['AFN']):,}", 
                       "flag": "🇦🇫"}
            }
            
            return currencies
        except Exception as e:
            self.logger.error(f"Error fetching currency rates: {str(e)}")
            return self._get_fallback_currencies()

    def _fetch_crypto_prices(self):
        """Fetch cryptocurrency prices and convert to USD and Toman."""
        try:
            params = {
                'ids': 'bitcoin,ethereum,litecoin,binancecoin,solana,cardano,tether,xrp,tron,dogecoin,shiba-inu,pepe,bonk,floki,ton,cake',
                'vs_currencies': 'usd'
            }
            response = requests.get(self.api_sources["crypto"], params=params)
            response.raise_for_status()
            data = response.json()
            

            usdt_toman_price = f"{self.usd_to_toman_rate:,}"
            

            crypto = {
                "usdt": {"name": "تتر", "price": usdt_toman_price, "symbol": "💵"},
                "btc": {"name": "بیت کوین", "price": f"{data['bitcoin']['usd']:,.0f}", "symbol": "💰"},
                "eth": {"name": "اتریوم", "price": f"{data['ethereum']['usd']:,.0f}", "symbol": "💰"},
                "bnb": {"name": "بایننس کوین", "price": f"{data['binancecoin']['usd']:,.2f}", "symbol": "💰"},
                "sol": {"name": "سولانا", "price": f"{data['solana']['usd']:,.2f}", "symbol": "💰"},
                "ada": {"name": "کاردانو", "price": f"{data['cardano']['usd']:,.4f}", "symbol": "💰"},
                "xrp": {"name": "ریپل", "price": f"{data['xrp']['usd']:,.4f}", "symbol": "💰"},
                "trx": {"name": "ترون", "price": f"{data['tron']['usd']:,.4f}", "symbol": "💰"},
                "doge": {"name": "دوج کوین", "price": f"{data['dogecoin']['usd']:,.4f}", "symbol": "💰"},
                "shib": {"name": "شیبا", "price": f"{data['shiba-inu']['usd']:.7f}", "symbol": "💰"},
                "pepe": {"name": "پپه", "price": f"{data['pepe']['usd']:.7f}", "symbol": "💰"},
                "bonk": {"name": "بونک", "price": f"{data['bonk']['usd']:.7f}", "symbol": "💰"},
                "floki": {"name": "فلوکی اینو", "price": f"{data['floki']['usd']:.7f}", "symbol": "💰"},
                "ton": {"name": "تون کوین", "price": f"{data['ton']['usd']:,.2f}", "symbol": "💰"},
                "cake": {"name": "پنکیک سواپ", "price": f"{data['cake']['usd']:,.2f}", "symbol": "💰"}
            }
            
            return crypto
        except Exception as e:
            self.logger.error(f"Error fetching crypto prices: {str(e)}")
            return self._get_fallback_crypto()

    def _fetch_gold_prices(self):
        """Fetch gold prices and convert to Iranian Toman."""
        try:

            response = requests.get("https://api.metals.live/v1/spot")
            response.raise_for_status()
            data = response.json()
            
            gold_price_usd = next((item for item in data if "gold" in item), {"price": 2000})["price"]
            

            gold_price_toman = gold_price_usd * self.usd_to_toman_rate
            gold_gram_price_toman = gold_price_toman / 31.1034768  
            gold_mithqal_price_toman = gold_gram_price_toman * 4.25  
            

            coin_premium = 1.15  
            
            gold = {
                "coin": {"name": "سکه", "price": f"{int(gold_gram_price_toman * 8.133 * coin_premium):,}"},  # Emami coin weight
                "mesghal": {"name": "هر مثقال طلا", "price": f"{int(gold_mithqal_price_toman):,}"},
                "gram": {"name": "هر گرم طلا", "price": f"{int(gold_gram_price_toman):,}"},
                "ounce": {"name": "انس طلا", "price": f"{int(gold_price_usd):,}"}
            }
            
            return gold, gold_price_usd
        except Exception as e:
            self.logger.error(f"Error fetching gold prices: {str(e)}")
            return self._get_fallback_gold()

    def _format_price(self, price_value):
        """Format price value to string with thousands separator."""
        if isinstance(price_value, (int, float)):
            if price_value > 1:
                return f"{price_value:,.0f}" if price_value > 100 else f"{price_value:,.3f}"
            return f"{price_value:.7f}".rstrip('0').rstrip('.')
        return str(price_value)

    def _get_fallback_currencies(self):
        """Provide fallback currency data when API fails."""
        return {
            "usd": {"name": "دلار آمریکا", "price": "83,535", "flag": "🇺🇸"},
            "eur": {"name": "یورو اروپا", "price": "97,020", "flag": "🇪🇺"},
            "gbp": {"name": "پوند انگلیس", "price": "113,620", "flag": "🇬🇧"},
            "chf": {"name": "فرانک سوئیس", "price": "102,980", "flag": "🇨🇭"},
            "cad": {"name": "دلار کانادا", "price": "61,320", "flag": "🇨🇦"},
            "try": {"name": "لیر ترکیه", "price": "2,120", "flag": "🇹🇷"},
            "rub": {"name": "روبل روسیه", "price": "1,047", "flag": "🇷🇺"},
            "cny": {"name": "یوان چین", "price": "11,650", "flag": "🇨🇳"},
            "iqd": {"name": "دینار عراق", "price": "58", "flag": "🇮🇶"},
            "aed": {"name": "درهم امارات", "price": "22,847", "flag": "🇦🇪"},
            "afn": {"name": "افغانی", "price": "1,207", "flag": "🇦🇫"}
        }

    def _get_fallback_crypto(self):
        """Provide fallback cryptocurrency data when API fails."""
        return {
            "usdt": {"name": "تتر", "price": "83,535", "symbol": "💵"}, 
            "btc": {"name": "بیت کوین", "price": "105,588", "symbol": "💰"},
            "eth": {"name": "اتریوم", "price": "2,553", "symbol": "💰"},
            "bnb": {"name": "بایننس کوین", "price": "653.94", "symbol": "💰"},
            "sol": {"name": "سولانا", "price": "147.32", "symbol": "💰"},
            "ada": {"name": "کاردانو", "price": "0.6382", "symbol": "💰"},
            "xrp": {"name": "ریپل", "price": "2.1487", "symbol": "💰"},
            "trx": {"name": "ترون", "price": "0.2696", "symbol": "💰"},
            "doge": {"name": "دوج کوین", "price": "0.1781", "symbol": "💰"},
            "shib": {"name": "شیبا", "price": "0.0000119", "symbol": "💰"},
            "pepe": {"name": "پپه", "price": "0.0000109", "symbol": "💰"},
            "bonk": {"name": "بونک", "price": "0.0000149", "symbol": "💰"},
            "floki": {"name": "فلوکی اینو", "price": "0.0000789", "symbol": "💰"},
            "ton": {"name": "تون کوین", "price": "2.99", "symbol": "💰"},
            "cake": {"name": "پنکیک سواپ", "price": "2.43", "symbol": "💰"}
        }

    def _get_fallback_gold(self):
        """Provide fallback gold data when API fails."""
        gold = {
            "coin": {"name": "سکه", "price": "75,890,000"},
            "mesghal": {"name": "هر مثقال طلا", "price": "29,346,000"},
            "gram": {"name": "هر گرم طلا", "price": "6,774,100"},
            "ounce": {"name": "انس طلا", "price": "3,427"}
        }
        return gold, 3427

    def get_current_rates(self):
        """
        Get the current exchange rates for currencies, cryptocurrency, and gold.
        Uses cached data if available and not expired.
        """
        current_time = datetime.now()
        

        if self.cached_data and (current_time - self.last_update).total_seconds() < self.cache_duration:
            self.logger.info("Using cached exchange rates")
            return self.cached_data
        
        self.logger.info("Fetching new exchange rates")
        

        persian_date, persian_time = self._get_iran_datetime()
        
        try:

            currencies = self._fetch_currency_rates()
            crypto = self._fetch_crypto_prices()
            gold, gold_price = self._fetch_gold_prices()
            

            rates = {
                "date": persian_date,
                "time": persian_time,
                "currencies": currencies,
                "gold": gold,
                "crypto": crypto
            }
            
            self.cached_data = rates
            self.last_update = current_time
            
            return rates
        except Exception as e:
            self.logger.error(f"Error getting current rates: {str(e)}")
            

            if self.cached_data:
                return self.cached_data
            else:
                return {
                    "date": persian_date,
                    "time": persian_time,
                    "currencies": self._get_fallback_currencies(),
                    "gold": self._get_fallback_gold()[0],
                    "crypto": self._get_fallback_crypto()
                }

    def format_currency_message(self, rates=None):
        """Format the currency data into a readable message."""
        if rates is None:
            rates = self.get_current_rates()
        
        message = f"""◄ نرخ ارز و طلا در بازار آزاد :
        
• تاریخ : {rates['date']}
• ساعت : {rates['time']}

"""

        for currency_code, currency_data in rates['currencies'].items():
            message += f"• {currency_data['name']} {currency_data['flag']} : {currency_data['price']} تومان\n"
        
        message += "\n~ ~ ~ ~ ~ ~\n"
        

        for gold_code, gold_data in rates['gold'].items():
            message += f"• {gold_data['name']} : {gold_data['price']} تومان\n"
        
        message += "\n~ ~ ~ ~ ~ ~\n"
        message += "◄ قیمت ارزهای دیجیتال:\n\n"
        

        for crypto_code, crypto_data in rates['crypto'].items():
            if crypto_code == "usdt":
                message += f"{crypto_data['symbol']} {crypto_data['name']} : {crypto_data['price']} تومان\n"
            else:
                message += f"{crypto_data['symbol']} {crypto_data['name']} : {crypto_data['price']} دلار\n"
        
        return message 

    def convert_usd_to_toman(self, amount_usd):
        """Convert USD amount to Iranian Toman"""
        self.usd_to_toman_rate = self._fetch_usd_to_toman_rate()
        return amount_usd * self.usd_to_toman_rate
        
    def convert_trx_to_toman(self, amount_trx):
        """Convert TRX (Tron) amount to Iranian Toman"""
        try:
            # Get current TRX price in USD
            params = {'ids': 'tron', 'vs_currencies': 'usd'}
            response = requests.get(self.api_sources["crypto"], params=params)
            response.raise_for_status()
            data = response.json()
            
            trx_to_usd = data['tron']['usd']
            
            # Convert to Toman
            usd_amount = amount_trx * trx_to_usd
            toman_amount = self.convert_usd_to_toman(usd_amount)
            
            return toman_amount
        except Exception as e:
            self.logger.error(f"Error converting TRX to Toman: {str(e)}")
            # Fallback to approximate conversion
            return amount_trx * 0.27 * self.usd_to_toman_rate  # Approximate TRX price in USD
    
    def convert_usdt_to_toman(self, amount_usdt):
        """Convert USDT (Tether) amount to Iranian Toman"""
        # USDT is pegged to USD, so 1 USDT ≈ 1 USD
        return self.convert_usd_to_toman(amount_usdt)
    
    def convert_gold_to_toman(self, amount_gold_gram):
        """Convert gold amount (in grams) to Iranian Toman"""
        try:
            # Get gold prices
            gold_data, gold_price_usd = self._fetch_gold_prices()
            
            # Calculate price per gram in USD
            gold_gram_price_usd = gold_price_usd / 31.1034768  # Troy ounce to gram
            
            # Convert to Toman
            usd_amount = amount_gold_gram * gold_gram_price_usd
            toman_amount = self.convert_usd_to_toman(usd_amount)
            
            return toman_amount
        except Exception as e:
            self.logger.error(f"Error converting gold to Toman: {str(e)}")
            # Fallback to approximate conversion
            return amount_gold_gram * 70 * self.usd_to_toman_rate  # Approximate gold price per gram in USD 

# ======================================================================
# بخش: database/database.py
# ======================================================================
class Database:
    def __init__(self, db_name):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # Create users table
        c.execute('''CREATE TABLE IF NOT EXISTS users
                    (user_id INTEGER PRIMARY KEY,
                     username TEXT,
                     first_name TEXT,
                     last_name TEXT,
                     warnings INTEGER DEFAULT 0,
                     is_banned BOOLEAN DEFAULT 0,
                     join_date TEXT,
                     last_active TEXT)''')
        
        # Create groups table with more settings
        c.execute('''CREATE TABLE IF NOT EXISTS groups
                    (group_id INTEGER PRIMARY KEY,
                     title TEXT,
                     welcome_enabled BOOLEAN DEFAULT 1,
                     welcome_message TEXT,
                     rules_message TEXT,
                     anti_spam BOOLEAN DEFAULT 1,
                     anti_link BOOLEAN DEFAULT 1,
                     anti_profanity BOOLEAN DEFAULT 1,
                     max_warnings INTEGER DEFAULT 3,
                     is_premium BOOLEAN DEFAULT 0,
                     added_by INTEGER,
                     added_date TEXT,
                     delete_new_members BOOLEAN DEFAULT 0,
                     delete_join_messages BOOLEAN DEFAULT 0,
                     delete_pin_messages BOOLEAN DEFAULT 0,
                     delete_video_chat_messages BOOLEAN DEFAULT 0)''')
        
        # Check and add missing columns to existing tables
        self._update_database_schema()
        
        # Create messages table for analytics
        c.execute('''CREATE TABLE IF NOT EXISTS messages
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     message_id INTEGER,
                     group_id INTEGER,
                     user_id INTEGER,
                     timestamp TEXT,
                     FOREIGN KEY (group_id) REFERENCES groups (group_id),
                     FOREIGN KEY (user_id) REFERENCES users (user_id))''')
        
        # Create warnings table for detailed warning logs
        c.execute('''CREATE TABLE IF NOT EXISTS warnings
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER,
                     group_id INTEGER,
                     reason TEXT,
                     warned_by INTEGER,
                     timestamp TEXT,
                     FOREIGN KEY (user_id) REFERENCES users (user_id),
                     FOREIGN KEY (group_id) REFERENCES groups (group_id))''')
        
        # Create custom buttons table for welcome messages
        c.execute('''CREATE TABLE IF NOT EXISTS custom_buttons
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     group_id INTEGER,
                     button_text TEXT,
                     button_url TEXT,
                     button_order INTEGER,
                     FOREIGN KEY (group_id) REFERENCES groups (group_id))''')
        
        # ایجاد جدول گزارش‌های کاربران
        c.execute('''CREATE TABLE IF NOT EXISTS user_reports
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     group_id INTEGER,
                     reported_user_id INTEGER,
                     reporter_user_id INTEGER,
                     message_id INTEGER,
                     report_text TEXT,
                     status TEXT DEFAULT 'pending',
                     admin_response TEXT,
                     responded_by INTEGER,
                     report_time TEXT,
                     response_time TEXT,
                     FOREIGN KEY (group_id) REFERENCES groups (group_id),
                     FOREIGN KEY (reported_user_id) REFERENCES users (user_id),
                     FOREIGN KEY (reporter_user_id) REFERENCES users (user_id))''')
        
        # ایجاد جدول لقب‌های کاربران
        c.execute('''CREATE TABLE IF NOT EXISTS user_nicknames
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER,
                     group_id INTEGER,
                     nickname TEXT,
                     set_by INTEGER,
                     set_date TEXT,
                     FOREIGN KEY (user_id) REFERENCES users (user_id),
                     FOREIGN KEY (group_id) REFERENCES groups (group_id))''')
        
        conn.commit()
        conn.close()

    def _update_database_schema(self):
        """به‌روزرسانی ساختار دیتابیس و اضافه کردن ستون‌های جدید"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # Check if max_warnings column exists in groups table
        c.execute("PRAGMA table_info(groups)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'max_warnings' not in columns:
            c.execute("ALTER TABLE groups ADD COLUMN max_warnings INTEGER DEFAULT 3")
        
        if 'delete_new_members' not in columns:
            c.execute("ALTER TABLE groups ADD COLUMN delete_new_members BOOLEAN DEFAULT 0")
            
        if 'delete_join_messages' not in columns:
            c.execute("ALTER TABLE groups ADD COLUMN delete_join_messages BOOLEAN DEFAULT 0")
            
        if 'delete_pin_messages' not in columns:
            c.execute("ALTER TABLE groups ADD COLUMN delete_pin_messages BOOLEAN DEFAULT 0")
            
        if 'delete_video_chat_messages' not in columns:
            c.execute("ALTER TABLE groups ADD COLUMN delete_video_chat_messages BOOLEAN DEFAULT 0")
        
        conn.commit()
        conn.close()

    def add_user(self, user_id, username):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, username, join_date) VALUES (?, ?, ?)",
                 (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

    def add_group(self, group_id, title, added_by=None):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        if added_by:
            c.execute("""INSERT OR IGNORE INTO groups 
                        (group_id, title, added_by, added_date) 
                        VALUES (?, ?, ?, ?)""",
                     (group_id, title, added_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        else:
            c.execute("INSERT OR IGNORE INTO groups (group_id, title) VALUES (?, ?)",
                     (group_id, title))
        conn.commit()
        conn.close()

    def set_group_premium(self, group_id, is_premium):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("UPDATE groups SET is_premium = ? WHERE group_id = ?", (is_premium, group_id))
        conn.commit()
        conn.close()

    def is_group_premium(self, group_id):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("SELECT is_premium FROM groups WHERE group_id = ?", (group_id,))
        result = c.fetchone()
        conn.close()
        return bool(result[0]) if result else False

    def get_premium_groups(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("SELECT group_id, title, added_by, added_date FROM groups WHERE is_premium = 1")
        result = c.fetchall()
        conn.close()
        return result

    def get_user_data(self, user_id):
        """دریافت اطلاعات کاربر"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        
        conn.close()
        
        if result:
            return {key: result[key] for key in result.keys()}
        return None

    def count_user_messages(self, user_id, group_id):
        """شمارش تعداد پیام‌های کاربر در گروه"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM messages WHERE user_id = ? AND group_id = ?", (user_id, group_id))
        count = c.fetchone()[0]
        
        conn.close()
        return count

    def get_user_warnings(self, user_id, group_id):
        """دریافت تعداد اخطارهای کاربر در گروه"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ? AND group_id = ?", (user_id, group_id))
        count = c.fetchone()[0]
        
        conn.close()
        return count

    def get_group_max_warnings(self, group_id):
        """دریافت حداکثر تعداد اخطارهای مجاز در گروه"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        c.execute("SELECT max_warnings FROM groups WHERE group_id = ?", (group_id,))
        result = c.fetchone()
        
        conn.close()
        return result[0] if result else 3  # مقدار پیش‌فرض 3

    def get_user_warning_history(self, user_id, group_id):
        """دریافت تاریخچه اخطارهای کاربر در گروه"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute("SELECT * FROM warnings WHERE user_id = ? AND group_id = ? ORDER BY timestamp DESC", (user_id, group_id))
        results = c.fetchall()
        
        conn.close()
        
        if results:
            return [{key: row[key] for key in row.keys()} for row in results]
        return []

    def get_user_activity(self, user_id, group_id):
        """دریافت آمار فعالیت کاربر در 7 روز گذشته"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # محاسبه تاریخ 7 روز قبل
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        # دریافت تعداد پیام‌ها به تفکیک روز
        c.execute("""
            SELECT strftime('%Y-%m-%d', timestamp) as day, COUNT(*) as count
            FROM messages
            WHERE user_id = ? AND group_id = ? AND timestamp >= ?
            GROUP BY day
            ORDER BY day
        """, (user_id, group_id, seven_days_ago))
        
        results = c.fetchall()
        conn.close()
        
        # تبدیل نتایجات به دیکشنری
        activity = {}
        for row in results:
            # تبدیل تاریخ میلادی به شمسی
            try:
                gregorian_date = datetime.strptime(row[0], "%Y-%m-%d")
                jalali_date = jdatetime.datetime.fromgregorian(datetime=gregorian_date)
                day = jalali_date.strftime("%Y/%m/%d")
            except Exception as e:
                day = row[0]
            
            activity[day] = row[1]
        
        return activity

    def get_group_settings(self, group_id):
        """Get all settings for a group"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        c = conn.cursor()
        c.execute("SELECT * FROM groups WHERE group_id = ?", (group_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            # Convert sqlite3.Row to dict
            return {key: result[key] for key in result.keys()}
        return None

    def add_message(self, message_id, group_id, user_id):
        """ثبت پیام در دیتابیس برای آمار و تگ کردن"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("INSERT INTO messages (message_id, group_id, user_id, timestamp) VALUES (?, ?, ?, ?)",
                 (message_id, group_id, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

    def add_user_report(self, group_id, reported_user_id, reporter_user_id, message_id, report_text):
        """ثبت گزارش کاربر"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("INSERT INTO user_reports (group_id, reported_user_id, reporter_user_id, message_id, report_text, report_time) VALUES (?, ?, ?, ?, ?, ?)",
                 (group_id, reported_user_id, reporter_user_id, message_id, report_text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        report_id = c.lastrowid
        conn.commit()
        conn.close()
        return report_id
        
    def update_report_status(self, report_id, status, admin_response, admin_id):
        """به‌روزرسانی وضعیت گزارش"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("UPDATE user_reports SET status = ?, admin_response = ?, responded_by = ?, response_time = ? WHERE id = ?",
                 (status, admin_response, admin_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), report_id))
        conn.commit()
        conn.close()
        
    def get_report_details(self, report_id):
        """دریافت جزئیات گزارش"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM user_reports WHERE id = ?", (report_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            return {key: result[key] for key in result.keys()}
        return None

    def init_admin_abuse_tables(self):
        """ایجاد جداول مربوط به تخلف ادمین‌ها"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # جدول گزارش‌های تخلف ادمین
        c.execute('''CREATE TABLE IF NOT EXISTS admin_abuse_reports
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     group_id INTEGER,
                     admin_id INTEGER,
                     reporter_id INTEGER,
                     message_id INTEGER,
                     report_text TEXT,
                     status TEXT DEFAULT 'pending',
                     admin_response TEXT,
                     responded_by INTEGER,
                     report_time TEXT,
                     response_time TEXT,
                     FOREIGN KEY (group_id) REFERENCES groups (group_id),
                     FOREIGN KEY (admin_id) REFERENCES users (user_id),
                     FOREIGN KEY (reporter_id) REFERENCES users (user_id))''')
        
        # جدول اقدامات ادمین‌ها
        c.execute('''CREATE TABLE IF NOT EXISTS admin_actions
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     admin_id INTEGER,
                     group_id INTEGER,
                     action_type TEXT,
                     timestamp TEXT,
                     FOREIGN KEY (admin_id) REFERENCES users (user_id),
                     FOREIGN KEY (group_id) REFERENCES groups (group_id))''')
        
        conn.commit()
        conn.close()
    
    def add_admin_abuse_report(self, group_id, admin_id, reporter_id, message_id, report_text):
        """ثبت گزارش تخلف ادمین"""
        # ابتدا اطمینان حاصل کنیم که جداول وجود دارند
        self.init_admin_abuse_tables()
        
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("INSERT INTO admin_abuse_reports (group_id, admin_id, reporter_id, message_id, report_text, report_time) VALUES (?, ?, ?, ?, ?, ?)",
                 (group_id, admin_id, reporter_id, message_id, report_text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        report_id = c.lastrowid
        conn.commit()
        conn.close()
        return report_id
    
    def update_admin_abuse_report_status(self, report_id, status, admin_response, responded_by):
        """به‌روزرسانی وضعیت گزارش تخلف ادمین"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("UPDATE admin_abuse_reports SET status = ?, admin_response = ?, responded_by = ?, response_time = ? WHERE id = ?",
                 (status, admin_response, responded_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), report_id))
        conn.commit()
        conn.close()
    
    def get_admin_abuse_report(self, report_id):
        """دریافت جزئیات گزارش تخلف ادمین"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM admin_abuse_reports WHERE id = ?", (report_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            return {key: result[key] for key in result.keys()}
        return None
    
    def add_admin_action(self, admin_id, group_id, action_type):
        """ثبت اقدام ادمین"""
        # ابتدا اطمینان حاصل کنیم که جداول وجود دارند
        self.init_admin_abuse_tables()
        
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("INSERT INTO admin_actions (admin_id, group_id, action_type, timestamp) VALUES (?, ?, ?, ?)",
                 (admin_id, group_id, action_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    
    def count_admin_actions(self, admin_id, group_id, action_type, time_window_seconds):
        """شمارش تعداد اقدامات ادمین در بازه زمانی مشخصص"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # محاسبه زمان شروع بازه
        time_threshold = (datetime.now() - timedelta(seconds=time_window_seconds)).strftime("%Y-%m-%d %H:%M:%S")
        
        c.execute("""SELECT COUNT(*) FROM admin_actions 
                   WHERE admin_id = ? AND group_id = ? AND action_type = ? AND timestamp > ?""",
                 (admin_id, group_id, action_type, time_threshold))
        count = c.fetchone()[0]
        conn.close()
        return count
    
    def get_admin_recent_actions(self, admin_id, group_id):
        """دریافت آمار اقدامات اخیر ادمین"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # محاسبه زمان 30 دقیقه قبل
        time_threshold = (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        # دریافت تعداد هر نوع اقدام
        actions = {}
        
        for action_type in ["ban", "kick", "mute", "delete"]:
            c.execute("""SELECT COUNT(*) FROM admin_actions 
                       WHERE admin_id = ? AND group_id = ? AND action_type = ? AND timestamp > ?""",
                     (admin_id, group_id, action_type, time_threshold))
            count = c.fetchone()[0]
            actions[f"{action_type}_count"] = count
        
        conn.close()
        return actions

    def set_user_nickname(self, user_id, group_id, nickname, set_by):
        """تنظیم لقب برای کاربر در گروه"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # ابتدا بررسی می‌کنیم آیا قبلاً لقبی برای این کاربر در این گروه تنظیم شده است
        c.execute("SELECT id FROM user_nicknames WHERE user_id = ? AND group_id = ?", (user_id, group_id))
        existing = c.fetchone()
        
        if existing:
            # اگر لقب قبلاً وجود داشته، آن را به‌روزرسانی می‌کنیم
            c.execute("UPDATE user_nicknames SET nickname = ?, set_by = ?, set_date = ? WHERE user_id = ? AND group_id = ?",
                     (nickname, set_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id, group_id))
        else:
            # اگر لقب وجود نداشته، یک رکورد جدید اضافه می‌کنیم
            c.execute("INSERT INTO user_nicknames (user_id, group_id, nickname, set_by, set_date) VALUES (?, ?, ?, ?, ?)",
                     (user_id, group_id, nickname, set_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        conn.close()
        return True

    def get_user_nickname(self, user_id, group_id):
        """دریافت لقب کاربر در گروه"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        c.execute("SELECT nickname FROM user_nicknames WHERE user_id = ? AND group_id = ?", (user_id, group_id))
        result = c.fetchone()
        
        conn.close()
        return result[0] if result else None

    def remove_user_nickname(self, user_id, group_id):
        """حذف لقب کاربر در گروه"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        c.execute("DELETE FROM user_nicknames WHERE user_id = ? AND group_id = ?", (user_id, group_id))
        
        conn.commit()
        conn.close()
        return True

    def add_warning(self, user_id, group_id=None, reason="نقض قوانین گروه", warned_by=None):
        """اضافه کردن اخطار به کاربر"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # اگر group_id ارسال نشده، فقط warnings counter را به‌روزرسانی می‌کنیم
        if group_id is None:
            # Legacy support - فقط counter را افزایش می‌دهیم
            c.execute("UPDATE users SET warnings = warnings + 1 WHERE user_id = ?", (user_id,))
        else:
            # ثبت اخطار در جدول warnings
            c.execute("INSERT INTO warnings (user_id, group_id, reason, warned_by, timestamp) VALUES (?, ?, ?, ?, ?)",
                     (user_id, group_id, reason, warned_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            # به‌روزرسانی counter کلی کاربر
            c.execute("UPDATE users SET warnings = warnings + 1 WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()

    def remove_warning(self, user_id, group_id=None):
        """حذف یک اخطار از کاربر"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        if group_id is None:
            # Legacy support - فقط counter را کاهش می‌دهیم
            c.execute("UPDATE users SET warnings = MAX(0, warnings - 1) WHERE user_id = ?", (user_id,))
        else:
            # ابتدا آخرین اخطار را پیدا می‌کنیم
            c.execute("SELECT id FROM warnings WHERE user_id = ? AND group_id = ? ORDER BY timestamp DESC LIMIT 1", 
                     (user_id, group_id))
            result = c.fetchone()
            
            if result:
                # حذف آخرین اخطار
                c.execute("DELETE FROM warnings WHERE id = ?", (result[0],))
                # به‌روزرسانی counter کلی کاربر
                c.execute("UPDATE users SET warnings = MAX(0, warnings - 1) WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()

    def clear_user_warnings(self, user_id, group_id=None):
        """پاک کردن تمام اخطارهای کاربر"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        if group_id is None:
            # پاک کردن تمام اخطارها از همه گروه‌ها
            c.execute("DELETE FROM warnings WHERE user_id = ?", (user_id,))
            c.execute("UPDATE users SET warnings = 0 WHERE user_id = ?", (user_id,))
        else:
            # پاک کردن اخطارهای مربوط به گروه خاص
            c.execute("DELETE FROM warnings WHERE user_id = ? AND group_id = ?", (user_id, group_id))
            
            # بازشماری اخطارهای باقیمانده
            c.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (user_id,))
            remaining_warnings = c.fetchone()[0]
            c.execute("UPDATE users SET warnings = ? WHERE user_id = ?", (remaining_warnings, user_id))
        
        conn.commit()
        conn.close()

    def ban_user(self, user_id):
        """مسدود کردن کاربر"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()

    def unban_user(self, user_id):
        """رفع مسدودیت کاربر"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        c.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()

    def is_user_banned(self, user_id):
        """بررسی مسدود بودن کاربر"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        c.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        
        conn.close()
        return bool(result[0]) if result else False

# ======================================================================
# بخش: database/premium.py
# ======================================================================
logger = logging.getLogger(__name__)

class PremiumManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_tables()

    def init_tables(self):
        """Initialize premium subscription tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Premium groups table
            cursor.execute(''' 
                CREATE TABLE IF NOT EXISTS premium_groups (
                    group_id INTEGER PRIMARY KEY,
                    subscription_start DATE NOT NULL,
                    subscription_end DATE NOT NULL,
                    buyer_id INTEGER NOT NULL,
                    buyer_username TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Subscription plans table
            cursor.execute(''' 
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    duration_days INTEGER NOT NULL,
                    price REAL NOT NULL,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')

            # Insert default subscription plans
            cursor.execute(''' 
                INSERT OR IGNORE INTO subscription_plans (id, name, duration_days, price)
                VALUES 
                    (1, 'ماهانه', 30, 50000),
                    (2, 'سه ماهه', 90, 120000),
                    (3, 'شش ماهه', 180, 200000),
                    (4, 'سالانه', 365, 350000)
            ''')

            conn.commit()
            conn.close()
            logger.info("Premium database tables initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing premium tables: {str(e)}")
            if conn:
                conn.close()

    def is_group_premium(self, group_id: int) -> bool:
        """Check if a group has active premium subscription"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(''' 
                SELECT COUNT(*) FROM premium_groups 
                WHERE group_id = ? AND subscription_end > date('now') AND is_active = 1
            ''', (group_id,))
            
            result = cursor.fetchone()[0] > 0
            conn.close()
            return result

        except Exception as e:
            logger.error(f"Error checking premium status for group {group_id}: {str(e)}")
            return False

    def get_group_subscription_info(self, group_id: int) -> Optional[Dict]:
        """Get subscription information for a group"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(''' 
                SELECT subscription_start, subscription_end, buyer_id, buyer_username, is_active
                FROM premium_groups 
                WHERE group_id = ?
                ORDER BY subscription_end DESC
                LIMIT 1
            ''', (group_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'subscription_start': result[0],
                    'subscription_end': result[1],
                    'buyer_id': result[2],
                    'buyer_username': result[3],
                    'is_active': result[4]
                }
            return None

        except Exception as e:
            logger.error(f"Error getting subscription info for group {group_id}: {str(e)}")
            return None

    def add_premium_subscription(self, group_id: int, buyer_id: int, buyer_username: str, duration_days: int = 30) -> bool:
        """Add premium subscription for a group"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=duration_days)
            
            cursor.execute(''' 
                INSERT OR REPLACE INTO premium_groups 
                (group_id, subscription_start, subscription_end, buyer_id, buyer_username)
                VALUES (?, ?, ?, ?, ?)
            ''', (group_id, start_date, end_date, buyer_id, buyer_username))
            
            conn.commit()
            conn.close()
            logger.info(f"Premium subscription added for group {group_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding premium subscription for group {group_id}: {str(e)}")
            return False

    def get_all_premium_groups(self) -> List[Dict]:
        """Get all premium groups"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(''' 
                SELECT group_id, subscription_start, subscription_end, buyer_id, buyer_username, is_active
                FROM premium_groups 
                ORDER BY subscription_end DESC
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            groups = []
            for result in results:
                groups.append({
                    'group_id': result[0],
                    'subscription_start': result[1],
                    'subscription_end': result[2],
                    'buyer_id': result[3],
                    'buyer_username': result[4],
                    'is_active': result[5]
                })
            
            return groups

        except Exception as e:
            logger.error(f"Error getting all premium groups: {str(e)}")
            return []

    def deactivate_subscription(self, group_id: int) -> bool:
        """Deactivate subscription for a group"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(''' 
                UPDATE premium_groups 
                SET is_active = 0 
                WHERE group_id = ?
            ''', (group_id,))
            
            conn.commit()
            conn.close()
            logger.info(f"Subscription deactivated for group {group_id}")
            return True

        except Exception as e:
            logger.error(f"Error deactivating subscription for group {group_id}: {str(e)}")
            return False

    def get_group_sudo_users(self, group_id: int) -> list:
        """Get list of sudo users for a group"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Check if table exists, if not create it
            c.execute("CREATE TABLE IF NOT EXISTS sudo_users (group_id INTEGER, user_id INTEGER, added_by INTEGER, added_date TEXT, PRIMARY KEY (group_id, user_id))")
            
            c.execute("SELECT user_id FROM sudo_users WHERE group_id = ?", (group_id,))
            results = c.fetchall()
            conn.close()
            
            if results:
                return [user_id[0] for user_id in results]
            return []
        except Exception as e:
            logger.error(f"Error getting sudo users for group {group_id}: {str(e)}")
            return []
    
    def add_sudo_user(self, group_id: int, user_id: int, added_by: int) -> bool:
        """Add a sudo user to a group"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Check if table exists, if not create it
            c.execute("CREATE TABLE IF NOT EXISTS sudo_users (group_id INTEGER, user_id INTEGER, added_by INTEGER, added_date TEXT, PRIMARY KEY (group_id, user_id))")
            
            # Check if user is already a sudo user
            c.execute("SELECT user_id FROM sudo_users WHERE group_id = ? AND user_id = ?", (group_id, user_id))
            if c.fetchone():
                conn.close()
                return False  # User is already a sudo user
            
            # Add user as sudo
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO sudo_users (group_id, user_id, added_by, added_date) VALUES (?, ?, ?, ?)", 
                     (group_id, user_id, added_by, current_date))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error adding sudo user {user_id} to group {group_id}: {str(e)}")
            return False
    
    def remove_sudo_user(self, group_id: int, user_id: int) -> bool:
        """Remove a sudo user from a group"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Check if table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sudo_users'")
            if not c.fetchone():
                conn.close()
                return False
            
            c.execute("DELETE FROM sudo_users WHERE group_id = ? AND user_id = ?", (group_id, user_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error removing sudo user {user_id} from group {group_id}: {str(e)}")
            return False

# ======================================================================
# بخش: middleware/premium_check.py
# ======================================================================
logger = logging.getLogger(__name__)

def check_group_premium_status(group_id: int, premium_cache: set, premium_manager: PremiumManager) -> bool:
    """Check if group has premium status using cache and database"""
    try:
        # First check cache
        if group_id in premium_cache:
            return True
        
        # If not in cache, check database
        is_premium = premium_manager.is_group_premium(group_id)
        
        # Update cache if premium
        if is_premium:
            premium_cache.add(group_id)
        
        return is_premium
        
    except Exception as e:
        logger.error(f"Error checking premium status for group {group_id}: {str(e)}")
        return False

def premium_required(func):
    """Decorator to check if group has premium subscription"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            # Skip premium check for private chats with admin
            if update.effective_chat.type == "private" and update.effective_user.id == ADMIN_ID:
                return await func(update, context, *args, **kwargs)
            
            # Skip premium check for private chats
            if update.effective_chat.type == "private":
                await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
                return
            
            # Initialize premium manager
            premium_manager = PremiumManager("group_manager.db")
            group_id = update.effective_chat.id
            
            # Check if group has premium subscription
            if not premium_manager.is_group_premium(group_id):
                await send_subscription_required_message(update, context, premium_manager, group_id)
                return
            
            # If premium is active, execute the original function
            return await func(update, context, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in premium_required decorator: {str(e)}")
            await update.message.reply_text("خطایی در بررسی وضعیت اشتراک رخ داد.")
    
    return wrapper

# اضافه کردن تابع جدید برای بررسی اینکه آیا کاربر خریدار گروه پرمیوم است یا خیر
def is_premium_buyer(user_id: int, group_id: int, premium_manager: PremiumManager) -> bool:
    """Check if user is the buyer of premium subscription for the group or a sudo user"""
    try:
        # Check if user is the buyer
        subscription_info = premium_manager.get_group_subscription_info(group_id)
        if subscription_info and subscription_info['buyer_id'] == user_id:
            return True
            
        # Check if user is a sudo user
        sudo_users = premium_manager.get_group_sudo_users(group_id)
        if sudo_users and user_id in sudo_users:
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error checking if user {user_id} is premium buyer for group {group_id}: {str(e)}")
        return False

async def send_subscription_required_message(update: Update, context: ContextTypes.DEFAULT_TYPE, premium_manager: PremiumManager, group_id: int):
    """Send subscription required message"""
    try:
        subscription_info = premium_manager.get_group_subscription_info(group_id)
        
        # Create subscription plans text
        plans_text = ""
        for plan_key, plan_info in SUBSCRIPTION_PLANS.items():
            plans_text += f"• *{plan_info['name']}*: `{plan_info['price']:,}` تومان ({plan_info['days']} روز)\n"
        
        if subscription_info and not subscription_info['is_active']:
            # Subscription expired
            message = f"""🔒 *اشتراک این گروه منقضی شده است!*
            
📅 تاریخ انقضا: `{subscription_info['subscription_end']}`
👤 خریدار قبلی: {subscription_info['buyer_username'] or 'نامشخص'} (ID: `{subscription_info['buyer_id']}`)
            
💎 *برای تمدید اشتراک و استفاده از امکانات ربات، لطفاً با ادمین تماس بگیرید:*
👨‍💼 [@{SUBSCRIPTION_CONTACT_USERNAME}](https://t.me/{SUBSCRIPTION_CONTACT_USERNAME})
🆔 آیدی خریدار: `{SUBSCRIPTION_CONTACT_ID}`
            
📋 *پلان‌های اشتراک:*
{plans_text}
🆔 آیدی گروه برای خرید: `{group_id}`"""
        else:
            # No subscription
            message = f"""🔒 *این گروه اشتراک فعال ندارد!*
            
💎 برای استفاده از امکانات ربات، نیاز به خرید اشتراک دارید.
            
👨‍💼 *برای خرید اشتراک با ادمین تماس بگیرید:*
[@{SUBSCRIPTION_CONTACT_USERNAME}](https://t.me/{SUBSCRIPTION_CONTACT_USERNAME})
🆔 آیدی خریدار: `{SUBSCRIPTION_CONTACT_ID}`
            
📋 *پلان‌های اشتراک:*
{plans_text}
🆔 آیدی گروه برای خرید: `{group_id}`
            
✨ *امکانات اشتراک پرمیوم:*
• سیستم اخطار خودکار
• ضد لینک و ضد فحش
• خوش‌آمدگویی خودکار  
• قفل تایم‌دار پیام همگانی
• جوین اجباری چنل
• پیام همگانی در تمام گروه‌ها
• مدیریت کامل گروه
• پشتیبانی ۲۴ ساعته"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in send_subscription_required_message: {str(e)}")
        await update.message.reply_text("خطایی در نمایش اطلاعات اشتراک رخ داد.")

# ======================================================================
# بخش: handlers/auto_permissions.py
# ======================================================================
logger = logging.getLogger(__name__)

class AutoPermissionManager:
    def __init__(self, premium_manager: PremiumManager):
        self.premium_manager = premium_manager

    async def grant_premium_admin_access(self, context: ContextTypes.DEFAULT_TYPE, group_id: int):
        """Grant full admin access to group admins and creator when group becomes premium"""
        try:
            logger.info(f"Starting admin access grant process for group {group_id}")
            
            # Get all current administrators
            administrators = await context.bot.get_chat_administrators(group_id)
            
            granted_permissions = []
            failed_permissions = []
            
            for admin in administrators:
                try:
                    # Skip if it's the bot itself
                    if admin.user.id == context.bot.id:
                        logger.info(f"Skipping bot itself in group {group_id}")
                        continue
                        
                    # Skip if user is already creator (has all permissions)
                    if admin.status == 'creator':
                        granted_permissions.append({
                            'user_id': admin.user.id,
                            'username': admin.user.username or 'بدون نام کاربری',
                            'first_name': admin.user.first_name or 'نام نامشخص',
                            'status': 'سازنده گروه (دارای تمام دسترسی‌ها)'
                        })
                        logger.info(f"User {admin.user.id} is creator in group {group_id}")
                        continue
                        
                    # Check current permissions
                    current_permissions = {
                        'can_delete_messages': getattr(admin, 'can_delete_messages', False),
                        'can_restrict_members': getattr(admin, 'can_restrict_members', False),
                        'can_promote_members': getattr(admin, 'can_promote_members', False),
                        'can_change_info': getattr(admin, 'can_change_info', False),
                        'can_invite_users': getattr(admin, 'can_invite_users', False),
                        'can_pin_messages': getattr(admin, 'can_pin_messages', False),
                        'can_manage_topics': getattr(admin, 'can_manage_topics', False),
                        'can_manage_video_chats': getattr(admin, 'can_manage_video_chats', False)
                    }
                    
                    # Check if user already has all permissions
                    if all(current_permissions.values()):
                        granted_permissions.append({
                            'user_id': admin.user.id,
                            'username': admin.user.username or 'بدون نام کاربری',
                            'first_name': admin.user.first_name or 'نام نامشخص',
                            'status': 'دارای تمام دسترسی‌ها'
                        })
                        logger.info(f"User {admin.user.id} already has full permissions in group {group_id}")
                        continue
                        
                    # Grant full admin permissions
                    await context.bot.promote_chat_member(
                        chat_id=group_id,
                        user_id=admin.user.id,
                        can_delete_messages=True,
                        can_restrict_members=True,
                        can_promote_members=True,
                        can_change_info=True,
                        can_invite_users=True,
                        can_pin_messages=True,
                        can_manage_topics=True,
                        can_manage_video_chats=True
                    )
                    
                    granted_permissions.append({
                        'user_id': admin.user.id,
                        'username': admin.user.username or 'بدون نام کاربری',
                        'first_name': admin.user.first_name or 'نام نامشخص',
                        'status': 'ارتقا به ادمین کامل'
                    })
                    
                    logger.info(f"Successfully granted full admin access to user {admin.user.id} in group {group_id}")
                    
                except BadRequest as e:
                    error_msg = str(e)
                    if "not enough rights" in error_msg.lower():
                        error_msg = "ربات دسترسی کافی برای ارتقا ندارد"
                    elif "user_not_mutual_contact" in error_msg.lower():
                        error_msg = "کاربر با ربات در تماس نیست"
                        
                    failed_permissions.append({
                        'user_id': admin.user.id,
                        'username': admin.user.username or 'بدون نام کاربری',
                        'first_name': admin.user.first_name or 'نام نامشخص',
                        'error': error_msg
                    })
                    logger.error(f"BadRequest error granting admin access to user {admin.user.id} in group {group_id}: {error_msg}")
                    
                except Forbidden as e:
                    failed_permissions.append({
                        'user_id': admin.user.id,
                        'username': admin.user.username or 'بدون نام کاربری',
                        'first_name': admin.user.first_name or 'نام نامشخص',
                        'error': "ربات مسدود شده یا دسترسی ندارد"
                    })
                    logger.error(f"Forbidden error granting admin access to user {admin.user.id} in group {group_id}: {str(e)}")
                    
                except TelegramError as e:
                    failed_permissions.append({
                        'user_id': admin.user.id,
                        'username': admin.user.username or 'بدون نام کاربری',
                        'first_name': admin.user.first_name or 'نام نامشخص',
                        'error': f"خطای تلگرام: {str(e)}"
                    })
                    logger.error(f"Telegram error granting admin access to user {admin.user.id} in group {group_id}: {str(e)}")
                    
                except Exception as e:
                    failed_permissions.append({
                        'user_id': admin.user.id,
                        'username': admin.user.username or 'بدون نام کاربری',
                        'first_name': admin.user.first_name or 'نام نامشخص',
                        'error': f"خطای غیرمنتظره: {str(e)}"
                    })
                    logger.error(f"Unexpected error granting admin access to user {admin.user.id} in group {group_id}: {str(e)}")
            
            logger.info(f"Admin access grant process completed for group {group_id}. Granted: {len(granted_permissions)}, Failed: {len(failed_permissions)}")
            
            return {
                'success': True,
                'granted': granted_permissions,
                'failed': failed_permissions
            }
            
        except Exception as e:
            logger.error(f"Critical error in grant_premium_admin_access for group {group_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'granted': [],
                'failed': []
            }

    async def notify_admin_access_granted(self, context: ContextTypes.DEFAULT_TYPE, group_id: int, result: dict):
        """Send notification about admin access changes"""
        try:
            if not result['success']:
                message = f"❌ خطا در اعطای دسترسی‌های ادمینی:\\n{result.get('error', 'خطای نامشخص')}"
            else:
                message = "🎉 گروه شما پرمیوم شد!\\n\\n"
                message += "✅ دسترسی‌های ادمینی به‌روزرسانی شد:\\n\\n"
                
                if result['granted']:
                    message += "👥 کاربران با دسترسی کامل:\\n"
                    for user in result['granted']:
                        name = user['first_name']
                        username = f"@{user['username']}" if user['username'] != 'بدون نام کاربری' else ""
                        message += f"• {name} {username}\\n  └ {user['status']}\\n"
                
                if result['failed']:
                    message += "\n⚠️ خطا در اعطای دسترسی:\\n"
                    for user in result['failed']:
                        name = user['first_name']
                        username = f"@{user['username']}" if user['username'] != 'بدون نام کاربری' else ""
                        message += f"• {name} {username}\\n  └ {user['error']}\\n"
                
                message += "\n💎 امکانات پرمیوم فعال شد:\\n"
                message += "• سیستم اخطار خودکار ✅\\n"
                message += "• ضد لینک و ضد فحش ✅\\n"
                message += "• خوش‌آمدگویی خودکار ✅\\n"
                message += "• قفل تایم‌دار پیام همگانی ✅\\n"
                message += "• جوین اجباری چنل ✅\\n"
                message += "• مدیریت کامل گروه ✅\\n"
                message += "• پشتیبانی ۲۴ ساعته ✅"
            
            # Split message if too long
            if len(message) > 4000:
                parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
                for part in parts:
                    await context.bot.send_message(chat_id=group_id, text=part)
            else:
                await context.bot.send_message(chat_id=group_id, text=message)
            
            logger.info(f"Successfully sent admin access notification to group {group_id}")
            
        except Exception as e:
            logger.error(f"Error sending admin access notification to group {group_id}: {str(e)}")

    async def check_bot_permissions(self, context: ContextTypes.DEFAULT_TYPE, group_id: int):
        """Check if bot has necessary permissions to promote users"""
        try:
            bot_member = await context.bot.get_chat_member(group_id, context.bot.id)
            
            if bot_member.status not in ['administrator', 'creator']:
                return False, "ربات ادمین گروه نیست"
            
            if not getattr(bot_member, 'can_promote_members', False):
                return False, "ربات دسترسی ارتقا کاربران ندارد"
            
            return True, "دسترسی‌های ربات کافی است"
            
        except Exception as e:
            logger.error(f"Error checking bot permissions in group {group_id}: {str(e)}")
            return False, f"خطا در بررسی دسترسی‌ها: {str(e)}"

# Global instance
auto_permission_manager = None

def get_auto_permission_manager(premium_manager: PremiumManager = None):
    """Get or create auto permission manager instance"""
    global auto_permission_manager
    if auto_permission_manager is None and premium_manager is not None:
        auto_permission_manager = AutoPermissionManager(premium_manager)
    return auto_permission_manager

# ======================================================================
# بخش: handlers/group.py
# ======================================================================
# Set up logger
logger = logging.getLogger(__name__)

# Initialize database
db = Database("group_manager.db")

# Regex patterns
LINK_PATTERN = r'(https?://\S+)|(t\.me/\S+)|(@\S+)|(telegram\.me/\S+)|(telegram\.dog/\S+)'

# Persian/Iranian profanity words list
PROFANITY_WORDS = [
    'کیر', 'کص', 'کس', 'جنده', 'گایید', 'گاید', 'کون', 'جاکش', 'قحبه',
    'مادرجنده', 'کسکش', 'کیری', 'گوه', 'عن', 'لاشی', 'بیناموس', 'حرومزاده',
    'دیوث', 'بیشرف', 'آشغال', 'عوضی', 'پفیوز', 'خفه شو', 'بی ناموس', 'حروم زاده',
    'کسخل', 'کصخل', 'بیغیرت', 'بی غیرت', 'جاکش', 'گوز', 'چاقال', 'جاکش', 'گه',
    'شاش', 'ریدی', 'مادر خراب', 'پدر سگ', 'پدرسگ'
]

def contains_profanity(text):
    """Check if text contains any profanity words."""
    text = text.lower()
    return any(word in text for word in PROFANITY_WORDS)

async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check messages for links and profanity."""
    try:
        # Add group to database if not exists
        db.add_group(update.effective_chat.id, update.effective_chat.title)
        
        # Add user to database if not exists
        user = update.effective_user
        db.add_user(user.id, user.username)
        
        # Add message to database for tagging feature
        db.add_message(update.message.message_id, update.effective_chat.id, user.id)
        
        # Check if group is premium
        is_premium = db.is_group_premium(update.effective_chat.id)

        # Ignore messages from admins
        user = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if user.status in ['administrator', 'creator'] or update.effective_user.id == ADMIN_ID:
            return

        message = update.message.text or update.message.caption or ""
        
        # Check for profanity or links
        has_profanity = contains_profanity(message)
        has_link = bool(re.search(LINK_PATTERN, message, re.IGNORECASE))
        
        if has_profanity or has_link:
            # Delete the message
            await update.message.delete()
            
            # Get user info
            user = update.effective_user
            db.add_user(user.id, user.username)
            
            if not is_premium:
                # Show premium subscription message
                warning_msg = (
                    "⭐️ برای استفاده از امکانات کامل ربات، گروه باید پرمیوم شود!\n\n"
                    "✅ مزایای اشتراک پرمیوم:\n"
                    "• سیستم اخطار خودکار\n"
                    "• خوش‌آمدگویی خودکار\n"
                    "• مدیریت کامل گروه\n"
                    "• پشتیبانی ۲۴ ساعته\n\n"
                    "👈 برای فعال‌سازی اشتراک پرمیوم، ادمین گروه می‌تواند از دستور /admin استفاده کند."
                )
            else:
                # Add warning in premium groups
                group_id = update.effective_chat.id
                db.add_warning(user.id, group_id, "استفاده از محتوای نامناسب" if has_profanity else "ارسال لینک غیرمجاز")
                warnings = db.get_user_warnings(user.id, group_id)
                
                if has_profanity:
                    warning_msg = (
                        f"🚫 <b>اخطار | کلمات نامناسب</b>\n\n"
                        f"👤 کاربر: {user.mention_html()}\n"
                        f"⚠️ دلیل: استفاده از کلمات نامناسب\n"
                        f"📊 تعداد اخطارها: <b>{warnings}/{MAX_WARNINGS}</b>\n\n"
                        f"💡 لطفاً از کلمات مناسب استفاده کنید و احترام به سایر اعضا را رعایت نمایید."
                    )
                else:
                    warning_msg = (
                        f"🔗 <b>اخطار | ارسال لینک</b>\n\n"
                        f"👤 کاربر: {user.mention_html()}\n"
                        f"⚠️ دلیل: ارسال لینک غیرمجاز\n"
                        f"📊 تعداد اخطارها: <b>{warnings}/{MAX_WARNINGS}</b>\n\n"
                        f"💡 برای حفظ امنیت گروه، ارسال لینک بدون اجازه ممنوع است."
                    )
                
                if warnings >= MAX_WARNINGS:
                    db.ban_user(user.id)
                    try:
                        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
                        warning_msg += f"\n\n🚨 <b>کاربر به دلیل دریافت {MAX_WARNINGS} اخطار از گروه مسدود شد!</b>"
                    except TelegramError:
                        warning_msg += "\n\n❌ خطا در مسدود کردن کاربر!"
                else:
                    remaining_warnings = MAX_WARNINGS - warnings
                    if remaining_warnings == 1:
                        warning_msg += f"\n\n⚡️ <b>توجه:</b> تنها <b>1 اخطار</b> تا مسدود شدن باقی مانده!"
                    elif remaining_warnings == 2:
                        warning_msg += f"\n\n⚠️ <b>هشدار:</b> <b>{remaining_warnings} اخطار</b> تا مسدود شدن باقی مانده!"
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=warning_msg,
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Error in check_message: {str(e)}")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome new members with customizable message"""
    try:
        # Get group settings
        group_id = update.effective_chat.id
        group_settings = db.get_group_settings(group_id)
        
        if not group_settings or not group_settings.get('welcome_enabled', True):
            return
            
        # Get custom welcome message if exists
        custom_welcome = group_settings.get('welcome_message', '')
        
        for new_member in update.message.new_chat_members:
            # Skip if the new member is the bot itself
            if new_member.id == context.bot.id:
                continue
                
            # Add user to database
            db.add_user(new_member.id, new_member.username)
            
            # Prepare welcome message
            if custom_welcome:
                # Replace placeholders
                welcome_msg = custom_welcome
                welcome_msg = welcome_msg.replace('{name}', new_member.first_name)
                welcome_msg = welcome_msg.replace('{username}', f"@{new_member.username}" if new_member.username else new_member.first_name)
                welcome_msg = welcome_msg.replace('{group}', update.effective_chat.title)
            else:
                # Default welcome message
                welcome_msg = f"👋 سلام {new_member.first_name} عزیز!\n\n"
                welcome_msg += f"به گروه {update.effective_chat.title} خوش آمدید.\n"
                welcome_msg += "لطفاً قوانین گروه را مطالعه کنید و رعایت نمایید.\n\n"
                welcome_msg += "⚠️ قوانین مهم:\n"
                welcome_msg += "• ارسال لینک ممنوع است\n"
                welcome_msg += "• استفاده از کلمات نامناسب ممنوع است\n"
                welcome_msg += "• احترام به سایر اعضا الزامی است\n"
            
            # Add buttons if enabled
            if group_settings.get('welcome_buttons_enabled', False):
                keyboard = []
                
                # Add rules button if rules message is set
                if group_settings.get('rules_message'):
                    keyboard.append([InlineKeyboardButton("📋 قوانین گروه", callback_data=f'rules_{group_id}')])
                
                # Add custom buttons
                custom_buttons = group_settings.get('custom_buttons', [])
                for button in custom_buttons:
                    if button.get('url'):
                        keyboard.append([InlineKeyboardButton(button.get('text', 'لینک'), url=button.get('url'))])
                
                if keyboard:
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text(welcome_msg, reply_markup=reply_markup)
                    return
            
            # Send welcome message without buttons
            await update.message.reply_text(welcome_msg)
            
    except Exception as e:
        logger.error(f"Error in welcome_new_member: {str(e)}")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warn a user by replying to their message."""
    try:
        # Add group to database if not exists
        db.add_group(update.effective_chat.id, update.effective_chat.title)

        # Only allow warning in premium groups
        if not db.is_group_premium(update.effective_chat.id):
            if update.effective_user.id == ADMIN_ID:
                await update.message.reply_text(
                    "❌ سیستم اخطار فقط در گروه‌های پرمیوم فعال است!\n"
                    "برای افزودن گروه به لیست پرمیوم، از دستور /admin استفاده کنید."
                )
            return

        # Check if command issuer is admin
        user = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if user.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("شما دسترسی به این دستور را ندارید!")
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً روی پیام کاربر مورد نظر ریپلای کنید.")
            return

        target_user = update.message.reply_to_message.from_user
        warner = update.message.from_user
        
        if target_user.id == warner.id:
            await update.message.reply_text("شما نمی‌توانید به خودتان اخطار دهید!")
            return
        
        # Add user to database if not exists
        db.add_user(target_user.id, target_user.username)
        
        # Add warning
        group_id = update.effective_chat.id
        reason = ' '.join(context.args) if context.args else "نقض قوانین گروه"
        db.add_warning(target_user.id, group_id, reason, warner.id)
        warnings = db.get_user_warnings(target_user.id, group_id)
        
        if warnings >= MAX_WARNINGS:
            db.ban_user(target_user.id)
            try:
                await context.bot.ban_chat_member(update.message.chat.id, target_user.id)
                await update.message.reply_text(
                    f"🚨 <b>مسدود شدن کاربر</b>\n\n"
                    f"👤 کاربر: {target_user.mention_html()}\n"
                    f"⚠️ دلیل: دریافت {MAX_WARNINGS} اخطار\n"
                    f"🔒 وضعیت: مسدود شده از گروه\n\n"
                    f"💡 کاربر به دلیل نقض مکرر قوانین از گروه حذف شد.",
                    parse_mode=ParseMode.HTML
                )
            except TelegramError:
                await update.message.reply_text(
                    f"❌ <b>خطا در مسدود کردن</b>\n\n"
                    f"👤 کاربر: {target_user.mention_html()}\n"
                    f"⚠️ علت: عدم دسترسی کافی ربات\n\n"
                    f"💡 لطفاً دسترسی‌های ربات را بررسی کنید.",
                    parse_mode=ParseMode.HTML
                )
        else:
            remaining_warnings = MAX_WARNINGS - warnings
            warning_msg = (
                f"⚠️ <b>اخطار دستی</b>\n\n"
                f"👤 کاربر: {target_user.mention_html()}\n"
                f"🔍 دلیل: {reason}\n"
                f"📊 تعداد اخطارها: <b>{warnings}/{MAX_WARNINGS}</b>\n"
                f"👮‍♂️ اخطار توسط: {warner.mention_html()}\n\n"
            )
            
            if remaining_warnings == 1:
                warning_msg += f"⚡️ <b>توجه:</b> تنها <b>1 اخطار</b> تا مسدود شدن باقی مانده!"
            elif remaining_warnings == 2:
                warning_msg += f"⚠️ <b>هشدار:</b> <b>{remaining_warnings} اخطار</b> تا مسدود شدن باقی مانده!"
            else:
                warning_msg += f"💡 <b>{remaining_warnings} اخطار</b> تا مسدود شدن باقی مانده."
            
            await update.message.reply_text(warning_msg, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error in warn_user: {str(e)}")
        await update.message.reply_text("خطایی رخ داد. لطفا دوباره تلاش کنید.")

async def unwarn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a warning from a user."""
    try:
        # Add group to database if not exists
        db.add_group(update.effective_chat.id, update.effective_chat.title)

        # Only allow unwarning in premium groups
        if not db.is_group_premium(update.effective_chat.id):
            if update.effective_user.id == ADMIN_ID:
                await update.message.reply_text(
                    "❌ سیستم اخطار فقط در گروه‌های پرمیوم فعال است!\n"
                    "برای افزودن گروه به لیست پرمیوم، از دستور /admin استفاده کنید."
                )
            return

        # Check if command issuer is admin
        user = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if user.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("شما دسترسی به این دستور را ندارید!")
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً روی پیام کاربر مورد نظر ریپلای کنید.")
            return

        target_user = update.message.reply_to_message.from_user
        
        # Add user to database if not exists
        db.add_user(target_user.id, target_user.username)
        
        # Remove warning
        group_id = update.effective_chat.id
        db.remove_warning(target_user.id, group_id)
        warnings = db.get_user_warnings(target_user.id, group_id)
        
        await update.message.reply_text(
            f"✅ <b>حذف اخطار</b>\n\n"
            f"👤 کاربر: {target_user.mention_html()}\n"
            f"📉 وضعیت: یک اخطار حذف شد\n"
            f"📊 تعداد اخطارهای فعلی: <b>{warnings}/{MAX_WARNINGS}</b>\n\n"
            f"💡 اخطار کاربر با موفقیت کاهش یافت.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error in unwarn_user: {str(e)}")
        await update.message.reply_text("خطایی رخ داد. لطفا دوباره تلاش کنید.")


async def set_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set group rules"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return
        
        # Get rules text
        if not context.args and not update.message.reply_to_message:
            await update.message.reply_text(
                "برای تنظیم قوانین گروه، متن قوانین را بعد از دستور بنویسید یا به یک پیام حاوی قوانین ریپلای کنید.\n\n"
                "مثال:\n"
                "/setrules قوانین گروه:\n1- احترام به اعضا\n2- ارسال نکردن لینک\n3- ..."
            )
            return
        
        # Get rules from reply or args
        if update.message.reply_to_message and update.message.reply_to_message.text:
            rules_text = update.message.reply_to_message.text
        else:
            rules_text = " ".join(context.args)
        
        # Save rules to database
        group_id = update.effective_chat.id
        conn = sqlite3.connect(db.db_name)
        c = conn.cursor()
        c.execute("UPDATE groups SET rules_message = ? WHERE group_id = ?", (rules_text, group_id))
        conn.commit()
        conn.close()
        
        await update.message.reply_text("✅ قوانین گروه با موفقیت تنظیم شد!\n\nاعضا می‌توانند با دستور /rules قوانین را مشاهده کنند.")
        
    except Exception as e:
        logger.error(f"Error in set_rules: {str(e)}")
        await update.message.reply_text(f"خطا در تنظیم قوانین: {str(e)}")

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show group rules"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Get rules from database
        group_id = update.effective_chat.id
        conn = sqlite3.connect(db.db_name)
        c = conn.cursor()
        c.execute("SELECT rules_message FROM groups WHERE group_id = ?", (group_id,))
        result = c.fetchone()
        conn.close()
        
        if result and result[0]:
            rules_text = result[0]
            await update.message.reply_text(f"📋 *قوانین گروه*\n\n{rules_text}", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ هنوز قوانینی برای این گروه تنظیم نشده است.\n\nادمین‌ها می‌توانند با دستور /setrules قوانین را تنظیم کنند.")
        
    except Exception as e:
        logger.error(f"Error in show_rules: {str(e)}")

# ======================================================================
# بخش: handlers/admin.py
# ======================================================================
# Set up logger
logger = logging.getLogger(__name__)

# Initialize database
db = Database("group_manager.db")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel with available options."""
    try:
        premium_manager = PremiumManager("group_manager.db")
        is_admin = update.effective_user.id == ADMIN_ID
        is_buyer = False
        group_id = None
        
        # تشخیص محیط (گروه یا پرایوت)
        if update.effective_chat.type != "private":
            group_id = update.effective_chat.id
            is_buyer = is_premium_buyer(update.effective_user.id, group_id, premium_manager)
        
        # بررسی دسترسی
        if not is_admin and not is_buyer:
            await update.message.reply_text(
                "❌ شما دسترسی به پنل مدیریت ندارید!\n\n"
                "💡 برای دسترسی به پنل:\n"
                "🔹 باید سازنده ربات باشید\n"
                "🔹 یا خریدار اشتراک این گروه باشید"
            )
            return
        
        keyboard = []
        
        # پنل ویژه خریداران اشتراک (فقط در گروه)
        if is_buyer and not is_admin and group_id:
            keyboard.append([InlineKeyboardButton("📊 آمار گروه", callback_data='buyer_stats'),
                             InlineKeyboardButton("⚠️ کاربران اخطار گرفته", callback_data='buyer_warned_users')])
            keyboard.append([InlineKeyboardButton("🚫 کاربران مسدود شده", callback_data='buyer_banned_users'),
                             InlineKeyboardButton("🔔 تنظیمات خوش‌آمدگویی", callback_data='buyer_welcome_settings')])
            keyboard.append([InlineKeyboardButton("🔒 قفل سرویس تلگرام", callback_data='buyer_telegram_service_lock'),
                             InlineKeyboardButton("📋 بررسی اشتراک", callback_data='check_subscription')])
            
            # ذخیره اطلاعات گروه در user_data برای استفاده در callback
            context.user_data['group_id'] = group_id
            context.user_data['is_admin'] = False
            context.user_data['is_buyer'] = True
            
            await update.message.reply_text(
                f"🎛️ <b>پنل مدیریت گروه</b>\n\n"
                f"👋 سلام <b>{update.effective_user.first_name}</b>!\n"
                f"💎 شما خریدار اشتراک این گروه هستید\n"
                f"🎯 <b>گروه:</b> {update.effective_chat.title}\n\n"
                f"📋 لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
            return
        
        # پنل سازنده ربات
        if is_admin:
            # آمار گروه و کاربران
            keyboard.append([InlineKeyboardButton("📊 آمار ربات", callback_data='stats'),
                             InlineKeyboardButton("⚠️ کاربران اخطار گرفته", callback_data='warned_users')])
            keyboard.append([InlineKeyboardButton("🚫 کاربران مسدود شده", callback_data='banned_users'),
                             InlineKeyboardButton("🔔 تنظیمات خوش‌آمدگویی", callback_data='welcome_settings')])
            
            # مدیریت اشتراک‌ها
            keyboard.append([InlineKeyboardButton("💎 مدیریت گروه‌های پرمیوم", callback_data='premium_groups'),
                             InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data='broadcast')])
            keyboard.append([InlineKeyboardButton("🔄 بروزرسانی کش", callback_data='refresh_cache')])
            
            # دکمه‌های مخصوص قفل سرویس تلگرام (اگر در گروه باشد)
            if group_id:
                keyboard.append([InlineKeyboardButton("🔒 قفل سرویس تلگرام", callback_data='telegram_service_lock')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # ذخیره اطلاعات گروه در user_data برای استفاده در callback
            if group_id:
                context.user_data['group_id'] = group_id
            context.user_data['is_admin'] = is_admin
            context.user_data['is_buyer'] = is_buyer
            
            await update.message.reply_text(
                f"🔧 <b>پنل مدیریت سازنده</b>\n\n"
                f"👋 سلام <b>{update.effective_user.first_name}</b>!\n"
                f"👑 شما سازنده ربات هستید\n\n"
                f"📋 لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return
        
        # اگر به اینجا رسید، خطا داشته
        await update.message.reply_text("❌ خطا در تشخیص نوع کاربر.")
        
    except Exception as e:
        logger.error(f"Error in admin_panel: {str(e)}")
        await update.message.reply_text("❌ خطایی رخ داد. لطفا دوباره تلاش کنید.")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel button callbacks."""
    try:
        query = update.callback_query
        premium_manager = PremiumManager("group_manager.db")
        
        # بررسی دسترسی کاربر
        is_admin = update.effective_user.id == ADMIN_ID
        is_buyer = False
        group_id = context.user_data.get('group_id')
        
        if group_id:
            is_buyer = is_premium_buyer(update.effective_user.id, group_id, premium_manager)
        
        if not is_admin and not is_buyer:
            await query.answer("شما دسترسی به این بخش را ندارید!")
            return
        
        # بررسی دسترسی به بخش‌های مخصوص ادمین
        admin_only_sections = ['premium_groups', 'broadcast', 'refresh_cache', 'advanced_settings']
        if query.data in admin_only_sections and not is_admin:
            await query.answer("فقط ادمین اصلی می‌تواند به این بخش دسترسی داشته باشد!")
            return
        
        await query.answer()
        
        if query.data == 'stats':
            # نمایش آمار واقعی گروه
            conn = sqlite3.connect(db.db_name)
            c = conn.cursor()
            
            if is_admin and not group_id:
                # آمار کلی برای ادمین اصلی
                total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                warned_users = c.execute("SELECT COUNT(*) FROM users WHERE warnings > 0").fetchone()[0]
                banned_users = c.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1").fetchone()[0]
                total_groups = c.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
                premium_groups_count = c.execute("SELECT COUNT(*) FROM groups WHERE is_premium = 1").fetchone()[0]
                total_messages = c.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
                total_reports = c.execute("SELECT COUNT(*) FROM user_reports").fetchone()[0]
                pending_reports = c.execute("SELECT COUNT(*) FROM user_reports WHERE status = 'pending'").fetchone()[0]
                
                # محاسبه درصد گروه‌های پرمیوم
                premium_percentage = round((premium_groups_count / total_groups) * 100) if total_groups > 0 else 0
                premium_bar = generate_progress_bar(premium_percentage)
                
                stats_text = (
                    "📊 آمار کلی سیستم:\n\n"
                    f"👥 تعداد کل کاربران: {total_users:,}\n"
                    f"⚠️ کاربران اخطار گرفته: {warned_users:,} ({round((warned_users/total_users)*100) if total_users > 0 else 0}%)\n"
                    f"🚫 کاربران مسدود شده: {banned_users:,} ({round((banned_users/total_users)*100) if total_users > 0 else 0}%)\n\n"
                    f"👥 تعداد کل گروه‌ها: {total_groups:,}\n"
                    f"💎 گروه‌های پرمیوم: {premium_groups_count:,} ({premium_percentage}%)\n"
                    f"{premium_bar}\n\n"
                    f"💬 تعداد کل پیام‌ها: {total_messages:,}\n"
                    f"🔔 گزارش‌های کاربران: {total_reports:,} (در انتظار: {pending_reports:,})\n"
                )
                
                # دکمه‌های مدیریتی بیشتر
                keyboard = [
                    [InlineKeyboardButton("📈 نمودار فعالیت", callback_data='activity_chart')],
                    [InlineKeyboardButton("👥 گروه‌های فعال", callback_data='active_groups'),
                     InlineKeyboardButton("👤 کاربران فعال", callback_data='active_users')],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.edit_text(stats_text, reply_markup=reply_markup)
            else:
                # آمار گروه فعلی برای خریدار یا ادمین
                if not group_id:
                    await query.message.edit_text("این دستور فقط در گروه قابل استفاده است.")
                    return
                
                # آمار واقعی گروه
                total_members = await context.bot.get_chat_member_count(group_id)
                admins_count = len(await context.bot.get_chat_administrators(group_id))
                
                # آمار پیام‌ها از دیتابیس
                total_messages = c.execute("SELECT COUNT(*) FROM messages WHERE group_id = ?", (group_id,)).fetchone()[0]
                unique_users = c.execute("SELECT COUNT(DISTINCT user_id) FROM messages WHERE group_id = ?", (group_id,)).fetchone()[0]
                
                # آمار اخطارها و بن‌ها
                warned_users = c.execute("SELECT COUNT(*) FROM warnings WHERE group_id = ?", (group_id,)).fetchone()[0]
                
                # آمار گزارش‌های کاربران
                total_reports = c.execute("SELECT COUNT(*) FROM user_reports WHERE group_id = ?", (group_id,)).fetchone()[0]
                pending_reports = c.execute("SELECT COUNT(*) FROM user_reports WHERE group_id = ? AND status = 'pending'", (group_id,)).fetchone()[0]
                
                # آمار پیام‌های هفته اخیر
                week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
                weekly_messages = c.execute("SELECT COUNT(*) FROM messages WHERE group_id = ? AND timestamp > ?", 
                                          (group_id, week_ago)).fetchone()[0]
                
                # محاسبه میانگین پیام روزانه
                daily_avg = round(weekly_messages / 7, 1) if weekly_messages > 0 else 0
                
                # محاسبه نسبت کاربران فعال به کل اعضا
                active_ratio = round((unique_users / total_members) * 100, 1) if total_members > 0 else 0
                activity_bar = generate_progress_bar(active_ratio)
                
                # اطلاعات اشتراک
                subscription_info = premium_manager.get_group_subscription_info(group_id)
                subscription_end = subscription_info['subscription_end'] if subscription_info else "ندارد"
                
                # محاسبه روزهای باقی‌مانده اشتراک
                days_left = "نامحدود"
                if subscription_end != "ندارد":
                    try:
                        end_date = datetime.strptime(subscription_end, "%Y-%m-%d")
                        days_left = (end_date - datetime.now()).days
                        if days_left < 0:
                            days_left = "منقضی شده"
                        else:
                            days_left = f"{days_left} روز"
                    except:
                        days_left = "نامشخص"
                
                stats_text = (
                    f"📊 آمار گروه {update.effective_chat.title}:\n\n"
                    f"👥 تعداد کل اعضا: {total_members:,}\n"
                    f"👮‍♂️ تعداد ادمین‌ها: {admins_count}\n"
                    f"💬 تعداد پیام‌های ثبت شده: {total_messages:,}\n"
                    f"📈 میانگین پیام روزانه: {daily_avg}\n"
                    f"👤 کاربران فعال: {unique_users:,} ({active_ratio}%)\n"
                    f"{activity_bar}\n"
                    f"⚠️ تعداد اخطارها: {warned_users:,}\n"
                    f"🔔 گزارش‌های کاربران: {total_reports:,} (در انتظار: {pending_reports})\n\n"
                    f"💎 وضعیت اشتراک: {'فعال ✅' if subscription_info else 'غیرفعال ❌'}\n"
                    f"📅 تاریخ پایان اشتراک: {subscription_end}\n"
                    f"⏳ زمان باقی‌مانده: {days_left}"
                )
                
                # دکمه‌های مدیریتی بیشتر
                keyboard = [
                    [InlineKeyboardButton("📊 گزارش هفتگی", callback_data=f'weekly_report_{group_id}')],
                    [InlineKeyboardButton("👤 کاربران فعال", callback_data=f'active_users_{group_id}'),
                     InlineKeyboardButton("⚠️ اخطارها", callback_data=f'warning_details_{group_id}')],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.edit_text(stats_text, reply_markup=reply_markup)
            
            conn.close()
        
        # Callback های ویژه خریداران
        elif query.data == 'buyer_stats':
            # همان کد آمار گروه اما فقط برای گروه خریدار
            await admin_callback(update, context)  # استفاده مجدد از stats
            
        elif query.data == 'buyer_warned_users':
            # کاربران اخطار گرفته در گروه خریدار
            await query.message.edit_text("⚠️ در حال بارگذاری لیست کاربران اخطار گرفته...")
            # پیاده‌سازی نمایش کاربران اخطار گرفته
            
        elif query.data == 'buyer_banned_users':
            # کاربران مسدود شده در گروه خریدار
            await query.message.edit_text("🚫 در حال بارگذاری لیست کاربران مسدود شده...")
            # پیاده‌سازی نمایش کاربران مسدود شده
            
        elif query.data == 'buyer_welcome_settings':
            # تنظیمات خوش‌آمدگویی برای خریدار
            keyboard = [
                [InlineKeyboardButton("فعال کردن خوش‌آمدگویی", callback_data='welcome_on')],
                [InlineKeyboardButton("غیرفعال کردن خوش‌آمدگویی", callback_data='welcome_off')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "🔔 <b>تنظیمات خوش‌آمدگویی</b>\n\n"
                "📋 لطفاً یک گزینه را انتخاب کنید:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
        elif query.data == 'buyer_telegram_service_lock':
            # منوی قفل سرویس‌های تلگرام برای خریدار
            keyboard = [
                [InlineKeyboardButton("🔒 قفل عکس", callback_data='lock_photo')],
                [InlineKeyboardButton("🔒 قفل ویدیو", callback_data='lock_video')],
                [InlineKeyboardButton("🔒 قفل فایل", callback_data='lock_document')],
                [InlineKeyboardButton("🔒 قفل گیف", callback_data='lock_animation')],
                [InlineKeyboardButton("🔒 حذف پیام ورود اعضا", callback_data='lock_new_members')],
                [InlineKeyboardButton("🔒 حذف پیام اد شدن", callback_data='lock_join_messages')],
                [InlineKeyboardButton("🔒 حذف پیام پین", callback_data='lock_pin_messages')],
                [InlineKeyboardButton("🔒 حذف پیام‌های ویدیو چت", callback_data='lock_video_chat_messages')],
                [InlineKeyboardButton("🔓 باز کردن همه قفل‌ها", callback_data='unlock_all')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "🔒 <b>قفل سرویس‌های تلگرام</b>\n\n"
                "📋 لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        
        elif query.data == 'warned_users':
            # Show users with warnings
            conn = sqlite3.connect(db.db_name)
            c = conn.cursor()
            warned = c.execute("SELECT user_id, username, warnings FROM users WHERE warnings > 0").fetchall()
            
            if not warned:
                await query.message.edit_text("هیچ کاربری اخطار ندارد.")
                return
                
            text = "⚠️ لیست کاربران اخطار گرفته:\n\n"
            for user_id, username, warnings in warned:
                text += f"👤 {username or user_id}\n"
                text += f"تعداد اخطار: {warnings}\n\n"
            
            await query.message.edit_text(text)
        
        elif query.data == 'banned_users':
            # Show banned users
            conn = sqlite3.connect(db.db_name)
            c = conn.cursor()
            banned = c.execute("SELECT user_id, username FROM users WHERE is_banned = 1").fetchall()
            
            if not banned:
                await query.message.edit_text("هیچ کاربری مسدود نشده است.")
                return
                
            text = "🚫 لیست کاربران مسدود شده:\n\n"
            for user_id, username in banned:
                text += f"👤 {username or user_id}\n"
            
            await query.message.edit_text(text)
        
        elif query.data == 'welcome_settings':
            keyboard = [
                [InlineKeyboardButton("فعال کردن خوش‌آمدگویی", callback_data='welcome_on')],
                [InlineKeyboardButton("غیرفعال کردن خوش‌آمدگویی", callback_data='welcome_off')],
                [InlineKeyboardButton("بازگشت به منوی اصلی", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "تنظیمات خوش‌آمدگویی:\n"
                "لطفاً یک گزینه را انتخاب کنید:",
                reply_markup=reply_markup
            )
        
        elif query.data == 'premium_groups':
            # Show premium groups list and management options
            premium_groups = db.get_premium_groups()
            
            if not premium_groups:
                text = "هیچ گروه پرمیومی وجود ندارد."
            else:
                text = "📊 لیست گروه‌های پرمیوم:\n\n"
                for group_id, title, added_by, added_date in premium_groups:
                    text += f"📌 {title or group_id}\n"
                    text += f"📅 تاریخ افزودن: {added_date}\n\n"
            
            keyboard = [
                [InlineKeyboardButton("افزودن گروه به لیست پرمیوم", callback_data='add_premium')],
                [InlineKeyboardButton("حذف گروه از لیست پرمیوم", callback_data='remove_premium')],
                [InlineKeyboardButton("بازگشت به منوی اصلی", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(text, reply_markup=reply_markup)
            
        elif query.data == 'add_premium':
            # Add current group to premium list
            if update.effective_chat.type != "private":
                group_id = update.effective_chat.id
                group_title = update.effective_chat.title
                db.add_group(group_id, group_title, update.effective_user.id)
                db.set_group_premium(group_id, True)
                await query.message.edit_text(
                    f"✅ گروه {group_title} به لیست پرمیوم اضافه شد.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("بازگشت", callback_data='premium_groups')
                    ]])
                )
            else:
                await query.message.edit_text(
                    "❌ این دستور فقط در گروه قابل استفاده است.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("بازگشت", callback_data='premium_groups')
                    ]])
                )
                
        elif query.data == 'remove_premium':
            # Remove current group from premium list
            if update.effective_chat.type != "private":
                group_id = update.effective_chat.id
                db.set_group_premium(group_id, False)
                await query.message.edit_text(
                    "✅ گروه از لیست پرمیوم حذف شد.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("بازگشت", callback_data='premium_groups')
                    ]])
                )
            else:
                await query.message.edit_text(
                    "❌ این دستور فقط در گروه قابل استفاده است.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("بازگشت", callback_data='premium_groups')
                    ]])
                )
                
        elif query.data == 'telegram_service_lock':
            # نمایش منوی قفل سرویس‌های تلگرام
            keyboard = [
                [InlineKeyboardButton("🔒 قفل عکس", callback_data='lock_photo')],
                [InlineKeyboardButton("🔒 قفل ویدیو", callback_data='lock_video')],
                [InlineKeyboardButton("🔒 قفل فایل", callback_data='lock_document')],
                [InlineKeyboardButton("🔒 قفل گیف", callback_data='lock_animation')],
                [InlineKeyboardButton("🔒 حذف پیام ورود اعضا", callback_data='lock_new_members')],
                [InlineKeyboardButton("🔒 حذف پیام اد شدن", callback_data='lock_join_messages')],
                [InlineKeyboardButton("🔒 حذف پیام پین", callback_data='lock_pin_messages')],
                [InlineKeyboardButton("🔒 حذف پیام‌های ویدیو چت", callback_data='lock_video_chat_messages')],
                [InlineKeyboardButton("🔓 باز کردن همه قفل‌ها", callback_data='unlock_all')],
                [InlineKeyboardButton("بازگشت به منوی اصلی", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "🔒 قفل سرویس‌های تلگرام:\n"
                "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
                reply_markup=reply_markup
            )
        
        elif query.data == 'lock_photo':
            if not group_id:
                await query.message.edit_text("این دستور فقط در گروه قابل استفاده است.")
                return
                
            # قفل کردن ارسال عکس
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_photos=False,
                can_send_videos=True,
                can_send_documents=True,
                can_send_audios=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
            
            await context.bot.set_chat_permissions(group_id, permissions)
            await query.message.edit_text(
                "✅ قفل عکس فعال شد. کاربران نمی‌توانند عکس ارسال کنند.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("بازگشت", callback_data='telegram_service_lock')
                ]])
            )
        
        elif query.data == 'lock_video':
            if not group_id:
                await query.message.edit_text("این دستور فقط در گروه قابل استفاده است.")
                return
                
            # قفل کردن ارسال ویدیو
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_photos=True,
                can_send_videos=False,
                can_send_documents=True,
                can_send_audios=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
            
            await context.bot.set_chat_permissions(group_id, permissions)
            await query.message.edit_text(
                "✅ قفل ویدیو فعال شد. کاربران نمی‌توانند ویدیو ارسال کنند.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("بازگشت", callback_data='telegram_service_lock')
                ]])
            )
            
        elif query.data == 'lock_document':
            if not group_id:
                await query.message.edit_text("این دستور فقط در گروه قابل استفاده است.")
                return
                
            # قفل کردن ارسال فایل
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_documents=False,
                can_send_audios=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
            
            await context.bot.set_chat_permissions(group_id, permissions)
            await query.message.edit_text(
                "✅ قفل فایل فعال شد. کاربران نمی‌توانند فایل ارسال کنند.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("بازگشت", callback_data='telegram_service_lock')
                ]])
            )
            
        elif query.data == 'lock_animation':
            if not group_id:
                await query.message.edit_text("این دستور فقط در گروه قابل استفاده است.")
                return
                
            # قفل کردن ارسال گیف
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_documents=True,
                can_send_audios=True,
                can_send_polls=True,
                can_send_other_messages=False,  # این گزینه برای گیف‌ها و استیکرها استفاده می‌شود
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
            
            await context.bot.set_chat_permissions(group_id, permissions)
            await query.message.edit_text(
                "✅ قفل گیف فعال شد. کاربران نمی‌توانند گیف ارسال کنند.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("بازگشت", callback_data='telegram_service_lock')
                ]])
            )
            
        elif query.data == 'unlock_all':
            if not group_id:
                await query.message.edit_text("این دستور فقط در گروه قابل استفاده است.")
                return
                
            # باز کردن همه قفل‌ها
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_documents=True,
                can_send_audios=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
            
            # غیرفعال کردن قفل‌های دیگر در دیتابیس
            conn = sqlite3.connect(db.db_name)
            c = conn.cursor()
            c.execute("UPDATE groups SET delete_new_members = 0, delete_join_messages = 0, delete_pin_messages = 0, delete_video_chat_messages = 0 WHERE group_id = ?", (group_id,))
            conn.commit()
            conn.close()
            
            await context.bot.set_chat_permissions(group_id, permissions)
            await query.message.edit_text(
                "✅ همه قفل‌های سرویس باز شدند. کاربران می‌توانند همه نوع محتوا ارسال کنند و قفل‌های پیام ورود و اد شدن نیز غیرفعال شدند.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("بازگشت", callback_data='telegram_service_lock')
                ]])
            )
            
        elif query.data == 'lock_new_members':
            if not group_id:
                await query.message.edit_text("این دستور فقط در گروه قابل استفاده است.")
                return
                
            # فعال/غیرفعال حذف پیام ورود اعضا
            conn = sqlite3.connect(db.db_name)
            c = conn.cursor()
            
            # بررسی وضعیت فعلی
            c.execute("SELECT delete_new_members FROM groups WHERE group_id = ?", (group_id,))
            result = c.fetchone()
            current_status = result[0] if result and result[0] is not None else 0
            
            # تغییر وضعیت
            new_status = 0 if current_status else 1
            c.execute("UPDATE groups SET delete_new_members = ? WHERE group_id = ?", (new_status, group_id))
            conn.commit()
            conn.close()
            
            status_text = "فعال" if new_status else "غیرفعال"
            await query.message.edit_text(
                f"✅ حذف پیام ورود اعضا {status_text} شد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("بازگشت", callback_data='telegram_service_lock')
                ]])
            )
            
        elif query.data == 'lock_join_messages':
            if not group_id:
                await query.message.edit_text("این دستور فقط در گروه قابل استفاده است.")
                return
                
            # فعال/غیرفعال کردن حذف پیام اد شدن
            conn = sqlite3.connect(db.db_name)
            c = conn.cursor()
            
            # بررسی وضعیت فعلی
            c.execute("SELECT delete_join_messages FROM groups WHERE group_id = ?", (group_id,))
            result = c.fetchone()
            current_status = result[0] if result and result[0] is not None else 0
            
            # تغییر وضعیت
            new_status = 0 if current_status else 1
            c.execute("UPDATE groups SET delete_join_messages = ? WHERE group_id = ?", (new_status, group_id))
            conn.commit()
            conn.close()
            
            status_text = "فعال" if new_status else "غیرفعال"
            await query.message.edit_text(
                f"✅ حذف پیام اد شدن {status_text} شد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("بازگشت", callback_data='telegram_service_lock')
                ]])
            )
            
        elif query.data == 'lock_pin_messages':
            if not group_id:
                await query.message.edit_text("این دستور فقط در گروه قابل استفاده است.")
                return
                
            # فعال/غیرفعال کردن حذف پیام پین
            conn = sqlite3.connect(db.db_name)
            c = conn.cursor()
            
            # بررسی وضعیت فعلی
            c.execute("SELECT delete_pin_messages FROM groups WHERE group_id = ?", (group_id,))
            result = c.fetchone()
            current_status = result[0] if result and result[0] is not None else 0
            
            # تغییر وضعیت
            new_status = 0 if current_status else 1
            c.execute("UPDATE groups SET delete_pin_messages = ? WHERE group_id = ?", (new_status, group_id))
            conn.commit()
            conn.close()
            
            status_text = "فعال" if new_status else "غیرفعال"
            await query.message.edit_text(
                f"✅ حذف پیام پین {status_text} شد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("بازگشت", callback_data='telegram_service_lock')
                ]])
            )
            
        elif query.data == 'lock_video_chat_messages':
            if not group_id:
                await query.message.edit_text("این دستور فقط در گروه قابل استفاده است.")
                return
                
            # فعال/غیرفعال کردن حذف پیام‌های ویدیو چت
            conn = sqlite3.connect(db.db_name)
            c = conn.cursor()
            
            # بررسی وضعیت فعلی
            c.execute("SELECT delete_video_chat_messages FROM groups WHERE group_id = ?", (group_id,))
            result = c.fetchone()
            current_status = result[0] if result and result[0] is not None else 0
            
            # تغییر وضعیت
            new_status = 0 if current_status else 1
            c.execute("UPDATE groups SET delete_video_chat_messages = ? WHERE group_id = ?", (new_status, group_id))
            conn.commit()
            conn.close()
            
            status_text = "فعال" if new_status else "غیرفعال"
            await query.message.edit_text(
                f"✅ حذف پیام‌های ویدیو چت {status_text} شد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("بازگشت", callback_data='telegram_service_lock')
                ]])
            )
            
        elif query.data == 'broadcast':
            # نمایش فرم ارسال پیام همگانی
            await query.message.edit_text(
                "📢 ارسال پیام همگانی:\n\n"
                "برای ارسال پیام همگانی به تمام گروه‌های پرمیوم، از دستور زیر استفاده کنید:\n\n"
                "`/broadcast متن پیام`\n\n"
                "این پیام به تمام گروه‌های پرمیوم فعال ارسال خواهد شد.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("بازگشت به منوی اصلی", callback_data='back_to_main')
                ]])
            )
            
    except Exception as e:
        logger.error(f"Error in admin_callback: {str(e)}")
        await query.message.edit_text("خطایی رخ داد. لطفا دوباره تلاش کنید.")

# در انتهای فایل اضافه کنید
def generate_progress_bar(percentage, length=10):
    """ایجاد نوار پیشرفت متنی با درصد مشخص"""
    filled = int(percentage / 100 * length)
    bar = '█' * filled + '░' * (length - filled)
    return f"[{bar}] {percentage}%"

# ======================================================================
# بخش: handlers/subscription.py
# ======================================================================
logger = logging.getLogger(__name__)

# Initialize premium manager
premium_manager = PremiumManager("group_manager.db")
db = Database("group_manager.db")  # اضافه کردن این خط

# Subscription plans
SUBSCRIPTION_PLANS = {
    'monthly': {'name': 'ماهانه', 'price': 50000, 'days': 30},
    'quarterly': {'name': 'سه ماهه', 'price': 120000, 'days': 90},
    'biannual': {'name': 'شش ماهه', 'price': 200000, 'days': 180},
    'annual': {'name': 'سالانه', 'price': 350000, 'days': 365}
}

async def subscription_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    "Check subscription status of current group"
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "این دستور فقط در گروه‌ها قابل استفاده است.\n\n"
                "برای خرید اشتراک با ادمین تماس بگیرید:\n\n"
                f"@{SUBSCRIPTION_CONTACT_USERNAME}"
            )
            return

        group_id = update.effective_chat.id
        subscription_info = premium_manager.get_group_subscription_info(group_id)

        if subscription_info and premium_manager.is_group_premium(group_id):
            message = f"✅ وضعیت اشتراک: فعال\n\n"
            message += f"📅 شروع اشتراک: {subscription_info['subscription_start']}\n"
            message += f"📅 پایان اشتراک: {subscription_info['subscription_end']}\n"
            message += f"👤 خریدار: @{subscription_info['buyer_username']}\n\n"

            message += "💎 امکانات فعال:\n"
            message += "• سیستم اخطار خودکار ✅\n"
            message += "• ضد لینک و ضد فحش ✅\n"
            message += "• خوش‌آمدگویی خودکار ✅\n"
            message += "• قفل تایم‌دار پیام همگانی ✅\n"
            message += "• جوین اجباری چنل ✅\n"
            message += "• مدیریت کامل گروه ✅\n"
            message += "• پشتیبانی ۲۴ ساعته ✅"

        else:
            message = f"❌ وضعیت اشتراک: غیرفعال\n\n"
            message += "💎 برای استفاده از امکانات پیشرفته ربات، نیاز به خرید اشتراک دارید.\n\n"
            message += f"👨‍💼 برای خرید اشتراک با ادمین تماس بگیرید:\n"
            message += f"@{SUBSCRIPTION_CONTACT_USERNAME}\n"
            message += f"🆔 آیدی خریدار: `{SUBSCRIPTION_CONTACT_ID}`\n\n"
            message += f"🆔 آیدی گروه برای خرید: `{group_id}`\n\n"
            message += "📋 پلان‌های اشتراک:\n"
            for plan_key, plan_info in SUBSCRIPTION_PLANS.items():
                message += f"• {plan_info['name']}: {plan_info['price']:,} تومان ({plan_info['days']} روز)\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in subscription_status: {str(e)}")
        await update.message.reply_text("خطایی در بررسی وضعیت اشتراک رخ داد.")

async def add_premium_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a group to premium list (Admin only)"""
    try:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین اصلی می‌تواند اشتراک اضافه کند.")
            return

        if len(context.args) < 3:
            await update.message.reply_text(
                "استفاده: /addpremium <group_id> <buyer_id> <duration_days>\n\n"
                "مثال:\n\n"
                "/addpremium -1001234567890 123456789 30\n\n"
                "پلان‌های پیش‌فرض:\n\n"
                "• 30 روز (ماهانه)\n"
                "• 90 روز (سه ماهه)\n"
                "• 180 روز (شش ماهه)\n"
                "• 365 روز (سالانه)"
            )
            return

        group_id = int(context.args[0])
        buyer_id = int(context.args[1])
        duration_days = int(context.args[2])

        # Get buyer info
        try:
            buyer_info = await context.bot.get_chat(buyer_id)
            buyer_username = buyer_info.username or "نامشخص"
        except:
            buyer_username = "نامشخص"

        # Check if bot has necessary permissions in the group
        auto_perm_manager = get_auto_permission_manager(premium_manager)
        if auto_perm_manager:
            bot_check, bot_message = await auto_perm_manager.check_bot_permissions(context, group_id)
            if not bot_check:
                await update.message.reply_text(
                    f"⚠️ هشدار: {bot_message}\n"
                    "اشتراک اضافه می‌شود اما ممکن است دسترسی‌های ادمینی به‌روزرسانی نشود.\n"
                    "لطفاً ربات را ادمین کنید و دسترسی 'ارتقا کاربران' را به آن بدهید."
                )

        # Add premium subscription
        success = premium_manager.add_premium_subscription(
            group_id=group_id,
            buyer_id=buyer_id,
            buyer_username=buyer_username,
            duration_days=duration_days
        )

        if success:
            # اضافه کردن این دو خط
            db.add_group(group_id, "Unknown", buyer_id)  # اضافه کردن گروه اگر وجود ندارد
            db.set_group_premium(group_id, True)  # تنظیم وضعیت پرمیوم
            
            logger.info(f"Premium subscription added successfully for group {group_id}")

            # Grant automatic admin access
            if auto_perm_manager:
                logger.info(f"Starting automatic admin access grant for group {group_id}")
                access_result = await auto_perm_manager.grant_premium_admin_access(context, group_id)

                # Send notification to group
                await auto_perm_manager.notify_admin_access_granted(context, group_id, access_result)

                # Confirm to admin
                await update.message.reply_text(
                    f"✅ اشتراک پرمیوم با موفقیت اضافه شد!\n\n"
                    f"🆔 گروه: `{group_id}`\n"
                    f"👤 خریدار: {buyer_username} (`{buyer_id}`)\n"
                    f"⏰ مدت: {duration_days} روز\n\n"
                    f"🔧 دسترسی‌های ادمینی:\n"
                    f"• موفق: {len(access_result.get('granted', []))}\n"
                    f"• ناموفق: {len(access_result.get('failed', []))}\n\n"
                    f"📊 جزئیات در گروه ارسال شد.",
                    parse_mode='Markdown'
                )

            else:
                await update.message.reply_text(
                    f"✅ اشتراک پرمیوم اضافه شد اما خطا در سیستم دسترسی‌ها!\n\n"
                    f"🆔 گروه: `{group_id}`\n"
                    f"👤 خریدار: {buyer_username} (`{buyer_id}`)\n"
                    f"⏰ مدت: {duration_days} روز",
                    parse_mode='Markdown'
                )

            # Refresh premium cache in main
            try:
                load_premium_groups()
                logger.info("Premium groups cache refreshed successfully")
            except Exception as cache_error:
                logger.error(f"Error refreshing premium cache: {str(cache_error)}")

        else:
            await update.message.reply_text("❌ خطا در اضافه کردن اشتراک!")

    except ValueError:
        await update.message.reply_text("❌ مقادیر وارد شده نامعتبر است!")
    except Exception as e:
        logger.error(f"Error in add_premium_group: {str(e)}")
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def list_premium_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    "List all premium groups (Admin only)"
    try:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین اصلی می‌تواند لیست گروه‌های پرمیوم را مشاهده کند.")
            return

        groups = premium_manager.get_all_premium_groups()

        if not groups:
            await update.message.reply_text("هیچ گروه پرمیومی یافت نشد.")
            return

        message = "📋 لیست گروه‌های پرمیوم:\n\n"

        active_count = 0
        inactive_count = 0

        for group in groups:
            is_active = premium_manager.is_group_premium(group['group_id'])
            status = "🟢 فعال" if is_active else "🔴 منقضی"

            if is_active:
                active_count += 1
            else:
                inactive_count += 1

            message += f"🆔 `{group['group_id']}`\n"
            message += f"📅 {group['subscription_start']} تا {group['subscription_end']}\n"
            message += f"👤 @{group['buyer_username']} (`{group['buyer_id']}`)\n"
            message += f"📊 {status}\n\n"

        message += f"📊 خلاصه آمار:\n"
        message += f"• فعال: {active_count}\n"
        message += f"• منقضی: {inactive_count}\n"
        message += f"• کل: {len(groups)}"

        # Split message if too long
        if len(message) > 4000:
            messages = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for msg in messages:
                await update.message.reply_text(msg, parse_mode='Markdown')
        else:
            await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in list_premium_groups: {str(e)}")
        await update.message.reply_text("خطایی در نمایش لیست گروه‌های پرمیوم رخ داد.")

async def check_expiring_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    """Check for subscriptions that are about to expire and send reminders"""
    try:
        premium_manager = PremiumManager("group_manager.db")
        expiring_groups = premium_manager.get_expiring_subscriptions(days=3)

        for group in expiring_groups:
            group_id = group['group_id']
            days_left = group['days_left']

            reminder_message = f"""⚠️ *هشدار انقضای اشتراک*

📅 اشتراک پرمیوم این گروه تا *{days_left} روز دیگر* منقضی می‌شود.

💎 برای تمدید اشتراک با ادمین تماس بگیرید:
[@{SUBSCRIPTION_CONTACT_USERNAME}](https://t.me/{SUBSCRIPTION_CONTACT_USERNAME})

🆔 آیدی گروه: `{group_id}`"""

            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    text=reminder_message,
                    parse_mode='Markdown'
                )
                logger.info(f"Sent expiration reminder to group {group_id} ({days_left} days left)")
            except Exception as e:
                logger.error(f"Failed to send expiration reminder to group {group_id}: {str(e)}")

    except Exception as e:
        logger.error(f"Error in check_expiring_subscriptions: {str(e)}")

# اضافه کردن این متغیر در بالای فایل
PAYMENT_CARD_NUMBER = "6037-XXXX-XXXX-XXXX"  # شماره کارت برای پرداخت

async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription purchase process"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "این دستور فقط در گروه‌ها قابل استفاده است.\n\n"
                "برای خرید اشتراک، ابتدا ربات را به گروه خود اضافه کنید و سپس این دستور را در گروه اجرا کنید."
            )
            return

        group_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Check if user is admin in the group
        chat_member = await context.bot.get_chat_member(group_id, user_id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند اشتراک خریداری کنند.")
            return
        
        # Create subscription plan buttons
        keyboard = []
        for plan_key, plan_info in SUBSCRIPTION_PLANS.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"💎 {plan_info['name']}: {plan_info['price']:,} تومان ({plan_info['days']} روز)", 
                    callback_data=f"buy_plan_{plan_key}_{group_id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🛒 *خرید اشتراک پرمیوم*\n\n"
            "لطفاً پلن مورد نظر خود را انتخاب کنید:\n",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in buy_subscription: {str(e)}")
        await update.message.reply_text("خطایی در فرآیند خرید اشتراک رخ داد.")

async def sub_handle_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription purchase callbacks"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("buy_plan_"):
            # Extract plan and group info
            _, plan_key, group_id = data.split("_", 2)
            group_id = int(group_id)
            
            plan_info = SUBSCRIPTION_PLANS.get(plan_key)
            if not plan_info:
                await query.edit_message_text("پلن انتخابی نامعتبر است. لطفاً دوباره تلاش کنید.")
                return
            
            # Create payment message
            payment_message = f"💳 *اطلاعات پرداخت*\n\n"
            payment_message += f"📋 پلن انتخابی: *{plan_info['name']}*\n"
            payment_message += f"💰 مبلغ قابل پرداخت: *{plan_info['price']:,} تومان*\n"
            payment_message += f"⏱ مدت اشتراک: *{plan_info['days']} روز*\n\n"
            payment_message += f"🏦 شماره کارت: `{PAYMENT_CARD_NUMBER}`\n\n"
            payment_message += f"🆔 آیدی گروه: `{group_id}`\n\n"
            payment_message += "پس از پرداخت، لطفاً رسید پرداخت را به همراه آیدی گروه به ادمین ارسال کنید:\n"
            payment_message += f"👨‍💼 @{SUBSCRIPTION_CONTACT_USERNAME}\n\n"
            payment_message += "⚠️ *نکته مهم*: پس از تأیید پرداخت توسط ادمین، اشتراک شما فعال خواهد شد."
            
            # Create back button
            keyboard = [[
                InlineKeyboardButton("🔙 بازگشت", callback_data=f"back_to_plans_{group_id}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                payment_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        elif data.startswith("back_to_plans_"):
            # Extract group id
            _, group_id = data.split("_", 3)
            group_id = int(group_id)
            
            # Recreate subscription plan buttons
            keyboard = []
            for plan_key, plan_info in SUBSCRIPTION_PLANS.items():
                keyboard.append([
                    InlineKeyboardButton(
                        f"💎 {plan_info['name']}: {plan_info['price']:,} تومان ({plan_info['days']} روز)", 
                        callback_data=f"buy_plan_{plan_key}_{group_id}"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🛒 *خرید اشتراک پرمیوم*\n\n"
                "لطفاً پلن مورد نظر خود را انتخاب کنید:\n",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    except Exception as e:
        logger.error(f"Error in sub_handle_subscription_callback: {str(e)}")
        await query.edit_message_text("خطایی در پردازش درخواست رخ داد. لطفاً دوباره تلاش کنید.")

# ======================================================================
# بخش: handlers/advanced_features.py
# ======================================================================
logger = logging.getLogger(__name__)

# Global dictionaries to store locks and muted users
locked_groups = {}
force_join_channels = {}
muted_users = {}  # {group_id: {user_id: {'until': datetime, 'task': asyncio.Task}}}

# Initialize premium manager
premium_manager = PremiumManager("group_manager.db")

async def mute_user_timed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute user for specified time duration"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return

        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return

        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return

        # Log the context args for debugging
        logger.info(f"Mute command context args: {context.args}")

        if not context.args:
            await update.message.reply_text(
                "استفاده: سکوت <مدت به ثانیه>\n"
                "مثال: سکوت 1800 (سکوت برای 30 دقیقه)\n"
                "حداکثر: 86400 ثانیه (24 ساعت)"
            )
            return

        try:
            duration = int(context.args[0])
            if duration <= 0 or duration > 86400:  # Max 24 hours
                await update.message.reply_text("مدت زمان باید بین 1 تا 86400 ثانیه (24 ساعت) باشد.")
                return
        except ValueError:
            await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید.")
            return

        user_to_mute = update.message.reply_to_message.from_user
        group_id = update.effective_chat.id

        # Don't mute admins
        target_member = await context.bot.get_chat_member(group_id, user_to_mute.id)
        if target_member.status in ['administrator', 'creator']:
            await update.message.reply_text("نمی‌توان ادمین‌ها را سکوت کرد.")
            return

        # Don't mute the main admin
        if user_to_mute.id == ADMIN_ID:
            await update.message.reply_text("نمی‌توان ادمین اصلی را سکوت کرد.")
            return

        # Set user permissions to muted
        mute_permissions = ChatPermissions(
            can_send_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False
        )

        # Calculate unmute time
        unmute_time = datetime.now() + timedelta(seconds=duration)

        # Restrict user
        await context.bot.restrict_chat_member(
            chat_id=group_id,
            user_id=user_to_mute.id,
            permissions=mute_permissions,
            until_date=unmute_time
        )

        # Store mute info
        if group_id not in muted_users:
            muted_users[group_id] = {}

        # Cancel previous mute task if exists
        if user_to_mute.id in muted_users[group_id]:
            old_task = muted_users[group_id][user_to_mute.id].get('task')
            if old_task and not old_task.done():
                old_task.cancel()

        # Create auto-unmute task
        unmute_task = asyncio.create_task(
            af_auto_unmute_user(context, group_id, user_to_mute.id, duration)
        )

        muted_users[group_id][user_to_mute.id] = {
            'until': unmute_time,
            'muted_by': update.effective_user.id,
            'muted_by_name': update.effective_user.first_name,
            'task': unmute_task
        }

        # Format time display
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60

        time_str = ""
        if hours > 0:
            time_str += f"{hours} ساعت "
        if minutes > 0:
            time_str += f"{minutes} دقیقه "
        if seconds > 0:
            time_str += f"{seconds} ثانیه"

        await update.message.reply_text(
            f"🔇 کاربر {user_to_mute.first_name} برای {time_str} سکوت شد.\n"
            f"⏰ باز شدن خودکار: {unmute_time.strftime('%H:%M:%S')}\n"
            f"👤 سکوت شده توسط: {update.effective_user.first_name}"
        )

        logger.info(f"User {user_to_mute.id} muted in group {group_id} for {duration} seconds by user {update.effective_user.id}")

    except BadRequest as e:
        if "not enough rights" in str(e).lower():
            await update.message.reply_text("ربات دسترسی کافی برای سکوت کردن کاربران ندارد.")
        else:
            await update.message.reply_text(f"خطا در سکوت کردن کاربر: {str(e)}")
        logger.error(f"BadRequest in mute_user_timed: {str(e)}")
    except Forbidden as e:
        await update.message.reply_text("ربات مسدود شده یا دسترسی ندارد.")
        logger.error(f"Forbidden in mute_user_timed: {str(e)}")
    except Exception as e:
        logger.error(f"Error in mute_user_timed: {str(e)}")
        await update.message.reply_text(f"خطا در سکوت کردن کاربر: {str(e)}")

async def af_unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unmute user manually"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return

        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return

        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return

        user_to_unmute = update.message.reply_to_message.from_user
        group_id = update.effective_chat.id

        # Check if user is muted
        if group_id not in muted_users or user_to_unmute.id not in muted_users[group_id]:
            await update.message.reply_text("این کاربر سکوت نیست.")
            return

        # Restore normal permissions
        normal_permissions = ChatPermissions(
            can_send_messages=True,
            #   # این پارامتر دیگر پشتیبانی نمی‌شود
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            # اضافه کردن پارامترهای جدید
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True
        )

        await context.bot.restrict_chat_member(
            chat_id=group_id,
            user_id=user_to_unmute.id,
            permissions=normal_permissions
        )

        # Cancel auto-unmute task
        mute_info = muted_users[group_id][user_to_unmute.id]
        if 'task' in mute_info and not mute_info['task'].done():
            mute_info['task'].cancel()

        # Remove from muted users
        del muted_users[group_id][user_to_unmute.id]
        if not muted_users[group_id]:
            del muted_users[group_id]

        await update.message.reply_text(f"🔊 کاربر {user_to_unmute.first_name} از حالت سکوت خارج شد.")

        logger.info(f"User {user_to_unmute.id} unmuted manually in group {group_id}")

    except Exception as e:
        logger.error(f"Error in af_unmute_user: {str(e)}")
        await update.message.reply_text(f"خطا در خارج کردن کاربر از حالت سکوت: {str(e)}")

async def af_auto_unmute_user(context: ContextTypes.DEFAULT_TYPE, group_id: int, user_id: int, duration: int):
    """Automatically unmute user after specified duration"""
    try:
        await asyncio.sleep(duration)

        if group_id in muted_users and user_id in muted_users[group_id]:
            # Restore normal permissions
            normal_permissions = ChatPermissions(
                can_send_messages=True,
                
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )

            await context.bot.restrict_chat_member(
                chat_id=group_id,
                user_id=user_id,
                permissions=normal_permissions
            )

            # Get user info for notification
            try:
                user_info = await context.bot.get_chat_member(group_id, user_id)
                user_name = user_info.user.first_name
            except:
                user_name = "کاربر"

            # Send notification
            await context.bot.send_message(
                chat_id=group_id,
                text=f"🔊 سکوت کاربر {user_name} به صورت خودکار برداشته شد."
            )

            # Remove from muted users
            del muted_users[group_id][user_id]
            if not muted_users[group_id]:
                del muted_users[group_id]

            logger.info(f"User {user_id} auto-unmuted in group {group_id} after {duration} seconds")

    except Exception as e:
        logger.error(f"Error in af_auto_unmute_user for user {user_id} in group {group_id}: {str(e)}")

async def lock_time_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lock group for specified time duration"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return

        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return

        if not context.args:
            await update.message.reply_text(
                "استفاده: /locktime <مدت به ثانیه>\n"
                "مثال: /locktime 3600 (قفل برای 1 ساعت)\n"
                "یا: قفل_زمانی 1800 (قفل برای 30 دقیقه)"
            )
            return

        try:
            duration = int(context.args[0])
            if duration <= 0 or duration > 86400:  # Max 24 hours
                await update.message.reply_text("مدت زمان باید بین 1 تا 86400 ثانیه (24 ساعت) باشد.")
                return
        except ValueError:
            await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید.")
            return

        group_id = update.effective_chat.id

        # Set group permissions to read-only
        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False
        )

        await context.bot.set_chat_permissions(group_id, permissions)

        # Store lock info
        unlock_time = datetime.now() + timedelta(seconds=duration)
        locked_groups[group_id] = {
            'unlock_time': unlock_time,
            'locked_by': update.effective_user.id,
            'locked_by_name': update.effective_user.first_name
        }

        # Schedule unlock
        asyncio.create_task(auto_unlock_group(context, group_id, duration))

        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60

        time_str = ""
        if hours > 0:
            time_str += f"{hours} ساعت "
        if minutes > 0:
            time_str += f"{minutes} دقیقه "
        if seconds > 0:
            time_str += f"{seconds} ثانیه"

        await update.message.reply_text(
            f"🔒 گروه برای {time_str} قفل شد.\n"
            f"⏰ باز شدن خودکار: {unlock_time.strftime('%H:%M:%S')}\n"
            f"👤 قفل شده توسط: {update.effective_user.first_name}"
        )

        logger.info(f"Group {group_id} locked for {duration} seconds by user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error in lock_time_messages: {str(e)}")
        await update.message.reply_text(f"خطا در قفل کردن گروه: {str(e)}")

async def unlock_time_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unlock group manually"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return

        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return

        group_id = update.effective_chat.id

        # حذف این بررسی تا دستور در هر حالتی کار کند
        # if group_id not in locked_groups:
        #     await update.message.reply_text("گروه قفل نیست.")
        #     return

        # Restore normal permissions
        permissions = ChatPermissions(
            can_send_messages=True,
            #   # این پارامتر دیگر پشتیبانی نمی‌شود
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False,
            # اضافه کردن پارامترهای جدید
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True
        )

        await context.bot.set_chat_permissions(group_id, permissions)

        # Remove from locked groups if exists
        if group_id in locked_groups:
            del locked_groups[group_id]

        await update.message.reply_text(
            f"🔓 قفل گروه توسط {update.effective_user.first_name} باز شد."
        )

        logger.info(f"Group {group_id} unlocked manually by user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error in unlock_time_messages: {str(e)}")
        await update.message.reply_text(f"خطا در باز کردن قفل گروه: {str(e)}")

async def auto_unlock_group(context: ContextTypes.DEFAULT_TYPE, group_id: int, duration: int):
    """Automatically unlock group after specified duration"""
    try:
        await asyncio.sleep(duration)

        if group_id in locked_groups:
            # Restore normal permissions
            permissions = ChatPermissions(
                can_send_messages=True,
                
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )

            await context.bot.set_chat_permissions(group_id, permissions)

            # Send notification
            await context.bot.send_message(
                chat_id=group_id,
                text="🔓 قفل گروه به صورت خودکار باز شد."
            )

            # Remove from locked groups
            del locked_groups[group_id]

            logger.info(f"Group {group_id} auto-unlocked after {duration} seconds")

    except Exception as e:
        logger.error(f"Error in auto_unlock_group for group {group_id}: {str(e)}")

async def set_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set force join channel for group"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return

        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return

        if not context.args:
            await update.message.reply_text(
                "استفاده: /forcejoin <channel_username>\n"
                "مثال: /forcejoin @mychannel\n"
                "یا: جوین_اجباری @mychannel"
            )
            return

        channel_username = context.args[0]
        if not channel_username.startswith('@'):
            channel_username = '@' + channel_username

        group_id = update.effective_chat.id

        # Test if channel exists and bot has access
        try:
            channel_info = await context.bot.get_chat(channel_username)
            force_join_channels[group_id] = {
                'channel_id': channel_info.id,
                'channel_username': channel_username,
                'channel_title': channel_info.title
            }

            await update.message.reply_text(
                f"✅ جوین اجباری چنل تنظیم شد.\n"
                f"📢 چنل: {channel_info.title} ({channel_username})\n"
                f"⚠️ کاربران باید عضو این چنل باشند تا بتوانند پیام ارسال کنند."
            )

            logger.info(f"Force join set for group {group_id} to channel {channel_username}")

        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا در تنظیم جوین اجباری:\n"
                f"• چنل وجود ندارد یا عمومی نیست\n"
                f"• ربات عضو چنل نیست\n"
                f"• نام کاربری چنل اشتباه است\n\n"
                f"خطا: {str(e)}"
            )

    except Exception as e:
        logger.error(f"Error in set_force_join: {str(e)}")
        await update.message.reply_text(f"خطا در تنظیم جوین اجباری: {str(e)}")

async def unset_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove force join channel for group"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return

        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return

        group_id = update.effective_chat.id

        if group_id not in force_join_channels:
            await update.message.reply_text("جوین اجباری برای این گروه تنظیم نشده است.")
            return

        channel_info = force_join_channels[group_id]
        del force_join_channels[group_id]

        await update.message.reply_text(
            f"✅ جوین اجباری حذف شد.\n"
            f"📢 چنل قبلی: {channel_info['channel_title']} ({channel_info['channel_username']})"
        )

        logger.info(f"Force join removed for group {group_id}")

    except Exception as e:
        logger.error(f"Error in unset_force_join: {str(e)}")
        await update.message.reply_text(f"خطا در حذف جوین اجباری: {str(e)}")

async def check_force_join_compliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user has joined required channel"""
    try:
        group_id = update.effective_chat.id

        if group_id not in force_join_channels:
            return

        user_id = update.effective_user.id
        channel_info = force_join_channels[group_id]

        # Check if user is member of required channel
        try:
            member_status = await context.bot.get_chat_member(
                channel_info['channel_id'],
                user_id
            )

            if member_status.status in ['left', 'kicked']:
                # Delete user's message
                await context.bot.delete_message(
                    chat_id=group_id,
                    message_id=update.message.message_id
                )

                # Send warning message
                warning_msg = await context.bot.send_message(
                    chat_id=group_id,
                    text=f"⚠️ {update.effective_user.first_name} عزیز!\n"
                         f"برای ارسال پیام در این گروه، ابتدا باید عضو چنل زیر شوید:\n\n"
                         f"📢 {channel_info['channel_title']}\n"
                         f"🔗 {channel_info['channel_username']}\n\n"
                         f"پس از عضویت، دوباره پیام خود را ارسال کنید."
                )

                # Delete warning message after 10 seconds
                asyncio.create_task(delete_message_after_delay(context, group_id, warning_msg.message_id, 10))

        except Exception as e:
            logger.error(f"Error checking force join compliance: {str(e)}")

    except Exception as e:
        logger.error(f"Error in check_force_join_compliance: {str(e)}")

async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
    """Delete message after specified delay"""
    try:
        await asyncio.sleep(delay)
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(f"Error deleting message after delay: {str(e)}")


async def delete_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete service messages like join/leave notifications"""
    try:
        # Delete the service message
        await update.message.delete()
    except Exception as e:
        logger.error(f"Error in delete_service_message: {str(e)}")

async def premium_delete_service_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete service message with premium check"""
    if update.effective_chat.type == "private":
        return
    
    group_id = update.effective_chat.id
    
    # Check if group is premium
    
    # If premium, delete the service message
    return await delete_service_message(update, context)

# ======================================================================
# بخش: handlers/moderation.py
# ======================================================================
logger = logging.getLogger(__name__)

async def mute_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute a user for a specified duration."""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if message text starts with "سکوت"
        if not update.message.text or not update.message.text.strip().startswith("سکوت"):
            return  # Not a mute command, ignore
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return
        
        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return
        
        # Extract the command text
        command_text = update.message.text.strip()
        parts = command_text.split()
        
        # Check if the command is valid
        if len(parts) != 2 or parts[0] != "سکوت" or not parts[1].isdigit():
            await update.message.reply_text(
                "فرمت نادرست است. لطفاً از فرمت 'سکوت <مدت زمان>' استفاده کنید.\n"
                "مثال: سکوت 1800 (برای 30 دقیقه)"
            )
            return
        
        duration = int(parts[1])  # Get the duration in seconds
        
        # Validate duration (max 24 hours)
        if duration <= 0 or duration > 86400:
            await update.message.reply_text("مدت زمان باید بین 1 تا 86400 ثانیه (24 ساعت) باشد.")
            return
        
        user_to_mute = update.message.reply_to_message.from_user
        
        # Don't mute admins
        target_member = await context.bot.get_chat_member(update.effective_chat.id, user_to_mute.id)
        if target_member.status in ['administrator', 'creator']:
            await update.message.reply_text("نمی‌توان ادمین‌ها را سکوت کرد.")
            return
        
        # Don't mute the main admin
        if user_to_mute.id == ADMIN_ID:
            await update.message.reply_text("نمی‌توان ادمین اصلی را سکوت کرد.")
            return
        
        # Set chat permissions to mute the user
        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_to_mute.id,
            permissions=permissions,
            until_date=int(time.time()) + duration  # Mute until the specified duration
        )
        
        # Format time display for user-friendly message
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        
        time_str = ""
        if hours > 0:
            time_str += f"{hours} ساعت "
        if minutes > 0:
            time_str += f"{minutes} دقیقه "
        if seconds > 0:
            time_str += f"{seconds} ثانیه"
        
        await update.message.reply_text(
            f"🔇 کاربر {user_to_mute.first_name} برای {time_str} سکوت شد.\n"
            f"👤 سکوت شده توسط: {update.effective_user.first_name}"
        )
        
        logger.info(f"User {user_to_mute.id} muted in group {update.effective_chat.id} for {duration} seconds by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in mute_user_handler: {str(e)}")
        await update.message.reply_text(f"خطا در سکوت کردن کاربر: {str(e)}")

def register_mute_handler(application: Application):
    """Register the mute handler with the application."""
    # Add a message handler that checks for messages starting with "سکوت"
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^سکوت \d+$") & ~filters.COMMAND,
            mute_user_handler
        )
    )
    logger.info("Mute handler registered")


async def promote_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Promote a user to administrator."""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if message text starts with "ارتقا"
        if not update.message.text or not update.message.text.strip().startswith("ارتقا"):
            return  # Not a promote command, ignore
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return
        
        # Check if admin has promote permission
        if chat_member.status == 'administrator' and not chat_member.can_promote_members:
            await update.message.reply_text("شما دسترسی ارتقای کاربران به ادمین را ندارید.")
            return
        
        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return
        
        user_to_promote = update.message.reply_to_message.from_user
        
        # Don't promote the bot itself
        if user_to_promote.id == context.bot.id:
            await update.message.reply_text("نمی‌توان ربات را ارتقا داد.")
            return
        
        # Check if user is already an admin
        target_member = await context.bot.get_chat_member(update.effective_chat.id, user_to_promote.id)
        if target_member.status in ['administrator', 'creator']:
            await update.message.reply_text("این کاربر در حال حاضر ادمین است.")
            return
        
        # Promote the user with basic permissions
        await context.bot.promote_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_to_promote.id,
            can_delete_messages=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_video_chats=True
        )
        
        await update.message.reply_text(
            f"🎉 <b>ارتقای موفقیت‌آمیز!</b>\n\n"
            f"👑 <b>{user_to_promote.first_name}</b> اکنون ادمین گروه است\n"
            f"🔑 <b>دسترسی‌های جدید:</b>\n"
            f"   • حذف پیام‌ها\n"
            f"   • محدود کردن کاربران\n"
            f"   • دعوت کاربران جدید\n"
            f"   • پین کردن پیام‌ها\n"
            f"   • مدیریت ویدیو چت\n\n"
            f"👤 <b>ارتقا داده شده توسط:</b> {update.effective_user.first_name}",
            parse_mode='HTML'
        )
        
        logger.info(f"User {user_to_promote.id} promoted to admin in group {update.effective_chat.id} by user {update.effective_user.id}")
        
    except BadRequest as e:
        error_msg = str(e)
        if "not enough rights" in error_msg.lower():
            await update.message.reply_text("ربات دسترسی کافی برای ارتقا ندارد.")
        elif "user_not_mutual_contact" in error_msg.lower():
            await update.message.reply_text("کاربر با ربات در تماس نیست.")
        else:
            await update.message.reply_text(f"خطا در ارتقای کاربر: {error_msg}")
        logger.error(f"Error promoting user: {error_msg}")
    except Exception as e:
        await update.message.reply_text(f"خطا در ارتقای کاربر: {str(e)}")
        logger.error(f"Error promoting user: {str(e)}")

async def demote_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demote an administrator to regular user."""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if message text starts with "عزل"
        if not update.message.text or not update.message.text.strip().startswith("عزل"):
            return  # Not a demote command, ignore
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return
        
        # Check if admin has promote permission (needed for demote as well)
        if chat_member.status == 'administrator' and not chat_member.can_promote_members:
            await update.message.reply_text("شما دسترسی عزل ادمین‌ها را ندارید.")
            return
        
        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return
        
        user_to_demote = update.message.reply_to_message.from_user
        
        # Don't demote the bot itself
        if user_to_demote.id == context.bot.id:
            await update.message.reply_text("نمی‌توان ربات را عزل کرد.")
            return
        
        # Check if user is an admin
        target_member = await context.bot.get_chat_member(update.effective_chat.id, user_to_demote.id)
        if target_member.status not in ['administrator']:
            await update.message.reply_text("این کاربر ادمین نیست.")
            return
        
        # Don't demote the creator
        if target_member.status == 'creator':
            await update.message.reply_text("نمی‌توان سازنده گروه را عزل کرد.")
            return
        
        # Demote the user
        await context.bot.promote_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_to_demote.id,
            can_change_info=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_video_chats=False,
            can_manage_topics=False
        )
        
        await update.message.reply_text(
            f"📉 <b>عزل انجام شد</b>\n\n"
            f"⬇️ <b>{user_to_demote.first_name}</b> از ادمینی گروه عزل شد\n"
            f"🔒 <b>دسترسی‌های حذف شده:</b>\n"
            f"   • حذف پیام‌ها\n"
            f"   • محدود کردن کاربران\n"
            f"   • دعوت کاربران\n"
            f"   • پین کردن پیام‌ها\n"
            f"   • مدیریت ویدیو چت\n\n"
            f"👤 <b>عزل شده توسط:</b> {update.effective_user.first_name}",
            parse_mode='HTML'
        )
        
        logger.info(f"User {user_to_demote.id} demoted from admin in group {update.effective_chat.id} by user {update.effective_user.id}")
        
    except BadRequest as e:
        error_msg = str(e)
        if "not enough rights" in error_msg.lower():
            await update.message.reply_text("ربات دسترسی کافی برای عزل ندارد.")
        elif "user_not_mutual_contact" in error_msg.lower():
            await update.message.reply_text("کاربر با ربات در تماس نیست.")
        else:
            await update.message.reply_text(f"خطا در عزل کاربر: {error_msg}")
        logger.error(f"Error demoting user: {error_msg}")
    except Exception as e:
        await update.message.reply_text(f"خطا در عزل کاربر: {str(e)}")
        logger.error(f"Error demoting user: {str(e)}")
async def special_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Give special permissions to a user."""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if message text starts with "ویژه"
        if not update.message.text or not update.message.text.strip().startswith("ویژه"):
            return  # Not a special command, ignore
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return
        
        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return
        
        user_to_special = update.message.reply_to_message.from_user
        
        # Check if bot has admin permissions
        bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        if not bot_member.can_restrict_members:
            await update.message.reply_text("ربات دسترسی لازم برای تغییر دسترسی‌های کاربران را ندارد.")
            return
        
        # Set special permissions for the user
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=True
        )
        
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_to_special.id,
            permissions=permissions
        )
        
        await update.message.reply_text(
            f"⭐ <b>دسترسی ویژه اعطا شد!</b>\n\n"
            f"✨ <b>{user_to_special.first_name}</b> دسترسی‌های ویژه دریافت کرد\n"
            f"🎯 <b>دسترسی‌های جدید:</b>\n"
            f"   • ارسال پیام‌ها\n"
            f"   • ارسال نظرسنجی\n"
            f"   • ارسال محتوای ویژه\n"
            f"   • دعوت کاربران\n"
            f"   • پین کردن پیام‌ها\n\n"
            f"👤 <b>تنظیم شده توسط:</b> {update.effective_user.first_name}",
            parse_mode='HTML'
        )
        
        logger.info(f"Special permissions given to user {user_to_special.id} in group {update.effective_chat.id} by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in special_user_handler: {str(e)}")
        await update.message.reply_text(f"خطا در تنظیم دسترسی‌های ویژه: {str(e)}")

async def remove_special_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove special permissions from a user."""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if message text starts with "حذف ویژه"
        if not update.message.text or not update.message.text.strip().startswith("حذف ویژه"):
            return  # Not a remove special command, ignore
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return
        
        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return
        
        user_to_remove_special = update.message.reply_to_message.from_user
        
        # Check if bot has admin permissions
        bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        if not bot_member.can_restrict_members:
            await update.message.reply_text("ربات دسترسی لازم برای تغییر دسترسی‌های کاربران را ندارد.")
            return
        
        # Get default chat permissions
        chat = await context.bot.get_chat(update.effective_chat.id)
        default_permissions = chat.permissions
        
        # Apply default permissions to the user
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_to_remove_special.id,
            permissions=default_permissions
        )
        
        await update.message.reply_text(
            f"🚫 وضعیت ویژه کاربر {user_to_remove_special.first_name} حذف شد و به حالت عادی برگشت.\n"
            f"👤 حذف شده توسط: {update.effective_user.first_name}"
        )
        
        logger.info(f"Special status removed from user {user_to_remove_special.id} in group {update.effective_chat.id} by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in remove_special_user_handler: {str(e)}")
        await update.message.reply_text(f"خطا در حذف وضعیت ویژه کاربر: {str(e)}")

def register_handlers(application: Application):
    """Register all moderation handlers with the application."""
    # Add a message handler that checks for messages starting with "سکوت"
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^سکوت \d+$") & ~filters.COMMAND,
            mute_user_handler
        )
    )
    logger.info("Mute handler registered")


    # Add a message handler that checks for messages starting with "ارتقا"
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^ارتقا$") & ~filters.COMMAND,
            promote_user_handler
        )
    )
    logger.info("Promote handler registered")


    # Add a message handler that checks for messages starting with "عزل"
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^عزل$") & ~filters.COMMAND,
            demote_user_handler
        )
    )
    logger.info("Demote handler registered")


    # Add a message handler that checks for messages starting with "ویژه"
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^ویژه$") & ~filters.COMMAND,
            special_user_handler
        )
    )
    logger.info("Special user handler registered")

    # Add a message handler for removing special status
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^حذف ویژه$") & ~filters.COMMAND,
            remove_special_user_handler
        )
    )

# ======================================================================
# بخش: handlers/broadcast.py
# ======================================================================
logger = logging.getLogger(__name__)

async def admin_broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast command for admin"""
    try:
        # Check if user is main admin
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین اصلی می‌تواند پیام همگانی ارسال کند.")
            return
        
        # Check if message is provided
        if not context.args:
            await update.message.reply_text(
                "استفاده: /broadcast <پیام>\n\n"
                "مثال: /broadcast سلام به همه گروه‌ها!\n\n"
                "این پیام به تمام گروه‌های پرمیوم که ربات در آن‌ها ادمین است ارسال خواهد شد."
            )
            return
        
        # Import here to avoid circular imports
        
        # Get the message to broadcast
        broadcast_text = " ".join(context.args)
        
        # Initialize premium manager
        premium_manager = PremiumManager("group_manager.db")
        
        # Get all premium groups
        premium_groups = premium_manager.get_all_premium_groups()
        active_groups = [
            group for group in premium_groups 
            if group['is_active'] and premium_manager.is_group_premium(group['group_id'])
        ]
        
        if not active_groups:
            await update.message.reply_text("هیچ گروه پرمیوم فعالی یافت نشد.")
            return
        
        # Send broadcast message
        success_count = 0
        failed_count = 0
        failed_groups = []
        
        status_message = await update.message.reply_text(
            f"🔄 در حال ارسال پیام به {len(active_groups)} گروه پرمیوم..."
        )
        
        for group in active_groups:
            group_id = group['group_id']
            try:
                # Check if bot is admin in the group
                bot_member = await context.bot.get_chat_member(group_id, context.bot.id)
                if bot_member.status not in ['administrator', 'creator']:
                    failed_count += 1
                    failed_groups.append(f"{group_id} (ربات ادمین نیست)")
                    continue
                
                # Send the broadcast message
                await context.bot.send_message(
                    chat_id=group_id,
                    text=f"📢 پیام همگانی از ادمین:\n\n{broadcast_text}",
                    parse_mode='Markdown'
                )
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                failed_groups.append(f"{group_id} ({str(e)[:50]})")
                logger.error(f"Failed to send broadcast to group {group_id}: {str(e)}")
        
        # Update status message with results
        result_text = f"✅ پیام همگانی ارسال شد!\n\n"
        result_text += f"📊 نتایج:\n"
        result_text += f"• موفق: {success_count} گروه\n"
        result_text += f"• ناموفق: {failed_count} گروه\n"
        
        if failed_groups and len(failed_groups) <= 5:
            result_text += f"\n❌ گروه‌های ناموفق:\n"
            for failed_group in failed_groups[:5]:
                result_text += f"• {failed_group}\n"
        elif failed_groups:
            result_text += f"\n❌ {len(failed_groups)} گروه ناموفق (جزئیات در لاگ)"
        
        await status_message.edit_text(result_text)
        
    except Exception as e:
        logger.error(f"Error in admin_broadcast_handler: {str(e)}")
        await update.message.reply_text(f"خطا در ارسال پیام همگانی: {str(e)}")

# ======================================================================
# بخش: handlers/user_reports.py
# ======================================================================
logger = logging.getLogger(__name__)
db = Database("group_manager.db")

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور گزارش پیام"""
    try:
        # بررسی اینکه آیا پیام ریپلای شده است
        if not update.message.reply_to_message:
            await update.message.reply_text("برای گزارش، باید روی پیام مورد نظر ریپلای کنید.")
            return
            
        # دریافت اطلاعات پیام و کاربر گزارش شده
        reported_message = update.message.reply_to_message
        reported_user = reported_message.from_user
        reporter_user = update.message.from_user
        group_id = update.effective_chat.id
        
        # دریافت متن گزارش (اختیاری)
        report_text = " ".join(context.args) if context.args else "بدون توضیحات"
        
        # ثبت گزارش در دیتابیس
        report_id = db.add_user_report(
            group_id=group_id,
            reported_user_id=reported_user.id,
            reporter_user_id=reporter_user.id,
            message_id=reported_message.message_id,
            report_text=report_text
        )
        
        # ارسال پیام تأیید به کاربر گزارش‌دهنده
        await update.message.reply_text(
            f"✅ گزارش شما با شناسه #{report_id} ثبت شد و توسط ادمین‌ها بررسی خواهد شد."
        )
        
        # ارسال گزارش به ادمین‌های گروه
        keyboard = [
            [InlineKeyboardButton("✅ تأیید", callback_data=f'report_approve_{report_id}')],
            [InlineKeyboardButton("❌ رد", callback_data=f'report_reject_{report_id}')],
            [InlineKeyboardButton("🔍 بررسی بیشتر", callback_data=f'report_details_{report_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # دریافت محتوای پیام گزارش شده
        reported_message_content = ""
        if reported_message.text:
            reported_message_content = reported_message.text
        elif reported_message.caption:
            reported_message_content = reported_message.caption
        elif reported_message.photo:
            reported_message_content = "[تصویر]"
        elif reported_message.video:
            reported_message_content = "[ویدیو]"
        elif reported_message.document:
            reported_message_content = f"[فایل: {reported_message.document.file_name}]"
        elif reported_message.sticker:
            reported_message_content = "[استیکر]"
        else:
            reported_message_content = "[محتوای نامشخص]"
        
        # ساخت متن گزارش برای ادمین‌ها
        admin_report = f"📣 گزارش جدید (#{report_id}):\n\n"
        admin_report += f"👤 گزارش‌دهنده: {reporter_user.first_name} (@{reporter_user.username or 'بدون یوزرنیم'})\n"
        admin_report += f"👤 کاربر گزارش‌شده: {reported_user.first_name} (@{reported_user.username or 'بدون یوزرنیم'})\n"
        admin_report += f"💬 متن گزارش: {report_text}\n\n"
        admin_report += f"📄 محتوای پیام گزارش شده:\n"
        admin_report += f"{reported_message_content}\n"
        
        # دریافت لیست ادمین‌های گروه
        try:
            chat_administrators = await context.bot.get_chat_administrators(group_id)
            admin_ids = [admin.user.id for admin in chat_administrators]
            admin_mentions = []
            
            # ساخت منشن برای هر ادمین
            for admin in chat_administrators:
                if not admin.user.is_bot:  # بات‌ها را منشن نکن
                    admin_mentions.append(f"[{admin.user.first_name}](tg://user?id={admin.user.id})")
            
            # اضافه کردن منشن ادمین‌ها به پیام
            if admin_mentions:
                admin_report += "\n🔔 ادمین‌های گروه: " + ", ".join(admin_mentions)
        except Exception as e:
            logger.error(f"Error getting chat administrators: {str(e)}")
        
        # ارسال به گروه
        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=admin_report,
                reply_markup=reply_markup,
                parse_mode="Markdown",
                reply_to_message_id=reported_message.message_id
            )
        except Exception as e:
            logger.error(f"Error sending report to group: {str(e)}")
            # اگر ارسال به گروه با خطا مواجه شد، به ADMIN_ID ارسال کن
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_report + "\n\n⚠️ خطا در ارسال به گروه",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        
    except Exception as e:
        logger.error(f"Error in report_command: {str(e)}")
        await update.message.reply_text(f"خطا در ثبت گزارش: {str(e)}")

async def report_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش دکمه‌های گزارش"""
    try:
        query = update.callback_query
        await query.answer()
        
        # دریافت شناسه گزارش و عملیات
        data = query.data.split('_')
        action = data[1]  # approve, reject, details
        report_id = int(data[2])
        
        # دریافت اطلاعات گزارش
        report = db.get_report_details(report_id)
        if not report:
            await query.message.edit_text("گزارش یافت نشد یا حذف شده است.")
            return
            
        if action == 'approve':
            # تأیید گزارش
            db.update_report_status(
                report_id=report_id,
                status='approved',
                admin_response="گزارش تأیید شد",
                admin_id=update.effective_user.id
            )
            
            # ویرایش پیام ادمین
            await query.message.edit_text(
                f"✅ گزارش #{report_id} تأیید شد.\n\n"
                f"👤 کاربر گزارش‌شده: {report['reported_user_id']}\n"
                f"💬 متن گزارش: {report['report_text']}",
                reply_markup=None
            )
            
            # ارسال پیام به کاربر گزارش‌دهنده
            try:
                await context.bot.send_message(
                    chat_id=report['reporter_user_id'],
                    text=f"✅ گزارش شما با شناسه #{report_id} بررسی و تأیید شد.\n\nاقدامات لازم انجام خواهد شد."
                )
            except Exception as e:
                logger.error(f"Error sending approval message to reporter: {str(e)}")
                
            # ریپلای به پیام گزارش‌شده با دکمه شیشه‌ای
            try:
                await context.bot.send_message(
                    chat_id=report['group_id'],
                    reply_to_message_id=report['message_id'],
                    text="✅ این پیام توسط ادمین بررسی و تأیید شد."
                )
            except Exception as e:
                logger.error(f"Error replying to reported message: {str(e)}")
                
        elif action == 'reject':
            # رد گزارش
            db.update_report_status(
                report_id=report_id,
                status='rejected',
                admin_response="گزارش رد شد",
                admin_id=update.effective_user.id
            )
            
            # ویرایش پیام ادمین
            await query.message.edit_text(
                f"❌ گزارش #{report_id} رد شد.\n\n"
                f"👤 کاربر گزارش‌شده: {report['reported_user_id']}\n"
                f"💬 متن گزارش: {report['report_text']}",
                reply_markup=None
            )
            
            # ارسال پیام به کاربر گزارش‌دهنده
            try:
                await context.bot.send_message(
                    chat_id=report['reporter_user_id'],
                    text=f"❌ گزارش شما با شناسه #{report_id} بررسی و رد شد.\n\nاین پیام مغایرتی با قوانین گروه ندارد."
                )
            except Exception as e:
                logger.error(f"Error sending rejection message to reporter: {str(e)}")
                
            # ریپلای به پیام گزارش‌شده با دکمه شیشه‌ای
            try:
                await context.bot.send_message(
                    chat_id=report['group_id'],
                    reply_to_message_id=report['message_id'],
                    text="❌ این پیام توسط ادمین بررسی و رد شد."
                )
            except Exception as e:
                logger.error(f"Error replying to reported message: {str(e)}")
                
        elif action == 'details':
            # نمایش جزئیات بیشتر گزارش
            details = f"🔍 جزئیات گزارش #{report_id}:\n\n"
            details += f"👤 گزارش‌دهنده: {report['reporter_user_id']}\n"
            details += f"👤 کاربر گزارش‌شده: {report['reported_user_id']}\n"
            details += f"💬 متن گزارش: {report['report_text']}\n"
            details += f"⏰ زمان گزارش: {report['report_time']}\n"
            details += f"📝 وضعیت: {report['status']}\n"
            
            keyboard = [
                [InlineKeyboardButton("✅ تأیید", callback_data=f'report_approve_{report_id}')],
                [InlineKeyboardButton("❌ رد", callback_data=f'report_reject_{report_id}')],
                [InlineKeyboardButton("بازگشت", callback_data=f'report_back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(details, reply_markup=reply_markup)
            
        elif action == 'back':
            # بازگشت به لیست گزارش‌ها (در نسخه کامل‌تر باید پیاده‌سازی شود)
            await query.message.edit_text("بازگشت به لیست گزارش‌ها...")
            
    except Exception as e:
        logger.error(f"Error in report_callback_handler: {str(e)}")
        await query.message.edit_text(f"خطا در پردازش گزارش: {str(e)}")

def setup_handlers(application):
    """تنظیم هندلرهای گزارش"""
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CallbackQueryHandler(report_callback_handler, pattern='^report_'))

# ======================================================================
# بخش: handlers/reports.py
# ======================================================================
logger = logging.getLogger(__name__)
db = Database("group_manager.db")

async def group_activity_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate activity report for a group"""
    try:
        if update.effective_chat.type == "private" and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("این دستور فقط برای ادمین اصلی قابل استفاده است.")
            return
            
        # Get group ID from args or current chat
        group_id = None
        if context.args and update.effective_user.id == ADMIN_ID:
            try:
                group_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("فرمت آیدی گروه نامعتبر است.")
                return
        else:
            group_id = update.effective_chat.id
            
        # Generate report
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        # Get statistics from database
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get message count for last week
        cursor.execute("""
            SELECT COUNT(*) FROM messages 
            WHERE group_id = ? AND timestamp > ?
        """, (group_id, week_ago.strftime("%Y-%m-%d %H:%M:%S")))
        message_count = cursor.fetchone()[0]
        
        # Get active users count
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM messages 
            WHERE group_id = ? AND timestamp > ?
        """, (group_id, week_ago.strftime("%Y-%m-%d %H:%M:%S")))
        active_users = cursor.fetchone()[0]
        
        # Get warning count
        cursor.execute("""
            SELECT COUNT(*) FROM warnings 
            WHERE group_id = ? AND timestamp > ?
        """, (group_id, week_ago.strftime("%Y-%m-%d %H:%M:%S")))
        warning_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Create report message
        report = f"📊 گزارش فعالیت گروه (۷ روز گذشته):\n\n"
        report += f"🔢 آیدی گروه: {group_id}\n"
        report += f"📝 تعداد پیام‌ها: {message_count}\n"
        report += f"👥 کاربران فعال: {active_users}\n"
        report += f"⚠️ اخطارهای صادر شده: {warning_count}\n"
        
        # Add buttons for more detailed reports
        keyboard = [
            [InlineKeyboardButton("📈 نمودار فعالیت", callback_data=f'activity_chart_{group_id}')],
            [InlineKeyboardButton("👤 کاربران فعال", callback_data=f'active_users_{group_id}')],
            [InlineKeyboardButton("⚠️ جزئیات اخطارها", callback_data=f'warning_details_{group_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(report, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in group_activity_report: {str(e)}")
        await update.message.reply_text(f"خطا در تهیه گزارش: {str(e)}")


async def reports_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callbacks for reports buttons"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Extract group_id from callback data
        if query.data.startswith('weekly_report_'):
            group_id = int(query.data.split('_')[-1])
            await handle_weekly_report(query, context, group_id)
            
        elif query.data.startswith('active_users_'):
            group_id = int(query.data.split('_')[-1])
            await handle_active_users(query, context, group_id)
            
        elif query.data.startswith('warning_details_'):
            group_id = int(query.data.split('_')[-1])
            await handle_warning_details(query, context, group_id)
            
        elif query.data.startswith('activity_chart_'):
            group_id = int(query.data.split('_')[-1])
            await handle_activity_chart(query, context, group_id)
            
    except Exception as e:
        logger.error(f"Error in reports_callback_handler: {str(e)}")
        await query.message.edit_text(f"خطایی رخ داد: {str(e)}")

async def handle_weekly_report(query, context, group_id):
    """Handle weekly report button"""
    try:
        # Get statistics from database for the last week
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get daily message counts for the last 7 days
        daily_messages = []
        for i in range(7):
            day = today - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            cursor.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE group_id = ? AND timestamp BETWEEN ? AND ?
            """, (group_id, day_start.strftime("%Y-%m-%d %H:%M:%S"), day_end.strftime("%Y-%m-%d %H:%M:%S")))
            count = cursor.fetchone()[0]
            daily_messages.append((day.strftime("%Y-%m-%d"), count))
        
        # Get top 5 active users
        cursor.execute("""
            SELECT user_id, COUNT(*) as msg_count FROM messages 
            WHERE group_id = ? AND timestamp > ?
            GROUP BY user_id ORDER BY msg_count DESC LIMIT 5
        """, (group_id, week_ago.strftime("%Y-%m-%d %H:%M:%S")))
        top_users = cursor.fetchall()
        
        # Get usernames for top users
        top_users_info = []
        for user_id, msg_count in top_users:
            cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            username = result[0] if result and result[0] else f"کاربر {user_id}"
            top_users_info.append((username, msg_count))
        
        conn.close()
        
        # Create report message
        report = f"📊 گزارش هفتگی گروه:\n\n"
        
        # Add daily message counts
        report += "📝 تعداد پیام‌ها در ۷ روز گذشته:\n"
        for date, count in reversed(daily_messages):
            report += f"{date}: {count} پیام\n"
        
        report += "\n👥 کاربران فعال برتر:\n"
        for i, (username, count) in enumerate(top_users_info, 1):
            report += f"{i}. {username}: {count} پیام\n"
        
        # Add back button
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data=f'stats_{group_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(report, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_weekly_report: {str(e)}")
        await query.message.edit_text(f"خطا در تهیه گزارش هفتگی: {str(e)}")

async def handle_active_users(query, context, group_id):
    """Handle active users button"""
    try:
        # Get active users from the last week
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get all users who sent messages in the last week
        cursor.execute("""
            SELECT u.user_id, u.username, u.first_name, COUNT(m.id) as msg_count 
            FROM users u JOIN messages m ON u.user_id = m.user_id
            WHERE m.group_id = ? AND m.timestamp > ?
            GROUP BY u.user_id ORDER BY msg_count DESC
        """, (group_id, week_ago.strftime("%Y-%m-%d %H:%M:%S")))
        active_users = cursor.fetchall()
        
        conn.close()
        
        # Create report message
        if not active_users:
            report = "👥 هیچ کاربر فعالی در هفته گذشته وجود نداشته است."
        else:
            report = f"👥 کاربران فعال در ۷ روز گذشته ({len(active_users)} کاربر):\n\n"
            
            for i, (user_id, username, first_name, msg_count) in enumerate(active_users, 1):
                display_name = username or first_name or f"کاربر {user_id}"
                report += f"{i}. {display_name}: {msg_count} پیام\n"
                
                # Add page break if list is too long
                if i % 20 == 0 and i < len(active_users):
                    report += "\n... ادامه دارد ...\n\n"
        
        # Add back button
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data=f'stats_{group_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(report, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_active_users: {str(e)}")
        await query.message.edit_text(f"خطا در نمایش کاربران فعال: {str(e)}")

async def handle_warning_details(query, context, group_id):
    """Handle warning details button"""
    try:
        # Get warnings from the last week
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get all warnings in the last week
        cursor.execute("""
            SELECT w.user_id, u.username, u.first_name, w.reason, w.timestamp, w.admin_id, a.username as admin_username
            FROM warnings w 
            JOIN users u ON w.user_id = u.user_id
            LEFT JOIN users a ON w.admin_id = a.user_id
            WHERE w.group_id = ? AND w.timestamp > ?
            ORDER BY w.timestamp DESC
        """, (group_id, week_ago.strftime("%Y-%m-%d %H:%M:%S")))
        warnings = cursor.fetchall()
        
        conn.close()
        
        # Create report message
        if not warnings:
            report = "⚠️ هیچ اخطاری در هفته گذشته ثبت نشده است."
        else:
            report = f"⚠️ اخطارهای ثبت شده در ۷ روز گذشته ({len(warnings)} اخطار):\n\n"
            
            for i, (user_id, username, first_name, reason, timestamp, admin_id, admin_username) in enumerate(warnings, 1):
                user_display = username or first_name or f"کاربر {user_id}"
                admin_display = admin_username or f"ادمین {admin_id}"
                report += f"{i}. کاربر: {user_display}\n"
                report += f"   دلیل: {reason or 'بدون دلیل'}\n"
                report += f"   زمان: {timestamp}\n"
                report += f"   توسط: {admin_display}\n\n"
                
                # Add page break if list is too long
                if i % 5 == 0 and i < len(warnings):
                    report += "... ادامه دارد ...\n\n"
        
        # Add back button
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data=f'stats_{group_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(report, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_warning_details: {str(e)}")
        await query.message.edit_text(f"خطا در نمایش جزئیات اخطارها: {str(e)}")

async def handle_activity_chart(query, context, group_id):
    """Handle activity chart button"""
    try:
        # Get message counts by hour for the last week
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get message counts by hour
        cursor.execute("""
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM messages 
            WHERE group_id = ? AND timestamp > ?
            GROUP BY hour
            ORDER BY hour
        """, (group_id, week_ago.strftime("%Y-%m-%d %H:%M:%S")))
        hourly_counts = cursor.fetchall()
        
        conn.close()
        
        # Create ASCII chart
        hours = [int(h) for h, _ in hourly_counts]
        counts = [c for _, c in hourly_counts]
        
        # Fill missing hours with zero
        full_hours = []
        full_counts = []
        for h in range(24):
            if h in hours:
                idx = hours.index(h)
                full_hours.append(h)
                full_counts.append(counts[idx])
            else:
                full_hours.append(h)
                full_counts.append(0)
        
        # Find max count for scaling
        max_count = max(full_counts) if full_counts else 0
        scale_factor = 10 / max_count if max_count > 0 else 0
        
        # Create chart
        chart = "📈 نمودار فعالیت گروه بر اساس ساعت (۷ روز گذشته):\n\n"
        
        for h, c in zip(full_hours, full_counts):
            bar_length = int(c * scale_factor)
            bar = "█" * bar_length
            chart += f"{h:02d}:00 | {bar} {c}\n"
        
        # Add back button
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data=f'stats_{group_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(chart, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in handle_activity_chart: {str(e)}")
        await query.message.edit_text(f"خطا در نمایش نمودار فعالیت: {str(e)}")

# ======================================================================
# بخش: handlers/admin_abuse.py
# ======================================================================
# اضافه کردن مسیر ریشه پروژه به sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# سپس بقیه import ها

logger = logging.getLogger(__name__)
db = Database("group_manager.db")

# تنظیمات آستانه‌های تخلف
ABUSE_THRESHOLDS = {
    "ban": {"count": 5, "time_window": 300},  # 5 بن در 5 دقیقه
    "kick": {"count": 7, "time_window": 300},  # 7 اخراج در 5 دقیقه
    "mute": {"count": 10, "time_window": 300},  # 10 سکوت در 5 دقیقه
    "delete": {"count": 15, "time_window": 300},  # 15 حذف پیام در 5 دقیقه
}

async def report_admin_abuse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """گزارش تخلف ادمین"""
    try:
        # بررسی اینکه آیا پیام ریپلای شده است
        if not update.message.reply_to_message:
            await update.message.reply_text("برای گزارش تخلف ادمین، باید روی پیام ادمین مورد نظر ریپلای کنید.")
            return
            
        # دریافت اطلاعات پیام و کاربر گزارش شده
        reported_message = update.message.reply_to_message
        reported_user = reported_message.from_user
        reporter_user = update.message.from_user
        group_id = update.effective_chat.id
        
        # بررسی اینکه آیا کاربر گزارش شده ادمین است
        chat_member = await context.bot.get_chat_member(group_id, reported_user.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("این کاربر ادمین نیست. برای گزارش تخلف ادمین‌ها از این دستور استفاده کنید.")
            return
        
        # دریافت متن گزارش (اختیاری)
        report_text = " ".join(context.args) if context.args else "بدون توضیحات"
        
        # ثبت گزارش در دیتابیس
        report_id = db.add_admin_abuse_report(
            group_id=group_id,
            admin_id=reported_user.id,
            reporter_id=reporter_user.id,
            message_id=reported_message.message_id,
            report_text=report_text
        )
        
        # ارسال پیام تأیید به کاربر گزارش‌دهنده
        await update.message.reply_text(
            f"✅ گزارش تخلف ادمین با شناسه #{report_id} ثبت شد و توسط مدیر گروه بررسی خواهد شد."
        )
        
        # ارسال گزارش به مدیر گروه
        keyboard = [
            [InlineKeyboardButton("✅ تأیید", callback_data=f'admin_abuse_approve_{report_id}')],
            [InlineKeyboardButton("❌ رد", callback_data=f'admin_abuse_reject_{report_id}')],
            [InlineKeyboardButton("🔍 بررسی بیشتر", callback_data=f'admin_abuse_details_{report_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # ساخت متن گزارش برای مدیر گروه
        admin_report = f"⚠️ گزارش تخلف ادمین (#{report_id}):\n\n"
        admin_report += f"👤 گزارش‌دهنده: {reporter_user.first_name} (@{reporter_user.username or 'بدون یوزرنیم'})\n"
        admin_report += f"👮‍♂️ ادمین گزارش‌شده: {reported_user.first_name} (@{reported_user.username or 'بدون یوزرنیم'})\n"
        admin_report += f"💬 متن گزارش: {report_text}\n\n"
        
        # دریافت آمار اقدامات ادمین در بازه زمانی اخیر
        admin_actions = db.get_admin_recent_actions(reported_user.id, group_id)
        if admin_actions:
            admin_report += f"📊 آمار اقدامات ادمین در 30 دقیقه اخیر:\n"
            admin_report += f"🚫 تعداد بن: {admin_actions.get('ban_count', 0)}\n"
            admin_report += f"👢 تعداد اخراج: {admin_actions.get('kick_count', 0)}\n"
            admin_report += f"🔇 تعداد سکوت: {admin_actions.get('mute_count', 0)}\n"
            admin_report += f"🗑️ تعداد حذف پیام: {admin_actions.get('delete_count', 0)}\n"
        
        # دریافت مدیر گروه
        try:
            chat_administrators = await context.bot.get_chat_administrators(group_id)
            creator = next((admin for admin in chat_administrators if admin.status == 'creator'), None)
            
            if creator:
                # ارسال به مدیر گروه
                try:
                    await context.bot.send_message(
                        chat_id=creator.user.id,
                        text=admin_report,
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Error sending report to group creator: {str(e)}")
                    # اگر ارسال به مدیر با خطا مواجه شد، به ADMIN_ID ارسال کن
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=admin_report + "\n\n⚠️ خطا در ارسال به مدیر گروه",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
            else:
                # اگر مدیر پیدا نشد، به ADMIN_ID ارسال کن
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=admin_report,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Error getting chat administrators: {str(e)}")
            # در صورت خطا به ADMIN_ID ارسال کن
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_report + "\n\n⚠️ خطا در دریافت لیست ادمین‌ها",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        
    except Exception as e:
        logger.error(f"Error in report_admin_abuse: {str(e)}")
        await update.message.reply_text(f"خطا در ثبت گزارش تخلف ادمین: {str(e)}")

async def admin_abuse_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش دکمه‌های گزارش تخلف ادمین"""
    try:
        query = update.callback_query
        await query.answer()
        
        # دریافت شناسه گزارش و عملیات
        data = query.data.split('_')
        action = data[2]  # approve, reject, details
        report_id = int(data[3])
        
        # دریافت اطلاعات گزارش
        report = db.get_admin_abuse_report(report_id)
        if not report:
            await query.message.edit_text("گزارش یافت نشد یا حذف شده است.")
            return
            
        if action == 'approve':
            # تأیید گزارش و محدود کردن دسترسی‌های ادمین
            db.update_admin_abuse_report_status(
                report_id=report_id,
                status='approved',
                admin_response="گزارش تأیید شد و دسترسی‌های ادمین محدود شد",
                responded_by=update.effective_user.id
            )
            
            # محدود کردن دسترسی‌های ادمین
            try:
                await context.bot.promote_chat_member(
                    chat_id=report['group_id'],
                    user_id=report['admin_id'],
                    can_change_info=False,
                    can_delete_messages=False,
                    can_restrict_members=False,
                    can_invite_users=True,
                    can_pin_messages=False,
                    can_promote_members=False,
                    can_manage_video_chats=False,
                    can_manage_topics=False
                )
                
                # ارسال پیام به گروه
                await context.bot.send_message(
                    chat_id=report['group_id'],
                    text=f"⚠️ به دلیل گزارش‌های متعدد تخلف، دسترسی‌های ادمین محدود شد."
                )
            except Exception as e:
                logger.error(f"Error restricting admin permissions: {str(e)}")
            
            # ویرایش پیام مدیر
            await query.message.edit_text(
                f"✅ گزارش تخلف ادمین #{report_id} تأیید شد.\n\n"
                f"👮‍♂️ ادمین گزارش‌شده: {report['admin_id']}\n"
                f"💬 متن گزارش: {report['report_text']}\n\n"
                f"🔒 دسترسی‌های ادمین محدود شد.",
                reply_markup=None
            )
            
        elif action == 'reject':
            # رد گزارش
            db.update_admin_abuse_report_status(
                report_id=report_id,
                status='rejected',
                admin_response="گزارش رد شد",
                responded_by=update.effective_user.id
            )
            
            # ویرایش پیام مدیر
            await query.message.edit_text(
                f"❌ گزارش تخلف ادمین #{report_id} رد شد.\n\n"
                f"👮‍♂️ ادمین گزارش‌شده: {report['admin_id']}\n"
                f"💬 متن گزارش: {report['report_text']}",
                reply_markup=None
            )
            
        elif action == 'details':
            # نمایش جزئیات بیشتر گزارش
            details = f"🔍 جزئیات گزارش تخلف ادمین #{report_id}:\n\n"
            details += f"👤 گزارش‌دهنده: {report['reporter_id']}\n"
            details += f"👮‍♂️ ادمین گزارش‌شده: {report['admin_id']}\n"
            details += f"💬 متن گزارش: {report['report_text']}\n"
            details += f"⏰ زمان گزارش: {report['report_time']}\n"
            details += f"📝 وضعیت: {report['status']}\n"
            
            # دریافت آمار اقدامات ادمین در بازه زمانی اخیر
            admin_actions = db.get_admin_recent_actions(report['admin_id'], report['group_id'])
            if admin_actions:
                details += f"\n📊 آمار اقدامات ادمین در 30 دقیقه اخیر:\n"
                details += f"🚫 تعداد بن: {admin_actions.get('ban_count', 0)}\n"
                details += f"👢 تعداد اخراج: {admin_actions.get('kick_count', 0)}\n"
                details += f"🔇 تعداد سکوت: {admin_actions.get('mute_count', 0)}\n"
                details += f"🗑️ تعداد حذف پیام: {admin_actions.get('delete_count', 0)}\n"
            
            keyboard = [
                [InlineKeyboardButton("✅ تأیید", callback_data=f'admin_abuse_approve_{report_id}')],
                [InlineKeyboardButton("❌ رد", callback_data=f'admin_abuse_reject_{report_id}')],
                [InlineKeyboardButton("بازگشت", callback_data=f'admin_abuse_back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(details, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Error in admin_abuse_callback_handler: {str(e)}")
        await query.message.edit_text(f"خطا در پردازش گزارش تخلف ادمین: {str(e)}")

async def check_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بررسی خودکار اقدامات ادمین‌ها برای شناسایی تخلف"""
    try:
        # بررسی اینکه آیا کاربر ادمین است
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['administrator', 'creator']:
            return  # کاربر ادمین نیست، نیازی به بررسی نیست
        
        # تشخیص نوع اقدام ادمین
        action_type = None
        if update.message and update.message.text:
            text = update.message.text.lower()
            if text.startswith("بن") or text.startswith("/ban"):
                action_type = "ban"
            elif text.startswith("اخراج") or text.startswith("/kick"):
                action_type = "kick"
            elif text.startswith("سکوت") or text.startswith("/mute"):
                action_type = "mute"
            elif text.startswith("حذف") or text.startswith("/delete"):
                action_type = "delete"
        
        if not action_type:
            return  # اقدام قابل تشخیص نیست
        
        # ثبت اقدام ادمین در دیتابیس
        db.add_admin_action(user_id, chat_id, action_type)
        
        # بررسی تعداد اقدامات ادمین در بازه زمانی مشخص
        threshold = ABUSE_THRESHOLDS.get(action_type)
        if not threshold:
            return
        
        count = db.count_admin_actions(user_id, chat_id, action_type, threshold["time_window"])
        
        # اگر تعداد اقدامات از آستانه بیشتر باشد، هشدار بده و محدود کن
        if count >= threshold["count"]:
            # ثبت تخلف خودکار
            report_id = db.add_admin_abuse_report(
                group_id=chat_id,
                admin_id=user_id,
                reporter_id=context.bot.id,  # ربات به عنوان گزارش‌دهنده
                message_id=update.message.message_id if update.message else 0,
                report_text=f"تشخیص خودکار تخلف: {count} {action_type} در {threshold['time_window']} ثانیه"
            )
            
            # محدود کردن دسترسی‌های ادمین
            try:
                await context.bot.promote_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    can_change_info=False,
                    can_delete_messages=False,
                    can_restrict_members=False,
                    can_invite_users=True,
                    can_pin_messages=False,
                    can_promote_members=False,
                    can_manage_video_chats=False,
                    can_manage_topics=False
                )
                
                # ارسال پیام به گروه
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ به دلیل تشخیص خودکار تخلف ({count} {action_type} در مدت کوتاه)، دسترسی‌های ادمین محدود شد."
                )
                
                # ارسال گزارش به مدیر گروه
                chat_administrators = await context.bot.get_chat_administrators(chat_id)
                creator = next((admin for admin in chat_administrators if admin.status == 'creator'), None)
                
                if creator:
                    admin_report = f"⚠️ گزارش خودکار تخلف ادمین (#{report_id}):\n\n"
                    admin_report += f"👮‍♂️ ادمین متخلف: {user_id}\n"
                    admin_report += f"🚫 نوع تخلف: {count} {action_type} در {threshold['time_window']} ثانیه\n"
                    admin_report += f"⏰ زمان تشخیص: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    admin_report += f"🔒 دسترسی‌های ادمین به صورت خودکار محدود شد."
                    
                    await context.bot.send_message(
                        chat_id=creator.user.id,
                        text=admin_report,
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Error restricting admin permissions: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error in check_admin_actions: {str(e)}")

def setup_admin_abuse_handlers(application):
    """تنظیم هندلرهای گزارش تخلف ادمین"""
    application.add_handler(CommandHandler("reportadmin", report_admin_abuse))
    application.add_handler(CallbackQueryHandler(admin_abuse_callback_handler, pattern='^admin_abuse_'))
    
    # اضافه کردن میدلور برای بررسی خودکار اقدامات ادمین‌ها
    application.add_handler(MessageHandler(filters.ALL, check_admin_actions), group=999)  # اولویت پایین

# ======================================================================
# بخش: handlers/nickname.py
# ======================================================================
# تنظیم لاگر
logger = logging.getLogger(__name__)

# مقداردهی اولیه دیتابیس
db = Database("group_manager.db")

async def set_nickname_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنظیم لقب برای کاربر و تغییر title در گروه"""
    try:
        # بررسی می‌کنیم که آیا پیام در گروه ارسال شده است
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # بررسی می‌کنیم که آیا کاربر ادمین است
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return
        
        # بررسی می‌کنیم که آیا پیام در پاسخ به پیام دیگری است
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return
        
        # Extract nickname from arguments or message text
        nickname = None
        
        # If called from handle_persian_commands, use context.args
        if hasattr(context, 'args') and context.args:
            nickname = ' '.join(context.args)
        else:
            # Fallback: extract from message text (for backward compatibility)
            command_text = update.message.text.strip()
            parts = command_text.split(" ", 2)  # حداکثر به 3 بخش تقسیم می‌کنیم
            
            if len(parts) >= 3 and parts[0] == "تنظیم" and parts[1] == "لقب":
                nickname = parts[2]
        
        if not nickname:
            await update.message.reply_text(
                "فرمت نادرست است. لطفاً از فرمت 'تنظیم لقب <لقب>' استفاده کنید.\n"
                "مثال: تنظیم لقب مهندس"
            )
            return
        
        target_user = update.message.reply_to_message.from_user
        
        # بررسی اینکه آیا کاربر هدف ادمین است
        target_chat_member = await context.bot.get_chat_member(update.effective_chat.id, target_user.id)
        if target_chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("فقط می‌توان title ادمین‌ها را تغییر داد.")
            return
        
        # بررسی اینکه آیا ربات مجوز تنظیم title ادمین‌ها را دارد
        bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        if not bot_member.can_promote_members:
            await update.message.reply_text("ربات دسترسی لازم برای تغییر title ادمین‌ها را ندارد.")
            return
        
        # تنظیم custom title برای ادمین
        try:
            await context.bot.set_chat_administrator_custom_title(
                chat_id=update.effective_chat.id,
                user_id=target_user.id,
                custom_title=nickname
            )
            
            # تنظیم لقب در دیتابیس نیز
            db.set_user_nickname(target_user.id, update.effective_chat.id, nickname, update.effective_user.id)
            
            # ارسال پیام تأیید
            await update.message.reply_text(
                f"🎖️ <b>تغییر لقب موفقیت‌آمیز!</b>\n\n"
                f"👤 <b>{target_user.first_name}</b>\n"
                f"🏷️ <b>لقب جدید:</b> «{nickname}»\n"
                f"✅ <b>وضعیت:</b> Title گروه به‌روزرسانی شد\n\n"
                f"👤 <b>تنظیم شده توسط:</b> {update.effective_user.first_name}",
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"Nickname and title set for user {target_user.id} to '{nickname}' in chat {update.effective_chat.id} by {update.effective_user.id}")
            
        except Exception as title_error:
            # اگر تنظیم title موفق نبود، حداقل در دیتابیس ذخیره کن
            db.set_user_nickname(target_user.id, update.effective_chat.id, nickname, update.effective_user.id)
            
            await update.message.reply_text(
                f"✅ لقب کاربر {target_user.first_name} به «{nickname}» تنظیم شد.\n"
                f"⚠️ تغییر title گروه ممکن نبود: {str(title_error)}",
                parse_mode=ParseMode.HTML
            )
            
            logger.warning(f"Could not set title but nickname saved for user {target_user.id}: {str(title_error)}")
        
    except Exception as e:
        logger.error(f"Error in set_nickname_handler: {str(e)}")
        await update.message.reply_text(f"خطایی رخ داد: {str(e)}")

async def show_nickname_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لقب کاربر"""
    try:
        # بررسی می‌کنیم که آیا پیام در گروه ارسال شده است
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # بررسی می‌کنیم که آیا پیام در پاسخ به پیام دیگری است
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return
        
        target_user = update.message.reply_to_message.from_user
        
        # دریافت لقب از دیتابیس
        nickname = db.get_user_nickname(target_user.id, update.effective_chat.id)
        
        if nickname:
            await update.message.reply_text(
                f"لقب کاربر <b>{target_user.first_name}</b>: <b>{nickname}</b>",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                f"کاربر <b>{target_user.first_name}</b> لقبی ندارد.",
                parse_mode=ParseMode.HTML
            )
        
    except Exception as e:
        logger.error(f"Error in show_nickname_handler: {str(e)}")
        await update.message.reply_text(f"خطایی رخ داد: {str(e)}")

async def remove_nickname_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف لقب کاربر و title از گروه"""
    try:
        # بررسی می‌کنیم که آیا پیام در گروه ارسال شده است
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # بررسی می‌کنیم که آیا کاربر ادمین است
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return
        
        # بررسی می‌کنیم که آیا پیام در پاسخ به پیام دیگری است
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return
        
        target_user = update.message.reply_to_message.from_user
        
        # بررسی اینکه آیا کاربر هدف ادمین است
        target_chat_member = await context.bot.get_chat_member(update.effective_chat.id, target_user.id)
        if target_chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("فقط می‌توان title ادمین‌ها را حذف کرد.")
            return
        
        # بررسی اینکه آیا ربات مجوز تنظیم title ادمین‌ها را دارد
        bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        if not bot_member.can_promote_members:
            await update.message.reply_text("ربات دسترسی لازم برای تغییر title ادمین‌ها را ندارد.")
            return
        
        # حذف custom title (با تنظیم title خالی)
        try:
            await context.bot.set_chat_administrator_custom_title(
                chat_id=update.effective_chat.id,
                user_id=target_user.id,
                custom_title=""  # title خالی
            )
            
            # حذف لقب از دیتابیس
            db.remove_user_nickname(target_user.id, update.effective_chat.id)
            
            await update.message.reply_text(
                f"✅ لقب و title کاربر {target_user.first_name} حذف شد.",
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"Nickname and title removed for user {target_user.id} in chat {update.effective_chat.id} by {update.effective_user.id}")
            
        except Exception as title_error:
            # اگر حذف title موفق نبود، حداقل از دیتابیس حذف کن
            db.remove_user_nickname(target_user.id, update.effective_chat.id)
            
            await update.message.reply_text(
                f"✅ لقب کاربر {target_user.first_name} از دیتابیس حذف شد.\n"
                f"⚠️ حذف title گروه ممکن نبود: {str(title_error)}",
                parse_mode=ParseMode.HTML
            )
            
            logger.warning(f"Could not remove title but nickname removed from database for user {target_user.id}: {str(title_error)}")
        
    except Exception as e:
        logger.error(f"Error in remove_nickname_handler: {str(e)}")
        await update.message.reply_text(f"خطایی رخ داد: {str(e)}")

# ======================================================================
# بخش: handlers/user_info.py
# ======================================================================
# تنظیم لاگر
logger = logging.getLogger(__name__)

# مقداردهی اولیه دیتابیس
db = Database("group_manager.db")

async def user_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش اطلاعات کاربر"""
    try:
        # بررسی می‌کنیم که آیا پیام در گروه ارسال شده است
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # بررسی می‌کنیم که آیا پیام در پاسخ به پیام دیگری است
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return
        
        target_user = update.message.reply_to_message.from_user
        group_id = update.effective_chat.id
        
        # دریافت اطلاعات کاربر از دیتابیس
        user_data = db.get_user_data(target_user.id)
        message_count = db.count_user_messages(target_user.id, group_id)
        warning_count = db.get_user_warnings(target_user.id, group_id)
        nickname = db.get_user_nickname(target_user.id, group_id)
        
        # تبدیل تاریخ میلادی به شمسی
        join_date = None
        if user_data and user_data.get('join_date'):
            try:
                gregorian_date = datetime.strptime(user_data['join_date'], "%Y-%m-%d %H:%M:%S")
                jalali_date = jdatetime.datetime.fromgregorian(datetime=gregorian_date)
                join_date = jalali_date.strftime("%Y/%m/%d %H:%M:%S")
            except Exception as e:
                logger.error(f"Error converting date: {str(e)}")
                join_date = user_data['join_date']
        
        # ایجاد پیام اطلاعات کاربر با طراحی زیبا
        info_message = f"""<b>📊 اطلاعات کاربر</b>

<b>👤 نام:</b> {target_user.first_name} {target_user.last_name or ''}
<b>🆔 شناسه کاربری:</b> <code>{target_user.id}</code>
<b>👑 نام کاربری:</b> {('@' + target_user.username) if target_user.username else 'تنظیم نشده'}"""
        
        if nickname:
            info_message += f"\n<b>🏷️ لقب:</b> {nickname}"
        
        info_message += f"""\n<b>📅 تاریخ عضویت:</b> {join_date or 'نامشخص'}
<b>💬 تعداد پیام‌ها:</b> {message_count or 0}
<b>⚠️ تعداد اخطارها:</b> {warning_count or 0}/{db.get_group_max_warnings(group_id)}"""
        
        # ایجاد دکمه‌های اینلاین
        keyboard = [
            [InlineKeyboardButton("📊 نمودار فعالیت", callback_data=f"user_activity_{target_user.id}")],
            [InlineKeyboardButton("⚠️ تاریخچه اخطارها", callback_data=f"user_warnings_{target_user.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # ارسال پیام
        await update.message.reply_text(
            info_message,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in user_info_handler: {str(e)}")
        await update.message.reply_text(f"خطایی رخ داد: {str(e)}")

async def user_info_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش دکمه‌های اینلاین اطلاعات کاربر"""
    try:
        query = update.callback_query
        await query.answer()
        
        # استخراج نوع درخواست و شناسه کاربر
        data = query.data.split('_')
        if len(data) != 3:
            return
        
        action_type = data[1]
        user_id = int(data[2])
        group_id = update.effective_chat.id
        
        if action_type == "activity":
            # نمایش نمودار فعالیت کاربر
            message_counts = db.get_user_activity(user_id, group_id)
            
            if not message_counts:
                await query.edit_message_text(
                    "اطلاعات فعالیت کاربر موجود نیست.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # ایجاد نمودار متنی ساده
            activity_chart = "<b>📊 نمودار فعالیت کاربر</b>\n\n"
            max_count = max(message_counts.values()) if message_counts else 0
            
            for day, count in message_counts.items():
                bar_length = int((count / max_count) * 20) if max_count > 0 else 0
                bar = "█" * bar_length
                activity_chart += f"<b>{day}:</b> {bar} {count}\n"
            
            # دکمه بازگشت
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data=f"user_info_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                activity_chart,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        elif action_type == "warnings":
            # نمایش تاریخچه اخطارها
            warnings = db.get_user_warning_history(user_id, group_id)
            
            if not warnings:
                await query.edit_message_text(
                    "کاربر تاکنون اخطاری دریافت نکرده است.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            warnings_text = "<b>⚠️ تاریخچه اخطارهای کاربر</b>\n\n"
            
            for i, warning in enumerate(warnings, 1):
                # تبدیل تاریخ میلادی به شمسی
                try:
                    gregorian_date = datetime.strptime(warning['timestamp'], "%Y-%m-%d %H:%M:%S")
                    jalali_date = jdatetime.datetime.fromgregorian(datetime=gregorian_date)
                    warning_date = jalali_date.strftime("%Y/%m/%d %H:%M:%S")
                except Exception as e:
                    logger.error(f"Error converting date: {str(e)}")
                    warning_date = warning['timestamp']
                
                warnings_text += f"<b>{i}. تاریخ:</b> {warning_date}\n"
                warnings_text += f"<b>دلیل:</b> {warning['reason']}\n\n"
            
            # دکمه بازگشت
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data=f"user_info_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                warnings_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        elif action_type == "info":
            # بازگشت به صفحه اصلی اطلاعات کاربر
            user = await context.bot.get_chat_member(group_id, user_id)
            target_user = user.user
            
            # دریافت اطلاعات کاربر از دیتابیس
            user_data = db.get_user_data(target_user.id)
            message_count = db.count_user_messages(target_user.id, group_id)
            warning_count = db.get_user_warnings(target_user.id, group_id)
            nickname = db.get_user_nickname(target_user.id, group_id)
            
            # تبدیل تاریخ میلادی به شمسی
            join_date = None
            if user_data and user_data.get('join_date'):
                try:
                    gregorian_date = datetime.strptime(user_data['join_date'], "%Y-%m-%d %H:%M:%S")
                    jalali_date = jdatetime.datetime.fromgregorian(datetime=gregorian_date)
                    join_date = jalali_date.strftime("%Y/%m/%d %H:%M:%S")
                except Exception as e:
                    logger.error(f"Error converting date: {str(e)}")
                    join_date = user_data['join_date']
            
            # ایجاد پیام اطلاعات کاربر با طراحی زیبا
            info_message = f"""<b>📊 اطلاعات کاربر</b>

<b>👤 نام:</b> {target_user.first_name} {target_user.last_name or ''}
<b>🆔 شناسه کاربری:</b> <code>{target_user.id}</code>
<b>👑 نام کاربری:</b> {('@' + target_user.username) if target_user.username else 'تنظیم نشده'}"""
            
            if nickname:
                info_message += f"\n<b>🏷️ لقب:</b> {nickname}"
            
            info_message += f"""\n<b>📅 تاریخ عضویت:</b> {join_date or 'نامشخص'}
<b>💬 تعداد پیام‌ها:</b> {message_count or 0}
<b>⚠️ تعداد اخطارها:</b> {warning_count or 0}/{db.get_group_max_warnings(group_id)}"""
            
            # ایجاد دکمه‌های اینلاین
            keyboard = [
                [InlineKeyboardButton("📊 نمودار فعالیت", callback_data=f"user_activity_{target_user.id}")],
                [InlineKeyboardButton("⚠️ تاریخچه اخطارها", callback_data=f"user_warnings_{target_user.id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                info_message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
        
    except Exception as e:
        logger.error(f"Error in user_info_callback_handler: {str(e)}")
        await update.callback_query.message.reply_text(f"خطایی رخ داد: {str(e)}")

# ======================================================================
# بخش: handlers/weather.py
# ======================================================================
# تنظیم لاگر
logger = logging.getLogger(__name__)

# کلید API برای OpenWeatherMap
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "demo_key")  # از environment variable یا demo key
WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

# لیست شهرهای مهم ایران با مختصات جغرافیایی
IRAN_CITIES = {
    'تهران': {'lat': 35.6892, 'lon': 51.3890, 'province': 'تهران'},
    'مشهد': {'lat': 36.2605, 'lon': 59.6168, 'province': 'خراسان رضوی'},
    'اصفهان': {'lat': 32.6546, 'lon': 51.6680, 'province': 'اصفهان'},
    'شیراز': {'lat': 29.5918, 'lon': 52.5837, 'province': 'فارس'},
    'تبریز': {'lat': 38.0962, 'lon': 46.2738, 'province': 'آذربایجان شرقی'},
    'کرج': {'lat': 35.8327, 'lon': 50.9916, 'province': 'البرز'},
    'اهواز': {'lat': 31.3183, 'lon': 48.6706, 'province': 'خوزستان'},
    'قم': {'lat': 34.6401, 'lon': 50.8764, 'province': 'قم'},
    'کرمانشاه': {'lat': 34.3142, 'lon': 47.0659, 'province': 'کرمانشاه'},
    'ارومیه': {'lat': 37.5527, 'lon': 45.0761, 'province': 'آذربایجان غربی'},
    'زاهدان': {'lat': 29.4963, 'lon': 60.8629, 'province': 'سیستان و بلوچستان'},
    'همدان': {'lat': 34.7992, 'lon': 48.5146, 'province': 'همدان'},
    'کرمان': {'lat': 30.2839, 'lon': 57.0834, 'province': 'کرمان'},
    'یزد': {'lat': 31.8974, 'lon': 54.3569, 'province': 'یزد'},
    'اردبیل': {'lat': 38.2498, 'lon': 48.2933, 'province': 'اردبیل'},
    'بندرعباس': {'lat': 27.1865, 'lon': 56.2808, 'province': 'هرمزگان'},
    'زنجان': {'lat': 36.6736, 'lon': 48.4787, 'province': 'زنجان'},
    'سنندج': {'lat': 35.3150, 'lon': 46.9999, 'province': 'کردستان'},
    'قشم': {'lat': 26.9581, 'lon': 56.2719, 'province': 'هرمزگان'},
    'کیش': {'lat': 26.5667, 'lon': 53.9833, 'province': 'هرمزگان'},
    'رشت': {'lat': 37.2809, 'lon': 49.5832, 'province': 'گیلان'},
    'بوشهر': {'lat': 28.9684, 'lon': 50.8385, 'province': 'بوشهر'},
    'ساری': {'lat': 36.5633, 'lon': 53.0601, 'province': 'مازندران'},
    'بابل': {'lat': 36.5510, 'lon': 52.6783, 'province': 'مازندران'},
    'گرگان': {'lat': 36.8427, 'lon': 54.4364, 'province': 'گلستان'},
    'بیرجند': {'lat': 32.8663, 'lon': 59.2211, 'province': 'خراسان جنوبی'},
    'بجنورد': {'lat': 37.4747, 'lon': 57.3167, 'province': 'خراسان شمالی'},
    'یاسوج': {'lat': 30.6682, 'lon': 51.5881, 'province': 'کهگیلویه و بویراحمد'},
    'ایلام': {'lat': 33.6374, 'lon': 46.4227, 'province': 'ایلام'},
    'شهرکرد': {'lat': 32.3256, 'lon': 50.8644, 'province': 'چهارمحال و بختیاری'},
    'خرم‌آباد': {'lat': 33.4878, 'lon': 48.3553, 'province': 'لرستان'},
    'دزفول': {'lat': 32.3895, 'lon': 48.4065, 'province': 'خوزستان'},
    'آبادان': {'lat': 30.3392, 'lon': 48.3043, 'province': 'خوزستان'},
    'خرمشهر': {'lat': 30.4416, 'lon': 48.1764, 'province': 'خوزستان'},
    'نجف‌آباد': {'lat': 32.6344, 'lon': 51.3667, 'province': 'اصفهان'},
    'کاشان': {'lat': 33.9831, 'lon': 51.4364, 'province': 'اصفهان'},
    'قزوین': {'lat': 36.2688, 'lon': 50.0041, 'province': 'قزوین'},
    'سمنان': {'lat': 35.5769, 'lon': 53.3915, 'province': 'سمنان'},
    'شاهرود': {'lat': 36.4183, 'lon': 54.9763, 'province': 'سمنان'},
    'گنبد کاووس': {'lat': 37.2500, 'lon': 55.1667, 'province': 'گلستان'},
    'کاشمر': {'lat': 35.2381, 'lon': 58.4651, 'province': 'خراسان رضوی'},
    'سبزوار': {'lat': 36.2126, 'lon': 57.6819, 'province': 'خراسان رضوی'},
    'نیشابور': {'lat': 36.2139, 'lon': 58.7956, 'province': 'خراسان رضوی'}
}

def persian_digits(text):
    """تبدیل اعداد انگلیسی به فارسی"""
    english_digits = '0123456789'
    persian_digits_map = '۰۱۲۳۴۵۶۷۸۹'
    
    for i, digit in enumerate(english_digits):
        text = str(text).replace(digit, persian_digits_map[i])
    
    return text

def get_weather_emoji(weather_main, weather_description):
    """دریافت ایموجی آب و هوا بر اساس وضعیت"""
    weather_emojis = {
        'clear': '☀️',
        'clouds': '☁️',
        'rain': '🌧️',
        'drizzle': '🌦️',
        'thunderstorm': '⛈️',
        'snow': '🌨️',
        'mist': '🌫️',
        'fog': '🌫️',
        'haze': '🌫️',
        'dust': '🌪️',
        'sand': '🌪️',
        'smoke': '💨'
    }
    
    return weather_emojis.get(weather_main.lower(), '🌤️')

def get_persian_weather_description(weather_description):
    """تبدیل توضیحات آب و هوا به فارسی"""
    weather_translations = {
        'clear sky': 'آسمان صاف',
        'few clouds': 'کمی ابری',
        'scattered clouds': 'ابرهای پراکنده',
        'broken clouds': 'ابری',
        'overcast clouds': 'کاملاً ابری',
        'light rain': 'بارش خفیف',
        'moderate rain': 'بارش متوسط',
        'heavy intensity rain': 'بارش شدید',
        'very heavy rain': 'بارش خیلی شدید',
        'extreme rain': 'بارش فوق‌العاده شدید',
        'freezing rain': 'بارش یخی',
        'light intensity shower rain': 'رگبار خفیف',
        'shower rain': 'رگبار',
        'heavy intensity shower rain': 'رگبار شدید',
        'ragged shower rain': 'رگبار نامنظم',
        'light snow': 'برف خفیف',
        'snow': 'برف',
        'heavy snow': 'برف شدید',
        'sleet': 'برف و باران',
        'light shower sleet': 'رگبار خفیف برف و باران',
        'shower sleet': 'رگبار برف و باران',
        'light rain and snow': 'باران و برف خفیف',
        'rain and snow': 'باران و برف',
        'light shower snow': 'رگبار برف خفیف',
        'shower snow': 'رگبار برف',
        'heavy shower snow': 'رگبار برف شدید',
        'mist': 'مه خفیف',
        'smoke': 'دود',
        'haze': 'مه',
        'sand/dust whirls': 'گردباد شن و خاک',
        'fog': 'مه غلیظ',
        'sand': 'طوفان شن',
        'dust': 'طوفان گرد و غبار',
        'volcanic ash': 'خاکستر آتشفشانی',
        'squalls': 'طوفان',
        'tornado': 'گردباد',
        'thunderstorm with light rain': 'رعد و برق با بارش خفیف',
        'thunderstorm with rain': 'رعد و برق با بارش',
        'thunderstorm with heavy rain': 'رعد و برق با بارش شدید',
        'light thunderstorm': 'رعد و برق خفیف',
        'thunderstorm': 'رعد و برق',
        'heavy thunderstorm': 'رعد و برق شدید',
        'ragged thunderstorm': 'رعد و برق نامنظم',
        'thunderstorm with light drizzle': 'رعد و برق با نم‌نم باران',
        'thunderstorm with drizzle': 'رعد و برق با نم‌نم باران',
        'thunderstorm with heavy drizzle': 'رعد و برق با نم‌نم باران شدید'
    }
    
    return weather_translations.get(weather_description.lower(), weather_description)

def get_wind_direction(degrees):
    """تبدیل درجه باد به جهت فارسی"""
    directions = [
        'شمال', 'شمال شرقی', 'شرق', 'جنوب شرقی',
        'جنوب', 'جنوب غربی', 'غرب', 'شمال غربی'
    ]
    
    index = round(degrees / 45) % 8
    return directions[index]

def get_aqi_status(aqi):
    """دریافت وضعیت کیفیت هوا"""
    if aqi <= 50:
        return "🟢 سالم"
    elif aqi <= 100:
        return "🟡 متوسط"
    elif aqi <= 150:
        return "🟠 برای گروه‌های حساس ناسالم است"
    elif aqi <= 200:
        return "🔴 ناسالم"
    elif aqi <= 300:
        return "🟣 خیلی ناسالم"
    else:
        return "🔴 خطرناک"

async def get_weather_data(city_name):
    """دریافت اطلاعات آب و هوا از API"""
    try:
        # اگر کلید API دمو باشد، داده‌های نمونه برگردان
        if WEATHER_API_KEY == "demo_key":
            return get_demo_weather_data(city_name)
        
        # دریافت مختصات شهر
        if city_name not in IRAN_CITIES:
            return None
        
        city_info = IRAN_CITIES[city_name]
        lat, lon = city_info['lat'], city_info['lon']
        
        # دریافت آب و هوای فعلی
        current_url = f"{WEATHER_BASE_URL}/weather"
        current_params = {
            'lat': lat,
            'lon': lon,
            'appid': WEATHER_API_KEY,
            'units': 'metric',
            'lang': 'fa'
        }
        
        current_response = requests.get(current_url, params=current_params, timeout=10)
        if current_response.status_code != 200:
            return None
        
        current_data = current_response.json()
        
        # دریافت پیش‌بینی ۵ روزه
        forecast_url = f"{WEATHER_BASE_URL}/forecast"
        forecast_params = {
            'lat': lat,
            'lon': lon,
            'appid': WEATHER_API_KEY,
            'units': 'metric',
            'lang': 'fa'
        }
        
        forecast_response = requests.get(forecast_url, params=forecast_params, timeout=10)
        forecast_data = forecast_response.json() if forecast_response.status_code == 200 else None
        
        # دریافت کیفیت هوا
        aqi_url = f"{WEATHER_BASE_URL}/air_pollution"
        aqi_params = {
            'lat': lat,
            'lon': lon,
            'appid': WEATHER_API_KEY
        }
        
        aqi_response = requests.get(aqi_url, params=aqi_params, timeout=10)
        aqi_data = aqi_response.json() if aqi_response.status_code == 200 else None
        
        return {
            'current': current_data,
            'forecast': forecast_data,
            'aqi': aqi_data,
            'city_info': city_info
        }
        
    except Exception as e:
        logger.error(f"Error fetching weather data: {str(e)}")
        return None

def get_demo_weather_data(city_name):
    """داده‌های نمونه برای تست"""
    import time
    import random
    
    if city_name not in IRAN_CITIES:
        return None
    
    city_info = IRAN_CITIES[city_name]
    
    # داده‌های نمونه واقع‌گرایانه
    base_temp = random.uniform(15, 35)  # دمای پایه
    
    current_data = {
        'main': {
            'temp': base_temp,
            'feels_like': base_temp + random.uniform(-3, 5),
            'temp_max': base_temp + random.uniform(2, 8),
            'temp_min': base_temp - random.uniform(2, 8),
            'humidity': random.randint(20, 90),
            'pressure': random.randint(990, 1020)
        },
        'weather': [{
            'main': random.choice(['Clear', 'Clouds', 'Rain', 'Mist']),
            'description': random.choice(['clear sky', 'few clouds', 'scattered clouds', 'light rain', 'mist'])
        }],
        'wind': {
            'speed': random.uniform(1, 10),
            'deg': random.randint(0, 360)
        },
        'clouds': {
            'all': random.randint(0, 100)
        },
        'visibility': random.randint(5000, 10000)
    }
    
    # پیش‌بینی نمونه
    forecast_data = {
        'list': []
    }
    
    for i in range(16):
        forecast_data['list'].append({
            'dt': int(time.time()) + (i * 3 * 3600),  # هر ۳ ساعت
            'main': {
                'temp': base_temp + random.uniform(-5, 5)
            },
            'weather': [{
                'main': random.choice(['Clear', 'Clouds', 'Rain']),
                'description': random.choice(['clear sky', 'few clouds', 'light rain'])
            }]
        })
    
    # کیفیت هوای نمونه
    aqi_data = {
        'list': [{
            'main': {
                'aqi': random.randint(1, 5)
            },
            'components': {
                'co': random.uniform(200, 800),
                'pm2_5': random.uniform(10, 100)
            }
        }]
    }
    
    return {
        'current': current_data,
        'forecast': forecast_data,
        'aqi': aqi_data,
        'city_info': city_info
    }

def format_weather_message(weather_data, city_name):
    """فرمت کردن پیام آب و هوا"""
    try:
        current = weather_data['current']
        forecast = weather_data.get('forecast')
        aqi = weather_data.get('aqi')
        city_info = weather_data['city_info']
        
        # تاریخ و زمان فعلی
        now = datetime.now()
        persian_date = jdatetime.datetime.fromgregorian(datetime=now)
        weekdays = ['دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه', 'شنبه', 'یکشنبه']
        weekday = weekdays[persian_date.weekday()]
        
        # اطلاعات اصلی
        temp = current['main']['temp']
        feels_like = current['main']['feels_like']
        temp_max = current['main']['temp_max']
        temp_min = current['main']['temp_min']
        humidity = current['main']['humidity']
        pressure = current['main']['pressure']
        visibility = current.get('visibility', 0) / 1000  # تبدیل به کیلومتر
        
        # باد
        wind_speed = current.get('wind', {}).get('speed', 0) * 3.6  # تبدیل m/s به km/h
        wind_deg = current.get('wind', {}).get('deg', 0)
        wind_direction = get_wind_direction(wind_deg)
        
        # آب و هوا
        weather_main = current['weather'][0]['main']
        weather_desc = get_persian_weather_description(current['weather'][0]['description'])
        weather_emoji = get_weather_emoji(weather_main, weather_desc)
        clouds = current.get('clouds', {}).get('all', 0)
        
        # شروع پیام
        message = f"◄ وضعیت هوای {city_name} :\n\n"
        message += f"• تاریخ : {weekday} {persian_digits(persian_date.strftime('%d %B %Y'))}\n"
        message += f"• ساعت : {persian_digits(now.strftime('%H:%M'))}\n\n"
        
        # دما
        message += "وضعیت دما\n"
        message += f"◂ دمای کنونی: {persian_digits(f'{temp:.1f}')} سانتی گراد\n"
        message += f"◂ دمای احساسی: {persian_digits(f'{feels_like:.1f}')} سانتی گراد\n"
        message += f"◂ حداکثر دما: {persian_digits(f'{temp_max:.1f}')} سانتی گراد\n"
        message += f"◂ حداقل دما: {persian_digits(f'{temp_min:.1f}')} سانتی گراد\n\n"
        
        # وضعیت جوی
        message += "وضعیت جَوی\n"
        message += f"◂ حالت فعلی: {weather_desc} {weather_emoji}\n"
        message += f"◂ میزان ابر: {persian_digits(clouds)} درصد\n"
        message += f"◂ رطوبت: {persian_digits(humidity)} درصد\n"
        message += f"◂ فشار هوا: {persian_digits(f'{pressure:.1f}')} میلیبار\n"
        message += f"◂ سرعت باد: {persian_digits(f'{wind_speed:.1f}')} کیلومتر بر ساعت\n"
        message += f"◂ جهت باد: {wind_direction} ({persian_digits(wind_deg)} درجه)\n"
        message += f"◂ محدوده دید: {persian_digits(f'{visibility:.1f}')} کیلومتر\n\n"
        
        # کیفیت هوا
        if aqi and 'list' in aqi and len(aqi['list']) > 0:
            aqi_main = aqi['list'][0]['main']['aqi']
            components = aqi['list'][0]['components']
            
            message += "کیفیت هوا\n"
            co_value = persian_digits(f"{components.get('co', 0):.2f}")
            pm25_value = persian_digits(f"{components.get('pm2_5', 0):.3f}")
            message += f"◂ مونوکسید کربن: {co_value}\n"
            message += f"◂ ذرات معلق: {pm25_value}\n"
            message += f"◂ شاخص کیفیت هوا: {get_aqi_status(aqi_main * 50)}\n\n"
        
        # موقعیت جغرافیایی
        message += "وضعیت مکانی\n"
        province_name = city_info['province']
        lon_value = persian_digits(f"{city_info['lon']:.4f}")
        lat_value = persian_digits(f"{city_info['lat']:.4f}")
        message += f"◂ موقعیت: {province_name}-ایران\n"
        message += f"◂ طول جغرافیایی: {lon_value}\n"
        message += f"◂ عرض جغرافیایی: {lat_value}\n\n"
        
        # پیش‌بینی
        if forecast and 'list' in forecast:
            message += "پیش بینی روزهای بعد\n"
            
            # گروه‌بندی پیش‌بینی‌ها بر اساس روز
            daily_forecasts = {}
            for item in forecast['list'][:16]:  # ۲ روز آینده
                dt = datetime.fromtimestamp(item['dt'])
                date_key = dt.strftime('%Y-%m-%d')
                
                if date_key not in daily_forecasts:
                    daily_forecasts[date_key] = {
                        'temps': [],
                        'weather': item['weather'][0],
                        'date': dt
                    }
                
                daily_forecasts[date_key]['temps'].append(item['main']['temp'])
            
            days_names = ['فردا', 'پس فردا']
            for i, (date_key, day_data) in enumerate(list(daily_forecasts.items())[1:3]):
                if i < len(days_names):
                    day_name = days_names[i]
                    temps = day_data['temps']
                    max_temp = max(temps)
                    min_temp = min(temps)
                    weather_desc = get_persian_weather_description(day_data['weather']['description'])
                    weather_emoji = get_weather_emoji(day_data['weather']['main'], weather_desc)
                    
                    message += f"◂ {day_name}:\n"
                    message += f"    ◂ دمای حداکثر: {persian_digits(f'{max_temp:.1f}')} سانتی گراد\n"
                    message += f"    ◂ دمای حداقل: {persian_digits(f'{min_temp:.1f}')} سانتی گراد\n"
                    message += f"    ◂ حالت: {weather_desc} {weather_emoji}\n"
        
        return message
        
    except Exception as e:
        logger.error(f"Error formatting weather message: {str(e)}")
        return f"خطا در پردازش اطلاعات آب و هوای {city_name}"

async def weather_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر اصلی آب و هوا"""
    try:
        # دریافت نام شهر از ورودی
        city_name = None
        
        # اگر از دستور فارسی آمده
        if hasattr(context, 'args') and context.args:
            city_name = ' '.join(context.args)
        else:
            # اگر از دستور انگلیسی آمده
            if len(context.args) > 0:
                city_name = ' '.join(context.args)
        
        # اگر نام شهر وارد نشده، لیست شهرها را نمایش بده
        if not city_name:
            keyboard = []
            cities_list = list(IRAN_CITIES.keys())
            
            # تقسیم شهرها به ردیف‌های ۳ تایی
            for i in range(0, len(cities_list), 3):
                row = []
                for j in range(3):
                    if i + j < len(cities_list):
                        city = cities_list[i + j]
                        row.append(InlineKeyboardButton(city, callback_data=f'weather_{city}'))
                keyboard.append(row)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🌤️ <b>انتخاب شهر برای آب و هوا</b>\n\n"
                "📋 لطفاً شهر مورد نظر خود را انتخاب کنید:\n"
                "یا می‌توانید نام شهر را بنویسید:\n"
                "<code>آب و هوا تهران</code>",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return
        
        # بررسی وجود شهر در لیست
        if city_name not in IRAN_CITIES:
            # پیشنهاد شهرهای مشابه
            suggestions = [city for city in IRAN_CITIES.keys() if city_name in city]
            
            if suggestions:
                keyboard = []
                for city in suggestions[:9]:  # حداکثر ۹ پیشنهاد
                    keyboard.append([InlineKeyboardButton(city, callback_data=f'weather_{city}')])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"❌ شهر '{city_name}' یافت نشد.\n\n"
                    "💡 آیا منظورتان یکی از این شهرها بود؟",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    f"❌ شهر '{city_name}' در لیست شهرهای ایران یافت نشد.\n\n"
                    "💡 از دستور 'آب و هوا' بدون نام شهر استفاده کنید تا لیست شهرها را ببینید."
                )
            return
        
        # ارسال پیام در حال بارگذاری
        loading_msg = await update.message.reply_text(
            f"🌤️ در حال دریافت اطلاعات آب و هوای {city_name}...\n"
            "⏳ لطفاً صبر کنید..."
        )
        
        # دریافت اطلاعات آب و هوا
        weather_data = await get_weather_data(city_name)
        
        if not weather_data:
            await loading_msg.edit_text(
                f"❌ متأسفانه نتوانستیم اطلاعات آب و هوای {city_name} را دریافت کنیم.\n"
                "🔄 لطفاً دوباره تلاش کنید."
            )
            return
        
        # فرمت کردن و ارسال پیام آب و هوا
        weather_message = format_weather_message(weather_data, city_name)
        
        await loading_msg.edit_text(
            weather_message,
            parse_mode='HTML' if '<' in weather_message else None
        )
        
        logger.info(f"Weather information sent for {city_name} to user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in weather_handler: {str(e)}")
        await update.message.reply_text(
            "❌ خطایی در دریافت اطلاعات آب و هوا رخ داد.\n"
            "🔄 لطفاً دوباره تلاش کنید."
        )

async def weather_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر callback برای انتخاب شهر"""
    try:
        query = update.callback_query
        await query.answer()
        
        # استخراج نام شهر از callback data
        city_name = query.data.replace('weather_', '')
        
        if city_name not in IRAN_CITIES:
            await query.message.edit_text("❌ شهر انتخاب شده معتبر نیست.")
            return
        
        # ارسال پیام در حال بارگذاری
        await query.message.edit_text(
            f"🌤️ در حال دریافت اطلاعات آب و هوای {city_name}...\n"
            "⏳ لطفاً صبر کنید..."
        )
        
        # دریافت اطلاعات آب و هوا
        weather_data = await get_weather_data(city_name)
        
        if not weather_data:
            await query.message.edit_text(
                f"❌ متأسفانه نتوانستیم اطلاعات آب و هوای {city_name} را دریافت کنیم.\n"
                "🔄 لطفاً دوباره تلاش کنید."
            )
            return
        
        # فرمت کردن و ارسال پیام آب و هوا
        weather_message = format_weather_message(weather_data, city_name)
        
        await query.message.edit_text(weather_message)
        
        logger.info(f"Weather information sent for {city_name} via callback to user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in weather_callback_handler: {str(e)}")
        await query.message.edit_text(
            "❌ خطایی در دریافت اطلاعات آب و هوا رخ داد.\n"
            "🔄 لطفاً دوباره تلاش کنید."
        )

# ======================================================================
# بخش: handlers/glass_links.py
# ======================================================================
# تنظیم لاگر
logger = logging.getLogger(__name__)

# پایگاه داده لینک‌های شیشه‌ای
class GlassLinksDB:
    def __init__(self, db_path="glass_links.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """مقداردهی اولیه پایگاه داده"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS glass_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_id TEXT UNIQUE NOT NULL,
                creator_id INTEGER NOT NULL,
                creator_username TEXT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                expiry_type TEXT NOT NULL,
                expiry_value INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                max_views INTEGER DEFAULT 1,
                current_views INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                background_style TEXT DEFAULT 'gradient',
                text_color TEXT DEFAULT 'white',
                is_private BOOLEAN DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS glass_link_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_id TEXT NOT NULL,
                viewer_id INTEGER,
                viewer_username TEXT,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_hash TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_link(self, creator_id, creator_username, title, content, content_type, 
                   expiry_type, expiry_value, max_views=1, background_style='gradient', 
                   text_color='white', is_private=False):
        """ایجاد لینک شیشه‌ای جدید"""
        link_id = str(uuid.uuid4())[:8]
        
        # محاسبه زمان انقضا
        expires_at = None
        if expiry_type == 'time':
            expires_at = datetime.now() + timedelta(hours=expiry_value)
        elif expiry_type == 'days':
            expires_at = datetime.now() + timedelta(days=expiry_value)
        elif expiry_type == 'weeks':
            expires_at = datetime.now() + timedelta(weeks=expiry_value)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO glass_links 
            (link_id, creator_id, creator_username, title, content, content_type, 
             expiry_type, expiry_value, expires_at, max_views, background_style, 
             text_color, is_private)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (link_id, creator_id, creator_username, title, content, content_type,
              expiry_type, expiry_value, expires_at, max_views, background_style,
              text_color, is_private))
        
        conn.commit()
        conn.close()
        
        return link_id
    
    def get_link(self, link_id):
        """دریافت اطلاعات لینک"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM glass_links WHERE link_id = ?', (link_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result
    
    def add_view(self, link_id, viewer_id=None, viewer_username=None, ip_hash=None):
        """اضافه کردن بازدید"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # اضافه کردن بازدید
        cursor.execute('''
            INSERT INTO glass_link_views (link_id, viewer_id, viewer_username, ip_hash)
            VALUES (?, ?, ?, ?)
        ''', (link_id, viewer_id, viewer_username, ip_hash))
        
        # به‌روزرسانی تعداد بازدیدها
        cursor.execute('''
            UPDATE glass_links 
            SET current_views = current_views + 1 
            WHERE link_id = ?
        ''', (link_id,))
        
        conn.commit()
        conn.close()
    
    def is_link_valid(self, link_id):
        """بررسی معتبر بودن لینک"""
        link_data = self.get_link(link_id)
        if not link_data:
            return False, "لینک یافت نشد"
        
        # بررسی فعال بودن
        if not link_data[14]:  # is_active
            return False, "لینک غیرفعال شده است"
        
        # بررسی تعداد بازدید
        if link_data[12] >= link_data[11]:  # current_views >= max_views
            return False, "حد مجاز بازدید این لینک تمام شده است"
        
        # بررسی زمان انقضا
        if link_data[10]:  # expires_at
            expires_at = datetime.fromisoformat(link_data[10])
            if datetime.now() > expires_at:
                return False, "زمان این لینک به پایان رسیده است"
        
        return True, "معتبر"
    
    def get_user_links(self, user_id):
        """دریافت لینک‌های کاربر"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT link_id, title, content_type, created_at, current_views, max_views, is_active
            FROM glass_links 
            WHERE creator_id = ? 
            ORDER BY created_at DESC
        ''', (user_id,))
        
        results = cursor.fetchall()
        conn.close()
        return results

# نمونه پایگاه داده
glass_db = GlassLinksDB()

def generate_glass_image(title, content, background_style='gradient', text_color='white'):
    """تولید تصویر شیشه‌ای زیبا"""
    try:
        # اندازه تصویر
        width, height = 800, 600
        
        # ایجاد تصویر جدید
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # رنگ‌های مختلف برای پس‌زمینه
        backgrounds = {
            'gradient': [(138, 43, 226), (30, 144, 255)],  # بنفش به آبی
            'sunset': [(255, 94, 77), (255, 154, 0)],      # نارنجی غروب
            'ocean': [(0, 119, 190), (0, 180, 216)],       # آبی اقیانوس
            'forest': [(76, 175, 80), (139, 195, 74)],     # سبز جنگل
            'aurora': [(106, 17, 203), (37, 117, 252)],    # شفق قطبی
            'fire': [(255, 61, 0), (255, 154, 0)],         # آتش
            'mint': [(67, 206, 162), (24, 90, 157)],       # نعنایی
            'royal': [(116, 116, 191), (52, 138, 199)]     # سلطنتی
        }
        
        colors = backgrounds.get(background_style, backgrounds['gradient'])
        
        # ایجاد گرادیان
        for y in range(height):
            ratio = y / height
            r = int(colors[0][0] * (1 - ratio) + colors[1][0] * ratio)
            g = int(colors[0][1] * (1 - ratio) + colors[1][1] * ratio)
            b = int(colors[0][2] * (1 - ratio) + colors[1][2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 180))
        
        # افزودن افکت شیشه‌ای
        overlay = Image.new('RGBA', (width, height), (255, 255, 255, 30))
        img = Image.alpha_composite(img, overlay)
        
        # اضافه کردن حاشیه شیشه‌ای
        draw = ImageDraw.Draw(img)
        margin = 40
        draw.rounded_rectangle(
            [margin, margin, width-margin, height-margin],
            radius=20,
            outline=(255, 255, 255, 100),
            width=3
        )
        
        # تنظیم فونت (استفاده از فونت پیش‌فرض)
        try:
            title_font = ImageFont.truetype("arial.ttf", 48)
            content_font = ImageFont.truetype("arial.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            content_font = ImageFont.load_default()
        
        # رنگ متن
        text_colors = {
            'white': (255, 255, 255, 255),
            'black': (0, 0, 0, 255),
            'gold': (255, 215, 0, 255),
            'silver': (192, 192, 192, 255)
        }
        
        text_fill = text_colors.get(text_color, text_colors['white'])
        
        # اضافه کردن عنوان
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        title_y = 120
        
        # سایه برای متن
        draw.text((title_x+2, title_y+2), title, fill=(0, 0, 0, 100), font=title_font)
        draw.text((title_x, title_y), title, fill=text_fill, font=title_font)
        
        # اضافه کردن محتوا
        max_width = width - 100
        lines = []
        words = content.split()
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=content_font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # محدود کردن تعداد خطوط
        if len(lines) > 10:
            lines = lines[:10]
            lines[-1] += "..."
        
        content_y = title_y + 80
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=content_font)
            line_width = bbox[2] - bbox[0]
            line_x = (width - line_width) // 2
            
            # سایه
            draw.text((line_x+1, content_y+1), line, fill=(0, 0, 0, 100), font=content_font)
            draw.text((line_x, content_y), line, fill=text_fill, font=content_font)
            content_y += 35
        
        # اضافه کردن لوگو یا نشان آبی
        draw.ellipse([width-100, height-100, width-20, height-20], 
                    fill=(255, 255, 255, 80))
        draw.text((width-70, height-70), "💎", font=title_font)
        
        # ذخیره تصویر در حافظه
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes
        
    except Exception as e:
        logger.error(f"Error generating glass image: {str(e)}")
        return None

async def create_glass_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند ساخت لینک شیشه‌ای"""
    try:
        # بررسی دسترسی (فقط در گروه)
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "🔒 لینک‌های شیشه‌ای فقط در گروه قابل ساخت هستند.\n"
                "💡 لطفاً در گروه این دستور را اجرا کنید."
            )
            return
        
        # منوی ساده ساخت لینک
        keyboard = [
            [InlineKeyboardButton("⚡ یکبار مصرف", callback_data='glass_quick_1')],
            [InlineKeyboardButton("⏰ ساعتی", callback_data='glass_quick_hour')],
            [InlineKeyboardButton("📅 روزانه", callback_data='glass_quick_day')],
            [InlineKeyboardButton("📋 لیست لینک‌های من", callback_data='glass_my_links')],
            [InlineKeyboardButton("❌ انصراف", callback_data='glass_cancel')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # دریافت تصویر پروفایل گروه
        try:
            chat_photos = await context.bot.get_chat(update.effective_chat.id)
            if chat_photos and hasattr(chat_photos, 'photo') and chat_photos.photo:
                # ارسال با تصویر پروفایل گروه
                await update.message.reply_photo(
                    photo=chat_photos.photo.small_file_id,
                    caption="✨ <b>ساخت لینک شیشه‌ای</b> ✨\n\n"
                            "💎 <b>ویژگی‌ها:</b>\n"
                            "🔹 طراحی زیبا با تصویر گروه\n"
                            "🔹 ارسال لینک به پیوی\n"
                            "🔹 انقضای خودکار\n\n"
                            "⚡ نوع لینک را انتخاب کنید:",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            else:
                # ارسال بدون تصویر
                await update.message.reply_text(
                    "✨ <b>ساخت لینک شیشه‌ای</b> ✨\n\n"
                    "💎 <b>ویژگی‌ها:</b>\n"
                    "🔹 طراحی زیبا\n"
                    "🔹 ارسال لینک به پیوی\n"
                    "🔹 انقضای خودکار\n\n"
                    "⚡ نوع لینک را انتخاب کنید:",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        except:
            # اگر نتوانست عکس پروفایل بگیرد
            await update.message.reply_text(
                "✨ <b>ساخت لینک شیشه‌ای</b> ✨\n\n"
                "💎 <b>ویژگی‌ها:</b>\n"
                "🔹 طراحی زیبا\n"
                "🔹 ارسال لینک به پیوی\n"
                "🔹 انقضای خودکار\n\n"
                "⚡ نوع لینک را انتخاب کنید:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        
        logger.info(f"Glass link creation started by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in create_glass_link_handler: {str(e)}")
        await update.message.reply_text("❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")

async def glass_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت callback های مربوط به لینک شیشه‌ای"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if data == 'glass_cancel':
            await query.message.delete()
            return
        
        elif data == 'glass_my_links':
            await show_user_links(query, user_id)
            
        elif data.startswith('glass_create_'):
            content_type = data.replace('glass_create_', '')
            await start_link_creation(query, content_type)
            
        elif data.startswith('glass_quick_'):
            quick_type = data.replace('glass_quick_', '')
            await start_quick_link_creation(query, quick_type)
            
        elif data.startswith('glass_style_'):
            style = data.replace('glass_style_', '')
            await select_expiry_settings(query, style)
            
        elif data.startswith('glass_expiry_'):
            expiry_type = data.replace('glass_expiry_', '')
            await select_expiry_value(query, expiry_type)
            
        elif data.startswith('glass_views_'):
            max_views = int(data.replace('glass_views_', ''))
            await finalize_link_creation(query, max_views)
            
        elif data.startswith('glass_view_'):
            link_id = data.replace('glass_view_', '')
            await view_glass_link(query, link_id)
            
        elif data.startswith('glass_time_'):
            time_value = int(data.replace('glass_time_', ''))
            user_id = query.from_user.id
            if user_id in user_temp_data:
                user_temp_data[user_id]['expiry_value'] = time_value
            await select_view_limit(query)
            
    except Exception as e:
        logger.error(f"Error in glass_callback_handler: {str(e)}")
        await query.message.reply_text("❌ خطایی رخ داد.")

async def show_user_links(query, user_id):
    """نمایش لینک‌های کاربر"""
    links = glass_db.get_user_links(user_id)
    
    if not links:
        await query.message.edit_text(
            "📭 شما هنوز لینک شیشه‌ای نساخته‌اید!\n\n"
            "✨ برای ساخت اولین لینک از دستور /glass استفاده کنید.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت", callback_data='glass_cancel')
            ]])
        )
        return
    
    message = "📋 <b>لینک‌های شیشه‌ای شما:</b>\n\n"
    keyboard = []
    
    for i, link in enumerate(links[:10], 1):  # حداکثر 10 لینک
        link_id, title, content_type, created_at, current_views, max_views, is_active = link
        
        status = "🟢 فعال" if is_active else "🔴 غیرفعال"
        type_emoji = {
            'text': '📝', 'image': '🖼️', 
            'audio': '🎵', 'video': '📹'
        }.get(content_type, '📄')
        
        message += f"{i}. {type_emoji} <b>{title[:20]}...</b>\n"
        message += f"   👁️ {current_views}/{max_views} | {status}\n"
        message += f"   🔗 <code>https://t.me/your_bot?start=glass_{link_id}</code>\n\n"
        
        keyboard.append([InlineKeyboardButton(
            f"{i}. {title[:15]}...", 
            callback_data=f'glass_view_{link_id}'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='glass_cancel')])
    
    await query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def start_link_creation(query, content_type):
    """شروع فرآیند ساخت لینک"""
    user_id = query.from_user.id
    
    # ذخیره اطلاعات در user_temp_data
    user_temp_data[user_id] = {
        'content_type': content_type,
        'step': 'title'
    }
    
    await query.message.edit_text(
        f"✨ <b>ساخت لینک شیشه‌ای - {content_type.upper()}</b>\n\n"
        "📝 لطفاً عنوان لینک خود را وارد کنید:\n"
        "(حداکثر 50 کاراکتر)",
        parse_mode='HTML'
    )

async def start_quick_link_creation(query, quick_type):
    """شروع فرآیند ساخت لینک سریع"""
    user_id = query.from_user.id
    
    # تعیین نوع لینک سریع
    if quick_type == '1':
        content_type = 'text'
        expiry_type = 'time'
        expiry_value = 1
        max_views = 1
    elif quick_type == 'hour':
        content_type = 'text'
        expiry_type = 'time'
        expiry_value = 1
        max_views = 1
    elif quick_type == 'day':
        content_type = 'text'
        expiry_type = 'days'
        expiry_value = 1
        max_views = 1
    else:
        await query.message.edit_text("❌ نوع لینک سریع معتبر نیست.")
        return
    
    # ذخیره اطلاعات در user_temp_data
    user_temp_data[user_id] = {
        'content_type': content_type,
        'expiry_type': expiry_type,
        'expiry_value': expiry_value,
        'max_views': max_views,
        'step': 'title'
    }
    
    await query.message.edit_text(
        f"✨ <b>ساخت لینک شیشه‌ای - {content_type.upper()}</b>\n\n"
        "📝 لطفاً عنوان لینک خود را وارد کنید:\n"
        "(حداکثر 50 کاراکتر)",
        parse_mode='HTML'
    )

async def view_glass_link(query, link_id):
    """نمایش محتوای لینک شیشه‌ای"""
    try:
        # بررسی معتبر بودن لینک
        is_valid, message = glass_db.is_link_valid(link_id)
        
        if not is_valid:
            await query.message.edit_text(
                f"⚠️ <b>لینک منقضی شده</b>\n\n"
                f"📝 <b>دلیل:</b> {message}\n\n"
                "💡 برای ساخت لینک جدید از دستور /glass استفاده کنید.",
                parse_mode='HTML'
            )
            return
        
        # دریافت اطلاعات لینک
        link_data = glass_db.get_link(link_id)
        if not link_data:
            await query.message.edit_text("❌ لینک یافت نشد.")
            return
        
        # اضافه کردن بازدید
        glass_db.add_view(link_id, query.from_user.id, query.from_user.username)
        
        # استخراج اطلاعات
        title = link_data[3]
        content = link_data[4]
        content_type = link_data[5]
        background_style = link_data[13]
        text_color = link_data[14]
        
        # نمایش محتوا بر اساس نوع
        if content_type == 'text':
            # تولید تصویر شیشه‌ای
            glass_image = generate_glass_image(title, content, background_style, text_color)
            
            if glass_image:
                # ارسال به صورت عکس
                await query.message.reply_photo(
                    photo=glass_image,
                    caption=f"✨ <b>{title}</b>\n\n{content}",
                    parse_mode='HTML'
                )
            else:
                # ارسال به صورت متن در صورت خرابی تصویر
                await query.message.edit_text(
                    f"✨ <b>{title}</b>\n\n"
                    f"{content}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 <i>ارسال شده از لینک شیشه‌ای</i>",
                    parse_mode='HTML'
                )
        
        # حذف لینک اگر یکبار مصرف باشد
        if link_data[12] >= link_data[11]:  # current_views >= max_views
            await query.message.reply_text(
                "🔥 <b>این لینک منقضی شد!</b>\n\n"
                "✨ این پیام فقط برای شما قابل مشاهده بود.\n"
                "💎 لینک شیشه‌ای - یکبار مصرف",
                parse_mode='HTML'
            )
        
        logger.info(f"Glass link {link_id} viewed by user {query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error viewing glass link: {str(e)}")
        await query.message.edit_text("❌ خطایی در نمایش لینک رخ داد.")

async def handle_glass_start_parameter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پارامتر start برای لینک‌های شیشه‌ای"""
    try:
        if not context.args or not context.args[0].startswith('glass_'):
            return False
        
        link_id = context.args[0].replace('glass_', '')
        
        # بررسی معتبر بودن لینک
        is_valid, message = glass_db.is_link_valid(link_id)
        
        if not is_valid:
            await update.message.reply_text(
                f"⚠️ <b>لینک منقضی شده</b>\n\n"
                f"📝 <b>دلیل:</b> {message}\n\n"
                "💡 لینک‌های شیشه‌ای محدودیت زمانی و تعداد بازدید دارند.",
                parse_mode='HTML'
            )
            return True
        
        # دریافت اطلاعات لینک
        link_data = glass_db.get_link(link_id)
        if not link_data:
            await update.message.reply_text("❌ لینک یافت نشد.")
            return True
        
        # اضافه کردن بازدید
        glass_db.add_view(link_id, update.effective_user.id, update.effective_user.username)
        
        # استخراج اطلاعات
        title = link_data[3]
        content = link_data[4]
        content_type = link_data[5]
        background_style = link_data[13] if len(link_data) > 13 else 'gradient'
        text_color = link_data[14] if len(link_data) > 14 else 'white'
        creator_username = link_data[2]
        
        # نمایش محتوا
        if content_type == 'text':
            # تولید تصویر شیشه‌ای
            glass_image = generate_glass_image(title, content, background_style, text_color)
            
            if glass_image:
                # ارسال به صورت عکس
                await update.message.reply_photo(
                    photo=glass_image,
                    caption=f"✨ <b>{title}</b>\n\n"
                           f"{content}\n\n"
                           f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                           f"💎 <i>لینک شیشه‌ای توسط @{creator_username or 'نامشخص'}</i>",
                    parse_mode='HTML'
                )
            else:
                # ارسال به صورت متن
                await update.message.reply_text(
                    f"✨ <b>{title}</b>\n\n"
                    f"{content}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 <i>لینک شیشه‌ای توسط @{creator_username or 'نامشخص'}</i>",
                    parse_mode='HTML'
                )
        
        # بررسی یکبار مصرف بودن
        if link_data[12] >= link_data[11]:  # current_views >= max_views
            await asyncio.sleep(2)
            await update.message.reply_text(
                "🔥 <b>این لینک منقضی شد!</b>\n\n"
                "✨ این پیام فقط برای شما قابل مشاهده بود.\n"
                "💎 لینک شیشه‌ای - یکبار مصرف\n\n"
                "🌟 برای ساخت لینک شیشه‌ای خودتان از /glass استفاده کنید.",
                parse_mode='HTML'
            )
        
        logger.info(f"Glass link {link_id} accessed via start parameter by user {update.effective_user.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error handling glass start parameter: {str(e)}")
        await update.message.reply_text("❌ خطایی در بازکردن لینک رخ داد.")
        return True

# تابع اصلی برای دستور /glass
async def glass_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور اصلی لینک شیشه‌ای"""
    await create_glass_link_handler(update, context)

# ذخیره موقت اطلاعات کاربران (در production باید از دیتابیس استفاده شود)
user_temp_data = {}

async def handle_glass_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های مربوط به ساخت لینک شیشه‌ای"""
    try:
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # بررسی وجود اطلاعات موقت کاربر
        if user_id not in user_temp_data:
            return False
        
        data = user_temp_data[user_id]
        step = data.get('step')
        
        if step == 'title':
            # دریافت عنوان
            if len(message_text) > 50:
                await update.message.reply_text(
                    "❌ عنوان نباید بیشتر از ۵۰ کاراکتر باشد.\n"
                    "لطفاً عنوان کوتاه‌تری وارد کنید:"
                )
                return True
            
            data['title'] = message_text
            data['step'] = 'content'
            
            content_type = data['content_type']
            if content_type == 'text':
                await update.message.reply_text(
                    "📝 حالا محتوای پیام خود را وارد کنید:\n"
                    "(حداکثر 500 کاراکتر)"
                )
            elif content_type == 'image':
                await update.message.reply_text(
                    "🖼️ لطفاً تصویر خود را ارسال کنید:\n"
                    "(همراه با توضیحات اختیاری)"
                )
                
        elif step == 'content':
            # دریافت محتوا
            content_type = data['content_type']
            
            if content_type == 'text':
                if len(message_text) > 500:
                    await update.message.reply_text(
                        "❌ محتوا نباید بیشتر از ۵۰۰ کاراکتر باشد.\n"
                        "لطفاً محتوای کوتاه‌تری وارد کنید:"
                    )
                    return True
                
                data['content'] = message_text
                
                # بررسی اینکه آیا اطلاعات کامل شده (برای quick links)
                if 'expiry_type' in data and 'max_views' in data:
                    await finalize_quick_link_creation(update, user_id)
                else:
                    await select_style_menu(update, user_id)
                
        return True
        
    except Exception as e:
        logger.error(f"Error handling glass message: {str(e)}")
        return False

async def handle_glass_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت تصاویر مربوط به لینک شیشه‌ای"""
    try:
        user_id = update.effective_user.id
        
        if user_id not in user_temp_data:
            return False
        
        data = user_temp_data[user_id]
        
        if data.get('step') == 'content' and data.get('content_type') == 'image':
            # ذخیره تصویر
            photo = update.message.photo[-1]  # بزرگترین سایز
            file_id = photo.file_id
            
            caption = update.message.caption or ""
            data['content'] = f"IMAGE:{file_id}:{caption}"
            
            await update.message.reply_text("✅ تصویر دریافت شد!")
            await select_style_menu(update, user_id)
            return True
            
    except Exception as e:
        logger.error(f"Error handling glass photo: {str(e)}")
        return False

async def select_style_menu(update, user_id):
    """منوی انتخاب استایل"""
    keyboard = [
        [InlineKeyboardButton("🌈 گرادیان", callback_data='glass_style_gradient'),
         InlineKeyboardButton("🌅 غروب", callback_data='glass_style_sunset')],
        [InlineKeyboardButton("🌊 اقیانوس", callback_data='glass_style_ocean'),
         InlineKeyboardButton("🌲 جنگل", callback_data='glass_style_forest')],
        [InlineKeyboardButton("🌌 شفق قطبی", callback_data='glass_style_aurora'),
         InlineKeyboardButton("🔥 آتش", callback_data='glass_style_fire')],
        [InlineKeyboardButton("🍃 نعنایی", callback_data='glass_style_mint'),
         InlineKeyboardButton("👑 سلطنتی", callback_data='glass_style_royal')]
    ]
    
    await update.message.reply_text(
        "🎨 <b>انتخاب استایل پس‌زمینه:</b>\n\n"
        "رنگ و استایل مورد نظر خود را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def select_expiry_settings(query, style):
    """انتخاب تنظیمات انقضا"""
    user_id = query.from_user.id
    if user_id in user_temp_data:
        user_temp_data[user_id]['background_style'] = style
    
    keyboard = [
        [InlineKeyboardButton("⏱️ ساعتی", callback_data='glass_expiry_time')],
        [InlineKeyboardButton("📅 روزانه", callback_data='glass_expiry_days')],
        [InlineKeyboardButton("📆 هفتگی", callback_data='glass_expiry_weeks')],
        [InlineKeyboardButton("♾️ بدون انقضا", callback_data='glass_expiry_never')]
    ]
    
    await query.message.edit_text(
        "⏰ <b>تنظیم زمان انقضا:</b>\n\n"
        "مدت زمان فعال بودن لینک را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def select_expiry_value(query, expiry_type):
    """انتخاب مقدار انقضا"""
    user_id = query.from_user.id
    if user_id in user_temp_data:
        user_temp_data[user_id]['expiry_type'] = expiry_type
    
    keyboard = []
    
    if expiry_type == 'time':
        options = [
            ("1 ساعت", 1), ("3 ساعت", 3), ("6 ساعت", 6),
            ("12 ساعت", 12), ("24 ساعت", 24)
        ]
    elif expiry_type == 'days':
        options = [
            ("1 روز", 1), ("3 روز", 3), ("7 روز", 7),
            ("15 روز", 15), ("30 روز", 30)
        ]
    elif expiry_type == 'weeks':
        options = [
            ("1 هفته", 1), ("2 هفته", 2), ("4 هفته", 4),
            ("8 هفته", 8), ("12 هفته", 12)
        ]
    else:  # never
        user_temp_data[user_id]['expiry_value'] = 0
        await select_view_limit(query)
        return
    
    for text, value in options:
        keyboard.append([InlineKeyboardButton(text, callback_data=f'glass_time_{value}')])
    
    await query.message.edit_text(
        f"🕐 <b>انتخاب مدت زمان:</b>\n\n"
        f"مدت {expiry_type} را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def select_view_limit(query):
    """انتخاب محدودیت تعداد بازدید"""
    keyboard = [
        [InlineKeyboardButton("👁️ یکبار مصرف", callback_data='glass_views_1')],
        [InlineKeyboardButton("👁️ 3 بار", callback_data='glass_views_3')],
        [InlineKeyboardButton("👁️ 5 بار", callback_data='glass_views_5')],
        [InlineKeyboardButton("👁️ 10 بار", callback_data='glass_views_10')],
        [InlineKeyboardButton("👁️ 25 بار", callback_data='glass_views_25')],
        [InlineKeyboardButton("♾️ نامحدود", callback_data='glass_views_999')]
    ]
    
    await query.message.edit_text(
        "👁️ <b>تعداد مجاز بازدید:</b>\n\n"
        "چند نفر می‌توانند این لینک را ببینند؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def finalize_link_creation(query, max_views):
    """نهایی سازی و ایجاد لینک"""
    try:
        user_id = query.from_user.id
        
        if user_id not in user_temp_data:
            await query.message.edit_text("❌ اطلاعات جلسه منقضی شده. دوباره تلاش کنید.")
            return
        
        data = user_temp_data[user_id]
        data['max_views'] = max_views
        
        # ایجاد لینک در دیتابیس
        link_id = glass_db.create_link(
            creator_id=user_id,
            creator_username=query.from_user.username,
            title=data['title'],
            content=data['content'],
            content_type=data['content_type'],
            expiry_type=data['expiry_type'],
            expiry_value=data.get('expiry_value', 0),
            max_views=max_views,
            background_style=data.get('background_style', 'gradient'),
            text_color='white'
        )
        
        # پاک کردن اطلاعات موقت
        del user_temp_data[user_id]
        
        # ایجاد لینک نهایی
        bot_username = context.bot.username if hasattr(context, 'bot') else "your_bot"
        share_link = f"https://t.me/{bot_username}?start=glass_{link_id}"
        
        # نمایش تصویر پیش‌نمایش
        if data['content_type'] == 'text':
            glass_image = generate_glass_image(
                data['title'], 
                data['content'], 
                data.get('background_style', 'gradient'), 
                'white'
            )
            
            if glass_image:
                await query.message.reply_photo(
                    photo=glass_image,
                    caption=f"✨ <b>لینک شیشه‌ای ساخته شد!</b>\n\n"
                           f"🔗 <code>{share_link}</code>\n\n"
                           f"📋 <b>جزئیات:</b>\n"
                           f"📝 عنوان: {data['title']}\n"
                           f"👁️ حداکثر بازدید: {max_views}\n"
                           f"⏰ انقضا: {data['expiry_type']}\n\n"
                           f"💡 این لینک را با دوستان خود به اشتراک بگذارید!",
                    parse_mode='HTML'
                )
            else:
                await query.message.edit_text(
                    f"✅ <b>لینک شیشه‌ای ساخته شد!</b>\n\n"
                    f"🔗 <code>{share_link}</code>\n\n"
                    f"📋 <b>جزئیات:</b>\n"
                    f"📝 عنوان: {data['title']}\n"
                    f"👁️ حداکثر بازدید: {max_views}\n"
                    f"⏰ انقضا: {data['expiry_type']}\n\n"
                    f"💡 این لینک را با دوستان خود به اشتراک بگذارید!",
                    parse_mode='HTML'
                )
        
        logger.info(f"Glass link {link_id} created successfully by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error finalizing link creation: {str(e)}")
        await query.message.edit_text("❌ خطایی در ساخت لینک رخ داد.")

async def finalize_quick_link_creation(update, user_id):
    """نهایی سازی و ایجاد لینک سریع"""
    try:
        if user_id not in user_temp_data:
            await update.message.reply_text("❌ اطلاعات جلسه منقضی شده. دوباره تلاش کنید.")
            return
        
        data = user_temp_data[user_id]
        
        # ایجاد لینک در دیتابیس
        link_id = glass_db.create_link(
            creator_id=user_id,
            creator_username=update.effective_user.username,
            title=data['title'],
            content=data['content'],
            content_type=data['content_type'],
            expiry_type=data['expiry_type'],
            expiry_value=data.get('expiry_value', 0),
            max_views=data['max_views'],
            background_style='gradient',
            text_color='white'
        )
        
        # پاک کردن اطلاعات موقت
        del user_temp_data[user_id]
        
        # ایجاد لینک نهایی
        bot_username = "your_bot"  # اینجا نام کاربری ربات باید وارد شود
        share_link = f"https://t.me/{bot_username}?start=glass_{link_id}"
        
        # تولید تصویر شیشه‌ای با تصویر گروه
        try:
            # دریافت تصویر پروفایل گروه
            from telegram import Update
            chat = await update.get_bot().get_chat(update.effective_chat.id)
            group_photo = None
            
            if chat and hasattr(chat, 'photo') and chat.photo:
                group_photo = chat.photo.big_file_id
            
            # تولید تصویر شیشه‌ای
            glass_image = generate_glass_image_with_group_photo(
                data['title'], 
                data['content'], 
                group_photo,
                'gradient', 
                'white'
            )
            
            if glass_image:
                # ارسال لینک به پیوی کاربر
                try:
                    await update.get_bot().send_photo(
                        chat_id=user_id,
                        photo=glass_image,
                        caption=f"✨ <b>لینک شیشه‌ای ساخته شد!</b>\n\n"
                               f"🔗 <code>{share_link}</code>\n\n"
                               f"📋 <b>جزئیات:</b>\n"
                               f"📝 عنوان: {data['title']}\n"
                               f"👁️ حداکثر بازدید: {data['max_views']}\n"
                               f"⏰ انقضا: {data['expiry_type']}\n\n"
                               f"💡 این لینک را با دوستان خود به اشتراک بگذارید!",
                        parse_mode='HTML'
                    )
                    
                    # پیام تأیید در گروه
                    await update.message.reply_text(
                        f"✅ لینک شیشه‌ای ساخته شد!\n"
                        f"💌 لینک به پیوی شما ارسال شد.\n"
                        f"📱 می‌توانید آن را با دوستان خود به اشتراک بگذارید."
                    )
                    
                except Exception as e:
                    # اگر نتوانست به پیوی بفرستد، در گروه نمایش بده
                    await update.message.reply_photo(
                        photo=glass_image,
                        caption=f"✨ <b>لینک شیشه‌ای ساخته شد!</b>\n\n"
                               f"🔗 <code>{share_link}</code>\n\n"
                               f"⚠️ نتوانستیم لینک را به پیوی شما بفرستیم.\n"
                               f"لطفاً ابتدا با ربات در پرایوت صحبت کنید.",
                        parse_mode='HTML'
                    )
            else:
                # ارسال بدون تصویر
                await update.message.reply_text(
                    f"✅ <b>لینک شیشه‌ای ساخته شد!</b>\n\n"
                    f"🔗 <code>{share_link}</code>\n\n"
                    f"📋 <b>جزئیات:</b>\n"
                    f"📝 عنوان: {data['title']}\n"
                    f"👁️ حداکثر بازدید: {data['max_views']}\n"
                    f"⏰ انقضا: {data['expiry_type']}\n\n"
                    f"💡 این لینک را با دوستان خود به اشتراک بگذارید!",
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logger.error(f"Error generating glass image: {str(e)}")
            await update.message.reply_text(
                f"✅ <b>لینک شیشه‌ای ساخته شد!</b>\n\n"
                f"🔗 <code>{share_link}</code>\n\n"
                f"💡 این لینک را با دوستان خود به اشتراک بگذارید!",
                parse_mode='HTML'
            )
        
        logger.info(f"Quick glass link {link_id} created successfully by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error finalizing quick link creation: {str(e)}")
        await update.message.reply_text("❌ خطایی در ساخت لینک رخ داد.")

def generate_glass_image_with_group_photo(title, content, group_photo_file_id=None, background_style='gradient', text_color='white'):
    """تولید تصویر شیشه‌ای با عکس پروفایل گروه"""
    try:
        # اگر عکس گروه موجود باشد، آن را دانلود کن
        # فعلاً از تابع قبلی استفاده می‌کنیم
        return generate_glass_image(title, content, background_style, text_color)
        
    except Exception as e:
        logger.error(f"Error generating glass image with group photo: {str(e)}")
        return None 

# ======================================================================
# بخش: main.py
# ======================================================================
# Define payment-related variables directly in main.py
PAYMENT_CARD_NUMBER = "1234-5678-9012-3456"  # شماره کارت بانکی (اینجا نمونه است، با شماره واقعی جایگزین کنید)
PAYMENT_INSTRUCTIONS = """
<b>لطفاً برای خرید اشتراک با ادمین تماس بگیرید:</b>
<a href="tg://user?id={SUBSCRIPTION_CONTACT_ID}">@{username}</a>
<b>🆔 آیدی گروه:</b> {group_id}
<b>💳 شماره کارت:</b> {card_number}
<b>💳 مبلغ قابل پرداخت:</b> {price:,} تومان
"""

# Create logs directory if not exists
if not os.path.exists('logs'):
    os.makedirs('logs')

# Set up file handler
file_handler = RotatingFileHandler(
    'logs/bot.log',
    maxBytes=10485760,  # 10MB
    backupCount=5,
    encoding='utf-8'
)

# Set up console handler
console_handler = logging.StreamHandler()

# Set up logging format
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(log_format)
console_handler.setFormatter(log_format)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

# Initialize database
db = Database("group_manager.db")
premium_manager = PremiumManager("group_manager.db")

# Initialize auto permission manager
auto_permission_manager = get_auto_permission_manager(premium_manager)

# Premium groups list (will be loaded from database)
premium_groups_cache = set()

# Persian command mapping (without slash)
PERSIAN_COMMANDS = {
    'شروع': 'start',
    'راهنما': 'help',
    'پنل': 'admin',    
    'کمک': 'help',
    'اشتراک': 'subscription',
    'اخطار': 'warn',
    'حذف_اخطار': 'unwarn',
    'ادمین': 'admin',
    'قفل_زمانی': 'locktime',
    'باز_کردن_قفل': 'unlocktime',
    'جوین_اجباری': 'forcejoin',
    'حذف_جوین_اجباری': 'unforcejoin',
    'بن': 'ban',
    'رفع_بن': 'unban',  # اضافه کردن دستور رفع بن
    'اخراج': 'kick',
    'حذف': 'delete',
    'سکوت': 'mute',
    'رفع_سکوت': 'unmute',
    'لیست_ساکت': 'mutelist',
    'پیام_همگانی': 'broadcast',
    'ساعت': 'time',
    'تاریخ': 'time',
    'زمان': 'time',
    'شروع_ویس': 'startvoice',
    'قطع_ویس': 'stopvoice',
    'پین': 'pin',
    'حذف_پین': 'unpin',
    'خرید_اشتراک': 'buypremium',
    'ارتقا': 'promote',  # اضافه کردن دستور ارتقا
    'عزل': 'demote',     # اضافه کردن دستور عزل
    'ویژه': 'special',   # اضافه کردن دستور ویژه
    'گزارش': 'report',     # اضافه کردن دستور گزارش
    'گزارش_ادمین': 'reportadmin',  # اضافه کردن دستور گزارش ادمین
    'آب و هوا': 'weather',  # اضافه کردن دستور آب و هوا
    'لقب': 'nickname',      # اضافه کردن دستور نمایش لقب
    'تنظیم لقب': 'setnickname',  # اضافه کردن دستور تنظیم لقب
    'حذف لقب': 'removenickname',  # اضافه کردن دستور حذف لقب
    'اطلاعات': 'userinfo',   # اضافه کردن دستور اطلاعات کاربر
    'آمار کاربر': 'userinfo',  # اضافه کردن دستور آمار کاربر
    'اکو': 'echo',  # اضافه کردن دستور اکو
    'لینک شیشه‌ای': 'glass',  # اضافه کردن دستور لینک شیشه‌ای
    'شیشه': 'glass',  # اضافه کردن دستور کوتاه شیشه
    'پنل': 'panel',  # اضافه کردن دستور پنل
    'سودو': 'sudo',   # اضافه کردن دستور سودو
    'آمار': 'stats',  # اضافه کردن دستور آمار
    'آمار_مدیران': 'stats',  # اضافه کردن دستور آمار مدیران
    'دسترسی_مدیران': 'stats',  # اضافه کردن دستور دسترسی مدیران
    'آمار_محتوا': 'stats',  # اضافه کردن دستور آمار محتوا
    'آمار_چت': 'stats',  # اضافه کردن دستور آمار چت
    'آمار_ادد': 'stats',  # اضافه کردن دستور آمار ادد
    'آمار_امروز': 'stats',  # اضافه کردن دستور آمار امروز
}

# Muted users dictionary: {(chat_id, user_id): {'unmute_time': datetime, 'muted_by': user_id}}
muted_users = {}

# Subscription plans
SUBSCRIPTION_PLANS = {
    'monthly': {'name': 'ماهانه', 'price': 50000, 'days': 30},
    'quarterly': {'name': 'سه ماهه', 'price': 121000, 'days': 90},
    'semiannual': {'name': 'شش ماهه', 'price': 211000, 'days': 180},
    'annual': {'name': 'سالانه', 'price': 351000, 'days': 365}
}

def load_premium_groups():
    """Load premium groups from database into cache"""
    global premium_groups_cache
    try:
        groups = premium_manager.get_all_premium_groups()
        premium_groups_cache = {
            group['group_id'] for group in groups 
            if group['is_active'] and premium_manager.is_group_premium(group['group_id'])
        }
        logger.info(f"Loaded {len(premium_groups_cache)} premium groups into cache")
    except Exception as e:
        logger.error(f"Error loading premium groups: {str(e)}")

async def send_premium_required_message(update: Update, context: ContextTypes.DEFAULT_TYPE = None, feature_name: str = "این قابلیت"):
    """Send premium required message for any feature"""
    group_id = update.effective_chat.id
    
    message = f"""🔒 {feature_name} نیاز به اشتراک پرمیوم دارد!\n\n💎 برای استفاده از امکانات ربات، نیاز به خرید اشتراک دارید.\n\n👨‍💼 برای خرید اشتراک با ادمین تماس بگیرید:\n@{SUBSCRIPTION_CONTACT_USERNAME}\n🆔 آیدی خریدار: `{SUBSCRIPTION_CONTACT_ID}`\n\n📋 پلن‌های اشتراک:\n• ماهانه: ۵۰,۰۰۰ تومان (۳۰ روز)\n• سه ماهه: ۱۲۱,۰۰۰ تومان (۹۰ روز)\n• شش ماهه: ۲۱۱,۰۰۰ تومان (۱۸۰ روز)\n• سالانه: ۳۵۱,۰۰۰ تومان (۳۶۵ روز)\n\n🆔 آیدی گروه برای خرید: `{group_id}`\n\n✨ امکانات اشتراک پرمیوم:\n• سیستم اخطار خودکار\n• ضد لینک و ضد فحش\n• خوش‌آمدگویی خودکار\n• قفل تایم‌دار پیام همگانی\n• جوین اجباری چنل\n• پیام همگانی در تمام گروه‌ها\n• مدیریت کامل گروه\n• پشتیبانی ۲۴ ساعته"""
    try:
        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in send_premium_required_message: {str(e)}")
        try:
            # Try to send a new message instead of replying
            if context and context.bot:
                await context.bot.send_message(chat_id=group_id, text=message, parse_mode='Markdown')
        except Exception as inner_e:
            logger.error(f"Failed to send alternative premium message: {str(inner_e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    try:
        # Check for glass link parameter
        if context.args and context.args[0].startswith('glass_'):
            handled = await handle_glass_start_parameter(update, context)
            if handled:
                return
        
        message = (
            "سلام! من ربات مدیریت گروه هستم.\n"
            "برای دیدن دستورات از /help استفاده کنید.\n"
            "برای بررسی وضعیت اشتراک از /subscription استفاده کنید."
        )
        
        if update.effective_chat.type == "private":
            if update.effective_user.id == ADMIN_ID:
                keyboard = [
                    [InlineKeyboardButton("🔧 پنل مدیریت", callback_data='admin_panel')],
                    [InlineKeyboardButton("📊 آمار ربات", callback_data='bot_stats')],
                    [InlineKeyboardButton("💎 مدیریت اشتراک‌ها", callback_data='manage_subscriptions')],
                    [InlineKeyboardButton("💎 خرید اشتراک", callback_data='buy_premium')],
                    [InlineKeyboardButton("📚 راهنما", callback_data='help')]
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton("➕ افزودن به گروه", url=f"https://t.me/{context.bot.username}?startgroup=true")],
                    [InlineKeyboardButton("💎 خرید اشتراک", callback_data='buy_premium')],
                    [InlineKeyboardButton("📚 راهنما", callback_data='help')]
                ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            keyboard = [
                [InlineKeyboardButton("💎 خرید اشتراک", callback_data='buy_premium')],
                [InlineKeyboardButton("📚 راهنما", callback_data='help')],
                [InlineKeyboardButton("📋 بررسی اشتراک", callback_data='check_subscription')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        logger.info(f"Start command executed by user {update.effective_user.id} in chat {update.effective_chat.id}")
            
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        await update.message.reply_text("خطایی رخ داد. لطفاً دوباره تلاش کنید.")

async def buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /buypremium command to initiate subscription purchase"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است. لطفاً ربات را به گروه خود اضافه کنید و این دستور را در گروه اجرا کنید.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند اشتراک خریداری کنند.")
            return
        
        # Check if group already has an active premium subscription
        group_id = update.effective_chat.id
        if premium_manager.is_group_premium(group_id):
            subscription_info = premium_manager.get_group_subscription_info(group_id)
            expiry_date_str = subscription_info['subscription_end'] if subscription_info else "نامشخص"
            await update.message.reply_text(
                f"این گروه در حال حاضر اشتراک پرمیوم فعال دارد.\n"
                f"📅 تاریخ انقضا: {expiry_date_str}\n"
                f"برای تمدید یا تغییر پلن، با ادمین تماس بگیرید: @{SUBSCRIPTION_CONTACT_USERNAME}"
            )
            return
        
        # Create inline keyboard with subscription plans
        keyboard = [
            [InlineKeyboardButton(f"{plan['name']}: {plan['price']:,} تومان ({plan['days']} روز)", 
                                callback_data=f"select_plan:{plan_id}")]
            for plan_id, plan in SUBSCRIPTION_PLANS.items()
        ]
        keyboard.append([InlineKeyboardButton("لغو", callback_data='cancel_buy_premium')])
        reply_settings = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📋 لطفاً یکی از پلن‌های اشتراک را انتخاب کنید:",
            reply_markup=reply_settings
        )
        logger.info(f"User {update.effective_user.id} initiated subscription purchase in chat {group_id}")
        
    except Exception as e:
        logger.error(f"Error in buy_premium: {str(e)}")
        await update.message.reply_text(f"خطا در خرید اشتراک: {str(e)}")

async def handle_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries for subscription purchase and other inline buttons"""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query
    
    try:
        data = query.data
        user_id = query.from_user.id
        chat_id = query.message.chat.id if query.message.chat.type != "private" else None
        
        logger.info(f"Callback received: {data} from user {user_id} in chat {chat_id}")
        
        if data == 'help':
            await help_command(query, context)
            return
        
        if data == 'cancel_buy_premium':
            await query.message.delete()
            if chat_id:
                await context.bot.send_message(chat_id, "خرید اشتراک لغو شد.")
            logger.info(f"User {user_id} cancelled subscription purchase")
            return
        
        if data == 'check_subscription':
            group_id = query.message.chat.id
            if premium_manager.is_group_premium(group_id):
                subscription_info = premium_manager.get_group_subscription_info(group_id)
                expiry_date_str = subscription_info['subscription_end'] if subscription_info else "نامشخص"
                await query.message.reply_text(
                    f"📊 وضعیت اشتراک گروه:\n"
                    f"💎 اشتراک پرمیوم فعال است\n"
                    f"📅 تاریخ انقضا: {expiry_date_str}"
                )
            else:
                await query.message.reply_text(
                    "❌ این گروه اشتراک پرمیوم فعالی ندارد.\n"
                    "برای خرید اشتراک از /buypremium استفاده کنید."
                )
            return
        
        if data == 'buy_premium':
            if query.message.chat.type == "private":
                await query.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است. لطفاً ربات را به گروه خود اضافه کنید و این دستور را در گروه اجرا کنید.")
                return
            
            # Check if user is admin
            chat_member = await context.bot.get_chat_member(query.message.chat.id, user_id)
            if chat_member.status not in ['administrator', 'creator'] and user_id != ADMIN_ID:
                await query.message.reply_text("فقط ادمین‌های گروه می‌توانند اشتراک خریداری کنند.")
                return
            
            # Check if group already has an active premium subscription
            group_id = query.message.chat.id
            if premium_manager.is_group_premium(group_id):
                subscription_info = premium_manager.get_group_subscription_info(group_id)
                expiry_date_str = subscription_info['subscription_end'] if subscription_info else "نامشخص"
                await query.message.reply_text(
                    f"این گروه در حال حاضر اشتراک پرمیوم فعال دارد.\n"
                    f"📅 تاریخ انقضا: {expiry_date_str}\n"
                    f"برای تمدید یا تغییر پلن، با ادمین تماس بگیرید: @{SUBSCRIPTION_CONTACT_USERNAME}"
                )
                return
            
            # Create inline keyboard with subscription plans
            keyboard = [
                [InlineKeyboardButton(f"{plan['name']}: {plan['price']:,} تومان ({plan['days']} روز)", 
                                    callback_data=f"select_plan:{plan_id}")]
                for plan_id, plan in SUBSCRIPTION_PLANS.items()
            ]
            keyboard.append([InlineKeyboardButton("لغو", callback_data='cancel_buy_premium')])
            reply_settings = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                "📋 لطفاً یکی از پلن‌های اشتراک را انتخاب کنید:",
                reply_markup=reply_settings
            )
            logger.info(f"User {user_id} initiated subscription purchase via callback in chat {group_id}")
            return
        
        if data.startswith('select_plan:'):
            plan_id = data.split(':')[1]
            if plan_id not in SUBSCRIPTION_PLANS:
                await query.message.reply_text("پلن انتخاب‌شده معتبر نیست.")
                return
                
            plan = SUBSCRIPTION_PLANS[plan_id]
            
            # Send payment instructions in private chat
            instructions = PAYMENT_INSTRUCTIONS.format(
                SUBSCRIPTION_CONTACT_ID=SUBSCRIPTION_CONTACT_ID,
                username=SUBSCRIPTION_CONTACT_USERNAME,
                group_id=chat_id,
                card_number=PAYMENT_CARD_NUMBER,
                price=plan['price']
            )
            
            await context.bot.send_message(
                chat_id=user_id,
                text=instructions,
                parse_mode='HTML'
            )
            
            # Delete the plan selection message in group
            await query.message.delete()
            
            # Notify group
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ <b>درخواست اشتراک ثبت شد</b>\n\n"
                     f"👤 درخواست کننده: {query.from_user.first_name}\n"
                     f"📋 پلن انتخابی: <b>{plan['name']}</b>\n"
                     f"💰 مبلغ: <b>{plan['price']:,} تومان</b>\n\n"
                     f"📞 برای تکمیل خرید با @{SUBSCRIPTION_CONTACT_USERNAME} تماس بگیرید.\n"
                     f"💡 اطلاعات پرداخت به صورت خصوصی ارسال شد.",
                parse_mode='HTML'
            )
            
            # Get group info for admin notification
            try:
                chat_info = await context.bot.get_chat(chat_id)
                group_title = chat_info.title
                group_members_count = await context.bot.get_chat_member_count(chat_id)
            except:
                group_title = "نامشخص"
                group_members_count = "نامشخص"
            
            # Create admin notification with action buttons
            admin_message = (
                f"🛒 <b>درخواست خرید اشتراک جدید</b>\n\n"
                f"👤 <b>مشتری:</b> {query.from_user.first_name}\n"
                f"🆔 <b>آیدی کاربر:</b> <code>{user_id}</code>\n"
                f"👑 <b>نام کاربری:</b> @{query.from_user.username or 'ندارد'}\n\n"
                f"🏢 <b>اطلاعات گروه:</b>\n"
                f"📝 نام: {group_title}\n"
                f"🆔 آیدی گروه: <code>{chat_id}</code>\n"
                f"👥 تعداد اعضا: {group_members_count}\n\n"
                f"💎 <b>جزئیات اشتراک:</b>\n"
                f"📋 پلن: <b>{plan['name']}</b>\n"
                f"💰 مبلغ: <b>{plan['price']:,} تومان</b>\n"
                f"📅 مدت: <b>{plan['days']} روز</b>\n\n"
                f"🕐 <b>زمان درخواست:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📱 <b>وضعیت:</b> در انتظار تأیید"
            )
            
            # Create inline keyboard for admin actions
            admin_keyboard = [
                [
                    InlineKeyboardButton("✅ تأیید و فعال‌سازی", callback_data=f"approve_sub_{chat_id}_{plan_id}"),
                    InlineKeyboardButton("❌ رد درخواست", callback_data=f"reject_sub_{chat_id}_{user_id}")
                ],
                [
                    InlineKeyboardButton("📞 تماس با مشتری", url=f"tg://user?id={user_id}"),
                    InlineKeyboardButton("🏢 مشاهده گروه", url=f"https://t.me/c/{str(chat_id)[4:]}/1" if str(chat_id).startswith('-100') else f"tg://resolve?domain={chat_id}")
                ],
                [
                    InlineKeyboardButton("📊 آمار گروه", callback_data=f"group_stats_{chat_id}"),
                    InlineKeyboardButton("📋 تاریخچه اشتراک", callback_data=f"sub_history_{chat_id}")
                ]
            ]
            admin_reply_markup = InlineKeyboardMarkup(admin_keyboard)
            
            # Notify admin
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode='HTML',
                reply_markup=admin_reply_markup
            )
            
            logger.info(f"User {user_id} selected plan {plan_id} for chat {chat_id}")
            return
        
        # Handle admin actions for subscription requests
        if data.startswith('approve_sub_'):
            # Only allow admin to approve
            if query.from_user.id != ADMIN_ID:
                await query.answer("⛔️ فقط ادمین اصلی می‌تواند اشتراک‌ها را تأیید کند!", show_alert=True)
                return
                
            parts = data.split('_')
            if len(parts) >= 4:
                target_chat_id = int(parts[2])
                plan_id = parts[3]
                
                # Add group to premium
                success = premium_manager.add_premium_subscription(
                    group_id=target_chat_id, 
                    buyer_id=user_id, 
                    buyer_username=query.from_user.username or "نامشخص",
                    duration_days=SUBSCRIPTION_PLANS[plan_id]['days']
                )
                
                if success:
                    # Update premium groups cache
                    load_premium_groups()
                    
                    await query.edit_message_text(
                        f"✅ <b>اشتراک فعال شد!</b>\n\n"
                        f"🏢 گروه: <code>{target_chat_id}</code>\n"
                        f"📋 پلن: {SUBSCRIPTION_PLANS[plan_id]['name']}\n"
                        f"✅ وضعیت: فعال\n"
                        f"🕐 تاریخ تأیید: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        parse_mode='HTML'
                    )
                    
                    # Notify the group
                    try:
                        await context.bot.send_message(
                            chat_id=target_chat_id,
                            text=f"🎉 <b>اشتراک پرمیوم فعال شد!</b>\n\n"
                                 f"💎 پلن: <b>{SUBSCRIPTION_PLANS[plan_id]['name']}</b>\n"
                                 f"📅 مدت: <b>{SUBSCRIPTION_PLANS[plan_id]['days']} روز</b>\n"
                                 f"✨ تمام قابلیت‌های پرمیوم اکنون در دسترس است!",
                            parse_mode='HTML'
                        )
                    except:
                        pass
                else:
                    await query.answer("❌ خطا در فعال‌سازی اشتراک!", show_alert=True)
            return
            
        if data.startswith('reject_sub_'):
            # Only allow admin to reject
            if query.from_user.id != ADMIN_ID:
                await query.answer("⛔️ فقط ادمین اصلی می‌تواند درخواست‌ها را رد کند!", show_alert=True)
                return
                
            parts = data.split('_')
            if len(parts) >= 4:
                target_chat_id = int(parts[2])
                target_user_id = int(parts[3])
                
                await query.edit_message_text(
                    f"❌ <b>درخواست رد شد</b>\n\n"
                    f"🏢 گروه: <code>{target_chat_id}</code>\n"
                    f"👤 کاربر: <code>{target_user_id}</code>\n"
                    f"🕐 تاریخ رد: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode='HTML'
                )
                
                # Notify the user
                try:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text="❌ متأسفانه درخواست اشتراک شما رد شد.\n"
                             "برای اطلاعات بیشتر با ادمین تماس بگیرید.",
                    )
                except:
                    pass
            return
        
        if data.startswith('group_stats_'):
            # Only allow admin to view stats
            if query.from_user.id != ADMIN_ID:
                await query.answer("⛔️ فقط ادمین اصلی می‌تواند آمار گروه‌ها را مشاهده کند!", show_alert=True)
                return
                
            target_chat_id = int(data.split('_')[2])
            
            try:
                chat_info = await context.bot.get_chat(target_chat_id)
                member_count = await context.bot.get_chat_member_count(target_chat_id)
                
                # Get more stats from database
                total_messages = db.count_user_messages(None, target_chat_id) if hasattr(db, 'count_group_messages') else "نامشخص"
                
                stats_msg = (
                    f"📊 <b>آمار گروه</b>\n\n"
                    f"📝 نام: {chat_info.title}\n"
                    f"🆔 آیدی: <code>{target_chat_id}</code>\n"
                    f"👥 تعداد اعضا: {member_count}\n"
                    f"💬 تعداد پیام‌ها: {total_messages}\n"
                    f"🎯 نوع گروه: {chat_info.type}\n"
                    f"📅 تاریخ بررسی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                await query.answer()
                await context.bot.send_message(
                    chat_id=query.message.chat.id,
                    text=stats_msg,
                    parse_mode='HTML'
                )
            except Exception as e:
                await query.answer(f"❌ خطا در دریافت آمار: {str(e)}", show_alert=True)
            return
        
        if data.startswith('sub_history_'):
            # Only allow admin to view history
            if query.from_user.id != ADMIN_ID:
                await query.answer("⛔️ فقط ادمین اصلی می‌تواند تاریخچه اشتراک را مشاهده کند!", show_alert=True)
                return
                
            target_chat_id = int(data.split('_')[2])
            
            # Get subscription history (if available)
            is_premium = premium_manager.is_group_premium(target_chat_id)
            
            history_msg = (
                f"📋 <b>تاریخچه اشتراک گروه</b>\n\n"
                f"🆔 آیدی گروه: <code>{target_chat_id}</code>\n"
                f"💎 وضعیت فعلی: {'✅ پرمیوم' if is_premium else '❌ رایگان'}\n"
                f"📅 تاریخ بررسی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"💡 برای اطلاعات بیشتر از پنل مدیریت استفاده کنید."
            )
            
            await query.answer()
            await context.bot.send_message(
                chat_id=query.message.chat.id,
                text=history_msg,
                parse_mode='HTML'
            )
            return
        
    except Exception as e:
        logger.error(f"Error in handle_subscription_callback: {str(e)}")
        await query.message.reply_text(f"خطا در پردازش درخواست: {str(e)}")

async def premium_check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check message with premium verification for anti-link and anti-profanity"""
    if update.effective_chat.type == "private":
        return
    
    group_id = update.effective_chat.id
    
    # Check if group is premium for anti-link and anti-profanity features
    if not check_group_premium_status(group_id, premium_groups_cache, premium_manager):
        message_text = update.message.text or update.message.caption or ""
        
        # Simple link detection
        link_keywords = ['http', 'https', 'www.', 't.me', 'telegram.me', '@']
        if any(keyword in message_text.lower() for keyword in link_keywords):
            if PREMIUM_FEATURES.get("anti_link", False):
                await send_premium_required_message(update, context, "قابلیت ضد لینک")
                return
        
        # Simple profanity detection
        profanity_words = ['کیر', 'کس', 'جنده', 'فاحشه', 'کونی', 'سگ']
        if any(word in message_text for word in profanity_words):
            if PREMIUM_FEATURES.get("anti_profanity", False):
                await send_premium_required_message(update, context, "قابلیت ضد فحش")
                return
    
    # If premium or no restricted content, execute normal check
    return await check_message(update, context)

# List of responses for the bot when someone mentions "ربات"
BOT_RESPONSES = ["چیه؟", "ها؟", "جونم؟", "چیه بزبزقندی؟", "بله؟", "در خدمتم", "جان دلم؟", "بفرمایید", "امر کنید", "چی شده؟", "اینجام", "گوش به فرمانم"]

# Counter to track which response to use
bot_response_counter = 0

async def handle_bot_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when someone mentions the word 'ربات' in a message"""
    global bot_response_counter
    
    if not update.message or not update.message.text:
        return False
    
    text = update.message.text.strip()
    
    # Check if the message contains only the word "ربات"
    if text == "ربات":
        # Get the next response from the list
        response = BOT_RESPONSES[bot_response_counter % len(BOT_RESPONSES)]
        
        # Increment the counter for next time
        bot_response_counter += 1
        
        # Reply to the message
        await update.message.reply_text(response)
        return True
    
    return False

async def premium_check_message_advanced(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced message checking with all premium features"""
    if update.effective_chat.type == "private":
        return
    
    group_id = update.effective_chat.id
    
    # First check if this is a Persian command
    if update.message and update.message.text:
        command_result = await handle_persian_commands(update, context)
        if command_result:
            return
    
    # Check if someone mentioned the bot
    if update.message and update.message.text:
        bot_mentioned = await handle_bot_mention(update, context)
        if bot_mentioned:
            return
    
    # Handle glass links messages in group
    if update.message.text:
        glass_handled = await handle_glass_message(update, context)
        if glass_handled:
            return
    elif update.message.photo:
        glass_handled = await handle_glass_photo(update, context)
        if glass_handled:
            return
    
    # Continue with existing premium checks
    await premium_check_message(update, context)

async def premium_welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome new member with premium check"""
    if update.effective_chat.type == "private":
        return
    
    group_id = update.effective_chat.id
    
    # Check if group is premium
    if not check_group_premium_status(group_id, premium_groups_cache, premium_manager):
        if PREMIUM_FEATURES.get("welcome_message", False):
            try:
                await send_premium_required_message(update, context, "پیام خوش‌آمدگویی")
            except Exception as e:
                # Handle case where message might not exist or can't be replied to
                logger.error(f"Error sending premium required message: {str(e)}")
                try:
                    # Try to send a new message instead of replying
                    message = f"""🔒 پیام خوش‌آمدگویی نیاز به اشتراک پرمیوم دارد!\n\n💎 برای استفاده از امکانات ربات، نیاز به خرید اشتراک دارید.\n\n👨‍💼 برای خرید اشتراک با ادمین تماس بگیرید:\n@{SUBSCRIPTION_CONTACT_USERNAME}\n🆔 آیدی خریدار: `{SUBSCRIPTION_CONTACT_ID}`\n\n📋 پلن‌های اشتراک:\n• ماهانه: ۵۰,۰۰۰ تومان (۳۰ روز)\n• سه ماهه: ۱۲۱,۰۰۰ تومان (۹۰ روز)\n• شش ماهه: ۲۱۱,۰۰۰ تومان (۱۸۰ روز)\n• سالانه: ۳۵۱,۰۰۰ تومان (۳۶۵ روز)\n\n🆔 آیدی گروه برای خرید: `{group_id}`\n\n✨ امکانات اشتراک پرمیوم:\n• سیستم اخطار خودکار\n• ضد لینک و ضد فحش\n• خوش‌آمدگویی خودکار\n• قفل تایم‌دار پیام همگانی\n• جوین اجباری چنل\n• پیام همگانی در تمام گروه‌ها\n• مدیریت کامل گروه\n• پشتیبانی ۲۴ ساعته"""
                    await context.bot.send_message(chat_id=group_id, text=message, parse_mode='Markdown')
                except Exception as inner_e:
                    logger.error(f"Error sending alternative premium message: {str(inner_e)}")
            return
    
    # If premium or feature not restricted, execute welcome
    try:
        return await welcome_new_member(update, context)
    except Exception as e:
        logger.error(f"Error in welcome_new_member: {str(e)}")
        # Don't try to send error message as it might cause another error

@premium_required
async def premium_warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warn user with premium check"""
    return await warn_user(update, context)

@premium_required
async def premium_unwarn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unwarn user with premium check"""
    return await unwarn_user(update, context)

@premium_required
async def premium_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel with premium check"""
    return await admin_panel(update, context)

@premium_required
async def premium_lock_time_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lock time messages with premium check"""
    return await lock_time_messages(update, context)

@premium_required
async def premium_unlock_time_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unlock time messages with premium check"""
    return await unlock_time_messages(update, context)

@premium_required
async def premium_set_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set force join with premium check"""
    return await set_force_join(update, context)

@premium_required
async def premium_unset_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unset force join with premium check"""
    return await unset_force_join(update, context)

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban user from the group"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return
        
        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return
        
        user_to_ban = update.message.reply_to_message.from_user
        
        # Don't ban admins
        target_member = await context.bot.get_chat_member(update.effective_chat.id, user_to_ban.id)
        if target_member.status in ['administrator', 'creator']:
            await update.message.reply_text("نمی‌توان ادمین‌ها را مسدود کرد.")
            return
        
        # Ban the user
        await context.bot.ban_chat_member(update.effective_chat.id, user_to_ban.id)
        
        await update.message.reply_text(f"کاربر {user_to_ban.first_name} از گروه مسدود شد.")
        
    except Exception as e:
        logger.error(f"Error in ban_user: {str(e)}")
        await update.message.reply_text(f"خطا در مسدود کردن کاربر: {str(e)}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user from the group"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return
        
        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return
        
        user_to_unban = update.message.reply_to_message.from_user
        
        # Unban the user
        await context.bot.unban_chat_member(update.effective_chat.id, user_to_unban.id, only_if_banned=True)
        
        await update.message.reply_text(f"کاربر {user_to_unban.first_name} از لیست افراد مسدود شده خارج شد.")
        
    except Exception as e:
        logger.error(f"Error in unban_user: {str(e)}")
        await update.message.reply_text(f"خطا در رفع مسدودیت کاربر: {str(e)}")

@premium_required
async def premium_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban user with premium check"""
    return await ban_user(update, context)

@premium_required
async def premium_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban user with premium check"""
    return await unban_user(update, context)
async def premium_kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick user with premium check"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنید.")
            return
        
        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return
        
        user_to_kick = update.message.reply_to_message.from_user
        
        # Don't kick admins
        target_member = await context.bot.get_chat_member(update.effective_chat.id, user_to_kick.id)
        if target_member.status in ['administrator', 'creator']:
            await update.message.reply_text("نمی‌توان ادمین‌ها را اخراج کرد.")
            return
        
        # Kick the user (ban and then unban)
        await context.bot.ban_chat_member(update.effective_chat.id, user_to_kick.id)
        await context.bot.unban_chat_member(update.effective_chat.id, user_to_kick.id)
        
        await update.message.reply_text(f"کاربر {user_to_kick.first_name} از گروه اخراج شد.")
        
    except Exception as e:
        logger.error(f"Error in kick_user: {str(e)}")
        await update.message.reply_text(f"خطا در اخراج کاربر: {str(e)}")

@premium_required
async def premium_mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute user with premium check and optional time duration"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return
        
        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.\n\n"
                "مثال:\n"
                "• سکوت (سکوت دائمی)\n"
                "• سکوت 1h (سکوت برای ۱ ساعت)\n"
                "• سکوت 30m (سکوت برای ۳۰ دقیقه)\n"
                "• سکوت 2d (سکوت برای ۲ روز)\n"
                "• سکوت 1h30m (سکوت برای ۱ ساعت و ۳۰ دقیقه)"
            )
            return
        
        user_to_mute = update.message.reply_to_message.from_user
        chat_id = update.effective_chat.id
        muter_id = update.effective_user.id
        
        # Don't mute admins
        target_member = await context.bot.get_chat_member(chat_id, user_to_mute.id)
        if target_member.status in ['administrator', 'creator']:
            await update.message.reply_text("نمی‌توان ادمین‌ها را ساکت کرد.")
            return
        
        # Parse time duration from command arguments
        duration = None
        duration_text = "دائمی"
        unmute_time = None
        
        if context.args:
            time_str = context.args[0]
            duration = parse_time_duration(time_str)
            if duration:
                unmute_time = datetime.now() + duration
                duration_text = format_time_duration(duration)
            else:
                await update.message.reply_text(
                    "فرمت زمان نادرست است.\n\n"
                    "فرمت صحیح: 1d2h30m (۱ روز، ۲ ساعت، ۳۰ دقیقه)\n"
                    "مثال‌ها: 1h, 30m, 2d, 1h30m"
                )
                return
        
        # Check if user is already muted
        mute_key = (chat_id, user_to_mute.id)
        if mute_key in muted_users:
            existing_unmute_time = muted_users[mute_key].get('unmute_time')
            if existing_unmute_time and existing_unmute_time > datetime.now():
                remaining = existing_unmute_time - datetime.now()
                await update.message.reply_text(
                    f"کاربر {user_to_mute.first_name} در حال حاضر ساکت است.\n"
                    f"زمان باقیمانده: {format_time_duration(remaining)}"
                )
                return
        
        # Mute the user by restricting their permissions
        mute_permissions = ChatPermissions(
            can_send_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False
        )
        
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_to_mute.id,
            permissions=mute_permissions
        )
        
        # Store mute information
        muted_users[mute_key] = {
            'unmute_time': unmute_time,
            'muted_by': muter_id,
            'muted_at': datetime.now(),
            'chat_id': chat_id,
            'user_id': user_to_mute.id,
            'user_name': user_to_mute.first_name
        }
        
        # Send confirmation message
        mute_message = f"🔇 کاربر {user_to_mute.first_name} ساکت شد."
        if duration:
            mute_message += f"\n⏰ مدت زمان: {duration_text}"
            mute_message += f"\n📅 تا تاریخ: {unmute_time.strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            mute_message += "\n⏰ مدت زمان: دائمی"
        
        await update.message.reply_text(mute_message)
        
        logger.info(f"User {user_to_mute.id} muted in chat {chat_id} by {muter_id} for {duration_text}")
        
    except Exception as e:
        logger.error(f"Error in mute_user: {str(e)}")
        await update.message.reply_text(f"خطا در ساکت کردن کاربر: {str(e)}")

async def auto_unmute_user(chat_id, user_id, bot):
    """Automatically unmute user when time expires"""
    try:
        mute_key = (chat_id, user_id)
        if mute_key not in muted_users:
            return
        
        mute_info = muted_users[mute_key]
        user_name = mute_info.get('user_name', 'کاربر')
        
        # Restore normal permissions
        normal_permissions = ChatPermissions(
            can_send_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True
        )
        
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=normal_permissions
        )
        
        # Remove from muted users
        del muted_users[mute_key]
        
        # Send notification message
        await bot.send_message(
            chat_id=chat_id,
            text=f"🔊 سکوت کاربر {user_name} به صورت خودکار برداشته شد."
        )
        
        logger.info(f"User {user_id} automatically unmuted in chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Error in auto_unmute_user: {str(e)}")
        # Remove from muted users even if unmute failed to prevent stuck entries
        mute_key = (chat_id, user_id)
        if mute_key in muted_users:
            del muted_users[mute_key]

async def check_muted_users(bot):
    """Background task to check and unmute users whose mute time has expired"""
    while True:
        try:
            current_time = datetime.now()
            expired_mutes = []
            
            for mute_key, mute_info in muted_users.items():
                unmute_time = mute_info.get('unmute_time')
                if unmute_time and unmute_time <= current_time:
                    expired_mutes.append(mute_key)
            
            # Process expired mutes
            for mute_key in expired_mutes:
                chat_id, user_id = mute_key
                await auto_unmute_user(chat_id, user_id, bot)
            
            # Wait 30 seconds before next check
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in check_muted_users: {str(e)}")
            await asyncio.sleep(60)  # Wait longer on error

async def cleanup_expired_mutes(bot):
    """Clean up expired mutes on bot startup"""
    try:
        current_time = datetime.now()
        expired_mutes = []
        
        for mute_key, mute_info in muted_users.items():
            unmute_time = mute_info.get('unmute_time')
            if unmute_time and unmute_time <= current_time:
                expired_mutes.append(mute_key)
        
        # Clean up expired mutes
        for mute_key in expired_mutes:
            chat_id, user_id = mute_key
            try:
                # Try to unmute the user
                normal_permissions = ChatPermissions(
                    can_send_messages=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_change_info=False,
                    can_invite_users=True,
                    can_pin_messages=False,
                    can_send_audios=True,
                    can_send_documents=True,
                    can_send_photos=True,
                    can_send_videos=True,
                    can_send_video_notes=True,
                    can_send_voice_notes=True
                )
                
                await bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions=normal_permissions
                )
                
                logger.info(f"Cleaned up expired mute for user {user_id} in chat {chat_id}")
            except Exception as e:
                logger.warning(f"Could not unmute user {user_id} in chat {chat_id}: {str(e)}")
                
            # Remove from muted users regardless of unmute success
            del muted_users[mute_key]
        
        if expired_mutes:
            logger.info(f"Cleaned up {len(expired_mutes)} expired mutes on startup")
            
    except Exception as e:
        logger.error(f"Error in cleanup_expired_mutes: {str(e)}")

@premium_required
async def premium_unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unmute user with premium check"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return
        
        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام کاربر مورد نظر استفاده کنید.")
            return
        
        user_to_unmute = update.message.reply_to_message.from_user
        chat_id = update.effective_chat.id
        mute_key = (chat_id, user_to_unmute.id)
        
        # Check if user is actually muted
        if mute_key not in muted_users:
            await update.message.reply_text(f"کاربر {user_to_unmute.first_name} ساکت نیست.")
            return
        
        # Get mute information
        mute_info = muted_users[mute_key]
        muted_at = mute_info.get('muted_at')
        unmute_time = mute_info.get('unmute_time')
        
        # Calculate mute duration
        if muted_at:
            mute_duration = datetime.now() - muted_at
            duration_text = format_time_duration(mute_duration)
        else:
            duration_text = "نامشخص"
        
        # Restore normal permissions
        normal_permissions = ChatPermissions(
            can_send_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True
        )
        
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_to_unmute.id,
            permissions=normal_permissions
        )
        
        # Remove from muted users
        del muted_users[mute_key]
        
        # Send confirmation message
        unmute_message = f"🔊 سکوت کاربر {user_to_unmute.first_name} برداشته شد."
        unmute_message += f"\n⏰ مدت سکوت: {duration_text}"
        
        if unmute_time and unmute_time > datetime.now():
            remaining = unmute_time - datetime.now()
            unmute_message += f"\n📅 زمان باقیمانده بود: {format_time_duration(remaining)}"
        
        await update.message.reply_text(unmute_message)
        
        logger.info(f"User {user_to_unmute.id} manually unmuted in chat {chat_id} by {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in unmute_user: {str(e)}")
        await update.message.reply_text(f"خطا در برداشتن سکوت کاربر: {str(e)}")

@premium_required
async def list_muted_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all muted users in the current chat"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از این دستور استفاده کنند.")
            return
        
        chat_id = update.effective_chat.id
        current_time = datetime.now()
        
        # Find muted users in this chat
        chat_muted_users = []
        for mute_key, mute_info in muted_users.items():
            if mute_key[0] == chat_id:  # Same chat
                chat_muted_users.append((mute_key, mute_info))
        
        if not chat_muted_users:
            await update.message.reply_text("هیچ کاربری در این گروه ساکت نیست.")
            return
        
        # Build message
        message = "📋 لیست کاربران ساکت:\n\n"
        
        for i, (mute_key, mute_info) in enumerate(chat_muted_users, 1):
            user_name = mute_info.get('user_name', 'نامشخص')
            user_id = mute_info.get('user_id')
            muted_at = mute_info.get('muted_at')
            unmute_time = mute_info.get('unmute_time')
            
            message += f"{i}. {user_name} (ID: {user_id})\n"
            
            if muted_at:
                mute_duration = current_time - muted_at
                message += f"   ⏰ مدت سکوت: {format_time_duration(mute_duration)}\n"
            
            if unmute_time:
                if unmute_time > current_time:
                    remaining = unmute_time - current_time
                    message += f"   📅 زمان باقیمانده: {format_time_duration(remaining)}\n"
                else:
                    message += f"   ⚠️ زمان سکوت منقضی شده (در انتظار بروزرسانی)\n"
            else:
                message += f"   ♾️ سکوت دائمی\n"
            
            message += "\n"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error in list_muted_users: {str(e)}")
        await update.message.reply_text(f"خطا در نمایش لیست کاربران ساکت: {str(e)}")

@premium_required
async def start_voice_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable voice chat in the group with premium check"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند چت صوتی را فعال کنند.")
            return
        
        # Check if bot has admin permissions
        bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        if not bot_member.can_restrict_members:
            await update.message.reply_text("ربات دسترسی لازم برای تغییر تنظیمات گروه را ندارد.")
            return
        
        # Enable voice chat by setting permissions
        voice_permissions = ChatPermissions(
            can_send_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True
        )
        
        await context.bot.set_chat_permissions(
            chat_id=update.effective_chat.id,
            permissions=voice_permissions
        )
        
        await update.message.reply_text("🎙️ چت صوتی گروه با موفقیت فعال شد.")
        logger.info(f"Voice chat enabled in chat {update.effective_chat.id} by {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in start_voice_chat: {str(e)}")
        await update.message.reply_text(f"خطا در فعال‌سازی چت صوتی: {str(e)}")

@premium_required
async def stop_voice_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable voice chat in the group with premium check"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند چت صوتی را غیرفعال کنند.")
            return
        
        # Check if bot has admin permissions
        bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        if not bot_member.can_restrict_members:
            await update.message.reply_text("ربات دسترسی لازم برای تغییر تنظیمات گروه را ندارد.")
            return
        
        # Disable voice chat by restricting voice-related permissions
        restricted_permissions = ChatPermissions(
            can_send_messages=True,
            can_send_polls=True,
            can_send_other_messages=False,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=True,
            can_send_audios=False,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=False,
            can_send_voice_notes=False
        )
        
        await context.bot.set_chat_permissions(
            chat_id=update.effective_chat.id,
            permissions=restricted_permissions
        )
        
        await update.message.reply_text("🎙️ چت صوتی گروه با موفقیت غیرفعال شد.")
        logger.info(f"Voice chat disabled in chat {update.effective_chat.id} by {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in stop_voice_chat: {str(e)}")
        await update.message.reply_text(f"خطا در غیرفعال‌سازی چت صوتی: {str(e)}")

@premium_required
async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pin a message in the group with premium check"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند پیام را پین کنند.")
            return
        
        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام مورد نظر استفاده کنید.")
            return
        
        # Check if bot has admin permissions to pin messages
        bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        if not bot_member.can_pin_messages:
            await update.message.reply_text("ربات دسترسی لازم برای پین کردن پیام‌ها را ندارد.")
            return
        
        # Pin the replied message
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id,
            message_id=update.message.reply_to_message.message_id,
            disable_notification=False
        )
        
        await update.message.reply_text("📌 پیام با موفقیت پین شد.")
        logger.info(f"Message {update.message.reply_to_message.message_id} pinned in chat {update.effective_chat.id} by {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in pin_message: {str(e)}")
        await update.message.reply_text(f"خطا در پین کردن پیام: {str(e)}")

@premium_required
async def unpin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unpin a message or all messages in the group with premium check"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند پین پیام را حذف کنند.")
            return
        
        # Check if bot has admin permissions to pin messages
        bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        if not bot_member.can_pin_messages:
            await update.message.reply_text("ربات دسترسی لازم برای حذف پین پیام‌ها را ندارد.")
            return
        
        # Check if specific message or all pins
        if update.message.reply_to_message:
            # Unpin specific message
            await context.bot.unpin_chat_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.reply_to_message.message_id
            )
            await update.message.reply_text("📌 پین پیام با موفقیت حذف شد.")
            logger.info(f"Message {update.message.reply_to_message.message_id} unpinned in chat {update.effective_chat.id} by {update.effective_user.id}")
        else:
            # Unpin all messages
            await context.bot.unpin_all_chat_messages(chat_id=update.effective_chat.id)
            await update.message.reply_text("📌 تمام پیام‌های پین‌شده با موفقیت حذف شدند.")
            logger.info(f"All messages unpinned in chat {update.effective_chat.id} by {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in unpin_message: {str(e)}")
        await update.message.reply_text(f"خطا در حذف پین پیام: {str(e)}")

@premium_required
async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a message in the group with premium check"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند پیام حذف کنند.")
            return
        
        # Check if message is a reply
        if not update.message.reply_to_message:
            await update.message.reply_text("لطفاً این دستور را در پاسخ به پیام مورد نظر استفاده کنید.")
            return
        
        # Check if bot has permission to delete messages
        bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        if not bot_member.can_delete_messages:
            await update.message.reply_text("ربات دسترسی لازم برای حذف پیام‌ها را ندارد.")
            return
        
        # Delete the replied message
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.message.reply_to_message.message_id
        )
        
        await update.message.reply_text("🗑️ پیام با موفقیت حذف شد.")
        logger.info(f"Message {update.message.reply_to_message.message_id} deleted in chat {update.effective_chat.id} by {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in delete_message: {str(e)}")
        await update.message.reply_text(f"خطا در حذف پیام: {str(e)}")

def parse_time_duration(time_str):
    """Parse time duration string and return timedelta object"""
    if not time_str:
        return None
        
    # Pattern to match time format like: 1h, 30m, 2d, 1h30m, etc.
    pattern = r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
    match = re.match(pattern, time_str.lower())
    
    if not match:
        return None
    
    days, hours, minutes, seconds = match.groups()
    
    total_seconds = 0
    if days:
        total_seconds += int(days) * 24 * 3600
    if hours:
        total_seconds += int(hours) * 3600
    if minutes:
        total_seconds += int(minutes) * 60
    if seconds:
        total_seconds += int(seconds)
        
    if total_seconds == 0:
        return None
    
    return timedelta(seconds=total_seconds)

def format_time_duration(td):
    """Format timedelta to readable Persian text"""
    if not td:
        return "نامحدود"
        
    total_seconds = int(td.total_seconds())
    days = total_seconds // (24 * 3600)
    hours = (total_seconds % (24 * 3600)) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} روز")
    if hours > 0:
        parts.append(f"{hours} ساعت")
    if minutes > 0:
        parts.append(f"{minutes} دقیقه")
    if seconds > 0:
        parts.append(f"{seconds} ثانیه")
        
    return " و ".join(parts) if parts else "کمتر از یک ثانیه"

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    try:
        # Help content divided into pages
        help_pages = [
            # Page 1
            """
<b>🤖 دستورات ربات مدیریت گروه</b>

<b>👤 کاربران عادی:</b>
• /start یا شروع - شروع کار با ربات
• /help یا راهنما/کمک - نمایش این راهنما
• /subscription یا اشتراک - بررسی وضعیت اشتراک گروه
• /buypremium یا خرید_اشتراک - خرید اشتراک پرمیوم
• /time یا ساعت/تاریخ/زمان - نمایش ساعت و تاریخ فعلی
• /convert - تبدیل ارز به تومان
""",
            # Page 2
            """
<b>👮‍♂️ دستورات ادمین‌ها (نیاز به اشتراک):</b>

• /warn یا اخطار - اخطار به کاربر (با ریپلای)
• /unwarn یا حذف_اخطار - حذف اخطار کاربر (با ریپلای)
• /admin یا ادمین - پنل مدیریت (فقط برای ادمین اصلی)
• /locktime یا قفل_زمانی - قفل تایم‌دار گروه
• /unlocktime یا باز_کردن_قفل - باز کردن قفل گروه
• /forcejoin یا جوین_اجباری - تنظیم جوین اجباری چنل
• /unforcejoin یا حذف_جوین_اجباری - حذف جوین اجباری
""",
            # Page 3
"""
<b>👮‍♂️ دستورات مدیریتی (ادامه):</b>

• /ban یا بن - مسدود کردن کاربر (با ریپلای)
• /unban یا رفع_بن - رفع مسدودیت کاربر (با ریپلای)
• /kick یا اخراج - اخراج کاربر (با ریپلای)
• /mute یا سکوت - ساکت کردن کاربر (با ریپلای)
• /unmute یا رفع_سکوت - برداشتن سکوت کاربر (با ریپلای)
• /mutelist یا لیست_ساکت - نمایش لیست کاربران ساکت
• /delete یا حذف - حذف پیام (با ریپلای)
""",
            # Page 4
            """
<b>👮‍♂️ دستورات مدیریتی (ادامه):</b>

• /startvoice یا شروع_ویس - فعال کردن چت صوتی گروه
• /stopvoice یا قطع_ویس - غیرفعال کردن چت صوتی
• /pin یا پین - پین کردن پیام (با ریپلای)
• /unpin یا حذف_پین - حذف پین پیام
• /broadcast یا پیام_همگانی - ارسال پیام همگانی
• /promote یا ارتقا - ارتقای کاربر به ادمین (با ریپلای)
• /demote یا عزل - عزل کاربر از ادمینی (با ریپلای)
""",
            # Page 5
            """
<b>🔍 دستورات اطلاعاتی و گزارش:</b>

• /special یا ویژه - دادن دسترسی ویژه به کاربر
• /sudo یا سودو - افزودن یا حذف کاربر سودو
• /report یا گزارش - گزارش پیام به ادمین‌ها
• /reportadmin یا گزارش_ادمین - گزارش ادمین‌ها
• /weather یا آب و هوا - دریافت اطلاعات آب و هوا
• /userinfo یا اطلاعات - نمایش اطلاعات کاربر
• /echo یا اکو - ارسال پیام از طرف ربات (ادمین فقط)
""",
            # Page 6
            """
<b>👤 دستورات مدیریت کاربران:</b>

• /nickname یا لقب - نمایش یا تنظیم لقب کاربر
• /setnickname یا تنظیم لقب - تنظیم لقب کاربر
• /removenickname یا حذف لقب - حذف لقب کاربر
• /glass یا شیشه - ساخت لینک شیشه‌ای زیبا و یکبار مصرف

برای اطلاعات بیشتر با ادمین تماس بگیرید.
"""
        ]

        # Style the help message with glass-like appearance
        page_index = 0
        if not isinstance(update, Update):  # Called from callback
            page_index = int(update.data.split('_')[-1]) - 1
        
        # Get the content for the current page
        content = help_pages[page_index]
        
        # Create styled message with glass effect
        styled_message = create_glass_help_message(content, page_index + 1, len(help_pages))
        
        # Create keyboard for pagination
        keyboard = get_help_page_keyboard(page_index + 1, len(help_pages))

        # Send the styled message
        if isinstance(update, Update):
            await update.message.reply_text(
                styled_message,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        else:
            # Handle callback query updates
            await update.edit_message_text(
                styled_message,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

        logger.info(f"Help command executed by user {update.effective_user.id if isinstance(update, Update) else update.from_user.id} in chat {update.effective_chat.id if isinstance(update, Update) else update.message.chat.id}")
    except Exception as e:
        logger.error(f"Error in help_command: {str(e)}")
        error_message = "خطایی در نمایش راهنما رخ داد. لطفاً دوباره تلاش کنید یا با ادمین تماس بگیرید."
        if isinstance(update, Update):
            await update.message.reply_text(error_message)
        else:
            await update.message.reply_text(error_message)

def create_glass_help_message(content, current_page, total_pages):
    """Create a styled glass-like help message"""
    # Add glass-like border and styling
    header = "╭┈┈┈┈┈┈┈「 📚 راهنمای دستورات 」┈┈┈┈┈┈┈╮\n"
    footer = f"\n╰┈┈┈┈┈┈┈「 صفحه {current_page} از {total_pages} 」┈┈┈┈┈┈┈╯"
    
    # Add glass effect decorations
    top_pattern = "┊  ✧  ✧  ✧  ✧  ✧  ✧  ✧  ✧  ✧  ✧  ✧  ┊\n"
    bottom_pattern = "\n┊  ✧  ✧  ✧  ✧  ✧  ✧  ✧  ✧  ✧  ✧  ✧  ┊"
    
    # Add side borders to content
    lines = content.split('\n')
    bordered_content = ""
    for line in lines:
        if line.strip():  # Only add borders to non-empty lines
            bordered_content += f"┊ {line} ┊\n"
        else:
            bordered_content += f"┊{line}┊\n"
    
    # Remove trailing newline
    if bordered_content.endswith('\n'):
        bordered_content = bordered_content[:-1]
    
    # Combine all parts with glass effect
    styled_message = f"{header}{top_pattern}{bordered_content}{bottom_pattern}{footer}"
    
    return styled_message

def get_help_page_keyboard(current_page, total_pages):
    """Generate keyboard for help pagination"""
    keyboard = []
    
    # Add navigation buttons
    row = []
    if current_page > 1:
        row.append(InlineKeyboardButton("➡️ صفحه قبل", callback_data=f"help_page_{current_page-1}"))
    
    if current_page < total_pages:
        row.append(InlineKeyboardButton("صفحه بعد ⬅️", callback_data=f"help_page_{current_page+1}"))
    
    keyboard.append(row)
    
    # Add page indicator and home button in second row
    row2 = []
    if current_page > 1:
        row2.append(InlineKeyboardButton("🏠 صفحه اصلی", callback_data="help_page_1"))
    
    # Add page indicator
    page_indicator = f"📄 صفحه {current_page} از {total_pages}"
    row2.append(InlineKeyboardButton(page_indicator, callback_data="help_noop"))
    
    keyboard.append(row2)
    
    return InlineKeyboardMarkup(keyboard)

async def handle_persian_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Persian text commands without slash"""
    if not update.message or not update.message.text:
        return False
        
    text = update.message.text.strip()
    
    # Special handling for "آمار" commands
    if text == "آمار" or text.startswith("آمار ") or text.startswith("آمار_"):
        await stats_command(update, context)
        return True
        
    # Check if text is a Persian command
    command = None
    args = []
    
    # First check for multi-word commands (check longest matches first)
    multi_word_commands = [
        'تنظیم لقب', 'حذف لقب', 'آب و هوا', 'آمار کاربر', 
        'حذف_اخطار', 'باز_کردن_قفل', 'جوین_اجباری', 'حذف_جوین_اجباری',
        'رفع_بن', 'رفع_سکوت', 'لیست_ساکت', 'پیام_همگانی', 'شروع_ویس',
        'قطع_ویس', 'حذف_پین', 'خرید_اشتراک', 'گزارش_ادمین',
        'اکو', 'لینک شیشه‌ای', 'شیشه', 'پنل', 'سودو'
    ]
    
    # Check for multi-word commands first
    for multi_cmd in multi_word_commands:
        if text.startswith(multi_cmd):
            if multi_cmd in PERSIAN_COMMANDS:
                command = PERSIAN_COMMANDS[multi_cmd]
                # Extract arguments after the multi-word command
                remaining_text = text[len(multi_cmd):].strip()
                args = remaining_text.split() if remaining_text else []
                break
    
    # If no multi-word command found, check single word commands
    if not command:
        parts = text.split()
        if parts and parts[0] in PERSIAN_COMMANDS:
            command = PERSIAN_COMMANDS[parts[0]]
            args = parts[1:]
        
    if not command:
        return False
        
    # Store args in context
    context.args = args
    
    # Handle different commands
    try:
        if command == 'start':
            await start(update, context)
        elif command == 'help':
            await help_command(update, context)
        elif command == 'subscription':
            await subscription_status(update, context)
        elif command == 'warn':
            await premium_warn_user(update, context)
        elif command == 'unwarn':
            await premium_unwarn_user(update, context)
        elif command == 'admin':
            await premium_admin_panel(update, context)
        elif command == 'locktime':
            await premium_lock_time_messages(update, context)
        elif command == 'unlocktime':
            await premium_unlock_time_messages(update, context)
        elif command == 'forcejoin':
            await premium_set_force_join(update, context)
        elif command == 'unforcejoin':
            await premium_unset_force_join(update, context)
        elif command == 'ban':
            await premium_ban_user(update, context)
        elif command == 'kick':
            await premium_kick_user(update, context)
        elif command == 'mute':
            await premium_mute_user(update, context)
        elif command == 'unmute':
            await premium_unmute_user(update, context)
        elif command == 'mutelist':
            await list_muted_users(update, context)
        elif command == 'delete':
            await delete_message(update, context)
        elif command == 'startvoice':
            await start_voice_chat(update, context)
        elif command == 'stopvoice':
            await stop_voice_chat(update, context)
        elif command == 'pin':
            await pin_message(update, context)
        elif command == 'unpin':
            await unpin_message(update, context)
        elif command == 'broadcast':
            await admin_broadcast_handler(update, context)
        elif command == 'buypremium':
            await buy_premium(update, context)
        elif command == 'time':
            await show_current_time(update, context)
        elif command == 'promote':
            await premium_promote_user(update, context)
        elif command == 'demote':
            await premium_demote_user(update, context)
        elif command == 'special':
            await premium_special_user(update, context)
        elif command == 'sudo':
            await sudo_user_handler(update, context)
        elif command == 'reportadmin':
            await report_admin_abuse(update, context)
        elif command == 'weather':
            await weather_handler(update, context)
        elif command == 'nickname':
            await show_nickname_handler(update, context)
        elif command == 'setnickname':
            await set_nickname_handler(update, context)
        elif command == 'removenickname':
            await remove_nickname_handler(update, context)
        elif command == 'userinfo':
            await user_info_handler(update, context)
        elif command == 'echo':
            await echo_command(update, context)
        elif command == 'glass':
            await glass_command(update, context)
        elif command == 'panel':
            await admin_panel(update, context)
        elif command == 'stats':
            await stats_command(update, context)
        else:
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error handling Persian command {command}: {str(e)}")
        return False

async def post_init(application):
    """Post initialization function to start background tasks"""
    try:
        # Clean up expired mutes on startup
        await cleanup_expired_mutes(application.bot)
        
        # Start background task for checking muted users
        asyncio.create_task(check_muted_users(application.bot))
        
        logger.info("Background tasks started successfully")
    except Exception as e:
        logger.error(f"Error in post_init: {str(e)}")

def get_persian_weekday(weekday):
    """Convert weekday number to Persian weekday name"""
    persian_weekdays = {
        0: 'دوشنبه',
        1: 'سه‌شنبه', 
        2: 'چهارشنبه',
        3: 'پنج‌شنبه',
        4: 'جمعه',
        5: 'شنبه',
        6: 'یکشنبه'
    }
    return persian_weekdays.get(weekday, 'نامشخص')

def get_persian_month(month):
    """Convert month number to Persian month name"""
    persian_months = {
        1: 'فروردین', 2: 'اردیبهشت', 3: 'خرداد',
        4: 'تیر', 5: 'مرداد', 6: 'شهریور',
        7: 'مهر', 8: 'آبان', 9: 'آذر',
        10: 'دی', 11: 'بهمن', 12: 'اسفند'
    }
    return persian_months.get(month, 'نامشخص')

def persian_digits(text):
    """Convert English digits to Persian digits"""
    english_digits = '0123456789'
    persian_digits_map = '۰۱۲۳۴۵۶۷۸۹'
    
    for i, digit in enumerate(english_digits):
        text = text.replace(digit, persian_digits_map[i])
        
    return text

async def show_current_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current time and date in Tehran timezone with Persian format"""
    try:
        # Get Tehran timezone
        tehran_tz = pytz.timezone('Asia/Tehran')
        
        # Get current time in Tehran
        now_tehran = datetime.now(tehran_tz)
        
        # Format time (24-hour format)
        time_str = now_tehran.strftime('%H:%M:%S')
        time_persian = persian_digits(time_str)
        
        # Format date
        day = now_tehran.day
        month = now_tehran.month
        year = now_tehran.year
        weekday = now_tehran.weekday()
        
        # Get Persian names
        persian_weekday = get_persian_weekday(weekday)
        persian_month = get_persian_month(month)
        
        # Format Persian date
        date_str = f"{persian_weekday}، {persian_digits(str(day))} {persian_month} {persian_digits(str(year))}"
        
        # Create beautiful message
        message = f"""🕐 **ساعت فعلی تهران:**\n`{time_persian}`\n\n📅 **تاریخ امروز:**\n`{date_str}`\n\n🌍 **منطقه زمانی:** آسیا/تهران (UTC+3:30)\n⏰ **به‌روزرسانی شده در:** {time_persian}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n💡 **نکته:** این اطلاعات بر اساس ساعت رسمی ایران محاسبه شده است."""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
        logger.info(f"Time command used by user {update.effective_user.id} in chat {update.effective_chat.id}")
        
    except Exception as e:
        logger.error(f"Error in show_current_time: {str(e)}")
        await update.message.reply_text(
            "❌ خطایی در نمایش ساعت و تاریخ رخ داد.\n"
            "لطفاً دوباره تلاش کنید."
        )

class CurrencyAPI:
    def __init__(self):
        self.last_update = datetime.now()
        self.cache_duration = 900
        self.cached_data = None
        self.usd_to_toman_rate = 83535
        self.api_sources = {
            "currencies": "https://open.er-api.com/v6/latest/USD",
            "crypto": "https://api.coingecko.com/api/v3/simple/price",
            "gold": "https://api.metals.live/v1/spot"
        }

    def _get_iran_datetime(self):
        tehran_tz = pytz.timezone('Asia/Tehran')
        now = datetime.now(tehran_tz)
        j_date = jdatetime.datetime.fromgregorian(datetime=now)
        return j_date.strftime("%A %d %B %Y"), now.strftime("%H:%M")

    def _fetch_usd_to_toman_rate(self):
        try:
            r = requests.get("https://api.nobitex.ir/market/stats", timeout=5)
            r.raise_for_status()
            data = r.json()
            usdt_to_irr = float(data['stats']['USDT_IRR']['latest'])
            return int(usdt_to_irr / 10)
        except Exception as e:
            logger.error(f"Failed to fetch USD to Toman rate: {str(e)}")
            return self.usd_to_toman_rate

    def _fetch_currency_rates(self):
        try:
            self.usd_to_toman_rate = self._fetch_usd_to_toman_rate()
            data = requests.get(self.api_sources["currencies"]).json()
            return {
                "USD": {"name": "دلار آمریکا", "price": f"{self.usd_to_toman_rate:,}"},
                "EUR": {"name": "یورو", "price": f"{int(self.usd_to_toman_rate / data['rates']['EUR']):,}"},
                "GBP": {"name": "پوند", "price": f"{int(self.usd_to_toman_rate / data['rates']['GBP']):,}"}
            }
        except:
            return {
                "USD": {"name": "دلار آمریکا", "price": "83,535"},
                "EUR": {"name": "یورو", "price": "97,000"},
                "GBP": {"name": "پوند", "price": "113,000"}
            }

    def _fetch_crypto_prices(self):
        try:
            params = {'ids': 'bitcoin,ethereum,tether', 'vs_currencies': 'usd'}
            data = requests.get(self.api_sources["crypto"], params=params).json()
            return {
                "USDT": {"name": "تتر", "price": f"{self.usd_to_toman_rate:,}"},
                "BTC": {"name": "بیت کوین", "price": f"{data['bitcoin']['usd']:,.0f}"},
                "ETH": {"name": "اتریوم", "price": f"{data['ethereum']['usd']:,.0f}"}
            }
        except:
            return {
                "USDT": {"name": "تتر", "price": "83,535"},
                "BTC": {"name": "بیت کوین", "price": "105,000"},
                "ETH": {"name": "اتریوم", "price": "2,500"}
            }

    def _fetch_gold_prices(self):
        try:
            data = requests.get(self.api_sources["gold"]).json()
            gold_price_usd = next((i for i in data if "gold" in i), {"price": 2000})["price"]
            gold_price_toman = gold_price_usd * self.usd_to_toman_rate
            gold_gram = gold_price_toman / 31.1
            return {
                "Gram": {"name": "هر گرم", "price": f"{int(gold_gram):,}"},
                "Ounce": {"name": "انس طلا", "price": f"{gold_price_usd:,} $"}
            }
        except:
            return {
                "Gram": {"name": "هر گرم", "price": "7,000,000"},
                "Ounce": {"name": "انس طلا", "price": "2,000 $"}
            }

    def get_current_rates(self):
        now = datetime.now()
        if self.cached_data and (now - self.last_update).total_seconds() < self.cache_duration:
            return self.cached_data
        date, time_now = self._get_iran_datetime()
        rates = {
            "date": date,
            "time": time_now,
            "currencies": self._fetch_currency_rates(),
            "crypto": self._fetch_crypto_prices(),
            "gold": self._fetch_gold_prices()
        }
        self.cached_data = rates
        self.last_update = now
        return rates

    def convert_usd_to_toman(self, amount_usd):
        self.usd_to_toman_rate = self._fetch_usd_to_toman_rate()
        return amount_usd * self.usd_to_toman_rate

currency_api = CurrencyAPI()
full_currency_api = FullCurrencyAPI()

async def currency_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates = currency_api.get_current_rates()
    message = f"💱 *نرخ ارز:*\n📅 {rates['date']} | 🕒 {rates['time']}\n\n"
    for c in rates['currencies'].values():
        message += f"• {c['name']}: {c['price']} تومان\n"
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def crypto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates = currency_api.get_current_rates()
    message = f"💰 *قیمت کریپتو:*\n📅 {rates['date']} | 🕒 {rates['time']}\n\n"
    for c in rates['crypto'].values():
        if c['name'] == "تتر":
            message += f"• {c['name']}: {c['price']} تومان\n"
        else:
            message += f"• {c['name']}: {c['price']} $\n"
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def gold_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates = currency_api.get_current_rates()
    message = f"🏆 *قیمت طلا:*\n📅 {rates['date']} | 🕒 {rates['time']}\n\n"
    for g in rates['gold'].values():
        message += f"• {g['name']}: {g['price']}\n"
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Convert between different currencies and assets with a nice design"""
    try:
        # Check if any arguments were provided
        if not context.args or len(context.args) < 2:
            # Show help message with a nice design
            help_message = """
╭───────「 💱 راهنمای تبدیل ارز 」───────╮
│                                        │
│  📌 <b>نحوه استفاده:</b>                 │
│  /convert [مقدار] [نوع ارز]            │
│                                        │
│  📋 <b>مثال‌ها:</b>                      │
│  /convert 100 usd  ➜  تبدیل ۱۰۰ دلار    │
│  /convert 50 eur   ➜  تبدیل ۵۰ یورو     │
│  /convert 10 btc   ➜  تبدیل ۱۰ بیت‌کوین │
│  /convert 1000 trx ➜  تبدیل ۱۰۰۰ ترون   │
│  /convert 1 gold   ➜  تبدیل ۱ گرم طلا   │
│                                        │
│  💰 <b>ارزهای پشتیبانی شده:</b>          │
│  USD, EUR, GBP, TRX, BTC, ETH, BNB     │
│  USDT, DOGE, XRP, LTC, GOLD            │
╰────────────────────────────────────────╯
"""
            await update.message.reply_text(help_message, parse_mode='HTML')
            return

        try:
            # Parse amount and currency
            amount = float(context.args[0])
            currency = context.args[1].upper()
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک مقدار عددی معتبر وارد کنید.")
            return

        # Get current rates
        rates = currency_api.get_current_rates()
        
        # Get current date and time in Persian format
        date_persian = rates['date']
        time_persian = rates['time']
        
        # Initialize result variables
        result_toman = 0
        result_usd = 0
        currency_name = ""
        
        # Convert based on currency type
        if currency in ["USD", "USDT", "DOLLAR", "دلار"]:
            result_toman = currency_api.convert_usd_to_toman(amount)
            result_usd = amount
            currency_name = "دلار"
        
        elif currency in ["EUR", "EURO", "یورو"]:
            # Convert EUR to USD first
            usd_rate = float(rates['currencies']['USD']['price'].replace(',', ''))
            eur_rate = float(rates['currencies']['EUR']['price'].replace(',', ''))
            result_toman = amount * eur_rate
            result_usd = amount * (eur_rate / usd_rate)
            currency_name = "یورو"
            
        elif currency in ["GBP", "POUND", "پوند"]:
            # Convert GBP to USD first
            usd_rate = float(rates['currencies']['USD']['price'].replace(',', ''))
            gbp_rate = float(rates['currencies']['GBP']['price'].replace(',', ''))
            result_toman = amount * gbp_rate
            result_usd = amount * (gbp_rate / usd_rate)
            currency_name = "پوند"
            
        elif currency in ["BTC", "BITCOIN", "بیتکوین", "بیت‌کوین"]:
            # Get BTC price in USD
            btc_usd_rate = float(rates['crypto']['BTC']['price'].replace(',', ''))
            usd_toman_rate = float(rates['currencies']['USD']['price'].replace(',', ''))
            result_usd = amount * btc_usd_rate
            result_toman = result_usd * usd_toman_rate
            currency_name = "بیت‌کوین"
            
        elif currency in ["ETH", "ETHEREUM", "اتریوم"]:
            # Get ETH price in USD
            eth_usd_rate = float(rates['crypto']['ETH']['price'].replace(',', ''))
            usd_toman_rate = float(rates['currencies']['USD']['price'].replace(',', ''))
            result_usd = amount * eth_usd_rate
            result_toman = result_usd * usd_toman_rate
            currency_name = "اتریوم"
            
        elif currency in ["TRX", "TRON", "ترون"]:
            # Get TRX price in USD (approximately 0.12 USD)
            trx_usd_rate = 0.12  # This should be fetched from API in production
            usd_toman_rate = float(rates['currencies']['USD']['price'].replace(',', ''))
            result_usd = amount * trx_usd_rate
            result_toman = result_usd * usd_toman_rate
            currency_name = "ترون"
            
        elif currency in ["BNB", "BINANCE", "بایننس"]:
            # Get BNB price in USD (approximately 600 USD)
            bnb_usd_rate = 600  # This should be fetched from API in production
            usd_toman_rate = float(rates['currencies']['USD']['price'].replace(',', ''))
            result_usd = amount * bnb_usd_rate
            result_toman = result_usd * usd_toman_rate
            currency_name = "بایننس کوین"
            
        elif currency in ["DOGE", "DOGECOIN", "دوج", "دوج‌کوین"]:
            # Get DOGE price in USD (approximately 0.1 USD)
            doge_usd_rate = 0.1  # This should be fetched from API in production
            usd_toman_rate = float(rates['currencies']['USD']['price'].replace(',', ''))
            result_usd = amount * doge_usd_rate
            result_toman = result_usd * usd_toman_rate
            currency_name = "دوج‌کوین"
            
        elif currency in ["XRP", "RIPPLE", "ریپل"]:
            # Get XRP price in USD (approximately 0.6 USD)
            xrp_usd_rate = 0.6  # This should be fetched from API in production
            usd_toman_rate = float(rates['currencies']['USD']['price'].replace(',', ''))
            result_usd = amount * xrp_usd_rate
            result_toman = result_usd * usd_toman_rate
            currency_name = "ریپل"
            
        elif currency in ["LTC", "LITECOIN", "لایت‌کوین"]:
            # Get LTC price in USD (approximately 70 USD)
            ltc_usd_rate = 70  # This should be fetched from API in production
            usd_toman_rate = float(rates['currencies']['USD']['price'].replace(',', ''))
            result_usd = amount * ltc_usd_rate
            result_toman = result_usd * usd_toman_rate
            currency_name = "لایت‌کوین"
            
        elif currency in ["GOLD", "طلا", "GRAM", "گرم"]:
            # Get gold price per gram in toman
            gold_gram_rate = float(rates['gold']['Gram']['price'].replace(',', ''))
            usd_toman_rate = float(rates['currencies']['USD']['price'].replace(',', ''))
            result_toman = amount * gold_gram_rate
            result_usd = result_toman / usd_toman_rate
            currency_name = "گرم طلا"
            
        else:
            await update.message.reply_text(f"❌ ارز {currency} پشتیبانی نمی‌شود. برای دیدن لیست ارزهای پشتیبانی شده، دستور /convert را بدون پارامتر وارد کنید.")
            return
        
        # Format the results with commas for better readability
        formatted_toman = f"{int(result_toman):,}"
        formatted_usd = f"{result_usd:,.2f}"
        
        # Create a beautiful response message
        response_message = f"""
╭───────「 💱 نتیجه تبدیل ارز 」───────╮
│                                      │
│  🔢 <b>مقدار اولیه:</b> {amount:,} {currency_name}  
│                                      │
│  💰 <b>معادل به تومان:</b>             │
│  {formatted_toman} تومان              
│                                      │
│  💵 <b>معادل به دلار:</b>              │
│  {formatted_usd} دلار                 
│                                      │
│  📅 <b>تاریخ به‌روزرسانی:</b> {date_persian}  │
│  🕒 <b>ساعت به‌روزرسانی:</b> {time_persian}   │
╰────────────────────────────────────────╯
"""
        
        # Send the response
        await update.message.reply_text(response_message, parse_mode='HTML')
        logger.info(f"Currency conversion: {amount} {currency} by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in convert_command: {str(e)}")
        await update.message.reply_text("❌ خطا در تبدیل ارز. لطفاً دوباره تلاش کنید!")

async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display complete market information including currencies, gold, and cryptocurrencies"""
    try:
        message = full_currency_api.format_currency_message()
        await update.message.reply_text(message)
        logger.info(f"Market information displayed for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in market_command: {str(e)}")
        await update.message.reply_text("❌ خطایی در دریافت اطلاعات بازار رخ داد.\nلطفاً دوباره تلاش کنید.")

async def delete_service_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete service messages like member joined/left"""
    try:
        chat_id = update.effective_chat.id
        # بررسی تنظیمات گروه
        settings = db.get_group_settings(chat_id)
        
        # حذف پیام‌های ورود و خروج اعضا
        if update.message.new_chat_members or update.message.left_chat_member:
            await update.message.delete()
            logger.info(f"Deleted a service message in {chat_id}")
            
        # حذف پیام‌های ورود اعضا با لینک
        elif update.message.new_chat_members and settings.get("delete_join_link_messages", False):
            if hasattr(update.message, "invite_link") and update.message.invite_link:
                await update.message.delete()
                logger.info(f"Deleted a join by link message in {chat_id}")
                
        # حذف پیام‌های اد شدن
        elif update.message.new_chat_members and settings.get("delete_join_messages", False):
            await update.message.delete()
            logger.info(f"Deleted a join message in {chat_id}")
            
        # حذف پیام‌های پین
        elif update.message.pinned_message and settings.get("delete_pin_messages", False):
            await update.message.delete()
            logger.info(f"Deleted a pin message in {chat_id}")
            
        # حذف پیام‌های ویدیو چت
        elif (update.message.video_chat_started or update.message.video_chat_ended or 
              update.message.video_chat_participants_invited) and settings.get("delete_video_chat_messages", False):
            await update.message.delete()
            logger.info(f"Deleted a video chat message in {chat_id}")
    except Exception as e:
        logger.warning(f"Could not delete service message: {str(e)}")

async def new_member_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new member messages"""
    await premium_welcome_new_member(update, context)

@premium_required
async def premium_promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Promote user with premium check"""
    return await promote_user_handler(update, context)

@premium_required
async def premium_demote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demote user with premium check"""
    return await demote_user_handler(update, context)

@premium_required
async def premium_special_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Make user special with premium check"""
    return await special_user_handler(update, context)

@premium_required
async def sudo_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add or remove sudo users for the group"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Initialize premium manager
        premium_manager = PremiumManager("group_manager.db")
        group_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Check if user is the buyer or admin
        subscription_info = premium_manager.get_group_subscription_info(group_id)
        is_buyer = subscription_info and subscription_info['buyer_id'] == user_id
        is_admin = user_id == ADMIN_ID
        
        if not (is_buyer or is_admin):
            await update.message.reply_text("فقط خریدار اشتراک یا ادمین اصلی می‌تواند سودو تعیین کند.")
            return
        
        # Check if message is a reply
        if not update.message.reply_to_message:
            # Show list of sudo users
            sudo_users = premium_manager.get_group_sudo_users(group_id)
            
            if not sudo_users:
                await update.message.reply_text(
                    "📋 لیست کاربران سودو خالی است.\n\n"
                    "💡 برای افزودن یا حذف کاربر سودو، روی پیام کاربر ریپلای کرده و دستور /sudo را بنویسید.\n"
                    "🔹 سودو می‌تواند به پنل مدیریت گروه دسترسی داشته باشد."
                )
                return
            
            # Get user info for each sudo user
            sudo_info = []
            for sudo_id in sudo_users:
                try:
                    user = await context.bot.get_chat_member(group_id, sudo_id)
                    name = user.user.first_name
                    username = user.user.username or "بدون نام کاربری"
                    sudo_info.append(f"👤 {name} (@{username}) - ID: {sudo_id}")
                except:
                    sudo_info.append(f"👤 کاربر ناشناس - ID: {sudo_id}")
            
            sudo_list = "\n".join(sudo_info)
            await update.message.reply_text(
                f"📋 لیست کاربران سودو:\n\n{sudo_list}\n\n"
                "💡 برای افزودن یا حذف کاربر سودو، روی پیام کاربر ریپلای کرده و دستور /sudo را بنویسید."
            )
            return
        
        # Get the user to add/remove as sudo
        target_user = update.message.reply_to_message.from_user
        target_id = target_user.id
        
        # Check if target is already a sudo
        sudo_users = premium_manager.get_group_sudo_users(group_id)
        is_sudo = target_id in sudo_users
        
        if is_sudo:
            # Remove from sudo
            success = premium_manager.remove_sudo_user(group_id, target_id)
            if success:
                await update.message.reply_text(f"✅ کاربر {target_user.first_name} از لیست سودو حذف شد.")
            else:
                await update.message.reply_text("❌ خطا در حذف کاربر از لیست سودو.")
        else:
            # Add as sudo
            success = premium_manager.add_sudo_user(group_id, target_id, user_id)
            if success:
                await update.message.reply_text(
                    f"✅ کاربر {target_user.first_name} به لیست سودو اضافه شد.\n"
                    "🔹 این کاربر اکنون می‌تواند به پنل مدیریت گروه دسترسی داشته باشد."
                )
            else:
                await update.message.reply_text("❌ خطا در افزودن کاربر به لیست سودو.")
        
    except Exception as e:
        logger.error(f"Error in sudo_user_handler: {str(e)}")
        await update.message.reply_text(f"خطا در مدیریت کاربران سودو: {str(e)}")

async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo command - Bot repeats the message and deletes the original"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin or has special permissions
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند از دستور اکو استفاده کنند.")
            return
        
        # Check if bot has permission to delete messages
        bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        if not bot_member.can_delete_messages:
            await update.message.reply_text("ربات دسترسی لازم برای حذف پیام‌ها را ندارد.")
            return
        
        # Extract the message text after "اکو"
        if not context.args:
            await update.message.reply_text(
                "لطفاً متن مورد نظر را بعد از کلمه اکو بنویسید.\n\n"
                "مثال: اکو سلام به همه دوستان!"
            )
            return
        
        # Join all arguments to form the complete message
        echo_text = " ".join(context.args)
        
        # Store original message info for potential reply
        original_message = update.message
        reply_to_message = original_message.reply_to_message
        
        # Delete the original command message
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=original_message.message_id
            )
        except Exception as e:
            logger.warning(f"Could not delete original echo message: {str(e)}")
        
        # Send the echo message
        if reply_to_message:
            # If original was a reply, reply to the same message
            await reply_to_message.reply_text(echo_text)
        else:
            # Otherwise send as a normal message
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=echo_text
            )
        
        logger.info(f"Echo command used by admin {update.effective_user.id} in chat {update.effective_chat.id}")
        
    except Exception as e:
        logger.error(f"Error in echo_command: {str(e)}")
        await update.message.reply_text(f"خطا در اجرای دستور اکو: {str(e)}")

async def help_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help pagination callbacks"""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == "help_noop":
            # No operation for page indicator button
            return
        
        if query.data.startswith("help_page_"):
            # Handle page navigation
            await help_command(query, context)
            
        logger.info(f"Help callback handled: {query.data} by user {query.from_user.id}")
    except Exception as e:
        logger.error(f"Error in help_callback_handler: {str(e)}")
        await query.message.reply_text("خطایی در پردازش دکمه‌ها رخ داد. لطفاً دوباره تلاش کنید.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show general group statistics with a nice design"""
    try:
        if update.effective_chat.type == "private":
            await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if chat_member.status not in ['administrator', 'creator'] and update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("فقط ادمین‌های گروه می‌توانند آمار گروه را مشاهده کنند.")
            return
        
        # Check if command has parameters for direct access to specific stats
        command_text = update.message.text.strip()
        
        # Handle Persian commands with parameters
        if ' ' in command_text or '_' in command_text:
            # Extract the parameter
            param = None
            
            if command_text.startswith('آمار_'):
                param = command_text.split('_', 1)[1] if '_' in command_text else ''
            elif command_text.startswith('آمار '):
                param = command_text.split(' ', 1)[1] if ' ' in command_text else ''
            elif command_text.startswith('/stats '):
                param = command_text.split(' ', 1)[1] if ' ' in command_text else ''
                
            # Map parameters to callback data
            param_mapping = {
                'مدیران': 'stats_admins',
                'دسترسی': 'stats_admin_permissions',
                'دسترسی_مدیران': 'stats_admin_permissions',
                'دسترسی مدیران': 'stats_admin_permissions',
                'محتوا': 'stats_content',
                'چت': 'stats_chat',
                'ادد': 'stats_adds',
                'امروز': 'stats_today',
                'admins': 'stats_admins',
                'permissions': 'stats_admin_permissions',
                'admin_permissions': 'stats_admin_permissions',
                'content': 'stats_content',
                'chat': 'stats_chat',
                'adds': 'stats_adds',
                'today': 'stats_today'
            }
            
            # Check if parameter is valid
            if param and param in param_mapping:
                # Create a fake callback query to reuse existing handler
                fake_query = SimpleNamespace()
                fake_query.data = param_mapping[param]
                fake_query.message = update.message
                fake_query.from_user = update.effective_user
                fake_query.answer = lambda *args, **kwargs: None
                fake_query.edit_message_text = update.message.reply_text
                
                # Call the appropriate stats handler
                await stats_callback_handler(fake_query, context)
                return
            
        # Get group info
        chat_id = update.effective_chat.id
        chat_info = await context.bot.get_chat(chat_id)
        
        # Get member count
        member_count = await context.bot.get_chat_member_count(chat_id)
        
        # Get message count from database (if available)
        total_messages = db.count_user_messages(None, chat_id) if hasattr(db, 'count_group_messages') else 0
        
        # Get admin count
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_count = len(admins)
        
        # Get current date and time in Persian format
        tehran_tz = pytz.timezone('Asia/Tehran')
        now_tehran = datetime.now(tehran_tz)
        j_date = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        date_persian = j_date.strftime("%A %d %B %Y")
        time_persian = now_tehran.strftime("%H:%M:%S")
        
        # Get group creation date if available
        creation_date = "نامشخص"
        if hasattr(chat_info, 'date'):
            creation_date = chat_info.date.strftime("%Y-%m-%d")
            
        # Check if group is premium
        is_premium = premium_manager.is_group_premium(chat_id)
        premium_status = "✅ فعال" if is_premium else "❌ غیرفعال"
        
        # Create a beautiful response message
        stats_message = f"""
╭─────「 📊 آمار گروه 」─────╮
│                           │
│  📝 <b>نام گروه:</b>        │
│  {chat_info.title}         
│                           │
│  👥 <b>تعداد اعضا:</b> {member_count:,} نفر │
│  👮‍♂️ <b>تعداد ادمین‌ها:</b> {admin_count} نفر │
│  💬 <b>تعداد پیام‌ها:</b> {total_messages:,} پیام │
│                           │
│  🆔 <b>شناسه گروه:</b>       │
│  <code>{chat_id}</code>    │
│                           │
│  📅 <b>تاریخ ایجاد:</b> {creation_date} │
│  💎 <b>وضعیت اشتراک:</b> {premium_status} │
│                           │
│  🕒 <b>زمان بررسی:</b> {time_persian} │
│  📆 <b>تاریخ بررسی:</b> {date_persian} │
╰───────────────────────────╯
"""
        
        # Create keyboard for more stats
        keyboard = [
            [
                InlineKeyboardButton("📊 آمار مدیران", callback_data="stats_admins"),
                InlineKeyboardButton("👮‍♂️ دسترسی مدیران", callback_data="stats_admin_permissions")
            ],
            [
                InlineKeyboardButton("📝 آمار محتوا", callback_data="stats_content"),
                InlineKeyboardButton("💬 آمار چت", callback_data="stats_chat")
            ],
            [
                InlineKeyboardButton("➕ آمار ادد", callback_data="stats_adds"),
                InlineKeyboardButton("📅 آمار امروز", callback_data="stats_today")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send the message
        await update.message.reply_text(stats_message, parse_mode='HTML', reply_markup=reply_markup)
        logger.info(f"Stats command executed by user {update.effective_user.id} in chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Error in stats_command: {str(e)}")
        await update.message.reply_text("❌ خطا در دریافت آمار گروه. لطفاً دوباره تلاش کنید.")

async def stats_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stats callback queries"""
    try:
        query = update.callback_query
        await query.answer()
        
        chat_id = query.message.chat.id
        user_id = query.from_user.id
        
        # Check if user is admin
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        if chat_member.status not in ['administrator', 'creator'] and user_id != ADMIN_ID:
            await query.answer("فقط ادمین‌های گروه می‌توانند آمار گروه را مشاهده کنند.", show_alert=True)
            return
            
        # Get current date and time in Persian format
        tehran_tz = pytz.timezone('Asia/Tehran')
        now_tehran = datetime.now(tehran_tz)
        j_date = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        date_persian = j_date.strftime("%A %d %B %Y")
        time_persian = now_tehran.strftime("%H:%M:%S")
        
        # Handle different stats types
        if query.data == "stats_main":
            # Return to main stats
            # Get group info
            chat_info = await context.bot.get_chat(chat_id)
            
            # Get member count
            member_count = await context.bot.get_chat_member_count(chat_id)
            
            # Get message count from database (if available)
            total_messages = db.count_user_messages(None, chat_id) if hasattr(db, 'count_group_messages') else 0
            
            # Get admin count
            admins = await context.bot.get_chat_administrators(chat_id)
            admin_count = len(admins)
            
            # Get group creation date if available
            creation_date = "نامشخص"
            if hasattr(chat_info, 'date'):
                creation_date = chat_info.date.strftime("%Y-%m-%d")
                
            # Check if group is premium
            is_premium = premium_manager.is_group_premium(chat_id)
            premium_status = "✅ فعال" if is_premium else "❌ غیرفعال"
            
            # Create a beautiful response message
            stats_message = f"""
╭─────「 📊 آمار گروه 」─────╮
│                           │
│  📝 <b>نام گروه:</b>        │
│  {chat_info.title}         
│                           │
│  👥 <b>تعداد اعضا:</b> {member_count:,} نفر │
│  👮‍♂️ <b>تعداد ادمین‌ها:</b> {admin_count} نفر │
│  💬 <b>تعداد پیام‌ها:</b> {total_messages:,} پیام │
│                           │
│  🆔 <b>شناسه گروه:</b>       │
│  <code>{chat_id}</code>    │
│                           │
│  📅 <b>تاریخ ایجاد:</b> {creation_date} │
│  💎 <b>وضعیت اشتراک:</b> {premium_status} │
│                           │
│  🕒 <b>زمان بررسی:</b> {time_persian} │
│  📆 <b>تاریخ بررسی:</b> {date_persian} │
╰───────────────────────────╯
"""
            
            # Create keyboard for more stats
            keyboard = [
                [
                    InlineKeyboardButton("📊 آمار مدیران", callback_data="stats_admins"),
                    InlineKeyboardButton("👮‍♂️ دسترسی مدیران", callback_data="stats_admin_permissions")
                ],
                [
                    InlineKeyboardButton("📝 آمار محتوا", callback_data="stats_content"),
                    InlineKeyboardButton("💬 آمار چت", callback_data="stats_chat")
                ],
                [
                    InlineKeyboardButton("➕ آمار ادد", callback_data="stats_adds"),
                    InlineKeyboardButton("📅 آمار امروز", callback_data="stats_today")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Update the message
            await query.edit_message_text(stats_message, parse_mode='HTML', reply_markup=reply_markup)
            return
            
        elif query.data == "stats_admins":
            # Get admins info
            admins = await context.bot.get_chat_administrators(chat_id)
            
            # Create admin list
            admin_list = ""
            for i, admin in enumerate(admins, 1):
                user = admin.user
                status = "👑 سازنده" if admin.status == "creator" else "👮‍♂️ ادمین"
                username = f"@{user.username}" if user.username else "بدون نام کاربری"
                admin_list += f"{i}. {status}: <b>{user.first_name}</b> ({username})\n"
            
            # Create a beautiful response message
            stats_message = f"""
╭─────「 👮‍♂️ آمار مدیران 」─────╮
│                              │
│  👥 <b>تعداد کل مدیران:</b> {len(admins)} نفر │
│                              │
│  📋 <b>لیست مدیران:</b>         │
{admin_list}│                              │
│  🕒 <b>زمان بررسی:</b> {time_persian} │
│  📆 <b>تاریخ بررسی:</b> {date_persian} │
╰──────────────────────────────╯
"""
            
        elif query.data == "stats_admin_permissions":
            # Get admins with their permissions
            admins = await context.bot.get_chat_administrators(chat_id)
            
            # Create admin permissions list
            admin_perms = ""
            for i, admin in enumerate(admins, 1):
                user = admin.user
                status = "👑 سازنده" if admin.status == "creator" else "👮‍♂️ ادمین"
                username = f"@{user.username}" if user.username else "بدون نام کاربری"
                
                # Get permissions
                perms = []
                if admin.can_change_info:
                    perms.append("تغییر اطلاعات")
                if admin.can_delete_messages:
                    perms.append("حذف پیام")
                if admin.can_invite_users:
                    perms.append("دعوت کاربر")
                if admin.can_restrict_members:
                    perms.append("محدود کردن")
                if admin.can_pin_messages:
                    perms.append("پین پیام")
                if admin.can_promote_members:
                    perms.append("ارتقاء")
                
                perm_text = ", ".join(perms) if perms else "بدون دسترسی"
                admin_perms += f"{i}. <b>{user.first_name}</b> ({status}):\n   {perm_text}\n\n"
            
            # Create a beautiful response message
            stats_message = f"""
╭────「 🔐 دسترسی مدیران 」────╮
│                             │
│  👥 <b>تعداد کل مدیران:</b> {len(admins)} نفر │
│                             │
│  📋 <b>دسترسی‌ها:</b>           │
{admin_perms}│                             │
│  🕒 <b>زمان بررسی:</b> {time_persian} │
│  📆 <b>تاریخ بررسی:</b> {date_persian} │
╰─────────────────────────────╯
"""
            
        elif query.data == "stats_content":
            # Get content statistics (placeholder - should be implemented with actual database queries)
            total_messages = db.count_user_messages(None, chat_id) if hasattr(db, 'count_group_messages') else 0
            text_messages = int(total_messages * 0.7)  # Placeholder - should be from database
            photo_messages = int(total_messages * 0.15)  # Placeholder
            video_messages = int(total_messages * 0.1)  # Placeholder
            voice_messages = int(total_messages * 0.03)  # Placeholder
            document_messages = int(total_messages * 0.02)  # Placeholder
            
            # Create a beautiful response message
            stats_message = f"""
╭────「 📝 آمار محتوا 」────╮
│                         │
│  💬 <b>کل پیام‌ها:</b> {total_messages:,} │
│  📝 <b>متن:</b> {text_messages:,} │
│  🖼 <b>عکس:</b> {photo_messages:,} │
│  🎬 <b>ویدیو:</b> {video_messages:,} │
│  🎤 <b>صدا:</b> {voice_messages:,} │
│  📁 <b>فایل:</b> {document_messages:,} │
│                         │
│  🕒 <b>زمان بررسی:</b> {time_persian} │
│  📆 <b>تاریخ بررسی:</b> {date_persian} │
╰─────────────────────────╯
"""
            
        elif query.data == "stats_chat":
            # Get chat activity statistics (placeholder)
            total_messages = db.count_user_messages(None, chat_id) if hasattr(db, 'count_group_messages') else 0
            
            # Placeholder data - should be from database
            today_messages = int(total_messages * 0.05)
            week_messages = int(total_messages * 0.3)
            month_messages = int(total_messages * 0.65)
            
            avg_daily = int(total_messages / 30)  # Placeholder
            most_active_hour = "18:00 - 20:00"  # Placeholder
            
            # Create a beautiful response message
            stats_message = f"""
╭────「 💬 آمار چت 」────╮
│                       │
│  💬 <b>کل پیام‌ها:</b> {total_messages:,} │
│  📅 <b>امروز:</b> {today_messages:,} │
│  📆 <b>هفته اخیر:</b> {week_messages:,} │
│  🗓 <b>ماه اخیر:</b> {month_messages:,} │
│                       │
│  📊 <b>میانگین روزانه:</b> {avg_daily:,} │
│  🕒 <b>ساعت فعال:</b> {most_active_hour} │
│                       │
│  🕒 <b>زمان بررسی:</b> {time_persian} │
│  📆 <b>تاریخ بررسی:</b> {date_persian} │
╰───────────────────────╯
"""
            
        elif query.data == "stats_adds":
            # Get member add statistics (placeholder)
            member_count = await context.bot.get_chat_member_count(chat_id)
            
            # Placeholder data - should be from database
            today_adds = int(member_count * 0.02)
            week_adds = int(member_count * 0.1)
            month_adds = int(member_count * 0.25)
            
            # Placeholder data for left members
            today_left = int(today_adds * 0.3)
            week_left = int(week_adds * 0.3)
            month_left = int(month_adds * 0.3)
            
            # Create a beautiful response message
            stats_message = f"""
╭────「 ➕ آمار ادد 」────╮
│                       │
│  👥 <b>کل اعضا:</b> {member_count:,} │
│                       │
│  ➕ <b>اضافه شده امروز:</b> {today_adds} │
│  ➕ <b>اضافه شده هفته:</b> {week_adds} │
│  ➕ <b>اضافه شده ماه:</b> {month_adds} │
│                       │
│  ➖ <b>خارج شده امروز:</b> {today_left} │
│  ➖ <b>خارج شده هفته:</b> {week_left} │
│  ➖ <b>خارج شده ماه:</b> {month_left} │
│                       │
│  🕒 <b>زمان بررسی:</b> {time_persian} │
│  📆 <b>تاریخ بررسی:</b> {date_persian} │
╰───────────────────────╯
"""
            
        elif query.data == "stats_today":
            # Get today's statistics (placeholder)
            
            # Placeholder data - should be from database
            today_messages = 250
            today_members = 5
            today_left = 2
            today_warns = 3
            today_mutes = 2
            today_pins = 1
            
            # Create a beautiful response message
            stats_message = f"""
╭────「 📅 آمار امروز 」────╮
│                         │
│  📆 <b>تاریخ:</b> {date_persian} │
│                         │
│  💬 <b>پیام‌های امروز:</b> {today_messages:,} │
│  ➕ <b>اعضای جدید:</b> {today_members} │
│  ➖ <b>اعضای خارج شده:</b> {today_left} │
│  ⚠️ <b>اخطارها:</b> {today_warns} │
│  🔇 <b>سکوت‌ها:</b> {today_mutes} │
│  📌 <b>پین‌ها:</b> {today_pins} │
│                         │
│  🕒 <b>زمان بررسی:</b> {time_persian} │
╰─────────────────────────╯
"""
            
        else:
            await query.edit_message_text("دستور نامعتبر است.")
            return
            
        # Create keyboard for navigation
        keyboard = [
            [
                InlineKeyboardButton("📊 آمار مدیران", callback_data="stats_admins"),
                InlineKeyboardButton("👮‍♂️ دسترسی مدیران", callback_data="stats_admin_permissions")
            ],
            [
                InlineKeyboardButton("📝 آمار محتوا", callback_data="stats_content"),
                InlineKeyboardButton("💬 آمار چت", callback_data="stats_chat")
            ],
            [
                InlineKeyboardButton("➕ آمار ادد", callback_data="stats_adds"),
                InlineKeyboardButton("📅 آمار امروز", callback_data="stats_today")
            ],
            [
                InlineKeyboardButton("🔄 بازگشت به آمار اصلی", callback_data="stats_main")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update the message
        await query.edit_message_text(stats_message, parse_mode='HTML', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in stats_callback_handler: {str(e)}")
        await query.edit_message_text("❌ خطا در دریافت آمار. لطفاً دوباره تلاش کنید.")

def main():
    """Main function to run the bot"""
    try:
        # Load premium groups cache on startup
        load_premium_groups()
        
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Set post init callback
        application.post_init = post_init
        
        # Register handlers from moderation.py
        register_handlers(application)
        
        # Add basic handlers (no premium required)
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("subscription", subscription_status))
        application.add_handler(CommandHandler("buypremium", buy_premium))
        application.add_handler(CommandHandler("currency", currency_command))
        application.add_handler(CommandHandler("crypto", crypto_command))
        application.add_handler(CommandHandler("gold", gold_command))
        application.add_handler(CommandHandler("convert", convert_command))
        application.add_handler(CommandHandler("market", market_command))
        application.add_handler(CommandHandler("time", show_current_time))
        application.add_handler(CommandHandler("stats", stats_command))  # Add stats command
        
        # Add callback handlers
        application.add_handler(CallbackQueryHandler(help_callback_handler, pattern='^help_'))
        application.add_handler(CallbackQueryHandler(stats_callback_handler, pattern='^stats_'))  # Add stats callback handler
        application.add_handler(CallbackQueryHandler(handle_subscription_callback, pattern='^sub_'))
        application.add_handler(CallbackQueryHandler(admin_callback, pattern='^admin_'))
        application.add_handler(CallbackQueryHandler(glass_callback_handler, pattern='^glass_'))
        application.add_handler(CallbackQueryHandler(report_callback_handler, pattern='^report_'))
        application.add_handler(CallbackQueryHandler(reports_callback_handler, pattern='^reports_'))
        application.add_handler(CallbackQueryHandler(admin_abuse_callback_handler, pattern='^abuse_'))
        application.add_handler(CallbackQueryHandler(user_info_callback_handler, pattern='^userinfo_'))
        
        # Add premium-required handlers
        application.add_handler(CommandHandler("warn", premium_warn_user))
        application.add_handler(CommandHandler("unwarn", premium_unwarn_user))
        application.add_handler(CommandHandler("admin", premium_admin_panel))
        application.add_handler(CommandHandler("locktime", premium_lock_time_messages))
        application.add_handler(CommandHandler("unlocktime", premium_unlock_time_messages))
        application.add_handler(CommandHandler("forcejoin", premium_set_force_join))
        application.add_handler(CommandHandler("unforcejoin", premium_unset_force_join))
        application.add_handler(CommandHandler("ban", premium_ban_user))
        application.add_handler(CommandHandler("unban", premium_unban_user))  # اضافه کردن دستور رفع بن
        application.add_handler(CommandHandler("kick", premium_kick_user))
        application.add_handler(CommandHandler("mute", premium_mute_user))
        application.add_handler(CommandHandler("unmute", premium_unmute_user))
        application.add_handler(CommandHandler("mutelist", list_muted_users))
        application.add_handler(CommandHandler("delete", delete_message))
        application.add_handler(CommandHandler("startvoice", start_voice_chat))
        application.add_handler(CommandHandler("stopvoice", stop_voice_chat))
        application.add_handler(CommandHandler("pin", pin_message))
        application.add_handler(CommandHandler("unpin", unpin_message))
        application.add_handler(CommandHandler("promote", premium_promote_user))
        application.add_handler(CommandHandler("demote", premium_demote_user))
        application.add_handler(CommandHandler("special", premium_special_user))
        application.add_handler(CommandHandler("sudo", sudo_user_handler))
        application.add_handler(CommandHandler("echo", echo_command))
        
        # Add glass links handlers
        application.add_handler(CommandHandler("glass", glass_command))
        
        # Add admin-only subscription management handlers
        application.add_handler(CommandHandler("addpremium", add_premium_group))
        application.add_handler(CommandHandler("listpremium", list_premium_groups))
        application.add_handler(CommandHandler("refreshcache", load_premium_groups))
        
        # Add broadcast handler (admin only)
        application.add_handler(CommandHandler("broadcast", admin_broadcast_handler))
        
        # Add report handler
        application.add_handler(CommandHandler("report", report_command))
        application.add_handler(CommandHandler("reportadmin", report_admin_abuse))
        
        # Add callback query handler for admin panel and subscription
        application.add_handler(CallbackQueryHandler(admin_callback, pattern='^(admin_panel|bot_stats|manage_subscriptions|stats|warned_users|banned_users|welcome_settings|premium_groups|add_premium|remove_premium|back_to_main|welcome_on|welcome_off|broadcast|refresh_cache|buyer_stats|buyer_warned_users|buyer_banned_users|buyer_welcome_settings|buyer_telegram_service_lock|telegram_service_lock|lock_photo|lock_video|lock_document|lock_animation|unlock_all|lock_voice|lock_sticker|lock_contact|lock_location|lock_poll|lock_game|lock_text|lock_forward|lock_url|lock_all|lock_new_members|lock_join_messages|lock_pin_messages|lock_video_chat_messages)$'))
        application.add_handler(CallbackQueryHandler(handle_subscription_callback, pattern='^(buy_premium|select_plan:.*|cancel_buy_premium|check_subscription|help|approve_sub_.*|reject_sub_.*|group_stats_.*|sub_history_.*)$'))
        application.add_handler(CallbackQueryHandler(report_callback_handler, pattern='^report_'))
        application.add_handler(CallbackQueryHandler(admin_abuse_callback_handler, pattern='^admin_abuse_'))
        
        # Add weather callback handler
        application.add_handler(CallbackQueryHandler(weather_callback_handler, pattern='^weather_'))
        
        # Add glass links callback handler
        application.add_handler(CallbackQueryHandler(glass_callback_handler, pattern='^glass_'))
        
        # Add message handler for Persian commands and premium checks
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, premium_check_message_advanced))
        
        # Add handler for new member messages
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member_message))
        
        # Add handler for service messages
        application.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER |
            filters.StatusUpdate.PINNED_MESSAGE | 
            filters.StatusUpdate.VIDEO_CHAT_STARTED | filters.StatusUpdate.VIDEO_CHAT_ENDED | 
            filters.StatusUpdate.VIDEO_CHAT_PARTICIPANTS_INVITED,
            delete_service_messages
        ))
        
        # Setup admin abuse handlers
        setup_admin_abuse_handlers(application)
        
        # Persian commands are now handled by handle_persian_commands function
        # Remove duplicate regex handlers to avoid conflicts
        # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^تنظیم لقب'), set_nickname_handler))
        # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^لقب$'), show_nickname_handler))
        # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^حذف لقب$'), remove_nickname_handler))
        
        # Persian commands are now handled by handle_persian_commands function
        # Remove duplicate regex handlers to avoid conflicts  
        # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^(اطلاعات|آمار کاربر)$'), user_info_handler))
        application.add_handler(CallbackQueryHandler(user_info_callback_handler, pattern='^user_(activity|warnings|info)_'))
        
        # Persian commands are now handled by handle_persian_commands function
        # Remove duplicate regex handlers to avoid conflicts
        # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^آب و هوا'), weather_handler))
        
        # Run the bot
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        raise

if __name__ == '__main__':
    main()
