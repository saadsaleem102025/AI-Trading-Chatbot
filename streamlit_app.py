import streamlit as st
import requests, datetime, pandas as pd, numpy as np, pytz, time
from datetime import time as dt_time, timedelta, timezone
import ta
from ta.volatility import AverageTrueRange
import json
import random
import openai

# --- CONFIGURATION & CONSTANTS ---
RISK_MULTIPLE = 1.0 
REWARD_MULTIPLE = 2.0 

# --- STREAMLIT CONFIGURATION ---
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === STYLE (unchanged) ===
st.markdown("""<style>/* Your full CSS styling here (same as previous) */</style>""", unsafe_allow_html=True)

# --- API KEYS ---
FH_API_KEY = st.secrets.get("FINNHUB_API_KEY", "") 
CG_PUBLIC_API_KEY = st.secrets.get("CG_PUBLIC_API_KEY", "") 
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "") 
openai.api_key = OPENAI_API_KEY

# --- Known Symbols ---
KNOWN_CRYPTO_SYMBOLS = {"BTC", "ETH", "ADA", "XRP", "DOGE", "SOL", "PI", "HYPE"}
KNOWN_STOCK_SYMBOLS = {"AAPL", "TSLA", "MSFT", "AMZN", "GOOGL", "NVDA", "META", "HOOD", "MSTR", "WMT", "^IXIC", "SPY"}

# --- SYMBOL RESOLUTION ---
def resolve_asset_symbol(input_text, asset_type, quote_currency="USD"):
    base_symbol = input_text.strip().upper()
    quote_currency_upper = quote_currency.upper()
    if asset_type == "Crypto":
        final_symbol = base_symbol + quote_currency_upper
    else:
        final_symbol = base_symbol
    return base_symbol, final_symbol

# === FORMATTING HELPERS ===
def format_price(p):
    if p is None: return "N/A"
    try: p = float(p)
    except: return "N/A"
    if abs(p) >= 10: s = f"{p:,.2f}"
    elif abs(p) >= 1: s = f"{p:,.4f}" 
    elif abs(p) >= 0.01: s = f"{p:.4f}"
    else: s = f"{p:.6f}"
    return s.rstrip("0").rstrip(".")
    
def format_change_main(ch):
    if ch is None: return f"<span class='neutral'>(24h% Change N/A)</span>"
    try: ch = float(ch)
    except: return f"<span class='neutral'>(24h% Change N/A)</span>"
    sign = "+" if ch > 0 else ""
    color_class = "bullish" if ch > 0 else ("bearish" if ch < 0 else "neutral")
    return f"<span class='{color_class}'>{sign}{ch:.2f}%</span>"

# --- API HELPERS ---
def fetch_stock_price_finnhub(ticker, api_key):
    if not api_key: return None, None
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={api_key}"
    try:
        r = requests.get(url, timeout=5).json()
        if r.get('c') and r.get('pc') and r['pc'] != 0 and float(r['c']) > 0:
            price = float(r['c'])
            prev_close = float(r['pc'])
            change_percent = ((price - prev_close) / prev_close) * 100
            time.sleep(0.5)
            return price, change_percent
    except: pass
    return None, None

def fetch_stock_price_yahoo(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
    try:
        r = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'}).json()
        result = r.get('chart', {}).get('result')
        if result:
            meta = result[0].get('meta', {})
            current_price = meta.get('regularMarketPrice')
            prev_close = meta.get('previousClose')
            if current_price is not None and prev_close not in (None, 0):
                change_percent = ((current_price - prev_close) / prev_close) * 100
                return float(current_price), float(change_percent)
    except Exception as e:
        print(f"Yahoo fetch error for {ticker}: {e}")
    return None, None

def fetch_crypto_price_binance(symbol):
    binance_symbol = symbol.replace("USD", "USDT")
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}"
    try:
        r = requests.get(url, timeout=5).json()
        if 'lastPrice' in r and 'priceChangePercent' in r and float(r['lastPrice']) > 0:
            price = float(r['lastPrice'])
            change_percent = float(r['priceChangePercent'])
            time.sleep(0.5)
            return price, change_percent
    except: pass
    return None, None

def fetch_crypto_price_coingecko(symbol, api_key=""):
    base_symbol = symbol.replace("USD", "").replace("USDT", "").lower()
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {'vs_currencies': 'usd', 'include_24hr_change': 'true', 'symbols': base_symbol}
    headers = {}
    if api_key: headers['x-cg-demo-api-key'] = api_key
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5).json()
        for coin_data in r.values():
            if 'usd' in coin_data and float(coin_data['usd']) > 0:
                price = float(coin_data['usd'])
                change_percent = float(coin_data.get('usd_24h_change', 0))
                time.sleep(0.5) 
                return price, change_percent
    except: pass
    return None, None

# === UNIVERSAL PRICE FETCHER ===
@st.cache_data(ttl=60, show_spinner=False)
def get_asset_price(symbol, vs_currency="usd", asset_type="Stock/Index"):
    symbol = symbol.upper()
    base_symbol = symbol.replace("USD", "").replace("USDT", "")
    if asset_type == "Stock/Index":
        price, change = fetch_stock_price_finnhub(base_symbol, FH_API_KEY)
        if price is not None: return price, change
        price, change = fetch_stock_price_yahoo(base_symbol)
        if price is not None: return price, change
        return None, None
    if asset_type == "Crypto":
        price, change = fetch_crypto_price_binance(symbol)
        if price is not None: return price, change
        price, change = fetch_crypto_price_coingecko(symbol, CG_PUBLIC_API_KEY)
        if price is not None: return price, change
        return None, None
    return None, None

# --- INDICATOR, KDE, ATR, BIAS, TRADE RECOMMENDATION LOGIC ---
# Keep all previous functions exactly as you provided:
# synthesize_series, kde_rsi, supertrend_status, bollinger_status, ema_crossover_status,
# parabolic_sar_status, get_kde_rsi_status, get_trade_recommendation, analyze(), etc.

# --- SESSION LOGIC ---
utc_now = datetime.datetime.now(timezone.utc)
# Session logic and sidebar display exactly as before

# --- MAIN EXECUTION ---
st.title("AI Trading Chatbot")

col1, col2 = st.columns([1.5, 2.5])

with col1:
    asset_type = st.selectbox(
        "Select Asset Type",
        ("Stock/Index", "Crypto"),
        index=0,
        help="Select 'Stock/Index' for stocks/indices. Select 'Crypto' for cryptocurrencies."
    )

with col2:
    user_input = st.text_input(
        "Enter Official Ticker Symbol",
        placeholder="e.g., TSLA, HOOD, BTC, HYPE",
        help="Please enter the official ticker symbol (e.g., AAPL, BTC, NDX)."
    )

vs_currency = "usd"
if user_input:
    base_symbol, resolved_symbol = resolve_asset_symbol(user_input, asset_type, vs_currency)
    validation_error = None
    is_common_crypto = base_symbol in KNOWN_CRYPTO_SYMBOLS
    is_common_stock = base_symbol in KNOWN_STOCK_SYMBOLS

    if asset_type == "Crypto" and is_common_stock:
        validation_error = f"You selected <strong>Crypto</strong> but entered a known stock/index symbol (<strong>{base_symbol}</strong>)."
    elif asset_type == "Stock/Index" and is_common_crypto:
        validation_error = f"You selected <strong>Stock/Index</strong> but entered a known crypto symbol (<strong>{base_symbol}</strong>)."

    if validation_error:
        st.markdown(generate_error_message(
            title="⚠️ Asset Type Mismatch ⚠️",
            message="Please ensure the selected **Asset Type** matches the **Ticker Symbol** you entered.",
            details=validation_error
        ), unsafe_allow_html=True)
    else:
        with st.spinner(f"Fetching live data and generating analysis for {resolved_symbol}..."):
            price, price_change_24h = get_asset_price(resolved_symbol, vs_currency, asset_type)
            st.markdown(analyze(resolved_symbol, price, price_change_24h, vs_currency, asset_type), unsafe_allow_html=True)
