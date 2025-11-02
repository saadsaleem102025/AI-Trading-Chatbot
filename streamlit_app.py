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

# === AUTO REFRESH QUOTES & MOTIVATION (30s) ===
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
        "Calm minds trade best."
    ])

# === REFRESH META TAG ===
st.sidebar.markdown("<meta http-equiv='refresh' content='30'>", unsafe_allow_html=True)

# === FUNCTIONS ===
def detect_symbol_type(symbol):
    crypto_list = ["BTC", "ETH", "SOL", "AVAX", "BNB", "XRP", "DOGE", "ADA", "DOT", "LTC"]
    return "crypto" if symbol.upper() in crypto_list else "noncrypto"

def get_crypto_price(symbol_id, vs_currency="usd"):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": symbol_id.lower(), "vs_currencies": vs_currency, "include_24hr_change": "true"}
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        data = res.json().get(symbol_id.lower(), {})
        return round(data.get(vs_currency, 0), 2), round(data.get(f"{vs_currency}_24h_change", 0), 2)
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
    prompt = f"""
    Technical analysis for {symbol} ({vs_currency.upper()}):
    - RSI: {rsi_text}
    - Bollinger Bands: {boll_text}
    - Supertrend: {trend_text}
    Price: {price:.2f} {vs_currency.upper()}
    Suggest realistic entry/exit:
    "Buy near {price*0.98:.2f}, Target {price*1.03:.2f}, Stop {price*0.96:.2f}".
    End with 1 motivational line.
    """
    try:
        res = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content.strip()
    except:
        return f"{symbol} analysis unavailable — stay disciplined."

# === SIDEBAR STYLE ===
st.sidebar.markdown("""
<style>
[data-testid="stSidebar"] {
    padding-top: 0rem !important;
    background-color: #F8F9FA;
    overflow-y: visible !important;
}
.crypto-symbol {font-size: 26px; font-weight: 800; color: #000;}
.crypto-price {font-size: 22px; font-weight: 700;}
.crypto-change {font-size: 18px; font-weight: 600;}
.sidebar-section {margin-bottom: 0.8rem;}
</style>
""", unsafe_allow_html=True)

# === SIDEBAR CONTENT ===
st.sidebar.title("📊 Market Context Panel")

# BTC / ETH Prices
st.sidebar.markdown("### 🪙 Live Crypto Snapshot")
btc_price, btc_change = get_crypto_price("bitcoin")
eth_price, eth_change = get_crypto_price("ethereum")

st.sidebar.markdown(
    f"<div class='crypto-symbol'>BTC</div>"
    f"<div class='crypto-price'>${btc_price:,.2f}</div>"
    f"<div class='crypto-change' style='color:{'green' if btc_change>=0 else 'red'}'>{btc_change:+.2f}%</div>",
    unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.markdown(
    f"<div class='crypto-symbol'>ETH</div>"
    f"<div class='crypto-price'>${eth_price:,.2f}</div>"
    f"<div class='crypto-change' style='color:{'green' if eth_change>=0 else 'red'}'>{eth_change:+.2f}%</div>",
    unsafe_allow_html=True)
st.sidebar.markdown("---")

# Timezone
st.sidebar.markdown("### 🌍 Select Your Timezone (UTC Offset)")
utc_offsets = [f"UTC{offset:+d}" for offset in range(-12, 13)]
user_offset = st.sidebar.selectbox("Timezone", utc_offsets, index=5)

offset_hours = int(user_offset.replace("UTC", ""))
user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset_hours)
session, vol = fx_session_volatility(user_time.hour)

st.sidebar.markdown(f"### 💹 {session}")
st.sidebar.info(interpret_vol(vol))
st.sidebar.caption(f"🕒 Local Time: {user_time.strftime('%Y-%m-%d %H:%M:%S')} ({user_offset})")
st.sidebar.markdown("---")

# Motivation
st.sidebar.markdown(f"💬 **Motivation:** {st.session_state.quote}")

# === MAIN CHAT ===
st.title("AI Trading Chatbot")

col1, col2 = st.columns([2, 1])
with col1:
    user_input = st.text_input("Enter Asset Name or Symbol (e.g., BTC, AAPL, EURUSD, GOLD)")
with col2:
    vs_currency = st.text_input("Quote Currency (e.g., USD, EUR, JPY)", "usd").lower()

if user_input:
    symbol = user_input.strip().upper()
    sym_type = detect_symbol_type(symbol)
    df = get_twelve_data(f"{symbol}/{vs_currency.upper()}") if sym_type == "crypto" else get_twelve_data(symbol)
    price = get_crypto_price(symbol.lower(), vs_currency)[0] if sym_type == "crypto" else (df["close"].astype(float).iloc[-1] if df is not None else 0.0)

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
