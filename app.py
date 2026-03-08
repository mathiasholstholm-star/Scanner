import streamlit as st
import pandas as pd
import requests
import time
from streamlit_autorefresh import st_autorefresh

# 1. Konfiguration & Mobil-design
st.set_page_config(page_title="Squeeze Terminal Ultra", page_icon="🧠", layout="centered")
st_autorefresh(interval=30 * 1000, key="datarefresh")

hide_style = """
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    div.block-container {padding-top: 2rem;}
    </style>
    """
st.markdown(hide_style, unsafe_allow_html=True)

def play_sound():
    sound_url = "https://www.soundjay.com/buttons/sounds/button-3.mp3"
    st.markdown(f'<audio autoplay><source src="{sound_url}" type="audio/mp3"></audio>', unsafe_allow_html=True)

st.title("🧠 Squeeze Ultra Terminal")
st.caption(f"Filtre: RVOL > 5x, Over VWAP & News Intelligence | {time.strftime('%H:%M:%S')}")

API_KEY = "DKC7vblNaiBbTzht7ASgqgnmlvzl5ym"

# 2. Den avancerede Score-Logik
def calculate_smart_score(rvol, sf, dtc, news_text, chg):
    score = 30 # Basis start
    
    # Power Words (Positive Katalysatorer)
    power_words = [
        'fda', 'phase 3', 'phase 2', 'clinical', 'breakthrough', 'approval', 'orphan',
        'earnings', 'beat', 'guidance', 'profitable', 'buyback', 'dividend', 'revenue',
        'contract', 'agreement', 'partnership', 'merger', 'acquisition', 'awarded', 'patent',
        'ai', 'artificial intelligence', 'bitcoin', 'crypto', 'nvidia', 'energy', 'lithium'
    ]
    
    # Danger Words (Negative Katalysatorer - Trækker 40 point fra)
    danger_words = ['offering', 'dilution', 'lawsuit', 'delisting', 'default', 'bankruptcy', 'fraud']
    
    news_clean = news_text.lower()
    
    # Beregn bonus/straf
    for word in power_words:
        if word in news_clean: score += 5
    
    for word in danger_words:
        if word in news_clean: score -= 40
        
    # RVOL Bonus (Max 20 point)
    score += min(20, (rvol / 1.5))
    
    # Short Float Bonus (Max 25 point)
    if sf > 15: score += 15
    if sf > 25: score += 10
    
    # Days to Cover (Max 5 point)
    score += min(5, dtc)
    
    # Price Action Bonus (Hvis den er over 25% stigning)
    if chg > 25: score += 10

    return max(0, min(100, int(score)))

# 3. Data-Hentning & Filtrering
def get_live_data():
    url = (f"https://financialmodelingprep.com/api/v3/stock-screener?"
           f"marketCapLowerThan=760000000&priceMoreThan=0.5&exchange=NYSE,NASDAQ,AMEX&apikey={API_KEY}")
    try:
        r = requests.get(url).json()
        df = pd.DataFrame(r)
        if df.empty: return []
        
        # Grundfilter: +15% stigning
        df = df[df['changesPercentage'] >= 15]
        results = []
        
        for _, row in df.head(10).iterrows():
            sym = row['symbol']
            q = requests.get(f"https://financialmodelingprep.com/api/v3/quote/{sym}?apikey={API_KEY}").json()[0]
            
            price, vwap = q.get('price', 0), q.get('vwap', 0)
            avg_v, curr_v = q.get('avgVolume', 1), q.get('volume', 0)
            rvol = curr_v / avg_v if avg_v > 0 else 0
            
            # KRAV: Skal være over VWAP og have 5x volumen
            if rvol >= 5 and price > vwap:
                s = requests.get(f"https://financialmodelingprep.com/api/v4/short-interest?symbol={sym}&apikey={API_KEY}").json()
                sf = s[0].get('shortFloat', 0) if s else 0
                dtc = s[0].get('daysToCover', 0) if s else 0
                
                # Nyheds-analyse
                n = requests.get(f"https://financialmodelingprep.com/api/v3/stock_news?tickers={sym}&limit=5&apikey={API_KEY}").json()
                news_text = " ".join([item.get('title', '') for item in n])
                
                final_score = calculate_smart_score(rvol, sf, dtc, news_text, row['changesPercentage'])
                
                results.append({
                    "sym": sym, "price": price, "chg": row['changesPercentage'],
                    "score": final_score, "rvol": round(rvol, 1), "sf": sf, "dtc": dtc, "vwap": vwap
                })
        
        # Sortér så højeste score er øverst
        return sorted(results, key=lambda x: x['score'], reverse=True)
    except: return []

data = get_live_data()

# 4. Visning i Appen
if data:
    play_sound()
    for stock in data:
        # Farvekode baseret på score
        status_icon = "🚀" if stock['score'] > 80 else "🔥" if stock['score'] > 60 else "👀"
        
        with st.expander(f"{status_icon} SCORE: {stock['score']}/100 | {stock['sym']} (+{stock['chg']:.1f}%)", expanded=True):
            st.progress(stock['score'] / 100)
            
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Pris:** ${stock['price']}")
                st.write(f"**VWAP:** ${stock['vwap']}")
                st.write(f"**RVOL:** {stock['rvol']}x")
            with c2:
                st.write(f"**Short Float:** {stock['sf']}%")
                st.write(f"**Days to Cover:** {stock['dtc']}")
            
            if stock['score'] > 75:
                st.success("STÆRKT SETUP: Høj score og nyheds-momentum!")
            elif stock['score'] < 40:
                st.warning("ADVARSEL: Lav score - tjek for nyheds-straf (dilution etc.)")
                
            st.markdown(f"[🔍 Hurtig Analyse på Google](https://www.google.com/search?q={stock['sym']}+stock+news)")
else:
    st.info("Scanner markederne... Intet matcher 5x volumen og VWAP-kravet lige nu.")
    
