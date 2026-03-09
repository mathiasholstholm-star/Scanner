import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# --- KONFIGURATION AF TERMINAL ---
st.set_page_config(page_title="Quant-X Real-Time Terminal", layout="wide", page_icon="⚡")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X REAL-TIME TERMINAL</h1>", unsafe_allow_html=True)

def get_screener_candidates():
    """Henter de mest aktive aktier via Yahoo Finance (Realtid)"""
    try:
        # Vi henter "Day Gainers" fra Yahoo Finance
        gainers = yf.Search("", n_results=50).quotes # Simpelt opslag
        # Da yfinance ikke har en direkte 'screener' i biblioteket, 
        # bruger vi en liste over mest aktive tickers som udgangspunkt
        tickers = ["AZI", "TSLA", "NVDA", "AAPL", "AMD"] # Her kan vi tilføje en liste eller bruge gainers-feed
        # For at gøre det 100% live, lader vi brugeren også tilføje en ticker manuelt hvis den mangler
        return tickers
    except:
        return ["AZI"]

def get_stock_data(ticker_symbol):
    """Henter alle dine data i realtid for en specifik ticker"""
    try:
        t = yf.Ticker(ticker_symbol)
        info = t.info
        hist = t.history(period="1d", interval="1m")

        if hist.empty:
            return None

        current_price = info.get('regularMarketPrice') or hist['Close'].iloc[-1]
        prev_close = info.get('previousClose') or hist['Open'].iloc[0]
        change_pct = ((current_price - prev_close) / prev_close) * 100
        vol = info.get('regularMarketVolume') or hist['Volume'].sum()
        
        # FLOAT & INSTITUTIONAL (Dine avancerede krav)
        float_shares = info.get('floatShares', 0)
        inst_own = info.get('heldPercentInstitutions', 0) * 100
        
        # VWAP BEREGNING
        hist['TP'] = (hist['High'] + hist['Low'] + hist['Close']) / 3
        vwap_val = (hist['TP'] * hist['Volume']).sum() / hist['Volume'].sum()
        vwap_status = "🟢 OVER" if current_price >= vwap_val else "🔴 UNDER"

        return {
            'TICKER': ticker_symbol,
            'PRICE': current_price,
            'GAIN %': change_pct,
            'VOLUME': vol,
            'FLOAT': float_shares,
            'INST %': inst_own,
            'VWAP': vwap_status,
            'SCORE': 0 # Beregnes nedenfor
        }
    except:
        return None

@st.cache_data(ttl=5)
def run_scanner():
    # Vi fokuserer på de mest aktive og dine specifikke gappers
    # For at gøre det hurtigt, tjekker vi de mest relevante tickers
    target_tickers = ["AZI", "NINE", "GME", "AMC", "KOSS"] # Eksempler på momentum aktier
    
    valid_stocks = []
    for symbol in target_tickers:
        data = get_stock_data(symbol)
        if data:
            # DINE FILTRE: Gain > 15% og Pris < $30
            if data['GAIN %'] >= 15.0 and data['PRICE'] <= 30.0:
                
                # RISK SCORE LOGIK (Din motor)
                score = 70
                if 0 < data['FLOAT'] < 20000000: score += 15
                if data['GAIN %'] > 40: score += 10
                if data['VWAP'] == "🟢 OVER": score += 5
                
                data['SCORE'] = min(99, score)
                
                if data['SCORE'] >= 75:
                    # Formatering til tabellen
                    data['PRICE'] = f"${data['PRICE']:.2f}"
                    data['GAIN %'] = f"+{data['GAIN %']:.2f}%"
                    data['FLOAT'] = f"{int(data['FLOAT']/1000000)}M" if data['FLOAT'] > 0 else "N/A"
                    data['VOLUME'] = f"{int(data['VOLUME']):,}"
                    data['INST %'] = f"{data['INST %']:.1f}%"
                    valid_stocks.append(data)
    
    return pd.DataFrame(valid_stocks)

# --- UI ---
st.subheader("Live Real-Time Momentum (Yahoo Finance Engine)")

manual_ticker = st.text_input("Tilføj ticker manuelt til overvågning (f.eks. AZI):").upper()
if manual_ticker and st.button("Tjek Ticker"):
    res = get_stock_data(manual_ticker)
    if res:
        st.write(f"**{manual_ticker} Status:** Price: ${res['PRICE']}, Gain: {res['GAIN %']:.2f}%, VWAP: {res['VWAP']}")
    else:
        st.error("Kunne ikke finde ticker.")

if st.button("🔄 SCAN NU"):
    st.rerun()

with st.spinner("Henter realtidsdata..."):
    df = run_scanner()

if not df.empty:
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("Søger efter gappers... (Ingen aktier over 15% fundet i test-listen)")

st.markdown("---")
st.caption(f"Kilde: Yahoo Finance (Real-time) | Opdateret: {datetime.now().strftime('%H:%M:%S')}")
