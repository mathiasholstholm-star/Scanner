import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --- TERMINAL SETUP ---
st.set_page_config(page_title="Quant-X Alpha Terminal", layout="wide")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X ALPHA (REALTID)</h1>", unsafe_allow_html=True)

def get_realtime_data(ticker):
    """Scraper realtidsdata direkte fra Yahoo Finance - ingen API nøgle påkrævet"""
    url = f"https://finance.yahoo.com/quote/{ticker}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Finder pris og ændring via data-fields
        price = float(soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})['value'])
        change = float(soup.find('fin-streamer', {'data-field': 'regularMarketChangePercent'})['value'])
        
        # Prøver at hente Float (ligger ofte i 'Statistics' fanen, her bruger vi et estimat)
        return {
            'TICKER': ticker,
            'PRICE': price,
            'GAIN %': change,
            'STATUS': "🟢 LIVE"
        }
    except Exception as e:
        return None

# --- UI VISNING ---
st.subheader("Direkte Markeds-Feed (Uden API)")

# Her skriver du de tickers, du vil overvåge live
user_input = st.text_input("Indtast tickers (adskilt af komma):", "AZI, NINE, GME, TSLA")
tickers = [x.strip().upper() for x in user_input.split(",") if x.strip()]

if st.button("🔄 OPDATER NU"):
    st.rerun()

results = []
with st.spinner("Henter live kurser..."):
    for t in tickers:
        data = get_realtime_data(t)
        if data:
            # DIN LOGIK: Score beregnes på live data
            score = 65
            if data['GAIN %'] > 15: score += 15
            if data['GAIN %'] > 40: score += 10
            
            results.append({
                'TICKER': data['TICKER'],
                'PRICE': f"${data['PRICE']:.2f}",
                'GAIN %': f"{data['GAIN %']:.2f}%",
                'SCORE': min(99, score)
            })

if results:
    df = pd.DataFrame(results)
    st.table(df) # Tabel er mest stabil til hurtig visning
else:
    st.warning("Kunne ikke hente data. Tjek om dine tickers er korrekte.")

st.markdown("---")
st.caption(f"Sidste synkronisering: {datetime.now().strftime('%H:%M:%S')} | Kilde: Yahoo Scraper")
