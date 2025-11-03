# ai_trading_chatbot.py
import streamlit as st
import time
import requests
import datetime
import pandas as pd
import numpy as np

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === CUSTOM STYLING ===
st.markdown("""
<style>
/* Sidebar Styling */
[data-testid="stSidebar"] {
    background-color: #f5f7fa;
    width: 330px !important;
    min-width: 330px !important;
    max-width: 340px !important;
    padding: 1.2rem 0.8rem;
}

/* Main content font size */
html, body, [class*="stText"], [data-testid="stMarkdownContainer"] {
    font-size: 22px !important;      /* 🔸 increase/decrease this value */
    line-height: 1.9!important;     /* 🔸 better readability */
}

/* AI response box styling */
.ai-response {
    font-size: 18px !important;
    line-height: 1.8;
    color: #E0E0E0;
    white-space: pre-line;
    margin-top: 15px;
}

/* Motivation text styling */
.motivation {
    font-weight: 600;
    color: #FFD700;
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)


# === API KEY ===
TWELVE_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]

# === AUTO REFRESH (30s) ===
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

# === PRICE FETCHER ===
def get_crypto_price(symbol, vs_currency="usd"):
    sid = CRYPTO_ID_MAP.get(symbol.upper(), symbol.lower())
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": sid, "vs_currencies": vs_currency, "include_24hr_change": "true"}
        res = requests.get(url, params=params, timeout=8)
        data = res.json().get(sid, {})
        price = float(data.get(vs_currency, 0) or 0)
        change = float(data.get(f"{vs_currency}_24h_change", 0) or 0)
        if 0.0000001 < price < 1e7:
            return round(price, 8), round(change, 2)
    except Exception:
        pass
    return 0.0, 0.0

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

# === SYNTHETIC SERIES (backup if API fails) ===
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

# === COMBINED BIAS (50/30/20 weighting) ===
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

# === VOLATILITY ===
def fx_sessions(utc_time):
    sessions = {"Sydney": (22, 7), "Tokyo": (0, 9), "London": (8, 17), "New York": (13, 22)}
    active_sessions = []
    for name, (start, end) in sessions.items():
        if start <= utc_time.hour < end or (start > end and (utc_time.hour >= start or utc_time.hour < end)):
            active_sessions.append(name)
    return active_sessions

def session_volatility(active_sessions):
    base = {"Sydney": 40, "Tokyo": 70, "London": 100, "New York": 120}
    if not active_sessions: return "20% — Flat (Low Activity)"
    vol = np.mean([base[s] for s in active_sessions])
    if vol < 60: desc = "Flat or Calm — Low Risk"
    elif vol < 100: desc = "Room to Move — Breakout Possible"
    elif vol < 120: desc = "High Activity — Watch Momentum"
    else: desc = "Extreme Move — Beware of Reversals"
    return f"{vol:.0f}% — {desc}"

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
        "Bullish": "🚀 The trend is your ally — trust your setup, but never chase. Stay calm and follow the plan.",
        "Bearish": "⚡ Patience pays — markets reward discipline. Protect capital and wait for the rebound.",
        "Neutral": "⏳ Every pause builds energy for the next move. Observe, learn, and strike only when clear."
    }

    return f"""
<div class='big-text'>
<div class='section-header'>📊 Price Overview</div>
<b>{symbol}</b>: {price:.6f} {vs_currency.upper()}

<div class='section-header'>📈 Indicators</div>
• KDE RSI: {kde_val:.2f}%  
• Bollinger Bands: {bb_text}  
• Supertrend: {st_text}

<div class='section-header'>🎯 Suggested Levels</div>
Entry: {entry:.6f}  
Target: {target:.6f}  
Stop Loss: {stop:.6f}

<div class='section-header'>📊 Overall Bias</div>
<b>{bias}</b> (Score: {score})

<div class='motivation'>💬 {motivation_msgs[bias]}</div>
</div>
"""

# === SIDEBAR ===
st.sidebar.markdown("<p class='sidebar-title'>📊 Market Context</p>", unsafe_allow_html=True)
btc, btc_ch = get_crypto_price("BTC")
eth, eth_ch = get_crypto_price("ETH")
st.sidebar.markdown(f"<p class='sidebar-item'><b>BTC:</b> ${btc} ({btc_ch:+.2f}%)</p>", unsafe_allow_html=True)
st.sidebar.markdown(f"<p class='sidebar-item'><b>ETH:</b> ${eth} ({eth_ch:+.2f}%)</p>", unsafe_allow_html=True)

utc_offsets = [f"UTC{offset:+d}" for offset in range(-12, 13)]
user_offset = st.sidebar.selectbox("Select Timezone (UTC)", utc_offsets, index=5)
offset_hours = int(user_offset.replace("UTC", ""))
user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset_hours)
st.sidebar.caption(f"🕒 Local Time: {user_time.strftime('%H:%M:%S')} ({user_offset})")

active = fx_sessions(datetime.datetime.utcnow())
volatility_info = session_volatility(active)
st.sidebar.markdown(f"<p class='sidebar-item'><b>Active Sessions:</b> {', '.join(active) if active else 'None'}</p>", unsafe_allow_html=True)
st.sidebar.markdown(f"<p class='sidebar-item'><b>Volatility:</b> {volatility_info}</p>", unsafe_allow_html=True)

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
    if price == 0.0:
        df = get_twelve_data(symbol, "1h")
        price = float(df["close"].iloc[-1]) if df is not None else 1.0
    analysis = analyze(symbol, price, vs_currency)
    st.markdown(analysis, unsafe_allow_html=True)
else:
    st.info("💬 Enter an asset symbol to get analysis.")
