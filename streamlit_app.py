import streamlit as st
import time
import requests
import datetime
import pandas as pd
import numpy as np
import openai
import random
import pytz

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

openai.api_key = st.secrets["OPENAI_API_KEY"]
TWELVE_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]

# === MOTIVATION AUTO REFRESH (every 30s) ===
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.session_state.quote = random.choice([
        "Discipline beats impulse — trade the plan, not emotions.",
        "Patience is also a position.",
        "Focus on setups, not outcomes.",
        "Stay consistent — every small win builds your edge.",
        "Calm minds trade best."
    ])
else:
    if "quote" not in st.session_state:
        st.session_state.quote = "Stay patient — great setups always return."

# === HELPERS ===

def detect_symbol_type(symbol: str):
    """Determine if the asset is crypto or not."""
    crypto_keywords = ["BTC", "ETH", "SOL", "AVAX", "BNB", "XRP", "DOGE", "ADA", "DOT", "LTC"]
    return "crypto" if symbol.upper() in crypto_keywords else "noncrypto"


def get_crypto_price(symbol_id, vs_currency="usd"):
    """Fetch crypto price from CoinGecko."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": symbol_id.lower(), "vs_currencies": vs_currency, "include_24hr_change": "true"}
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        data = res.json().get(symbol_id.lower(), {})
        price = data.get(vs_currency)
        change = data.get(f"{vs_currency}_24h_change", 0)
        return round(price, 3), round(change, 2)
    except Exception:
        return None, 0.0


def get_twelve_data(symbol):
    """Fetch data for forex/stocks."""
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
        return "🔴 Oversold – Possible Bullish Reversal"
    elif rsi < 40:
        return "🟠 Weak Bearish – Potential Turn"
    elif rsi < 60:
        return "🟡 Neutral – Consolidation or Continuation"
    elif rsi < 80:
        return "🟢 Bullish – Momentum Up"
    else:
        return "🔵 Overbought – Caution on Longs"


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
        return "⚪ Low Volatility – Sideways Movement"
    elif vol < 80:
        return "🟢 Moderate Volatility – Steady Market"
    elif vol < 120:
        return "🟡 Active – Good Trading Conditions"
    else:
        return "🔴 High Volatility – Expect Sharp Moves"


def get_ai_analysis(symbol, price, rsi_text, boll_text, trend_text, vs_currency):
    prompt = f"""
    Provide a short technical summary for {symbol} ({vs_currency.upper()}).
    Indicators:
    - RSI: {rsi_text}
    - Bollinger Bands: {boll_text}
    - Supertrend: {trend_text}
    Current Price: {price:.2f} {vs_currency.upper()}
    Suggest realistic entry and exit zones based on this actual price.
    Example format: "Buy near 18.50 – Target 19.20 – Stop 18.10"
    End with one motivational line for traders.
    """
    try:
        res = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content.strip()
    except Exception:
        return f"{symbol} analysis unavailable. Stay patient and trade your plan."


# === SIDEBAR ===
st.sidebar.title("📊 Market Context Panel")

btc_price, btc_change = get_crypto_price("bitcoin")
eth_price, eth_change = get_crypto_price("ethereum")

st.sidebar.metric("BTC (USD)", f"${btc_price:,.2f}" if btc_price else "N/A", f"{btc_change:.2f}%")
st.sidebar.metric("ETH (USD)", f"${eth_price:,.2f}" if eth_price else "N/A", f"{eth_change:.2f}%")

# Safe timezone selector
tz_list = pytz.all_timezones
default_index = 0
try:
    default_index = tz_list.index("Asia/Karachi")
except ValueError:
    default_index = 0

user_tz = st.sidebar.selectbox("Select Your Timezone", ["UTC"] + tz_list, index=default_index + 1)
now_local = datetime.datetime.now(pytz.timezone(user_tz if user_tz != "UTC" else "UTC"))
st.sidebar.write(f"🕒 Local Time: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")

# Detect FX session based on current UTC hour
session, vol = fx_session_volatility(datetime.datetime.utcnow().hour)
st.sidebar.markdown(f"### 💹 {session}")
st.sidebar.info(interpret_vol(vol))

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

    if sym_type == "crypto":
        price, _ = get_crypto_price(symbol.lower(), vs_currency)
        df = get_twelve_data(f"{symbol}/{vs_currency.upper()}")  # Optional
    else:
        df = get_twelve_data(symbol)
        price = df["close"].astype(float).iloc[-1] if df is not None else None

    if price is None:
        st.error(f"Data for {symbol} not available. Try another asset.")
    else:
        if df is None or df.empty:
            st.warning("Using simplified calculations — live chart unavailable.")
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

        st.info(f"💬 Motivation: {st.session_state.quote}")

else:
    st.write("Welcome to the **AI Trading Chatbot**! Enter any symbol or name and your quote currency.You can also adjust your timezone to check current sessions volatility")
    st.success(st.session_state.quote)
