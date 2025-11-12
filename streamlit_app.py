import streamlit as st
import pandas as pd
import numpy as np
import ta
from ta.volatility import AverageTrueRange, BollingerBands
from ta.momentum import RSI
from ta.trend import SMAIndicator, PSARIndicator
import random # Used here only for initial dummy data creation

# --- Dummy Data Generator (Essential for TA calculations) ---
def generate_dummy_data(rows=200):
    """Generates a DataFrame with Open, High, Low, Close (OHLC) data."""
    np.random.seed(42) # for reproducibility
    # Ensure all required libraries are imported for this function
    
    dates = pd.date_range(end=pd.Timestamp.now(), periods=rows, freq='D')
    
    # Start price around 100
    close_prices = 100 + np.cumsum(np.random.normal(0, 1, rows))
    
    # Generate OHLC data
    df = pd.DataFrame({
        'Close': close_prices
    }, index=dates)
    
    df['High'] = df['Close'] + np.random.uniform(0.1, 0.5, rows)
    df['Low'] = df['Close'] - np.random.uniform(0.1, 0.5, rows)
    df['Open'] = df['Close'].shift(1).fillna(100)
    
    # Ensure High is always highest, Low is always lowest
    df['High'] = np.maximum(df['High'], df[['Open', 'Close']].max(axis=1))
    df['Low'] = np.minimum(df['Low'], df[['Open', 'Close']].min(axis=1))
    
    return df.iloc[1:] # Drop first row

# --- Indicator Calculation Functions ---

def calculate_all_indicators(df: pd.DataFrame):
    # 1. Volatility: Average True Range (ATR)
    atr_indicator = AverageTrueRange(df['High'], df['Low'], df['Close'], window=14)
    df['ATR'] = atr_indicator.average_true_range()

    # 2. Momentum: Relative Strength Index (RSI)
    rsi_indicator = RSI(df['Close'], window=14)
    df['RSI'] = rsi_indicator.rsi()

    # 3. Trend: Simple Moving Averages (SMA) - Used for Crossover
    df['SMA_5'] = SMAIndicator(df['Close'], window=5).sma_indicator()
    df['SMA_20'] = SMAIndicator(df['Close'], window=20).sma_indicator()
    
    # 4. Volatility: Bollinger Bands (BBands)
    bb_indicator = BollingerBands(df['Close'], window=20, window_dev=2)
    df['BBL'] = bb_indicator.bollinger_lband()
    df['BBH'] = bb_indicator.bollinger_hband()
    
    # 5. Trend: Parabolic SAR (PSAR)
    psar_indicator = PSARIndicator(df['High'], df['Low'], df['Close'])
    # PSAR_BULL/BEAR returns 1.0 if the trend is active, 0.0 otherwise
    df['PSAR_BULL'] = psar_indicator.psar_up_indicator()
    df['PSAR_BEAR'] = psar_indicator.psar_down_indicator()

    return df

# --- Status Interpretation Functions (Using Last Row of Data) ---

def supertrend_status(last_row):
    # Simulating SuperTrend status based on ATR (volatility) and SMA crossover (trend)
    atr_val = last_row['ATR']
    
    if last_row['SMA_5'] > last_row['SMA_20'] and atr_val > 0.5:
        return f"Bullish (High Volatility: {atr_val:.2f}) - Trend Confirmed"
    if last_row['SMA_5'] < last_row['SMA_20'] and atr_val > 0.5:
        return f"Bearish (High Volatility: {atr_val:.2f}) - Trend Confirmed"
    return f"Consolidation (Low Volatility: {atr_val:.2f}) - Range Bound"

def bollinger_status(last_row):
    close_val = last_row['Close']
    if close_val < last_row['BBL']:
        return "Outside Lower Band - Extreme Oversold"
    if close_val > last_row['BBH']:
        return "Outside Upper Band - Extreme Overbought"
    return "Within Bands - Normal Volatility"

def ema_crossover_status(last_row):
    # Using SMA 5 (Fast) and SMA 20 (Slow) as an EMA crossover proxy
    if last_row['SMA_5'] > last_row['SMA_20']:
        return "Bullish Cross (5 > 20) - Strong Momentum"
    if last_row['SMA_5'] < last_row['SMA_20']:
        return "Bearish Cross (5 < 20) - Strong Momentum"
    return "Indecisive/Flat EMAs"

def parabolic_sar_status(last_row):
    if last_row['PSAR_BULL'] == 1.0:
        return "Bullish (Dots Below Price) - Uptrend Confirmed"
    if last_row['PSAR_BEAR'] == 1.0:
        return "Bearish (Dots Above Price) - Downtrend Confirmed"
    return "Reversal Imminent - Avoid Entry"

def rsi_status(last_row):
    rsi_val = last_row['RSI']
    if rsi_val > 70:
        return f"Overbought ({rsi_val:.2f}) - Potential Reversal Down"
    if rsi_val < 30:
        return f"Oversold ({rsi_val:.2f}) - Potential Reversal Up"
    return f"Neutral ({rsi_val:.2f}) - Normal Market Conditions"

# --- Streamlit App Layout ---

st.title("📊 Multi-Indicator Technical Analysis Dashboard")
st.markdown("---")

# **API Key Handling**
try:
    # This line assumes you are using this key to fetch real data
    FH_API_KEY = st.secrets["FINNHUB_API_KEY"]
except KeyError:
    # If the secret is missing, display an error and halt the script.
    st.error("🚨 Missing API Key: Please create a `.streamlit/secrets.toml` file and add the FINNHUB_API_KEY.")
    st.stop()
    # Note: If you want to use the dummy data without the API key, 
    # you can remove st.stop() and use a placeholder for FH_API_KEY.

# 1. Setup Data
symbol = st.selectbox("Select Symbol", ["AAPL", "MSFT", "GOOGL"])
timeframe = st.selectbox("Select Timeframe", ["1D", "1H"])

# Replace this with your actual API call using FH_API_KEY
# df_data = fetch_data(symbol, timeframe, FH_API_KEY)
df_data = generate_dummy_data() 

# 2. Calculate All Indicators
df_indicators = calculate_all_indicators(df_data)
last_row = df_indicators.iloc[-1]

st.header(f"Results for **{symbol}** ({timeframe})")

# 3. Display Statuses
st.subheader("Market Summary")

col1, col2, col3 = st.columns(3)

with col1:
    st.info(f"**Close Price:** {last_row['Close']:.2f}")
    st.info(f"**ATR (Volatility):** {last_row['ATR']:.4f}")
    
with col2:
    st.success(f"**RSI (Momentum):** {rsi_status(last_row)}")
    st.success(f"**SuperTrend:** {supertrend_status(last_row)}")

with col3:
    st.warning(f"**EMA Crossover:** {ema_crossover_status(last_row)}")
    st.warning(f"**Parabolic SAR:** {parabolic_sar_status(last_row)}")

st.markdown("---")
st.subheader("Volatility and Band Status")
st.code(f"Bollinger Bands: {bollinger_status(last_row)}")

# Optional: Display the latest data row for debugging
st.subheader("Latest Calculated Data (Last Day)")
st.dataframe(pd.DataFrame(last_row).transpose(), use_container_width=True)

# Safety Disclaimer (Good practice for financial apps)
st.caption("Disclaimer: This information is for educational purposes only and does not constitute financial advice.")
