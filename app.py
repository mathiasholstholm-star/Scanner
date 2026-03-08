import streamlit as st
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# --- 1. TERMINAL CONFIGURATION ---
st.set_page_config(layout="wide", page_title="QUANT-X MASTER TERMINAL", page_icon="📈")
st_autorefresh(interval=30000, key="terminal_refresh")

# Professional CSS Styling
st.markdown("""
    <style>
    .main { background-color: #0b0e11; }
    .stDataFrame { border: 1px solid #30363d; }
    .status-bar {
        font-family: 'Courier New', monospace;
        color: #848d97;
        font-size: 12px;
        margin-bottom: 15px;
    }
    h1 { color: #f0f6fc; font-family: 'Inter', sans-serif; font-size: 24px; }
    </style>
    """, unsafe_allow_html=True)

FMP_API_KEY = st.secrets["FMP_API_KEY"]

# --- 2. BROWSER ALERTS ---
def send_browser_notification(symbol, score, change):
    js = f"""<script>if (Notification.permission === "granted") 
    {{ new Notification("QUANT-X SIGNAL: {symbol}", {{ body: "Score: {score}% | Gain: {change}%", icon: "" }}); }}</script>"""
    components.html(js, height=0)

# --- 3. DATA ENGINE (13 DATAPUNKTER) ---
def get_detailed_metrics(symbol):
    try:
        # API kald til forskellige endpoints
        f_url = f"https://financialmodelingprep.com/api/v4/shares_float?symbol={symbol}&apikey={FMP_API_KEY}"
        s_url = f"https://financialmodelingprep.com/api/v4/short-interest?symbol={symbol}&apikey={FMP_API_KEY}"
        sec_url = f"https://financialmodelingprep.com/api/v3/sec_filings/{symbol}?limit=5&apikey={FMP_API_KEY}"
        news_url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={symbol}&limit=1&apikey={FMP_API_KEY}"
        quote_url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={FMP_API_KEY}"
        
        # Hent data
        fl_res = requests.get(f_url).json()
        sh_res = requests.get(s_url).json()
        sec_res = requests.get(sec_url).json()
        nw_res = requests.get(news_url).json()
        qt_res = requests.get(quote_url).json()
        
        # Beregninger
        float_m = round(fl_res[0]['floatShares'] / 1e6, 2) if fl_res else 0.0
        dtc = round(sh_res[0]['daysToCover'], 2) if sh_res else 0.0
        short_pct = round(sh_res[0]['shortInterestRatio'], 2) if sh_res else 0.0
        
        # RVOL (Current Volume / Avg Volume)
        avg_vol = qt_res[0]['avgVolume'] if qt_res and qt_res[0]['avgVolume'] > 0 else 1
        curr_vol = qt_res[0]['volume'] if qt_res else 0
        rvol = round(curr_vol / avg_vol, 2)
        
        # Risk & SEC Filings
        risk_status = "STABLE"
        penalty = 0
        filing_types = []
        if sec_res:
            for f in sec_res:
                f_type = f['type']
                filing_types.append(f_type)
                if any(k in f_type for k in ["S-3", "424B", "F-3"]):
                    risk_status = "WARRANTS/S-3"
                    penalty = -35
        
        sec_archive_link = f"https://www.sec.gov/cgi-bin/browse-edgar?CIK={symbol}&action=getcompany"
        headline = nw_res[0]['title'] if nw_res else "NO RECENT NEWS"
        
        return rvol, short_pct, dtc, float_m, risk_status, penalty, filing_types, sec_archive_link, headline
    except:
        return 0.0, 0.0, 0.0, 0.0, "N/A", 0, [], "#", "ERROR FETCHING NEWS"

@st.cache_data(ttl=20)
def run_master_scanner():
    url = f"https://financialmodelingprep.com/api/v3/stock_screener?priceLowerThan=30&marketCapLowerThan=760000000&volumeMoreThan=500000&isActivelyTrading=true&limit=40&apikey={FMP_API_KEY}"
    try:
        stocks = requests.get(url).json()
        master_list = []
        for s in stocks:
            gain = round(s.get('changesPercentage', 0), 2)
            
            # --- FILTER: KUN OVER 15% ---
            if gain >= 15.0:
                sym = s['symbol']
                rvol, si, dtc, fl, risk, penalty, filings, sec_link, news = get_detailed_metrics(sym)
                
                # SCORE LOGIK
                score = 40 + penalty
                if gain > 30: score += 20
                if fl < 10.0: score += 25
                if dtc > 2.0: score += 10
                if rvol > 3.0: score += 5
                
                master_list.append({
                    "SCORE": min(max(score, 0), 100),
                    "TICKER": sym,
                    "PRICE": f"${round(s['price'], 2)}",
                    "GAIN %": gain,
                    "RISK STATUS": risk,
                    "SEC ARCHIVE": sec_link,
                    "SEC FILINGS": ", ".join(filings[:3]),
                    "RVOL": f"{rvol}x",
                    "FLOAT (M)": fl,
                    "SHORT %": f"{si}%",
                    "DTC": dtc,
                    "VOL (M)": round(s['volume']/1e6, 2),
                    "NEWS HEADLINE": news
                })
        return sorted(master_list, key=lambda x: x['SCORE'], reverse=True)
    except:
        return []

# --- 4. INTERFACE ---
st.markdown("<h1>QUANT-X MASTER TERMINAL v3.0</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='status-bar'>SYSTEM: ACTIVE | {pd.Timestamp.now().strftime('%H:%M:%S')} | THRESHOLD: 15%</div>", unsafe_allow_html=True)

if st.button("ENABLE ALERTS"):
    components.html("<script>Notification.requestPermission();</script>", height=0)

data = run_master_scanner()

if data:
    df = pd.DataFrame(data)
    
    # Send notifikation for topscoreren
    if df.iloc[0]['SCORE'] >= 80:
        send_browser_notification(df.iloc[0]['TICKER'], df.iloc[0]['SCORE'], df.iloc[0]['GAIN %'])

    # Styling af tabellen
    def color_risk(val):
        color = '#f85149' if val == "WARRANTS/S-3" else '#238636'
        return f'color: {color}; font-weight: bold'

    # Vi bruger st.column_config til at lave klikbare links til SEC
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "SEC ARCHIVE": st.column_config.LinkColumn("SEC ARCHIVE", display_text="OPEN EDGAR"),
            "SCORE": st.column_config.ProgressColumn("SCORE", format="%d%%", min_value=0, max_value=100)
        }
    )
else:
    st.info("Searching for tickers with >15% gain and sufficient volume...")

st.divider()
st.caption("INTERNAL USE ONLY | QUANT-X PRO ALGORITHM")
