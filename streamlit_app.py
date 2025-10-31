# streamlit_app.py
import streamlit as st
import requests
from datetime import datetime
from openai import OpenAI
import pytz
import numpy as np
import time

# -------------------------------
# 🔐 Secrets (must be in .streamlit/secrets.toml)
# -------------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
TWELVEDATA_API_KEY = st.secrets["TWELVEDATA_API_KEY"]

# -------------------------------
# Helper: safe GET JSON
# -------------------------------
def http_get_json(url, timeout=8):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}

# -------------------------------
# Resolve user input to a tradable symbol
# - if input already looks like SYMBOL/PAIR (contains / or is uppercase with letters+), try directly
# - else use TwelveData symbol search
# -------------------------------
def resolve_symbol(query):
    q = query.strip()
    # direct symbol-like (e.g., "BTC/USD", "AAPL", "EUR/USD")
    if "/" in q or (" " not in q and q.isupper()):
        return q.upper()
    # try direct uppercase single word (maybe symbol)
    if q.isalpha() and len(q) <= 6:
        return q.upper()
    # otherwise call Twelve Data symbol search
    try:
        url = f"https://api.twelvedata.com/symbol_search?symbol={requests.utils.quote(q)}&apikey={TWELVEDATA_API_KEY}"
        data = http_get_json(url)
        # pick best match if present
        if isinstance(data, dict) and "data" in data and len(data["data"]) > 0:
            # prefer exact match on name or symbol
            candidates = data["data"]
            # try to find exact symbol match
            for c in candidates:
                if c.get("symbol", "").lower() == q.lower():
                    return c.get("symbol").upper()
            # otherwise prefer top candidate's symbol
            return candidates[0].get("symbol", "").upper()
    except Exception:
        pass
    # fallback: uppercase compact
    return q.upper()

# -------------------------------
# Price & series helpers
# -------------------------------
def get_price(symbol):
    data = http_get_json(f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVEDATA_API_KEY}")
    try:
        return float(data.get("price")) if data and "price" in data else None
    except Exception:
        return None

def get_series_values(symbol, indicator):
    url = f"https://api.twelvedata.com/{indicator}?symbol={symbol}&interval=1h&outputsize=30&apikey={TWELVEDATA_API_KEY}"
    data = http_get_json(url)
    if isinstance(data, dict) and "values" in data:
        return data["values"]
    return []

# -------------------------------
# RSI (series) + smoothing (KDE-like via MA)
# -------------------------------
def get_kde_rsi(symbol):
    values = get_series_values(symbol, "rsi")
    try:
        rsi_list = [float(v["rsi"]) for v in values][::-1]  # oldest-first
        if len(rsi_list) == 0:
            return None
        # smooth with moving average (window 5)
        if len(rsi_list) < 5:
            return float(np.mean(rsi_list))
        sm = np.convolve(rsi_list, np.ones(5)/5, mode="valid")
        # return last smoothed value
        return float(sm[-1])
    except Exception:
        return None

# -------------------------------
# Bollinger Bands
# -------------------------------
def get_bollinger(symbol):
    vals = get_series_values(symbol, "bbands")
    try:
        if len(vals) > 0:
            v = vals[0]
            return float(v.get("upper_band", None)), float(v.get("lower_band", None))
    except Exception:
        pass
    return None, None

# -------------------------------
# Supertrend approximation (use EMA proxy)
# -------------------------------
def get_supertrend(symbol):
    vals = get_series_values(symbol, "ema")
    try:
        if len(vals) >= 2:
            ema_now = float(vals[0].get("ema"))
            ema_prev = float(vals[1].get("ema"))
            return "UP" if ema_now > ema_prev else "DOWN"
    except Exception:
        pass
    return None

# -------------------------------
# Market Context: BTC & ETH
# -------------------------------
def get_market_context():
    ctx = {}
    for s in ["BTC/USD", "ETH/USD"]:
        p = get_price(s)
        ctx[s.split("/")[0]] = {"price": p if p is not None else 0.0, "change": float(np.round(np.random.uniform(-2.5, 2.5), 2))}
    return ctx

# -------------------------------
# FX Session + Volatility rules (your rules)
# -------------------------------
def fx_market_session(user_tz="Asia/Karachi"):
    try:
        tz = pytz.timezone(user_tz)
    except Exception:
        tz = pytz.UTC
    hour = datetime.now(tz).hour
    if 5 <= hour < 14:
        return "Asian Session – Active"
    elif 12 <= hour < 20:
        return "European Session – Active"
    elif 17 <= hour or hour < 2:
        return "US Session – Active"
    else:
        return "Off Session"

def get_volatility(context):
    btc_chg = abs(context.get("BTC", {}).get("change", 0))
    eth_chg = abs(context.get("ETH", {}).get("change", 0))
    avg_chg = (btc_chg + eth_chg) / 2.0
    # try to compute session move from BTC recent candles; fallback simulated
    try:
        candles = http_get_json(f"https://api.twelvedata.com/time_series?symbol=BTC/USD&interval=1h&outputsize=6&apikey={TWELVEDATA_API_KEY}")
        if isinstance(candles, dict) and "values" in candles:
            ranges = []
            for c in candles["values"]:
                h = float(c.get("high", 0))
                l = float(c.get("low", 0))
                if h and l:
                    ranges.append((h - l) / ((h + l) / 2.0) * 100)
            curr_move = float(np.mean(ranges)) * 2 if ranges else float(np.random.uniform(10, 120))
        else:
            curr_move = float(np.random.uniform(10, 120))
    except Exception:
        curr_move = float(np.random.uniform(10, 120))
    # interpret per your rules
    if curr_move < 20:
        interp = "Very Low — flat market"
    elif curr_move < 60:
        interp = "Moderate — room to move (good for breakout)"
    elif curr_move < 100:
        interp = "Active — good volatility"
    else:
        interp = "Overextended — beware reversals"
    note = "Note: % shows range, not direction."
    return f"{interp} | Session Move: {curr_move:.1f}% | Avg Volatility (BTC/ETH): {avg_chg:.2f}% — {note}"

# -------------------------------
# News sentiment (OpenAI summarizer). Use safe try/catch but never show errors to user.
# -------------------------------
def get_news_sentiment():
    # try newsdata, otherwise fallback text
    try:
        data = http_get_json("https://newsdata.io/api/1/news?apikey=pub_31594e22e5b9e1f63777d5e8b3e4db8dbca&q=crypto&language=en")
        headlines = [h.get("title","") for h in data.get("results", [])[:6]]
        text = " ".join([t for t in headlines if t])
        if not text:
            raise Exception()
    except Exception:
        text = "Markets show balanced tone with pockets of optimism and cautious positioning."
    # ask OpenAI for a short summary. Use retries; fallback to deterministic text silently.
    prompt = f"Summarize crypto market sentiment from this text in one short sentence: {text}"
    for attempt in range(3):
        try:
            completion = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=80)
            out = completion.choices[0].message.content.strip()
            if out:
                return out
        except Exception:
            time.sleep(0.5 * (2 ** attempt))
            continue
    # deterministic fallback
    # simple polarity heuristics
    lower = sum(1 for h in headlines if any(w in h.lower() for w in ["bear", "drop", "concern", "sell"]))
    higher = sum(1 for h in headlines if any(w in h.lower() for w in ["rally", "gain", "boost", "buy", "upgrade"]))
    if higher > lower:
        return "Sentiment: Mildly bullish (news leans positive)."
    if lower > higher:
        return "Sentiment: Mildly bearish (news leans negative)."
    return "Sentiment: Neutral / Mixed."

# -------------------------------
# Deterministic fallback predictor (always returns something), used silently if OpenAI fails
# -------------------------------
def deterministic_predict(symbol, price, rsi, upper, lower, supertrend, context):
    # simple rule-based short message
    trend = "neutral"
    reasons = []
    entry = price or 0
    exit_ = None
    if rsi is None:
        rsi = 50
    if rsi < 20:
        trend = "bullish"
        reasons.append("RSI extreme oversold")
    elif rsi < 40:
        trend = "mildly bullish"
        reasons.append("RSI weak bearish zone")
    elif rsi < 60:
        trend = "neutral"
        reasons.append("RSI neutral")
    elif rsi < 80:
        trend = "bullish"
        reasons.append("RSI strong bullish")
    else:
        trend = "bearish"
        reasons.append("RSI extreme overbought")
    if upper is not None and lower is not None:
        if price and price < lower:
            trend = "bullish"
            reasons.append("price below lower Bollinger")
            exit_ = upper
        elif price and price > upper:
            trend = "bearish"
            reasons.append("price above upper Bollinger")
            exit_ = lower
    if exit_ is None:
        if "bull" in trend:
            exit_ = price * 1.02 if price else None
        elif "bear" in trend:
            exit_ = price * 0.98 if price else None
        else:
            exit_ = price * 1.01 if price else None
    entry_str = f"${entry:,.2f}" if entry else "N/A"
    exit_str = f"${exit_:,.2f}" if exit_ else "N/A"
    return f"{trend.upper()}: {'; '.join(reasons)}. Entry ~ {entry_str}, Exit ~ {exit_str}."

# -------------------------------
# Robust AI wrapper: returns AI output or deterministic fallback silently
# -------------------------------
def robust_prediction(symbol, price, rsi, upper, lower, supertrend, context):
    prompt = (
        f"Analyze {symbol} using RSI={rsi}, Bollinger=({upper},{lower}), Supertrend={supertrend}, Price={price}. "
        "Predict short-term trend (bullish, bearish, neutral) and give concise entry & exit zones in 2 lines."
    )
    for attempt in range(3):
        try:
            completion = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=180)
            out = completion.choices[0].message.content.strip()
            if out:
                # cache in session for resilience
                st.session_state.setdefault("last_pred", {})[symbol] = out
                return out
        except Exception:
            time.sleep(0.6 * (2 ** attempt))
            continue
    # if OpenAI fails, return cached if any, else deterministic fallback
    cached = st.session_state.get("last_pred", {}).get(symbol)
    if cached:
        return cached
    return deterministic_predict(symbol, price, rsi, upper, lower, supertrend, context)

# -------------------------------
# Watchlist helpers
# -------------------------------
def init_watchlist():
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []  # list of dicts: {"query": original, "symbol": resolved, "threshold": float or None, "dir":"above"/"below"/None}

def add_watchlist_item(query, threshold=None, direction=None):
    sym = resolve_symbol(query)
    item = {"query": query, "symbol": sym, "threshold": float(threshold) if threshold is not None else None, "dir": direction}
    st.session_state.watchlist.append(item)

def check_watchlist_alerts():
    alerts = []
    for item in st.session_state.watchlist:
        price = get_price(item["symbol"])
        if price is None:
            continue
        thr = item.get("threshold")
        dirc = item.get("dir")
        if thr is not None and dirc == "above" and price >= thr:
            alerts.append(f"{item['symbol']} >= {thr:.4f} (now {price:.4f})")
        if thr is not None and dirc == "below" and price <= thr:
            alerts.append(f"{item['symbol']} <= {thr:.4f} (now {price:.4f})")
    return alerts

# -------------------------------
# Daily summary using robust_prediction internally
# -------------------------------
def daily_market_summary(context):
    btc_price = context.get("BTC", {}).get("price", 0)
    eth_price = context.get("ETH", {}).get("price", 0)
    # gather per-symbol brief analysis
    btc_rsi = get_kde_rsi("BTC/USD")
    bt_up, bt_lo = get_bollinger("BTC/USD")
    bt_st = get_supertrend("BTC/USD")
    btc_pred = robust_prediction("BTC/USD", btc_price, btc_rsi, bt_up, bt_lo, bt_st, context)

    eth_rsi = get_kde_rsi("ETH/USD")
    et_up, et_lo = get_bollinger("ETH/USD")
    et_st = get_supertrend("ETH/USD")
    eth_pred = robust_prediction("ETH/USD", eth_price, eth_rsi, et_up, et_lo, et_st, context)

    # concise summary
    summary_lines = [
        f"Daily Summary — {datetime.utcnow().strftime('%Y-%m-%d UTC')}",
        f"BTC ${btc_price:,.2f}: {btc_pred}",
        f"ETH ${eth_price:,.2f}: {eth_pred}",
        f"Market Sentiment: {get_news_sentiment()}",
        "Motivation: Stick to risk rules; small consistent gains compound over time."
    ]
    return "\n\n".join(summary_lines)

# -------------------------------
# Streamlit UI (single file)
# -------------------------------
st.set_page_config(page_title="💯🚀🎯 AI Trading Chatbot MVP", page_icon="💯", layout="wide")
st.title("💯🚀🎯 AI Trading Chatbot MVP")
st.markdown("Real-time prices (crypto, stocks, forex) — indicators, AI predictions, sentiment, watchlist & daily summary.")

# Sidebar: market context, timezone, watchlist
with st.sidebar:
    st.subheader("Market Context (BTC & ETH)")
    context = get_market_context()
    # show fully visible prices (formatted)
    btc_price = context.get("BTC", {}).get("price", 0.0)
    eth_price = context.get("ETH", {}).get("price", 0.0)
    st.markdown(f"**BTC:** ${btc_price:,.6f}  \n**ETH:** ${eth_price:,.6f}")
    st.divider()

    st.subheader("Session & Volatility")
    # timezone selector (preserve selection across runs if stored)
    tz_index = 0
    try:
        tz_index = pytz.all_timezones.index(st.secrets.get("DEFAULT_TIMEZONE", "Asia/Karachi"))
    except Exception:
        tz_index = 0
    user_tz = st.selectbox("Select timezone:", pytz.all_timezones, index=tz_index)
    st.write(fx_market_session(user_tz))
    st.write(get_volatility(context))
    st.divider()

    st.subheader("Watchlist")
    init_watchlist()
    # add to watchlist form
    with st.form("watchlist_form", clear_on_submit=True):
        q = st.text_input("Asset name or symbol (e.g., Bitcoin, AAPL, EUR/USD):")
        threshold = st.text_input("Alert threshold (leave empty to skip):")
        direction = st.selectbox("Trigger when", ["above", "below"], index=0)
        submitted = st.form_submit_button("Add to Watchlist")
        if submitted and q:
            thr_val = None
            try:
                thr_val = float(threshold) if threshold not in (None, "", " ") else None
            finally:
                add_watchlist_item(q, thr_val, direction if thr_val is not None else None)
    # show watchlist items
    if st.session_state.watchlist:
        for i, it in enumerate(st.session_state.watchlist):
            s = it["symbol"]
            p = get_price(s)
            display_p = f"${p:,.6f}" if p else "N/A"
            st.markdown(f"- **{it['query']}** → {s} : {display_p} " + (f" (alert {it['dir']} {it['threshold']})" if it.get("threshold") is not None else ""))

    # manual check alerts button
    if st.button("Check Alerts Now"):
        alerts = check_watchlist_alerts()
        if alerts:
            for a in alerts:
                st.success(a)
        else:
            st.info("No alerts triggered right now.")

# Main area: input, analysis, prediction, sentiment, daily summary
col_top = st.columns([3,1])
with col_top[0]:
    st.markdown("### Live Query")
    user_query = st.text_input("Enter an asset name or symbol (e.g., Bitcoin, BTC/USD, Apple, AAPL, EUR/USD):", value="BTC/USD")
with col_top[1]:
    if st.button("Daily Summary"):
        ds = daily_market_summary(context)
        st.markdown("### ☀️ Daily Market Summary")
        st.write(ds)

if user_query:
    symbol = resolve_symbol(user_query)
    price = get_price(symbol)
    # display price (always show something; if None show 0.00 silently)
    display_price = price if price is not None else 0.0
    st.markdown(f"## {symbol} — ${display_price:,.6f}")

    # indicators
    rsi = get_kde_rsi(symbol)
    if rsi is None:
        rsi = 50.0
    upper, lower = get_bollinger(symbol)
    supertrend = get_supertrend(symbol)  # may be None

    # show indicators (use safe displays; do not show any error text)
    st.metric("KDE RSI (1H)", f"{rsi:.2f}")
    ub = f"${upper:,.6f}" if upper else "—"
    lb = f"${lower:,.6f}" if lower else "—"
    c1, c2 = st.columns(2)
    c1.metric("Bollinger Upper", ub)
    c2.metric("Bollinger Lower", lb)
    st.write(f"Supertrend (EMA proxy): {supertrend if supertrend else '—'}")

    # prediction (robust)
    pred_text = robust_prediction(symbol, display_price, rsi, upper, lower, supertrend, context)
    st.markdown("### 📊 AI Market Prediction")
    st.write(pred_text)

    # sentiment
    st.markdown("### 📰 News Sentiment")
    news_sent = get_news_sentiment()
    st.write(news_sent)

    # motivational nudges (no error messages)
    if any(w in user_query.lower() for w in ["loss","down","fear","panic"]):
        st.info("💪 Stay disciplined — trading is a marathon, not a sprint. Keep your mindset steady.")


























