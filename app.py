import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from alpaca_trade_api.rest import REST, TimeFrame

# --- 1. SETUP & SECRETS ---
st.set_page_config(layout="wide", page_title="QUANT-X TERMINAL")

ALPACA_KEY = st.secrets["ALPACA_KEY"]
ALPACA_SECRET = st.secrets["ALPACA_SECRET"]
FMP_API_KEY = st.secrets["FMP_API_KEY"]

alpaca = REST(ALPACA_KEY, ALPACA_SECRET, base_url='https://paper-api.alpaca.markets')

# --- 2. SCREENER (Finder Fredagens 5x RVOL setups) ---
@st.cache_data(ttl=3600)
def get_friday_screener():
    # Liste over dine vigtigste aktier
    stocks = ["TSLA", "NVDA", "GME", "AMD", "AAPL", "SMCI", "MARA", "PLTR", "COIN"]
    results = []
    for s in stocks:
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{s}?timeseries=30&apikey={FMP_API_KEY}"
        try:
            r = requests.get(url).json()
            df = pd.DataFrame(r['historical']).iloc[::-1]
            df['avg_vol'] = df['volume'].rolling(window=20).mean()
            last = df.iloc[-1] # Fredag
            rvol = round(last['volume'] / df['avg_vol'].iloc[-2], 2)
            results.append({"Symbol": s, "RVOL": rvol, "Price": last['close']})
        except: continue
    return sorted(results, key=lambda x: x['RVOL'], reverse=True)

# --- 3. SIDEBAR (FAST LISTE - INGEN DROPDOWN) ---
st.sidebar.title("🔍 FREDAGS SCREENER")
screener_list = get_friday_screener()

if 'active_ticker' not in st.session_state:
    st.session_state.active_ticker = "TSLA"

for item in screener_list:
    # Hver aktie er en stor knap i sidebaren
    label = f"{item['Symbol']} | RVOL: {item['RVOL']}"
    if st.sidebar.button(label, use_container_width=True, key=f"btn_{item['Symbol']}"):
        st.session_state.active_ticker = item['Symbol']

# --- 4. DATA HENTNING ---
ticker = st.session_state.active_ticker
def load_all_data(s):
    try:
        # Intraday (til 233-tick og VWAP) + Daily (til Daily Chart)
        m = alpaca.get_bars(s, TimeFrame.Minute, limit=300, extended_hours=True).df
        d = alpaca.get_bars(s, TimeFrame.Day, limit=252).df
        for df in [m, d]:
            if not df.empty:
                df['ema9'] = ta.ema(df['close'], length=9)
                df['ema21'] = ta.ema(df['close'], length=21)
                df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        return m, d
    except: return pd.DataFrame(), pd.DataFrame()

# --- 5. TERMINAL VISNING ---
st.title(f"⚡ {ticker} PRO TERMINAL")
m_data, d_data = load_all_data(ticker)

t1, t2 = st.tabs(["📊 INTRADAY / TICK", "📅 DAILY CANDLE"])

with t1:
    if not m_data.empty:
        # 233-TICK MÅLER (Baseret på seneste volumen-flow)
        v = m_data['volume'].iloc[-1]
        t_speed = round(233 / (v / 60), 2) if v > 0 else 0
        st.metric("⏱️ 233-TICK HASTIGHED", f"{t_speed}s")

        fig = make_subplots(rows=2, cols=2, shared_xaxes=True, 
                            column_widths=[0.8, 0.2], row_heights=[0.7, 0.3],
                            vertical_spacing=0.03, horizontal_spacing=0.02,
                            specs=[[{"secondary_y": False}, {"rowspan": 2}],
                                   [{"secondary_y": False}, None]])

        # Pris & Indikatorer
        fig.add_trace(go.Candlestick(x=m_data.index, open=m_data['open'], high=m_data['high'], low=m_data['low'], close=m_data['close'], name="1-Min"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_data.index, y=m_data['ema9'], line=dict(color='cyan', width=1), name="EMA 9"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_data.index, y=m_data['ema21'], line=dict(color='orange', width=1), name="EMA 21"), row=1, col=1)
        fig.add_trace(go.Scatter(x=m_data.index, y=m_data['vwap'], line=dict(color='white', width=1.5), name="VWAP"), row=1, col=1)
        
        # Volume & Profile
        fig.add_trace(go.Bar(x=m_data.index, y=m_data['volume'], marker_color="gray"), row=2, col=1)
        fig.add_trace(go.Histogram(y=m_data['close'], nbinsy=50, orientation='h', marker_color='rgba(100,200,255,0.2)'), row=1, col=2)

        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Markedet er lukket. Skift til 'DAILY CANDLE' fanen for at se fredagens setup.")

with t2:
    if not d_data.empty:
        fig_d = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.05)
        fig_d.add_trace(go.Candlestick(x=d_data.index, open=d_data['open'], high=d_data['high'], low=d_data['low'], close=d_data['close']), row=1, col=1)
        fig_d.add_trace(go.Bar(x=d_data.index, y=d_data['volume'], marker_color="royalblue"), row=2, col=1)
        fig_d.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_d, use_container_width=True)
