import streamlit as st
import pandas as pd
import requests
import time
from streamlit_autorefresh import st_autorefresh

# Konfiguration til både Mobil & PC
st.set_page_config(page_title="Squeeze Terminal", page_icon="⚡", layout="centered")
st_autorefresh(interval=30 * 1000, key="datarefresh")

# Skjul menuer for rent look
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>", unsafe_allow_html=True)

def play_sound():
    sound_url = "https://www.soundjay.com/buttons/sounds/button-3.mp3"
    st.markdown(f'<audio autoplay><source src="{sound_url}" type="audio/mp3"></audio>', unsafe_allow_html=True)

st.title("⚡ Live Squeeze List")
st.caption(f"Scanner: RVOL > 5x, Over VWAP & News Score | {time.strftime('%H:%M:%S')}")

API_KEY = "DKC7vblNaiBbTzht7ASgqgnmlvzl5ym"

def calculate_smart_score(rvol, sf, dtc, news_text, chg):
    score = 30
    power_words = ['fda', 'phase 3', 'phase 2', 'clinical', 'breakthrough', 'approval', 'earnings', 'beat', 'guidance', 'profitable', 'contract', 'partnership', 'merger', 'acquisition', 'ai', 'crypto']
    danger_words = ['offering', 'dilution', 'lawsuit', 'delisting', 'default']
    
    news_clean = news_text.lower()
    for word in power_words:
        if word in news_clean: score += 5
    for word in danger_words:
        if word in news_clean: score -= 40
        
    score += min(20, (rvol / 1.5))
    if sf > 15: score += 15
    if sf > 25: score += 10
    score += min(5, dtc)
    if chg > 25: score += 10
    return max(0, min(100, int(score)))

def get_data():
    url = (f"https://financialmodelingprep.com/api/v3/stock-screener?"
           f"marketCapLowerThan=760000000&priceMoreThan=0.5&exchange=NYSE,NASDAQ,AMEX&apikey={API_KEY}")
    try:
        r = requests.get(url).json()
        df = pd.DataFrame(r)
        if df.empty: return []
        
        df = df[df['changesPercentage'] >= 15]
        results = []
        
        for _, row in df.head(10).iterrows():
            sym = row['symbol']
            q = requests.get(f"https://financialmodelingprep.com/api/v3/quote/{sym}?apikey={API_KEY}").json()[0]
            price, vwap = q.get('price', 0), q.get('vwap', 0)
            avg_v, curr_v = q.get('avgVolume', 1), q.get('volume', 0)
            rvol = curr_v / avg_v if avg_v > 0 else 0
            
            if rvol >= 5 and price > vwap:
                s = requests.get(f"https://financialmodelingprep.com/api/v4/short-interest?symbol={sym}&apikey={API_KEY}").json()
                sf = s[0].get('shortFloat', 0) if s else 0
                dtc = s[0].get('daysToCover', 0) if s else 0
                
                n = requests.get(f"https://financialmodelingprep.com/api/v3/stock_news?tickers={sym}&limit=5&apikey={API_KEY}").json()
                news_text = " ".join([item.get('title', '') for item in n])
                
                f_score = calculate_smart_score(rvol, sf, dtc, news_text, row['changesPercentage'])
                
                results.append({
                    "sym": sym, "price": price, "chg": row['changesPercentage'],
                    "score": f_score, "rvol": round(rvol, 1), "sf": sf, "dtc": dtc
                })
        return sorted(results, key=lambda x: x['score'], reverse=True)
    except: return []

data = get_data()

if data:
    play_sound()
    for stock in data:
        # Enkel liste-visning
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                st.subheader(stock['sym'])
                st.write(f"${stock['price']}")
            with col2:
                st.write(f"**Score:** {stock['score']}/100")
                st.progress(stock['score'] / 100)
            with col3:
                st.write(f"**+{stock['chg']:.1f}%**")
                st.write(f"**{stock['rvol']}x Vol**")
            
            # Små detaljer under hver linje
            st.caption(f"Short Float: {stock['sf']}% | DTC: {stock['dtc']} | [Nyheder](https://www.google.com/search?q={stock['sym']}+stock+news)")
            st.divider()
else:
    st.info("Scanner... Ingen aktier opfylder kravene lige nu.")
                
