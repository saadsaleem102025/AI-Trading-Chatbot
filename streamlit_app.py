import streamlit as st
import requests
import datetime
import pandas as pd
import numpy as np
import openai

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide")
openai.api_key = st.secrets["OPENAI_API_KEY"]
TWELVE_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]

# === HELPERS ===
def get_crypto_price(symbol):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd&include_24hr_change=true"
        res = requests.get(url).json()
        data = res[symbol]
        return data["usd"], data["usd_24h_change"]
    except Exception:
        return None, None


def get_twelve_data(symbol):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1h&outputsize=50&apikey={TWELVE_API_KEY}"
        res = requests.get(url).json()
        df = pd.DataFrame(res["values"])
        df["close"] = df["close"].astype(float)
        df = df.sort_values("datetime")
        return df
    except Exception:
        return None


def calculate_kde_rsi(df):
    prices = df["close"].values
    deltas = np.diff(prices)
    seed = deltas[:14]
    up = seed[seed >= 0].sum() / 14
    down = -seed[seed < 0].sum() / 14
    rs = up / down if down != 0 else 0
    rsi = 100 - 100 / (1 + rs)
    return np.clip(rsi, 0, 100)


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
    df["MA20"] = df["close"].rolling(window=20).mean()
    df["STD"] = df["close"].rolling(window=20).std()
    df["Upper"] = df["MA20"] + (df["STD"] * 2)
    df["Lower"] = df["MA20"] - (df["STD"] * 2)
    if df["close"].iloc[-1] > df["Upper"].iloc[-1]:
        return "Above Upper Band → Overbought / Possible Reversal"
    elif df["close"].iloc[-1] < df["Lower"].iloc[-1]:
        return "Below Lower Band → Oversold / Possible Bounce"
    else:
        return "Inside Bands → Normal or Consolidation Phase"


def calculate_supertrend(df, period=10, multiplier=3):
    hl2 = (df["high"].astype(float) + df["low"].astype(float)) / 2
    df["atr"] = df["high"].astype(float) - df["low"].astype(float)
    df["upperband"] = hl2 + (multiplier * df["atr"])
    df["lowerband"] = hl2 - (multiplier * df["atr"])
    close = df["close"].astype(float)
    supertrend = "Bullish" if close.iloc[-1] > df["lowerband"].iloc[-1] else "Bearish"
    return f"{supertrend} trend per SuperTrend Indicator"


def fx_volatility_indicator(current_pct):
    if current_pct < 20:
        return "⚪ Flat Market – Low Volatility, Avoid or Reduce Risk"
    elif 40 <= current_pct <= 60:
        return "🟡 Room to Move – Good for Breakouts"
    elif current_pct >= 100:
        return "🔴 Overextended – Beware of Reversals"
    else:
        return "🟢 Moderate Activity – Normal Volatility"


def get_ai_analysis(symbol, rsi_text, bollinger_text, supertrend_text):
    prompt = f"""
    You are a trading AI. Analyze {symbol} with following indicator interpretations:
    - KDE RSI: {rsi_text}
    - Bollinger Bands: {bollinger_text}
    - SuperTrend: {supertrend_text}
    Give a concise summary: overall sentiment (Bullish, Bearish, Neutral),
    possible entry & exit zone hints, and short motivational tip.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI Analysis unavailable: {e}"


def motivational_quote():
    quotes = [
        "Discipline beats impulse — trade the plan, not emotions.",
        "Patience is also a position.",
        "Focus on setups, not outcomes.",
        "Stay consistent — every small win builds your edge."
    ]
    return np.random.choice(quotes)


# === SIDEBAR ===
st.sidebar.title("📊 Market Context Panel")

btc_price, btc_change = get_crypto_price("bitcoin")
eth_price, eth_change = get_crypto_price("ethereum")

if btc_price:
    st.sidebar.metric("BTC Price (USD)", f"${btc_price:,.2f}", f"{btc_change:.2f}%")
if eth_price:
    st.sidebar.metric("ETH Price (USD)", f"${eth_price:,.2f}", f"{eth_change:.2f}%")

# Timezone selection
st.sidebar.markdown("### 🌍 Timezone (UTC-based)")
utc_offset = st.sidebar.selectbox("Select UTC Offset", [f"UTC{offset:+}" for offset in range(-12, 13)], index=5)
now_utc = datetime.datetime.utcnow()
st.sidebar.write(f"🕒 Current time: {(now_utc + datetime.timedelta(hours=int(utc_offset[3:]))).strftime('%Y-%m-%d %H:%M:%S')}")

# FX Session Volatility
st.sidebar.markdown("### 💹 FX Market Session Volatility")
vol_input = st.sidebar.slider("Current % Movement", 0, 150, 60)
st.sidebar.write(fx_volatility_indicator(vol_input))

# === MAIN CHAT AREA ===
st.title(" AI Trading Chatbot")
user_input = st.text_input("Enter Asset Name or Symbol:")

if user_input:
    st.write("---")
    symbol = user_input.upper()
    df = get_twelve_data(symbol)

    if df is not None:
        rsi = calculate_kde_rsi(df)
        rsi_text = interpret_kde_rsi(rsi)
        bollinger_text = calculate_bollinger_bands(df)
        supertrend_text = calculate_supertrend(df)

        st.subheader(f"Technical Summary for {symbol}")
        st.write(f"**KDE RSI:** {rsi_text}")
        st.write(f"**Bollinger Bands:** {bollinger_text}")
        st.write(f"**SuperTrend:** {supertrend_text}")

        ai_text = get_ai_analysis(symbol, rsi_text, bollinger_text, supertrend_text)
        st.success(ai_text)

        st.info(f"💬 Motivation: {motivational_quote()}")

    else:
        st.error("Data not found or unavailable for this symbol. Try another one.")
