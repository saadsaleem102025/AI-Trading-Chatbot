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
from ta.trend import PSARIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import random
from collections import defaultdict



# --- DEMO MODE FLAG ---
DEMO_MODE = True  # Set to False for full version

# --- CONFIGURATION ---
RISK_REWARD_OPTIONS = {
    "1:1 (Conservative/Scalper)": (1.0, 1.0),
    "1:1.5 (Conservative/Swing Trader)": (1.0, 1.5),
    "1:2 (Moderate/Default)": (1.0, 2.0),
    "1:3 (Aggressive/Trend Trader)": (1.0, 3.0),
    "1:4 (Highly Aggressive/Position Trader)": (1.0, 4.0),
    "Custom": None
} 

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Crypto Market Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- API KEYS ---
CG_PUBLIC_API_KEY = st.secrets.get("CG_PUBLIC_API_KEY", "") 

# --- STYLES ---
st.markdown("""
<style>
* {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
}

header[data-testid="stHeader"], footer {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}

[data-testid="stAppViewContainer"] {
    background: #0f1724;
    padding-left: 360px !important;
    padding-right: 25px;
}

[data-testid="stSidebar"] {
    background: #0d1520;
    width: 340px !important;
    min-width: 340px !important;
    position: fixed !important;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 100;
    padding: 0.5rem 1.2rem;
    border-right: 1px solid rgba(96, 165, 250, 0.1);
}

.sidebar-title {
    font-size: 24px;
    font-weight: 700;
    color: #60A5FA;
    margin-top: 5px;
    margin-bottom: 15px;
}
.sidebar-item {
    background: rgba(31, 41, 55, 0.5);
    border-radius: 10px;
    padding: 10px 14px;
    margin: 6px 0;
    font-size: 15px;
    color: #D1D5DB;
    border: 1px solid rgba(55, 65, 81, 0.3);
}
.local-time-info { color: #22D3EE !important; font-weight: 700; font-size: 18px; }
.active-session-info { color: #FBBF24 !important; font-weight: 700; font-size: 18px; }

.main-title {
    font-size: 28px;
    font-weight: 700;
    color: #E5E7EB;
    margin-bottom: 20px;
}

.price-card {
    background: #1a2332;
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid rgba(55, 65, 81, 0.3);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 20px;
}
.price-card .price-section .label {
    font-size: 12px;
    color: #9CA3AF;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.price-card .price-section .value {
    font-size: 32px;
    font-weight: 700;
    color: #F59E0B;
}
.price-card .price-section .value .currency {
    font-size: 16px;
    color: #9CA3AF;
    font-weight: 400;
}
.price-card .change-section .label {
    font-size: 12px;
    color: #9CA3AF;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.price-card .change-section .change {
    font-size: 22px;
    font-weight: 700;
}
.bias-badge {
    display: inline-block;
    padding: 8px 24px;
    border-radius: 50px;
    font-size: 18px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.section-header {
    font-size: 14px;
    color: #9CA3AF;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
}

.indicator-card {
    background: #1a2332;
    border-radius: 10px;
    padding: 16px 18px;
    border-left: 4px solid #374151;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    margin-bottom: 12px;
}
.indicator-card .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}
.indicator-card .name {
    font-size: 12px;
    color: #9CA3AF;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.indicator-card .signal-badge {
    font-size: 12px;
    font-weight: 700;
    padding: 2px 12px;
    border-radius: 20px;
}
.indicator-card .value {
    font-size: 18px;
    font-weight: 700;
    color: #E5E7EB;
    margin: 4px 0 2px 0;
}
.indicator-card .explanation {
    font-size: 13px;
    color: #9CA3AF;
    margin-top: 4px;
    line-height: 1.5;
}

.indicator-card-full {
    background: #1a2332;
    border-radius: 10px;
    padding: 16px 18px;
    border-left: 4px solid #8B5CF6;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    margin-top: 12px;
}
.indicator-card-full .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}
.indicator-card-full .name {
    font-size: 12px;
    color: #9CA3AF;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.indicator-card-full .signal-badge {
    font-size: 12px;
    font-weight: 700;
    padding: 2px 12px;
    border-radius: 20px;
}
.indicator-card-full .value {
    font-size: 18px;
    font-weight: 700;
    color: #E5E7EB;
    margin: 4px 0 2px 0;
}
.indicator-card-full .explanation {
    font-size: 13px;
    color: #9CA3AF;
    margin-top: 4px;
    line-height: 1.5;
}

.recommendation-box {
    background: #1a2332;
    border-radius: 12px;
    padding: 20px 24px;
    margin-top: 16px;
    border: 1px solid rgba(55, 65, 81, 0.3);
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
.recommendation-box .content strong {
    color: #F59E0B;
}
.recommendation-box .trigger-pending {
    color: #FBBF24;
    font-weight: 700;
}
.recommendation-box .trigger-hit {
    color: #34D399;
    font-weight: 700;
}
.recommendation-box .current-price-label {
    color: #9CA3AF;
    font-weight: 400;
}

.demo-notice {
    background: rgba(251, 191, 36, 0.08);
    border: 1px solid rgba(251, 191, 36, 0.15);
    border-radius: 8px;
    padding: 12px 16px;
    margin-top: 8px;
    font-size: 14px;
    color: #D1D5DB;
}
.demo-notice strong {
    color: #FBBF24;
}

.disclaimer {
    font-size: 12px;
    color: #6B7280;
    text-align: center;
    margin-top: 20px;
    padding-top: 14px;
    border-top: 1px solid rgba(55, 65, 81, 0.2);
    line-height: 1.6;
}

.bullish { color: #34D399 !important; font-weight: 700; }
.bearish { color: #F87171 !important; font-weight: 700; }
.neutral { color: #FBBF24 !important; font-weight: 700; }

.stMarkdown p, .stMarkdown div {
    color: #E5E7EB !important;
}
.stTextInput label, .stSelectbox label, .stCheckbox label {
    color: #9CA3AF !important;
    font-weight: 500 !important;
}
.stTextInput input {
    background-color: #1a2332 !important;
    color: #E5E7EB !important;
    border: 1px solid rgba(55, 65, 81, 0.3) !important;
}
.stSelectbox div[data-baseweb="select"] {
    background-color: #1a2332 !important;
}

@media (max-width: 768px) {
    [data-testid="stAppViewContainer"] {
        padding-left: 0px !important;
        padding-right: 15px !important;
    }
    .indicator-grid {
        grid-template-columns: 1fr;
    }
    .price-card {
        flex-direction: column;
        align-items: flex-start;
    }
    .main-title {
        font-size: 22px;
    }
}
</style>
""", unsafe_allow_html=True)

# --- CONSTANTS ---
TIMEZONE_MAP = {
    "Pakistan (PKT)": "Asia/Karachi",
    "UTC": "UTC",
    "US Eastern (ET)": "America/New_York",
    "UK (GMT/BST)": "Europe/London",
    "Japan (JST)": "Asia/Tokyo",
    "Singapore (SGT)": "Asia/Singapore",
    "UAE (GST)": "Asia/Dubai",
    "India (IST)": "Asia/Kolkata",
}

# --- FULL COIN MAP (commented for demo, uncomment for paid version) ---
# FULL_COIN_MAP = {
#     'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
#     'ADA': 'cardano', 'XRP': 'ripple', 'DOGE': 'dogecoin',
#     'DOT': 'polkadot', 'LINK': 'chainlink', 'MATIC': 'polygon',
#     'UNI': 'uniswap', 'ATOM': 'cosmos', 'LTC': 'litecoin',
#     'BCH': 'bitcoin-cash', 'NEAR': 'near', 'ALGO': 'algorand',
#     'AVAX': 'avalanche-2', 'FTM': 'fantom'
# }

# --- DEMO COIN MAP (only 3 coins) ---
DEMO_COIN_MAP = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'SOL': 'solana',
}

def format_price(p):
    if p is None: return "N/A" 
    try: p = float(p)
    except: return "N/A" 
    if abs(p) >= 10: return f"{p:,.2f}"
    elif abs(p) >= 1: return f"{p:,.4f}" 
    else: return f"{p:.6f}".rstrip("0").rstrip(".")

# --- COINGECKO API ---
def get_coin_id(symbol):
    """Map symbol to CoinGecko coin ID - uses demo or full map based on DEMO_MODE"""
    symbol = symbol.upper().replace("USD", "").replace("USDT", "")
    
    if DEMO_MODE:
        return DEMO_COIN_MAP.get(symbol, symbol.lower())
    else:
        # Full map would be used here
        return symbol.lower()

@st.cache_data(ttl=60, show_spinner=False)
def fetch_crypto_price_coingecko(symbol, api_key=""):
    """Fetch current price from CoinGecko"""
    coin_id = get_coin_id(symbol)
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': coin_id, 
        'vs_currencies': 'usd', 
        'include_24hr_change': 'true'
    }
    headers = {}
    if api_key:
        headers['x-cg-demo-api-key'] = api_key
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        if coin_id in data and 'usd' in data[coin_id]:
            price = float(data[coin_id]['usd'])
            change_percent = float(data[coin_id].get('usd_24h_change', 0))
            return price, change_percent
    except Exception as e:
        pass
    return None, None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_historical_data_coingecko(symbol, days=30, api_key=""):
    """Fetch REAL historical OHLC data from CoinGecko"""
    coin_id = get_coin_id(symbol)
    
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    
    if days <= 1:
        interval = '1m'
    elif days <= 30:
        interval = '1h'
    elif days <= 90:
        interval = '4h'
    else:
        interval = '1d'
    
    params = {
        'vs_currency': 'usd',
        'days': days,
    }
    
    headers = {}
    if api_key:
        headers['x-cg-demo-api-key'] = api_key
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        data = response.json()
        
        if not data or len(data) < 10:
            st.error(f"Insufficient historical data returned for {symbol}. Please try again.")
            return None
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        
        df = df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close'
        })
        
        df = df.sort_index()
        
        return df
        
    except requests.exceptions.Timeout:
        st.error("⏱️ Historical data request timed out. Please try again.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"🌐 Network error fetching historical data: {str(e)}")
        return None
    except Exception as e:
        st.error(f"❌ Error fetching historical data: {str(e)}")
        return None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_volume_data_coingecko(symbol, days=30, api_key=""):
    """Fetch REAL volume data from CoinGecko"""
    coin_id = get_coin_id(symbol)
    
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {
        'vs_currency': 'usd',
        'days': days,
    }
    
    headers = {}
    if api_key:
        headers['x-cg-demo-api-key'] = api_key
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        data = response.json()
        
        if not data or 'total_volumes' not in data or not data['total_volumes']:
            return None
        
        volume_data = data['total_volumes']
        df_volume = pd.DataFrame(volume_data, columns=['timestamp', 'Volume'])
        df_volume['timestamp'] = pd.to_datetime(df_volume['timestamp'], unit='ms')
        df_volume = df_volume.set_index('timestamp')
        
        return df_volume
        
    except Exception:
        return None

def merge_ohlc_with_volume(df_ohlc, df_volume):
    """Merge OHLC data with volume data by timestamp alignment"""
    if df_ohlc is None or df_volume is None:
        return df_ohlc
    
    df = df_ohlc.copy()
    df['Volume'] = df_volume['Volume'].reindex(df.index, method='nearest')
    
    if df['Volume'].isna().any():
        median_volume = df['Volume'].median()
        df['Volume'] = df['Volume'].fillna(median_volume)
    
    return df

def get_asset_price(symbol):
    """Get current price from CoinGecko"""
    return fetch_crypto_price_coingecko(symbol, CG_PUBLIC_API_KEY)

def get_historical_data(symbol, days=30):
    """Get REAL historical data with volume"""
    df_ohlc = fetch_historical_data_coingecko(symbol, days, CG_PUBLIC_API_KEY)
    
    if df_ohlc is None or len(df_ohlc) < 10:
        return None
    
    df_volume = fetch_volume_data_coingecko(symbol, days, CG_PUBLIC_API_KEY)
    
    if df_volume is not None:
        df = merge_ohlc_with_volume(df_ohlc, df_volume)
    else:
        df = df_ohlc.copy()
        df['Volume'] = None
    
    return df

# --- SWING POINT DETECTION ---
def find_swing_points(df, lookback=30):
    if df is None or len(df) < lookback:
        return None, None
    
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    if len(close) > lookback:
        price_array = close.iloc[-lookback:].values
        high_array = high.iloc[-lookback:].values
        low_array = low.iloc[-lookback:].values
    else:
        price_array = close.values
        high_array = high.values
        low_array = low.values
    
    swing_highs = []
    swing_lows = []
    
    for i in range(2, len(price_array) - 1):
        is_swing_high = (
            i >= 2 and i <= len(price_array) - 2 and
            price_array[i] > price_array[i-1] and price_array[i] > price_array[i-2] and
            price_array[i] > price_array[i+1]
        )
        
        is_swing_low = (
            i >= 2 and i <= len(price_array) - 2 and
            price_array[i] < price_array[i-1] and price_array[i] < price_array[i-2] and
            price_array[i] < price_array[i+1]
        )
        
        if is_swing_high:
            swing_highs.append(price_array[i])
        if is_swing_low:
            swing_lows.append(price_array[i])
    
    resistance = swing_highs[-1] if swing_highs else None
    support = swing_lows[-1] if swing_lows else None
    
    if resistance is None:
        resistance = max(high_array[-5:])
    if support is None:
        support = min(low_array[-5:])
    
    return resistance, support

# --- INDICATOR FUNCTIONS ---
def calculate_supertrend(df, period=10, multiplier=3):
    if df is None or len(df) < period:
        return {"status": "Error", "value": None, "detail": "Insufficient data"}
    
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
                trend.iloc[i] = 1
                supertrend.iloc[i] = lower_band.iloc[i]
            else:
                trend.iloc[i] = -1
                supertrend.iloc[i] = upper_band.iloc[i]
        else:
            if trend.iloc[i-1] == 1:
                if close.iloc[i] < lower_band.iloc[i]:
                    trend.iloc[i] = -1
                    supertrend.iloc[i] = upper_band.iloc[i]
                else:
                    trend.iloc[i] = 1
                    supertrend.iloc[i] = max(lower_band.iloc[i], supertrend.iloc[i-1])
            else:
                if close.iloc[i] > upper_band.iloc[i]:
                    trend.iloc[i] = 1
                    supertrend.iloc[i] = lower_band.iloc[i]
                else:
                    trend.iloc[i] = -1
                    supertrend.iloc[i] = min(upper_band.iloc[i], supertrend.iloc[i-1])
    
    current_trend = "Bullish" if trend.iloc[-1] == 1 else "Bearish"
    current_value = supertrend.iloc[-1]
    
    return {
        "status": current_trend,
        "value": current_value,
        "detail": f"SuperTrend line at ${format_price(current_value)}" if not DEMO_MODE else "SuperTrend: " + current_trend
    }

def calculate_rsi_with_divergence(df, rsi_period=14, ma_period=9):
    if df is None or len(df) < rsi_period + ma_period:
        return {"status": "Error", "value": None, "detail": "Insufficient data"}
    
    close = df['Close']
    
    rsi_indicator = RSIIndicator(close=close, window=rsi_period)
    rsi = rsi_indicator.rsi()
    rsi_ma = rsi.rolling(window=ma_period).mean()
    
    current_rsi = rsi.iloc[-1]
    current_rsi_ma = rsi_ma.iloc[-1]
    
    lookback = 30
    divergence = "No Divergence"
    
    if len(rsi) > lookback:
        rsi_array = rsi.iloc[-lookback:].values
        price_array = close.iloc[-lookback:].values
        
        price_highs = []; price_lows = []; rsi_highs = []; rsi_lows = []
        
        for i in range(2, len(price_array) - 1):
            is_swing_high = (
                i >= 2 and i <= len(price_array) - 2 and
                price_array[i] > price_array[i-1] and price_array[i] > price_array[i-2] and
                price_array[i] > price_array[i+1]
            )
            is_swing_low = (
                i >= 2 and i <= len(price_array) - 2 and
                price_array[i] < price_array[i-1] and price_array[i] < price_array[i-2] and
                price_array[i] < price_array[i+1]
            )
            
            if is_swing_high:
                price_highs.append((i, price_array[i]))
                rsi_highs.append((i, rsi_array[i]))
            if is_swing_low:
                price_lows.append((i, price_array[i]))
                rsi_lows.append((i, rsi_array[i]))
        
        if len(price_highs) >= 2 and price_highs[-1][1] > price_highs[-2][1] and rsi_highs[-1][1] < rsi_highs[-2][1]:
            divergence = "Bearish Divergence"
        if len(price_lows) >= 2 and price_lows[-1][1] < price_lows[-2][1] and rsi_lows[-1][1] > rsi_lows[-2][1]:
            divergence = "Bullish Divergence"
    
    if current_rsi > 70:
        status = "Overbought"
    elif current_rsi < 30:
        status = "Oversold"
    else:
        status = "Neutral"
    
    return {
        "status": status,
        "value": current_rsi,
        "detail": f"RSI: {status}" if DEMO_MODE else f"RSI: {current_rsi:.2f} | MA: {current_rsi_ma:.2f} | {divergence}"
    }

def calculate_bollinger_bands(df, period=20, std_dev=2):
    if df is None or len(df) < period:
        return {"status": "Error", "value": None, "detail": "Insufficient data"}
    
    close = df['Close']
    
    bb_indicator = BollingerBands(close=close, window=period, window_dev=std_dev)
    upper = bb_indicator.bollinger_hband()
    middle = bb_indicator.bollinger_mavg()
    lower = bb_indicator.bollinger_lband()
    
    current_upper = upper.iloc[-1]
    current_middle = middle.iloc[-1]
    current_lower = lower.iloc[-1]
    current_close = close.iloc[-1]
    
    band_width = (current_upper - current_lower) / current_middle
    
    historical_widths = []
    for i in range(period, len(close)):
        if not pd.isna(upper.iloc[i]) and not pd.isna(lower.iloc[i]) and not pd.isna(middle.iloc[i]):
            width = (upper.iloc[i] - lower.iloc[i]) / middle.iloc[i]
            historical_widths.append(width)
    
    is_squeeze = False
    if len(historical_widths) >= 100:
        percentile_20 = np.percentile(historical_widths, 20)
        if band_width <= percentile_20:
            is_squeeze = True
    
    if current_close > current_upper:
        position = "Above Upper Band"
    elif current_close < current_lower:
        position = "Below Lower Band"
    else:
        position = "Within Bands"
    
    if is_squeeze:
        status = "Squeeze"
        detail = f"🔥 SQUEEZE DETECTED" if DEMO_MODE else f"🔥 SQUEEZE! {position} | Width: {band_width:.3f}"
    else:
        status = "Normal"
        detail = f"Bollinger: {position}" if DEMO_MODE else f"{position} | Upper: ${format_price(current_upper)} | Mid: ${format_price(current_middle)} | Lower: ${format_price(current_lower)}"
    
    return {
        "status": status,
        "value": band_width,
        "detail": detail,
        "is_squeeze": is_squeeze,
        "upper": current_upper,
        "middle": current_middle,
        "lower": current_lower,
        "position": position
    }

def calculate_parabolic_sar(df, step=0.02, max_step=0.2):
    if df is None or len(df) < 10:
        return {"status": "Error", "value": None, "detail": "Insufficient data"}
    
    high = df['High']; low = df['Low']; close = df['Close']
    
    psar_indicator = PSARIndicator(high=high, low=low, close=close, step=step, max_step=max_step)
    psar = psar_indicator.psar()
    
    current_psar = psar.iloc[-1]
    current_close = close.iloc[-1]
    
    if current_close > current_psar:
        status = "Bullish"
        detail = "SAR: Bullish" if DEMO_MODE else f"SAR at ${format_price(current_psar)} — Below price"
    else:
        status = "Bearish"
        detail = "SAR: Bearish" if DEMO_MODE else f"SAR at ${format_price(current_psar)} — Above price"
    
    is_reversal = False
    if len(psar) > 2:
        for i in range(1, min(3, len(psar))):
            if (psar.iloc[-i] > close.iloc[-i] and psar.iloc[-i-1] < close.iloc[-i-1]) or \
               (psar.iloc[-i] < close.iloc[-i] and psar.iloc[-i-1] > close.iloc[-i-1]):
                is_reversal = True
                break
    
    if is_reversal and DEMO_MODE:
        detail += " | ⚠️ REVERSAL"
    elif is_reversal:
        detail += " | ⚠️ REVERSAL!"
    
    return {
        "status": status,
        "value": current_psar,
        "detail": detail,
        "is_reversal": is_reversal
    }

def calculate_volume_profile(df, num_bins=25):
    if df is None or len(df) < 20:
        return {"status": "Error", "value": None, "detail": "Insufficient data"}
    
    has_volume = 'Volume' in df.columns and df['Volume'].notna().any() and df['Volume'].sum() > 0
    
    if not has_volume:
        high = df['High'].iloc[-50:] if len(df) > 50 else df['High']
        low = df['Low'].iloc[-50:] if len(df) > 50 else df['Low']
        return {
            "status": "Fallback",
            "value": (high.max() + low.min()) / 2,
            "detail": "Volume Profile: POC analysis available in full version" if DEMO_MODE else f"Resistance: ${format_price(high.max())} | Support: ${format_price(low.min())}"
        }
    
    lookback = min(200, len(df))
    price = df['Close'].iloc[-lookback:]
    volume = df['Volume'].iloc[-lookback:]
    
    price_min = price.min(); price_max = price.max()
    bins = np.linspace(price_min, price_max, num_bins + 1)
    bin_indices = np.digitize(price, bins) - 1
    
    volume_by_bin = defaultdict(float)
    for idx, vol in zip(bin_indices, volume):
        if 0 <= idx < num_bins and not pd.isna(vol):
            volume_by_bin[idx] += vol
    
    if not volume_by_bin:
        high = df['High'].iloc[-50:] if len(df) > 50 else df['High']
        low = df['Low'].iloc[-50:] if len(df) > 50 else df['Low']
        return {
            "status": "Fallback",
            "value": (high.max() + low.min()) / 2,
            "detail": "Volume Profile: POC analysis available in full version" if DEMO_MODE else f"Resistance: ${format_price(high.max())} | Support: ${format_price(low.min())}"
        }
    
    poc_bin = max(volume_by_bin, key=volume_by_bin.get)
    poc_price = (bins[poc_bin] + bins[poc_bin + 1]) / 2
    
    sorted_bins = sorted(volume_by_bin.items(), key=lambda x: x[1], reverse=True)[:3]
    top_prices = [(bins[bin_idx] + bins[bin_idx + 1]) / 2 for bin_idx, _ in sorted_bins]
    
    if DEMO_MODE:
        detail = "Volume Profile: POC analysis available in full version"
    else:
        detail = f"POC: ${format_price(poc_price)}"
        if len(top_prices) > 1:
            detail += f" | Zone 2: ${format_price(top_prices[1])}"
        if len(top_prices) > 2:
            detail += f" | Zone 3: ${format_price(top_prices[2])}"
    
    return {
        "status": "Volume Profile",
        "value": poc_price,
        "detail": detail
    }

def calculate_all_indicators(symbol, df):
    if df is None:
        return {
            "trend": {"status": "Error", "value": None, "detail": "No data"},
            "momentum": {"status": "Error", "value": None, "detail": "No data"},
            "volatility": {"status": "Error", "value": None, "detail": "No data"},
            "reversal": {"status": "Error", "value": None, "detail": "No data"},
            "liquidity": {"status": "Error", "value": None, "detail": "No data"}
        }
    
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
    
    if "Bearish Divergence" in indicator_data["momentum"]["detail"]: bearish += 1
    elif "Bullish Divergence" in indicator_data["momentum"]["detail"]: bullish += 1
    
    if indicator_data["reversal"]["status"] == "Bullish": bullish += 1
    elif indicator_data["reversal"]["status"] == "Bearish": bearish += 1
    
    if indicator_data["volatility"]["status"] == "Squeeze":
        if indicator_data["trend"]["status"] == "Bullish": bullish += 0.5
        elif indicator_data["trend"]["status"] == "Bearish": bearish += 0.5
    
    if bullish > bearish:
        return "Strong Bullish" if bullish - bearish >= 2 else "Bullish"
    elif bearish > bullish:
        return "Strong Bearish" if bearish - bullish >= 2 else "Bearish"
    else:
        return "Neutral"

# --- SESSION LOGIC ---
def get_session_info(utc_now):
    current_time_utc = utc_now.time()
    session_name = "Quiet Session"
    
    if dt_time(13, 0) <= current_time_utc < dt_time(17, 0):
        session_name = "Overlap: London / New York"
    elif dt_time(13, 0) <= current_time_utc < dt_time(22, 0):
        session_name = "US Session (New York)"
    elif dt_time(8, 0) <= current_time_utc < dt_time(17, 0):
        session_name = "European Session (London)"
    elif dt_time(0, 0) <= current_time_utc < dt_time(9, 0):
        session_name = "Asian Session (Tokyo)"
    
    return session_name

# --- TRADE PARAMETERS ---
def get_trade_parameters(price, atr_val, bias, indicator_data, risk_multiple, reward_multiple, df):
    if DEMO_MODE:
        return {
            "title": "📋 Trade Plan",
            "direction": "DEMO",
            "current_price": price,
            "entry_trigger": None,
            "entry_label": "📋 Your personalized entry, target, and stop-loss levels are generated when you order your own dashboard — this demo shows the analysis method only.",
            "trigger_hit": False,
            "stop_loss": None,
            "target": None,
            "strategy": "Full trade plan available in custom build",
            "type": "demo"
        }
    
    if df is None:
        return {
            "title": "⏳ No Data Available",
            "direction": "ERROR",
            "current_price": price,
            "entry_trigger": None,
            "entry_label": "No historical data",
            "trigger_hit": False,
            "stop_loss": None,
            "target": None,
            "strategy": "Unable to calculate indicators",
            "type": "neutral"
        }
    
    resistance, support = find_swing_points(df, lookback=30)
    
    if resistance is None or support is None:
        bb_upper = indicator_data['volatility'].get('upper', price * 1.02)
        bb_lower = indicator_data['volatility'].get('lower', price * 0.98)
        resistance = resistance or bb_upper
        support = support or bb_lower
    
    atr_multiplier = 1.5
    
    if "Bullish" in bias:
        entry_trigger = resistance
        entry_label = f"Break above ${format_price(entry_trigger)}"
        trigger_hit = price > entry_trigger
        
        stop_loss = entry_trigger - (atr_multiplier * atr_val)
        target = entry_trigger + (atr_multiplier * atr_val * reward_multiple / risk_multiple)
        
        trade_params = {
            "title": "📈 LONG Position Setup",
            "direction": "LONG",
            "current_price": price,
            "entry_trigger": entry_trigger,
            "entry_label": entry_label,
            "trigger_hit": trigger_hit,
            "stop_loss": stop_loss,
            "target": target,
            "strategy": "Wait for breakout above resistance level",
            "type": "bullish"
        }
        
    elif "Bearish" in bias:
        entry_trigger = support
        entry_label = f"Break below ${format_price(entry_trigger)}"
        trigger_hit = price < entry_trigger
        
        stop_loss = entry_trigger + (atr_multiplier * atr_val)
        target = entry_trigger - (atr_multiplier * atr_val * reward_multiple / risk_multiple)
        
        trade_params = {
            "title": "📉 SHORT Position Setup",
            "direction": "SHORT",
            "current_price": price,
            "entry_trigger": entry_trigger,
            "entry_label": entry_label,
            "trigger_hit": trigger_hit,
            "stop_loss": stop_loss,
            "target": target,
            "strategy": "Wait for breakdown below support level",
            "type": "bearish"
        }
        
    else:
        trade_params = {
            "title": "⏳ No Trade Setup — Wait for Clarity",
            "direction": "NEUTRAL",
            "current_price": price,
            "entry_trigger": None,
            "entry_label": "No clear entry signal",
            "trigger_hit": False,
            "stop_loss": None,
            "target": None,
            "strategy": "Wait for clear breakout or breakdown",
            "type": "neutral"
        }
    
    return trade_params

# --- DISPLAY FUNCTION ---
def display_analysis(symbol, price, price_change, vs_currency, indicator_data, bias, risk_multiple, reward_multiple, df, show_details):
    
    if df is None:
        st.error("❌ No historical data available for analysis.")
        return
    
    atr_indicator = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14)
    atr_val = atr_indicator.average_true_range().iloc[-1]
    
    trade_params = get_trade_parameters(price, atr_val, bias, indicator_data, risk_multiple, reward_multiple, df)
    
    if "Bullish" in bias:
        bias_color = "#34D399"; bias_bg = "rgba(52, 211, 153, 0.15)"; bias_text = "BULLISH"
    elif "Bearish" in bias:
        bias_color = "#F87171"; bias_bg = "rgba(248, 113, 113, 0.15)"; bias_text = "BEARISH"
    else:
        bias_color = "#FBBF24"; bias_bg = "rgba(251, 191, 36, 0.15)"; bias_text = "NEUTRAL"
    
    change_sign = "+" if price_change > 0 else ""
    change_class = "bullish" if price_change > 0 else "bearish"
    
    # Price Card
    st.markdown(f"""
    <div class="price-card">
        <div class="price-section">
            <div class="label">Current Price</div>
            <div class="value">${format_price(price)} <span class="currency">{vs_currency.upper()}</span></div>
        </div>
        <div class="change-section">
            <div class="label">24h Change</div>
            <div class="change {change_class}">{change_sign}{price_change:.2f}%</div>
        </div>
        <div>
            <span class="bias-badge" style="background: {bias_bg}; color: {bias_color}; border: 2px solid {bias_color};">
                {bias_text}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Indicator Cards - only shown if show_details is True
    if show_details:
        st.markdown('<div class="section-header">Technical Indicators</div>', unsafe_allow_html=True)
        
        # Get colors for indicators
        trend_color = "#34D399" if indicator_data["trend"]["status"] == "Bullish" else "#F87171" if indicator_data["trend"]["status"] == "Bearish" else "#FBBF24"
        momentum_color = "#F87171" if indicator_data["momentum"]["status"] == "Overbought" else "#34D399" if indicator_data["momentum"]["status"] == "Oversold" else "#FBBF24"
        volatility_color = "#F59E0B" if indicator_data["volatility"]["status"] == "Squeeze" else "#60A5FA"
        reversal_color = "#F87171" if indicator_data["reversal"]["is_reversal"] else "#34D399" if indicator_data["reversal"]["status"] == "Bullish" else "#FBBF24"
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class="indicator-card" style="border-left-color: {trend_color};">
                <div class="card-header">
                    <span class="name">Trend — SuperTrend</span>
                    <span class="signal-badge" style="background: {trend_color}22; color: {trend_color};">{indicator_data['trend']['status'].upper()}</span>
                </div>
                <div class="value">{indicator_data['trend']['status']}</div>
                <div class="explanation">{indicator_data['trend']['detail']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            squeeze_label = "🔥 SQUEEZE" if indicator_data['volatility']['status'] == "Squeeze" else "NORMAL"
            st.markdown(f"""
            <div class="indicator-card" style="border-left-color: {volatility_color};">
                <div class="card-header">
                    <span class="name">Volatility — Bollinger Bands</span>
                    <span class="signal-badge" style="background: {volatility_color}22; color: {volatility_color};">{squeeze_label}</span>
                </div>
                <div class="value">{'Squeeze Detected' if indicator_data['volatility']['status'] == 'Squeeze' else 'Normal Volatility'}</div>
                <div class="explanation">{indicator_data['volatility']['detail']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="indicator-card" style="border-left-color: {momentum_color};">
                <div class="card-header">
                    <span class="name">Momentum — RSI</span>
                    <span class="signal-badge" style="background: {momentum_color}22; color: {momentum_color};">{indicator_data['momentum']['status'].upper()}</span>
                </div>
                <div class="value">{indicator_data['momentum']['status']}</div>
                <div class="explanation">{indicator_data['momentum']['detail']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            reversal_label = "⚠️ REVERSAL" if indicator_data['reversal']['is_reversal'] else indicator_data['reversal']['status'].upper()
            reversal_color_display = "#F87171" if indicator_data['reversal']['is_reversal'] else reversal_color
            st.markdown(f"""
            <div class="indicator-card" style="border-left-color: {reversal_color_display};">
                <div class="card-header">
                    <span class="name">Reversal — Parabolic SAR</span>
                    <span class="signal-badge" style="background: {reversal_color_display}22; color: {reversal_color_display};">{reversal_label}</span>
                </div>
                <div class="value">{'Reversal Imminent' if indicator_data['reversal']['is_reversal'] else indicator_data['reversal']['status']}</div>
                <div class="explanation">{indicator_data['reversal']['detail']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Liquidity - Full width
        st.markdown(f"""
        <div class="indicator-card-full">
            <div class="card-header">
                <span class="name">Liquidity — Volume Profile</span>
                <span class="signal-badge" style="background: rgba(139, 92, 246, 0.2); color: #A78BFA;">POC</span>
            </div>
            <div class="value">{indicator_data['liquidity']['status']}</div>
            <div class="explanation">{indicator_data['liquidity']['detail']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Trade Plan Box
    if DEMO_MODE:
        st.markdown(f"""
        <div class="recommendation-box">
            <div class="title">📋 Trade Plan</div>
            <div class="content">
                <strong>Current Price:</strong> <span class="current-price-label">${format_price(trade_params['current_price'])}</span><br>
                <strong>Analysis:</strong> {trade_params['entry_label']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Demo notice
        st.markdown("""
        <div class="demo-notice">
            <strong>🔒 Demo Mode</strong> — This is a demonstration of the analysis method. 
            Exact entry, target, and stop-loss levels are available in the full version.
        </div>
        """, unsafe_allow_html=True)
    else:
        if trade_params["type"] != "neutral" and trade_params["type"] != "demo":
            trigger_status = "✅ TRIGGER HIT" if trade_params["trigger_hit"] else "⏳ PENDING TRIGGER"
            trigger_class = "trigger-hit" if trade_params["trigger_hit"] else "trigger-pending"
            
            st.markdown(f"""
            <div class="recommendation-box">
                <div class="title">📋 {trade_params['title']}</div>
                <div class="content">
                    <strong>Current Price:</strong> <span class="current-price-label">${format_price(trade_params['current_price'])}</span><br>
                    <strong>Entry Trigger:</strong> <span class="{trigger_class}">{trade_params['entry_label']}</span> — {trigger_status}<br>
                    <strong>Stop Loss:</strong> ${format_price(trade_params['stop_loss'])}<br>
                    <strong>Target:</strong> ${format_price(trade_params['target'])}<br>
                    <strong>Strategy:</strong> {trade_params['strategy']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="recommendation-box">
                <div class="title">📋 {trade_params['title']}</div>
                <div class="content">
                    <strong>Current Price:</strong> <span class="current-price-label">${format_price(trade_params['current_price'])}</span><br>
                    <strong>Strategy:</strong> {trade_params['strategy']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Disclaimer
    st.markdown("""
    <div class="disclaimer">
        <strong>Risk Disclaimer:</strong> This is not financial advice. All trading involves risk. 
        Past performance doesn't guarantee future results. Only trade with money you can afford to lose.
    </div>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
utc_now = datetime.datetime.now(timezone.utc)
session_name = get_session_info(utc_now)

st.sidebar.markdown("<p class='sidebar-title'>📊 Market Context</p>", unsafe_allow_html=True)

tz_city_names = sorted(TIMEZONE_MAP.keys())
try: default_ix = tz_city_names.index("Pakistan (PKT)")
except ValueError: default_ix = 0

selected_tz_name = st.sidebar.selectbox("Select Your Timezone", tz_city_names, index=default_ix)

if selected_tz_name == "UTC":
    selected_tz_pytz = pytz.UTC
else:
    selected_tz_pytz = pytz.timezone(TIMEZONE_MAP[selected_tz_name])

user_local_time = datetime.datetime.now(selected_tz_pytz)

st.sidebar.markdown(f"""
<div class='sidebar-item'>
    <b>Your Local Time</b><br>
    <span class='local-time-info'>{user_local_time.strftime('%H:%M')}</span>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div class='sidebar-item'>
    <b>Active Session</b><br>
    <span class='active-session-info'>{session_name}</span>
</div>
""", unsafe_allow_html=True)

today_overlap_start = datetime.datetime.combine(utc_now.date(), dt_time(13, 0), tzinfo=timezone.utc)
today_overlap_end = datetime.datetime.combine(utc_now.date(), dt_time(17, 0), tzinfo=timezone.utc)
overlap_start_local = today_overlap_start.astimezone(selected_tz_pytz)
overlap_end_local = today_overlap_end.astimezone(selected_tz_pytz)

st.sidebar.markdown(f"""
<div class='sidebar-item'>
    <b>London/NY Overlap (Peak Liquidity)</b><br>
    <span style='font-size: 20px; color: #22D3EE; font-weight: 700;'>
        {overlap_start_local.strftime('%H:%M')} - {overlap_end_local.strftime('%H:%M')}
    </span>
    <br>({selected_tz_name})
</div>
""", unsafe_allow_html=True)

# --- MAIN ---
st.markdown('<div class="main-title">📊 Crypto Market Analyzer</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([1.5, 2.5, 1.5])

with col1:
    st.markdown("**Asset Type**")
    st.markdown("Crypto")

with col2:
    if DEMO_MODE:
        # Demo mode: dropdown with only 3 coins
        coin_options = ['BTC', 'ETH', 'SOL']
        user_input = st.selectbox(
            "Select Cryptocurrency",
            options=coin_options,
            help="Demo mode: BTC, ETH, SOL available"
        )
    else:
        # Full mode: text input
        user_input = st.text_input(
            "Enter Cryptocurrency Ticker",
            placeholder="e.g., BTC, ETH, SOL, ADA, DOGE",
            label_visibility="visible"
        )

with col3:
    show_indicator_details = st.checkbox("Show Indicator Details", value=False)

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
col_rr1, col_rr2, col_rr3 = st.columns([2, 2, 2])

with col_rr1:
    rr_selection = st.selectbox(
        "Risk:Reward Ratio",
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

if user_input:
    vs_currency = "usd"
    symbol = user_input.strip().upper()
    
    # Check if coin is in demo list (if demo mode)
    if DEMO_MODE and symbol not in ['BTC', 'ETH', 'SOL']:
        st.warning("⚠️ Demo mode only supports BTC, ETH, and SOL. Please select one of these.")
    else:
        with st.spinner(f"Fetching live data for {symbol} from CoinGecko..."):
            price, price_change = get_asset_price(symbol)
            
            if price is not None:
                df = get_historical_data(symbol, days=30)
                
                if df is not None:
                    indicator_data = calculate_all_indicators(symbol, df)
                    bias = determine_overall_bias(indicator_data)
                    
                    display_analysis(
                        symbol, price, price_change, vs_currency,
                        indicator_data, bias, RISK_MULTIPLE, REWARD_MULTIPLE, df, show_indicator_details
                    )
                else:
                    st.error("❌ Unable to fetch historical data. Please try again.")
            else:
                st.error(f"❌ Unable to fetch price data for {symbol}. Please check the ticker symbol and try again.")
