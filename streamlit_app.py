import streamlit as st
import requests, datetime, pandas as pd, numpy as np, pytz, time
from datetime import time as dt_time

# tzlocal optional (for server-side timezone, falls back to UTC)
try:
    from tzlocal import get_localzone
except Exception:
    get_localzone = None

st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")

# === 1. UPDATED STYLE (Contrast Theme) ===
st.markdown("""
<style>
/* Base Streamlit overrides */
header[data-testid="stHeader"], footer {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}

/* Base font and colors */
html, body, [class*="stText"], [data-testid="stMarkdownContainer"] {
    font-size: 18px !important;
    color: #E0E0E0 !important; /* Softer white text */
    font-family: 'Inter', 'Segoe UI', sans-serif;
    line-height: 1.7 !important;
}

/* --- NEW COLOR SCHEME --- */
/* Main background (Lighter) */
[data-testid="stAppViewContainer"] {
    background: #1F2937; /* Lighter blue-grey */
    color: #E0E0E0 !important;
    padding-left: 360px !important;
    padding-right: 25px;
}
/* Sidebar styling (Darker) */
[data-testid="stSidebar"] {
    background: #111827; /* Darker sidebar */
    width: 340px !important; min-width: 340px !important; max-width: 350px !important;
    position: fixed !important; top: 0; left: 0; bottom: 0; z-index: 100;
    padding: 1.6rem 1.2rem 2rem 1.2rem;
    border-right: 1px solid #1F2937; /* Subtle border */
    box-shadow: 8px 0 18px rgba(0,0,0,0.4);
}
/* Main content boxes (Darker, to contrast main bg) */
.big-text {
    background: #111827; /* Darker, matches sidebar */
    border: 1px solid #374151; 
    border-radius: 16px; 
    padding: 28px; 
    margin-top: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
/* --- END NEW COLOR SCHEME --- */

.sidebar-title {
    font-size: 32px; 
    font-weight: 800; 
    color: #22D3EE; /* Bright Cyan */
    margin-bottom: 25px;
    text-shadow: 0 0 10px rgba(34, 211, 238, 0.3);
}
.sidebar-item {
    background: #1F2937; /* Matches main bg */
    border-radius: 10px; 
    padding: 14px 16px; 
    margin: 10px 0; 
    font-size: 17px; 
    color: #9CA3AF; /* Grey text for info */
    border: 1px solid #374151;
}
.sidebar-item b {
    color: #E5E7EB; /* Whiter text for labels */
    font-weight: 600;
}
/* Specific item for countdown */
.sidebar-countdown {
    background: linear-gradient(145deg, #1F2937, #111827);
    border: 1px solid #22D3EE;
    color: #E5E7EB;
    text-align: center;
    padding: 16px;
    font-size: 18px;
    border-radius: 10px;
    box-shadow: 0 0 15px rgba(34, 211, 238, 0.2);
}
/* Section Headers */
.section-header {
    font-size: 24px; 
    font-weight: 700; 
    color: #67E8F9; /* Light Cyan */
    margin-top: 25px; 
    border-left: 4px solid #22D3EE; 
    padding-left: 10px;
}
/* Inputs */
[data-baseweb="input"] input { 
    background-color: #1F2937 !important; 
    color: #F5F9FF !important; 
    border-radius: 10px !important; 
    border: 1px solid #374151 !important; 
    font-weight: 600 !important; 
}
[data-baseweb="input"] input:focus {
    border: 1px solid #22D3EE !important;
    box-shadow: 0 0 5px rgba(34, 211, 238, 0.5) !important;
}

/* Status colors */
.bullish { color: #10B981; font-weight: 700; } /* Green */
.bearish { color: #EF4444; font-weight: 700; } /* Red */
.neutral { color: #F59E0B; font-weight: 700; } /* Amber */
.motivation {font-weight:600; font-size:16px; margin-top:12px; color: #9CA3AF;}
</style>
""", unsafe_allow_html=True)

# === API KEYS from Streamlit secrets ===
AV_API_KEY = st.secrets.get("ALPHAVANTAGE_API_KEY", "")
FH_API_KEY = st.secrets.get("FINNHUB_API_KEY", "")
TWELVE_API_KEY = st.secrets.get("TWELVE_DATA_API_KEY", "")
CG_API_KEY = st.secrets.get("COINGECKO_API_KEY", "") 

# === safe autorefresh import fallback (REMOVED, using JS for timer) ===
# No longer needed, as the JS timer handles the live countdown.

# === HELPERS FOR FORMATTING (avoid TypeError) ===
def format_price(p):
    """Return a human-friendly price string."""
    if p is None: return "N/A"
    try: p = float(p)
    except Exception: return "N/A"
    if abs(p) >= 10: s = f"{p:,.2f}"
    elif abs(p) >= 1: s = f"{p:,.3f}"
    else: s = f"{p:.6f}"
    return s.rstrip("0").rstrip(".")

def format_change(ch):
    """Format percent change with sign and color."""
    if ch is None: return "N/A"
    try: ch = float(ch)
    except Exception: return "N/A"
    sign = "+" if ch > 0 else ""
    color_class = "bullish" if ch > 0 else ("bearish" if ch < 0 else "neutral")
    return f"<span class='{color_class}'>({sign}{ch:.2f}%)</span>"

# === UNIVERSAL PRICE FETCHER (With Public Fallback) ===
def get_asset_price(symbol, vs_currency="usd"):
    symbol = symbol.upper()
    
    # 0) Coingecko (Primary for BTC/ETH/Crypto - using API Key)
    if CG_API_KEY and symbol in ("BTCUSD", "ETHUSD"):
        try:
            cg_id = {"BTCUSD": "bitcoin", "ETHUSD": "ethereum"}.get(symbol)
            if cg_id:
                r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies={vs_currency}&include_24hr_change=true&x_cg_demo_api_key={CG_API_KEY}", timeout=6).json()
                if cg_id in r and vs_currency in r[cg_id]:
                    price = r[cg_id].get(vs_currency)
                    change = r[cg_id].get(f"{vs_currency}_24h_change")
                    if price is not None and price > 0:
                        return float(price), round(float(change), 2) if change is not None else None
        except Exception:
            pass

    # 1) Finnhub (Stocks/Forex/Crypto)
    if FH_API_KEY:
        try:
            r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FH_API_KEY}", timeout=6).json()
            if isinstance(d, dict) and d.get("c") not in (None, 0):
                chg = None
                if "pc" in d and d.get("pc") and d.get("c") != d.get("pc"):
                    chg = ((d["c"] - d["pc"]) / d["pc"]) * 100
                return float(d["c"]), round(chg, 2) if chg is not None else None
        except Exception:
            pass

    # 2) Alpha Vantage (Stocks/Forex)
    if AV_API_KEY:
        try:
            r = requests.get(f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={AV_API_KEY}", timeout=6).json()
            if "Global Quote" in r and r["Global Quote"].get("05. price"):
                p = float(r["Global Quote"]["05. price"])
                ch_raw = r["Global Quote"].get("10. change percent", "0%").replace("%", "")
                ch = float(ch_raw) if ch_raw != "" else None
                return p, round(ch, 2) if ch is not None else None
        except Exception:
            pass
            
    # 3) TwelveData (Stocks/Forex/Crypto)
    if TWELVE_API_KEY:
        try:
            td_symbol = f"{symbol}/{vs_currency.upper()}" if not symbol.endswith(vs_currency.upper()) else symbol
            r = requests.get(f"https://api.twelvedata.com/price?symbol={td_symbol}&apikey={TWELVE_API_KEY}", timeout=6).json()
            if "price" in r:
                return float(r["price"]), None
        except Exception:
            pass

    # 4) PUBLIC FALLBACK (No Key - for Demo)
    if symbol in ("BTCUSD", "ETHUSD"):
        try:
            cg_id = {"BTCUSD": "bitcoin", "ETHUSD": "ethereum"}.get(symbol)
            if cg_id:
                # Using the public API endpoint
                r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies={vs_currency}&include_24hr_change=true", timeout=6).json()
                if cg_id in r and vs_currency in r[cg_id]:
                    price = r[cg_id].get(vs_currency)
                    change = r[cg_id].get(f"{vs_currency}_24h_change")
                    if price is not None and price > 0:
                        return float(price), round(float(change), 2) if change is not None else None
        except Exception:
            pass

    # final: return None to indicate total failure
    return None, None

# === HISTORICAL FETCH (TwelveData) ===
def get_twelve_data(symbol, interval="1h", outputsize=200):
    if not TWELVE_API_KEY: return None
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=10).json()
        if "values" not in res: return None
        df = pd.DataFrame(res["values"])
        df[["close","high","low"]] = df[["close","high","low"]].astype(float)
        return df.sort_values("datetime").reset_index(drop=True)
    except Exception:
        return None

# === SYNTHETIC BACKUP (only used if ALL sources fail) ===
def synthesize_series(price, length=100, volatility_pct=0.005):
    base = float(price or 1.0)
    np.random.seed(int(base * 1000) % 2**31)
    returns = np.random.normal(0, volatility_pct, size=length)
    series = base * np.exp(np.cumsum(returns))
    df = pd.DataFrame({
        "datetime": pd.date_range(end=datetime.datetime.utcnow(), periods=length, freq="T"),
        "close": series, "high": series * (1.002), "low": series * (0.998),
    })
    return df

# === INDICATORS ===
def kde_rsi(df):
    closes = df["close"].astype(float).values
    if len(closes) < 5: return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = pd.Series(gains).ewm(alpha=1/14, adjust=False).mean()
    avg_loss = pd.Series(losses).ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    w = np.exp(-0.5 * (np.linspace(-2, 2, max(len(rsi[-30:]),1)))**2)
    return float(np.average(rsi[-30:], weights=w))

def supertrend_status(df):
    if "high" not in df.columns or "low" not in df.columns: return "Supertrend: N/A"
    hl2 = (df["high"] + df["low"]) / 2
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"] - df["close"].shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/10, adjust=False).mean()
    last_close = df["close"].iloc[-1]
    return "Supertrend: Bullish" if last_close > hl2.iloc[-1] else "Supertrend: Bearish"

def bollinger_status(df):
    close = df["close"]
    if len(close) < 20: return "Within Bands — Normal"
    ma = close.rolling(20).mean().iloc[-1]
    std = close.rolling(20).std().iloc[-1]
    upper, lower = ma + 2*std, ma - 2*std
    last = close.iloc[-1]
    if last > upper: return "Upper Band — Overbought"
    if last < lower: return "Lower Band — Oversold"
    return "Within Bands — Normal"

def combined_bias(kde_val, st_text, bb_text):
    score = 0
    if kde_val < 20: score += 50
    elif kde_val < 40: score += 25
    elif kde_val < 60: score += 0
    elif kde_val < 80: score -= 25
    else: score -= 50
    if "Bull" in st_text: score += 30
    elif "Bear" in st_text: score -= 30
    if "overbought" in bb_text.lower(): score -= 20
    elif "oversold" in bb_text.lower(): score += 20
    if score > 20: return "Bullish"
    if score < -20: return "Bearish"
    return "Neutral"

# === VOLATILITY LOGIC (for sidebar) ===
def fx_volatility_analysis(curr_range_pct, avg_range_pct):
    """Apply Boitoki-like volatility logic."""
    ratio = (curr_range_pct / avg_range_pct) * 100
    if ratio < 20:
        status = "Flat / Very Low Volatility"
        action = "Market is flat. Skip or reduce risk."
    elif 20 <= ratio < 60:
        status = "Low Volatility / Room to Move"
        action = "Session still has room to move. Good for breakouts."
    elif 60 <= ratio < 100:
        status = "Moderate Volatility / Near Average"
        action = "Market active but not overextended."
    else:
        status = "High Volatility / Possible Exhaustion"
        action = "Session moved a lot. Beware of reversals."
    return f"<b>Status:</b> {status} ({ratio:.0f}% of Avg)<br><b>Action:</b> {action}"

# === ANALYZE ===
def analyze(symbol, price, vs_currency):
    df_4h = get_twelve_data(symbol, "4h") or synthesize_series(price or 1.0)
    df_1h = get_twelve_data(symbol, "1h") or synthesize_series(price or 1.0)
    df_15m = get_twelve_data(symbol, "15min") or synthesize_series(price or 1.0)
    kde_val = kde_rsi(df_1h)
    st_text = f"{supertrend_status(df_4h)} (4H) • {supertrend_status(df_1h)} (1H)"
    bb_text = bollinger_status(df_15m)
    bias = combined_bias(kde_val, st_text, bb_text)
    
    if "high" in df_1h.columns and "low" in df_1h.columns and not df_1h.empty:
         atr = (df_1h["high"].max() - df_1h["low"].min()) / len(df_1h) * 10
    else:
        atr = (float(price or 1.0) * 0.01) 
        
    base = float(price or 1.0)
    entry = base - 0.3 * atr
    target = base + 1.5 * atr
    stop = base - 1.0 * atr

    motivation = {
        "Bullish": "Stay sharp — momentum’s on your side.",
        "Bearish": "Discipline is your shield.",
        "Neutral": "Market resting — patience now builds precision later."
    }[bias]
    
    return f"""
<div class='big-text'>
<div class='section-header'>📊 Price Overview</div>
<b>{symbol}</b>: <span style='color:#67E8F9;'>{format_price(price)} {vs_currency.upper()}</span>
<div class='section-header'>📈 Indicators</div>
• KDE RSI: <b>{kde_val:.2f}%</b><br>
• Bollinger Bands: {bb_text}<br>
• Supertrend: {st_text}
<div class='section-header'>🎯 Suggested Levels (Based on current price and volatility)</div>
Entry: <b style='color:#67E8F9;'>{format_price(entry)}</b><br>
Target: <b style='color:#10B981;'>{format_price(target)}</b><br>
Stop Loss: <b style='color:#EF4444;'>{format_price(stop)}</b>
<div class='section-header'>📊 Overall Bias</div>
<b class='{bias.lower()}'>{bias}</b>
<div class='motivation'>💬 {motivation}</div>
</div>
"""

# === Session Logic (Using UTC) ===
utc_now = datetime.datetime.utcnow()
utc_hour = utc_now.hour

SESSION_TOKYO = (dt_time(0, 0), dt_time(9, 0))    # 00:00 - 09:00 UTC
SESSION_LONDON = (dt_time(8, 0), dt_time(17, 0)) # 08:00 - 17:00 UTC
SESSION_NY = (dt_time(13, 0), dt_time(22, 0))   # 13:00 - 22:00 UTC
OVERLAP_START_UTC = dt_time(13, 0) # 13:00 UTC
OVERLAP_END_UTC = dt_time(17, 0)   # 17:00 UTC

session_name = "Quiet/Sydney Session"
current_range_pct = 0.02 # Dummy %
avg_range_pct = 0.1 # Dummy %
current_time_utc = utc_now.time()

if SESSION_TOKYO[0] <= current_time_utc < SESSION_TOKYO[1]:
    session_name = "Asian Session (Tokyo)"
    current_range_pct = 0.08 if utc_hour < 3 else 0.05
if SESSION_LONDON[0] <= current_time_utc < SESSION_LONDON[1]:
    session_name = "European Session (London)"
    current_range_pct = 0.15
if SESSION_NY[0] <= current_time_utc < SESSION_NY[1]:
    session_name = "US Session (New York)"
    current_range_pct = 0.15
if dt_time(8, 0) <= current_time_utc < dt_time(9, 0):
    session_name = "Overlap: Tokyo / London"
    current_range_pct = 0.18
if OVERLAP_START_UTC <= current_time_utc < OVERLAP_END_UTC:
    session_name = "Overlap: London / New York"
    current_range_pct = 0.30 # Most volatile

volatility_html = fx_volatility_analysis(current_range_pct, avg_range_pct)

# --- SIDEBAR ---
st.sidebar.markdown("<p class='sidebar-title'>📊 Market Context</p>", unsafe_allow_html=True)

# 1. API KEY WARNING
st.sidebar.warning("""
**Prices `N/A`?**
This app requires API keys. Please add your keys for `COINGECKO_API_KEY`, `FINNHUB_API_KEY`, etc., to your **Streamlit Secrets** to fetch live data.
""")

# 2. BTC/ETH Display
btc, btc_ch = get_asset_price("BTCUSD")
eth, eth_ch = get_asset_price("ETHUSD")
st.sidebar.markdown(f"<div class='sidebar-item'><b>BTC:</b> ${format_price(btc)} {format_change(btc_ch)}</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='sidebar-item'><b>ETH:</b> ${format_price(eth)} {format_change(eth_ch)}</div>", unsafe_allow_html=True)

# 3. Time Display (Cleaned up)
st.sidebar.markdown(f"<div class='sidebar-item'><b>Current Time (UTC):</b> {utc_now.strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='sidebar-item'><b>Active Session:</b> {session_name}<br>{volatility_html}</div>", unsafe_allow_html=True)

# 4. JAVASCRIPT LIVE COUNTDOWN
# This calculates the target time in Python, then passes it to JavaScript to handle the live countdown.
now_utc = datetime.datetime.utcnow()
today_overlap_start = datetime.datetime.combine(now_utc.date(), OVERLAP_START_UTC)
today_overlap_end = datetime.datetime.combine(now_utc.date(), OVERLAP_END_UTC)

if now_utc < today_overlap_start:
    target_timestamp = today_overlap_start.timestamp()
    label = "London/NY Overlap Starts In:"
elif now_utc < today_overlap_end:
    target_timestamp = today_overlap_end.timestamp()
    label = "London/NY Overlap Ends In:"
else:
    next_day_overlap_start = today_overlap_start + datetime.timedelta(days=1)
    target_timestamp = next_day_overlap_start.timestamp()
    label = "London/NY Overlap Starts In:"

# Inject the JavaScript
st.sidebar.markdown(f"""
<div class='sidebar-item sidebar-countdown'>
<b>{label}</b><br>
<span id='countdown-timer' style='font-size: 22px; color: #22D3EE; font-weight: 700;'>Loading...</span>
</div>

<script>
// Ensure this script only runs once
if (!window.countdownInterval) {{
    const targetTime = {target_timestamp} * 1000; // Convert to JS milliseconds
    const timerElement = document.getElementById('countdown-timer');

    const updateTimer = () => {{
        const now = new Date().getTime();
        const distance = targetTime - now;

        if (distance < 0) {{
            timerElement.innerHTML = "00:00:00";
            // Optionally, force a Streamlit rerun to get the next target time
            // window.parent.document.querySelector('.stApp [data-testid="stToolbar"] .st-emotion-cache-1f4w9kd .st-emotion-cache-6i8l1n').click();
            return;
        }}

        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);

        timerElement.innerHTML = 
            (hours < 10 ? "0" : "") + hours + ":" + 
            (minutes < 10 ? "0" : "") + minutes + ":" + 
            (seconds < 10 ? "0" : "") + seconds;
    }};

    updateTimer(); // Run once immediately
    window.countdownInterval = setInterval(updateTimer, 1000); // Update every second
}}
</script>
""", unsafe_allow_html=True)


# === MAIN ===
st.title("AI Trading Chatbot")
col1, col2 = st.columns([2, 1])
with col1:
    user_input = st.text_input("Enter Asset Symbol (e.g., BTCUSD, AAPL, EURUSD)")
with col2:
    vs_currency = st.text_input("Quote Currency", "usd").lower()

if user_input:
    symbol = user_input.strip().upper()
    price, _ = get_asset_price(symbol, vs_currency)
    
    if price is None:
        df = get_twelve_data(symbol, "1h")
        price = float(df["close"].iloc[-1]) if df is not None and not df.empty else None
        
    if price is None:
        st.info(f"Could not retrieve data for {symbol}. Please check the symbol or your API keys.")
    else:
        st.markdown(analyze(symbol, price, vs_currency), unsafe_allow_html=True)
else:
    st.info("Enter an asset symbol to GET REAL-TIME AI INSIGHT.")
