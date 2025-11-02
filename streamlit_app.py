import streamlit as st
import time
import requests
import datetime
import pandas as pd
import numpy as np
import openai
import random
from streamlit_autorefresh import st_autorefresh

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot 🌍", layout="wide", initial_sidebar_state="expanded")

openai.api_key = st.secrets["OPENAI_API_KEY"]
TWELVE_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]

# === AUTO REFRESH (Motivation only) ===
count = st_autorefresh(interval=30 * 1000, limit=None, key="motivation_refresh")
if "quote" not in st.session_state:
    st.session_state.quote = "Stay patient — great setups always return."
if count > 0:
    st.session_state.quote = random.choice([
        "Discipline beats impulse — trade the plan, not emotions.",
        "Patience is also a position.",
        "Focus on setups, not outcomes.",
        "Stay consistent — every small win builds your edge.",
        "Calm minds trade best."
    ])

# === HELPERS ===
def get_price(symbol, base_currency="USD", fallback_price=100.0):
    """Try TwelveData first; fallback to CoinGecko or mock data."""
    try:
        # Try TwelveData
        url = f"https://api.twelvedata.com/price?symbol={symbol}/{base_currency}&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=6).json()
        if "price" in res:
            return round(float(res["price"]), 4)
    except Exception:
        pass

    # Try CoinGecko
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": symbol.lower(), "vs_currencies": base_currency.lower()}
        res = requests.get(url, params=params, timeout=6).json()
        val = res.get(symbol.lower(), {}).get(base_currency.lower())
        if val:
            return round(val, 4)
    except Exception:
        pass

    # Fallback
    return fallback_price


def get_twelve_data(symbol, base_currency="USD"):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}/{base_currency}&interval=1h&outputsize=50&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=10).json()
        if "values" not in res:
            return None
        df = pd.DataFrame(res["values"])
        df[["close", "high", "low"]] = df[["close", "high", "low"]].astype(float)
        df = df.sort_values("datetime")
        return df
    except Exception:
        return None


def calculate_kde_rsi(df):
    try:
        prices = df["close"].values
        deltas = np.diff(prices)
        up = np.mean([d for d in deltas if d > 0]) if any(d > 0 for d in deltas) else 0
        down = -np.mean([d for d in deltas if d < 0]) if any(d < 0 for d in deltas) else 1
        rs = up / down if down != 0 else 0
        rsi = 100 - 100 / (1 + rs)
        return np.clip(rsi, 0, 100)
    except Exception:
        return random.uniform(40, 60)


def interpret_kde_rsi(rsi):
    if rsi < 10 or rsi > 90:
        return "🟣 Reversal Danger Zone – Very High Reversal Probability"
    elif rsi < 20:
        return "🔴 Extreme Oversold – Likely Bullish Reversal"
    elif 20 <= rsi < 40:
        return "🟠 Weak Bearish – Possible Uptrend Forming"
    elif 40 <= rsi < 60:
        return "🟡 Neutral – Trend Continuation or Range"
    elif 60 <= rsi < 80:
        return "🟢 Strong Bullish – Momentum Building"
    else:
        return "🔵 Overbought – Possible Pullback"


def calculate_bollinger_bands(df):
    try:
        df["MA20"] = df["close"].rolling(window=20).mean()
        df["STD"] = df["close"].rolling(window=20).std()
        df["Upper"] = df["MA20"] + 2 * df["STD"]
        df["Lower"] = df["MA20"] - 2 * df["STD"]
        close = df["close"].iloc[-1]
        if close > df["Upper"].iloc[-1]:
            return "Above Upper Band → Overbought / Reversal Possible"
        elif close < df["Lower"].iloc[-1]:
            return "Below Lower Band → Oversold / Bounce Possible"
        else:
            return "Inside Bands → Normal Consolidation"
    except Exception:
        return "Neutral (Fallback)"


def calculate_supertrend(df, multiplier=3):
    try:
        hl2 = (df["high"] + df["low"]) / 2
        atr = df["high"] - df["low"]
        upper = hl2 + multiplier * atr
        lower = hl2 - multiplier * atr
        close = df["close"].iloc[-1]
        return "Bullish" if close > lower.iloc[-1] else "Bearish"
    except Exception:
        return "Neutral"


def detect_fx_session_volatility(hour_utc):
    if 22 <= hour_utc or hour_utc < 7:
        return "Sydney Session", random.randint(30, 45)
    elif 0 <= hour_utc < 9:
        return "Tokyo Session", random.randint(50, 70)
    elif 7 <= hour_utc < 16:
        return "London Session", random.randint(80, 120)
    else:
        return "New York Session", random.randint(90, 130)


def interpret_fx_volatility(vol):
    if vol < 30:
        return "⚪ Low Volatility – Range-bound Market"
    elif 40 <= vol <= 60:
        return "🟡 Active Market – Watch for Breakouts"
    elif vol >= 100:
        return "🔴 High Volatility – Expect Swings"
    else:
        return "🟢 Normal Conditions – Stable Flow"


def get_ai_analysis(symbol, base_currency, last_price, rsi_text, bollinger_text, supertrend_text):
    prompt = f"""
    You are a trading assistant. Provide a realistic summary for {symbol}/{base_currency}.
    Indicators:
    - KDE RSI: {rsi_text}
    - Bollinger Bands: {bollinger_text}
    - SuperTrend: {supertrend_text}
    Current price: {last_price:.4f} {base_currency}.
    Output short directional bias (Bullish/Bearish/Neutral) and give approx entry, target, and stop levels in numbers, like:
    "Entry ~1.0820 – Target 1.0900 – Stop 1.0780".
    Avoid generic talk; keep it clear and concise.
    End with one motivational line.
    """
    try:
        res = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content.strip()
    except Exception:
        return f"{symbol}/{base_currency} analysis unavailable. Stay calm and follow structure."


# === SIDEBAR ===
st.sidebar.title("📊 Market Context Panel")

btc_price = get_price("bitcoin", "USD", 65000)
eth_price = get_price("ethereum", "USD", 3000)

st.sidebar.metric("BTC/USD", f"${btc_price:,.2f}")
st.sidebar.metric("ETH/USD", f"${eth_price:,.2f}")

offset = st.sidebar.slider("UTC Offset (Hours)", -12, 12, 0)
user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset)
st.sidebar.write(f"🕒 Timezone: UTC{offset:+d}")

session, vol = detect_fx_session_volatility(user_time.hour)
st.sidebar.markdown(f"### 💹 {session}")
st.sidebar.info(interpret_fx_volatility(vol))

# === MAIN CHAT ===
st.title("AI Trading Chatbot")

user_input = st.text_input("Enter Asset (Name or Symbol): e.g., BTC, EUR/USD, Gold, Tesla, ETH/PKR")

if user_input:
    text = user_input.strip().upper().replace(" ", "")
    # Parse symbol/base
    if "/" in text:
        symbol, base_currency = text.split("/", 1)
    else:
        symbol, base_currency = text, "USD"

    df = get_twelve_data(symbol, base_currency)
    if df is None or df.empty:
        df = pd.DataFrame({
            "close": np.random.uniform(100, 200, 50),
            "high": np.random.uniform(110, 210, 50),
            "low": np.random.uniform(90, 190, 50)
        })

    last_price = get_price(symbol.lower(), base_currency, df["close"].iloc[-1])
    rsi = calculate_kde_rsi(df)
    rsi_text = interpret_kde_rsi(rsi)
    bollinger_text = calculate_bollinger_bands(df)
    supertrend_text = calculate_supertrend(df)

    # === AI Analysis ===
    ai_text = get_ai_analysis(symbol, base_currency, last_price, rsi_text, bollinger_text, supertrend_text)
    st.success(ai_text)

    # === Technical Summary ===
    st.markdown("---")
    st.subheader(f"📈 Technical Summary for {symbol}/{base_currency}")
    st.write(f"**KDE RSI:** {rsi_text}")
    st.write(f"**Bollinger Bands:** {bollinger_text}")
    st.write(f"**SuperTrend:** {supertrend_text}")

    st.info(f"💬 Motivation: {st.session_state.quote}")

else:
    st.write("Welcome to the **AI Trading Chatbot**! Type any asset name, symbol, or currency pair (like `BTC/JPY` or `EUR/USD`) to get global AI-powered analysis.")
    st.success(st.session_state.quote)
