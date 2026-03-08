import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from alpaca_trade_api.rest import REST, TimeFrame

# --- 1. SETUP & SECRETS ---
st.set_page_config(layout="wide", page_title="PRO TERMINAL")

try:
    ALPACA_KEY = st.secrets["ALPACA_KEY"]
    ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
    FMP_API_KEY = st.secrets["FMP_API_KEY"]
except Exception as e:
    st.error("Nøgler mangler i Secrets!")
    st.stop()

alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

# --- 2. DATA FUNKTIONER ---
def get_charts(symbol):
    try:
        # Henter 1-minut bars inkl. Extended Hours (Pre/After market)
        min_bars = alpaca.get_bars(symbol, TimeFrame.Minute, limit=200, extended_hours=True).df
        # Henter Daily bars
        day_bars = alpaca.get_bars(symbol, TimeFrame.Day, limit=100).df
        
        # Beregn indikatorer hvis der er data
        for df in [min_bars, day_bars]:
            if not df.empty:
                df['ema9'] = ta.ema(df['close'], length=9)
                df['ema21'] = ta.ema(df['close'], length=21)
                df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        return min_bars, day_bars
    except:
        return pd.DataFrame(), pd.DataFrame()

# --- 3. UI LAYOUT ---
st.title("⚡ QUANT-X PRO TERMINAL")
ticker = st.sidebar.text_input("Vælg Ticker", "TSLA").upper()

tab1, tab2, tab3 = st.tabs(["📊 Intraday (1-Min/Tick)", "📅 Daily Candle", "💰 Trade"])

with tab1:
    min_data, _ = get_charts(ticker)
    
    if not min_data.empty:
        # Her bygger vi din fulde graf med alle indikatorer
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.03, row_heights=[0.7, 0.3])

        # Candlesticks
        fig.add_trace(go.Candlestick(x=min_data.index, open=min_data['open'], high=min_data['high'], 
                                     low=min_data['low'], close=min_data['close'], name="1-Min"), row=1, col=1)
        
        # EMA & VWAP
        fig.add_trace(go.Scatter(x=min_data.index, y=min_data['ema9'], line=dict(color='cyan', width=1), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=min_data.index, y=min_data['ema21'], line=dict(color='orange', width=1), name="EMA 21"), row=1, col=1)
        fig.add_trace(go.Scatter(x=min_data.index, y=min_data['vwap'], line=dict(color='white', width=1.5), name="VWAP"), row=1, col=1)

        # Volume Bars i bunden
        fig.add_trace(go.Bar(x=min_data.index, y=min_data['volume'], name="Volume", marker_color="rgba(100, 100, 100, 0.5)"), row=2, col=1)

        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"Kunne ikke finde live data for {ticker}. Markedet kan være lukket.")

with tab2:
    _, day_data = get_charts(ticker)
    if not day_data.empty:
        fig_day = go.Figure(data=[go.Candlestick(x=day_data.index, open=day_data['open'], 
                                                high=day_data['high'], low=day_data['low'], close=day_data['close'])])
        fig_day.update_layout(template="plotly_dark", title=f"Daily: {ticker}", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_day, use_container_width=True)

with tab3:
    st.subheader("Lyn-Handel")
    if st.button("🚀 KØB 10 STK TEST", use_container_width=True):
        st.info("Handel aktiveres ved markedsåbning!")
        
