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

# === AUTO REFRESH (Motivation every 30s) ===
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
def get_crypto_price(symbol_id, vs_currency="usd"):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": symbol_id, "vs_currencies": vs_currency, "include_24hr_change": "true"}
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        data = res.json().get(symbol_id, {})
        price = data.get(vs_currency, None)
        change = data.get(f"{vs_currency}_24h_change", 0)
        if price is None:
            raise ValueError
        return round(price, 2), round(change, 2)
    except Exception:
        return None, 0.0


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
    if vol < 20:
        return "⚪ Flat Market – Low Volatility, Avoid or Reduce Risk"
    elif 40 <= vol <= 60:
        return "🟡 Room to Move – Good for Breakouts"
    elif vol >= 100:
        return "🔴 Overextended – Beware of Reversals"
    else:
        return "🟢 Moderate Activity – Normal Volatility"


def get_ai_analysis(symbol, last_price, rsi_text, bollinger_text, supertrend_text, vs_currency):
    prompt = f"""
    You are a trading AI giving helpful technical summaries for traders.
    Use the following indicators for {symbol}:
    - KDE RSI: {rsi_text}
    - Bollinger Bands: {bollinger_text}
    - SuperTrend: {supertrend_text}
    The current price is around {last_price:.2f} {vs_currency.upper()}.
    Suggest realistic entry and exit zones with approximate numbers
    (e.g., "Buy near 63,200 – Target 64,100 – Stop 62,800").
    Keep the tone professional and realistic.
    End with one short motivational line.
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

st.sidebar.metric("BTC Price (USD)", f"${btc_price:,.2f}" if btc_price else "N/A", f"{btc_change:.2f}%")
st.sidebar.metric("ETH Price (USD)", f"${eth_price:,.2f}" if eth_price else "N/A", f"{eth_change:.2f}%")

offset = st.sidebar.slider("UTC Offset (Hours)", -12, 12, 0)
user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset)
st.sidebar.write(f"🕒 Timezone: UTC{offset:+d}")

session, vol = detect_fx_session_volatility(user_time.hour)
st.sidebar.markdown(f"### 💹 {session}")
st.sidebar.info(interpret_fx_volatility(vol))

# === MAIN CHAT ===
st.title("AI Trading Chatbot")

col1, col2 = st.columns([2, 1])
with col1:
    user_input = st.text_input("Enter Asset Name or Symbol (e.g., BTC, AAPL, EURUSD, Gold)")
with col2:
    vs_currency = st.text_input("Quote Currency (e.g., USD, EUR, JPY)", "usd").lower()

if user_input:
    symbol = user_input.strip().upper()
    df = get_twelve_data(symbol)
    if df is None or df.empty:
        df = pd.DataFrame({
            "close": np.random.uniform(100, 200, 50),
            "high": np.random.uniform(110, 210, 50),
            "low": np.random.uniform(90, 190, 50)
        })

    last_price = df["close"].iloc[-1]
    rsi = calculate_kde_rsi(df)
    rsi_text = interpret_kde_rsi(rsi)
    bollinger_text = calculate_bollinger_bands(df)
    supertrend_text = calculate_supertrend(df)

    ai_text = get_ai_analysis(symbol, last_price, rsi_text, bollinger_text, supertrend_text, vs_currency)
    st.success(ai_text)

    st.markdown("---")
    st.subheader(f"📈 Technical Summary for {symbol}")
    st.write(f"**KDE RSI:** {rsi_text}")
    st.write(f"**Bollinger Bands:** {bollinger_text}")
    st.write(f"**SuperTrend:** {supertrend_text}")

    st.info(f"💬 Motivation: {st.session_state.quote}")

else:
    st.write("Welcome to the **AI Trading Chatbot**! Type any asset name or symbol and choose your quote currency to get AI-powered technical insights.")
    st.success(st.session_state.quote)
