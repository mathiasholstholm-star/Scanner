import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from alpaca_trade_api.rest import REST, TimeFrame

# --- 1. SETUP ---
st.set_page_config(layout="wide", page_title="QUANT-X ULTIMATE")

ALPACA_KEY = st.secrets["ALPACA_KEY"]
ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
FMP_API_KEY = st.secrets["FMP_API_KEY"]

alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

# --- 2. SCREENER-MOTOR (Finder Fredagens setups med 5x RVOL) ---
@st.cache_data(ttl=3600)
def run_friday_screener():
    # En bred liste af kandidater at scanne igennem
    candidates = ["TSLA", "NVDA", "AAPL", "AMD", "GME", "SMCI", "MARA", "PLTR", "COIN", "RIVN", "NIO", "BA", "META"]
    results = []
    
    for symbol in candidates:
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?timeseries=30&apikey={FMP_API_KEY}"
        try:
            r = requests.get(url).json()
            df = pd.DataFrame(r['historical']).iloc[::-1] # Ældst til nyest
            df['avg_vol'] = df['volume'].rolling(window=20).mean()
            
            # Fredagens data (sidste række i historikken)
            friday = df.iloc[-1]
            prev_avg = df['avg_vol'].iloc[-2]
            rvol = round(friday['volume'] / prev_avg, 2)
            
            # Kriterie: Gemmer dem der har momentum (Du kan rette 1.0 til 5.0 for din 5x RVOL)
            if rvol >= 1.0: 
                results.append({"Symbol": symbol, "RVOL": rvol, "Vol": friday['volume']})
        except: continue
    
    # Sorterer så dem med højest RVOL står øverst
    return sorted(results, key=lambda x: x['RVOL'], reverse=True)

# --- 3. SIDEBAR (LISTE-VIEW) ---
st.sidebar.title("🔍 FREDAGS SCREENER")
screener_list = run_friday_screener()

if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = screener_list[0]['Symbol'] if screener_list else "TSLA"

for item in screener_list:
    # Viser hver aktie som en stor knap med data under hinanden
    btn_label = f"PROFIL: {item['Symbol']} | RVOL: {item['RVOL']}"
    if st.sidebar.button(btn_label, use_container_width=True):
        st.session_state.selected_ticker = item['Symbol']

# --- 4. DATA LOGIK (Intraday & Daily) ---
def get_full_data(symbol):
    try:
        # Henter 1-min bars (Extended for Pre-market) og Daily bars
        m_bars = alpaca.get_bars(symbol, TimeFrame.Minute, limit=300, extended_hours=True).df
        d_bars = alpaca.get_bars(symbol, TimeFrame.Day, limit=252).df
        
        for df in [m_bars, d_bars]:
            if not df.empty:
                df['ema9'] = ta.ema(df['close'], length=9)
                df['ema21'] = ta.ema(df['close'], length=21)
                df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        return m_bars, d_bars
    except:
        return pd.DataFrame(), pd.DataFrame()

# --- 5. VISNING ---
ticker = st.session_state.selected_ticker
st.title(f"⚡ {ticker} - Terminal")

m_data, d_data = get_full_data(ticker)

tab1, tab2 = st.tabs(["📊 Intraday & 233-Tick", "📅 Daily Candle Chart"])

with tab1:
    if not m_data.empty:
        # 233-Tick Kalkulator
        last_vol = m_data['volume'].iloc[-1]
        tick_speed = round(233 / (last_vol / 60), 2) if last_vol > 0 else 0
        st.metric("⏱️ 233-Tick Hastighed", f"{tick_speed}s", delta="-0.2s" if tick_speed < 1.0 else None)

        # Hovedgraf med 2 kolonner (Graf + Volume Profile)
        fig = make_subplots(rows=2, cols=2, shared_xaxes=True, 
                            column_widths=[0.8, 0.2], row_heights=[0.7, 0.3],
                            vertical_spacing=0.03, horizontal_spacing=0.02,
                            specs=[[{"secondary_y": False}, {"rowspan": 2}],
                                   [{"secondary_y": False}, None]])

        # 1-Min Candlesticks
        fig.add_trace(go.Candlestick(x=m_data.index, open=m_data['open'], high=m_data['high'], 
                                     low=m_data['low'], close=m_data['close'], name="1-Min"), row=1, col=1)
        
        # EMA 9, EMA 21 & VWAP
        fig.add_trace(go.Scatter(x=m_data.index, y=m_data['ema9'], line=dict(color='cyan', width=1), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_data.index, y=m_data['ema21'], line=dict(color='orange', width=1), name="EMA 21"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_data.index, y=m_data['vwap'], line=dict(color='white', width=1.5), name="VWAP"), row=1, col=1)

        # Volume Bars (Bund)
        fig.add_trace(go.Bar(x=m_data.index, y=m_data['volume'], name="Volume", marker_color="gray"), row=2, col=1)

        # Volume Profile (Højre side)
        fig.add_trace(go.Histogram(y=m_data['close'], nbinsy=50, orientation='h', name='Vol Profile', 
                                   marker_color='rgba(100, 200, 255, 0.3)'), row=1, col=2)

        fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"Ingen intraday data for {ticker}. Tjek Daily fanen for at se fredagens setup.")

with tab2:
    if not d_data.empty:
        fig_d = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.05)
        # Daily Candles
        fig_d.add_trace(go.Candlestick(x=d_data.index, open=d_data['open'], high=d_data['high'], 
                                       low=d_data['low'], close=d_data['close']), row=1, col=1)
        # Daily Volume
        fig_d.add_trace(go.Bar(x=d_data.index, y=d_data['volume'], marker_color="royalblue"), row=2, col=1)
        
        fig_d.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, title="365 Dages Historik")
        st.plotly_chart(fig_d, use_container_width=True)
        
