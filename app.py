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

# --- 2. AUTOMATISK FREDAGS-LISTE (Låser data til sidste børsdag) ---
@st.cache_data(ttl=300)
def get_last_market_day_results():
    candidates = ["TSLA", "NVDA", "AAPL", "AMD", "GME", "SMCI", "MARA", "PLTR", "COIN", "RIVN"]
    results = []
    
    for symbol in candidates:
        # Henter de sidste 30 dages historik fra FMP
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?timeseries=30&apikey={FMP_API_KEY}"
        try:
            r = requests.get(url).json()
            if 'historical' not in r: continue
            
            df = pd.DataFrame(r['historical']).iloc[::-1] # Fra ældst til nyest
            df['avg_vol'] = df['volume'].rolling(window=20).mean()
            
            # Vi tager fat i den SIDSTE lukkede dag (Fredag)
            last_day = df.iloc[-1]
            prev_avg = df['avg_vol'].iloc[-2]
            rvol = round(last_day['volume'] / prev_avg, 2)
            
            # Tilføjer alle med RVOL over 1.0 til listen (sorteres senere)
            results.append({
                "Symbol": symbol, 
                "RVOL": rvol, 
                "Vol": f"{int(last_day['volume']):,}",
                "Price": last_day['close']
            })
        except: continue
    
    # Sorterer så de største bevægelser fra fredag står øverst
    return sorted(results, key=lambda x: x['RVOL'], reverse=True)

# --- 3. SIDEBAR (LISTE OVER FREDAGENS VINDERE) ---
st.sidebar.title("📅 SIDSTE BØRSDAG")
st.sidebar.write("Klik for at åbne chart:")

friday_list = get_last_market_day_results()

# Session State holder styr på hvilken aktie du har trykket på
if 'current_ticker' not in st.session_state:
    st.session_state.current_ticker = friday_list[0]['Symbol'] if friday_list else "TSLA"

for item in friday_list:
    # Laver hver aktie som en bred knap med RVOL data
    btn_text = f"{item['Symbol']} (RVOL: {item['RVOL']})"
    if st.sidebar.button(btn_text, use_container_width=True):
        st.session_state.current_ticker = item['Symbol']

# --- 4. DATA LOGIK (INTRADAY + DAILY) ---
def get_charts(symbol):
    try:
        # Henter Intraday (1-min) og Daily (365 dage)
        m_bars = alpaca.get_bars(symbol, TimeFrame.Minute, limit=300, extended_hours=True).df
        d_bars = alpaca.get_bars(symbol, TimeFrame.Day, limit=252).df
        
        for df in [m_bars, d_bars]:
            if not df.empty:
                df['ema9'] = ta.ema(df['close'], length=9)
                df['ema21'] = ta.ema(df['close'], length=21)
                df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        return m_bars, d_bars
    except: return pd.DataFrame(), pd.DataFrame()

# --- 5. TERMINAL VISNING ---
ticker = st.session_state.current_ticker
st.title(f"⚡ {ticker} Terminal")

m_data, d_data = get_charts(ticker)

tab1, tab2 = st.tabs(["📊 1-Min / 233-Tick", "📅 Daily Candle"])

with tab1:
    if not m_data.empty:
        # 233-Tick Hastighed (Baseret på seneste volumen)
        vol_now = m_data['volume'].iloc[-1]
        tick_speed = round(233 / (vol_now / 60), 2) if vol_now > 0 else 0
        st.metric("⏱️ 233-Tick Tempo", f"{tick_speed} sek")

        # Hovedgraf med Volume Profile
        fig = make_subplots(rows=2, cols=2, shared_xaxes=True, 
                            column_widths=[0.8, 0.2], row_heights=[0.7, 0.3],
                            vertical_spacing=0.03, horizontal_spacing=0.02,
                            specs=[[{"secondary_y": False}, {"rowspan": 2}],
                                   [{"secondary_y": False}, None]])

        fig.add_trace(go.Candlestick(x=m_data.index, open=m_data['open'], high=m_data['high'], low=m_data['low'], close=m_data['close'], name="1-Min"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_data.index, y=m_data['ema9'], line=dict(color='cyan', width=1), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_data.index, y=m_data['ema21'], line=dict(color='orange', width=1), name="EMA 21"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_data.index, y=m_data['vwap'], line=dict(color='white', width=1.5), name="VWAP"), row=1, col=1)
        fig.add_trace(go.Bar(x=m_data.index, y=m_data['volume'], marker_color="gray"), row=2, col=1)
        fig.add_trace(go.Histogram(y=m_data['close'], nbinsy=50, orientation='h', marker_color='rgba(0,150,255,0.2)'), row=1, col=2)

        fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Intraday grafen er tom (Markedet er lukket). Se Daily fanen for fredagens lys.")

with tab2:
    if not d_data.empty:
        fig_d = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.05)
        fig_d.add_trace(go.Candlestick(x=d_data.index, open=d_data['open'], high=d_data['high'], low=d_data['low'], close=d_data['close']), row=1, col=1)
        fig_d.add_trace(go.Bar(x=d_data.index, y=d_data['volume'], marker_color="royalblue"), row=2, col=1)
        fig_d.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_d, use_container_width=True)
        
