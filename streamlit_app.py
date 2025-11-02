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

# === AUTO REFRESH QUOTES (30s) ===
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

# === REFRESH INTERVAL (BTC/ETH Live Update) ===
st_autorefresh = st.sidebar.empty()
st_autorefresh.markdown(
    "<meta http-equiv='refresh' content='30'>", unsafe_allow_html=True
)

# === HELPER FUNCTIONS ===
def detect_symbol_type(symbol: str):
    crypto_keywords = ["BTC", "ETH", "SOL", "AVAX", "BNB", "XRP", "DOGE", "ADA", "DOT", "LTC"]
    return "crypto" if symbol.upper() in crypto_keywords else "noncrypto"

def get_crypto_price(symbol_id, vs_currency="usd"):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": symbol_id.lower(), "vs_currencies": vs_currency, "include_24hr_change": "true"}
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        data = res.json().get(symbol_id.lower(), {})
        return round(data.get(vs_currency, 0), 2), round(data.get(f"{vs_currency}_24h_change", 0), 2)
    except Exception:
        return 0.0, 0.0

def get_twelve_data(symbol):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1h&outputsize=50&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=10).json()
        if "values" not in res:
            return None
        df = pd.DataFrame(res["values"])
        df[["close", "high", "low"]] = df[["close", "high", "low"]].astype(float)
        df = df.sort_values("datetime")
        return df
    except Exception:
        return None

def calculate_rsi(df):
    try:
        prices = df["close"].values
        deltas = np.diff(prices)
        up = np.mean([d for d in deltas if d > 0]) if any(d > 0 for d in deltas) else 0
        down = -np.mean([d for d in deltas if d < 0]) if any(d < 0 for d in deltas) else 1
        rs = up / down if down != 0 else 0
        return np.clip(100 - 100 / (1 + rs), 0, 100)
    except Exception:
        return random.uniform(40, 60)

def interpret_rsi(rsi):
    if rsi < 20:
        return "🔴 <20% → Extreme Oversold | Bullish Reversal Chance"
    elif rsi < 40:
        return "🟠 20–40% → Weak Bearish | Early Long Setup"
    elif rsi < 60:
        return "🟡 40–60% → Neutral | Consolidation"
    elif rsi < 80:
        return "🟢 60–80% → Strong Bullish | Trend Continuation"
    else:
        return "🔵 >80% → Overbought | Bearish Reversal Risk"

def bollinger_signal(df):
    try:
        df["MA20"] = df["close"].rolling(window=20).mean()
        df["STD"] = df["close"].rolling(window=20).std()
        df["Upper"] = df["MA20"] + 2 * df["STD"]
        df["Lower"] = df["MA20"] - 2 * df["STD"]
        close = df["close"].iloc[-1]
        if close > df["Upper"].iloc[-1]:
            return "Above Upper Band → Overbought"
        elif close < df["Lower"].iloc[-1]:
            return "Below Lower Band → Oversold"
        else:
            return "Inside Bands → Normal"
    except Exception:
        return "Neutral"

def supertrend_signal(df):
    try:
        hl2 = (df["high"] + df["low"]) / 2
        atr = df["high"] - df["low"]
        lower = hl2 - 3 * atr
        close = df["close"].iloc[-1]
        return "Bullish" if close > lower.iloc[-1] else "Bearish"
    except Exception:
        return "Neutral"

def fx_session_volatility(hour_utc):
    if 22 <= hour_utc or hour_utc < 7:
        return "Sydney Session", 40
    elif 0 <= hour_utc < 9:
        return "Tokyo Session", 60
    elif 7 <= hour_utc < 16:
        return "London Session", 100
    else:
        return "New York Session", 120

def interpret_vol(vol):
    if vol < 40:
        return "⚪ Low Volatility – Sideways Market"
    elif vol < 80:
        return "🟢 Moderate Volatility – Steady Moves"
    elif vol < 120:
        return "🟡 Active – Good Trading Conditions"
    else:
        return "🔴 High Volatility – Reversal Risk"

def get_ai_analysis(symbol, price, rsi_text, boll_text, trend_text, vs_currency):
    prompt = f"""
    Provide a concise technical analysis for {symbol} ({vs_currency.upper()}):
    - RSI: {rsi_text}
    - Bollinger Bands: {boll_text}
    - Supertrend: {trend_text}
    Current Price: {price:.2f} {vs_currency.upper()}
    Give realistic entry and exit prices like: "Buy near {price*0.98:.2f} – Target {price*1.03:.2f} – Stop {price*0.96:.2f}".
    End with one motivational line.
    """
    try:
        res = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content.strip()
    except Exception:
        return f"{symbol} analysis unavailable — stay disciplined and trust your process."

# === SIDEBAR STYLING ===
st.sidebar.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        padding-top: 0.3rem !important;
    }
    .crypto-block {
        text-align: center;
        margin-bottom: 0.7rem;
        font-family: 'Segoe UI', sans-serif;
    }
    .crypto-symbol {
        font-size: 24px;
        font-weight: 800;
        color: #0a0a0a;
    }
    .crypto-price {
        font-size: 22px;
        font-weight: 600;
        color: #1a1a1a;
    }
    .crypto-change {
        font-size: 18px;
        font-weight: 500;
        margin-top: 0.1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# === SIDEBAR CONTENT ===
st.sidebar.title("📊 Market Context Panel")
st.sidebar.markdown("### 🪙 Live Crypto Snapshot")

btc_price, btc_change = get_crypto_price("bitcoin")
eth_price, eth_change = get_crypto_price("ethereum")

btc_col, eth_col = st.sidebar.columns(2)
with btc_col:
    st.markdown(f"""
    <div class='crypto-block'>
        <div class='crypto-symbol'>BTC</div>
        <div class='crypto-price'>${btc_price:,.2f}</div>
        <div class='crypto-change' style='color:{"green" if btc_change >= 0 else "red"};'>{btc_change:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with eth_col:
    st.markdown(f"""
    <div class='crypto-block'>
        <div class='crypto-symbol'>ETH</div>
        <div class='crypto-price'>${eth_price:,.2f}</div>
        <div class='crypto-change' style='color:{"green" if eth_change >= 0 else "red"};'>{eth_change:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown("---")

# === TIMEZONE & VOLATILITY ===
st.sidebar.markdown("### 🌍 Select Your Timezone (UTC Offset)")
utc_offsets = [f"UTC{offset:+d}" for offset in range(-12, 13)]
user_offset = st.sidebar.selectbox("Timezone", utc_offsets, index=5)

offset_hours = int(user_offset.replace("UTC", ""))
user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset_hours)
hour_utc = user_time.hour

session, vol = fx_session_volatility(hour_utc)
st.sidebar.markdown(f"### 💹 {session}")
st.sidebar.info(interpret_vol(vol))
st.sidebar.caption(f"🕒 Local Time: {user_time.strftime('%Y-%m-%d %H:%M:%S')} ({user_offset})")

st.sidebar.markdown("---")
st.sidebar.markdown(f"💬 **Motivation:** {st.session_state.quote}")

# === MAIN ===
st.title("AI Trading Chatbot")

col1, col2 = st.columns([2, 1])
with col1:
    user_input = st.text_input("Enter Asset Name or Symbol (e.g., BTC, AAPL, EURUSD, GOLD)")
with col2:
    vs_currency = st.text_input("Quote Currency (e.g., USD, EUR, JPY)", "usd").lower()

if user_input:
    symbol = user_input.strip().upper()
    sym_type = detect_symbol_type(symbol)

    if sym_type == "crypto":
        price, _ = get_crypto_price(symbol.lower(), vs_currency)
        df = get_twelve_data(f"{symbol}/{vs_currency.upper()}")
    else:
        df = get_twelve_data(symbol)
        price = df["close"].astype(float).iloc[-1] if df is not None else 0.0

    if df is None or df.empty or price == 0.0:
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
    st.info("💬 Enter any asset symbol or name to get instant real-time AI analysis.")
