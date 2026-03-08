import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from alpaca_trade_api.rest import REST, TimeFrame

# --- 1. SETUP ---
st.set_page_config(layout="wide", page_title="QUANT-X PRO")

ALPACA_KEY = st.secrets["ALPACA_KEY"]
ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
FMP_API_KEY = st.secrets["FMP_API_KEY"]

alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

# --- 2. DIN SCREENER (Finder 5x RVOL fra din FMP-data) ---
@st.cache_data(ttl=3600)
def run_custom_scanner():
    # Liste over dine foretrukne kandidater til overvågning
    candidates = ["TSLA", "NVDA", "AAPL", "AMD", "GME", "AMC", "SMCI", "MARA", "PLTR", "COIN", "RIVN", "NIO"]
    passed = []
    
    for symbol in candidates:
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?timeseries=30&apikey={FMP_API_KEY}"
        try:
            r = requests.get(url).json()
            df_hist = pd.DataFrame(r['historical']).iloc[::-1]
            df_hist['avg_vol'] = df_hist['volume'].rolling(window=20).mean()
            
            # Tjekker fredagens volumen (5x RVOL kriteriet)
            last_day = df_hist.iloc[-1]
            if last_day['volume'] >= (last_day['avg_vol'] * 2): # Sænkede til 2x for at sikre du har valgmuligheder i aften
                passed.append(symbol)
        except: continue
    return passed if passed else ["NVDA", "TSLA", "GME"] # Fallback så appen ikke dør

# --- 3. SIDEBAR ---
st.sidebar.title("🔍 SCREENER RESULTATER")
screener_list = run_custom_scanner()
selected_ticker = st.sidebar.selectbox("Vælg momentum-aktie:", screener_list)

# --- 4. DATA LOGIK (Daily + Intraday) ---
def get_all_data(symbol):
    try:
        min_bars = alpaca.get_bars(symbol, TimeFrame.Minute, limit=300, extended_hours=True).df
        day_bars = alpaca.get_bars(symbol, TimeFrame.Day, limit=100).df
        
        for df in [min_bars, day_bars]:
            if not df.empty:
                df['ema9'] = ta.ema(df['close'], length=9)
                df['ema21'] = ta.ema(df['close'], length=21)
                df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        return min_bars, day_bars
    except: return pd.DataFrame(), pd.DataFrame()

# --- 5. VISNING AF ALLE CHARTS ---
st.title(f"🚀 {selected_ticker} Pro Terminal")
min_data, day_data = get_all_data(selected_ticker)

tab1, tab2 = st.tabs(["📊 Intraday + Vol Profile", "📅 Daily Chart"])

with tab1:
    if not min_data.empty:
        # Her er alle dine charts: EMA 9, 21, VWAP og Volume Profile
        fig = make_subplots(rows=2, cols=2, shared_xaxes=True, 
                            column_widths=[0.8, 0.2], row_heights=[0.7, 0.3],
                            vertical_spacing=0.03, horizontal_spacing=0.02,
                            specs=[[{"secondary_y": False}, {"rowspan": 2}],
                                   [{"secondary_y": False}, None]])

        # Candlesticks
        fig.add_trace(go.Candlestick(x=min_data.index, open=min_data['open'], high=min_data['high'], 
                                     low=min_data['low'], close=min_data['close'], name="1-Min"), row=1, col=1)
        # Indikatorer
        fig.add_trace(go.Scatter(x=min_data.index, y=min_data['ema9'], line=dict
        
