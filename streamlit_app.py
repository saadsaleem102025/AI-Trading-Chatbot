import streamlit as st
import time, requests, datetime, pandas as pd, numpy as np
from tzlocal import get_localzone

st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === API KEYS ===
TWELVE_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]
ALPHA_KEY = st.secrets["ALPHA_VANTAGE_API_KEY"]
FINNHUB_KEY = st.secrets["FINNHUB_API_KEY"]

# === CRYPTO ID MAP ===
CRYPTO_ID_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "AVAX": "avalanche-2",
    "BNB": "binancecoin", "XRP": "ripple", "DOGE": "dogecoin", "ADA": "cardano",
    "DOT": "polkadot", "LTC": "litecoin", "CFX": "conflux-token", "XLM": "stellar",
    "SHIB": "shiba-inu", "PEPE": "pepe", "TON": "the-open-network",
    "SUI": "sui", "NEAR": "near"
}

# === UNIVERSAL MULTI-BACKUP FETCHER ===
def get_price(symbol, category="crypto", vs_currency="usd"):
    sid = CRYPTO_ID_MAP.get(symbol.upper(), symbol.lower())
    urls = []

    if category == "crypto":
        urls = [
            ("coingecko", f"https://api.coingecko.com/api/v3/simple/price?ids={sid}&vs_currencies={vs_currency}&include_24hr_change=true"),
            ("binance", f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.upper()}USDT"),
            ("twelvedata", f"https://api.twelvedata.com/price?symbol={symbol.upper()}/{vs_currency.upper()}&apikey={TWELVE_API_KEY}"),
            ("finnhub", f"https://finnhub.io/api/v1/crypto/price?symbol=BINANCE:{symbol.upper()}USDT&token={FINNHUB_KEY}"),
            ("alphavantage", f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol.upper()}&apikey={ALPHA_KEY}")
        ]

    elif category == "stock":
        urls = [
            ("twelvedata", f"https://api.twelvedata.com/price?symbol={symbol.upper()}&apikey={TWELVE_API_KEY}"),
            ("finnhub", f"https://finnhub.io/api/v1/quote?symbol={symbol.upper()}&token={FINNHUB_KEY}"),
            ("alphavantage", f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol.upper()}&apikey={ALPHA_KEY}")
        ]

    elif category == "forex":
        urls = [
            ("twelvedata", f"https://api.twelvedata.com/price?symbol={symbol.upper()}&apikey={TWELVE_API_KEY}"),
            ("finnhub", f"https://finnhub.io/api/v1/forex/rate?pair={symbol.upper()}&token={FINNHUB_KEY}"),
            ("alphavantage", f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={symbol[:3]}&to_currency={symbol[3:]}&apikey={ALPHA_KEY}")
        ]

    for name, url in urls:
        try:
            res = requests.get(url, timeout=6)
            res.raise_for_status()
            data = res.json()

            if name == "coingecko" and sid in data:
                d = data[sid]
                return float(d[vs_currency]), float(d.get(f"{vs_currency}_24h_change", 0))
            if name == "binance" and "lastPrice" in data:
                return float(data["lastPrice"]), float(data["priceChangePercent"])
            if name == "twelvedata" and "price" in data:
                return float(data["price"]), 0.0
            if name == "finnhub":
                if "c" in data: return float(data["c"]), 0.0
                if "price" in data: return float(data["price"]), 0.0
                if "rate" in data: return float(data["rate"]), 0.0
            if name == "alphavantage":
                if "Global Quote" in data:
                    q = data["Global Quote"]
                    price = float(q.get("05. price", 0))
                    change = float(q.get("10. change percent", "0%").replace("%", ""))
                    if price > 0: return price, change
                if "Realtime Currency Exchange Rate" in data:
                    r = data["Realtime Currency Exchange Rate"]
                    return float(r["5. Exchange Rate"]), 0.0
        except Exception:
            continue

    return 1.0, 0.0  # safe fallback


# === HISTORICAL DATA ===
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

# === KDE RSI ===
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

# === SUPER TREND ===
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

# === BOLLINGER BANDS ===
def bollinger_status(df):
    close = df["close"]
    ma = close.rolling(20).mean().iloc[-1]
    std = close.rolling(20).std().iloc[-1]
    upper, lower = ma + 2*std, ma - 2*std
    last = close.iloc[-1]
    if last > upper: return "Upper Band — Overbought"
    if last < lower: return "Lower Band — Oversold"
    return "Within Bands — Normal"

# === COMBINE BIAS ===
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
    df_4h = get_twelve_data(symbol, "4h")
    df_1h = get_twelve_data(symbol, "1h")
    df_15m = get_twelve_data(symbol, "15min")

    if df_1h is None: return "<div class='big-text'>⚠ Data unavailable — check symbol or API limits.</div>"

    kde_val = kde_rsi(df_1h)
    st_text = f"{supertrend_status(df_4h)} (4H) • {supertrend_status(df_1h)} (1H)"
    bb_text = bollinger_status(df_15m)
    bias, score = combined_bias(kde_val, st_text, bb_text)

    atr = df_1h["high"].max() - df_1h["low"].min()
    entry = price - 0.3 * atr
    target = price + 1.5 * atr
    stop = price - 1.0 * atr

    motivation_msgs = {
        "Bullish": "🚀 Stay sharp — momentum’s on your side.\nTrade with confidence, not emotion.",
        "Bearish": "⚡ Discipline is your shield.\nWait for clarity, and strike when odds align.",
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

# === TIMEZONE AUTO-DETECTION ===
user_time = datetime.datetime.now(get_localzone())
st.sidebar.markdown(f"<div class='sidebar-clock'>🕒 {user_time.strftime('%H:%M:%S')} (Local)</div>", unsafe_allow_html=True)

# === MARKET CONTEXT ===
btc, btc_ch = get_price("BTC", "crypto")
eth, eth_ch = get_price("ETH", "crypto")
st.sidebar.markdown(f"<div class='sidebar-item'><b>BTC:</b> ${btc:.2f} ({btc_ch:+.2f}%)</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='sidebar-item'><b>ETH:</b> ${eth:.2f} ({eth_ch:+.2f}%)</div>", unsafe_allow_html=True)

# === MAIN CHAT ===
st.title("AI Trading Chatbot")
symbol = st.text_input("Enter Asset Symbol (e.g., BTC, AAPL, EURUSD)").strip().upper()
vs_currency = st.text_input("Quote Currency", "usd").lower()

if symbol:
    category = "crypto" if symbol in CRYPTO_ID_MAP else "stock" if symbol.isalpha() and len(symbol)<=5 else "forex"
    price, _ = get_price(symbol, category, vs_currency)
    analysis = analyze(symbol, price, vs_currency)
    st.markdown(analysis, unsafe_allow_html=True)
else:
    st.info("💬 Enter an asset symbol to get analysis.")
