import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta

# --- CONFIGURATION & CONSTANTS ---
# 1. CHANGE: Risk-to-Reward Ratio is now 1:2 (2.0)
RISK_TO_REWARD_RATIO = 2.0 
RSI_THRESHOLD_HIGH = 70.0
RSI_THRESHOLD_LOW = 30.0

# Asset mapping for user-friendly names and reliable tickers
ASSET_MAPPING = {
    "BTC": "BTCUSD", "ETH": "ETHUSD", "SOL": "SOLUSD", "ADA": "ADAUSD",
    "BITCOIN": "BTCUSD", "ETHEREUM": "ETHUSD", "SOLANA": "SOLUSD", 
    "TESLA": "TSLA", "APPLE": "AAPL", "MICROSOFT": "MSFT", "AMAZON": "AMZN",
    "NASDAQ": "^IXIC", "NDX": "^IXIC", 
    # 2. CHANGE: Added SPY for reliable market overview
    "SPY": "SPY", "S&P 500": "SPY", "MARKET": "SPY"
}

# --- DATA SIMULATION (for indicator calculation) ---

# Simulate a time series for indicators (MVP stage)
@st.cache_data(ttl=60*60*24)
def synthesize_series(symbol, days=365):
    """Generates a synthetic time series that looks like a stock/crypto chart."""
    np.random.seed(hash(symbol) % (2**32 - 1))  # Seed based on symbol for consistent data
    
    start_price = 10.0  # Base starting price for simulation
    
    # Generate daily returns with a slight upward drift
    daily_returns = np.random.normal(0.0001, 0.015, days)
    price_series = start_price * (1 + daily_returns).cumprod()
    
    dates = [datetime.now() - timedelta(days=d) for d in range(days)][::-1]
    
    # Create OHLCV data (O=C[t-1], H=C*1.01, L=C*0.99)
    df = pd.DataFrame({'Close': price_series}, index=dates)
    df['Open'] = df['Close'].shift(1).fillna(start_price)
    df['High'] = df[['Open', 'Close']].max(axis=1) * 1.005
    df['Low'] = df[['Open', 'Close']].min(axis=1) * 0.995
    df['Volume'] = np.random.randint(100000, 1000000, days)
    
    return df

# --- API HELPERS (for live price data) ---

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

# --- UNIVERSAL PRICE FETCHER (Handles Fallback) ---
@st.cache_data(ttl=60)
def get_asset_price(symbol, asset_type="Stock/Index"):
    symbol = symbol.upper()
    base_symbol = symbol.replace("USD", "").replace("USDT", "")
    
    if asset_type == "Stock/Index":
        # Primary API: Finnhub
        price, change = fetch_stock_price_finnhub(base_symbol, st.secrets.get("FINNHUB_API_KEY", ""))
        if price is not None: return price, change
        
        # Secondary API: Yahoo Finance
        price, change = fetch_stock_price_yahoo(base_symbol)
        if price is not None: return price, change
        
        return None, None
            
    if asset_type == "Crypto":
        # Primary API: Binance
        price, change = fetch_crypto_price_binance(symbol)
        if price is not None: return price, change
        
        # Secondary API: CoinGecko
        price, change = fetch_crypto_price_coingecko(symbol, st.secrets.get("CG_PUBLIC_API_KEY", ""))
        if price is not None: return price, change
        
        return None, None
    
    return None, None

# --- ASSET RESOLUTION ---

def resolve_asset_symbol(input_symbol, asset_type="Stock/Index", quote_currency="USD"):
    input_upper = input_symbol.upper().strip()
    
    # 1. Check for full name or common alias in mapping
    if input_upper in ASSET_MAPPING:
        base_symbol = ASSET_MAPPING[input_upper]
    else:
        # 2. Use input directly as the symbol if not found
        base_symbol = input_upper
    
    # 3. Handle Crypto symbol suffix (e.g., BTC -> BTCUSD)
    if asset_type == "Crypto" and not base_symbol.endswith(("USD", "USDT")):
        final_symbol = base_symbol + quote_currency.upper()
    else:
        final_symbol = base_symbol
        
    # Return the un-suffixed base and the final API symbol
    return base_symbol.replace("USD", "").replace("USDT", ""), final_symbol

# --- INDICATOR CALCULATIONS ---

def calculate_indicators(df, price):
    """Simulates indicator calculation on the synthetic data."""
    if df.empty:
        return np.nan, np.nan, np.nan
    
    # Calculate RSI on the simulated data
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs)).iloc[-1]
    
    # Simulate a KDE RSI (just for architectural consistency in MVP)
    # The simulated price series gives a plausible RSI value
    kde_rsi = rsi 

    # Calculate EMA (e.g., 50-period)
    ema_50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
    
    # Simulate SuperTrend: Use EMA to mimic the trend direction
    if price > ema_50:
        supertrend_signal = "Buy"
    else:
        supertrend_signal = "Sell"

    return kde_rsi, ema_50, supertrend_signal

# --- BIAS GENERATION ---

def generate_bias(kde_rsi, supertrend_signal):
    """Generates a trading bias based on indicator signals."""
    
    if np.isnan(kde_rsi):
        return "Neutral", "Insufficient data for analysis."

    # Trend filter from SuperTrend
    is_bullish_trend = (supertrend_signal == "Buy")
    is_bearish_trend = (supertrend_signal == "Sell")
    
    # Momentum from KDE RSI
    is_overbought = (kde_rsi >= RSI_THRESHOLD_HIGH)
    is_oversold = (kde_rsi <= RSI_THRESHOLD_LOW)

    # 1. Strong Bullish: Momentum is strong (oversold) AND Trend is up
    if is_oversold and is_bullish_trend:
        return "Strong Bullish", "Momentum is recovering from oversold conditions within a strong confirmed uptrend."

    # 2. Strong Bearish: Momentum is strong (overbought) AND Trend is down
    if is_overbought and is_bearish_trend:
        return "Strong Bearish", "Momentum is weakening from overbought conditions within a strong confirmed downtrend."

    # 3. Bullish: Simple uptrend or momentum slightly positive
    if is_bullish_trend and (kde_rsi > 50 and not is_overbought):
        return "Bullish", "Trend remains positive with room for price expansion."

    # 4. Bearish: Simple downtrend or momentum slightly negative
    if is_bearish_trend and (kde_rsi < 50 and not is_oversold):
        return "Bearish", "Trend remains negative with a continuation of price compression."
    
    # 5. Neutral: Conflicting signals or flat movement
    return "Neutral", "The market is consolidating or indicators are conflicting, suggesting a wait-and-see approach."

# --- TRADING RECOMMENDATION ---

def get_recommendation(bias):
    """Generates a trade recommendation and targets based on the final bias."""
    
    if "Strong Bullish" in bias:
        action = "BUY ⬆️"
        # 1. CHANGE: Risk-to-Reward Ratio is 1:2
        details = f"Risk 1 unit to gain {RISK_TO_REWARD_RATIO} units (1:2 R:R)."
        
    elif "Strong Bearish" in bias:
        action = "SELL ⬇️"
        # 1. CHANGE: Risk-to-Reward Ratio is 1:2
        details = f"Risk 1 unit to gain {RISK_TO_REWARD_RATIO} units (1:2 R:R)."
        
    else:
        action = "HOLD/WAIT ⏸️"
        details = "A clear entry or exit is not confirmed. Stay on the sidelines."
        
    return action, details

# --- UI DISPLAY HELPERS ---

def generate_error_message(title, message, details):
    """Generates a formatted error message."""
    return st.error(f"**{title}**\n\n{message}\n\n*Details: {details}*", icon="🚨")

# --- MAIN ANALYSIS FUNCTION ---

def analyze(symbol, asset_type, quote_currency):
    
    # Resolve the final API symbol
    base_symbol, api_symbol = resolve_asset_symbol(symbol, asset_type, quote_currency)
    
    # --- STEP 1: FETCH LIVE PRICE DATA (Fallback logic included in get_asset_price) ---
    price_raw, price_change_24h = get_asset_price(api_symbol, asset_type)
    
    if price_raw is None:
        return generate_error_message(
            title="❌ Data Retrieval Failed ❌",
            message=f"Unable to fetch live price data for **{api_symbol}** as a **{asset_type}**.",
            details="The primary and all backup data sources for this asset are currently unavailable. Please ensure the ticker symbol is correct and try again in a few minutes."
        )

    # --- STEP 2: GENERATE SIMULATED SERIES FOR INDICATORS ---
    df_simulated = synthesize_series(api_symbol)
    
    # --- STEP 3: CALCULATE INDICATORS ---
    kde_rsi, ema_50, supertrend_signal = calculate_indicators(df_simulated, price_raw)
    
    # --- STEP 4: GENERATE BIAS AND RECOMMENDATION ---
    bias, bias_rationale = generate_bias(kde_rsi, supertrend_signal)
    action, trade_details = get_recommendation(bias)

    # --- STEP 5: DISPLAY RESULTS ---
    st.markdown(f"## 📈 {base_symbol} Live Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Current Price", value=f"${price_raw:,.2f}", delta=f"{price_change_24h:+.2f}% (24h)")
    
    with col2:
        st.markdown(f"**Trading Bias**")
        if "Strong" in bias:
            st.markdown(f"<h3 style='color: {'#00C853' if 'Bullish' in bias else '#FF3547'};'>{bias}</h3>", unsafe_allow_html=True)
        else:
            st.markdown(f"<h3 style='color: #FFC107;'>{bias}</h3>", unsafe_allow_html=True)

    with col3:
        st.markdown(f"**Action**")
        if "BUY" in action:
             st.markdown(f"<h3 style='color: #00C853;'>{action}</h3>", unsafe_allow_html=True)
        elif "SELL" in action:
             st.markdown(f"<h3 style='color: #FF3547;'>{action}</h3>", unsafe_allow_html=True)
        else:
             st.markdown(f"<h3 style='color: #FFC107;'>{action}</h3>", unsafe_allow_html=True)
    
    st.divider()

    st.markdown("### 📊 Analysis Rationale")
    
    # Recommendation Box
    st.info(f"**Recommendation:** {trade_details}", icon="🎯")
    
    # Indicator Details
    st.markdown("#### Indicator Summary")
    
    # Use HTML to ensure numbers are formatted nicely in the table
    kde_color = '#00C853' if kde_rsi < RSI_THRESHOLD_LOW else ('#FF3547' if kde_rsi > RSI_THRESHOLD_HIGH else '#FFC107')
    kde_status = 'Oversold (BUY Signal)' if kde_rsi < RSI_THRESHOLD_LOW else ('Overbought (SELL Signal)' if kde_rsi > RSI_THRESHOLD_HIGH else 'Neutral')
    
    indicator_data = [
        ("KDE RSI (Simulated)", f"<span style='color: {kde_color}; font-weight: bold;'>{kde_rsi:.2f}</span>", kde_status),
        ("SuperTrend (Simulated)", f"<span style='color: {'#00C853' if supertrend_signal == 'Buy' else '#FF3547'}; font-weight: bold;'>{supertrend_signal}</span>", "Trend Direction"),
        ("EMA 50 (Simulated)", f"${ema_50:,.2f}", "Trend Baseline"),
    ]
    
    df_indicators = pd.DataFrame(indicator_data, columns=['Indicator', 'Value', 'Context'])
    st.markdown(df_indicators.to_html(escape=False, index=False), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Bias Summary")
    st.markdown(f"> **Final Bias Rationale:** {bias_rationale}")

# --- STREAMLIT UI ---

st.set_page_config(layout="wide", page_title="AI Trading Bot MVP")

st.sidebar.title("🤖 Trading Bot Settings")

with st.sidebar.form(key='input_form'):
    asset_type = st.radio("Asset Type", ("Crypto", "Stock/Index"))
    
    default_symbol = "BTC" if asset_type == "Crypto" else "TSLA"
    symbol = st.text_input("Enter Ticker or Name", default_symbol)
    
    quote_currency = "USD" if asset_type == "Stock/Index" else "USD" # Use USD for generic crypto symbol construction
    
    submit_button = st.form_submit_button(label='Analyze Asset')

# --- Sidebar Overview ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🇺🇸 **US Market Overview**")

# 2. CHANGE: Fetch and display SPY price instead of NASDAQ index
spy_base_symbol, spy_symbol = resolve_asset_symbol("SPY", "Stock/Index", "USD")
spy_price, spy_change = get_asset_price(spy_symbol, asset_type="Stock/Index")

if spy_price is not None:
    spy_color = 'green' if spy_change >= 0 else 'red'
    st.sidebar.markdown(f"**S&P 500 ($SPY$)**:")
    st.sidebar.markdown(f"<p style='color: {spy_color}; font-size: 18px;'>${spy_price:,.2f} ({spy_change:+.2f}%)</p>", unsafe_allow_html=True)
else:
    st.sidebar.markdown("S&P 500 ($SPY$): N/A")

st.sidebar.markdown("---")

# --- Main Page Execution ---
if submit_button and symbol:
    analyze(symbol, asset_type, quote_currency)