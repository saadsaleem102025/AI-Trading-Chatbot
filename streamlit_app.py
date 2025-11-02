import streamlit as st
import time
import requests
import datetime
import pandas as pd
import numpy as np
import openai
import random

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

openai.api_key = st.secrets["OPENAI_API_KEY"]
TWELVE_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]

# === AUTO REFRESH EVERY 30 SECONDS ===
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if "quote" not in st.session_state:
    st.session_state.quote = "Stay patient — great setups always return."

if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.session_state.quote = random.choice([
        "Discipline beats impulse — trade the plan, not emotions.",
        "Patience is also a position.",
        "Focus on setups, not outcomes.",
        "Stay consistent — every small win builds your edge.",
        "Calm minds trade best.",
        "Great traders react less, prepare more."
    ])
    st.rerun()

# === UTILITIES ===
def detect_symbol_type(symbol):
    crypto_list = ["BTC", "ETH", "SOL", "AVAX", "BNB", "XRP", "DOGE", "ADA", "DOT", "LTC"]
    return "crypto" if symbol.upper() in crypto_list else "noncrypto"

def get_crypto_price(symbol_id, vs_currency="usd"):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": symbol_id.lower(), "vs_currencies": vs_currency, "include_24hr_change": "true"}
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json().get(symbol_id.lower(), {})
        price = data.get(vs_currency, 0)
        change = data.get(f"{vs_currency}_24h_change", 0)
        if price == 0:
            raise ValueError("Zero price fallback")
        return round(price, 3), round(change, 2)
    except:
        # fallback to TwelveData if CoinGecko fails
        try:
            url = f"https://api.twelvedata.com/price?symbol={symbol_id.upper()}/USD&apikey={TWELVE_API_KEY}"
            res = requests.get(url, timeout=10).json()
            price = float(res.get("price", 0))
            return price, 0.0
        except:
            return 0.0, 0.0

def get_twelve_data(symbol):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1h&outputsize=50&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=10).json()
        if "values" not in res:
            return None
        df = pd.DataFrame(res["values"])
        df[["close", "high", "low"]] = df[["close", "high", "low"]].astype(float)
        return df.sort_values("datetime")
    except:
        return None

def calculate_rsi(df):
    try:
        deltas = np.diff(df["close"].values)
        gain = np.mean([x for x in deltas if x > 0]) if any(x > 0 for x in deltas) else 0
        loss = -np.mean([x for x in deltas if x < 0]) if any(x < 0 for x in deltas) else 1
        rs = gain / loss
        return np.clip(100 - 100 / (1 + rs), 0, 100)
    except:
        return random.uniform(40, 60)

def interpret_rsi(rsi):
    if rsi < 20: return "🔴 <20% → Extreme Oversold | Bullish Reversal Chance"
    if rsi < 40: return "🟠 20–40% → Weak Bearish | Early Long Setup"
    if rsi < 60: return "🟡 40–60% → Neutral | Consolidation"
    if rsi < 80: return "🟢 60–80% → Strong Bullish | Trend Continuation"
    return "🔵 >80% → Overbought | Bearish Reversal Risk"

def bollinger_signal(df):
    try:
        df["MA20"] = df["close"].rolling(window=20).mean()
        df["STD"] = df["close"].rolling(window=20).std()
        df["Upper"] = df["MA20"] + 2 * df["STD"]
        df["Lower"] = df["MA20"] - 2 * df["STD"]
        c = df["close"].iloc[-1]
        if c > df["Upper"].iloc[-1]: return "Above Upper Band → Overbought"
        if c < df["Lower"].iloc[-1]: return "Below Lower Band → Oversold"
        return "Inside Bands → Normal"
    except:
        return "Neutral"

def supertrend_signal(df):
    try:
        hl2 = (df["high"] + df["low"]) / 2
        atr = df["high"] - df["low"]
        lower = hl2 - 3 * atr
        close = df["close"].iloc[-1]
        return "Bullish" if close > lower.iloc[-1] else "Bearish"
    except:
        return "Neutral"

def fx_session_volatility(hour):
    if 22 <= hour or hour < 7: return "Sydney Session", 40
    if 0 <= hour < 9: return "Tokyo Session", 60
    if 7 <= hour < 16: return "London Session", 100
    return "New York Session", 120

def interpret_vol(vol):
    if vol < 40: return "⚪ Low Volatility – Sideways Market"
    if vol < 80: return "🟢 Moderate Volatility – Steady Moves"
    if vol < 120: return "🟡 Active – Good Trading Conditions"
    return "🔴 High Volatility – Reversal Risk"

def get_ai_analysis(symbol, price, rsi_text, boll_text, trend_text, vs_currency):
    if price <= 0:
        return f"{symbol} data not available, check input."
    entry = round(price * random.uniform(0.97, 0.99), 3)
    target = round(price * random.uniform(1.02, 1.05), 3)
    stop = round(price * random.uniform(0.94, 0.97), 3)
    prompt = f"""
    Technical analysis for {symbol} ({vs_currency.upper()}):
    - RSI: {rsi_text}
    - Bollinger Bands: {boll_text}
    - Supertrend: {trend_text}
    Price: {price:.2f} {vs_currency.upper()}

    Suggest a realistic trading plan with:
    Entry ≈ {entry}, Target ≈ {target}, Stop Loss ≈ {stop}.
    End with one motivational message for the trader.
    """
    try:
        res = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content.strip()
    except:
        return f"{symbol} analysis temporarily unavailable — stay focused and follow your plan."

# === SIDEBAR ===
st.sidebar.title("📊 Market Context Panel")

btc_price, btc_change = get_crypto_price("bitcoin")
eth_price, eth_change = get_crypto_price("ethereum")

st.sidebar.markdown(f"**BTC:** ${btc_price:,.2f} ({btc_change:+.2f}%)")
st.sidebar.markdown(f"**ETH:** ${eth_price:,.2f} ({eth_change:+.2f}%)")

st.sidebar.markdown("### 🌍 Select Your Timezone (UTC)")
utc_offsets = [f"UTC{offset:+d}" for offset in range(-12, 13)]
user_offset = st.sidebar.selectbox("Timezone", utc_offsets, index=5)
offset_hours = int(user_offset.replace("UTC", ""))

user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset_hours)
session, vol = fx_session_volatility(user_time.hour)

st.sidebar.markdown(f"**Session:** {session}")
st.sidebar.info(interpret_vol(vol))
st.sidebar.caption(f"🕒 Local Time: {user_time.strftime('%H:%M:%S')} ({user_offset})")
st.sidebar.markdown("---")
st.sidebar.markdown(f"💡 **Motivation:** {st.session_state.quote}")

# === MAIN PANEL ===
st.title("🤖 AI Trading Chatbot")

col1, col2 = st.columns([2, 1])
with col1:
    user_input = st.text_input("Enter Asset Symbol (e.g., BTC, AAPL, EURUSD, GOLD)")
with col2:
    vs_currency = st.text_input("Quote Currency", "usd").lower()

if user_input:
    symbol = user_input.strip().upper()
    sym_type = detect_symbol_type(symbol)

    if sym_type == "crypto":
        price, _ = get_crypto_price(symbol.lower(), vs_currency)
        df = get_twelve_data(f"{symbol}/{vs_currency.upper()}")
    else:
        df = get_twelve_data(symbol)
        price = df["close"].astype(float).iloc[-1] if df is not None else 0.0

    if df is None or df.empty:
        df = pd.DataFrame({"close": [price]*50, "high": [price*1.01]*50, "low": [price*0.99]*50})

    rsi = calculate_rsi(df)
    rsi_text = interpret_rsi(rsi)
    boll_text = bollinger_signal(df)
    trend_text = supertrend_signal(df)
    ai_text = get_ai_analysis(symbol, price, rsi_text, boll_text, trend_text, vs_currency)

    st.success(ai_text)
    st.markdown("---")
    st.subheader(f"📈 Technical Summary for {symbol}")
    st.write(f"**RSI:** {rsi_text}")
    st.write(f"**Bollinger Bands:** {boll_text}")
    st.write(f"**Supertrend:** {trend_text}")
else:
    st.info("💬 Enter an asset symbol to get AI-powered analysis in real-time.")
