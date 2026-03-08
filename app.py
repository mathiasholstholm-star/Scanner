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

# --- 2. SCREENER DATA (Henter 5x RVOL og Volumen) ---
@st.cache_data(ttl=60)
def get_full_screener():
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
            results.append({"Symbol": symbol, "Vol": vol, "RVOL": rvol})
        except: continue
    return results

# --- 3. SIDEBAR (INGEN DROP-DOWN - KUN LISTE) ---
st.sidebar.title("🔍 SCREENER LISTE")
screener_results = get_full_screener()

# Vi bruger session_state til at holde styr på valgt aktie uden dropdown
if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = "TSLA"

for item in screener_results:
    # Laver en knap for hver aktie med tilhørende data
    label = f"{item['Symbol']} | RVOL: {item['RVOL']}"
    if st.sidebar.button(label, use_container_width=True):
        st.session_state.selected_ticker = item['Symbol']

# --- 4. DATA LOGIK ---
def get_data(symbol):
    try:
        m_bars = alpaca.get_bars(symbol, TimeFrame.Minute, limit=300, extended_hours=True).df
        d_bars = alpaca.get_bars(symbol, TimeFrame.Day, limit=100).df
        for df in [m_bars, d_bars]:
            if not df.empty:
                df['ema9'] = ta.ema(df['close'], length=9)
                df['ema21'] = ta.ema(df['close'], length=21)
                df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        return m_bars, d_bars
    except: return pd.DataFrame(), pd.DataFrame()

# --- 5. VISNING AF TERMINAL ---
ticker = st.session_state.selected_ticker
st.title(f"🚀 {ticker} Terminal")

m_data, d_data = get_data(ticker)

tab1, tab2 = st.tabs(["📊 1-Min / 233-Tick", "📅 Daily Candle"])

with tab1:
    if not m_data.empty:
        # 233-Tick Kalkulation
        last_vol = m_data['volume'].iloc[-1]
        tick_speed = round(233 / (last_vol / 60), 2) if last_vol > 0 else 0
        st.metric("⏱️ 233-Tick Tempo", f"{tick_speed} sek", help="Beregnet ud fra volumen-flow")

        fig = make_subplots(rows=2, cols=2, shared_xaxes=True, 
                            column_widths=[0.8, 0.2], row_heights=[0.7, 0.3],
                            vertical_spacing=0.03, horizontal_spacing=0.02,
                            specs=[[{"secondary_y": False}, {"rowspan": 2}],
                                   [{"secondary_y": False}, None]])

        fig.add_trace(go.Candlestick(x=m_data.index, open=m_data['open'], high=m_data['high'], low=m_data['low'], close=m_data['close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_data.index, y=m_data['ema9'], line=dict(color='cyan', width=1), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_data.index, y=m_data['ema21'], line=dict(color='orange', width=1), name="EMA 21"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_data.index, y=m_data['vwap'], line=dict(color='white', width=1.5), name="VWAP"), row=1, col=1)
        fig.add_trace(go.Bar(x=m_data.index, y=m_data['volume'], name="Vol", marker_color="gray"), row=2, col=1)
        fig.add_trace(go.Histogram(y=m_data['close'], nbinsy=50, orientation='h', marker_color='rgba(0,150,255,0.3)'), row=1, col=2)

        fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"Ingen Intraday data for {ticker} (Markedet er lukket). Skift til Daily fanen.")

with tab2:
    if not d_data.empty:
        fig_d = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.05)
        fig_d.add_trace(go.Candlestick(x=d_data.index, open=d_data['open'], high=d_data['high'], low=d_data['low'], close=d_data['close']), row=1, col=1)
        fig_d.add_trace(go.Bar(x=d_data.index, y=d_data['volume'], marker_color="royalblue"), row=2, col=1)
        fig_d.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_d, use_container_width=True)
        
