from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from binance.client import Client
from dotenv import load_dotenv
import sqlite3
import asyncio
import pandas as pd
import ta
import time
import os

load_dotenv()

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

CHANNEL = int(os.getenv("CHANNEL_ID"))

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

try:
    client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
except Exception as e:
    print(f"Binance connection failed: {e}")
    client = None

COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
# ================= DATABASE =================
conn = sqlite3.connect("cryptrix.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    plan TEXT DEFAULT 'none',
    status TEXT DEFAULT 'free',
    vip INTEGER DEFAULT 0,
    paid INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    created_at INTEGER
)
""")
conn.commit()

# ================= DB HELPERS =================
def add_user(uid, username):
    cursor.execute("""
    INSERT OR IGNORE INTO users (user_id, username, created_at)
    VALUES (?, ?, ?)
    """, (uid, username, int(time.time())))
    conn.commit()

def set_plan(uid, plan):
    cursor.execute("UPDATE users SET plan=?, status='pending' WHERE user_id=?", (plan, uid))
    conn.commit()

def set_vip(uid):
    cursor.execute("UPDATE users SET vip=1, paid=1, status='vip' WHERE user_id=?", (uid,))
    conn.commit()

def get_plan(uid):
    cursor.execute("SELECT plan FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    return row[0] if row else "none"

def get_vip_users():
    cursor.execute("SELECT user_id FROM users WHERE vip=1")
    return cursor.fetchall()

# ================= INVITE LINK =================
async def create_invite(context):
    try:
        link = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL,
            member_limit=1
        )
        return link.invite_link
    except Exception as e:
        print("Invite error:", e)
        return None

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id
    add_user(uid, update.effective_user.username or "user")

    keyboard = [
        [InlineKeyboardButton("⚙ Starter ($150)", callback_data="starter")],
        [InlineKeyboardButton("🚀 Pro ($250)", callback_data="pro")],
        [InlineKeyboardButton("💎 Elite ($300)", callback_data="elite")],
        [InlineKeyboardButton("👑 Lifetime ($500)", callback_data="lifetime")],
        [InlineKeyboardButton("ℹ️ About Us", callback_data="about")]
    ]

    await update.message.reply_text(
"""
🚀 WELCOME TO CRYPTRIX TRADER

Our system scans the crypto market for trading opportunities. Make at least $1000 a week while trading with us.

━━━━━━━━━━━━━━

⚙ STARTER - $150

• 5 signals daily\
• BTC & ETH signals
• Basic trade entries
• Community updates
• Standard support

━━━━━━━━━━━━━━

🚀 PRO - $250

• Unlimited signals
• BTC, ETH, SOL, XRP
• Advanced entries
• TP & SL levels
• VIP support
• Market trend updates

━━━━━━━━━━━━━━

💎 ELITE - $300

• Everything in PRO
• Early signal delivery
• Smart Money analysis
• Elite reports
• Priority support
• Future AI upgrades
• Trade for you passively with weekly guaranteed earning

━━━━━━━━━━━━━━

Choose a plan:

⚙ Starter - $150 (Subscription)
🚀 Pro - $250 (Subscription)
💎 Elite - $300 (Subscription)
👑 Lifetime - $500 (One-time)

Select below 👇
""",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= CALLBACK =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    data = q.data

    # ---------- PLAN ----------
    if data in ["starter", "pro", "elite", "lifetime"]:

        set_plan(uid, data)

        msg = f"""
💰 PAYMENT REQUIRED

Plan: {data.upper()}

Network: Solana (SOL)

Send payment to:

3CzoGRmm6JGyaWTA4WbgNQosCBcngpi1aon5Z1T1cAQN
"""

        if data == "lifetime":
            msg += "\n🔥 One-time payment (No renewal)"
        else:
            msg += "\n🔁 Subscription plan"

        msg += "\n\nAfter payment press: I've Paid"

        await q.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 I've Paid", callback_data="paid")]
            ])
        )

    # ---------- ABOUT ----------
    elif data == "about":
        await q.message.reply_text("""
ℹ️ CRYPTRIX ABOUT

We provide AI-assisted crypto trading signals and passive trading.

Features:
• RSI + EMA analysis
• Smart trend detection
• BTC, ETH, SOL, XRP coverage
• Real-time alerts

Goal:
Help traders enter better positions with less emotion and help make as much money as possible
""")

    # ---------- PAID ----------
    elif data == "paid":

        plan = get_plan(uid)

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"""
🚨 PAYMENT REQUEST

User: {uid}
Plan: {plan}
""",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}")
                ]
            ])
        )

        await q.message.reply_text("⏳ Sent to admin.")

    # ---------- APPROVE ----------
    elif data.startswith("approve_"):

        if uid != ADMIN_ID:
            return

        user_id = int(data.split("_")[1])

        set_vip(user_id)

        invite = await create_invite(context)

        if invite:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"""
✅ APPROVED
🔥 VIP ACTIVATED

Join channel:
{invite}
"""
            )

        await q.message.reply_text("Approved.")

    # ---------- REJECT ----------
    elif data.startswith("reject_"):

        if uid != ADMIN_ID:
            return

        user_id = int(data.split("_")[1])

        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Payment rejected."
        )

        await q.message.reply_text("Rejected.")

# ================= SIGNAL ENGINE =================
def get_data(symbol):
    if client is None:
        return None

    try:
        df = pd.DataFrame(
            client.get_klines(symbol=symbol, interval="1m", limit=100),
            columns=["t","o","h","l","c","v","ct","q","n","tb","tq","i"]
        )
        df["c"] = df["c"].astype(float)
        return df
    except:
        return None


def generate_signal():

    for coin in COINS[:2]:

        df = get_data(coin)
        if df is None or len(df) < 60:
            continue

        df["rsi"] = ta.momentum.RSIIndicator(df["c"]).rsi()
        df["ema9"] = ta.trend.EMAIndicator(df["c"], 9).ema_indicator()
        df["ema21"] = ta.trend.EMAIndicator(df["c"], 21).ema_indicator()

        last = df.iloc[-1]

        rsi = last["rsi"]
        ema9 = last["ema9"]
        ema21 = last["ema21"]

        if rsi < 45 and ema9 > ema21:
            return f"""
🟢 BUY SIGNAL
Coin: {coin}
RSI: {rsi:.2f}
"""

        if rsi > 55 and ema9 < ema21:
            return f"""
🔴 SELL SIGNAL
Coin: {coin}
RSI: {rsi:.2f}
"""

    return None

# ================= AUTO SIGNALS =================
async def auto_signals(app):

    while True:

        try:
            signal = await asyncio.to_thread(generate_signal)
        except:
            signal = None

        if signal:
            print("SIGNAL SENT:", signal)
            try:
                await app.bot.send_message(
                    chat_id=CHANNEL,
                    text=signal
                )
            except Exception as e:
                print("Send error:", e)

        await asyncio.sleep(15)  # faster cycle

# ================= STATS =================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    cursor.execute("SELECT wins, losses FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()

    if not row:
        await update.message.reply_text("No data yet.")
        return

    wins, losses = row
    total = wins + losses
    winrate = (wins / total * 100) if total > 0 else 0

    await update.message.reply_text(f"""
📊 STATS

Wins: {wins}
Losses: {losses}
Win Rate: {winrate:.2f}%
""")

# ================= INIT =================
async def post_init(app):
    asyncio.create_task(auto_signals(app))

app = Application.builder().token(TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CallbackQueryHandler(button))

print("🚀 CRYPTRIX FULL SYSTEM RUNNING...")
app.run_polling()