import streamlit as st

import requests
import datetime
import pandas as pd
import numpy as np
import pytz
import time
from datetime import time as dt_time, timedelta, timezone
import ta
from ta.volatility import AverageTrueRange
from ta.trend import MACD, EMAIndicator, SMAIndicator, PSARIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import random
import json
from collections import defaultdict



# --- CONFIGURATION & CONSTANTS ---
# Risk-Reward Ratios with descriptions
RISK_REWARD_OPTIONS = {
    "1:1 (Conservative/Scalper)": (1.0, 1.0),
    "1:1.5 (Conservative/Swing Trader)": (1.0, 1.5),
    "1:2 (Moderate/Default)": (1.0, 2.0),
    "1:3 (Aggressive/Trend Trader)": (1.0, 3.0),
    "1:4 (Highly Aggressive/Position Trader)": (1.0, 4.0),
    "Custom": None  # Will be handled separately
} 

# --- STREAMLIT CONFIGURATION ---
st.set_page_config(page_title="AI Crypto Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === MAIN STYLES ===
st.markdown("""
<style>
/* Base Streamlit overrides */
header[data-testid="stHeader"], footer {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}

/* Main background */
[data-testid="stAppViewContainer"] {
    background: #1F2937;
    padding-left: 360px !important;
    padding-right: 25px;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: #111827;
    width: 340px !important; min-width: 340px !important;
    position: fixed !important; top: 0; left: 0; bottom: 0; z-index: 100;
    padding: 0.1rem 1.0rem 0.1rem 1.0rem; 
    border-right: 1px solid #1F2937;
    box-shadow: 8px 0 18px rgba(0,0,0,0.4);
}

/* Main content boxes */
.big-text {
    background: #111827;
    border: 1px solid #374151;
    border-radius: 16px;
    padding: 28px;
    margin-top: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

/* Price Header */
.price-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #1a2332;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 20px;
    border: 1px solid #374151;
    flex-wrap: wrap;
    gap: 12px;
}
.price-header .price-section .label {
    font-size: 13px;
    color: #9CA3AF;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.price-header .price-section .value {
    font-size: 30px;
    font-weight: 700;
    color: #F59E0B;
}
.price-header .price-section .value .currency {
    font-size: 16px;
    color: #9CA3AF;
    font-weight: 400;
}
.price-header .change-section {
    text-align: right;
}
.price-header .change-section .change {
    font-size: 20px;
    font-weight: 700;
}
.price-header .change-section .label {
    font-size: 13px;
    color: #9CA3AF;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.bias-badge {
    display: inline-block;
    padding: 8px 24px;
    border-radius: 50px;
    font-size: 20px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Indicator Cards */
.indicator-card {
    background: #1a2332;
    border-radius: 10px;
    padding: 16px 18px;
    border-left: 4px solid #374151;
    transition: all 0.2s ease;
    margin-bottom: 12px;
}
.indicator-card:hover {
    background: #1f2a3a;
    transform: translateX(3px);
}
.indicator-card .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2px;
}
.indicator-card .name {
    font-size: 13px;
    color: #9CA3AF;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.indicator-card .signal-badge {
    font-size: 13px;
    font-weight: 700;
    padding: 2px 12px;
    border-radius: 20px;
}
.indicator-card .value {
    font-size: 18px;
    font-weight: 700;
    color: #E5E7EB;
    margin: 2px 0;
}
.indicator-card .explanation {
    font-size: 13px;
    color: #9CA3AF;
    margin-top: 6px;
    line-height: 1.5;
}

/* Recommendation Box */
.recommendation-box {
    background: #1a2332;
    border-radius: 12px;
    padding: 20px 24px;
    margin-top: 20px;
    border: 1px solid #374151;
    border-left: 4px solid #60A5FA;
}
.recommendation-box .title {
    font-size: 18px;
    font-weight: 700;
    color: #60A5FA;
    margin-bottom: 8px;
}
.recommendation-box .content {
    font-size: 16px;
    line-height: 1.8;
    color: #E5E7EB;
}

/* Trade Summary */
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

/* Motivation */
.motivation-text {
    font-size: 15px;
    font-weight: 700;
    color: #F59E0B;
    text-align: center;
    padding: 12px 16px;
    margin-top: 16px;
    border: 2px solid #F59E0B;
    border-radius: 8px;
    background: rgba(245, 158, 11, 0.05);
}

/* Disclaimer */
.disclaimer {
    font-size: 12px;
    color: #6B7280;
    text-align: center;
    margin-top: 20px;
    padding-top: 14px;
    border-top: 1px solid #1F2937;
    line-height: 1.6;
}

/* Sidebar components */
.sidebar-title {
    font-size: 28px; font-weight: 800; color: #60A5FA; margin-top: 0px; margin-bottom: 5px;
    padding-top: 5px; text-shadow: 0 0 10px rgba(96, 165, 250, 0.3);
}
.sidebar-item {
    background: #1F2937; border-radius: 8px;
    padding: 8px 12px; margin: 4px 0; 
    font-size: 17px;
    color: #9CA3AF; border: 1px solid #374151;
}
.local-time-info { color: #00FFFF !important; font-weight: 700; }
.active-session-info { color: #FF8C00 !important; font-weight: 700; }
.status-volatility-info { color: #32CD32 !important; font-weight: 700; }

/* Colors */
.bullish { color: #10B981 !important; font-weight: 700; }
.bearish { color: #EF4444 !important; font-weight: 700; }
.neutral { color: #F59E0B !important; font-weight: 700; }

/* Responsive */
@media (max-width: 768px) {
    [data-testid="stAppViewContainer"] {
        padding-left: 0px !important;
    }
    [data-testid="stSidebar"] {
        width: 280px !important;
        min-width: 280px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# --- API KEYS from Streamlit secrets ---
FH_API_KEY = st.secrets.get("FINNHUB_API_KEY", "") 
FH_PRIVATE_API_KEY = st.secrets.get("FINNHUB_PRIVATE_API_KEY", "")
CG_PUBLIC_API_KEY = st.secrets.get("CG_PUBLIC_API_KEY", "") 

# Define crypto symbols
KNOWN_CRYPTO_SYMBOLS = {"BTC", "ETH", "ADA", "XRP", "DOGE", "SOL", "PI", "HYPE", "AVAX", "DOT", "LINK", "MATIC", "UNI", "ATOM", "LTC", "BCH", "NEAR", "ALGO", "VET", "ICP", "FIL", "EGLD", "XTZ", "AAVE", "MKR", "COMP", "YFI", "ZEC", "XLM", "HBAR", "ETC", "QNT", "GRT", "SNX", "STORJ", "ANKR", "CRV", "1INCH", "SUSHI", "UMA", "OCEAN", "REN", "ZRX", "BAT", "KNC", "ENJ", "CHR", "MANA", "SAND", "GALA", "AXS", "SLP", "ILV", "RNDR", "FET", "AGIX"}

# Timezone mapping
TIMEZONE_MAP = {
    "Pakistan (PKT)": "Asia/Karachi",
    "United States - New York (EST/EDT)": "America/New_York",
    "United States - Los Angeles (PST/PDT)": "America/Los_Angeles",
    "United Kingdom (GMT/BST)": "Europe/London",
    "France (CET/CEST)": "Europe/Paris",
    "Germany (CET/CEST)": "Europe/Berlin",
    "Japan (JST)": "Asia/Tokyo",
    "Singapore (SGT)": "Asia/Singapore",
    "Australia (AEST/AEDT)": "Australia/Sydney",
    "India (IST)": "Asia/Kolkata",
    "China (CST)": "Asia/Shanghai",
}

def resolve_asset_symbol(input_text, asset_type, quote_currency="USD"):
    base_symbol = input_text.strip().upper()
    if asset_type == "Crypto":
        final_symbol = base_symbol + quote_currency.upper()
    else:
        final_symbol = base_symbol
    return base_symbol, final_symbol

# === HELPERS FOR FORMATTING ===
def format_price(p):
    if p is None: return "N/A" 
    try: p = float(p)
    except Exception: return "N/A" 
    if abs(p) >= 10: s = f"{p:,.2f}"
    elif abs(p) >= 1: s = f"{p:,.4f}" 
    elif abs(p) >= 0.01: s = f"{p:.4f}"
    else: s = f"{p:.6f}"
    return s.rstrip("0").rstrip(".")

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
    except Exception:
        pass
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
    except Exception:
        pass
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
    except Exception:
        pass
    return None, None

# === UNIVERSAL PRICE FETCHER ===
@st.cache_data(ttl=60, show_spinner=False)
def get_asset_price(symbol, vs_currency="usd", asset_type="Crypto"):
    symbol = symbol.upper()
    
    if FH_PRIVATE_API_KEY:
        price, change = fetch_stock_price_finnhub(symbol, FH_PRIVATE_API_KEY)
        if price is not None:
            return price, change
    
    if FH_API_KEY:
        price, change = fetch_stock_price_finnhub(symbol, FH_API_KEY)
        if price is not None:
            return price, change
    
    price, change = fetch_crypto_price_binance(symbol)
    if price is not None:
        return price, change
    
    price, change = fetch_crypto_price_coingecko(symbol, CG_PUBLIC_API_KEY)
    if price is not None:
        return price, change
    
    return None, None

# === HISTORICAL DATA ===
def get_historical_data(symbol, interval="1h", limit=200):
    return synthesize_series(symbol, length=limit)

def synthesize_series(symbol, length=200, volatility_pct=0.008): 
    seed_val = int(hash(symbol) % (2**31 - 1))
    np.random.seed(seed_val) 
    base = 100.0
    returns = np.random.normal(0, volatility_pct, size=length)
    series = base * np.exp(np.cumsum(returns))
    volume = np.random.lognormal(mean=10, sigma=1, size=length) * 1000
    
    df = pd.DataFrame({
        "datetime": pd.date_range(end=datetime.datetime.utcnow(), periods=length, freq="h"),
        "Close": series, 
        "High": series * (1.002 + np.random.uniform(0, 0.001, size=length)), 
        "Low": series * (0.998 - np.random.uniform(0, 0.001, size=length)), 
        "Open": series * (1.0005 + np.random.uniform(-0.001, 0.001, size=length)),
        "Volume": volume
    })
    return df.iloc[-length:].set_index('datetime')

# === INDICATOR FUNCTIONS ===
def calculate_supertrend(df, period=10, multiplier=3):
    high = df['High']; low = df['Low']; close = df['Close']
    atr_indicator = AverageTrueRange(high=high, low=low, close=close, window=period)
    atr = atr_indicator.average_true_range()
    hl2 = (high + low) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    supertrend = pd.Series(index=df.index, dtype=float)
    trend = pd.Series(index=df.index, dtype=int)
    
    for i in range(period, len(df)):
        if i == period:
            if close.iloc[i] > upper_band.iloc[i]:
                trend.iloc[i] = 1; supertrend.iloc[i] = lower_band.iloc[i]
            else:
                trend.iloc[i] = -1; supertrend.iloc[i] = upper_band.iloc[i]
        else:
            if trend.iloc[i-1] == 1:
                if close.iloc[i] < lower_band.iloc[i]:
                    trend.iloc[i] = -1; supertrend.iloc[i] = upper_band.iloc[i]
                else:
                    trend.iloc[i] = 1; supertrend.iloc[i] = max(lower_band.iloc[i], supertrend.iloc[i-1])
            else:
                if close.iloc[i] > upper_band.iloc[i]:
                    trend.iloc[i] = 1; supertrend.iloc[i] = lower_band.iloc[i]
                else:
                    trend.iloc[i] = -1; supertrend.iloc[i] = min(upper_band.iloc[i], supertrend.iloc[i-1])
    
    current_trend = "Bullish" if trend.iloc[-1] == 1 else "Bearish"
    current_value = supertrend.iloc[-1]
    return {"status": current_trend, "value": current_value, "detail": f"SuperTrend line at ${format_price(current_value)}"}

def calculate_rsi_with_divergence(df, rsi_period=14, ma_period=9):
    close = df['Close']
    rsi_indicator = RSIIndicator(close=close, window=rsi_period)
    rsi = rsi_indicator.rsi()
    rsi_ma = rsi.rolling(window=ma_period).mean()
    current_rsi = rsi.iloc[-1]
    
    lookback = 20
    divergence = "No Divergence"
    if len(rsi) > lookback:
        rsi_array = rsi.iloc[-lookback:].values
        price_array = close.iloc[-lookback:].values
        price_highs = []; price_lows = []; rsi_highs = []; rsi_lows = []
        for i in range(2, len(price_array) - 2):
            if price_array[i] > price_array[i-1] and price_array[i] > price_array[i-2] and price_array[i] > price_array[i+1] and price_array[i] > price_array[i+2]:
                price_highs.append((i, price_array[i])); rsi_highs.append((i, rsi_array[i]))
            if price_array[i] < price_array[i-1] and price_array[i] < price_array[i-2] and price_array[i] < price_array[i+1] and price_array[i] < price_array[i+2]:
                price_lows.append((i, price_array[i])); rsi_lows.append((i, rsi_array[i]))
        if len(price_highs) >= 2 and price_highs[-1][1] > price_highs[-2][1] and rsi_highs[-1][1] < rsi_highs[-2][1]:
            divergence = "Bearish Divergence"
        if len(price_lows) >= 2 and price_lows[-1][1] < price_lows[-2][1] and rsi_lows[-1][1] > rsi_lows[-2][1]:
            divergence = "Bullish Divergence"
    
    if current_rsi > 70: status = "Overbought"
    elif current_rsi < 30: status = "Oversold"
    else: status = "Neutral"
    
    return {"status": status, "value": current_rsi, "detail": f"RSI: {current_rsi:.2f} | MA: {rsi_ma.iloc[-1]:.2f} | {divergence}"}

def calculate_bollinger_bands(df, period=20, std_dev=2):
    close = df['Close']
    bb_indicator = BollingerBands(close=close, window=period, window_dev=std_dev)
    upper = bb_indicator.bollinger_hband(); middle = bb_indicator.bollinger_mavg(); lower = bb_indicator.bollinger_lband()
    current_upper = upper.iloc[-1]; current_middle = middle.iloc[-1]; current_lower = lower.iloc[-1]
    band_width = (current_upper - current_lower) / current_middle
    
    historical_widths = []
    for i in range(period, len(close)):
        if not pd.isna(upper.iloc[i]) and not pd.isna(lower.iloc[i]) and not pd.isna(middle.iloc[i]):
            historical_widths.append((upper.iloc[i] - lower.iloc[i]) / middle.iloc[i])
    
    is_squeeze = False
    if len(historical_widths) >= 100 and band_width <= np.percentile(historical_widths, 20):
        is_squeeze = True
    
    detail = f"Upper: ${format_price(current_upper)} | Mid: ${format_price(current_middle)} | Lower: ${format_price(current_lower)}"
    if is_squeeze: detail += " | 🔥 SQUEEZE!"
    else: detail += f" | Width: {band_width:.3f}"
    
    return {"status": "Normal", "value": band_width, "detail": detail, "is_squeeze": is_squeeze}

def calculate_parabolic_sar(df, step=0.02, max_step=0.2):
    high = df['High']; low = df['Low']; close = df['Close']
    psar_indicator = PSARIndicator(high=high, low=low, close=close, step=step, max_step=max_step)
    psar = psar_indicator.psar()
    current_psar = psar.iloc[-1]
    
    if close.iloc[-1] > current_psar:
        status = "Bullish"; detail = f"SAR at ${format_price(current_psar)} — Below price"
    else:
        status = "Bearish"; detail = f"SAR at ${format_price(current_psar)} — Above price"
    
    is_reversal = False
    if len(psar) > 2:
        for i in range(1, min(3, len(psar))):
            if (psar.iloc[-i] > close.iloc[-i] and psar.iloc[-i-1] < close.iloc[-i-1]) or \
               (psar.iloc[-i] < close.iloc[-i] and psar.iloc[-i-1] > close.iloc[-i-1]):
                is_reversal = True; break
    
    if is_reversal: detail += " | ⚠️ REVERSAL!"
    return {"status": status, "value": current_psar, "detail": detail, "is_reversal": is_reversal}

def calculate_volume_profile(df, num_bins=25):
    if 'Volume' not in df.columns or df['Volume'].sum() == 0:
        high = df['High'].iloc[-100:] if len(df) > 100 else df['High']
        low = df['Low'].iloc[-100:] if len(df) > 100 else df['Low']
        return {"status": "Fallback", "value": (high.max() + low.min()) / 2, 
                "detail": f"Resistance: ${format_price(high.max())} | Support: ${format_price(low.min())}"}
    
    lookback = min(200, len(df))
    price = df['Close'].iloc[-lookback:]; volume = df['Volume'].iloc[-lookback:]
    price_min = price.min(); price_max = price.max()
    bins = np.linspace(price_min, price_max, num_bins + 1)
    bin_indices = np.digitize(price, bins) - 1
    
    volume_by_bin = defaultdict(float)
    for idx, vol in zip(bin_indices, volume):
        if 0 <= idx < num_bins: volume_by_bin[idx] += vol
    
    poc_bin = max(volume_by_bin, key=volume_by_bin.get)
    poc_price = (bins[poc_bin] + bins[poc_bin + 1]) / 2
    
    sorted_bins = sorted(volume_by_bin.items(), key=lambda x: x[1], reverse=True)[:3]
    top_prices = [(bins[bin_idx] + bins[bin_idx + 1]) / 2 for bin_idx, _ in sorted_bins]
    
    detail = f"POC: ${format_price(poc_price)}"
    if len(top_prices) > 1: detail += f" | Zone 2: ${format_price(top_prices[1])}"
    if len(top_prices) > 2: detail += f" | Zone 3: ${format_price(top_prices[2])}"
    
    return {"status": "Volume Profile", "value": poc_price, "detail": detail}

def calculate_all_indicators(symbol, df):
    try:
        return {
            "trend": calculate_supertrend(df),
            "momentum": calculate_rsi_with_divergence(df),
            "volatility": calculate_bollinger_bands(df),
            "reversal": calculate_parabolic_sar(df),
            "liquidity": calculate_volume_profile(df)
        }
    except Exception as e:
        return {
            "trend": {"status": "Error", "value": None, "detail": str(e)},
            "momentum": {"status": "Error", "value": None, "detail": "Error"},
            "volatility": {"status": "Error", "value": None, "detail": "Error"},
            "reversal": {"status": "Error", "value": None, "detail": "Error"},
            "liquidity": {"status": "Error", "value": None, "detail": "Error"}
        }

def determine_overall_bias(indicator_data):
    bullish = 0; bearish = 0
    if indicator_data["trend"]["status"] == "Bullish": bullish += 2
    elif indicator_data["trend"]["status"] == "Bearish": bearish += 2
    if indicator_data["momentum"]["status"] == "Overbought": bearish += 1
    elif indicator_data["momentum"]["status"] == "Oversold": bullish += 1
    if indicator_data["reversal"]["status"] == "Bullish": bullish += 1
    elif indicator_data["reversal"]["status"] == "Bearish": bearish += 1
    
    if bullish > bearish: return "Strong Bullish" if bullish - bearish >= 2 else "Bullish"
    elif bearish > bullish: return "Strong Bearish" if bearish - bullish >= 2 else "Bearish"
    return "Neutral"

# === SESSION LOGIC ===
def get_session_info(utc_now):
    current_time_utc = utc_now.time()
    utc_hour = utc_now.hour
    session_name = "Quiet/Sydney Session"
    current_range_pct = 0.02
    
    if dt_time(13, 0) <= current_time_utc < dt_time(17, 0):
        session_name = "Overlap: London / New York"
        current_range_pct = 0.30 
    elif dt_time(8, 0) <= current_time_utc < dt_time(9, 0):
        session_name = "Overlap: Tokyo / London"
        current_range_pct = 0.18
    elif dt_time(13, 0) <= current_time_utc < dt_time(22, 0):
        session_name = "US Session (New York)"
        current_range_pct = 0.15
    elif dt_time(8, 0) <= current_time_utc < dt_time(17, 0):
        session_name = "European Session (London)"
        current_range_pct = 0.15
    elif dt_time(0, 0) <= current_time_utc < dt_time(9, 0):
        session_name = "Asian Session (Tokyo)"
        current_range_pct = 0.08 if utc_hour < 3 else 0.05
    
    avg_range_pct = 0.1
    ratio = (current_range_pct / avg_range_pct) * 100
    if ratio < 20: status = "Flat / Very Low Volatility"
    elif 20 <= ratio < 60: status = "Low Volatility / Room to Move"
    elif 60 <= ratio < 100: status = "Moderate Volatility / Near Average"
    else: status = "High Volatility / Possible Exhaustion"
    
    return session_name, f"Status: {status} ({ratio:.0f}% of Avg)"

# === DISPLAY FUNCTIONS ===
def display_analysis(symbol, price, price_change, vs_currency, indicator_data, bias, risk_multiple, reward_multiple):
    
    # Get ATR for trade params
    df = get_historical_data(symbol)
    atr_indicator = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14)
    atr_val = atr_indicator.average_true_range().iloc[-1] * price / 100
    
    # Generate trade params
    if "Bullish" in bias:
        entry = price; target = entry + (reward_multiple * atr_val); stop = entry - (risk_multiple * atr_val)
        trade_params = {
            "title": "Long Position Recommended",
            "action": f"entering a long position near ${format_price(entry)}",
            "strategy": "Wait for confirmation or a slight pullback",
            "target": f"take profit at ${format_price(target)}",
            "stop": f"stop loss below ${format_price(stop)}",
            "type": "bullish"
        }
    elif "Bearish" in bias:
        entry = price; target = entry - (reward_multiple * atr_val); stop = entry + (risk_multiple * atr_val)
        trade_params = {
            "title": "Short Position Recommended",
            "action": f"entering a short position near ${format_price(entry)}",
            "strategy": "Short on rallies to resistance levels",
            "target": f"cover short at ${format_price(target)}",
            "stop": f"stop loss above ${format_price(stop)}",
            "type": "bearish"
        }
    else:
        target_trigger = price + (2.0 * atr_val); stop_trigger = price - (1.0 * atr_val)
        trade_params = {
            "title": "No Trade Recommended (Wait for Clarity)",
            "action": "stay on the sidelines and preserve capital",
            "strategy": "Avoid entering until a clear break occurs",
            "target": f"bullish trigger above ${format_price(target_trigger)}",
            "stop": f"bearish trigger below ${format_price(stop_trigger)}",
            "type": "neutral"
        }
    
    # Get bias color
    if "Bullish" in bias:
        bias_color = "#10B981"; bias_bg = "rgba(16, 185, 129, 0.15)"; bias_text = "BULLISH 📈"
    elif "Bearish" in bias:
        bias_color = "#EF4444"; bias_bg = "rgba(239, 68, 68, 0.15)"; bias_text = "BEARISH 📉"
    else:
        bias_color = "#F59E0B"; bias_bg = "rgba(245, 158, 11, 0.15)"; bias_text = "NEUTRAL ➡️"
    
    # Get indicator colors
    trend_color = "#10B981" if indicator_data["trend"]["status"] == "Bullish" else "#EF4444" if indicator_data["trend"]["status"] == "Bearish" else "#F59E0B"
    momentum_color = "#EF4444" if "Overbought" in indicator_data["momentum"]["status"] else "#10B981" if "Oversold" in indicator_data["momentum"]["status"] else "#F59E0B"
    volatility_color = "#F59E0B" if indicator_data["volatility"]["is_squeeze"] else "#60A5FA"
    reversal_color = "#EF4444" if indicator_data["reversal"]["is_reversal"] else "#10B981" if indicator_data["reversal"]["status"] == "Bullish" else "#F59E0B"
    
    # Motivation
    motivation_options = {
        "Strong Bullish": ["MOMENTUM CONFIRMED: Look for breakout entries or pullbacks."],
        "Bullish": ["BULLISH PRESSURE: Capitalize on the upward force."],
        "Strong Bearish": ["DOWNTREND CONFIRMED: Respect stops and look for short opportunities."],
        "Bearish": ["BEARISH PRESSURE: Do not hold against a strong downtrend."],
        "Neutral": ["MARKET RESTING: Patience now builds precision later."]
    }
    motivation = random.choice(motivation_options.get(bias, ["MAINTAIN EMOTIONAL DISTANCE"]))
    
    # --- DISPLAY USING STREAMLIT NATIVE COMPONENTS ---
    
    # Price Header
    col1, col2, col3 = st.columns([2, 1.5, 1.5])
    with col1:
        st.markdown("**Current Price**")
        st.markdown(f"<span style='font-size: 30px; font-weight: 700; color: #F59E0B;'>${format_price(price)}</span> <span style='color: #9CA3AF;'>{vs_currency.upper()}</span>", unsafe_allow_html=True)
    with col2:
        st.markdown("**24h Change**")
        change_class = "bullish" if price_change > 0 else "bearish"
        st.markdown(f"<span style='font-size: 20px; font-weight: 700;' class='{change_class}'>{'+' if price_change > 0 else ''}{price_change:.2f}%</span>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<span class='bias-badge' style='background: {bias_bg}; color: {bias_color}; border: 2px solid {bias_color};'>{bias_text}</span>", unsafe_allow_html=True)
    
    st.divider()
    
    # Indicator Grid - 2x2
    st.markdown("**Technical Indicators**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Trend
        with st.container():
            st.markdown(f"""
            <div class='indicator-card' style='border-left-color: {trend_color};'>
                <div class='card-header'>
                    <span class='name'>Trend — SuperTrend</span>
                    <span class='signal-badge' style='background: {trend_color}22; color: {trend_color};'>{indicator_data['trend']['status']}</span>
                </div>
                <div class='value'>{indicator_data['trend']['status']}</div>
                <div class='explanation'>{indicator_data['trend']['detail']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Volatility
        with st.container():
            squeeze_text = "🔥 SQUEEZE" if indicator_data['volatility']['is_squeeze'] else "NORMAL"
            squeeze_color = "#F59E0B" if indicator_data['volatility']['is_squeeze'] else "#60A5FA"
            st.markdown(f"""
            <div class='indicator-card' style='border-left-color: {volatility_color};'>
                <div class='card-header'>
                    <span class='name'>Volatility — Bollinger Bands</span>
                    <span class='signal-badge' style='background: {squeeze_color}22; color: {squeeze_color};'>{squeeze_text}</span>
                </div>
                <div class='value'>{'Squeeze Detected!' if indicator_data['volatility']['is_squeeze'] else 'Normal Volatility'}</div>
                <div class='explanation'>{indicator_data['volatility']['detail']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Momentum
        with st.container():
            st.markdown(f"""
            <div class='indicator-card' style='border-left-color: {momentum_color};'>
                <div class='card-header'>
                    <span class='name'>Momentum — RSI</span>
                    <span class='signal-badge' style='background: {momentum_color}22; color: {momentum_color};'>{indicator_data['momentum']['status']}</span>
                </div>
                <div class='value'>RSI: {indicator_data['momentum']['value']:.2f}</div>
                <div class='explanation'>{indicator_data['momentum']['detail']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Reversal
        with st.container():
            reversal_label = "⚠️ REVERSAL" if indicator_data['reversal']['is_reversal'] else indicator_data['reversal']['status']
            reversal_color_display = "#EF4444" if indicator_data['reversal']['is_reversal'] else reversal_color
            st.markdown(f"""
            <div class='indicator-card' style='border-left-color: {reversal_color_display};'>
                <div class='card-header'>
                    <span class='name'>Reversal — Parabolic SAR</span>
                    <span class='signal-badge' style='background: {reversal_color_display}22; color: {reversal_color_display};'>{reversal_label}</span>
                </div>
                <div class='value'>{'Reversal Imminent!' if indicator_data['reversal']['is_reversal'] else indicator_data['reversal']['status']}</div>
                <div class='explanation'>{indicator_data['reversal']['detail']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Liquidity - Full width
    st.markdown(f"""
    <div class='indicator-card' style='border-left-color: #C084FC; margin-top: 12px;'>
        <div class='card-header'>
            <span class='name'>Liquidity — Volume Profile</span>
            <span class='signal-badge' style='background: #C084FC22; color: #C084FC;'>POC</span>
        </div>
        <div class='value'>POC: ${format_price(indicator_data['liquidity']['value'])}</div>
        <div class='explanation'>{indicator_data['liquidity']['detail']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # AI Recommendation
    with st.container():
        st.markdown(f"""
        <div class='recommendation-box'>
            <div class='title'>⭐ AI Trading Recommendation</div>
            <div class='content'>
                <strong>{trade_params['title']}</strong><br>
                {trade_params['action']}<br>
                <strong>Target:</strong> {trade_params['target']}<br>
                <strong>Stop Loss:</strong> {trade_params['stop']}<br>
                <strong>Strategy:</strong> {trade_params['strategy']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Natural Language Summary
    summary = f"The AI analysis for <strong>{symbol}</strong> indicates an <strong>{bias}</strong> market bias."
    summary += "<br><br><strong>📊 Indicator Breakdown:</strong><br>"
    summary += f"• <strong>Trend (SuperTrend):</strong> {indicator_data['trend']['status']} — {indicator_data['trend']['detail']}<br>"
    summary += f"• <strong>Momentum (RSI):</strong> {indicator_data['momentum']['status']} — {indicator_data['momentum']['detail']}<br>"
    summary += f"• <strong>Volatility (Bollinger):</strong> {indicator_data['volatility']['detail']}<br>"
    summary += f"• <strong>Reversal (Parabolic SAR):</strong> {indicator_data['reversal']['detail']}<br>"
    summary += f"• <strong>Liquidity (Volume Profile):</strong> {indicator_data['liquidity']['detail']}"
    
    st.markdown(f"""
    <div class='trade-recommendation-summary'>
    {summary}
    </div>
    """, unsafe_allow_html=True)
    
    # Motivation
    st.markdown(f"<div class='motivation-text'>{motivation}</div>", unsafe_allow_html=True)
    
    # Disclaimer
    st.markdown("""
    <div class='disclaimer'>
        <strong>⚠️ Risk Disclaimer:</strong> This is not financial advice. All trading involves risk. 
        Past performance doesn't guarantee future results. Only trade with money you can afford to lose. 
        Always use stop losses.
    </div>
    """, unsafe_allow_html=True)

# === SIDEBAR ===
utc_now = datetime.datetime.now(timezone.utc)
session_name, volatility_html = get_session_info(utc_now)

st.sidebar.markdown("<p class='sidebar-title'>📊 Crypto Market Context</p>", unsafe_allow_html=True)

tz_city_names = sorted(TIMEZONE_MAP.keys())
try: default_ix = tz_city_names.index("Pakistan (PKT)")
except ValueError: default_ix = 0

selected_tz_name = st.sidebar.selectbox("Select Your Timezone", tz_city_names, index=default_ix)
selected_tz_pytz = pytz.timezone(TIMEZONE_MAP[selected_tz_name])
user_local_time = datetime.datetime.now(selected_tz_pytz)

st.sidebar.markdown(f"<div class='sidebar-item'><b>Your Local Time:</b> <span class='local-time-info'>{user_local_time.strftime('%H:%M')}</span></div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='sidebar-item'><b>Active Session:</b> <span class='active-session-info'>{session_name}</span><br><span class='status-volatility-info'>{volatility_html}</span></div>", unsafe_allow_html=True)

today_overlap_start = datetime.datetime.combine(utc_now.date(), dt_time(13, 0), tzinfo=timezone.utc)
today_overlap_end = datetime.datetime.combine(utc_now.date(), dt_time(17, 0), tzinfo=timezone.utc)
overlap_start_local = today_overlap_start.astimezone(selected_tz_pytz)
overlap_end_local = today_overlap_end.astimezone(selected_tz_pytz)

st.sidebar.markdown(f"""
<div class='sidebar-item'>
<b>London/NY Overlap Times (Peak Liquidity)</b><br>
<span style='font-size: 20px; color: #22D3EE; font-weight: 700;'>
{overlap_start_local.strftime('%H:%M')} - {overlap_end_local.strftime('%H:%M')}
</span>
<br>({selected_tz_name})
</div>
""", unsafe_allow_html=True)

# === MAIN EXECUTION ===
st.title("🤖 AI Crypto Trading Chatbot")

col1, col2, col3 = st.columns([1.5, 2.5, 1.5])

with col1:
    st.markdown("**Select Asset Type**")
    st.markdown("💰 Crypto")

with col2:
    user_input = st.text_input(
        "Enter Cryptocurrency Ticker",
        placeholder="e.g., BTC, ETH, SOL, ADA, DOGE",
        label_visibility="visible",
        help="Enter any crypto ticker symbol"
    )

with col3:
    show_indicator_details = st.checkbox("Show Indicator Details", value=False)

# Risk-Reward Ratio Selection
st.markdown("<div style='margin-top: 15px; margin-bottom: 10px;'></div>", unsafe_allow_html=True)
col_rr1, col_rr2, col_rr3 = st.columns([2, 2, 2])

with col_rr1:
    rr_selection = st.selectbox(
        "Select Risk:Reward Ratio Profile",
        list(RISK_REWARD_OPTIONS.keys()),
        index=2
    )

with col_rr2:
    if rr_selection == "Custom":
        custom_risk = st.number_input("Risk Multiple", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
    else:
        custom_risk = None
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

with col_rr3:
    if rr_selection == "Custom":
        custom_reward = st.number_input("Reward Multiple", min_value=0.1, max_value=10.0, value=2.0, step=0.1)
    else:
        custom_reward = None
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

if rr_selection == "Custom":
    RISK_MULTIPLE = custom_risk if custom_risk else 1.0
    REWARD_MULTIPLE = custom_reward if custom_reward else 2.0
else:
    RISK_MULTIPLE, REWARD_MULTIPLE = RISK_REWARD_OPTIONS[rr_selection]

vs_currency = "usd"
if user_input:
    asset_type = "Crypto"
    base_symbol, resolved_symbol = resolve_asset_symbol(user_input, asset_type, vs_currency)
    
    with st.spinner(f"Fetching live data and generating analysis for {resolved_symbol}..."):
        price, price_change = get_asset_price(resolved_symbol, vs_currency, asset_type)
        
        if price is not None:
            df = get_historical_data(resolved_symbol)
            indicator_data = calculate_all_indicators(resolved_symbol, df)
            bias = determine_overall_bias(indicator_data)
            
            display_analysis(
                resolved_symbol, price, price_change, vs_currency,
                indicator_data, bias, RISK_MULTIPLE, REWARD_MULTIPLE
            )
        else:
            st.error(f"❌ Unable to fetch price data for {resolved_symbol}. Please check the ticker symbol and try again.")
