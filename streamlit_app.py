# streamlit_app.py
import streamlit as st
import requests
from openai import OpenAI
import datetime
from datetime import time
import pytz

# -------------------------------
# REQUIREMENTS (put in requirements.txt)
# streamlit
# openai>=1.0.0
# requests
# pytz
# -------------------------------

# -------------------------------
# CONFIG / SECRETS
# -------------------------------
st.set_page_config(page_title="AI Trading Chatbot MVP", page_icon="💬", layout="wide")

# Initialize OpenAI client (new SDK)
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
TWELVEDATA_API_KEY = st.secrets["TWELVEDATA_API_KEY"]

# -------------------------------
# HELPERS: API calls, utilities
# -------------------------------
def safe_get(url, params=None, timeout=8):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

# Unified price fetch (Twelve Data)
def get_price(symbol):
    if not symbol:
        return None
    try:
        url = f"https://api.twelvedata.com/price"
        params = {"symbol": symbol.upper(), "apikey": TWELVEDATA_API_KEY}
        res = safe_get(url, params)
        if res and "price" in res:
            return float(res["price"])
    except Exception:
        pass
    return None

# Market context from CoinGecko
def get_market_context():
    try:
        g = safe_get("https://api.coingecko.com/api/v3/global")
        if not g: 
            return None
        data = g.get("data", {})
        btc_dom = round(data.get("market_cap_percentage", {}).get("btc", 0), 2)
        total_cap = round(data.get("total_market_cap", {}).get("usd", 0) / 1e9, 2)
        # top benchmark prices for specific coins
        coins = ["bitcoin", "ethereum", "solana", "ripple"]  # ripple is id for XRP
        prices = {}
        for c in coins:
            p = safe_get("https://api.coingecko.com/api/v3/simple/price", params={"ids": c, "vs_currencies": "usd"})
            if p and c in p:
                prices[c] = p[c]["usd"]
            else:
                prices[c] = None
        return {"btc_dominance": btc_dom, "total_cap_b": total_cap, "prices": prices}
    except Exception:
        return None

# Indicators via Twelve Data
def get_rsi(symbol, interval="1h"):
    try:
        params = {"symbol": symbol.upper(), "interval": interval, "apikey": TWELVEDATA_API_KEY}
        res = safe_get("https://api.twelvedata.com/rsi", params)
        if res and "values" in res:
            return float(res["values"][0]["rsi"])
    except:
        pass
    return None

def get_bollinger(symbol, interval="1h"):
    try:
        params = {"symbol": symbol.upper(), "interval": interval, "apikey": TWELVEDATA_API_KEY}
        res = safe_get("https://api.twelvedata.com/bbands", params)
        if res and "values" in res:
            v = res["values"][0]
            upper = float(v.get("upper_band")) if v.get("upper_band") else None
            lower = float(v.get("lower_band")) if v.get("lower_band") else None
            return upper, lower
    except:
        pass
    return None, None

def get_supertrend(symbol, interval="1h"):
    try:
        params = {"symbol": symbol.upper(), "interval": interval, "apikey": TWELVEDATA_API_KEY}
        res = safe_get("https://api.twelvedata.com/supertrend", params)
        if res and "values" in res:
            v = res["values"][0]
            if "supertrend" in v:
                return float(v["supertrend"])
    except:
        pass
    return None

# KDE RSI interpretation rules (as you provided)
def interpret_rsi_kde(rsi):
    if rsi is None:
        return "RSI unavailable"
    try:
        r = float(rsi)
    except:
        return "RSI invalid"
    if r < 10 or r > 90:
        return "🟣 Reversal Danger Zone — Very high reversal probability"
    if r < 20:
        return "🔴 Extreme Oversold — High chance of bullish reversal; consider long setups"
    if r < 40:
        return "🟠 Weak Bearish — momentum shifting; look for confirmation for early long"
    if r < 60:
        return "🟡 Neutral Zone — consolidation/continuation"
    if r < 80:
        return "🟢 Strong Bullish — trend likely to continue; watch for exhaustion"
    return "🔵 Extreme Overbought — reversal warning; consider short signals"

# FX session by user's timezone string (use pytz timezone names)
def fx_session_for_timezone(tz_name="UTC"):
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.UTC
    now = datetime.datetime.now(tz).time()

    def between(t1, t2):
        if t1 <= t2:
            return t1 <= now <= t2
        # overnight wrap
        return now >= t1 or now <= t2

    # define sessions in local times (these are general session windows)
    if between(time(5, 0), time(14, 0)):
        return "Asian Session (5:00–14:00)", "Medium"
    if between(time(12, 0), time(20, 0)):
        return "European Session (12:00–20:00)", "High"
    if between(time(17, 0), time(1, 0)):
        return "US Session (17:00–01:00)", "High"
    return "Off-hours", "Low"

# Safe sentiment: try CryptoPanic then fallback to OpenAI summary
def get_sentiment_safe():
    try:
        cp = safe_get("https://cryptopanic.com/api/v1/posts/?auth_token=demo&kind=news")
        headlines = []
        if cp and isinstance(cp.get("results"), list):
            for p in cp["results"][:6]:
                headlines.append(p.get("title", ""))
        joined = " ".join([h for h in headlines if h])
        if joined:
            prompt = f"Summarize crypto market sentiment (bullish/bearish/neutral) based on these headlines:\n\n{joined}"
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content": prompt}]
            )
            return res.choices[0].message.content
    except Exception:
        pass

    # fallback: short AI-only summary
    fallback_prompt = "Give a concise 2-line summary of the current overall crypto market mood (bullish/bearish/neutral)."
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content": fallback_prompt}]
        )
        return res.choices[0].message.content
    except Exception:
        return "Sentiment unavailable."

# Smart AI fallback prompt (when prices/indicators missing)
def smart_ai_insight(user_query, context=None):
    ctx = context or {}
    prompt = f"""
You are a professional trading analyst.
User query: "{user_query}"

Context: {ctx}

1) Identify what instrument this likely refers to (stock/crypto/forex and symbol).
2) Give short technical bias (bullish/bearish/neutral) and reasoning.
3) Provide a 2-line trade idea: entry zone, exit/target, and a risk tip.
4) One line market sentiment summary.
Keep it concise and actionable.
"""
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":"You are an expert financial market analyst."},
                      {"role":"user","content":prompt}],
        )
        return res.choices[0].message.content
    except Exception:
        return "AI insight unavailable."

# -------------------------------
# APP UI & Logic
# -------------------------------
st.title("💯🚀 AI Trading Chatbot MVP")
st.markdown("Live prices (crypto/stock/forex), indicators, AI predictions, sentiment, watchlist & alerts.")

# Sidebar: market context and user timezone selection
with st.sidebar:
    st.header("🌐 Market Context")
    ctx = get_market_context()
    if ctx:
        st.metric("BTC Dominance", f"{ctx['btc_dominance']}%")
        st.metric("Total Market Cap (B)", f"${ctx['total_cap_b']}")
        # show benchmark prices if available
        p = ctx["prices"]
        st.write(f"BTC: ${p['bitcoin'] if p['bitcoin'] else 'N/A'}  •  ETH: ${p['ethereum'] if p['ethereum'] else 'N/A'}")
        st.write(f"SOL: ${p['solana'] if p['solana'] else 'N/A'}  •  XRP: ${p['ripple'] if p['ripple'] else 'N/A'}")
    else:
        st.info("Market context unavailable.")

    st.markdown("---")
    st.subheader("🕒 FX Session (Your timezone)")
    # timezone selection (short list) - user can pick
    tz_default = "UTC"
    # try auto pick from browser via query param? simpler: default to UTC
    tz = st.selectbox("Select your timezone", 
                      ["UTC","Asia/Karachi","Asia/Kolkata","Europe/London","America/New_York","Asia/Singapore","Australia/Sydney"],
                      index=1 if "Asia/Karachi" else 0)
    session_name, volatility = fx_session_for_tz = fx_session_name = None
    try:
        session_name, volatility = fx_session_for_tz = fx_session_for_tz = None
    except:
        pass
    # compute session
    session_name, vol = fx_session_for_timezone(tz), None  # fx_session_for_timezone returns just name — but earlier function returns pair in older code; keep simple
    # use new function:
    session_label, session_vol = fx_session_for_timezone(tz), None
    # display
    st.write(f"**Current session:** {session_label}")

    st.markdown("---")
    st.subheader("📋 Watchlist & Alerts")
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []  # list of dicts {"symbol":..., "alert_above":float or None, "alert_below":float or None, "last_price":float or None}
    add_sym = st.text_input("Add symbol to watchlist (e.g. BTC/USD OR TSLA)", value="")
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        add_above = st.text_input("Alert above (optional)", value="")
    with col2:
        add_below = st.text_input("Alert below (optional)", value="")
    with col3:
        if st.button("Add to Watchlist"):
            sym = add_sym.strip().upper()
            if sym:
                try:
                    above = float(add_above) if add_above.strip() else None
                except:
                    above = None
                try:
                    below = float(add_below) if add_below.strip() else None
                except:
                    below = None
                st.session_state.watchlist.append({"symbol":sym, "alert_above":above, "alert_below":below, "last_price":None})
                st.success(f"Added {sym} to watchlist.")
    st.write("Your Watchlist:")
    for i, item in enumerate(st.session_state.watchlist):
        st.write(f"- {item['symbol']}   (above: {item['alert_above']}  below: {item['alert_below']})")
    if st.button("Clear Watchlist"):
        st.session_state.watchlist = []
        st.success("Watchlist cleared.")

# Main column layout
col_main, col_right = st.columns([3,1])
with col_main:
    st.subheader("💬 Chat / Query")
    user_input = st.text_input("Ask about price, trend, or enter symbol(s):", "")
    st.markdown("**Indicator controls**")
    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        show_rsi = st.checkbox("Show RSI (KDE rules)", value=True)
    with ic2:
        show_bbands = st.checkbox("Show Bollinger Bands", value=True)
    with ic3:
        show_supertrend = st.checkbox("Show Supertrend", value=False)

    if user_input:
        st.markdown("---")
        # sanitize words: remove common stopwords to avoid "FOR" being treated as symbol
        stop_words = {"FOR","THE","PRICE","SHOW","WHAT","IS","TO","CURRENT","AT","A","IN","OF"}
        words = [w for w in user_input.upper().replace(",", " ").split() if w not in stop_words]
        prices_found = False
        indicators = {}

        # Try each token as potential symbol
        for token in words:
            price = get_price(token)
            if price is not None:
                prices_found = True
                st.success(f"💰 **{token}** = ${price}")
                indicators[token] = {"price": price}
                # indicators
                if show_rsi:
                    rsi = get_rsi(token)
                    indicators[token]["rsi"] = rsi
                    if rsi is not None:
                        st.metric(f"RSI (1H) for {token}", f"{rsi:.2f}")
                        st.caption(interpret_rsi_kde(rsi))
                if show_bbands:
                    ub, lb = get_bollinger(token)
                    indicators[token]["bb_upper"] = ub
                    indicators[token]["bb_lower"] = lb
                    if ub and lb:
                        st.info(f"📊 Bollinger Bands for {token} → Upper: ${ub:.2f}, Lower: ${lb:.2f}")
                if show_supertrend:
                    stval = get_supertrend(token)
                    indicators[token]["supertrend"] = stval
                    if stval:
                        st.info(f"📈 Supertrend (1H) for {token}: ${stval:.2f}")

                # AI prediction for this token using context
                ctx = {"btc_dominance": ctx["btc_dominance"] if (ctx := get_market_context()) else None}
                prompt = f"Analyze {token}. Price={price}. Indicators: {indicators[token]}. BTC Dominance: {ctx.get('btc_dominance') if ctx else 'N/A'}."
                try:
                    with st.spinner(f"Generating AI prediction for {token}..."):
                        pred = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role":"system","content":"You are a professional market analyst."},
                                {"role":"user","content":(
                                    f"{prompt}\n\nProvide short actionable forecast (bullish/bearish/neutral), "
                                    "and 2-line entry/exit suggestion. Keep concise."
                                )},
                            ],
                        )
                        st.markdown(f"### 🤖 AI Prediction for {token}:")
                        st.write(pred.choices[0].message.content)
                except Exception as e:
                    st.error(f"AI prediction error: {e}")

        # If no token price found, use smart fallback AI insight
        if not prices_found:
            with st.spinner("Generating AI market insight..."):
                # pass a small market context to the prompt
                market_ctx = get_market_context()
                fallback = smart_ai_insight(user_input, context={"market_ctx": market_ctx})
                st.markdown("### 🤖 AI Market Insight:")
                st.write(fallback)

        # Update watchlist last_price and check alerts
        if "watchlist" in st.session_state and st.session_state.watchlist:
            for item in st.session_state.watchlist:
                sym = item["symbol"]
                p = get_price(sym)
                # update last_price
                if p is not None:
                    # check alerts
                    if item.get("alert_above") and p >= item["alert_above"]:
                        st.balloons()
                        st.warning(f"ALERT: {sym} is above {item['alert_above']} (current {p})")
                    if item.get("alert_below") and p <= item["alert_below"]:
                        st.balloons()
                        st.warning(f"ALERT: {sym} is below {item['alert_below']} (current {p})")
                    item["last_price"] = p

        # Sentiment & Daily summary and motivation
        st.markdown("---")
        if show_sentiment := st.checkbox("Show Sentiment & Daily Summary", value=True):
            st.subheader("📰 Market Sentiment")
            s = get_sentiment_safe()
            st.write(s)

            # Daily summary (top 5 coins by market cap)
            st.subheader("📅 Daily Market Summary (top 5 by market cap)")
            try:
                top5 = safe_get("https://api.coingecko.com/api/v3/coins/markets", params={"vs_currency":"usd","order":"market_cap_desc","per_page":5,"page":1})
                if top5:
                    for c in top5:
                        st.write(f"- **{c['name']}**: ${c['current_price']} ({c['price_change_percentage_24h']:.2f}% 24h)")
                else:
                    st.info("Daily summary unavailable.")
            except:
                st.info("Daily summary unavailable.")

        # Motivation
        if any(k in user_input.lower() for k in ["loss","down","fear","panic","stressed"]):
            st.info("💪 Keep discipline: follow your plan, size positions responsibly, and use stop-losses.")
        else:
            st.caption("💡 Tip: Trade your plan — consistency compounds gains.")

with col_right:
    st.subheader("Quick Tools")
    if st.button("Show Market Context Now"):
        mc = get_market_context()
        st.write(mc if mc else "Context unavailable.")
    if st.button("Run Sentiment Check"):
        st.write(get_sentiment_safe())

# End of app









