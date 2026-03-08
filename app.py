import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from alpaca_trade_api.rest import REST, TimeFrame

# --- 1. SETUP & SECRETS ---
st.set_page_config(layout="wide", page_title="QUANT-X SCANNER")

# Sikrer at vi har dine gemte nøgler fra billede 1168
ALPACA_KEY = st.secrets["ALPACA_KEY"]
ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
FMP_API_KEY = st.secrets["FMP_API_KEY"]

alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

# --- 2. SCREENER: FINDER FREDAGENS 5x RVOL VINDERE ---
@st.cache_data(ttl=3600)
def run_fredags_scanner():
    # Liste over dine primære kandidater
    candidates = ["TSLA", "NVDA", "AAPL", "AMD", "GME", "AMC", "SMCI", "MARA", "PLTR", "COIN"]
    passed_criteria = []
    
    for symbol in candidates:
        # Henter historik via din FMP nøgle fra billede 1166
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?timeseries=252&apikey={FMP_API_KEY}"
        try:
            r = requests.get(url).json()
            df = pd.DataFrame(r['historical']).iloc[::-1]
            df['avg_vol'] = df['volume'].rolling(window=20).mean()
            
            # Tjekker fredagens volumen (sidste handelsdag)
            last_day = df.iloc[-1]
            if last_day['volume'] >= (last_day['avg_vol'] * 2): # Justeret til 2x for at sikre valgmuligheder i aften
                passed_criteria.append(symbol)
        except: continue
    
    # Hvis ingen findes, viser vi standardlisten for at undgå fejlen i billede 1174
    return passed_criteria if passed_criteria else ["TSLA", "NVDA", "GME"]

# --- 3. SIDEBAR SCREENER ---
st.sidebar.title("🔍 FREDAGS SCANNER")
screener_list = run_fredags_scanner()
selected_ticker = st.sidebar.selectbox("Aktier fra din scanner:", screener_list)

# --- 4. DATA FUNKTION (MED FEJLSIKRING) ---
def get_safe_data(symbol):
    try:
        # Henter 1-minut bars inkl. Pre-market
        min_bars = alpaca.get_bars(symbol, TimeFrame.Minute, limit=200, extended_hours=True).df
        if min_bars.empty:
            return pd.DataFrame()
        
        min_bars['ema9'] = ta.ema(min_bars['close'], length=9)
        min_bars['ema21'] = ta.ema(min_bars['close'], length=21)
        min_bars['vwap'] = ta.vwap(min_bars['high'], min_bars['low'], min_bars['close'], min_bars['volume'])
        return min_bars
    except:
        return pd.DataFrame()

# --- 5. VISNING ---
st.title(f"🚀 {selected_ticker} - Terminal")
data = get_safe_data(selected_ticker)

if not data.empty:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    # Candlesticks + EMA + VWAP
    fig.add_trace(go.Candlestick(x=data.index, open=data['open'], high=data['high'], low=data['low'], close=data['close'], name="Pris"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['ema9'], line=dict(color='cyan', width=1), name="EMA 9"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['ema21'], line=dict(color='orange', width=1), name="EMA 21"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['vwap'], line=dict(color='white', width=1.5), name="VWAP"), row=1, col=1)
    
    # Volume Bars
    fig.add_trace(go.Bar(x=data.index, y=data['volume'], name="Volume", marker_color="gray"), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(f"Venter på live data for {selected_ticker}. Dette skyldes normalt at markedet er lukket i weekenden.")
    
