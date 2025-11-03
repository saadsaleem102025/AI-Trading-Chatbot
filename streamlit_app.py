import streamlit as st
import time
import requests
import datetime
import pandas as pd
import numpy as np
from statistics import median

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === MODERN STYLING ===
st.markdown("""
<style>
header[data-testid="stHeader"], footer {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}
html, body, [class*="stText"], [data-testid="stMarkdownContainer"] {
    font-size: 18px !important;
    color: #E9EEF6 !important;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    line-height: 1.8 !important;
}
[data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #0F2027, #203A43, #2C5364);
    color: white !important;
    padding-left: 360px !important;
    padding-right: 25px;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0E111A 0%, #1B1F2E 100%);
    width: 340px !important;
    position: fixed !important;
    top: 0; left: 0; bottom: 0;
    z-index: 100;
    padding: 1.6rem 1.2rem 2rem 1.2rem;
    border-right: 1px solid rgba(255,255,255,0.08);
    box-shadow: 8px 0 18px rgba(0,0,0,0.4);
}
.sidebar-title { font-size: 30px; font-weight: 800; color: #66FCF1; margin-bottom: 25px; }
.sidebar-item {
    background: rgba(255,255,255,0.07);
    border-radius: 12px; padding: 12px; margin: 10px 0;
    font-size: 17px; box-shadow: inset 0 0 10px rgba(0,0,0,0.3);
    color: #C5C6C7;
}
.sidebar-clock {
    display: flex; align-items: center; gap: 8px;
    margin-top: 10px; padding: 8px 12px;
    background: rgba(255,255,255,0.05);
    border-radius: 8px; color: #D8DEE9;
    font-size: 15px; font-weight: 600;
    text-shadow: 0 0 6px rgba(102,252,241,0.4);
    box-shadow: inset 0 0 5px rgba(255,255,255,0.05);
}
.sidebar-clock svg, .sidebar-clock span { color: #66FCF1 !important; }
.section-header {
    font-size: 22px; font-weight: 700; color: #45A29E;
    margin-top: 25px; border-left: 4px solid #66FCF1; padding-left: 8px;
}
.big-text {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 16px; padding: 28px; margin-top: 15px;
    box-shadow: 0 0 25px rgba(0,0,0,0.4);
}
[data-baseweb="input"] input {
    background-color: rgba(255,255,255,0.12) !important;
    color: #E9EEF6 !important;
    border-radius: 10px !important;
}
h1, h2, h3 { color: #66FCF1 !important; text-shadow: 0 0 10px rgba(102,252,241,0.4); }
</style>
""", unsafe_allow_html=True)

# === API KEYS ===
TWELVE_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]
ALPHA_API_KEY = st.secrets.get("ALPHA_VANTAGE_API_KEY", "")
FINNHUB_KEY = st.secrets.get("FINNHUB_API_KEY", "")

# === AUTO REFRESH ===
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

# === UNIVERSAL PRICE FETCHER (multi-source redundancy) ===
@st.cache_data(ttl=60)
def get_verified_price(symbol, vs_currency="usd"):
    prices = []
    symbol_up = symbol.upper()

    # --- CRYPTO SOURCES ---
    sid = CRYPTO_ID_MAP.get(symbol_up, symbol.lower())
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                         params={"ids": sid, "vs_currencies": vs_currency},
                         timeout=6).json()
        if sid in r and vs_currency in r[sid]:
            prices.append(float(r[sid][vs_currency]))
    except Exception:
        pass

    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol_up}USDT", timeout=6).json()
        if "price" in r:
            prices.append(float(r["price"]))
    except Exception:
        pass

    # --- STOCK SOURCES ---
    if not prices:  # assume symbol might be stock
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol_up}", timeout=6).json()
            c = r["chart"]["result"][0]["meta"]["regularMarketPrice"]
            prices.append(float(c))
        except Exception:
            pass

        if ALPHA_API_KEY:
            try:
                r = requests.get(f"https://www.alphavantage.co/query",
                                 params={"function": "GLOBAL_QUOTE", "symbol": symbol_up, "apikey": ALPHA_API_KEY},
                                 timeout=6).json()
                if "Global Quote" in r and "05. price" in r["Global Quote"]:
                    prices.append(float(r["Global Quote"]["05. price"]))
            except Exception:
                pass

        if FINNHUB_KEY:
            try:
                r = requests.get(f"https://finnhub.io/api/v1/quote",
                                 params={"symbol": symbol_up, "token": FINNHUB_KEY}, timeout=6).json()
                if "c" in r and r["c"] != 0:
                    prices.append(float(r["c"]))
            except Exception:
                pass

    # --- FOREX SOURCES ---
    if not prices and "/" in symbol_up:
        base, quote = symbol_up.split("/")
        try:
            r = requests.get(f"https://api.exchangerate.host/latest?base={base}&symbols={quote}", timeout=6).json()
            rate = r["rates"].get(quote)
            if rate:
                prices.append(float(rate))
        except Exception:
            pass

        if ALPHA_API_KEY:
            try:
                r = requests.get("https://www.alphavantage.co/query",
                                 params={"function": "CURRENCY_EXCHANGE_RATE",
                                         "from_currency": base,
                                         "to_currency": quote,
                                         "apikey": ALPHA_API_KEY},
                                 timeout=6).json()
                rate = r.get("Realtime Currency Exchange Rate", {}).get("5. Exchange Rate")
                if rate:
                    prices.append(float(rate))
            except Exception:
                pass

    # === FINAL VALIDATION ===
    if prices:
        valid_prices = [p for p in prices if p > 0]
        if valid_prices:
            return round(median(valid_prices), 6)
    return None

# === MARKET SESSION + VOLATILITY ===
def get_market_session_and_volatility(offset_hours):
    utc_now = datetime.datetime.utcnow() + datetime.timedelta(hours=offset_hours)
    hour = utc_now.hour
    if 7 <= hour < 15:
        return "London", "High"
    elif 12 <= hour < 21:
        return "New York", "Very High"
    elif 0 <= hour < 8:
        return "Tokyo", "Medium"
    else:
        return "Sydney", "Low"

# === SIDEBAR ===
st.sidebar.markdown("<p class='sidebar-title'>📊 Market Context</p>", unsafe_allow_html=True)

btc = get_verified_price("BTC")
eth = get_verified_price("ETH")

if btc and eth:
    st.sidebar.markdown(f"<div class='sidebar-item'><b>BTC:</b> ${btc}</div>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<div class='sidebar-item'><b>ETH:</b> ${eth}</div>", unsafe_allow_html=True)
else:
    st.sidebar.warning("⚠️ Live prices temporarily unavailable.")

utc_offsets = [f"UTC{offset:+d}" for offset in range(-12, 13)]
user_offset = st.sidebar.selectbox("Select Timezone (UTC)", utc_offsets, index=5)
offset_hours = int(user_offset.replace("UTC", ""))

user_time = datetime.datetime.utcnow() + datetime.timedelta(hours=offset_hours)
st.sidebar.markdown(f"<div class='sidebar-clock'>🕒 {user_time.strftime('%H:%M:%S')} ({user_offset})</div>", unsafe_allow_html=True)

session, vol = get_market_session_and_volatility(offset_hours)
st.sidebar.markdown(f"<div class='sidebar-item'><b>Active Session:</b> {session}</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='sidebar-item'><b>Volatility:</b> {vol} Activity</div>", unsafe_allow_html=True)

# === MAIN ===
st.title("💬 AI Trading Chatbot")

col1, col2 = st.columns([2, 1])
with col1:
    user_input = st.text_input("Enter Asset Symbol (e.g., BTC, AAPL, EUR/USD)")
with col2:
    vs_currency = st.text_input("Quote Currency (for crypto only)", "usd").lower()

if user_input:
    symbol = user_input.strip().upper()
    price = get_verified_price(symbol, vs_currency)
    if price:
        st.markdown(f"<div class='big-text'><b>{symbol}</b>: ${price}</div>", unsafe_allow_html=True)
    else:
        st.error("❌ Could not verify live data. Try again later.")
else:
    st.info("💬 Enter an asset symbol to get analysis.")
