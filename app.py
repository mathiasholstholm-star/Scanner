import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from alpaca_trade_api.rest import REST, TimeFrame
from datetime import datetime, timedelta

# --- 1. SETUP ---
st.set_page_config(layout="wide", page_title="QUANT-X TERMINAL")

ALPACA_KEY = st.secrets["ALPACA_KEY"]
ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
FMP_API_KEY = st.secrets["FMP_API_KEY"]

# Vi bruger 'paper' url til gratis konti
alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

# --- 2. SCREENER (Opdateret til nyeste FMP API) ---
@st.cache_data(ttl=3600)
def get_screener_list():
    # Vi bruger en fast liste over de vigtigste momentum aktier
    stocks = ["TSLA", "NVDA", "AAPL", "AMD", "GME", "SMCI", "MARA", "PLTR", "COIN"]
    results = []
    
    for s in stocks:
        # NYT ENDPOINT FORMAT HER
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{s}?apikey={FMP_API_KEY}"
        try:
            r = requests.get(url).json()
            if 'historical' in r:
                df = pd.DataFrame(r['historical']).head(20) # Sidste 20 dage
                df = df.iloc[::-1] # Vend om til kronologisk
                
                avg_vol = df['volume'].mean()
                last_vol = df.iloc[-1]['volume']
                rvol = round(last_vol / avg_vol, 2)
                
                results.append({"Symbol": s, "RVOL": rvol})
        except: continue
    return sorted(results, key=lambda x: x['RVOL'], reverse=True) if results else [{"Symbol": "TSLA", "RVOL": 1.0}]

# --- 3. SIDEBAR LISTE ---
st.sidebar.title("🔍 MOMENTUM LISTE")
screener_results = get_screener_list()

if 'active_ticker' not in st.session_state:
    st.session_state.active_ticker = "TSLA"

for item in screener_results:
    if st.sidebar.button(f"{item['Symbol']} | RVOL: {item['RVOL']}", use_container_width=True):
        st.session_state.active_ticker = item['Symbol']

ticker = st.session_state.active_ticker

# --- 4. DATA HENTNING (Sikret mod 15-min forsinkelse) ---
def get_safe_data(symbol):
    try:
        # VI SKAL GÅ 20 MINUTTER TILBAGE FOR AT UNDGÅ SIP-FEJL PÅ GRATIS KONTO
        now = datetime.now() - timedelta(minutes=20)
        start_date = (now - timedelta(days=4)).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Henter 1-min data (Uden extended_hours da det kræver betaling)
        m_bars = alpaca.get_bars(symbol, TimeFrame.Minute, start=start_date, end=end_date, limit=1000).df
        # Henter Daily data
        d_bars = alpaca.get_bars(symbol, TimeFrame.Day, limit=100).df
        
        for df in [m_bars, d_bars]:
            if not df.empty:
                df['ema9'] = ta.ema(df['close'], length=9)
                df['ema21'] = ta.ema(df['close'], length=21)
                df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        return m_bars, d_bars
    except Exception as e:
        st.error(f"Data-hentning fejlede: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- 5. VISNING ---
st.title(f"🚀 {ticker} Terminal")
m_data, d_data = get_safe_data(ticker)

tab1, tab2 = st.tabs(["📊 Intraday & 233-Tick", "📅 Daily Chart"])

with tab1:
    if not m_data.empty:
        # Plot kun de sidste 200 bars for overblik
        m_plot = m_data.tail(200)
        
        # 233-Tick (Beregnet ud fra volumen hastighed)
        last_v = m_plot['volume'].iloc[-1]
        t_speed = round(233 / (last_v / 60), 2) if last_v > 0 else 0
        st.metric("⏱️ Estimeret 233-Tick Tempo", f"{t_speed}s")

        fig = make_subplots(rows=2, cols=2, shared_xaxes=True, 
                            column_widths=[0.8, 0.2], row_heights=[0.7, 0.3],
                            vertical_spacing=0.03, horizontal_spacing=0.02,
                            specs=[[{"secondary_y": False}, {"rowspan": 2}],
                                   [{"secondary_y": False}, None]])

        fig.add_trace(go.Candlestick(x=m_plot.index, open=m_plot['open'], high=m_plot['high'], low=m_plot['low'], close=m_plot['close'], name="Pris"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_plot.index, y=m_plot['ema9'], line=dict(color='cyan', width=1), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_plot.index, y=m_plot['ema21'], line=dict(color='orange', width=1), name="EMA 21"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_plot.index, y=m_plot['vwap'], line=dict(color='white', width=1.5), name="VWAP"), row=1, col=1)
        fig.add_trace(go.Bar(x=m_plot.index, y=m_plot['volume'], marker_color="gray"), row=2, col=1)
        fig.add_trace(go.Histogram(y=m_plot['close'], nbinsy=50, orientation='h', marker_color='rgba(100,200,255,0.2)'), row=1, col=2)

        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Venter på forsinkede data (15 min). Tjek Daily fanen for historik.")

with tab2:
    if not d_data.empty:
        fig_d = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2])
        fig_d.add_trace(go.Candlestick(x=d_data.index, open=d_data['open'], high=d_data['high'], low=d_data['low'], close=d_data['close']), row=1, col=1)
        fig_d.add_trace(go.Bar(x=d_data.index, y=d_data['volume'], marker_color="royalblue"), row=2, col=1)
        fig_d.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_d, use_container_width=True)
        
