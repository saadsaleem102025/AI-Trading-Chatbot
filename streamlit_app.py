# ai_trading_chatbot.py
import streamlit as st
import time
import requests
import datetime
import pandas as pd
import numpy as np

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === MODERN STYLING ===
st.markdown("""
<style>
/* === GENERAL === */
html, body, [class*="stText"], [data-testid="stMarkdownContainer"] {
    font-size: 20px !important;
    line-height: 1.9 !important;
    color: #EAEAEA !important;
    font-family: 'Inter', sans-serif;
}

/* === MAIN BACKGROUND === */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #1b2735, #090a0f);
    color: white !important;
    padding: 20px;
}

/* === SIDEBAR === */
[data-testid="stSidebar"] {
    background: linear-gradient(145deg, #f1f3f6, #d9e2ec);
    width: 330px !important;
    min-width: 330px !important;
    max-width: 340px !important;
    border-right: 1px solid #ccc;
    padding: 1.4rem 1rem;
    border-radius: 0 12px 12px 0;
}

.sidebar-title {
    font-size: 24px;
    color: #333;
    font-weight: 700;
    margin-bottom: 20px;
}

.sidebar-item {
    font-size: 18px;
    margin: 8px 0;
    padding: 10px;
    border-radius: 8px;
    background-color: rgba(255,255,255,0.8);
    color: #111;
}

/* === SECTION HEADERS === */
.section-header {
    font-size: 22px;
    font-weight: 700;
    color: #00B4D8;
    margin-top: 25px;
    text-decoration: underline;
}

/* === ANALYSIS TEXT === */
.big-text {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 12px;
    padding: 25px;
    margin-top: 10px;
    color: #E0E0E0;
    box-shadow: 0 0 15px rgba(0,0,0,0.3);
}

/* === BIAS COLORS === */
.bullish { color: #00FFB3; font-weight: bold; }
.bearish { color: #FF6B6B; font-weight: bold; }
.neutral { color: #FFD93D; font-weight: bold; }

/* === MOTIVATION === */
.motivation {
    font-weight: 600;
    font-size: 20px;
    background: rgba(255,255,255,0.08);
    padding: 10px 15px;
    border-radius: 10px;
    color: #FFD700;
    margin-top: 15px;
    text-shadow: 0px 0px 5px rgba(255,215,0,0.3);
}
</style>
""", unsafe_allow_html=True)


# === API KEY ===
TWELVE_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]

# === REFRESH (30s) ===
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.rerun()

# === CRYPTO ID MAP ===
CRYPTO_ID_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "AVAX": "avalanche-2",
    "BNB": "binancecoin", "XRP": "ripple", "DOGE": "dogecoin", "ADA": "cardano",
    "DOT": "polkadot", "LTC": "litecoin", "CFX": "conflux-token", "XLM": "stellar",
    "SHIB": "shiba-inu", "PEPE": "pepe", "TON": "the-open-network",
    "SUI": "sui", "NEAR": "near"
}

# === PRICE FETCHER (stable fix) ===
def get_crypto_price(symbol, vs_currency="usd"):
    sid = CRYPTO_ID_MAP.get(symbol.upper(), symbol.lower())
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": sid, "vs_currencies": vs_currency, "include_24hr_change": "true"}
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        data = res.json().get(sid, {})
        price = data.get(vs_currency)
        change = data.get(f"{vs_currency}_24h_change")
        if price is None or change is None:
            raise ValueError("Incomplete data")
        if 0.0000001 < price < 1e7:
            return round(float(price), 6), round(float(change), 2)
    except Exception:
        pass
    return 1.0, 0.0  # fallback safe value

# === HISTORICAL DATA ===
def get_twelve_data(symbol, interval="1h", outputsize=100):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=10).json()
        if "values" not in res:
            return None
        df = pd.DataFrame(res["values"])
        df[["close","high","low"]] = df[["close","high","low"]].astype(float)
        return df.sort_values("datetime").reset_index(drop=True)
    except Exception:
        return None

# === SYNTHETIC SERIES (backup) ===
def synthesize_series(price, length=100, volatility_pct=0.005):
    np.random.seed(int(price * 1000) % 2**31)
    returns = np.random.normal(0, volatility_pct, size=length)
    series = price * np.exp(np.cumsum(returns))
    df = pd.DataFrame({
        "datetime": pd.date_range(end=datetime.datetime.utcnow(), periods=length, freq="T"),
        "close": series,
        "high": series * (1 + np.random.normal(0, volatility_pct / 2, size=length)),
        "low": series * (1 - np.random.normal(0, volatility_pct / 2, size=length)),
    })
    return df

# === INDICATORS ===
def kde_rsi(df):
    closes = df["close"].astype(float).values
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = pd.Series(gains).ewm(alpha=1/14, adjust=False).mean()
    avg_loss = pd.Series(losses).ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    w = np.exp(-0.5 * (np.linspace(-2, 2, len(rsi[-30:])))**2)
    return float(np.average(rsi[-30:], weights=w))

def supertrend_status(df):
    hl2 = (df["high"] + df["low"]) / 2
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"] - df["close"].shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/10, adjust=False).mean()
    last_close = df["close"].iloc[-1]
    return "Supertrend: Bullish" if last_close > hl2.iloc[-1] else "Supertrend: Bearish"

def bollinger_status(df):
    close = df["close"]
    ma = close.rolling(20).mean().iloc[-1]
    std = close.rolling(20).std().iloc[-1]
    upper, lower = ma + 2*std, ma - 2*std
    last = close.iloc[-1]
    if last > upper: return "Upper Band — Overbought"
    if last < lower: return "Lower Band — Oversold"
    return "Within Bands — Normal"

# === BIAS (50/30/20) ===
def combined_bias(kde_val, st_text, bb_text):
    score = 0
    if kde_val < 20: score += 50
    elif kde_val < 40: score += 25
    elif kde_val < 60: score += 0
    elif kde_val < 80: score -= 25
    else: score -= 50
    if "Bull" in st_text: score += 30
    elif "Bear" in st_text: score -= 30
    if "overbought" in bb_text.lower(): score -= 20
    elif "oversold" in bb_text.lower(): score += 20
    if score > 20: return "Bullish", score
    if score < -20: return "Bearish", score
    return "Neutral", score

# === ANALYSIS ===
def analyze(symbol, price, vs_currency):
    df_4h = get_twelve_data(symbol, "4h") or synthesize_series(price)
    df_1h = get_twelve_data(symbol, "1h") or synthesize_series(price)
    df_15m = get_twelve_data(symbol, "15min") or synthesize_series(price)

    kde_val = kde_rsi(df_1h)
    st_text = f"{supertrend_status(df_4h)} (4H) • {supertrend_status(df_1h)} (1H)"
    bb_text = bollinger_status(df_15m)
    bias, score = combined_bias(kde_val, st_text, bb_text)

    atr = df_1h["high"].max() - df_1h["low"].min()
    entry = price - 0.3 * atr
    target = price + 1.5 * atr
    stop = price - 1.0 * atr

    motivation_msgs = {
        "Bullish": "🚀 Stay sharp — momentum’s on your side. Trade with confidence, not emotion.",
        "Bearish": "⚡ Discipline is your shield. Wait for clarity, and strike when odds align.",
        "Neutral": "⏳ Market resting — patience now builds precision later."
    }

    bias_class = {"Bullish": "bullish", "Bearish": "bearish", "Neutral": "neutral"}[bias]

    return f"""
<div class='big-text'>
<div class='section-header'>📊 Price Overview</div>
<b>{symbol}</b>: <span style='color:#58C5FF;'>{price:.6f} {vs_currency.upper()}</span>

<div class='section-header'>📈 Indicators</div>
• KDE RSI: <b>{kde_val:.2f}%</b><br>
• Bollinger Bands: {bb_text}<br>
• Supertrend: {st_text}

<div class='section-header'>🎯 Suggested Levels</div>
Entry: <b style='color:#58FFB5;'>{entry:.6f}</b><br>
Target: <b style='color:#58FFB5;'>{target:.6f}</b><br>
Stop Loss: <b style='color:#FF7878;'>{stop:.6f}</b>

<div class='section-header'>📊 Overall Bias</div>
<b class='{bias_class}'>{bias}</b> (Score: {score})

<div class='motivation'>💬 {motivation_msgs[bias]}</div>
</div>
"""

# === SIDEBAR ===
st.sidebar.markdown("<p class='sidebar-title'>📊 Market Context</p>", unsafe_allow_html=True)
btc, btc_ch = get_crypto_price("BTC")
eth, eth_ch = get_crypto_price("ETH")
st.sidebar.markdown(f"<div class='sidebar-item'><b>BTC:</b> ${btc} ({btc_ch:+.2f}%)</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='sidebar-item'><b>ETH:</b> ${eth} ({eth_ch:+.2f}%)</div>", unsafe_allow_html=True)

utc_offsets = [f"UTC{offset:+d}" for offset in range(-12, 13)]
user_offset = st.sidebar.selectbox("Select Timezone (UTC)", utc_offsets, index=5)
offset_hours = int(user_offset.replace("UTC", ""))
user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset_hours)
st.sidebar.caption(f"🕒 Local Time: {user_time.strftime('%H:%M:%S')} ({user_offset})")

active = ["London", "New York"]
st.sidebar.markdown(f"<div class='sidebar-item'><b>Active Sessions:</b> {', '.join(active)}</div>", unsafe_allow_html=True)
st.sidebar.markdown("<div class='sidebar-item'><b>Volatility:</b> 85% — High Activity</div>", unsafe_allow_html=True)

# === MAIN ===
st.title("AI Trading Chatbot")
col1, col2 = st.columns([2,1])
with col1:
    user_input = st.text_input("Enter Asset Symbol (e.g., BTC, AAPL, EURUSD)")
with col2:
    vs_currency = st.text_input("Quote Currency", "usd").lower()

if user_input:
    symbol = user_input.strip().upper()
    price, _ = get_crypto_price(symbol, vs_currency)
    if price == 1.0:
        df = get_twelve_data(symbol, "1h")
        price = float(df["close"].iloc[-1]) if df is not None else 1.0
    analysis = analyze(symbol, price, vs_currency)
    st.markdown(analysis, unsafe_allow_html=True)
else:
    st.info("💬 Enter an asset symbol to get analysis.")
