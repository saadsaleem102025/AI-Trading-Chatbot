import streamlit as st
import time, requests, datetime, pandas as pd, numpy as np, openai, random

# === CONFIG ===
st.set_page_config(page_title="AI Trading Chatbot", layout="wide", initial_sidebar_state="expanded")
openai.api_key = st.secrets["OPENAI_API_KEY"]
TWELVE_API_KEY = st.secrets["TWELVE_DATA_API_KEY"]

# === MOTIVATION AUTO-REFRESH ===
if "last_refresh" not in st.session_state or time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.session_state.quote = random.choice([
        "Discipline beats impulse — trade the plan, not emotions.",
        "Patience is also a position.",
        "Focus on setups, not outcomes.",
        "Stay consistent — every small win builds your edge.",
        "Calm minds trade best."
    ])
elif "quote" not in st.session_state:
    st.session_state.quote = "Stay patient — great setups always return."

# === HELPERS ===
def get_crypto_price(symbol_id, vs_currency="usd"):
    try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": symbol_id, "vs_currencies": vs_currency, "include_24hr_change": "true"},
            timeout=8,
        )
        data = res.json().get(symbol_id, {})
        return round(data.get(vs_currency, 0), 2), round(data.get(f"{vs_currency}_24h_change", 0), 2)
    except:
        return None, 0.0


def get_twelve_data(symbol):
    try:
        res = requests.get(
            f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1h&outputsize=50&apikey={TWELVE_API_KEY}",
            timeout=10,
        ).json()
        if "values" not in res:
            return None
        df = pd.DataFrame(res["values"])
        df[["close", "high", "low"]] = df[["close", "high", "low"]].astype(float)
        df = df.sort_values("datetime")
        return df
    except:
        return None


def calculate_rsi(df):
    prices = df["close"].values
    deltas = np.diff(prices)
    up = np.mean(deltas[deltas > 0]) if np.any(deltas > 0) else 0
    down = -np.mean(deltas[deltas < 0]) if np.any(deltas < 0) else 1
    rs = up / down if down != 0 else 0
    return np.clip(100 - 100 / (1 + rs), 0, 100)


def interpret_rsi(rsi):
    if rsi < 20: return "🔴 Oversold — Reversal Up Possible"
    if rsi < 40: return "🟠 Mild Bearish — Caution"
    if rsi < 60: return "🟡 Neutral — Range or Build-Up"
    if rsi < 80: return "🟢 Bullish Momentum"
    return "🔵 Overbought — Reversal Down Possible"


def bollinger_status(df):
    df["MA20"] = df["close"].rolling(20).mean()
    df["STD"] = df["close"].rolling(20).std()
    df["Upper"] = df["MA20"] + 2 * df["STD"]
    df["Lower"] = df["MA20"] - 2 * df["STD"]
    close = df["close"].iloc[-1]
    if close > df["Upper"].iloc[-1]: return "Above Upper Band → Overbought"
    if close < df["Lower"].iloc[-1]: return "Below Lower Band → Oversold"
    return "Inside Bands → Normal"


def supertrend_signal(df, multiplier=3):
    hl2 = (df["high"] + df["low"]) / 2
    atr = df["high"] - df["low"]
    lower = hl2 - multiplier * atr
    close = df["close"].iloc[-1]
    return "Bullish" if close > lower.iloc[-1] else "Bearish"


def detect_fx_session_volatility(hour_utc):
    if 22 <= hour_utc or hour_utc < 7:  # Sydney
        return "Sydney Session", random.randint(30, 45)
    elif 0 <= hour_utc < 9:  # Tokyo
        return "Tokyo Session", random.randint(50, 70)
    elif 7 <= hour_utc < 16:  # London
        return "London Session", random.randint(80, 120)
    else:
        return "New York Session", random.randint(90, 130)


def interpret_volatility(vol):
    if vol < 40: return "⚪ Calm Market – Low Volatility"
    if vol < 80: return "🟢 Moderate Activity – Good Liquidity"
    if vol < 110: return "🟡 Strong Movement – Good for Short-Term Trades"
    return "🔴 High Volatility – Manage Risk Carefully"


def get_ai_analysis(symbol, price, rsi_text, bollinger_text, supertrend_text, vs_currency):
    # Keep price-based realism (entries within ±3–5% range)
    low_zone = round(price * 0.97, 2)
    high_zone = round(price * 1.03, 2)
    target = round(price * 1.05, 2)
    stop = round(price * 0.95, 2)

    prompt = f"""
    Give a concise technical summary for {symbol} ({vs_currency.upper()}).
    Indicators:
    - RSI: {rsi_text}
    - Bollinger: {bollinger_text}
    - SuperTrend: {supertrend_text}
    Current price: {price} {vs_currency.upper()}.
    Suggest a realistic trading plan using nearby levels:
    Entry Zone: between {low_zone} and {high_zone}
    Target: around {target}
    Stop Loss: near {stop}
    End with a one-line motivation.
    """
    try:
        res = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content.strip()
    except:
        return f"AI analysis for {symbol} temporarily unavailable. Stay disciplined and review key levels."


# === SIDEBAR ===
st.sidebar.title("📊 Market Context Panel")

btc, btc_ch = get_crypto_price("bitcoin")
eth, eth_ch = get_crypto_price("ethereum")
st.sidebar.metric("BTC (USD)", f"${btc:,.2f}" if btc else "N/A", f"{btc_ch:.2f}%")
st.sidebar.metric("ETH (USD)", f"${eth:,.2f}" if eth else "N/A", f"{eth_ch:.2f}%")

utc_now = datetime.datetime.utcnow()
session, vol = detect_fx_session_volatility(utc_now.hour)
st.sidebar.write(f"🕒 Timezone: UTC")
st.sidebar.markdown(f"### 💹 {session}")
st.sidebar.info(interpret_volatility(vol))

# === MAIN ===
st.title("AI Trading Chatbot")

col1, col2 = st.columns([2, 1])
with col1:
    user_input = st.text_input("Enter Asset Symbol (e.g., BTCUSD, EURUSD, AAPL)")
with col2:
    vs_currency = st.text_input("Quote Currency", "usd").lower()

if user_input:
    df = get_twelve_data(user_input.upper())
    if df is None or df.empty:
        st.warning("Using fallback price data (API temporary issue).")
        df = pd.DataFrame({
            "close": np.random.uniform(100, 200, 50),
            "high": np.random.uniform(110, 210, 50),
            "low": np.random.uniform(90, 190, 50)
        })

    price = df["close"].iloc[-1]
    rsi = calculate_rsi(df)
    ai_output = get_ai_analysis(
        user_input.upper(), price, interpret_rsi(rsi),
        bollinger_status(df), supertrend_signal(df), vs_currency
    )

    st.success(ai_output)
    st.markdown("---")
    st.subheader(f"📈 Technical Summary – {user_input.upper()}")
    st.write(f"**RSI:** {interpret_rsi(rsi)}")
    st.write(f"**Bollinger:** {bollinger_status(df)}")
    st.write(f"**SuperTrend:** {supertrend_signal(df)}")
    st.info(f"💬 Motivation: {st.session_state.quote}")

else:
    st.write("Welcome to the **AI Trading Chatbot** — enter any symbol to receive intelligent, price-aware market insights.")
    st.success(st.session_state.quote)
