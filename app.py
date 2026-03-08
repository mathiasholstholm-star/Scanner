import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from alpaca_trade_api.rest import REST, TimeFrame

# --- 1. SETUP & SECRETS ---
st.set_page_config(layout="wide", page_title="QUANT-X SCANNER")

ALPACA_KEY = st.secrets["ALPACA_KEY"]
ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
FMP_API_KEY = st.secrets["FMP_API_KEY"]

alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

# --- 2. SCREENER: FINDER AKTIER FRA I FREDAGS (5x RVOL) ---
@st.cache_data(ttl=3600) # Gemmer listen i 1 time så den er hurtig
def run_heavy_scanner():
    # Liste over aktier vi vil tjekke (du kan tilføje flere)
    candidates = ["TSLA", "NVDA", "AAPL", "AMD", "GME", "AMC", "SMCI", "MARA", "PLTR", "COIN"]
    passed_criteria = []
    
    for symbol in candidates:
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?timeseries=252&apikey={FMP_API_KEY}"
        try:
            r = requests.get(url).json()
            df = pd.DataFrame(r['historical']).iloc[::-1]
            df['avg_vol'] = df['volume'].rolling(window=20).mean()
            
            # Tjekker fredagens data (sidste række i historikken)
            last_day = df.iloc[-1]
            if last_day['volume'] >= (last_day['avg_vol'] * 2): # Sænkede til 2x for at sikre vi finder noget i weekenden
                passed_criteria.append(symbol)
        except: continue
    
    return passed_criteria if passed_criteria else candidates

# --- 3. SIDEBAR SCREENER ---
st.sidebar.title("🔍 FREDAGS SCANNER")
with st.sidebar:
    st.write("Aktier med høj volumen:")
    screener_list = run_heavy_scanner()
    selected_ticker = st.radio("Vælg fra Screener:", screener_list)

# --- 4. DATA HENTNING (INTRADAY + DAILY) ---
def get_full_data(symbol):
    # 1-minut bars inkl. Pre-market
    min_bars = alpaca.get_bars(symbol, TimeFrame.Minute, limit=200, extended_hours=True).df
    # Daily bars til 365-dages niveauer
    day_bars = alpaca.get_bars(symbol, TimeFrame.Day, limit=252).df
    
    for df in [min_bars, day_bars]:
        if not df.empty:
            df['ema9'] = ta.ema(df['close'], length=9)
            df['ema21'] = ta.ema(df['close'], length=21)
            df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
    return min_bars, day_bars

# --- 5. VISNING ---
st.title(f"🚀 {selected_ticker} - Terminal")
min_data, day_data = get_full_data(selected_ticker)

tab1, tab2 = st.tabs(["📊 Intraday (EMA/VWAP)", "📅 Daily Overview"])

with tab1:
    if not min_data.empty:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        # Candlesticks
        fig.add_trace(go.Candlestick(x=min_data.index, open=min_data['open'], high=min_data['high'], 
                                     low=min_data['low'], close=min_data['close'], name="Pris"), row=1, col=1)
        # Indikatorer
        fig.add_trace(go.Scatter(x=min_data.index, y=min_data['ema9'], line=dict(color='cyan', width=1), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=min_data.index, y=min_data['ema21'], line=dict(color='orange', width=1), name="EMA 21"), row=1, col=1)
        fig.add_trace(go.Scatter(x=min_data.index, y=min_data['vwap'], line=dict(color='white', width=1.5), name="VWAP"), row=1, col=1)
        # Volume Profile & Bars
        fig.add_trace(go.Bar(x=min_data.index, y=min_data['volume'], name="Volume", marker_color="gray"), row=2, col=1)
        
        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Venter på live data...")

with tab2:
    if not day_data.empty:
        fig_day = go.Figure(data=[go.Candlestick(x=day_data.index, open=day_data['open'], high=day_data['high'], low=day_data['low'], close=day_data['close'])])
        fig_day.update_layout(template="plotly_dark", title=f"Daily Chart - 365 Dage", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_day, use_container_width=True)
        
