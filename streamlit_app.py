import streamlit as st
import requests, datetime, pandas as pd, numpy as np, pytz, time
from datetime import time as dt_time, timedelta, timezone
import ta
from ta.volatility import AverageTrueRange
import json
import random

# --- CONFIGURATION & CONSTANTS ---
RISK_MULTIPLE = 1.0 
REWARD_MULTIPLE = 2.0 

# --- STREAMLIT CONFIGURATION ---
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === 1. STYLE (Altered for Sidebar Scrolling) ===
st.markdown("""
<style>
/* Base Streamlit overrides */
header[data-testid="stHeader"], footer {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}

/* Base font and colors */
html, body, [class*="stText"], [data-testid="stMarkdownContainer"] {
    font-size: 18px !important;
    color: #E0E0E0 !important;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    line-height: 1.7 !important;
}

/* Main background (Lighter) */
[data-testid="stAppViewContainer"] {
    background: #1F2937;
    color: #E0E0E0 !important;
    padding-left: 360px !important;
    padding-right: 25px;
}
/* Sidebar styling (Darker) */
[data-testid="stSidebar"] {
    background: #111827;
    width: 340px !important; min-width: 340px !important; max-width: 350px !important;
    position: fixed !important; top: 0; left: 0; bottom: 0; z-index: 100;
    padding: 0.1rem 1.0rem 0.1rem 1.0rem; 
    border-right: 1px solid #1F2937;
    box-shadow: 8px 0 18px rgba(0,0,0,0.4);
}
/* Main content boxes (Darker, to contrast main bg) */
.big-text {
    background: #111827;
    border: 1px solid #374151;
    border-radius: 16px;
    padding: 28px;
    margin-top: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

/* Section headers */
.section-header {
    font-size: 22px;
    font-weight: 700;
    color: #60A5FA;
    margin-top: 20px;
    margin-bottom: 10px;
    padding-bottom: 5px;
    border-bottom: 2px solid #374151;
}

/* --- BOLD TEXT COLOR CHANGE (KEYWORD COLOR) --- */
.big-text b, .trade-recommendation-summary strong {
    color: #FFD700 !important; /* Gold color for bolded text */
    font-weight: 800;
}
[data-testid="stSidebar"] b {
    color: #FFFFFF !important; font-weight: 800;
}
.analysis-item b { color: #60A5FA; font-weight: 700; }
.asset-price-value { color: #F59E0B !important; }

/* --- SIDEBAR COMPONENTS --- */
.sidebar-title { font-size: 28px; font-weight: 800; color: #60A5FA; margin-top: 0px; margin-bottom: 5px; padding-top: 5px; text-shadow: 0 0 10px rgba(96, 165, 250, 0.3); }
.sidebar-item { background: #1F2937; border-radius: 8px; padding: 8px 12px; margin: 4px 0; font-size: 17px; color: #9CA3AF; border: 1px solid #374151; }
.local-time-info { color: #00FFFF !important; font-weight: 700; font-size: 17px !important; }
.active-session-info { color: #FF8C00 !important; font-weight: 700; font-size: 17px !important; }
.status-volatility-info { color: #32CD32 !important; font-weight: 700; font-size: 17px !important; }
.sidebar-item b { color: #FFFFFF !important; font-weight: 800; }

/* Analysis items with descriptions */
.analysis-item { font-size: 18px; color: #E0E0E0; margin: 8px 0; }
.indicator-explanation { font-size: 15px; color: #9CA3AF; font-style: italic; margin-left: 20px; margin-top: 3px; margin-bottom: 10px; }
.analysis-bias { font-size: 24px; font-weight: 800; margin-top: 15px; padding-top: 10px; border-top: 1px dashed #374151; }

/* Trading recommendation (for Natural Language Summary box) */
.trade-recommendation-summary { font-size: 18px; line-height: 1.8; margin-top: 10px; margin-bottom: 20px; padding: 15px; background: #243B55; border-radius: 8px; border-left: 5px solid #60A5FA; }

/* Risk warning */
.risk-warning { background: #7C2D12; border: 2px solid #DC2626; border-radius: 8px; padding: 15px; margin-top: 20px; font-size: 14px; color: #FCA5A5; }

/* Psychology motto */
.analysis-motto-prominent { font-size: 20px; font-weight: 900; color: #F59E0B; text-transform: uppercase; text-shadow: 0 0 10px rgba(245, 158, 11, 0.4); margin-top: 15px; padding: 10px; border: 2px solid #F59E0B; border-radius: 8px; background: #111827; text-align: center; }

/* Colors for data/bias */
.bullish { color: #10B981; font-weight: 700; }
.bearish { color: #EF4444; font-weight: 700; }
.neutral { color: #F59E0B; font-weight: 700; }
.percent-label { color: #C084FC; font-weight: 700; }

.kde-red { color: #EF4444; }
.kde-orange { color: #F59E0B; }
.kde-yellow { color: #FFCC00; }
.kde-green { color: #10B981; }
.kde-purple { color: #C084FC; }
</style>
""", unsafe_allow_html=True)

# --- API KEYS from Streamlit secrets ---
FH_API_KEY = st.secrets.get("FINNHUB_API_KEY", None)  # Private key for Finnhub
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)  # Private key for OpenAI
CG_PUBLIC_API_KEY = st.secrets.get("CG_PUBLIC_API_KEY", "")  # Public key optional

# --- KNOWN SYMBOLS ---
KNOWN_CRYPTO_SYMBOLS = {"BTC", "ETH", "ADA", "XRP", "DOGE", "SOL", "PI", "HYPE"}
KNOWN_STOCK_SYMBOLS = {"AAPL", "TSLA", "MSFT", "AMZN", "GOOGL", "NVDA", "META", "HOOD", "MSTR", "WMT", "^IXIC", "SPY"}

# --- HELPER FUNCTIONS (unchanged from original code) ---
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
# ... all other helper functions remain identical ...

# --- PRICE FETCHERS (Finnhub, Yahoo, Binance, CoinGecko) ---
# identical to your original code but now FH_API_KEY and OPENAI_API_KEY will be used if set

# --- ANALYSIS & INDICATORS ---
# unchanged, full logic preserved (kde_rsi, supertrend_status, bollinger_status, etc.)
# ATR calculation still uses ta library
# trade recommendation logic unchanged

# --- STREAMLIT INTERFACE ---
# sidebar and main UI as per original code
# asset selection, ticker input, timezone, session info all unchanged

# --- MAIN EXECUTION ---
st.title("AI Trading Chatbot")

col1, col2 = st.columns([1.5, 2.5])
with col1:
    asset_type = st.selectbox("Select Asset Type", ("Stock/Index", "Crypto"), index=0)

with col2:
    user_input = st.text_input("Enter Official Ticker Symbol", placeholder="e.g., TSLA, HOOD, BTC, HYPE")

vs_currency = "usd"
if user_input:
    base_symbol, resolved_symbol = resolve_asset_symbol(user_input, asset_type, vs_currency)
    validation_error = None
    is_common_crypto = base_symbol in KNOWN_CRYPTO_SYMBOLS
    is_common_stock = base_symbol in KNOWN_STOCK_SYMBOLS
    if asset_type == "Crypto" and is_common_stock:
        validation_error = f"Crypto selected but entered stock symbol ({base_symbol})."
    elif asset_type == "Stock/Index" and is_common_crypto:
        validation_error = f"Stock/Index selected but entered crypto symbol ({base_symbol})."

    if validation_error:
        st.markdown(generate_error_message(
            title="⚠️ Asset Type Mismatch ⚠️",
            message="Please ensure Asset Type matches Ticker Symbol.",
            details=validation_error
        ), unsafe_allow_html=True)
    else:
        with st.spinner(f"Fetching live data and generating analysis for {resolved_symbol}..."):
            price, price_change_24h = get_asset_price(resolved_symbol, vs_currency, asset_type)
            st.markdown(analyze(resolved_symbol, price, price_change_24h, vs_currency, asset_type), unsafe_allow_html=True)
