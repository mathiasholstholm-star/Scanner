import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- KONFIGURATION AF TERMINAL ---
st.set_page_config(page_title="Quant-X Real-Time", layout="wide", page_icon="⚡")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X REAL-TIME TERMINAL</h1>", unsafe_allow_html=True)

def get_vwap_and_metrics(ticker_symbol):
    """Henter realtidsdata, VWAP og Float via Yahoo Finance"""
    try:
        t = yf.Ticker(ticker_symbol)
        # Hent intraday data (1-minutters intervaller for i dag)
        hist = t.history(period="1d", interval="1m")
        if hist.empty: return None
        
        info = t.info
        current_price = hist['Close'].iloc[-1]
        prev_close = info.get('previousClose') or hist['Open'].iloc[0]
        change_pct = ((current_price - prev_close) / prev_close) * 100
        vol = hist['Volume'].sum()
        
        # Beregn VWAP manuelt
        hist['TP'] = (hist['High'] + hist['Low'] + hist['Close']) / 3
        vwap_val = (hist['TP'] * hist['Volume']).sum() / hist['Volume'].sum()
        vwap_status = "🟢 OVER" if current_price >= vwap_val else "🔴 UNDER"
        
        # Float og Inst data
        float_shares = info.get('floatShares', 0)
        inst_own = info.get('heldPercentInstitutions', 0) * 100
        
        return {
            'TICKER': ticker_symbol,
            'PRICE': current_price,
            'GAIN %': change_pct,
            'VOLUME': vol,
            'FLOAT': float_shares,
            'INST %': inst_own,
            'VWAP': vwap_status
        }
    except:
        return None

@st.cache_data(ttl=10)
def fetch_terminal_data(manual_list):
    valid_stocks = []
    # Vi tjekker AZI og andre momentum-kandidater direkte
    # Da yfinance ikke har en "live screener", tilføjer vi AZI til overvågning her
    for ticker in manual_list:
        data = get_vwap_and_metrics(ticker)
        if data and data['GAIN %'] >= 15.0 and data['PRICE'] <= 30.0:
            
            # DIN RISK SCORE LOGIK (PUNKT FOR PUNKT)
            score = 65
            if 0 < data['FLOAT'] < 20000000: score += 15 # Low float bonus
            if data['GAIN %'] > 40: score += 10
            if data['VWAP'] == "🟢 OVER": score += 5
            
            final_score = min(99, score)
            
            if final_score >= 75:
                valid_stocks.append({
                    'TICKER': data['TICKER'],
                    'PRICE': f"${data['PRICE']:.2f}",
                    'GAIN %': f"+{data['GAIN %']:.2f}%",
                    'VWAP': data['VWAP'],
                    'FLOAT': f"{int(data['FLOAT']/1000000)}M" if data['FLOAT'] > 0 else "N/A",
                    'INST %': f"{data['INST %']:.1f}%",
                    'VOLUME': f"{int(data['VOLUME']):,}",
                    'SCORE': final_score
                })
    return pd.DataFrame(valid_stocks)

# --- UI VISNING ---
st.subheader("Live Momentum Scanner (Realtid via Yahoo Engine)")

# Manuel overvågning så vi er sikre på at AZI er der
watch_input = st.text_input("Tilføj tickers til scanning (separeret med komma):", "AZI, NINE, GME, KOSS")
active_list = [x.strip().upper() for x in watch_input.split(",")]

if st.button("🔄 FORCE REFRESH"):
    fetch_terminal_data.clear()
    st.rerun()

with st.spinner("Henter realtidsdata for dine tickers..."):
    df = fetch_terminal_data(active_list)

if not df.empty:
    # Sorter efter gain
    df['n_gain'] = df['GAIN %'].str.replace('+', '').str.replace('%', '').astype(float)
    st.dataframe(df.sort_values('n_gain', ascending=False).drop(columns=['n_gain']), use_container_width=True, hide_index=True)
else:
    st.info("Ingen af de overvågede aktier opfylder dine krav (Gain > 15% / Price < $30).")

st.markdown("---")
st.caption(f"Kilde: Yahoo Finance (Realtid) | Sidst opdateret: {datetime.now().strftime('%H:%M:%S')}")
