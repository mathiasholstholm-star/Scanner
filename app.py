import streamlit as st
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh # Husk at tilføje denne til requirements.txt
import streamlit.components.v1 as components

# --- 1. SETUP & AUTO-REFRESH (Hvert 30. sekund) ---
st.set_page_config(layout="wide", page_title="QUANT-X LIVE TERMINAL")

# Dette får appen til at genindlæse hvert 30.000 millisekund (30 sek)
count = st_autorefresh(interval=30000, key="fmp_refresh")

FMP_API_KEY = st.secrets["FMP_API_KEY"]

# --- 2. JAVASCRIPT TIL CHROME NOTIFIKATIONER ---
def send_chrome_notification(title, message):
    js_code = f"""
    <script>
    function notify() {{
      if (Notification.permission === "granted") {{
        new Notification("{title}", {{ body: "{message}", icon: "https://cdn-icons-png.flaticon.com/512/2522/2522648.png" }});
      }} else if (Notification.permission !== "denied") {{
        Notification.requestPermission().then(permission => {{
          if (permission === "granted") {{
            new Notification("{title}", {{ body: "{message}" }});
          }}
        }});
      }}
    }}
    notify();
    </script>
    """
    components.html(js_code, height=0)

# --- 3. DATA & SCANNER (Præcis som før) ---
@st.cache_data(ttl=25) # Cache er kortere end refresh for at få friske data
def run_live_scanner():
    url = f"https://financialmodelingprep.com/api/v3/stock_screener?priceLowerThan=30&marketCapLowerThan=760000000&volumeMoreThan=500000&isEtf=false&isActivelyTrading=true&limit=20&apikey={FMP_API_KEY}"
    try:
        stocks = requests.get(url).json()
        results = []
        for s in stocks:
            symbol = s['symbol']
            # RVOL og andre data her... (forkortet for plads, brug din eksisterende logik)
            results.append(s)
        return results
    except: return []

# --- 4. NOTIFIKATIONS LOGIK ---
# Vi gemmer de fundne aktier i 'session_state', så vi kun får besked om NYE aktier
if 'last_seen_stocks' not in st.session_state:
    st.session_state.last_seen_stocks = []

st.title("🚀 QUANT-X LIVE TERMINAL")
st.write(f"Sidste opdatering: {pd.Timestamp.now().strftime('%H:%M:%S')} (Næste om 30 sek)")

data = run_live_scanner()

if data:
    current_symbols = [s['symbol'] for s in data]
    
    # Find nye aktier der ikke var på listen sidst
    new_stocks = [s for s in current_symbols if s not in st.session_state.last_seen_stocks]
    
    if new_stocks:
        # SEND CHROME NOTIFIKATION!
        msg = f"Nye breakouts fundet: {', '.join(new_stocks)}"
        send_chrome_notification("🚀 QUANT-X ALERT", msg)
        st.session_state.last_seen_stocks = current_symbols # Opdater listen over sete aktier

    # VIS TABELLEN
    st.table(pd.DataFrame(data))

# --- 5. TILLADELSE KNAP ---
if st.button("🔔 Aktiver Chrome Notifikationer"):
    components.html("""
    <script>
    Notification.requestPermission().then(function(result) {
      alert("Notifikationer er nu: " + result);
    });
    </script>
    """, height=0)
    
