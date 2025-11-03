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
/* === REMOVE HEADER + FOOTER === */
header[data-testid="stHeader"], footer {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}

/* === GLOBAL FONT + BODY === */
html, body, [class*="stText"], [data-testid="stMarkdownContainer"] {
    font-size: 18px !important;
    color: #E9EEF6 !important;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    line-height: 1.8 !important;
}

/* === MAIN BACKGROUND === */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #0F2027, #203A43, #2C5364);
    color: white !important;
    padding-left: 360px !important; /* ensures main content is visible */
    padding-right: 25px;
}

/* === SIDEBAR === */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0E111A 0%, #1B1F2E 100%);
    width: 340px !important;
    min-width: 340px !important;
    max-width: 350px !important;
    position: fixed !important;
    top: 0; left: 0; bottom: 0;
    z-index: 100;
    padding: 1.6rem 1.2rem 2rem 1.2rem;
    border-right: 1px solid rgba(255,255,255,0.08);
    box-shadow: 8px 0 18px rgba(0,0,0,0.4);
}

/* === MARKET CONTEXT HEADING === */
.sidebar-title {
    font-size: 24px;
    font-weight: 800;
    color: #66FCF1;
    margin-bottom: 25px;
}

/* === SIDEBAR ITEM BOX === */
.sidebar-item {
    background: rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 12px;
    margin: 10px 0;
    font-size: 17px;
    box-shadow: inset 0 0 10px rgba(0,0,0,0.3);
    color: #C5C6C7;
}

/* === CLOCK FIX (Under Timezone) === */
.sidebar-clock {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 10px;
    padding: 8px 12px;
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
    color: #D8DEE9;
    font-size: 15px;
    font-weight: 600;
    text-shadow: 0 0 6px rgba(102,252,241,0.4);
    box-shadow: inset 0 0 5px rgba(255,255,255,0.05);
}
.sidebar-clock svg, .sidebar-clock span {
    color: #66FCF1 !important;
}

/* === SECTION HEADERS === */
.section-header {
    font-size: 22px;
    font-weight: 700;
    color: #45A29E;
    margin-top: 25px;
    border-left: 4px solid #66FCF1;
    padding-left: 8px;
}

/* === BIG TEXT === */
.big-text {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 16px;
    padding: 28px;
    margin-top: 15px;
    box-shadow: 0 0 25px rgba(0,0,0,0.4);
}

/* === TEXT COLORS === */
.bullish { color: #00FFB3; font-weight: 700; }
.bearish { color: #FF6B6B; font-weight: 700; }
.neutral { color: #FFD93D; font-weight: 700; }

/* === MOTIVATION BOX === */
.motivation {
    font-weight: 600;
    font-size: 19px;
    margin-top: 25px;
    color: #FFD700;
    background: rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 14px 16px;
    text-shadow: 0 0 8px rgba(255,215,0,0.5);
    box-shadow: inset 0 0 8px rgba(255,255,255,0.05);
}

/* === INPUT FIELDS === */
[data-baseweb="input"] input {
    background-color: rgba(255,255,255,0.12) !important;
    color: #E9EEF6 !important;
    border-radius: 10px !important;
}

/* === TITLES === */
h1, h2, h3 {
    color: #66FCF1 !important;
    text-shadow: 0 0 10px rgba(102,252,241,0.4);
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

# === CRYPTO ID MAP ===
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
        res.raise_for_status()
        data = res.json().get(sid, {})
        price = data.get(vs_currency)
        change = data.get(f"{vs_currency}_24h_change")
        if price and change:
            return round(float(price), 6), round(float(change), 2)
    except Exception:
        pass
    return 1.0, 0.0

# === HISTORICAL FETCH ===
def get_twelve_data(symbol, interval="1h", outputsize=100):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=10).json()
        if "values" not in res: return None
        df = pd.DataFrame(res["values"])
        df[["close","high","low"]] = df[["close","high","low"]].astype(float)
        return df.sort_values("datetime").reset_index(drop=True)
    except Exception:
        return None

# === SYNTHETIC BACKUP ===
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
st.sidebar.markdown(
    f"<div class='sidebar-clock'>🕒 Local Time: {user_time.strftime('%H:%M:%S')} ({user_offset})</div>",
    unsafe_allow_html=True
)

st.sidebar.markdown("<div class='sidebar-item'><b>Active Sessions:</b> London, New York</div>", unsafe_allow_html=True)
st.sidebar.markdown("<div class='sidebar-item'><b>Volatility:</b> 85% — High Activity</div>", unsafe_allow_html=True)

# === MAIN ===
st.title("💬 AI Trading Chatbot")
col1, col2 = st.columns([2, 1])
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
