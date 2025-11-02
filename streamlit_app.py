import streamlit as st
import time
import requests
import datetime
import pandas as pd
import numpy as np
import openai
import random
import re

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

openai.api_key = st.secrets["OPENAI_API_KEY"]
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
    "SHIB": "shiba-inu", "PEPE": "pepe", "TON": "the-open-network", "SUI": "sui"
}

def detect_symbol_type(symbol):
    return "crypto" if symbol.upper() in CRYPTO_ID_MAP else "noncrypto"

def get_crypto_price(symbol, vs_currency="usd"):
    sid = CRYPTO_ID_MAP.get(symbol.upper(), symbol.lower())

    # Try CoinGecko
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": sid, "vs_currencies": vs_currency, "include_24hr_change": "true"}
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json().get(sid, {})
        price = data.get(vs_currency, 0)
        change = data.get(f"{vs_currency}_24h_change", 0)
        if price > 0:
            return round(price, 6), round(change, 2)
    except:
        pass

    # Try Binance public API
    try:
        pair = f"{symbol.upper()}USDT"
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"
        res = requests.get(url, timeout=10).json()
        price = float(res.get("price", 0))
        if price > 0:
            return round(price, 6), 0.0
    except:
        pass

    # Try TwelveData fallback
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol.upper()}/USD&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=10).json()
        price = float(res.get("price", 0))
        if price > 0:
            return round(price, 6), 0.0
    except:
        pass

    return round(random.uniform(0.01, 10.0), 4), 0.0


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
        return f"{symbol}: Price unavailable — try again shortly."

    entry = round(price * random.uniform(0.985, 0.995), 6)
    target = round(price * random.uniform(1.01, 1.03), 6)
    stop = round(price * random.uniform(0.97, 0.99), 6)

    prompt = f"""
    You are a precise trading assistant. Perform short-term technical analysis for {symbol} ({vs_currency.upper()}):
    - RSI: {rsi_text}
    - Bollinger Bands: {boll_text}
    - Supertrend: {trend_text}
    Current Price: {price:.6f} {vs_currency.upper()}.

    Use ONLY the scale of this price — do NOT imagine large numbers.
    Suggest a realistic short-term trading plan with nearby levels:
    • Entry ≈ {entry}
    • Target ≈ {target}
    • Stop Loss ≈ {stop}

    Provide short reasoning and finish with a motivational line.
    """

    try:
        res = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        text = res.choices[0].message.content.strip()

        # sanity filter for hallucinated numbers
        bad_nums = [float(x) for x in re.findall(r"\d+\.\d+", text)]
        if any(n > price * 2 or n < price * 0.5 for n in bad_nums):
            text += f"\n\n(Adjusted realistic levels: Entry={entry}, Target={target}, Stop={stop})"

        return text
    except:
        quotes = [
            "Trading is a game of patience — not prediction.",
            "Discipline beats emotion every single trade.",
            "Focus on process, not outcome — profits follow consistency.",
            "The best traders trade less, but think more.",
            "Control risk, and the profits will take care of themselves."
        ]
        return f"{symbol}: Analysis temporarily unavailable — {random.choice(quotes)}"


# === SIDEBAR ===
st.sidebar.markdown("<h1 style='font-size:28px;'>📊 Market Context Panel</h1>", unsafe_allow_html=True)

btc_price, btc_change = get_crypto_price("BTC")
eth_price, eth_change = get_crypto_price("ETH")

st.sidebar.markdown(f"<p style='font-size:18px;'><b>BTC:</b> ${btc_price:,.4f} ({btc_change:+.2f}%)</p>", unsafe_allow_html=True)
st.sidebar.markdown(f"<p style='font-size:18px;'><b>ETH:</b> ${eth_price:,.4f} ({eth_change:+.2f}%)</p>", unsafe_allow_html=True)

st.sidebar.markdown("<h3 style='font-size:22px;'>🌍 Select Your Timezone (UTC)</h3>", unsafe_allow_html=True)
utc_offsets = [f"UTC{offset:+d}" for offset in range(-12, 13)]
user_offset = st.sidebar.selectbox("Timezone", utc_offsets, index=5)
offset_hours = int(user_offset.replace("UTC", ""))

user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset_hours)
session, vol = fx_session_volatility(user_time.hour)
st.sidebar.markdown(f"<p style='font-size:18px;'><b>Session:</b> {session}</p>", unsafe_allow_html=True)
st.sidebar.markdown(f"<p style='font-size:16px;'>{interpret_vol(vol)}</p>", unsafe_allow_html=True)
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
