# ai_trading_chatbot.py
import streamlit as st
import time
import requests
import datetime
import pandas as pd
import numpy as np
import random

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === CUSTOM STYLING (keeps layout tidy & readable) ===
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background-color: #f5f7fa;
    padding: 1.2rem 0.8rem;
}
.sidebar-title { font-size: 26px !important; font-weight:700; color:#0f172a; margin-bottom:8px; }
.sidebar-item { font-size:15px; color:#334155; margin-bottom:6px; line-height:1.3; white-space:normal; word-wrap:break-word; }
.sidebar-highlight { font-weight:700; color:#0f172a; }
</style>
""", unsafe_allow_html=True)

# === API KEY (set in Streamlit secrets) ===
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

# === PRICE FETCHER (robust multi-source fallback) ===
def get_crypto_price(symbol, vs_currency="usd"):
    sid = CRYPTO_ID_MAP.get(symbol.upper(), symbol.lower())
    # CoinGecko
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

    # Binance fallback
    try:
        pair = f"{symbol.upper()}USDT"
        res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={pair}", timeout=8).json()
        price = float(res.get("price", 0))
        if 0.0000001 < price < 1e7:
            return round(price, 8), 0.0
    except Exception:
        pass

    # TwelveData fallback
    try:
        res = requests.get(f"https://api.twelvedata.com/price?symbol={symbol.upper()}/USD&apikey={TWELVE_API_KEY}", timeout=8).json()
        price = float(res.get("price", 0) or 0)
        if 0.0000001 < price < 1e7:
            return round(price, 8), 0.0
    except Exception:
        pass

    return 0.0, 0.0  # fallback if all fail

# === HISTORICAL DATA FETCH ===
def get_twelve_data(symbol, interval="1h", outputsize=100):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=10).json()
        if "values" not in res:
            return None
        df = pd.DataFrame(res["values"])
        df = df.rename(columns={"datetime":"datetime","close":"close","high":"high","low":"low"})
        df[["close","high","low"]] = df[["close","high","low"]].astype(float)
        return df.sort_values("datetime").reset_index(drop=True)
    except Exception:
        return None

# === SYNTHETIC SERIES CREATION ===
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

# === TRUE ATR ===
def true_atr(df, period=14):
    try:
        df = df.copy()
        df["H-L"] = df["high"] - df["low"]
        df["H-PC"] = (df["high"] - df["close"].shift(1)).abs()
        df["L-PC"] = (df["low"] - df["close"].shift(1)).abs()
        df["TR"] = df[["H-L","H-PC","L-PC"]].max(axis=1)
        atr = df["TR"].ewm(alpha=1/period, adjust=False).mean().iloc[-1]
        return float(atr)
    except Exception:
        return max(1e-8, float(df["close"].iloc[-1]) * 0.01)

# === KDE-LIKE RSI (no SciPy) ===
def kde_rsi(df):
    try:
        closes = df["close"].astype(float).values
        if len(closes) < 16:
            return 50.0
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = pd.Series(gains).ewm(alpha=1/14, adjust=False).mean().to_numpy()
        avg_loss = pd.Series(losses).ewm(alpha=1/14, adjust=False).mean().to_numpy()
        rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss!=0)
        rsi = 100 - (100 / (1 + rs))
        rsi_vals = rsi[-30:]
        # smooth with Gaussian weights (manual KDE)
        w = np.exp(-0.5 * (np.linspace(-2, 2, len(rsi_vals)))**2)
        return float(np.average(rsi_vals, weights=w))
    except Exception:
        return 50.0

def interpret_kde_rsi(rsi):
    if rsi < 10 or rsi > 90: return "🟣 Reversal Danger Zone"
    if rsi < 20: return "🔴 <20% → Extreme Oversold"
    if rsi < 40: return "🟠 20–40% → Weak Bearish"
    if rsi < 60: return "🟡 40–60% → Neutral Zone"
    if rsi < 80: return "🟢 60–80% → Strong Bullish"
    return "🔵 >80% → Extreme Overbought"

def bollinger_status(df):
    try:
        close = df["close"].astype(float)
        ma = close.rolling(20).mean().iloc[-1]
        std = close.rolling(20).std().iloc[-1]
        upper = ma + 2*std
        lower = ma - 2*std
        last = close.iloc[-1]
        if last > upper: return "Upper Band — overbought"
        if last < lower: return "Lower Band — oversold"
        return "Within Bands — normal"
    except Exception:
        return "Neutral"

def supertrend_status(df, multiplier=3, period=10):
    try:
        hl2 = (df["high"] + df["low"]) / 2
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        last_close = df["close"].iloc[-1]
        if last_close > hl2.iloc[-1]:
            return "Supertrend: Bullish"
        else:
            return "Supertrend: Bearish"
    except Exception:
        return "Supertrend neutral"

# === COMBINED BIAS (50 / 30 / 20) ===
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

# === MAIN ANALYSIS ===
def analyze(symbol, price, vs_currency):
    df_4h = get_twelve_data(symbol, "4h") or synthesize_series(price)
    df_1h = get_twelve_data(symbol, "1h") or synthesize_series(price)
    df_15m = get_twelve_data(symbol, "15min") or synthesize_series(price)

    kde_val = kde_rsi(df_1h)
    st_text = f"{supertrend_status(df_4h)} (4H) • {supertrend_status(df_1h)} (1H)"
    bb_text = bollinger_status(df_15m)

    bias, score = combined_bias(kde_val, st_text, bb_text)
    atr = true_atr(df_1h)
    entry = price - 0.3 * atr
    target = price + 1.5 * atr
    stop = price - 1.0 * atr

    motivation = {
        "Bullish": "Focus on trend-following; trail stops smartly.",
        "Bearish": "Stay disciplined and protect capital.",
        "Neutral": "Patience is key — wait for confluence.",
    }[bias]

    return f"""
**Price:** {price:.6f} {vs_currency.upper()}
- KDE RSI: {kde_val:.2f}% → {interpret_kde_rsi(kde_val)}
- Bollinger: {bb_text}
- Supertrend: {st_text}

**Levels**
- Entry: {entry:.6f}
- Target: {target:.6f}
- Stop: {stop:.6f}

**Bias:** {bias} ({score})
💡 {motivation}
""".strip()

# === SIDEBAR ===
st.sidebar.markdown("<p class='sidebar-title'>📊 Market Context</p>", unsafe_allow_html=True)
btc, btc_ch = get_crypto_price("BTC")
eth, eth_ch = get_crypto_price("ETH")
st.sidebar.markdown(f"<p class='sidebar-item'><b>BTC:</b> ${btc} ({btc_ch:+.2f}%)</p>", unsafe_allow_html=True)
st.sidebar.markdown(f"<p class='sidebar-item'><b>ETH:</b> ${eth} ({eth_ch:+.2f}%)</p>", unsafe_allow_html=True)

utc_offsets = [f"UTC{offset:+d}" for offset in range(-12, 13)]
user_offset = st.sidebar.selectbox("Select Timezone", utc_offsets, index=5)
offset_hours = int(user_offset.replace("UTC", ""))
user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset_hours)
st.sidebar.caption(f"🕒 Local Time: {user_time.strftime('%H:%M:%S')} ({user_offset})")

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
        if df is not None:
            price = float(df["close"].iloc[-1])
        else:
            price = 1.0
    analysis = analyze(symbol, price, vs_currency)
    st.success(analysis)
else:
    st.info("💬 Enter an asset symbol to get analysis.")
