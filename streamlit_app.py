import streamlit as st
import requests, datetime, pandas as pd, numpy as np, pytz, time
from datetime import time as dt_time, timedelta, timezone
import ta
from ta.volatility import AverageTrueRange
import json
import random
import yfinance as yf

# --- CONFIGURATION & CONSTANTS ---
RISK_MULTIPLE = 1.0
REWARD_MULTIPLE = 2.0

# --- STREAMLIT CONFIGURATION ---
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# --- CSS STYLING ---
st.markdown("""
<style>
/* Your full CSS here from previous code */
</style>
""", unsafe_allow_html=True)

# --- API KEYS from Streamlit secrets ---
FH_API_KEY = st.secrets.get("FINNHUB_API_KEY", None)
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)
CG_PUBLIC_API_KEY = st.secrets.get("CG_PUBLIC_API_KEY", "")

# --- KNOWN SYMBOLS ---
KNOWN_CRYPTO_SYMBOLS = {"BTC", "ETH", "ADA", "XRP", "DOGE", "SOL", "PI", "HYPE"}
KNOWN_STOCK_SYMBOLS = {"AAPL", "TSLA", "MSFT", "AMZN", "GOOGL", "NVDA", "META", "HOOD", "MSTR", "WMT", "^IXIC", "SPY"}

# --- HELPER FUNCTIONS ---
def resolve_asset_symbol(input_text, asset_type, quote_currency="USD"):
    base_symbol = input_text.strip().upper()
    quote_currency_upper = quote_currency.upper()
    final_symbol = base_symbol + quote_currency_upper if asset_type == "Crypto" else base_symbol
    return base_symbol, final_symbol

def format_price(p):
    if p is None: return "N/A"
    try: p = float(p)
    except Exception: return "N/A"
    if abs(p) >= 10: s = f"{p:,.2f}"
    elif abs(p) >= 1: s = f"{p:,.4f}"
    elif abs(p) >= 0.01: s = f"{p:.4f}"
    else: s = f"{p:.6f}"
    return s.rstrip("0").rstrip(".")

# --- PUBLIC API FETCH FUNCTIONS ---
# CoinGecko
def fetch_cg_price(symbol, vs_currency="usd"):
    symbol = symbol.lower()
    try:
        resp = requests.get("https://api.coingecko.com/api/v3/simple/price",
                            params={"ids": symbol, "vs_currencies": vs_currency})
        data = resp.json()
        return data.get(symbol, {}).get(vs_currency, None)
    except:
        return None

# Binance
def fetch_binance_price(symbol):
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": symbol.upper()})
        data = resp.json()
        return float(data.get("price", 0))
    except:
        return None

# Yahoo Finance
def fetch_yf_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.history(period="1d")['Close'][-1]
        return float(price)
    except:
        return None

# --- STREAMLIT SIDEBAR ---
st.sidebar.markdown('<div class="sidebar-title">AI Trading Chatbot</div>', unsafe_allow_html=True)
asset_type = st.sidebar.selectbox("Select Asset Type", ("Stock/Index", "Crypto"), index=0)
user_input = st.sidebar.text_input("Enter Ticker Symbol", placeholder="e.g., TSLA, BTC, HOOD")
selected_timezone = st.sidebar.selectbox("Select Timezone", pytz.all_timezones, index=pytz.all_timezones.index("UTC"))

# Optional: session info, local time
now_utc = datetime.datetime.now(pytz.utc)
now_local = now_utc.astimezone(pytz.timezone(selected_timezone))
st.sidebar.markdown(f'<div class="local-time-info">Local Time: {now_local.strftime("%Y-%m-%d %H:%M:%S")}</div>', unsafe_allow_html=True)

# --- MAIN APP ---
st.title("AI Trading Chatbot")

if user_input:
    base_symbol, resolved_symbol = resolve_asset_symbol(user_input, asset_type)
    
    price = None
    # Crypto: CoinGecko fallback to Binance
    if asset_type == "Crypto":
        if base_symbol in KNOWN_CRYPTO_SYMBOLS:
            price = fetch_cg_price(base_symbol) or fetch_binance_price(resolved_symbol)
    # Stock/Index: Yahoo Finance
    else:
        if base_symbol in KNOWN_STOCK_SYMBOLS:
            price = fetch_yf_price(base_symbol)
    
    price_display = format_price(price)
    
    st.markdown(f"<div class='big-text'>Analysis for {resolved_symbol}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='asset-price-value'>Current Price: {price_display}</div>", unsafe_allow_html=True)
