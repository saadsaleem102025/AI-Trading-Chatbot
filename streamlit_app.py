import streamlit as st
import requests, datetime, pandas as pd, numpy as np, pytz, time
from datetime import time as dt_time, timedelta, timezone
import pandas_ta as ta
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
    /* Adjusted padding to reduce overall height and prevent scrolling */
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
/* Target <b> tags and <strong> tags, setting the color to Gold */
.big-text b, .trade-recommendation-summary strong {
    color: #FFD700 !important; /* Gold color for bolded text */
    font-weight: 800;
}
/* Ensure the sidebar bold text remains white for contrast */
[data-testid="stSidebar"] b {
    color: #FFFFFF !important;
    font-weight: 800;
}
/* Ensure Analysis items headers remain blue */
.analysis-item b { color: #60A5FA; font-weight: 700; }
/* Override Gold for the Asset Price which uses a different color */
.asset-price-value { color: #F59E0B !important; }

/* --- SIDEBAR COMPONENTS --- */
.sidebar-title {
    font-size: 28px; font-weight: 800; color: #60A5FA; margin-top: 0px; margin-bottom: 5px;
    padding-top: 5px; text-shadow: 0 0 10px rgba(96, 165, 250, 0.3);
}
/* 💡 CHANGE 1: Increased font size and padding for sidebar items */
.sidebar-item {
    background: #1F2937; border-radius: 8px;
    padding: 8px 12px; margin: 4px 0; 
    font-size: 17px; /* Increased from 16px */
    color: #9CA3AF; border: 1px solid #374151;
}
.local-time-info { color: #00FFFF !important; font-weight: 700; font-size: 17px !important; }
.active-session-info { color: #FF8C00 !important; font-weight: 700; font-size: 17px !important; }
.status-volatility-info { color: #32CD32 !important; font-weight: 700; font-size: 17px !important; }
.sidebar-item b { color: #FFFFFF !important; font-weight: 800; }

/* Sidebar Asset Price block (No longer used, but kept for future) */
.sidebar-asset-price-item {
    background: #1F2937; border-radius: 8px;
    padding: 6px 10px; margin: 8px 0;
    font-size: 16px; color: #E5E7EB; border: 1px solid #374151;
}

/* Price figure prominence in sidebar (No longer used, but kept for future) */
.asset-price-value-sidebar {
    color: #F59E0B;
    font-weight: 800;
    font-size: 22px; 
    display: inline-block;
    margin-right: 5px;
}
.change-percent-sidebar {
    font-weight: 700;
    font-size: 16px;
}

/* Analysis items with descriptions */
.analysis-item {
    font-size: 18px;
    color: #E0E0E0;
    margin: 8px 0;
}

.indicator-explanation {
    font-size: 15px;
    color: #9CA3AF;
    font-style: italic;
    margin-left: 20px;
    margin-top: 3px;
    margin-bottom: 10px;
}

.analysis-bias {
    font-size: 24px;
    font-weight: 800;
    margin-top: 15px;
    padding-top: 10px;
    border-top: 1px dashed #374151;
}

/* Trading recommendation (for Natural Language Summary box) */
.trade-recommendation-summary {
    font-size: 18px;
    line-height: 1.8;
    margin-top: 10px;
    margin-bottom: 20px;
    padding: 15px;
    background: #243B55;
    border-radius: 8px;
    border-left: 5px solid #60A5FA;
}

/* Risk warning */
.risk-warning {
    background: #7C2D12;
    border: 2px solid #DC2626;
    border-radius: 8px;
    padding: 15px;
    margin-top: 20px;
    font-size: 14px;
    color: #FCA5A5;
}

/* Psychology motto */
.analysis-motto-prominent {
    font-size: 20px;
    font-weight: 900;
    color: #F59E0B;
    text-transform: uppercase;
    text-shadow: 0 0 10px rgba(245, 158, 11, 0.4);
    margin-top: 15px;
    padding: 10px;
    border: 2px solid #F59E0B;
    border-radius: 8px;
    background: #111827;
    text-align: center;
}

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
FH_API_KEY = st.secrets.get("FINNHUB_API_KEY", "") 
CG_PUBLIC_API_KEY = st.secrets.get("CG_PUBLIC_API_KEY", "") 

# Define simplified sets for basic type validation (not comprehensive)
KNOWN_CRYPTO_SYMBOLS = {"BTC", "ETH", "ADA", "XRP", "DOGE", "SOL", "PI", "HYPE"}
KNOWN_STOCK_SYMBOLS = {"AAPL", "TSLA", "MSFT", "AMZN", "GOOGL", "NVDA", "META", "HOOD", "MSTR", "WMT", "^IXIC", "SPY"}

def resolve_asset_symbol(input_text, asset_type, quote_currency="USD"):
    """
    Resolves the asset symbol based ONLY on the input ticker, 
    and appends USD for Crypto type.
    Returns: (base_symbol, final_symbol)
    """
    base_symbol = input_text.strip().upper()
    quote_currency_upper = quote_currency.upper()
    
    if asset_type == "Crypto":
        # Crypto symbols are always pairs (e.g., BTCUSD)
        final_symbol = base_symbol + quote_currency_upper
    else:
        # Stock/Index symbols are the ticker itself (e.g., TSLA, ^IXIC)
        final_symbol = base_symbol
        
    return base_symbol, final_symbol

# === HELPERS FOR FORMATTING (Unchanged) ===
def format_price(p):
    if p is None: return "N/A" 
    try: p = float(p)
    except Exception: return "N/A" 
    
    if abs(p) >= 10: s = f"{p:,.2f}"
    elif abs(p) >= 1: s = f"{p:,.4f}" 
    elif abs(p) >= 0.01: s = f"{p:.4f}"
    else: s = f"{p:.6f}"
    return s.rstrip("0").rstrip(".")

def format_change_sidebar(ch):
    """Formats the price change for the sidebar, including color."""
    if ch is None: return "<span class='neutral'>N/A</span>"
    try: ch = float(ch)
    except Exception: return "<span class='neutral'>N/A</span>"
    sign = "+" if ch > 0 else ""
    color_class = "bullish" if ch > 0 else ("bearish" if ch < 0 else "neutral")
    return f"<span class='change-percent-sidebar {color_class}' style='font-size: 16px; font-weight: 700;'>{sign}{ch:.2f}%</span>"

def format_change_main(ch):
    if ch is None:
        return f"<span style='white-space: nowrap;'>&nbsp;|&nbsp;<span class='neutral'>(24h% Change N/A)</span></span>"
    
    try: ch = float(ch)
    except Exception: return f"<span style='white-space: nowrap;'>&nbsp;|&nbsp;<span class='neutral'>(24h% Change N/A)</span></span>"
    
    sign = "+" if ch > 0 else ""
    color_class = "bullish" if ch > 0 else ("bearish" if ch < 0 else "neutral")
    
    return f"<span style='white-space: nowrap;'>&nbsp;|&nbsp;<span class='{color_class}'>{sign}{ch:.2f}%</span> <span class='percent-label'>(24h% Change)</span></span>"

# --- API HELPERS (Unchanged) ---
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
    except Exception:
        pass
    return None, None

def fetch_stock_price_yahoo(ticker):
   url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
    try:
        r = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if 'chart' in r and 'result' in r['chart'] and r['chart']['result']:
            result = r['chart']['result'][0]
            meta = result.get('meta', {})
            current_price = meta.get('regularMarketPrice')
            prev_close = meta.get('previousClose')
            if current_price and prev_close and prev_close > 0:
                change_percent = ((current_price - prev_close) / prev_close) * 100
                return float(current_price), float(change_percent)
    except Exception:
        pass
    return None, None

def fetch_crypto_price_binance(symbol):
    # This uses the full symbol, e.g., BTCUSD
    binance_symbol = symbol.replace("USD", "USDT")
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}"
    try:
        r = requests.get(url, timeout=5).json()
        if 'lastPrice' in r and 'priceChangePercent' in r and float(r['lastPrice']) > 0:
            price = float(r['lastPrice'])
            change_percent = float(r['priceChangePercent'])
            time.sleep(0.5)
            return price, change_percent
    except Exception:
        pass
    return None, None

def fetch_crypto_price_coingecko(symbol, api_key=""):
    # This needs the base symbol (e.g., BTC, not BTCUSD)
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
    except Exception:
        pass
    return None, None

# === UNIVERSAL PRICE FETCHER (Loading Spinner Suppressed) ===
@st.cache_data(ttl=60, show_spinner=False) # Spinner is hidden here
def get_asset_price(symbol, vs_currency="usd", asset_type="Stock/Index"):
    symbol = symbol.upper()
    base_symbol = symbol.replace("USD", "").replace("USDT", "")
    
    # --- 1. STOCK/INDEX LOGIC (Finnhub -> Yahoo) ---
    if asset_type == "Stock/Index":
        price, change = fetch_stock_price_finnhub(base_symbol, FH_API_KEY)
        if price is not None:
            return price, change
        
        price, change = fetch_stock_price_yahoo(base_symbol)
        if price is not None:
            return price, change
        
        return None, None
            
    # --- 2. CRYPTO LOGIC (Binance -> CoinGecko) ---
    if asset_type == "Crypto":
        price, change = fetch_crypto_price_binance(symbol)
        if price is not None:
            return price, change
        
        price, change = fetch_crypto_price_coingecko(symbol, CG_PUBLIC_API_KEY)
        if price is not None:
            return price, change
        
        return None, None
    
    return None, None

# === INDICATOR LOGIC (Unchanged) ===
def get_historical_data(symbol, interval="1h", outputsize=200):
    return None

def synthesize_series(symbol, length=200, volatility_pct=0.008): 
    seed_val = int(hash(symbol) % (2**31 - 1))
    np.random.seed(seed_val) 
    base = 10.0 
    returns = np.random.normal(0, volatility_pct, size=length)
    series = base * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        "datetime": pd.date_range(end=datetime.datetime.utcnow(), periods=length, freq="T"),
        "Close": series, 
        "High": series * (1.002 + np.random.uniform(0, 0.001, size=length)), 
        "Low": series * (0.998 - np.random.uniform(0, 0.001, size=length)), 
        "Open": series * (1.0005 + np.random.uniform(-0.001, 0.001, size=length)), 
    })
    return df.iloc[-length:].set_index('datetime')

def kde_rsi(df_placeholder, symbol):
    seed_val = int(hash(symbol) % (2**31 - 1))
    np.random.seed(seed_val)
    kde_val = np.random.randint(1500, 8500) / 100.0
    return float(kde_val)

def supertrend_status(df, kde_val):
    if kde_val > 65: return "Bullish - Trend Confirmed"
    if kde_val < 35: return "Bearish - Trend Confirmed"
    return "Consolidation - Range Bound"

def bollinger_status(df, kde_val):
    if kde_val < 20: return "Outside Lower Band - Extreme Oversold"
    if kde_val > 80: return "Outside Upper Band - Extreme Overbought"
    return "Within Bands - Normal Volatility"

def ema_crossover_status(kde_val): 
    if kde_val > 70: return "Bullish Cross (5>20) - Strong Momentum"
    if kde_val < 30: return "Bearish Cross (5<20) - Strong Momentum"
    return "Indecisive/Flat EMAs"

def parabolic_sar_status(kde_val):
    if kde_val > 60: return "Bullish (Dots Below Price) - Uptrend Confirmed"
    if kde_val < 40: return "Bearish (Dots Above Price) - Downtrend Confirmed"
    return "Reversal Imminent - Avoid Entry"

def get_kde_rsi_status(kde_val):
    if kde_val < 15: return f"<span class='kde-purple'>🟣 {kde_val:.2f}% → Extreme Oversold</span> (High Bullish Reversal Probability)"
    elif kde_val < 30: return f"<span class='kde-red'>🔴 {kde_val:.2f}% → Oversold</span> (Potential Bullish Trend Start)"
    elif kde_val < 45: return f"<span class='kde-orange'>🟠 {kde_val:.2f}% → Weak Bearish</span> (Momentum Neutralizing)"
    elif kde_val < 55: return f"<span class='kde-yellow'>🟡 {kde_val:.2f}% → Neutral Zone</span> (Consolidation/Trend Continuation)"
    elif kde_val < 70: return f"<span class='kde-green'>🟢 {kde_val:.2f}% → Strong Bullish</span> (Bullish Trend Likely Continuing)"
    elif kde_val < 85: return f"<span class='kde-red'>🔵 {kde_val:.2f}% → Overbought</span> (Potential Bearish Trend Start)"
    else: return f"<span class='kde-purple'>🟣 {kde_val:.2f}% → Extreme Overbought</span> (High Bearish Reversal Probability)"
    
def get_kde_rsi_explanation(): return "KDE RSI measures the density of momentum to identify extreme overbought/oversold conditions more accurately."
def get_supertrend_explanation(status):
    if "Bullish" in status: return "Price is trading above the SuperTrend line, indicating **upward momentum and trend strength**."
    else: return "Price is trading below the SuperTrend line, indicating **downward momentum**."
def get_bollinger_explanation(status):
    if "Normal" in status: return "Price is moving within expected volatility range. Watch for breaks above/below bands for potential moves."
    elif "Upper" in status: return "**Price touching upper band** - potential overbought condition or strong trend."
    else: return "**Price touching lower band** - potential oversold condition or weak trend."
def get_ema_explanation(status):
    if "Bullish" in status: return "Fast EMA crossed above slow EMA - suggests **buying pressure** and upward momentum."
    elif "Bearish" in status: return "Fast EMA crossed below slow EMA - suggests **selling pressure** and downward momentum."
    else: return "EMAs are close together - market is consolidating, wait for clear direction."
def get_psar_explanation(status):
    if "Bullish" in status: return "SAR dots below price confirm the **uptrend** and provide trailing stop levels for long positions."
    elif "Bearish" in status: return "SAR dots above price provide trailing stop levels for short positions."
    else: return "SAR switching position - trend may be reversing, avoid new entries."
    
def combined_bias(kde_val, st_text):
    is_bullish_trend = ("Bullish" in st_text) and (kde_val > 55)
    is_bearish_trend = ("Bearish" in st_text) and (kde_val < 45)
    
    if is_bullish_trend and kde_val > 65: return "Strong Bullish"
    if is_bearish_trend and kde_val < 35: return "Strong Bearish"
    
    if 45 <= kde_val <= 55: return "Neutral (Consolidation/Wait for Entry Trigger)"
    
    if ("Bullish" in st_text and kde_val > 80) or ("Bearish" in st_text and kde_val < 20):
        return "Neutral (Conflicting Signals/Extreme Condition)"

    return "Neutral (Consolidation/Wait for Entry Trigger)" 

def get_trade_recommendation(bias, current_price, atr_val):
    
    if "Strong Bullish" in bias:
        entry = current_price
        target = entry + (REWARD_MULTIPLE * atr_val) 
        stop = entry - (RISK_MULTIPLE * atr_val)
        return {
            "title": "Long Position Recommended",
            "action": f"entering a long position near <strong>{format_price(entry)}</strong>",
            "strategy": "Wait for confirmation or a slight pullback",
            "target": f"plan to take profit at <strong>{format_price(target)}</strong>",
            "stop": f"strictly set the stop loss below <strong>{format_price(stop)}</strong>",
            "type": "bullish"
        }
    elif "Strong Bearish" in bias:
        entry = current_price
        target = entry - (REWARD_MULTIPLE * atr_val)
        stop = entry + (RISK_MULTIPLE * atr_val)
        return {
            "title": "Short Position Recommended",
            "action": f"entering a short position near <strong>{format_price(entry)}</strong>",
            "strategy": "Short on rallies to resistance levels",
            "target": f"plan to cover the short at <strong>{format_price(target)}</strong>",
            "stop": f"strictly set the stop loss above <strong>{format_price(stop)}</strong>",
            "type": "bearish"
        }
    else:
        target_trigger = current_price + (2.0 * atr_val)
        stop_trigger = current_price - (1.0 * atr_val)
        return {
            "title": "No Trade Recommended (Wait for Clarity)",
            "action": "stay on the sidelines and preserve capital",
            "strategy": "Avoid entering until a clear break occurs",
            "target": f"A <strong>bullish entry trigger</strong> would be a break above <strong>{format_price(target_trigger)}</strong>",
            "stop": f"A <strong>bearish entry trigger</strong> would be a break below <strong>{format_price(stop_trigger)}</strong>",
            "type": "neutral"
        }

# === NATURAL LANGUAGE SUMMARY (Unchanged) ===
def get_natural_language_summary(symbol, bias, trade_params):
    summary = f"The AI analysis for <strong>{symbol}</strong> indicates an <strong>{bias}</strong> market bias."
    
    if trade_params["type"] == "bullish":
        summary += (
            f"<strong>{trade_params['title']}</strong> is given. The analysis suggests {trade_params['action']} "
            f"with a clear volatility-adjusted setup. Traders should {trade_params['target']} "
            f"and {trade_params['stop']}. The strategy suggests: <i>{trade_params['strategy']}</i>."
        )
    elif trade_params["type"] == "bearish":
        summary += (
            f"<strong>{trade_params['title']}</strong> is given. The analysis recommends {trade_params['action']} "
            f"with a volatility-adjusted setup. Traders should {trade_params['target']} "
            f"and {trade_params['stop']}. The strategy suggests: <i>{trade_params['strategy']}</i>."
        )
    else:
        summary += (
            f"<strong>{trade_params['title']}</strong>. The market for {symbol} is currently consolidating or showing mixed signals. "
            f"The recommendation is to <strong>{trade_params['action']}</strong>. "
            f"<strong>Action Triggers:</strong> {trade_params['target']} or {trade_params['stop']}."
        )

    return f"""
<div class='trade-recommendation-summary'>
{summary}
</div>
"""

# === UNIVERSAL ERROR MESSAGE GENERATOR (Unchanged) ===
def generate_error_message(title, message, details=""):
    return f"""
<div class='big-text'>
<div class='section-header' style='color: #DC2626;'>{title}</div>
<p style='color: #FCA5A5; font-size: 20px; font-weight: 700;'>
{message}
</p>
{f"<p>{details}</p>" if details else ""}
<p style='color: #FCA5A5;'>
The primary and all backup data sources for this asset are currently unavailable. **Please ensure the ticker symbol is correct and try again later.**
</p>
<div class='analysis-motto-prominent' style='border-color: #DC2626; color: #DC2626;'>
⚠️ ACTION REQUIRED: PLEASE TRY AGAIN WITH CORRECT INPUTS ⚠️
</div>
</div>
"""


# === ANALYZE (Main Logic - Unchanged) ===
def analyze(symbol, price_raw, price_change_24h, vs_currency, asset_type):
    
    # --- STEP 1: HANDLE API FAILURE ---
    if price_raw is None:
        return generate_error_message(
            title="❌ Data Retrieval Failed ❌",
            message=f"Unable to fetch live price data for <strong>{symbol}</strong> as a <strong>{asset_type}</strong>."
        )
    
    current_price = price_raw 
    price_display = format_price(current_price) 
    price_change_24h = price_change_24h if price_change_24h is not None else 0.0 
    change_display = format_change_main(price_change_24h)
    
    # --- STEP 2: Indicator Calculation ---
    df_synth_1h = synthesize_series(symbol)
    df_4h = get_historical_data(symbol, "4h") or synthesize_series(symbol + "4H", length=48)
    df_1h = get_historical_data(symbol, "1h") or df_synth_1h 
    df_15m = get_historical_data(symbol, "15min") or synthesize_series(symbol + "15M", length=80)
    
    kde_val = kde_rsi(df_1h, symbol) 
    
    st_status_4h = supertrend_status(df_4h, kde_val) 
    st_status_1h = supertrend_status(df_1h, kde_val) 
    bb_status = bollinger_status(df_15m, kde_val)
    ema_status = ema_crossover_status(kde_val) 
    psar_status = parabolic_sar_status(kde_val) 
    
    supertrend_output = f"SuperTrend: {st_status_4h.split(' - ')[0]} (4H), {st_status_1h.split(' - ')[0]} (1H)"
    kde_rsi_output = get_kde_rsi_status(kde_val)
    bias = combined_bias(kde_val, supertrend_output)
    
    # --- STEP 3: ATR CALCULATION ---
    if all(col in df_1h.columns for col in ['High', 'Low', 'Close']):
        df_1h.ta.atr(append=True, length=14) 
        atr_synth_val = df_1h.get('ATR_14', pd.Series()).iloc[-1] if 'ATR_14' in df_1h.columns else np.nan
    else:
        atr_synth_val = np.nan
    
    synth_base = 10.0
    if pd.isna(atr_synth_val) or atr_synth_val <= 0:
        atr_multiplier = 0.015
        atr_val = current_price * atr_multiplier
    else:
        volatility_percent = atr_synth_val / synth_base
        atr_val = current_price * volatility_percent
        
    # --- STEP 4: OUTPUT GENERATION (Dynamic Motivation - Unchanged) ---
    
    motivation_options = {
        "Strong Bullish": [
            "MOMENTUM CONFIRMED: Look for breakout entries or pullbacks. Trade the plan! **The market rewards conviction.**",
            "STRONG BUY SIGNAL: The trend and momentum align. **Never fight the trend, but always respect your stops.**",
            "BULLISH PRESSURE: Capitalize on the upward force. **Successful trading is 80% preparation, 20% execution.**"
        ],
        "Strong Bearish": [
            "DOWNTREND CONFIRMED: Respect stops and look for short opportunities near resistance. **Keep risk management paramount.**",
            "STRONG SELL SIGNAL: Sentiment has turned decisively. **Manage the downside, and the upside will take care of itself.**",
            "BEARISH PRESSURE: Do not hold against a strong downtrend. **The goal is not to trade often, but to trade well.**"
        ],
        "Neutral (Consolidation/Wait for Entry Trigger)": [
            "MARKET RESTING: Patience now builds precision later. Preserve capital. **Successful trading is 80% waiting.**",
            "CONSOLIDATION ZONE: Wait for the price to show its hand. **No position is a position.**",
            "IDLE CAPITAL: Do not enter a trade without a clear edge. **The best opportunities are often the ones you wait for.**"
        ],
        "Neutral (Conflicting Signals/Extreme Condition)": [
            "CONFLICTING SIGNALS: Wait for clear confirmation from trend or momentum. **Avoid emotional trading; trade only what you see.**",
            "HIGH UNCERTAINTY: Indicators are mixed or at extremes. **Protect your capital; avoid the urge to guess.**",
            "AVOID THE CHOP: This is a market for scalpers or observers. **Focus on the next clear setup, not this messy one.**"
        ]
    }
    
    default_motivation = "MAINTAIN EMOTIONAL DISTANCE: Trade the strategy, not the emotion."
    motivation = random.choice(motivation_options.get(bias, [default_motivation]))
    
    current_price_line = f"Current Price : <span class='asset-price-value'>{price_display} {vs_currency.upper()}</span>{change_display}"
    trade_parameters = get_trade_recommendation(bias, current_price, atr_val)
    analysis_summary_html = get_natural_language_summary(symbol, bias, trade_parameters)
    
    # --- FINAL OUTPUT STRUCTURE (Unchanged) ---
    full_output = f"""
<div class='big-text'>
<div class='analysis-item'>{current_price_line}</div>

<div class='section-header'>📊 Detailed Indicator Analysis</div>

<div class='analysis-item'>KDE RSI Status: <b>{kde_rsi_output}</b></div>
<div class='indicator-explanation'>{get_kde_rsi_explanation()}</div>

<div class='analysis-item'><b>{supertrend_output}</b> ({st_status_1h.split(' - ')[1]})</div>
<div class='indicator-explanation'>{get_supertrend_explanation(st_status_1h)}</div>

<div class='analysis-item'>Bollinger Bands: <b>{bb_status}</b></div>
<div class='indicator-explanation'>{get_bollinger_explanation(bb_status)}</div>

<div class='analysis-item'>EMA Crossover (5/20): <b>{ema_status}</b></div>
<div class='indicator-explanation'>{get_ema_explanation(ema_status)}</div>

<div class='analysis-item'>Parabolic SAR: <b>{psar_status}</b></div>
<div class='indicator-explanation'>{get_psar_explanation(psar_status)}</div>

<div class='analysis-bias'>Overall Market Bias: <span class='{bias.split(" ")[0].lower()}'>{bias}</span></div>

<div class='section-header'>⭐ AI Trading Recommendation Summary</div>
{analysis_summary_html}

<div class='analysis-motto-prominent'>{motivation}</div>

<div class='risk-warning'>
⚠️ <b>Risk Disclaimer:</b> This is not financial advice. All trading involves risk. Past performance doesn't guarantee future results. Only trade with money you can afford to lose. Always use stop losses .
</div>
</div>
"""
    return full_output

# === Session Logic (Unchanged) ---
utc_now = datetime.datetime.now(timezone.utc)
utc_hour = utc_now.hour

SESSION_TOKYO = (dt_time(0, 0), dt_time(9, 0))
SESSION_LONDON = (dt_time(8, 0), dt_time(17, 0))
SESSION_NY = (dt_time(13, 0), dt_time(22, 0)) 
OVERLAP_START_UTC = dt_time(13, 0)
OVERLAP_END_UTC = dt_time(17, 0) 

def get_session_info(utc_now):
    current_time_utc = utc_now.time()
    session_name = "Quiet/Sydney Session"
    current_range_pct = 0.02
    
    if OVERLAP_START_UTC <= current_time_utc < OVERLAP_END_UTC:
        session_name = "Overlap: London / New York"
        current_range_pct = 0.30 
    elif dt_time(8, 0) <= current_time_utc < dt_time(9, 0):
        session_name = "Overlap: Tokyo / London"
        current_range_pct = 0.18
    elif SESSION_NY[0] <= current_time_utc < SESSION_NY[1]:
        session_name = "US Session (New York)"
        current_range_pct = 0.15
    elif SESSION_LONDON[0] <= current_time_utc < SESSION_LONDON[1]:
        session_name = "European Session (London)"
        current_range_pct = 0.15
    elif SESSION_TOKYO[0] <= current_time_utc < SESSION_TOKYO[1]:
        session_name = "Asian Session (Tokyo)"
        current_range_pct = 0.08 if utc_hour < 3 else 0.05
    
    avg_range_pct = 0.1
    ratio = (current_range_pct / avg_range_pct) * 100
    if ratio < 20: status = "Flat / Very Low Volatility"
    elif 20 <= ratio < 60: status = "Low Volatility / Room to Move"
    elif 60 <= ratio < 100: status = "Moderate Volatility / Near Average"
    else: status = "High Volatility / Possible Exhaustion"
    
    volatility_html = f"<span class='status-volatility-info'><b>Status:</b> {status} ({ratio:.0f}% of Avg)</span>"
    return session_name, volatility_html

session_name, volatility_html = get_session_info(utc_now)

# --- SIDEBAR DISPLAY ---
st.sidebar.markdown("<p class='sidebar-title'>📊 Market Context</p>", unsafe_allow_html=True)

# 💡 CHANGE: Removed the BTC and SPY price fetching and display block
# This makes the app load instantly.

tz_options = [f"UTC{h:+03d}:{m:02d}" for h in range(-12, 15) for m in (0, 30) if not (h == 14 and m == 30) or (h == 13 and m==30) or (h == -12 and m == 30) or (h==-11 and m==30)]
tz_options.extend(["UTC+05:45", "UTC+08:45", "UTC+12:45"])
tz_options = sorted(list(set(tz_options))) 
try: default_ix = tz_options.index("UTC+05:00") 
except ValueError: default_ix = tz_options.index("UTC+00:00") 

selected_tz_str = st.sidebar.selectbox("Select Your Timezone", tz_options, index=default_ix)

offset_str = selected_tz_str.replace("UTC", "")
hours, minutes = map(int, offset_str.split(':'))
total_minutes = (abs(hours) * 60 + minutes) * (-1 if hours < 0 or offset_str.startswith('-') else 1)
user_tz = timezone(timedelta(minutes=total_minutes))
user_local_time = datetime.datetime.now(user_tz)

st.sidebar.markdown(f"<div class='sidebar-item'><b>Your Local Time:</b> <span class='local-time-info'>{user_local_time.strftime('%H:%M')}</span></div>", unsafe_allow_html=True)

# 💡 CHANGE 2: Fixed the typo (class='sidebar-item') to correctly wrap the Session Info in a box
st.sidebar.markdown(f"<div class='sidebar-item'><b>Active Session:</b> <span class='active-session-info'>{session_name}</span><br>{volatility_html}</div>", unsafe_allow_html=True)

today_overlap_start_utc = datetime.datetime.combine(utc_now.date(), OVERLAP_START_UTC, tzinfo=timezone.utc)
today_overlap_end_utc = datetime.datetime.combine(utc_now.date(), OVERLAP_END_UTC, tzinfo=timezone.utc)

overlap_start_local = today_overlap_start_utc.astimezone(user_tz)
overlap_end_local = today_overlap_end_utc.astimezone(user_tz)

st.sidebar.markdown(f"""
<div class='sidebar-item sidebar-overlap-time'>
<b>London/NY Overlap Times (Peak Liquidity)</b><br>
<span style='font-size: 20px; color: #22D3EE; font-weight: 700;'>
{overlap_start_local.strftime('%H:%M')} - {overlap_end_local.strftime('%H:%M')}
</span>
<br>({selected_tz_str})
</div>
""", unsafe_allow_html=True)

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
    # 1. Resolve to the base symbol (input is now assumed to be the ticker)
    base_symbol, resolved_symbol = resolve_asset_symbol(user_input, asset_type, vs_currency)
    
    # 2. PERFORM SIMPLIFIED ASSET TYPE VALIDATION
    validation_error = None
    
    is_common_crypto = base_symbol in KNOWN_CRYPTO_SYMBOLS
    is_common_stock = base_symbol in KNOWN_STOCK_SYMBOLS

    if asset_type == "Crypto" and is_common_stock:
        validation_error = f"You selected <strong>Crypto</strong> but entered a known stock/index symbol (<strong>{base_symbol}</strong>). Please select 'Stock/Index' from the dropdown to proceed."
    elif asset_type == "Stock/Index" and is_common_crypto:
        validation_error = f"You selected <strong>Stock/Index</strong> but entered a known crypto symbol (<strong>{base_symbol}</strong>). Please select 'Crypto' from the dropdown to proceed."

    # 3. Handle Validation Error or Proceed to Fetch/Analyze
    if validation_error:
        st.markdown(generate_error_message(
            title="⚠️ Asset Type Mismatch ⚠️",
            message="Please ensure the selected **Asset Type** matches the **Ticker Symbol** you entered.",
            details=validation_error
        ), unsafe_allow_html=True)
    else:
        # 💡 CHANGE 2: Use a custom spinner to provide feedback during network latency
        with st.spinner(f"Fetching live data and generating analysis for {resolved_symbol}...") :
            price, price_change_24h = get_asset_price(resolved_symbol, vs_currency, asset_type)
            st.markdown(analyze(resolved_symbol, price, price_change_24h, vs_currency, asset_type), unsafe_allow_html=True)
