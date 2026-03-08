import streamlit as st
import pandas as pd
import requests

# --- 1. SETUP ---
st.set_page_config(layout="wide", page_title="QUANT-X ULTIMATE TERMINAL")
FMP_API_KEY = st.secrets["FMP_API_KEY"]

# Eksplosive nøgleord for AI, Droner, Defense og Medicin
BULL_KEYWORDS = [
    "FDA", "APPROVAL", "PHASE", "AI", "NVIDIA", "CHIPS", "LLM", "DRONE", 
    "UAV", "DEFENSE", "MILITARY", "PENTAGON", "CONTRACT", "LITHIUM", "SQUEEZE"
]

# --- 2. DATA-MOTORER ---

def get_market_data(symbol):
    """Henter Float, Short Interest og Days to Cover i ét hug"""
    try:
        # Hent Float
        f_url = f"https://financialmodelingprep.com/api/v4/shares_float?symbol={symbol}&apikey={FMP_API_KEY}"
        f_shares = requests.get(f_url).json()
        float_val = round(f_shares[0]['floatShares'] / 1e6, 2) if f_shares else 0.0
        
        # Hent Short Data
        s_url = f"https://financialmodelingprep.com/api/v4/short-interest?symbol={symbol}&apikey={FMP_API_KEY}"
        s_data = requests.get(s_url).json()
        si_pct = round(s_data[0]['shortInterestRatio'], 2) if s_data else 0.0
        dtc = round(s_data[0]['daysToCover'], 2) if s_data else 0.0
        
        return float_val, si_pct, dtc
    except: return 0.0, 0.0, 0.0

def analyze_news(symbol):
    """Scanner nyheder for de eksplosive emner du elsker"""
    url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={symbol}&limit=1&apikey={FMP_API_KEY}"
    try:
        news = requests.get(url).json()
        if news:
            title = news[0]['title']
            found = [w for w in BULL_KEYWORDS if w in title.upper()]
            sentiment = "🟢 GOD" if found else "🟡 NEUTRAL"
            bonus = len(found) * 15
            return title[:60], sentiment, bonus, ", ".join(found)
    except: pass
    return "N/A", "⚪ N/A", 0, ""

# --- 3. CORE SCANNER (BASERET PÅ DINE SCREENSHOT FILTRE) ---

@st.cache_data(ttl=300)
def run_ultimate_power_scanner():
    # FILTRE FRA DIT BILLEDE: Price < 30 | Market Cap < 760M | Volume > 500k
    url = f"https://financialmodelingprep.com/api/v3/stock_screener?priceLowerThan=30&marketCapLowerThan=760000000&volumeMoreThan=500000&isEtf=false&isActivelyTrading=true&limit=100&apikey={FMP_API_KEY}"
    
    try:
        stocks = requests.get(url).json()
        results = []
        
        for s in stocks:
            symbol = s['symbol']
            hist_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey={FMP_API_KEY}"
            h = requests.get(hist_url).json()
            
            if 'historical' in h:
                df = pd.DataFrame(h['historical']).head(21)
                last = df.iloc[0]
                avg_vol = df.iloc[1:21]['volume'].mean()
                
                # RVOL BEREGNING
                rvol = round(last['volume'] / avg_vol, 2)
                vwap_approx = (last['high'] + last['low'] + last['close']) / 3
                
                # HENT FLOAT & SHORT DATA (Kritisk!)
                fl, si, dtc = get_market_data(symbol)
                
                # FILTER: Free Float < 30M (Præcis som dit screenshot)
                if fl > 30.0: continue
                
                # ANALYSER NYHEDER
                news_title, sent, bonus, keys = analyze_news(symbol)
                
                # DIN SANDSYNLIGHEDS-SCORE (0-100%)
                score = 40
                if rvol >= 5.0: score += 20     # RVOL x5 Power
                if fl < 10.0: score += 15       # Ultra Low Float Bonus
                if si > 15.0: score += 10       # Squeeze potentiale
                if s['price'] > vwap_approx: score += 10 # Over VWAP
                score += bonus                  # Hype-News Bonus
                
                if rvol >= 1.2: # Vi vil kun se dem der flytter sig
                    results.append({
                        "SCORE": f"{min(score, 100)}%",
                        "SYMBOL": symbol,
                        "STATUS": "🔥 RVOL X5" if rvol >= 5.0 else "👀 MOMENTUM",
                        "RVOL": rvol,
                        "FLOAT (M)": fl,
                        "SHORT %": f"{si}%",
                        "DTC": dtc,
                        "VWAP": "✅" if s['price'] > vwap_approx else "❌",
                        "NYHED": news_title,
                        "SENTIMENT": sent,
                        "PRICE": f"${s['price']}",
                        "CHANGE": f"{round(((s['price'] - last['open'])/last['open'])*100, 2)}%"
                    })
        return sorted(results, key=lambda x: x['RVOL'], reverse=True)
    except: return []

# --- 4. TERMINAL VISNING ---

st.title("🚀 QUANT-X ULTIMATE TERMINAL")
st.subheader("Small-Cap Breakouts | Low Float | News Hype | Squeeze")

data = run_ultimate_power_scanner()

if data:
    st.table(pd.DataFrame(data))
else:
    st.info("Scanner... Ingen aktier rammer dine ekstreme kriterier lige nu.")

# --- 5. DIN STRATEGI-LOGIK ---
st.divider()
st.markdown("""
### 📊 Din Setup-Logik:
* **A+ Setup:** RVOL > 5.0 + Float < 10M + Over VWAP + Nyheder (AI/Drone/FDA).
* **Short Squeeze:** Tjek om DTC (Days to Cover) er over 3.0.
* **Volume:** Minimum 500.000 (Bekræftet interesse).
""")
