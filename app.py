import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from alpaca_trade_api.rest import REST, TimeFrame

# --- 1. SETUP ---
st.set_page_config(layout="wide", page_title="QUANT-X SCREENER")

ALPACA_KEY = st.secrets["ALPACA_KEY"]
ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
FMP_API_KEY = st.secrets["FMP_API_KEY"]

alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

# --- 2. SCREENER LOGIK (Finder Top Gainers/Volume) ---
def get_screener_list():
    # Her henter vi en liste over aktive aktier. 
    # Du kan også manuelt skrive din favoritliste her:
    watchlist = ["TSLA", "NVDA", "AAPL", "AMD", "MSFT", "GME", "AMC", "SMCI"]
    return watchlist

# --- 3. SIDEBAR SCREENER ---
st.sidebar.title("🔍 QUANT-X SCREENER")
st.sidebar.write("Vælg en aktie fra listen:")

# Opretter knapper for hver aktie i din screener
watchlist = get_screener_list()
selected_ticker = st.sidebar.radio("Top Momentum:", watchlist)

# --- 4. DATA & GRAF LOGIK ---
def get_data(symbol):
    df = alpaca.get_bars(symbol, TimeFrame.Minute, limit=200, extended_hours=True).df
    if not df.empty:
        df['ema9'] = ta.ema(df['close'], length=9)
        df['ema21'] = ta.ema(df['close'], length=21)
        df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
    return df

# --- 5. VISNING ---
st.title(f"⚡ Terminal: {selected_ticker}")

data = get_data(selected_ticker)

if not data.empty:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    # Pris, EMA og VWAP
    fig.add_trace(go.Candlestick(x=data.index, open=data['open'], high=data['high'], low=data['low'], close=data['close'], name="Pris"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['ema9'], line=dict(color='cyan', width=1), name="EMA 9"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['ema21'], line=dict(color='orange', width=1), name="EMA 21"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['vwap'], line=dict(color='white', width=1.5), name="VWAP"), row=1, col=1)
    
    # Volume
    fig.add_trace(go.Bar(x=data.index, y=data['volume'], name="Volume", marker_color="gray"), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Venter på markedsdata for " + selected_ticker)
    
