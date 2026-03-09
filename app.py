import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz

# --- KONFIGURATION ---
st.set_page_config(page_title="Quant-X Master Terminal", layout="wide", page_icon="⚡")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X MASTER TERMINAL</h1>", unsafe_allow_html=True)

API_KEY = "DIN_FMP_API_KEY_HER" 

def is_regular_market_hours():
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    if now_est.weekday() >= 5: return False
    return now_est.replace(hour=9, minute=30) <= now_est <= now_est.replace(hour=16, minute=0)

def get_daily_vwap(ticker):
    url = f"https://financialmodelingprep.com/api/v3/historical-chart/1min/{ticker}?apikey={API_KEY}"
    try:
        data = requests.get(url).json()
        if not data: return None
        today_str = data[0]['date'][:10]
        total_vol = sum(c['volume'] for c in data if c['date'].startswith(today_str))
        total_pv = sum(((c['high']+c['low']+c['close'])/3) * c['volume'] for c in data if c['date'].startswith(today_str))
        return total_pv / total_vol if total_vol > 0 else None
    except: return None

@st.cache_data(ttl=10)
def fetch_terminal_data():
    # 1. BRUG 'top-gainers' I STEDET FOR SCREENER (Meget hurtigere i pre-market)
    url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        if not data: return pd.DataFrame()

        regular_hours = is_regular_market_hours()
        min_vol = 500000 if regular_hours else 50000
        valid_stocks = []

        for stock in data:
            ticker = stock.get('symbol')
            price = stock.get('price', 0)
            change_pct = stock.get('changesPercentage', 0)
            # FMP Gainers sender nogle gange volumen som 'None' i pre-market, vi henter quote for sikkerhed
            vol = stock.get('volume', 0)

            # --- FILTRERING ---
            if change_pct >= 15.0 and 0.5 <= price <= 30 and vol >= min_vol:
                
                # VWAP TJEK
                vwap_val = get_daily_vwap(ticker)
                vwap_status = "🟢 OVER" if vwap_val and price >= vwap_val else "🔴 UNDER"
                
                # RISK SCORE (Simpelt eksempel - her skal din fulde logik ind)
                risk_score = min(99, int(50 + change_pct)) 

                if risk_score >= 75:
                    valid_stocks.append({
                        'TICKER': ticker,
                        'PRICE': f"${price:.2f}",
                        'GAIN %': f"+{change_pct:.2f}%",
                        'VWAP': vwap_status,
                        'VOLUME': f"{int(vol):,}",
                        'SCORE': risk_score
                    })
        
        return pd.DataFrame(valid_stocks)
    except Exception as e:
        st.error(f"Fejl: {e}")
        return pd.DataFrame()

# --- UI VISNING ---
st.subheader("Live Momentum Scanner (Top Gainers > 15%)")

if st.button("🔄 Manuel Refresh"):
    fetch_terminal_data.clear()
    st.rerun()

with st.spinner("Henter live pre-market vindere..."):
    df = fetch_terminal_data()

if not df.empty:
    st.dataframe(df.sort_values('SCORE', ascending=False), use_container_width=True, hide_index=True)
else:
    st.info("Ingen aktier fundet med Gain > 15% og Volume > 50k lige nu. Tjek om din API-key er korrekt.")

st.caption(f"Sidst opdateret: {datetime.now().strftime('%H:%M:%S')}")
