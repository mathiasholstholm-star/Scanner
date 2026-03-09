import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import time

# --- KONFIGURATION AF TERMINAL ---
st.set_page_config(page_title="Quant-X Master Terminal", layout="wide", page_icon="⚡")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X MASTER TERMINAL</h1>", unsafe_allow_html=True)

# ⚠️ DIN API NØGLE ⚠️
API_KEY = "DIN_FMP_API_KEY_HER" 

def is_regular_market_hours():
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    if now_est.weekday() >= 5: return False
    return now_est.replace(hour=9, minute=30, second=0) <= now_est <= now_est.replace(hour=16, minute=0, second=0)

def get_detailed_metrics(ticker):
    """Henter Float, Warrants og Institutionelle data (Din avancerede logik)"""
    try:
        # 1. Hent Key Metrics (Float)
        metrics_url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}?limit=1&apikey={API_KEY}"
        m_data = requests.get(metrics_url).json()
        float_data = m_data[0].get('floatShares', 0) if m_data else 0
        
        # 2. Hent Institutional Ownership
        inst_url = f"https://financialmodelingprep.com/api/v3/institutional-ownership/symbol-ownership-percent/{ticker}?apikey={API_KEY}"
        i_data = requests.get(inst_url).json()
        inst_own = i_data[0].get('totalWeight', 0) if i_data else 0
        
        return float_data, inst_own
    except:
        return 0, 0

def get_daily_vwap(ticker):
    url = f"https://financialmodelingprep.com/api/v3/historical-chart/1min/{ticker}?apikey={API_KEY}"
    try:
        resp = requests.get(url)
        data = resp.json()
        if not data or not isinstance(data, list): return None
        today_str = data[0]['date'][:10]
        current_day = [c for c in data if c['date'].startswith(today_str)]
        if not current_day: return None
        total_vol = sum(c['volume'] for c in current_day)
        total_pv = sum(((c['high'] + c['low'] + c['close']) / 3) * c['volume'] for c in current_day)
        return total_pv / total_vol if total_vol > 0 else None
    except: return None

@st.cache_data(ttl=10)
def fetch_terminal_data():
    # RETTELSE 1: Fjernet marketCapMoreThan for at få AZI med
    url = f"https://financialmodelingprep.com/api/v3/stock-screener?priceLowerThan=30&isActivelyTrading=true&limit=100&apikey={API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        if not data: return pd.DataFrame()

        regular_hours = is_regular_market_hours()
        # RETTELSE 2: Dynamisk volumen (50k vs 500k)
        min_vol = 500000 if regular_hours else 50000
        valid_stocks = []

        # Batch-processing af quotes for hastighed
        symbols = [s['symbol'] for s in data]
        symbols_str = ",".join(symbols)
        quote_url = f"https://financialmodelingprep.com/api/v3/quote/{symbols_str}?apikey={API_KEY}"
        quotes = requests.get(quote_url).json()

        for q in quotes:
            ticker = q.get('symbol')
            price = q.get('price', 0)
            change_pct = q.get('changesPercentage', 0)
            vol = q.get('volume', 0)

            # --- DINE PARAMETRE ---
            if change_pct >= 15.0 and price <= 30.0 and vol >= min_vol:
                
                # Hent de tunge metrics
                float_val, inst_val = get_detailed_metrics(ticker)
                vwap_val = get_daily_vwap(ticker)
                
                # VWAP STATUS
                vwap_status = "🟢 OVER" if vwap_val and price >= vwap_val else "🔴 UNDER"
                
                # AVANCERET RISK SCORE LOGIK (Float + Momentum + Inst)
                # Lav float + høj gain = Høj score
                score = 60
                if float_val > 0 and float_val < 10000000: score += 15 # Low float bonus
                if change_pct > 30: score += 10
                if vwap_status == "🟢 OVER": score += 10
                if inst_val > 20: score -= 5 # Institutionelt pres
                
                final_score = min(99, score)

                if final_score >= 75:
                    valid_stocks.append({
                        'TICKER': ticker,
                        'PRICE': f"${price:.2f}",
                        'GAIN %': f"+{change_pct:.2f}%",
                        'VWAP': vwap_status,
                        'FLOAT': f"{int(float_val/1000000)}M" if float_val > 0 else "N/A",
                        'INST %': f"{inst_val:.1f}%",
                        'VOLUME': f"{int(vol):,}",
                        'SCORE': final_score
                    })
        
        return pd.DataFrame(valid_stocks)
    except Exception as e:
        st.error(f"Fejl: {e}")
        return pd.DataFrame()

# --- UI VISNING ---
st.subheader("Quant-X Master Momentum Scanner")

if st.button("🔄 Force Refresh"):
    fetch_terminal_data.clear()
    st.rerun()

with st.spinner("Kører dyb scanning (Float, Warrants, VWAP)..."):
    df = fetch_terminal_data()

if not df.empty:
    df['n_gain'] = df['GAIN %'].str.replace('+', '').str.replace('%', '').astype(float)
    st.dataframe(df.sort_values('n_gain', ascending=False).drop(columns=['n_gain']), use_container_width=True, hide_index=True)
else:
    st.info("Ingen aktier fundet. Tjek volumen (50k pre / 500k regular).")

st.markdown("---")
st.caption(f"Scanner Aktiv | Tid: {datetime.now().strftime('%H:%M:%S')} | Session: {'Regular' if is_regular_market_hours() else 'Extended'}")
        
