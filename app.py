import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from alpaca_trade_api.rest import REST, TimeFrame
import time

# --- 1. SETUP ---
st.set_page_config(layout="wide", page_title="QUANT-X TICK TERMINAL")

ALPACA_KEY = st.secrets["ALPACA_KEY"]
ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
FMP_API_KEY = st.secrets["FMP_API_KEY"]

alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

# --- 2. SCREENER-LISTE (Viser data for hver aktie) ---
@st.cache_data(ttl=60)
def get_screener_data():
    candidates = ["TSLA", "NVDA", "AAPL", "AMD", "GME", "SMCI", "MARA", "PLTR", "COIN"]
    results = []
    for symbol in candidates:
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?timeseries=5&apikey={FMP_API_KEY}"
        try:
            r = requests.get(url).json()
            df = pd.DataFrame(r['historical'])
            vol = df.iloc[0]['volume']
            avg_vol = df['volume'].mean()
            rvol = round(vol / avg_vol, 2)
            results.append({"Symbol": symbol, "Vol": f"{vol:,}", "RVOL": rvol})
        except: continue
    return results

# --- 3. SIDEBAR SOM LISTE ---
st.sidebar.title("🔍 LIVE SCREENER")
screener_data = get_screener_data()

# Viser hver aktie under hinanden med data
selected_ticker = "TSLA" # Default
for item in screener_data:
    col1, col2 = st.sidebar.columns([1, 2])
    if col1.button(item['Symbol'], key=item['Symbol']):
        selected_ticker = item['Symbol']
    col2.write(f"RVOL: {item['RVOL']} | Vol: {item['Vol']}")
st.sidebar.markdown("---")

# --- 4. DATA LOGIK ---
def get_all_data(symbol):
    min_bars = alpaca.get_bars(symbol, TimeFrame.Minute, limit=300, extended_hours=True).df
    day_bars = alpaca.get_bars(symbol, TimeFrame.Day, limit=100).df
    for df in [min_bars, day_bars]:
        if not df.empty:
            df['ema9'] = ta.ema(df['close'], length=9)
            df['ema21'] = ta.ema(df['close'], length=21)
            df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
    return min_bars, day_bars

# --- 5. TERMINAL VISNING ---
st.title(f"🚀 {selected_ticker} - 233 Tick Terminal")
min_data, day_data = get_all_data(selected_ticker)

tab1, tab2 = st.tabs(["📊 1-Min / Tick Chart", "📅 Daily Candle"])

with tab1:
    if not min_data.empty:
        # Tick Hastighed (Simuleret baseret på volumen-flow)
        st.subheader("⏱️ 233-Tick Hastighed")
        tick_speed = round(233 / (min_data['volume'].iloc[-1] / 60), 2) if not min_data.empty else 0
        st.metric("Nuværende Tick-tempo", f"{tick_speed} sek", delta="-0.5s" if tick_speed < 2 else "Normal")

        fig = make_subplots(
            rows=2, cols=2, shared_xaxes=True, 
            column_widths=[0.8, 0.2], row_heights=[0.7, 0.3],
            vertical_spacing=0.03, horizontal_spacing=0.02,
            specs=[[{"secondary_y": False}, {"rowspan": 2}],
                   [{"secondary_y": False}, None]]
        )
        
        # Candlesticks, EMA 9, EMA 21, VWAP
        fig.add_trace(go.Candlestick(x=min_data.index, open=min_data['open'], high=min_data['high'], low=min_data['low'], close=min_data['close'], name="Pris"), row=1, col=1)
        fig.add_trace(go.Scatter(x=min_data.index, y=min_data['ema9'], line=dict(color='cyan', width=1), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=min_data.index, y=min_data['ema21'], line=dict(color='orange', width=1), name="EMA 21"), row=1, col=1)
        fig.add_trace(go.Scatter(x=min_data.index, y=min_data['vwap'], line=dict(color='white', width=1.5), name="VWAP"), row=1, col=1)
        
        # Volume Bars & Volume Profile
        fig.add_trace(go.Bar(x=min_data.index, y=min_data['volume'], name="Volume", marker_color="gray"), row=2, col=1)
        fig.add_trace(go.Histogram(y=min_data['close'], nbinsy=50, orientation='h', name='Vol Profile', marker_color='rgba(100, 200, 255, 0.3)'), row=1, col=2)

        fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ingen intraday data. Tjek Daily fanen for historik.")

with tab2:
    if not day_data.empty:
        fig_day = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.8, 0.2])
        fig_day.add_trace(go.Candlestick(x=day_data.index, open=day_data['open'], high=day_data['high'], low=day_data['low'], close=day_data['close'], name="Daily"), row=1, col=1)
        fig_day.add_trace(go.Bar(x=day_data.index, y=day_data['volume'], name="Volume", marker_color="royalblue"), row=2, col=1)
        fig_day.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_day, use_container_width=True)
        
