import feedparser
import sqlite3
import threading
import time
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from datetime import datetime
import os

# ====== قاعدة البيانات ======
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")
conn.commit()

# ====== رابط RSS ======
RSS_FEED = "https://www.investing.com/rss/news_25.rss"

# ====== لوحة الأزرار ======
keyboard = [["📰 الأخبار اليوم"], ["💰 أسعار العملات"], ["📈 أسعار الأسهم"]]
markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False)

# ====== استدعاء Environment Variables ======
TOKEN = os.getenv("TOKEN")  # ضع توكن البوت هنا في Environment Variables
ALPHA_KEY = os.getenv("ALPHA_KEY")  # اختياري للحصول على أسعار الأسهم

# ====== أوامر البوت ======
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    update.message.reply_text(
        "مرحبًا! أنا بوت الأخبار الاقتصادية 📊\nاختر من الأزرار أدناه:",
        reply_markup=markup
    )

# ====== الأخبار من RSS ======
def get_news():
    feed = feedparser.parse(RSS_FEED)
    news_list = []
    for entry in feed.entries[:5]:
        news_list.append(f"📰 {entry.title}\n🔗 {entry.link}")
    return news_list

# ====== أسعار العملات الرقمية ======
def get_crypto_prices():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
    r = requests.get(url).json()
    return f"💰 Bitcoin: ${r['bitcoin']['usd']}\n💰 Ethereum: ${r['ethereum']['usd']}"

# ====== أسعار الأسهم ======
def get_stock_price(symbol="AAPL"):
    if not ALPHA_KEY:
        return "📈 أسعار الأسهم غير مفعلة بعد."
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_KEY}"
    r = requests.get(url).json()
    try:
        price = r["Global Quote"]["05. price"]
        return f"📈 {symbol}: ${price}"
    except:
        return f"📈 {symbol}: غير متوفر"

# ====== التعامل مع الرسائل ======
def message_handler(update: Update, context: CallbackContext):
    text = update.message.text
    if text == "📰 الأخبار اليوم":
        news_items = get_news()
        for news in news_items:
            update.message.reply_text(news)
    elif text == "💰 أسعار العملات":
        update.message.reply_text(get_crypto_prices())
    elif text == "📈 أسعار الأسهم":
        update.message.reply_text(get_stock_price())

# ====== إرسال الأخبار تلقائيًا في أوقات محددة ======
def scheduled_news(updater):
    while True:
        now = datetime.now()
        if now.hour in [9, 18] and now.minute == 0:
            news_items = get_news()
            c.execute("SELECT user_id FROM users")
            all_users = c.fetchall()
            for user in all_users:
                user_id = user[0]
                for news in news_items:
                    try:
                        updater.bot.send_message(chat_id=user_id, text=news)
                    except:
                        pass
            time.sleep(60)
        time.sleep(20)

# ====== تشغيل البوت ======
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))

    threading.Thread(target=scheduled_news, args=(updater,), daemon=True).start()

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
