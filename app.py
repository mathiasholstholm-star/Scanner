import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from alpaca_trade_api.rest import REST, TimeFrame

# --- 1. SETUP & SIKKERHED ---
st.set_page_config(layout="wide", page_title="QUANT-X TERMINAL")

# Henter dine nøgler fra Streamlit Secrets
ALPACA_KEY = st.secrets["ALPACA_KEY"]
ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
FMP_API_KEY = st.secrets["FMP_API_KEY"]

alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

# --- 2. SCANNER-MOTOR (FINDER DINE FREDAGS-AKTIER) ---
@st.cache_data(ttl=3600)
def get_scanner_results():
    # Liste over de aktier du vil overvåge
    watchlist = ["NVDA", "TSLA", "GME", "AMD", "AAPL", "SMCI", "MARA", "PLTR"]
    found_stocks = []
    
    for symbol in watchlist:
        # Bruger din FMP nøgle til at tjekke volumen-kriterier
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?timeseries=5&apikey={FMP_API_KEY}"
        try:
            r = requests.get(url).json()
            hist = pd.DataFrame(r['historical'])
            # Tjekker om volumen i fredags var højere end gennemsnittet
            if hist.iloc[0]['volume'] > hist['volume'].mean():
                found_stocks.append(symbol)
        except:
            continue
    return found_stocks if found_stocks else watchlist

# --- 3. SIDEBAR SCREENER ---
st.sidebar.title("🔍 DIN SCANNER")
options = get_scanner_results()
# Her vælger du aktien fra din liste
selected_ticker = st.sidebar.selectbox("Vælg momentum-aktie:", options)

# --- 4. DATA-HENTNING ---
def get_clean_data(symbol):
    try:
        # Henter 1-minut bars
        bars = alpaca.get_bars(symbol, TimeFrame.Minute, limit=100, extended_hours=True).df
        if not bars.empty:
            bars['ema9'] = ta.ema(bars['close'], length=9)
            bars['ema21'] = ta.ema(bars['close'], length=21)
            bars['vwap'] = ta.vwap(bars['high'], bars['low'], bars['close'], bars['volume'])
        return bars
    except:
        return pd.DataFrame()

# --- 5. TERMINAL VISNING ---
st.title(f"🚀 {selected_ticker} Terminal") # Nu ændrer navnet sig efter dit valg!

data = get_clean_data(selected_ticker)

if not data.empty:
    # Bygger grafen med alle dine indikatorer
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    # Prisgraf (Candlesticks)
    fig.add_trace(go.Candlestick(x=data.index, open=data['open'], high=data['high'], 
                                 low=data['low'], close=data['close'], name="Pris"), row=1, col=1)
    
    # EMA & VWAP linjer
    fig.add_trace(go.Scatter(x=data.index, y=data['ema9'], line=dict(color='cyan', width=1), name="EMA 9"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['ema21'], line=dict(color='orange', width=1), name="EMA 21"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['vwap'], line=dict(color='white', width=1.5), name="VWAP"), row=1, col=1)

    # Volumen barer i bunden
    fig.add_trace(go.Bar(x=data.index, y=data['volume'], name="Volumen", marker_color="gray"), row=2, col=1)

    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    # Denne besked vises når markedet er lukket
    st.info(f"Venter på markedsåbning for {selected_ticker}. Prøv igen i morgen kl. 10:00.")
    
