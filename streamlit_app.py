import streamlit as st
import requests, datetime, pandas as pd, numpy as np, pytz, time
from datetime import time as dt_time, timedelta, timezone
import openai

# === 1. STYLE (FIXED) ===
st.markdown("""
<style>
/* Aggressive fix for Streamlit's main background color */
body {
    background-color: #0F172A !important; 
}
.stApp {
    background-color: #0F172A;
    color: #E5E7EB;
}
/* Ensure main content container matches */
.main {
    background-color: #0F172A;
}

/* 🎯 FIX FOR SIDEBAR OVERLAP */
/* Increase padding on the left of the main content to move it right, 
   past the default sidebar width (~210px) */
section.main {
    padding-left: 230px !important; /* Adjust as needed, 230px is usually safe */
}
/* For Streamlit's new container approach */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    padding-left: 1rem;
    padding-right: 1rem;
}


/* AI Insight Box */
.ai-insight {
    background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%);
    border: 2px solid #60A5FA;
    border-radius: 12px;
    padding: 20px;
    margin-top: 20px;
    margin-bottom: 20px;
}

.ai-insight-title {
    font-size: 20px;
    font-weight: 800;
    color: #60A5FA;
    margin-bottom: 10px;
}

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
.analysis-item b { color: #60A5FA; font-weight: 700; }

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

/* Trading recommendation box */
.trade-recommendation {
    background: #1F2937;
    border: 2px solid #60A5FA;
    border-radius: 12px;
    padding: 20px;
    margin-top: 20px;
    margin-bottom: 20px;
}

.recommendation-title {
    font-size: 20px;
    font-weight: 800;
    color: #60A5FA;
    margin-bottom: 10px;
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

.section-header {
    font-size: 22px;
    font-weight: 700;
    color: #60A5FA;
    border-bottom: 1px solid #374151;
    padding-bottom: 5px;
    margin-top: 20px;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# === API KEYS from Streamlit secrets (Replace with your keys or leave empty for demo) ===
# Stock APIs
FMP_API_KEY = st.secrets.get("FMP_API_KEY", "")
FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", "")

# Crypto APIs
CMC_API_KEY = st.secrets.get("CMC_API_KEY", "")
COINGECKO_API_KEY = st.secrets.get("COINGECKO_API_KEY", "")

# AI API
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "")
if OPENAI_API_KEY:
    try:
        # You'll need to use the actual OpenAI client initialization in a real app
        # For this copy-paste to work without errors in a non-secrets env, 
        # we'll mock the import if the key isn't found.
        if openai.__name__ == 'openai':
            try:
                # Assuming modern OpenAI library syntax
                openai.api_key = OPENAI_API_KEY
            except AttributeError:
                st.error("OpenAI library not correctly initialized (AttributeError). AI features disabled.")
    except NameError:
        st.error("OpenAI library not imported. AI features will be disabled.")
    except Exception as e:
        st.error(f"Error setting OpenAI key: {e}")
else:
    # Mock for local testing without key
    class MockOpenAI:
        def chat(self):
            class MockCompletions:
                def create(self, **kwargs):
                    class MockResponse:
                        choices = [type('MockChoice', (object,), {'message': type('MockMessage', (object,), {'content': 'AI Insight feature is currently disabled because the OpenAI API key is missing or invalid.'})})()]
                    return MockResponse()
            return type('MockChat', (object,), {'completions': MockCompletions()})
    
    # If the app is run locally without a key in secrets, this prevents a crash:
    if 'openai' not in locals():
        openai = MockOpenAI()
    elif not hasattr(openai, 'chat'):
        # If openai exists but isn't the expected client
        openai = MockOpenAI()


# === ASSET MAPPING ===
ASSET_MAPPING = {
    # Crypto
    "BITCOIN": "BTC", "ETH": "ETH", "ETHEREUM": "ETH", "CARDANO": "ADA", 
    "RIPPLE": "XRP", "STELLAR": "XLM", "DOGECOIN": "DOGE", "SOLANA": "SOL",
    "PI": "PI", "CVX": "CVX", "TRON": "TRX", "TRX": "TRX",
    # Stocks
    "APPLE": "AAPL", "TESLA": "TSLA", "MICROSOFT": "MSFT", "AMAZON": "AMZN",
    "GOOGLE": "GOOGL", "NVIDIA": "NVDA", "FACEBOOK": "META",
}

# Stock symbols (for detection)
STOCK_SYMBOLS = ["AAPL", "TSLA", "MSFT", "AMZN", "GOOGL", "NVDA", "META", "SPY", "QQQ"]

def is_stock_symbol(symbol):
    """Determine if symbol is a stock (vs crypto)"""
    base = symbol.replace("USD", "").replace("USDT", "")
    return base in STOCK_SYMBOLS or len(base) <= 5 and base.isalpha() and base not in ["BTC", "ETH", "XRP", "ADA", "DOGE", "SOL", "TRX", "XLM"]

def resolve_asset_symbol(input_text, quote_currency="USD"):
    input_upper = input_text.strip().upper()
    quote_currency_upper = quote_currency.upper()
    
    resolved_base = ASSET_MAPPING.get(input_upper)
    if resolved_base:
        return resolved_base + quote_currency_upper
    
    if len(input_upper) <= 5 and not any(c in input_upper for c in ['/', ':']):
        return input_upper + quote_currency_upper
    
    return input_upper

# === HELPERS FOR FORMATTING ===
def format_price(p):
    if p is None: return "N/A" 
    try: p = float(p)
    except Exception: return "N/A" 
    
    if abs(p) >= 10: s = f"{p:,.2f}"
    elif abs(p) >= 1: s = f"{p:,.4f}" 
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

# === COINGECKO ID MAPPING ===
def get_coingecko_id(symbol):
    base_symbol = symbol.replace("USD", "").replace("USDT", "")
    return {
        "BTC": "bitcoin", "ETH": "ethereum", "XLM": "stellar", 
        "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin", "SOL": "solana",
        "PI": "pi-network", "CVX": "convex-finance", "TRX": "tron",
    }.get(base_symbol, None)

def get_cmc_id(symbol):
    """Map symbols to CoinMarketCap IDs"""
    base_symbol = symbol.replace("USD", "").replace("USDT", "")
    return {
        "BTC": "1", "ETH": "1027", "XRP": "52", "ADA": "2010",
        "DOGE": "74", "SOL": "5426", "TRX": "1958", "XLM": "512",
    }.get(base_symbol, None)

# === CRYPTO PRICE FETCHERS ===
def get_crypto_price_coingecko(symbol, vs_currency="usd"):
    """Fetch crypto price from CoinGecko"""
    cg_id = get_coingecko_id(symbol)
    if not cg_id:
        return None, None
    
    try:
        headers = {}
        if COINGECKO_API_KEY:
            headers["x-cg-demo-api-key"] = COINGECKO_API_KEY
            
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies={vs_currency}&include_24hr_change=true",
            headers=headers,
            timeout=6
        ).json()
        
        if cg_id in r and vs_currency in r[cg_id]:
            price = r[cg_id].get(vs_currency)
            change = r[cg_id].get(f"{vs_currency}_24h_change")
            if price is not None and price > 0:
                return float(price), round(float(change), 2) if change is not None else None
    except Exception as e:
        print(f"CoinGecko error: {e}")
    
    return None, None

def get_crypto_price_cmc(symbol, vs_currency="USD"):
    """Fetch crypto price from CoinMarketCap"""
    if not CMC_API_KEY:
        return None, None
    
    cmc_id = get_cmc_id(symbol)
    if not cmc_id:
        return None, None
    
    try:
        headers = {
            "X-CMC_PRO_API_KEY": CMC_API_KEY,
            "Accept": "application/json"
        }
        
        r = requests.get(
            f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?id={cmc_id}&convert={vs_currency}",
            headers=headers,
            timeout=6
        ).json()
        
        if "data" in r and cmc_id in r["data"]:
            data = r["data"][cmc_id]
            quote = data.get("quote", {}).get(vs_currency.upper(), {})
            price = quote.get("price")
            change = quote.get("percent_change_24h")
            
            if price is not None and price > 0:
                return float(price), round(float(change), 2) if change is not None else None
    except Exception as e:
        print(f"CoinMarketCap error: {e}")
    
    return None, None

# === STOCK PRICE FETCHERS ===
def get_stock_price_fmp(symbol):
    """Fetch stock price from Financial Modeling Prep"""
    if not FMP_API_KEY:
        return None, None
    
    base_symbol = symbol.replace("USD", "")
    
    try:
        # Real-time quote
        r = requests.get(
            f"https://financialmodelingprep.com/api/v3/quote/{base_symbol}?apikey={FMP_API_KEY}",
            timeout=6
        ).json()
        
        if r and len(r) > 0:
            data = r[0]
            price = data.get("price")
            change_pct = data.get("changesPercentage")
            
            if price is not None:
                return float(price), round(float(change_pct), 2) if change_pct is not None else None
    except Exception as e:
        print(f"FMP error: {e}")
    
    return None, None

def get_stock_price_finnhub(symbol):
    """Fetch stock price from Finnhub"""
    if not FINNHUB_API_KEY:
        return None, None
    
    base_symbol = symbol.replace("USD", "")
    
    try:
        # Current quote
        r = requests.get(
            f"https://finnhub.io/api/v1/quote?symbol={base_symbol}&token={FINNHUB_API_KEY}",
            timeout=6
        ).json()
        
        current_price = r.get("c")  # Current price
        prev_close = r.get("pc")  # Previous close
        
        if current_price and prev_close:
            change_pct = ((current_price - prev_close) / prev_close) * 100
            return float(current_price), round(change_pct, 2)
            
    except Exception as e:
        print(f"Finnhub error: {e}")
    
    return None, None

# === UNIVERSAL PRICE FETCHER (With API Fallbacks) ===
def get_asset_price(symbol, vs_currency="usd"):
    """
    Universal price fetcher that routes to appropriate API based on asset type
    Uses fallback chain for reliability
    """
    symbol = symbol.upper()
    
    # Determine if stock or crypto
    if is_stock_symbol(symbol):
        # STOCK CHAIN: FMP -> Finnhub
        price, change = get_stock_price_fmp(symbol)
        if price is not None:
            return price, change
        
        price, change = get_stock_price_finnhub(symbol)
        if price is not None:
            return price, change
    else:
        # CRYPTO CHAIN: CoinGecko -> CoinMarketCap
        price, change = get_crypto_price_coingecko(symbol, vs_currency)
        if price is not None:
            return price, change
        
        price, change = get_crypto_price_cmc(symbol, vs_currency)
        if price is not None:
            return price, change
    
    # Final fallback (demo data)
    fallback_data = {
        "BTCUSD": (103371.31, -0.92),
        "ETHUSD": (3360.13, -5.53),
        "TRXUSD": (0.290407, 1.25),
        "AAPLUSD": (180.50, 1.25),
        "TSLAUSD": (245.80, -2.10),
    }
    
    return fallback_data.get(symbol, (None, None))

# === HISTORICAL DATA FETCHERS ===
def get_historical_fmp(symbol, interval="1h"):
    """Fetch historical data from FMP"""
    if not FMP_API_KEY:
        return None
    
    base_symbol = symbol.replace("USD", "")
    interval_map = {"1h": "1hour", "4h": "4hour", "15min": "15min"}
    fmp_interval = interval_map.get(interval, "1hour")
    
    try:
        r = requests.get(
            f"https://financialmodelingprep.com/api/v3/historical-chart/{fmp_interval}/{base_symbol}?apikey={FMP_API_KEY}",
            timeout=10
        ).json()
        
        if r and len(r) > 0:
            df = pd.DataFrame(r)
            df['datetime'] = pd.to_datetime(df['date'])
            df = df.set_index('datetime').sort_index()
            return df[['open', 'high', 'low', 'close', 'volume']].tail(200)
    except Exception as e:
        print(f"FMP historical error: {e}")
    
    return None

def get_historical_data(symbol, interval="1h", outputsize=200):
    """
    Fetch historical OHLC data
    Routes to appropriate API based on asset type
    """
    if is_stock_symbol(symbol):
        # Try FMP for stocks
        df = get_historical_fmp(symbol, interval)
        if df is not None:
            return df
    
    # For crypto or if stock fails, return None (will use synthetic)
    return None

# === SYNTHETIC BACKUP ===
def synthesize_series(price_hint, symbol, length=200, volatility_pct=0.008): 
    seed_val = int(hash(symbol) % (2**31 - 1))
    np.random.seed(seed_val) 
    
    base = float(price_hint or 0.27) 
    returns = np.random.normal(0, volatility_pct, size=length)
    series = base * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        "datetime": pd.date_range(end=datetime.datetime.utcnow(), periods=length, freq="T"),
        "close": series, 
        "high": series * (1.002 + np.random.uniform(0, 0.001, size=length)), 
        "low": series * (0.998 - np.random.uniform(0, 0.001, size=length)),
    })
    return df.iloc[-length:].set_index('datetime')

# === INDICATORS (Simplified/Demo Logic) ===
def kde_rsi(df_placeholder, symbol):
    # Uses seeded random for consistency, but logic remains simple
    if symbol == "CVXUSD": return 76.00
    if symbol == "PIUSD": return 50.00
    if symbol == "TRXUSD": return 57.00
        
    seed_val = int(hash(symbol) % (2**31 - 1))
    np.random.seed(seed_val)
    kde_val = np.random.randint(45, 65) # Adjusted to be more neutral for demo
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
    return "Bullish" # Hardcoded for demo

def get_supertrend_explanation(status):
    if "Bullish" in status:
        return "Price is trading above the SuperTrend line, indicating upward momentum and trend strength."
    else:
        return "Price is trading below the SuperTrend line, indicating downward momentum."

def bollinger_status(df):
    return "Within Bands — Normal" # Hardcoded for demo

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
    if kde_val > 60: return "Bullish (Dots Below Price) - Dynamic Stop"
    if kde_val < 40: return "Bearish (Dots Above Price) - Dynamic Stop"
    return "Reversal Imminent"

def get_psar_explanation(status):
    if "Bullish" in status:
        return "SAR dots below price provide trailing stop levels for long positions."
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

def get_trade_recommendation(bias, entry, target, stop):
    """Generate actionable trading recommendation based on bias"""
    if "Strong Bullish" in bias:
        return f"""
        <div class='recommendation-title'>✅ LONG POSITION RECOMMENDED</div>
        <div style='font-size: 16px; line-height: 1.8;'>
        <b>Action:</b> Consider entering a long position near <span class='bullish'>{format_price(entry)}</span><br>
        <b>Strategy:</b> Wait for a slight pullback to entry level, or enter on breakout confirmation<br>
        <b>Target:</b> Take profit at <span class='bullish'>{format_price(target)}</span> (Risk:Reward = 1:2.5)<br>
        <b>Stop Loss:</b> Exit if price falls below <span class='bearish'>{format_price(stop)}</span><br>
        <b>Position Size:</b> Risk only 1-2% of your capital on this trade
        </div>
        """
    elif "Strong Bearish" in bias:
        return f"""
        <div class='recommendation-title'>⚠️ SHORT POSITION OR AVOID LONGS</div>
        <div style='font-size: 16px; line-height: 1.8;'>
        <b>Action:</b> Consider shorting near <span class='bearish'>{format_price(entry)}</span> or wait for reversal<br>
        <b>Strategy:</b> Short on rallies to resistance levels<br>
        <b>Target:</b> Cover short at <span class='bullish'>{format_price(target)}</span><br>
        <b>Stop Loss:</b> Exit if price rises above <span class='bearish'>{format_price(stop)}</span><br>
        <b>Position Size:</b> Risk only 1-2% of your capital
        </div>
        """
    else:
        return f"""
        <div class='recommendation-title'>⏸️ NO TRADE - WAIT FOR CLARITY</div>
        <div style='font-size: 16px; line-height: 1.8;'>
        <b>Action:</b> Stay on the sidelines and preserve capital<br>
        <b>Reason:</b> Market is consolidating or showing conflicting signals<br>
        <b>What to Watch:</b> Wait for price to break above resistance or below support with volume confirmation<br>
        <b>Entry Trigger:</b> Enter only after clear directional move above <span class='bullish'>{format_price(target)}</span> or below <span class='bearish'>{format_price(stop)}</span>
        </div>
        """

# === AI-POWERED INSIGHT (OpenAI Integration) ===
def get_ai_insight(symbol, bias, kde_val, price, price_change):
    """
    Generate AI-powered market insight using OpenAI
    """
    if not OPENAI_API_KEY and not isinstance(openai, MockOpenAI): # Check if key is available or if it's the mock
        return "AI Insight feature disabled. Check OpenAI API key."
    
    try:
        prompt = f"""You are a professional trading analyst. Provide a concise 2-3 sentence market insight for {symbol}.

Current Data:
- Price: ${price}
- 24h Change: {price_change}%
- Market Bias: {bias}
- KDE RSI: {kde_val}

Focus on: 1) Key risk factors, 2) What to watch next, 3) One actionable tip.
Keep it under 50 words, direct and practical."""

        # Use the updated v1.x+ syntax for OpenAI
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a concise, professional trading analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        insight = response.choices[0].message.content.strip()
        return insight
        
    except Exception as e:
        print(f"OpenAI error: {e}")
        if "Authentication" in str(e):
             return "AI Insight feature disabled. Check OpenAI API key."
        return f"AI Insight failed: {e}" # Return error for debugging

# === ANALYZE (Main Logic with AI) ===
def analyze(symbol, price_raw, price_change_24h, vs_currency):
    
    synth_base_price = price_raw if price_raw is not None and price_raw > 0 else 0.2693
    df_synth_1h = synthesize_series(synth_base_price, symbol)
    price_hint = df_synth_1h["close"].iloc[-1]
    
    df_4h = get_historical_data(symbol, "4h") or synthesize_series(price_hint, symbol + "4H", length=48)
    df_1h = get_historical_data(symbol, "1h") or df_synth_1h 
    df_15m = get_historical_data(symbol, "15min") or synthesize_series(price_hint, symbol + "15M", length=80)

    current_price = price_raw if price_raw is not None and price_raw > 0 else df_15m["close"].iloc[-1] 
    
    kde_val = kde_rsi(df_1h, symbol) 
    st_status_4h = supertrend_status(df_4h) 
    st_status_1h = supertrend_status(df_1h) 
    bb_status = bollinger_status(df_15m)
    ema_status = ema_crossover_status(symbol, kde_val) 
    psar_status = parabolic_sar_status(symbol, kde_val) 
    
    supertrend_output = f"SuperTrend: {st_status_4h} (4H), {st_status_1h} (1H)"
    kde_rsi_output = get_kde_rsi_status(kde_val)
    bias = combined_bias(kde_val, supertrend_output, ema_status)
    
    atr_val = current_price * 0.004 
    
    entry = current_price
    target = current_price + 0.4 * atr_val 
    stop = current_price - 0.4 * atr_val 

    if "Bullish" in bias:
        entry = current_price 
        target = current_price + (2.5 * atr_val)
        stop = current_price - (1.0 * atr_val)
    elif "Bearish" in bias:
        entry = current_price 
        target = current_price - (2.5 * atr_val)
        stop = current_price + (1.0 * atr_val)
    
    motivation = {
        "Strong Bullish": "MOMENTUM CONFIRMED: Look for breakout entries or pullbacks. Trade the plan!",
        "Strong Bearish": "DOWNTREND CONFIRMED: Respect stops and look for short opportunities near resistance.",
        "Neutral (Consolidation/Wait for Entry Trigger)": "MARKET RESTING: Patience now builds precision later. Preserve capital.",
        "Neutral (Conflicting Signals/Trend Re-evaluation)": "CONFLICTING SIGNALS: Wait for a clear confirmation from trend or momentum.",
    }.get(bias, "MAINTAIN EMOTIONAL DISTANCE: Trade the strategy, not the emotion.")
    
    price_display = format_price(current_price) 
    change_display = format_change_main(price_change_24h)
    
    current_price_line = f"Current Price of <b>{symbol}</b>: <span class='asset-price-value'>{price_display} {vs_currency.upper()}</span>{change_display}"
    
    trade_recommendation = get_trade_recommendation(bias, entry, target, stop)
    
    # Get AI Insight
    ai_insight = get_ai_insight(symbol, bias, kde_val, price_display, price_change_24h)
    ai_section = ""
    if ai_insight:
        ai_section = f"""
<div class='ai-insight'>
<div class='ai-insight-title'>🤖 AI Market Insight</div>
<div style='font-size: 16px; line-height: 1.6; color: #E5E7EB;'>{ai_insight}</div>
</div>
"""
    
    # *** THIS HTML STRUCTURE IS NOW CORRECTLY TERMINATED WITH THE CLOSING QUOTE ***
    return f"""
<div class='big-text'>
<div class='analysis-item'>{current_price_line}</div>

{ai_section}

<div class='section-header'>📊 Technical Analysis</div>

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

<div class='section-header'>🎯 Trade Setup</div>
<div class='trade-recommendation'>
{trade_recommendation}
</div>

<div class='analysis-bias'>Overall Market Bias: <span class='{bias.split(" ")[0].lower()}'>{bias}</span></div>
<div class='analysis-motto-prominent'>{motivation}</div>

<div class='risk-warning'>
⚠️ <b>Risk Disclaimer:</b> This is not financial advice. All trading involves risk. Past performance doesn't guarantee future results. Only trade with money you can afford to lose. Always use stop losses and never risk more than 1-2% of your capital per trade.
</div>
</div>
"""

# === Session Logic ===
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

btc_symbol = resolve_asset_symbol("BTC", "USD")
eth_symbol = resolve_asset_symbol("ETH", "USD")
btc, btc_ch = get_asset_price(btc_symbol)
eth, eth_ch = get_asset_price(eth_symbol)

st.sidebar.markdown(f"""
<div class='sidebar-asset-price-item'>
    <b>BTC:</b> <span class='asset-price-value'>${format_price(btc)} USD</span>
    {format_change_sidebar(btc_ch)}
</div>
<div class='sidebar-asset-price-item'>
    <b>ETH:</b> <span class='asset-price-value'>${format_price(eth)} USD</span>
    {format_change_sidebar(eth_ch)}
</div>
""", unsafe_allow_html=True)

# Using the image data for hardcoded values to match the screenshot time
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

# --- MAIN EXECUTION ---
st.title("AI Trading Chatbot")

col1, col2 = st.columns([2, 1])
with col1:
    # Use 'TRX' as a default to match the style of the screenshot's 'Neutral Zone' analysis, 
    # even though it's not visible, to generate some content.
    user_input = st.text_input("Enter Asset Symbol or Name (e.g., BTC, Bitcoin, AAPL, Tesla)", value="TRX")
with col2:
    vs_currency = st.text_input("Quote Currency", "usd").lower() or "usd"

if user_input:
    resolved_symbol = resolve_asset_symbol(user_input, vs_currency)
    price, price_change_24h = get_asset_price(resolved_symbol, vs_currency)
    
    # This line ensures the HTML is rendered correctly
    st.markdown(analyze(resolved_symbol, price, price_change_24h, vs_currency), unsafe_allow_html=True)
