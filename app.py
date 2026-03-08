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

# --- 2. SCREENER (Sikret mod tomme data) ---
@st.cache_data(ttl=3600)
def get_screener_data():
    stocks = ["TSLA", "NVDA", "AAPL", "AMD", "GME", "SMCI", "MARA", "PLTR", "COIN", "RIVN"]
    results = []
    
    for s in stocks:
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{s}?timeseries=30&apikey={FMP_API_KEY}"
        try:
            r = requests.get(url).json()
            if 'historical' in r:
                df = pd.DataFrame(r['historical']).iloc[::-1]
                df['avg_vol'] = df['volume'].rolling(window=20).mean()
                
                last_day = df.iloc[-1] # Fredag
                prev_avg = df['avg_vol'].iloc[-2] if len(df) > 1 else 1
                
                rvol = round(last_day['volume'] / prev_avg, 2) if prev_avg > 0 else 0
                
                # Viser dem der har haft over 1.0 RVOL (du kan stramme den til 5 senere)
                if rvol >= 1.0: 
                    results.append({"Symbol": s, "RVOL": rvol, "Vol": last_day['volume']})
        except Exception:
            continue
            
    # Nødsikring: Hvis API'en er nede, smider vi en backup-liste, så appen ikke dør
    if not results:
        return [{"Symbol": "NVDA", "RVOL": 0.0, "Vol": 0}, {"Symbol": "TSLA", "RVOL": 0.0, "Vol": 0}]
        
    return sorted(results, key=lambda x: x['RVOL'], reverse=True)

# --- 3. SIDEBAR (Knapper under hinanden) ---
st.sidebar.title("🔍 FREDAGS SCREENER")
screener_list = get_screener_data()

# Låser sig fast på aktien
if 'active_ticker' not in st.session_state:
    st.session_state.active_ticker = screener_list[0]['Symbol']

for item in screener_list:
    label = f"{item['Symbol']} | RVOL: {item['RVOL']}"
    if st.sidebar.button(label, use_container_width=True):
        st.session_state.active_ticker = item['Symbol']

ticker = st.session_state.active_ticker

# --- 4. DATA LOGIK (Tvinger den tilbage til fredag) ---
def fetch_data(symbol):
    try:
        # 2000 minutter er nok til at spænde over en hel weekend og hente fredag!
        m = alpaca.get_bars(symbol, TimeFrame.Minute, limit=2000, extended_hours=True).df
        d = alpaca.get_bars(symbol, TimeFrame.Day, limit=252).df
        
        for df in [m, d]:
            if not df.empty:
                df['ema9'] = ta.ema(df['close'], length=9)
                df['ema21'] = ta.ema(df['close'], length=21)
                df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        return m, d
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

# --- 5. VISNING ---
st.title(f"⚡ {ticker} PRO TERMINAL")
m_data, d_data = fetch_data(ticker)

tab1, tab2 = st.tabs(["📊 INTRADAY / TICK", "📅 DAILY CANDLE"])

with tab1:
    if not m_data.empty:
        # For ikke at vise 2000 minutter og crashe skærmen, plotter vi kun de sidste 300 minutter af fredagen
        m_plot = m_data.tail(300)
        
        # 233-Tick Tæller
        v = m_plot['volume'].iloc[-1]
        t_speed = round(233 / (v / 60), 2) if v > 0 else 0
        st.metric("⏱️ 233-TICK HASTIGHED", f"{t_speed}s")

        fig = make_subplots(rows=2, cols=2, shared_xaxes=True, 
                            column_widths=[0.8, 0.2], row_heights=[0.7, 0.3],
                            vertical_spacing=0.03, horizontal_spacing=0.02,
                            specs=[[{"secondary_y": False}, {"rowspan": 2}],
                                   [{"secondary_y": False}, None]])

        # Candlesticks og Indikatorer
        fig.add_trace(go.Candlestick(x=m_plot.index, open=m_plot['open'], high=m_plot['high'], low=m_plot['low'], close=m_plot['close'], name="1-Min"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_plot.index, y=m_plot['ema9'], line=dict(color='cyan', width=1), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_plot.index, y=m_plot['ema21'], line=dict(color='orange', width=1), name="EMA 21"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_plot.index, y=m_plot['vwap'], line=dict(color='white', width=1.5), name="VWAP"), row=1, col=1)
        
        # Volume Bars og Volume Profile
        fig.add_trace(go.Bar(x=m_plot.index, y=m_plot['volume'], marker_color="gray", name="Vol"), row=2, col=1)
        fig.add_trace(go.Histogram(y=m_plot['close'], nbinsy=50, orientation='h', marker_color='rgba(100,200,255,0.2)', name="Profile"), row=1, col=2)

        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Alpaca returnerede ingen data for {ticker}. Prøv en anden aktie.")

with tab2:
    if not d_data.empty:
        fig_d = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.05)
        fig_d.add_trace(go.Candlestick(x=d_data.index, open=d_data['open'], high=d_data['high'], low=d_data['low'], close=d_data['close']), row=1, col=1)
        fig_d.add_trace(go.Bar(x=d_data.index, y=d_data['volume'], marker_color="royalblue"), row=2, col=1)
        fig_d.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_d, use_container_width=True)
        
