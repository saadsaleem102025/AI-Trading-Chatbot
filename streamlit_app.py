import streamlit as st
import time
import requests
import datetime
import pandas as pd
import numpy as np
import random
from scipy.stats import gaussian_kde

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === STYLING ===
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background-color: #f5f7fa;
    padding: 1.5rem 1rem;
}
.sidebar-title {
    font-size: 28px !important;
    font-weight: 800;
    color: #1e293b;
    margin-bottom: 12px;
}
.sidebar-subtitle {
    font-size: 20px;
    font-weight: 600;
    color: #334155;
    margin-top: 18px;
    margin-bottom: 8px;
}
.sidebar-item {
    font-size: 17px;
    line-height: 1.5;
    color: #334155;
    margin-bottom: 8px;
    word-wrap: break-word;
}
.sidebar-highlight {
    font-weight: 700;
    color: #0f172a;
}
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

# === FETCH PRICE ===
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

# === FETCH DATA ===
def get_twelve_data(symbol, interval="1h"):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize=100&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=10).json()
        if "values" not in res:
            return None
        df = pd.DataFrame(res["values"])
        df[["close", "high", "low"]] = df[["close", "high", "low"]].astype(float)
        return df.sort_values("datetime")
    except:
        return None

# === INDICATORS ===
def kde_rsi(df):
    try:
        close = df["close"].astype(float).values
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.convolve(gains, np.ones(14)/14, mode='valid')
        avg_loss = np.convolve(losses, np.ones(14)/14, mode='valid')
        rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss!=0)
        rsi = 100 - (100 / (1 + rs))
        kde = gaussian_kde(rsi)
        density = kde.evaluate(rsi)
        smooth_rsi = np.average(rsi, weights=density)
        return np.clip(smooth_rsi, 0, 100)
    except:
        return random.uniform(40, 60)

def interpret_kde_rsi(rsi):
    if rsi < 10 or rsi > 90: zone = "🟣 Reversal Danger Zone — Extreme probability of reversal."
    elif rsi < 20: zone = "🔴 Extreme Oversold — Strong bullish reversal potential."
    elif rsi < 40: zone = "🟠 Weak Bearish — Bullish momentum may build soon."
    elif rsi < 60: zone = "🟡 Neutral Zone — Consolidation likely."
    elif rsi < 80: zone = "🟢 Strong Bullish — Uptrend continuation likely."
    else: zone = "🔵 Extreme Overbought — Bearish reversal risk high."
    return zone

def bollinger_signal(df):
    try:
        df["MA20"] = df["close"].rolling(20).mean()
        df["STD"] = df["close"].rolling(20).std()
        df["Upper"] = df["MA20"] + 2 * df["STD"]
        df["Lower"] = df["MA20"] - 2 * df["STD"]
        c = df["close"].iloc[-1]
        if c > df["Upper"].iloc[-1]: return "Price at upper band — overbought."
        if c < df["Lower"].iloc[-1]: return "Price at lower band — oversold."
        return "Price within Bollinger range."
    except:
        return "Neutral Bollinger signal."

def supertrend_signal(df):
    try:
        hl2 = (df["high"] + df["low"]) / 2
        tr = pd.concat([
            df["high"] - df["low"],
            abs(df["high"] - df["close"].shift(1)),
            abs(df["low"] - df["close"].shift(1))
        ], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/14, adjust=False).mean()
        upper_band = hl2 + (3 * atr)
        lower_band = hl2 - (3 * atr)
        close = df["close"].iloc[-1]
        if close > lower_band.iloc[-1]:
            return "Supertrend: Bullish bias."
        else:
            return "Supertrend: Bearish bias."
    except:
        return "Supertrend neutral."

# === ATR Accurate ===
def true_atr(df, period=14):
    df["H-L"] = df["high"] - df["low"]
    df["H-PC"] = abs(df["high"] - df["close"].shift(1))
    df["L-PC"] = abs(df["low"] - df["close"].shift(1))
    df["TR"] = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
    return df["TR"].ewm(alpha=1/period, adjust=False).mean().iloc[-1]

# === VOLATILITY ===
def fx_session_volatility(hour):
    if 22 <= hour or hour < 7: return "Sydney Session", 40
    if 7 <= hour < 16: return "London Session", 100
    if 12 <= hour < 21: return "New York Session", 120
    return "Tokyo Session", 60

def interpret_vol(vol):
    if vol < 40: return "⚪ Low Volatility – Range-bound"
    if vol < 80: return "🟢 Moderate Volatility – Smooth trends"
    if vol < 120: return "🟡 Active Market – Good movement"
    return "🔴 High Volatility – Reversal Risk"

# === AI ANALYSIS ===
def get_ai_analysis(symbol, price, df_4h, df_1h, df_15m, vs_currency):
    # Indicator signals
    kde_val = kde_rsi(df_1h)
    kde_text = interpret_kde_rsi(kde_val)
    bb_text = bollinger_signal(df_15m)
    st_text = supertrend_signal(df_4h)

    # Weighted Bias (50/30/20)
    bias_score = 0
    if "Bullish" in st_text: bias_score += 30
    if "Bearish" in st_text: bias_score -= 30
    if "Bullish" in kde_text or "Uptrend" in kde_text: bias_score += 50
    if "Bearish" in kde_text or "Overbought" in kde_text: bias_score -= 50
    if "overbought" in bb_text.lower(): bias_score -= 20
    if "oversold" in bb_text.lower(): bias_score += 20

    sentiment = "🟢 Bullish Bias" if bias_score > 20 else "🟡 Neutral" if abs(bias_score) <= 20 else "🔴 Bearish Bias"

    atr = true_atr(df_1h)
    entry = round(price - (0.5 * atr), 4)
    target = round(price + (1.2 * atr), 4)
    stop = round(price - (0.8 * atr), 4)

    motivation = random.choice([
        "Discipline turns volatility into profit.",
        "Small consistent wins beat impulsive trades.",
        "Your edge is patience and process.",
        "Focus on setups, not emotions.",
        "Trade the plan, not the noise."
    ])

    return f"""
📊 **AI Market Summary for {symbol} ({vs_currency.upper()})**

{st_text}
{kde_text}
{bb_text}

**Bias:** {sentiment}

🎯 **Suggested Trade Plan**
- Buy near: {entry} {vs_currency.upper()}
- Target: {target} {vs_currency.upper()}
- Stop Loss: {stop} {vs_currency.upper()}

💬 *{motivation}*
"""

# === SIDEBAR ===
st.sidebar.markdown("<p class='sidebar-title'>📊 Market Context Panel</p>", unsafe_allow_html=True)
btc_price, btc_change = get_crypto_price("BTC")
eth_price, eth_change = get_crypto_price("ETH")
st.sidebar.markdown(f"<p class='sidebar-item'><span class='sidebar-highlight'>BTC:</span> ${btc_price:,.2f} ({btc_change:+.2f}%)</p>", unsafe_allow_html=True)
st.sidebar.markdown(f"<p class='sidebar-item'><span class='sidebar-highlight'>ETH:</span> ${eth_price:,.2f} ({eth_change:+.2f}%)</p>", unsafe_allow_html=True)

st.sidebar.markdown("<p class='sidebar-subtitle'>🌍 Select Your Timezone (UTC)</p>", unsafe_allow_html=True)
utc_offsets = [f"UTC{offset:+d}" for offset in range(-12, 13)]
user_offset = st.sidebar.selectbox("Timezone", utc_offsets, index=5)
offset_hours = int(user_offset.replace("UTC", ""))
user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset_hours)
session, vol = fx_session_volatility(user_time.hour)
st.sidebar.markdown(f"<p class='sidebar-item'>🌐 Session: {session}</p>", unsafe_allow_html=True)
st.sidebar.markdown(f"<p class='sidebar-item'>{interpret_vol(vol)}</p>", unsafe_allow_html=True)
st.sidebar.caption(f"🕒 Local Time: {user_time.strftime('%H:%M:%S')} ({user_offset})")

# === MAIN ===
st.title("AI Trading Chatbot")

col1, col2 = st.columns([2, 1])
with col1:
    user_input = st.text_input("Enter Asset Symbol (e.g., BTC, AAPL, EURUSD)")
with col2:
    vs_currency = st.text_input("Quote Currency", "usd").lower()

if user_input:
    symbol = user_input.strip().upper()
    sym_type = detect_symbol_type(symbol)
    data_id = f"{symbol}/{vs_currency.upper()}" if sym_type == "crypto" else symbol

    df_4h = get_twelve_data(data_id, "4h")
    df_1h = get_twelve_data(data_id, "1h")
    df_15m = get_twelve_data(data_id, "15min")

    price, _ = get_crypto_price(symbol, vs_currency)
    if price == 0 and df_1h is not None:
        price = df_1h["close"].astype(float).iloc[-1]

    if df_1h is None:
        st.warning("⚠️ Data temporarily unavailable, retry shortly.")
    else:
        analysis = get_ai_analysis(symbol, price, df_4h or df_1h, df_1h, df_15m or df_1h, vs_currency)
        st.success(analysis)
else:
    st.info("💬 Enter an asset symbol to get full AI-powered multi-timeframe analysis.")
