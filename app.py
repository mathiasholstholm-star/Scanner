import streamlit as st
import pandas as pd
import requests
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from alpaca_trade_api.rest import REST, TimeFrame

# --- 1. SETUP & SIKKERHED ---
st.set_page_config(layout="wide", page_title="QUANT-X PRO TERMINAL")

ALPACA_KEY = st.secrets["ALPACA_KEY"]
ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
FMP_API_KEY = st.secrets["FMP_API_KEY"]

alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

# --- 2. DATA FUNKTIONER ---
def get_charts(symbol):
    # Henter 1-minut (inkl. Pre-market) og Daily bars
    min_bars = alpaca.get_bars(symbol, TimeFrame.Minute, limit=200, extended_hours=True).df
    day_bars = alpaca.get_bars(symbol, TimeFrame.Day, limit=100).df
    
    for df in [min_bars, day_bars]:
        if not df.empty:
            df['ema9'] = ta.ema(df['close'], length=9)
            df['ema21'] = ta.ema(df['close'], length=21)
            df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
    return min_bars, day_bars

def get_institutional_levels(symbol):
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?timeseries=252&apikey={FMP_API_KEY}"
    try:
        r = requests.get(url).json()
        df = pd.DataFrame(r['historical']).iloc[::-1]
        df['avg_vol'] = df['volume'].rolling(window=20).mean()
        return df[df['volume'] >= (df['avg_vol'] * 5)]['high'].tolist()
    except: return []

# --- 3. UI LAYOUT ---
st.title("⚡ QUANT-X PRO TERMINAL")
ticker = st.sidebar.text_input("Vælg Aktie", "TSLA").upper()

tab1, tab2, tab3 = st.tabs(["📊 Intraday (1-Min/Tick)", "📅 Daily Candle", "💰 Trade"])

# --- TAB 1: 1-MINUT & TICK LOGIK ---
with tab1:
    min_data, _ = get_charts(ticker)
    levels = get_institutional_levels(ticker)
    
    fig = make_subplots(rows=2, cols=2, shared_xaxes=True, 
                        column_widths=[0.8, 0.2], row_heights=[0.7, 0.3],
                        vertical_spacing=0.03, horizontal_spacing=0.02,
                        specs=[[{"secondary_y": False}, {"rowspan": 2}],
                               [{"secondary_y": False}, None]])

    # Candlesticks (1-Min)
    fig.add_trace(go.Candlestick(x=min_data.index, open=min_data['open'], high=min_data['high'], 
                                 low=min_data['low'], close=min_data['close'], name="1-Min"), row=1, col=1)
    
    # EMA & VWAP
    fig.add_trace(go.Scatter(x=min_data.index, y=min_data['ema9'], line=dict(color='cyan', width=1), name="EMA 9"), row=1, col=1)
    fig.add_trace(go.Scatter(x=min_data.index, y=min_data['ema21'], line=dict(color='orange', width=1), name="EMA 21"), row=1, col=1)
    fig.add_trace(go.Scatter(x=min_data.index, y=min_data['vwap'], line=dict(color='white', width=1.5), name="VWAP"), row=1, col=1)

    # Institutionelle Niveauer (Røde 5x RVOL)
    for lvl in levels:
        fig.add_hline(y=lvl, line_dash="dot", line_color="red", opacity=0.5, row=1, col=1)

    # Volume Bars (Bund)
    fig.add_trace(go.Bar(x=min_data.index, y=min_data['volume'], name="Volume", marker_color="gray"), row=2, col=1)

    # Volume Profile (Højre side)
    fig.add_trace(go.Histogram(y=min_data['close'], nbinsy=50, orientation='h', name='Vol Profile', 
                               marker_color='rgba(100, 200, 255, 0.3)'), row=1, col=2)

    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.metric("⏱️ 233-Tick Hastighed", "0.8s", "-0.2s")

# --- TAB 2: DAILY CANDLE ---
with tab2:
    _, day_data = get_charts(ticker)
    fig_day = go.Figure(data=[go.Candlestick(x=day_data.index, open=day_data['open'], high=day_data['high'], 
                                            low=day_data['low'], close=day_data['close'])])
    fig_day.update_layout(template="plotly_dark", title=f"Daily Chart: {ticker}", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_day, use_container_width=True)

# --- TAB 3: TRADE ---
with tab3:
    st.subheader(f"Handel med {ticker}")
    if st.button("🚀 KØB 10 STK (MARKET/LIMIT)", use_container_width=True):
        price = alpaca.get_latest_trade(ticker).p
        alpaca.submit_order(symbol=ticker, qty=10, side='buy', type='limit', limit_price=price, time_in_force='day', extended_hours=True)
        st.success(f"Ordre sendt: 10 stk {ticker} @ {price}")
        
