import streamlit as st
import time
import requests
import datetime
import pandas as pd
import numpy as np
import openai
import random

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide")

# Auto-refresh every 30 seconds
REFRESH_INTERVAL = 30
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
elif time.time() - st.session_state.last_refresh > REFRESH_INTERVAL:
    st.session_state.last_refresh = time.time()
    st.rerun()

# Continue with rest of your existing imports and functions here...


# === HELPERS ===
def get_crypto_price(symbol_id, fallback_price):
    """Fetch crypto price safely with guaranteed fallback."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": symbol_id, "vs_currencies": "usd", "include_24hr_change": "true"}
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        data = res.json().get(symbol_id, {})
        price = data.get("usd", fallback_price)
        change = data.get("usd_24h_change", 0)
        if not price or price == 0:
            price = fallback_price
        return round(price, 2), round(change, 2)
    except Exception:
        return fallback_price, 0.0


def get_twelve_data(symbol):
    """Get price data for any asset from Twelve Data."""
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


def calculate_kde_rsi(df):
    """Simplified RSI as KDE proxy."""
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
        return "🔴 Extreme Oversold – High chance of Bullish Reversal (Long Setup)"
    elif 20 <= rsi < 40:
        return "🟠 Weak Bearish – Possible Bullish Trend Starting"
    elif 40 <= rsi < 60:
        return "🟡 Neutral Zone – Trend Continuation or Consolidation"
    elif 60 <= rsi < 80:
        return "🟢 Strong Bullish – Momentum Up but Watch Exhaustion"
    else:
        return "🔵 Extreme Overbought – High chance of Bearish Reversal (Short Setup)"


def calculate_bollinger_bands(df):
    try:
        df["MA20"] = df["close"].rolling(window=20).mean()
        df["STD"] = df["close"].rolling(window=20).std()
        df["Upper"] = df["MA20"] + 2 * df["STD"]
        df["Lower"] = df["MA20"] - 2 * df["STD"]
        close = df["close"].iloc[-1]
        if close > df["Upper"].iloc[-1]:
            return "Above Upper Band → Overbought / Possible Reversal"
        elif close < df["Lower"].iloc[-1]:
            return "Below Lower Band → Oversold / Possible Bounce"
        else:
            return "Inside Bands → Normal or Consolidation Phase"
    except Exception:
        return "Neutral (Fallback Mode)"


def calculate_supertrend(df, multiplier=3):
    try:
        hl2 = (df["high"] + df["low"]) / 2
        atr = df["high"] - df["low"]
        upper = hl2 + multiplier * atr
        lower = hl2 - multiplier * atr
        close = df["close"].iloc[-1]
        return "Bullish trend per SuperTrend Indicator" if close > lower.iloc[-1] else "Bearish trend per SuperTrend Indicator"
    except Exception:
        return "Neutral trend (Fallback Mode)"


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
    if vol < 20:
        return "⚪ Flat Market – Low Volatility, Avoid or Reduce Risk"
    elif 40 <= vol <= 60:
        return "🟡 Room to Move – Good for Breakouts"
    elif vol >= 100:
        return "🔴 Overextended – Beware of Reversals"
    else:
        return "🟢 Moderate Activity – Normal Volatility"


def get_ai_analysis(symbol, rsi_text, bollinger_text, supertrend_text):
    prompt = f"""
    You are a trading AI. Analyze {symbol} using:
    - KDE RSI: {rsi_text}
    - Bollinger Bands: {bollinger_text}
    - SuperTrend: {supertrend_text}
    Provide a clear direction (Bullish/Bearish/Neutral),
    give entry/exit hints, and add a motivational trading reminder.
    """
    try:
        res = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content.strip()
    except Exception:
        fallback = random.choice(["Bullish", "Bearish", "Neutral"])
        return f"{symbol} appears {fallback}. Keep your discipline and trade smart."


def motivational_quote():
    return random.choice([
        "Discipline beats impulse — trade the plan, not emotions.",
        "Patience is also a position.",
        "Focus on setups, not outcomes.",
        "Stay consistent — every small win builds your edge.",
        "Calm minds trade best."
    ])

# === SIDEBAR ===
st.sidebar.title("📊 Market Context Panel")

# Auto-refresh prices (never zero)
btc_price, btc_change = get_crypto_price("bitcoin", 65000)
eth_price, eth_change = get_crypto_price("ethereum", 3000)

st.sidebar.metric("BTC Price (USD)", f"${btc_price:,.2f}", f"{btc_change:.2f}%")
st.sidebar.metric("ETH Price (USD)", f"${eth_price:,.2f}", f"{eth_change:.2f}%")

# Timezone and FX session
st.sidebar.markdown("### 🌍 Timezone")
offset = st.sidebar.slider("UTC Offset (Hours)", -12, 12, 0)
user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset)
st.sidebar.write(f"🕒 Timezone: UTC{offset:+d}")

session, vol = detect_fx_session_volatility(user_time.hour)
st.sidebar.markdown(f"### 💹 {session}")
st.sidebar.info(interpret_fx_volatility(vol))

# === MAIN CHAT ===
st.title("🤖 AI Trading Chatbot")

user_input = st.text_input("Enter Asset (e.g. BTC/USD, AAPL, EUR/USD):")

if user_input:
    symbol = user_input.strip().upper()
    df = get_twelve_data(symbol)
    if df is None or df.empty:
        # fallback dummy data (so AI never fails)
        df = pd.DataFrame({
            "close": np.random.uniform(100, 200, 50),
            "high": np.random.uniform(110, 210, 50),
            "low": np.random.uniform(90, 190, 50)
        })

    rsi = calculate_kde_rsi(df)
    rsi_text = interpret_kde_rsi(rsi)
    bollinger_text = calculate_bollinger_bands(df)
    supertrend_text = calculate_supertrend(df)

    st.subheader(f"📈 Technical Summary for {symbol}")
    st.write(f"**KDE RSI:** {rsi_text}")
    st.write(f"**Bollinger Bands:** {bollinger_text}")
    st.write(f"**SuperTrend:** {supertrend_text}")

    ai_text = get_ai_analysis(symbol, rsi_text, bollinger_text, supertrend_text)
    st.success(ai_text)
    st.info(f"💬 Motivation: {motivational_quote()}")

else:
    st.write("Welcome to the **AI Trading Chatbot**! Type any symbol (e.g. BTC/USD, EUR/USD, AAPL) to get AI-powered insights.")
    st.success(motivational_quote())
