import streamlit as st
import time
import requests
import datetime
import pandas as pd
import numpy as np
import random

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === CUSTOM STYLING (IMPROVED SIDEBAR) ===
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background-color: #f5f7fa;
    padding: 1.5rem 1rem;
}

/* Sidebar title */
.sidebar-title {
    font-size: 28px !important;
    font-weight: 800;
    color: #1e293b;
    margin-bottom: 12px;
}

/* Subtitles */
.sidebar-subtitle {
    font-size: 20px;
    font-weight: 600;
    color: #334155;
    margin-top: 18px;
    margin-bottom: 8px;
}

/* Sidebar text */
.sidebar-item {
    font-size: 17px;
    line-height: 1.5;
    color: #334155;
    margin-bottom: 8px;
    word-wrap: break-word;
    white-space: normal;
}

/* Highlighted items like BTC / ETH */
.sidebar-highlight {
    font-weight: 700;
    color: #0f172a;
}

/* Caption at bottom */
.sidebar caption {
    font-size: 14px;
    color: #475569;
    margin-top: 14px;
}
</style>
""", unsafe_allow_html=True)

# === API KEY ===
TWELVE_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]

# === AUTO REFRESH EVERY 30 SECONDS ===
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.rerun()

# === CRYPTO MAP ===
CRYPTO_ID_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "AVAX": "avalanche-2",
    "BNB": "binancecoin", "XRP": "ripple", "DOGE": "dogecoin", "ADA": "cardano",
    "DOT": "polkadot", "LTC": "litecoin", "CFX": "conflux-token", "XLM": "stellar",
    "SHIB": "shiba-inu", "PEPE": "pepe", "TON": "the-open-network",
    "SUI": "sui", "NEAR": "near"
}

def detect_symbol_type(symbol):
    return "crypto" if symbol.upper() in CRYPTO_ID_MAP else "noncrypto"

# === PRICE FETCHER ===
def get_crypto_price(symbol, vs_currency="usd"):
    sid = CRYPTO_ID_MAP.get(symbol.upper(), symbol.lower())
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": sid, "vs_currencies": vs_currency, "include_24hr_change": "true"}
        res = requests.get(url, params=params, timeout=10)
        data = res.json().get(sid, {})
        price = data.get(vs_currency, 0)
        change = data.get(f"{vs_currency}_24h_change", 0)
        if 0.000001 < price < 1000000:
            return round(price, 6), round(change, 2)
    except:
        pass
    try:
        pair = f"{symbol.upper()}USDT"
        res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={pair}", timeout=10).json()
        price = float(res.get("price", 0))
        if 0.000001 < price < 1000000:
            return round(price, 6), 0.0
    except:
        pass
    try:
        res = requests.get(f"https://api.twelvedata.com/price?symbol={symbol.upper()}/USD&apikey={TWELVE_API_KEY}", timeout=10).json()
        price = float(res.get("price", 0))
        if 0.000001 < price < 1000000:
            return round(price, 6), 0.0
    except:
        pass
    return 0.0, 0.0

# === PRICE HISTORY FETCH ===
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

# === TECHNICAL INDICATORS ===
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
    if rsi < 30: return "RSI indicates oversold — potential bullish reversal."
    if rsi > 70: return "RSI indicates overbought — possible correction ahead."
    return "RSI shows neutral momentum — sideways or consolidation likely."

def bollinger_signal(df):
    try:
        df["MA20"] = df["close"].rolling(window=20).mean()
        df["STD"] = df["close"].rolling(window=20).std()
        df["Upper"] = df["MA20"] + 2 * df["STD"]
        df["Lower"] = df["MA20"] - 2 * df["STD"]
        c = df["close"].iloc[-1]
        if c > df["Upper"].iloc[-1]: return "Price near upper Bollinger Band — overbought zone."
        if c < df["Lower"].iloc[-1]: return "Price near lower Bollinger Band — oversold zone."
        return "Price within normal Bollinger Band range."
    except:
        return "Bollinger Band signal neutral."

def supertrend_signal(df):
    try:
        hl2 = (df["high"] + df["low"]) / 2
        atr = df["high"] - df["low"]
        lower = hl2 - 3 * atr
        close = df["close"].iloc[-1]
        if close > lower.iloc[-1]:
            return "Supertrend indicates bullish momentum."
        else:
            return "Supertrend indicates bearish pressure."
    except:
        return "Supertrend signal neutral."

# === VOLATILITY ===
def fx_session_volatility(hour):
    if 22 <= hour or hour < 7: return "Sydney Session", 40
    if 7 <= hour < 16: return "London Session", 100
    if 12 <= hour < 21: return "New York Session", 120
    return "Tokyo Session", 60

def interpret_vol(vol):
    if vol < 40: return "⚪ Low Volatility – Sideways Market"
    if vol < 80: return "🟢 Moderate Volatility – Steady Moves"
    if vol < 120: return "🟡 Active – Good Trading Conditions"
    return "🔴 High Volatility – Reversal Risk"

# === AI ANALYSIS ===
def get_ai_analysis(symbol, price, rsi_text, boll_text, trend_text, vs_currency, df):
    if price <= 0:
        price = 1.0
    try:
        df["H-L"] = df["high"] - df["low"]
        df["H-PC"] = abs(df["high"] - df["close"].shift(1))
        df["L-PC"] = abs(df["low"] - df["close"].shift(1))
        df["TR"] = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
        atr = df["TR"].rolling(window=14).mean().iloc[-1]
        if np.isnan(atr) or atr == 0:
            atr = price * 0.01
    except:
        atr = price * 0.01

    entry = round(price - 0.2 * atr, 4)
    target = round(price + 0.5 * atr, 4)
    stop = round(price - 0.4 * atr, 4)

    motivation = random.choice([
        "Patience is the hidden edge — consistency beats prediction.",
        "Control your emotions; focus on process, not outcome.",
        "Discipline turns volatility into opportunity.",
        "Stay calm; trends favor the patient trader.",
        "Trading success is built on small, smart decisions repeated daily."
    ])

    return f"""
📈 **AI Technical Summary for {symbol} ({vs_currency.upper()})**

{rsi_text}
{boll_text}
{trend_text}

**Suggested Trading Plan**
- 💰 **Buy near:** {entry} {vs_currency.upper()}
- 🎯 **Target:** {target} {vs_currency.upper()}
- 🛑 **Stop Loss:** {stop} {vs_currency.upper()}

💡 *{motivation}*
""".strip()

# === SIDEBAR ===
st.sidebar.markdown("<p class='sidebar-title'>📊 Market Context Panel</p>", unsafe_allow_html=True)

btc_price, btc_change = get_crypto_price("BTC")
eth_price, eth_change = get_crypto_price("ETH")

st.sidebar.markdown(f"<p class='sidebar-item'><span class='sidebar-highlight'>BTC:</span> ${btc_price:,.4f} ({btc_change:+.2f}%)</p>", unsafe_allow_html=True)
st.sidebar.markdown(f"<p class='sidebar-item'><span class='sidebar-highlight'>ETH:</span> ${eth_price:,.4f} ({eth_change:+.2f}%)</p>", unsafe_allow_html=True)

st.sidebar.markdown("<p class='sidebar-subtitle'>🌍 Select Your Timezone (UTC)</p>", unsafe_allow_html=True)
utc_offsets = [f"UTC{offset:+d}" for offset in range(-12, 13)]
user_offset = st.sidebar.selectbox("Timezone", utc_offsets, index=5)
offset_hours = int(user_offset.replace("UTC", ""))

user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset_hours)
session, vol = fx_session_volatility(user_time.hour)

st.sidebar.markdown(f"<p class='sidebar-item'>🌐 <strong>Session:</strong> {session}</p>", unsafe_allow_html=True)
st.sidebar.markdown(f"<p class='sidebar-item'>{interpret_vol(vol)}</p>", unsafe_allow_html=True)
st.sidebar.caption(f"🕒 Local Time: {user_time.strftime('%H:%M:%S')} ({user_offset})")

# === MAIN ===
st.title("AI Trading Chatbot")

col1, col2 = st.columns([2, 1])
with col1:
    user_input = st.text_input("Enter Asset Symbol (e.g., BTC, AAPL, EURUSD, XLM)")
with col2:
    vs_currency = st.text_input("Quote Currency", "usd").lower()

if user_input:
    symbol = user_input.strip().upper()
    sym_type = detect_symbol_type(symbol)
    if sym_type == "crypto":
        price, _ = get_crypto_price(symbol, vs_currency)
        df = get_twelve_data(f"{symbol}/{vs_currency.upper()}")
    else:
        df = get_twelve_data(symbol)
        price = df["close"].astype(float).iloc[-1] if df is not None else 0.0

    if df is None or df.empty or price <= 0:
        price, _ = get_crypto_price(symbol, vs_currency)
        df = pd.DataFrame({"close": [price]*50, "high": [price*1.01]*50, "low": [price*0.99]*50})

    rsi = calculate_rsi(df)
    ai_text = get_ai_analysis(symbol, price, interpret_rsi(rsi), bollinger_signal(df), supertrend_signal(df), vs_currency, df)
    st.success(ai_text)
else:
    st.info("💬 Enter an asset symbol to get AI-powered real-time analysis.")
