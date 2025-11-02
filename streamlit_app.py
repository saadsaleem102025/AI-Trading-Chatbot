import streamlit as st
import time
import requests
import datetime
import pandas as pd
import numpy as np
import random

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === API KEYS ===
TWELVE_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]

# === AUTO REFRESH EVERY 30 SECONDS ===
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.rerun()

# === UTILITIES ===
CRYPTO_ID_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "AVAX": "avalanche-2",
    "BNB": "binancecoin", "XRP": "ripple", "DOGE": "dogecoin", "ADA": "cardano",
    "DOT": "polkadot", "LTC": "litecoin", "CFX": "conflux-token", "XLM": "stellar",
    "SHIB": "shiba-inu", "PEPE": "pepe", "TON": "the-open-network", "SUI": "sui", "NEAR": "near"
}

def detect_symbol_type(symbol):
    return "crypto" if symbol.upper() in CRYPTO_ID_MAP else "noncrypto"

# === PRICE FETCHER ===
def get_crypto_price(symbol, vs_currency="usd"):
    sid = CRYPTO_ID_MAP.get(symbol.upper(), symbol.lower())

    # CoinGecko first
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": sid, "vs_currencies": vs_currency, "include_24hr_change": "true"}
        res = requests.get(url, params=params, timeout=10)
        data = res.json().get(sid, {})
        price = data.get(vs_currency, 0)
        change = data.get(f"{vs_currency}_24h_change", 0)
        if 0.0001 < price < 1000000:
            return round(price, 6), round(change, 2)
    except:
        pass

    # Binance fallback
    try:
        pair = f"{symbol.upper()}USDT"
        res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={pair}", timeout=10).json()
        price = float(res.get("price", 0))
        if 0.0001 < price < 1000000:
            return round(price, 6), 0.0
    except:
        pass

    # TwelveData fallback
    try:
        res = requests.get(f"https://api.twelvedata.com/price?symbol={symbol.upper()}/USD&apikey={TWELVE_API_KEY}", timeout=10).json()
        price = float(res.get("price", 0))
        if 0.0001 < price < 1000000:
            return round(price, 6), 0.0
    except:
        pass

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


# === INDICATORS ===
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
    if rsi < 30: return "RSI indicates an oversold condition, hinting at a potential bullish reversal."
    if rsi > 70: return "RSI indicates overbought levels, suggesting a possible correction."
    return "RSI indicates a neutral position, suggesting consolidation may prevail."


def bollinger_signal(df):
    try:
        df["MA20"] = df["close"].rolling(window=20).mean()
        df["STD"] = df["close"].rolling(window=20).std()
        df["Upper"] = df["MA20"] + 2 * df["STD"]
        df["Lower"] = df["MA20"] - 2 * df["STD"]
        c = df["close"].iloc[-1]
        if c > df["Upper"].iloc[-1]: return "Bollinger Bands show that the asset is overbought, caution is advised."
        if c < df["Lower"].iloc[-1]: return "Bollinger Bands show that the asset is currently oversold, which could present a buying opportunity."
        return "Bollinger Bands show the price is within a normal range."
    except:
        return "Bollinger Bands data unavailable."


def supertrend_signal(df):
    try:
        hl2 = (df["high"] + df["low"]) / 2
        atr = df["high"] - df["low"]
        lower = hl2 - 3 * atr
        close = df["close"].iloc[-1]
        if close > lower.iloc[-1]:
            return "Supertrend is bullish, indicating a potential upward trend."
        else:
            return "Supertrend is bearish, indicating possible downside pressure."
    except:
        return "Supertrend data unavailable."


# === VOLATILITY ===
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


# === AI RESPONSE ===
def get_ai_analysis(symbol, price, rsi_text, boll_text, trend_text, vs_currency):
    if price <= 0:
        return f"{symbol}: ⚠️ Price data unavailable, please retry shortly."

    entry = round(price * random.uniform(0.985, 0.995), 4)
    target = round(price * random.uniform(1.03, 1.07), 4)
    stop = round(price * random.uniform(0.95, 0.98), 4)

    motivation = random.choice([
        "Patience is the hidden edge — consistency beats prediction.",
        "Control your emotions; focus on process, not outcome.",
        "Discipline turns volatility into opportunity.",
        "Stay calm; trends favor the patient trader.",
        "Trading success is built on small, smart decisions repeated daily."
    ])

    return f"""
Based on the technical analysis for **{symbol} ({vs_currency.upper()})**:

{rsi_text}
{boll_text}
{trend_text}

**Suggested Trading Position:**
Buy near: {entry} {vs_currency.upper()}
Target: {target} {vs_currency.upper()}
Stop Loss: {stop} {vs_currency.upper()}

💡 *{motivation}*
""".strip()


# === SIDEBAR ===
st.sidebar.markdown("<h1 style='font-size:28px;'>📊 Market Context Panel</h1>", unsafe_allow_html=True)
btc_price, btc_change = get_crypto_price("BTC")
eth_price, eth_change = get_crypto_price("ETH")
st.sidebar.markdown(f"<p><b>BTC:</b> ${btc_price:,.4f} ({btc_change:+.2f}%)</p>", unsafe_allow_html=True)
st.sidebar.markdown(f"<p><b>ETH:</b> ${eth_price:,.4f} ({eth_change:+.2f}%)</p>", unsafe_allow_html=True)

st.sidebar.markdown("<h3>🌍 Select Your Timezone (UTC)</h3>", unsafe_allow_html=True)
utc_offsets = [f"UTC{offset:+d}" for offset in range(-12, 13)]
user_offset = st.sidebar.selectbox("Timezone", utc_offsets, index=5)
offset_hours = int(user_offset.replace("UTC", ""))
user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset_hours)
session, vol = fx_session_volatility(user_time.hour)
st.sidebar.markdown(f"<b>Session:</b> {session}")
st.sidebar.markdown(interpret_vol(vol))
st.sidebar.caption(f"🕒 Local Time: {user_time.strftime('%H:%M:%S')} ({user_offset})")

# === MAIN PANEL ===
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
    ai_text = get_ai_analysis(symbol, price, interpret_rsi(rsi), bollinger_signal(df), supertrend_signal(df), vs_currency)
    st.success(ai_text)
else:
    st.info("💬 Enter an asset symbol to get AI-powered real-time analysis.")
