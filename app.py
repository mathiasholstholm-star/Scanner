import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --- QUANT-X TERMINAL SETUP ---
st.set_page_config(page_title="Quant-X Google Engine", layout="wide")
st.markdown("<h1 style='text-align: center; color: #00ff00;'>QUANT-X REAL-TIME (GOOGLE ENGINE)</h1>", unsafe_allow_html=True)

def get_google_finance_data(ticker):
    """Henter realtidspris og gain direkte fra Google Finance (Intet API påkrævet)"""
    try:
        url = f"https://www.google.com/search?q=NASDAQ:{ticker}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Finder pris og ændring i koden (simpel scrape)
        price_raw = soup.find_all("div", attrs={'class': 'BNeawe iBp4i AP7Wnd'})
        if not price_raw: return None
        
        data_str = price_raw[0].text.split()
        price = float(data_str[0].replace(',', ''))
        # Estimerer gain ud fra teksten
        change_str = data_str[1] if len(data_str) > 1 else "+0.00%"
        change_pct = float(change_str.replace('+', '').replace('%', '').replace('(', '').replace(')', ''))
        
        return {
            'TICKER': ticker,
            'PRICE': price,
            'GAIN %': change_pct,
            'VOLUME': 1000000, # Dummy vol da scrape ikke giver præcis vol
            'FLOAT': 5000000   # Dummy float til score-beregning
        }
    except:
        return None

@st.cache_data(ttl=2)
def run_terminal(tickers):
    valid_stocks = []
    for t in tickers:
        data = get_google_finance_data(t)
        if data and data['GAIN %'] >= 15.0: # DIT KRAV
            
            # DIN RISK SCORE MOTOR
            score = 75
            if data['GAIN %'] > 50: score += 10
            if data['PRICE'] < 5: score += 5
            
            valid_stocks.append({
                'TICKER': data['TICKER'],
                'PRICE': f"${data['PRICE']:.2f}",
                'GAIN %': f"+{data['GAIN %']:.2f}%",
                'STATUS': "🟢 MOMENTUM",
                'SCORE': min(99, score)
            })
    return pd.DataFrame(valid_stocks)

# --- UI VISNING ---
st.subheader("Live Momentum Monitor (Ingen API Nødvendig)")

# Vi tvinger AZI og andre ind her
watch_list = st.text_input("Overvågning (tickers adskilt af komma):", "AZI, NINE, GME, KOSS")
tickers = [x.strip().upper() for x in watch_list.split(",") if x.strip()]

if st.button("🔄 FORCE REFRESH"):
    run_terminal.clear()
    st.rerun()

with st.spinner("Henter data direkte fra Google..."):
    df = run_terminal(tickers)

if not df.empty:
    st.table(df) # Bruger tabel for maksimal stabilitet
else:
    st.warning("Venter på gappers... Tjek om AZI er over 15% på din telefon.")

st.markdown("---")
st.caption(f"Engine: Google Live Scrape | Tid: {datetime.now().strftime('%H:%M:%S')}")
