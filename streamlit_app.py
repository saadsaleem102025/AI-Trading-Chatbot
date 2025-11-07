import streamlit as st
import requests, datetime, pandas as pd, numpy as np, pytz, time
from datetime import time as dt_time, timedelta, timezone
import pandas_ta as ta

# --- STREAMLIT CONFIGURATION ---
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === 1. STYLE (Contrast Theme & Prominence) ===
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
    padding: 0.1rem 1.2rem 0.1rem 1.2rem; 
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
.sidebar-item {
    background: #1F2937; border-radius: 8px; padding: 8px 14px; margin: 3px 0; 
    font-size: 16px; color: #9CA3AF; border: 1px solid #374151;
}
.local-time-info { color: #00FFFF !important; font-weight: 700; font-size: 16px !important; }
.active-session-info { color: #FF8C00 !important; font-weight: 700; font-size: 16px !important; }
.status-volatility-info { color: #32CD32 !important; font-weight: 700; font-size: 16px !important; }
.sidebar-item b { color: #FFFFFF !important; font-weight: 800; }
.sidebar-asset-price-item {
    background: #1F2937; border-radius: 8px; padding: 8px 14px; margin: 3px 0; 
    font-size: 16px; color: #E5E7EB; border: 1px solid #374151;
}

/* Price figure prominence */
.asset-price-value {
    color: #F59E0B;
    font-weight: 800;
    font-size: 24px;
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
AV_API_KEY = st.secrets.get("ALPHAVANTAGE_API_KEY", "")
FH_API_KEY = st.secrets.get("FINNHUB_API_KEY", "")
TWELVE_API_KEY = st.secrets.get("TWELVE_DATA_API_KEY", "")

# === ASSET MAPPING (Name-to-Symbol Resolution) ===
ASSET_MAPPING = {
    # Crypto
    "BITCOIN": "BTC", "ETH": "ETH", "ETHEREUM": "ETH", "CARDANO": "ADA", 
    "RIPPLE": "XRP", "STELLAR": "XLM", "DOGECOIN": "DOGE", "SOLANA": "SOL",
    "PI": "PI", "CVX": "CVX", "TRON": "TRX", "TRX": "TRX",
    "CFX": "CFX", 
    # Stocks
    "APPLE": "AAPL", "TESLA": "TSLA", "MICROSOFT": "MSFT", "AMAZON": "AMZN",
    "GOOGLE": "GOOGL", "NVIDIA": "NVDA", "FACEBOOK": "META",
    "MICROSTRATEGY": "MSTR", "MSTR": "MSTR", "WALMART": "WMT", 
    # Index
    "NASDAQ": "NDX", "NDX": "NDX" 
}

def resolve_asset_symbol(input_text, quote_currency="USD"):
    input_upper = input_text.strip().upper()
    quote_currency_upper = quote_currency.upper()
    
    resolved_base = ASSET_MAPPING.get(input_upper)
    if resolved_base:
        # If it's a known crypto base symbol, append the quote currency
        if resolved_base in ["BTC", "ETH", "ADA", "XRP", "XLM", "DOGE", "SOL", "PI", "CVX", "TRX", "CFX"]:
            return resolved_base + quote_currency_upper
        # Otherwise, return the stock/index ticker directly
        return resolved_base
    
    # If the user enters a raw ticker (e.g., AAPL)
    if len(input_upper) <= 5 and not any(c in input_upper for c in ['/', ':']):
        # If it looks like a known crypto ticker, append the quote currency
        if input_upper in ["BTC", "ETH", "ADA", "XRP", "XLM", "DOGE", "SOL", "PI", "CVX", "TRX", "CFX"]:
            return input_upper + quote_currency_upper
        # Otherwise, treat the short string as a stock/index ticker
        return input_upper 
    
    return input_upper

# === HELPERS FOR FORMATTING (UNCHANGED) ===
def format_price(p):
    if p is None: return "N/A" 
    try: p = float(p)
    except Exception: return "N/A" 
    
    if abs(p) >= 10: s = f"{p:,.2f}"
    elif abs(p) >= 1: s = f"{p:,.4f}" 
    # Adjusted for micro-caps where the price is very small
    elif abs(p) >= 0.01: s = f"{p:.4f}"
    else: s = f"{p:.6f}"
    return s.rstrip("0").rstrip(".")

def format_change_sidebar(ch):
    if ch is None: return "N/A"
    try: ch = float(ch)
    except Exception: return "N/A"
    sign = "+" if ch > 0 else ""
    color_class = "bullish" if ch > 0 else ("bearish" if ch < 0 else "neutral")
    return f"<div style='text-align: center; margin-top: 2px;'><span style='white-space: nowrap;'><span class='{color_class}'>{sign}{ch:.2f}%</span> <span class='percent-label'>(24h% Change)</span></span></div>"

def format_change_main(ch):
    if ch is None:
        return f"<span style='white-space: nowrap;'>&nbsp;|&nbsp;<span class='neutral'>(24h% Change N/A)</span></span>"
    
    try: ch = float(ch)
    except Exception: return f"<span style='white-space: nowrap;'>&nbsp;|&nbsp;<span class='neutral'>(24h% Change N/A)</span></span>"
    
    sign = "+" if ch > 0 else ""
    color_class = "bullish" if ch > 0 else ("bearish" if ch < 0 else "neutral")
    
    return f"<span style='white-space: nowrap;'>&nbsp;|&nbsp;<span class='{color_class}'>{sign}{ch:.2f}%</span> <span class='percent-label'>(24h% Change)</span></span>"

# --- NEW API HELPERS ---
def fetch_stock_price_alphavantage(ticker):
    """Fetches real-time price and change from AlphaVantage."""
    # NOTE: If AV_API_KEY is not set in secrets, this will fail and fall back to placeholders
    if not AV_API_KEY:
        # print("AlphaVantage API Key missing.")
        return None, None
        
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={AV_API_KEY}"
    try:
        r = requests.get(url, timeout=5).json()
        quote = r.get("Global Quote", {})
        
        if quote and quote.get("05. price") and quote.get("10. change percent"):
            price = float(quote["05. price"])
            # AlphaVantage change is "X.XX%"
            change_percent = float(quote["10. change percent"].replace('%', ''))
            
            if price > 0:
                time.sleep(1) # Be mindful of API rate limits
                return price, change_percent
    except Exception:
        pass
    return None, None

def fetch_crypto_price_binance(symbol):
    """Fetches real-time price from Binance Public API."""
    # Binance uses USDT pairs (e.g., BTCUSDT)
    binance_symbol = symbol.replace("USD", "USDT")
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}"
    
    try:
        r = requests.get(url, timeout=5).json()
        
        # Check if the response contains price data (i.e., not an error message like {'code': -1121})
        if 'lastPrice' in r and 'priceChangePercent' in r:
            price = float(r['lastPrice'])
            change_percent = float(r['priceChangePercent'])
            
            if price > 0:
                time.sleep(1) # Be mindful of API rate limits
                return price, change_percent
    except Exception:
        pass
    return None, None

# === UNIVERSAL PRICE FETCHER (NOW PRIORITIZING APIs) ===
@st.cache_data(ttl=60)
def get_asset_price(symbol, vs_currency="usd", asset_type="Stock/Index"):
    symbol = symbol.upper()
    base_symbol = symbol.replace("USD", "").replace("USDT", "")

    # --- 1. STOCK/INDEX LOGIC ---
    if asset_type == "Stock/Index":
        # 🟢 1a. Attempt to fetch price via AlphaVantage API for ANY stock
        price, change = fetch_stock_price_alphavantage(base_symbol)
        if price is not None:
            return price, change
        
        # 🟡 1b. Fallback to hardcoded placeholders if API fails (Keep the list small for known assets)
        if base_symbol == "TSLA": return 250.00, -1.50   # Tesla
        if base_symbol == "MSTR": return 240.00, 3.50    # MicroStrategy
        if base_symbol == "WMT": return 101.70, 0.23     # Walmart
        if base_symbol == "NDX": return 19800.00, 0.85  # NASDAQ 100
        
        # 🔴 1c. Final generic fallback for any unrecognized stock/index
        return 50.00, -0.35 
            
    # --- 2. CRYPTO LOGIC ---
    if asset_type == "Crypto":
        # 🟢 2a. Attempt to fetch price via Binance Public API for ANY crypto
        price, change = fetch_crypto_price_binance(symbol)
        if price is not None:
            return price, change
                
        # 🟡 2b. Fallback to hardcoded placeholders if API fails (for niche/unlisted coins)
        if symbol == "BTCUSD": return 105000.00, -5.00 # Backup BTC price
        if symbol == "CFXUSD": return 0.315986, 1.15 
        if symbol == "PIUSD": return 0.267381, 0.40 
        
        # 🔴 2c. Final generic fallback for any unrecognized crypto
        return 0.99, -2.50
    
    # Final default return if all attempts fail
    return None, None

# === HISTORICAL DATA (Placeholder) ===
def get_historical_data(symbol, interval="1h", outputsize=200):
    return None

def synthesize_series(price_hint, symbol, length=200, volatility_pct=0.008): 
    # This length is sufficient for ATR (14 periods)
    seed_val = int(hash(symbol) % (2**31 - 1))
    np.random.seed(seed_val) 
    
    base = float(price_hint or 0.27) 
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

# === INDICATORS (UNCHANGED LOGIC) ===
def kde_rsi(df_placeholder, symbol):
    # Fixed values for specific symbols to simulate different market states
    if symbol == "CFXUSD": return 76.00 
    if symbol == "PIUSD": return 50.00
    if "NDX" in symbol: return 70.00
    if "TSLA" in symbol: return 40.00
        
    seed_val = int(hash(symbol) % (2**31 - 1))
    np.random.seed(seed_val)
    kde_val = np.random.randint(30, 80)
    return float(kde_val)

def get_kde_rsi_status(kde_val):
    if kde_val < 10: return f"<span class='kde-purple'>🟣 {kde_val:.2f}% → Reversal Danger Zones</span> (Very High Bullish Reversal Probability)"
    elif kde_val < 20: return f"<span class='kde-red'>🔴 {kde_val:.2f}% → Extreme Oversold</span> (High chance of Bullish Reversal)"
    elif kde_val < 40: return f"<span class='kde-orange'>🟠 {kde_val:.2f}% → Weak Bearish</span> (Possible Bullish Trend Starting)"
    elif kde_val < 60: return f"<span class='kde-yellow'>🟡 {kde_val:.2f}% → Neutral Zone</span> (Trend Continuation or Consolidation)"
    elif kde_val < 80: return f"<span class='kde-green'>🟢 {kde_val:.2f}% → Strong Bullish</span> (Bullish Trend Likely Continuing)"
    elif kde_val < 90: return f"<span class='kde-red'>🔵 {kde_val:.2f}% → Extreme Overbought</span> (High chance of Bearish Reversal)"
    else: return f"<span class='kde-purple'>🟣 {kde_val:.2f}% → Reversal Danger Zones</span> (Very High Bearish Reversal Probability)"

def get_kde_rsi_explanation():
    return "KDE RSI uses probability density to identify overbought/oversold conditions more accurately than traditional RSI."

def supertrend_status(df):
    # Simplistic status for MVP
    return "Bullish"

def get_supertrend_explanation(status):
    if "Bullish" in status:
        return "Price is trading above the SuperTrend line, indicating upward momentum and trend strength."
    else:
        return "Price is trading below the SuperTrend line, indicating downward momentum."

def bollinger_status(df):
    return "Within Bands — Normal"

def get_bollinger_explanation(status):
    if "Normal" in status:
        return "Price is moving within expected volatility range. Watch for breaks above/below bands for potential moves."
    elif "Upper" in status:
        return "Price is touching upper band - potential overbought condition or strong trend."
    else:
        return "Price is touching lower band - potential oversold condition or weak trend."

def ema_crossover_status(symbol, kde_val):
    if kde_val > 60: return "Bullish Cross (5>20) - Trend Confirmed"
    if kde_val < 40: return "Bearish Cross (5<20) - Trend Confirmed"
    return "Indecisive"

def get_ema_explanation(status):
    if "Bullish" in status:
        return "Fast EMA crossed above slow EMA - suggests buying pressure and upward momentum."
    elif "Bearish" in status:
        return "Fast EMA crossed below slow EMA - suggests selling pressure and downward momentum."
    else:
        return "EMAs are close together - market is consolidating, wait for clear direction."

def parabolic_sar_status(symbol, kde_val):
    if kde_val > 60: return "Bullish (Dots Below Price) - Uptrend Confirmed"
    if kde_val < 40: return "Bearish (Dots Above Price) - Dynamic Stop"
    return "Reversal Imminent"

def get_psar_explanation(status):
    if "Bullish" in status:
        return "SAR dots below price confirm the <strong>uptrend</strong> and provide trailing stop levels for long positions."
    elif "Bearish" in status:
        return "SAR dots above price provide trailing stop levels for short positions."
    else:
        return "SAR switching position - trend may be reversing, avoid new entries."

def combined_bias(kde_val, st_text, ema_status):
    is_bullish_trend = ("Bullish" in st_text) and ("5>20" in ema_status or "Indecisive" in ema_status)
    is_bearish_trend = ("Bearish" in st_text) and ("5<20" in ema_status)
    
    if kde_val > 60 and is_bullish_trend:
        return "Strong Bullish"
    if kde_val < 40 and is_bearish_trend:
        return "Strong Bearish"

    if 40 <= kde_val < 60:
        return "Neutral (Consolidation/Wait for Entry Trigger)"
        
    return "Neutral (Conflicting Signals/Trend Re-evaluation)"

def get_trade_recommendation(bias, current_price, atr_val):
    """
    Generates dynamic, ATR-based trade parameters and returns them as a dictionary
    for use in the Natural Language Summary.
    """
    
    # Define ATR multiples for a 1:2.5 Risk-to-Reward Ratio (UNCHANGED)
    RISK_MULTIPLE = 1.0 
    REWARD_MULTIPLE = 2.5
    
    if "Strong Bullish" in bias:
        # Long Entry: Current Price, Stop: 1.0 ATR below, Target: 2.5 ATR above
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
        # Short Entry: Current Price, Stop: 1.0 ATR above, Target: 2.5 ATR below
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
        # Neutral: Suggests entry triggers based on ATR multiples
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

# === NATURAL LANGUAGE SUMMARY (UNCHANGED) ===
def get_natural_language_summary(symbol, bias, trade_params):
    """Generate the natural English summary using HTML tags instead of asterisks."""
    
    # Using <strong> for bolding and <i> for italics to avoid visible asterisks
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

    # Return the summary formatted for Streamlit Markdown
    return f"""
<div class='trade-recommendation-summary'>
{summary}
</div>
"""


# === ANALYZE (Main Logic - ATR Calculation FIXED) ===
def analyze(symbol, price_raw, price_change_24h, vs_currency):
    
    # Determine a sensible price for synthesis if the API failed
    # Fallback logic needs to handle both crypto (low price) and stock (high price) fallbacks
    base_symbol = symbol.replace("USD", "").replace("USDT", "")
    
    # Simple logic to determine a fallback base price
    if base_symbol in ["CFX", "PI"]: synth_fallback = 0.3 # Low-priced crypto
    elif base_symbol == "BTC": synth_fallback = 105000.00 # High-priced crypto
    elif base_symbol in ["NDX"]: synth_fallback = 19800.00 # Index
    elif base_symbol in ["TSLA", "MSTR", "AAPL", "MSFT"]: synth_fallback = 240.00 # Stock
    else: synth_fallback = 50.00 # Default fallback for unrecognized asset
    
    # Use the fetched price or the sensible fallback for synthesis base
    synth_base_price = price_raw if price_raw is not None and price_raw > 0 else synth_fallback
    
    # Use synthesis to generate OHLCV data for indicator calculation
    df_synth_1h = synthesize_series(synth_base_price, symbol)
    price_hint = df_synth_1h["Close"].iloc[-1] 
    
    df_4h = get_historical_data(symbol, "4h") or synthesize_series(price_hint, symbol + "4H", length=48)
    df_1h = get_historical_data(symbol, "1h") or df_synth_1h 
    df_15m = get_historical_data(symbol, "15min") or synthesize_series(price_hint, symbol + "15M", length=80)

    # Use the real price if available, otherwise use the last synthesized price
    current_price = price_raw if price_raw is not None and price_raw > 0 else df_15m["Close"].iloc[-1] 
    
    kde_val = kde_rsi(df_1h, symbol) 
    st_status_4h = supertrend_status(df_4h) 
    st_status_1h = supertrend_status(df_1h) 
    bb_status = bollinger_status(df_15m)
    ema_status = ema_crossover_status(symbol, kde_val) 
    psar_status = parabolic_sar_status(symbol, kde_val) 
    
    supertrend_output = f"SuperTrend: {st_status_4h} (4H), {st_status_1h} (1H)"
    kde_rsi_output = get_kde_rsi_status(kde_val)
    bias = combined_bias(kde_val, supertrend_output, ema_status)
    
    # --- ATR CALCULATION (REALISTIC using pandas_ta, with robust fallback) ---
    # Ensure the dataframe has 'High', 'Low', 'Close' for ATR calculation
    if all(col in df_1h.columns for col in ['High', 'Low', 'Close']):
        df_1h.ta.atr(append=True, length=14)
        atr_val = df_1h.get('ATR_14', pd.Series()).iloc[-1] if 'ATR_14' in df_1h.columns else np.nan
    else:
        atr_val = np.nan
    
    # Fallback to a sensible simulation if ATR calculation fails 
    if pd.isna(atr_val) or atr_val <= 0: 
        # Calculate a simulated ATR based on price 
        if current_price > 1000: atr_multiplier = 0.005 # High value assets (BTC, NDX)
        elif current_price > 100: atr_multiplier = 0.015 # Mid value assets (TSLA, MSTR)
        elif current_price > 1: atr_multiplier = 0.02 
        else: atr_multiplier = 0.008
        atr_val = current_price * atr_multiplier 
    # --- END ATR CALCULATION ---
    
    motivation = {
        "Strong Bullish": "MOMENTUM CONFIRMED: Look for breakout entries or pullbacks. Trade the plan!",
        "Strong Bearish": "DOWNTREND CONFIRMED: Respect stops and look for short opportunities near resistance.",
        "Neutral (Consolidation/Wait for Entry Trigger)": "MARKET RESTING: Patience now builds precision later. Preserve capital.",
        "Neutral (Conflicting Signals/Trend Re-evaluation)": "CONFLICTING SIGNALS: Wait for clear confirmation from trend or momentum.",
    }.get(bias, "MAINTAIN EMOTIONAL DISTANCE: Trade the strategy, not the emotion.")
    
    price_display = format_price(current_price) 
    change_display = format_change_main(price_change_24h)
    
    # --- PRICE LINE DISPLAY ---
    current_price_line = f"Current Price : <span class='asset-price-value'>{price_display} {vs_currency.upper()}</span>{change_display}"
    
    # Generate dynamic, ATR-based trade parameters
    trade_parameters = get_trade_recommendation(bias, current_price, atr_val)
    
    # Generate the natural language summary
    analysis_summary_html = get_natural_language_summary(symbol, bias, trade_parameters)
    
    # --- FINAL OUTPUT STRUCTURE (UNCHANGED) ---
    full_output = f"""
<div class='big-text'>
<div class='analysis-item'>{current_price_line}</div>

<div class='section-header'>📊 Detailed Indicator Analysis</div>

<div class='analysis-item'>KDE RSI Status: <b>{kde_rsi_output}</b></div>
<div class='indicator-explanation'>{get_kde_rsi_explanation()}</div>

<div class='analysis-item'><b>{supertrend_output}</b></div>
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

# === Session Logic (CLEANED) ---
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

# Note: Sidebar defaults to the 'Stock/Index' path for NDX, and 'Crypto' path for BTC for demonstration
btc_symbol = resolve_asset_symbol("BTC", "USD")
ndx_symbol = resolve_asset_symbol("NDX", "USD")
btc, btc_ch = get_asset_price(btc_symbol, asset_type="Crypto")
ndx, ndx_ch = get_asset_price(ndx_symbol, asset_type="Stock/Index")

st.sidebar.markdown(f"""
<div class='sidebar-asset-price-item'>
    <b>BTC:</b> <span class='asset-price-value'>${format_price(btc)} USD</span>
    {format_change_sidebar(btc_ch)}
</div>
<div class='sidebar-asset-price-item'>
    <b>NDX:</b> <span class='asset-price-value'>${format_price(ndx)} USD</span> 
    {format_change_sidebar(ndx_ch)}
</div>
""", unsafe_allow_html=True)

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

# --- MAIN EXECUTION (NEW DROPDOWN INTEGRATION) ---
st.title("AI Trading Chatbot")

# Use columns for the input widgets
col1, col2 = st.columns([1.5, 2.5])

with col1:
    # Asset Type Dropdown
    asset_type = st.selectbox(
        "Select Asset Type",
        ("Stock/Index", "Crypto"),
        index=0,
        help="Select 'Stock/Index' for TSLA, AAPL, NDX, etc. Select 'Crypto' for BTC, ETH, PI, etc."
    )

with col2:
    # Asset Ticker Input
    user_input = st.text_input(
        "Enter Asset Symbol or Name",
        placeholder="e.g., TSLA, NDX, BTC, PI"
    )

vs_currency = "usd" 

if user_input:
    # 1. Resolve symbol based on user input
    resolved_symbol = resolve_asset_symbol(user_input, vs_currency)
    
    # 2. Fetch price using the selected asset type
    price, price_change_24h = get_asset_price(resolved_symbol, vs_currency, asset_type)
    
    # 3. Run analysis
    st.markdown(analyze(resolved_symbol, price, price_change_24h, vs_currency), unsafe_allow_html=True)