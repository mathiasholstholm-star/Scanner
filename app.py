# --- 4. SCANNER (KUN BREAKOUTS OVER 15%) ---
@st.cache_data(ttl=20)
def run_scanner():
    # Filter: Pris < 30, Vol > 500k, Cap < 760M
    url = f"https://financialmodelingprep.com/api/v3/stock_screener?priceLowerThan=30&marketCapLowerThan=760000000&volumeMoreThan=500000&isEtf=false&isActivelyTrading=true&limit=40&apikey={FMP_API_KEY}"
    try:
        stocks = requests.get(url).json()
        results = []
        for s in stocks:
            # HENT STIGNING I %
            change_pct = round(s.get('changesPercentage', 0), 2)
            
            # 🔥 DET NYE FILTER: KUN HVIS STIGNING > 15%
            if change_pct >= 15.0:
                symbol = s['symbol']
                fl, si, dtc, risk_label, penalty = get_stock_details(symbol)
                
                # --- SCORE BEREGNING (0-100) ---
                score = 40 + penalty
                if change_pct > 30: score += 20  # Ekstra point for massive ryk
                if fl < 10.0: score += 20        # Lav float er kritisk her
                if dtc > 2.0: score += 10        # Short squeeze potentiale
                if s.get('volume', 0) > 1000000: score += 10 # Bekræftet af volumen
                
                results.append({
                    "SYMBOL": symbol,
                    "STIGNING %": f"{change_pct}%",
                    "SCORE": min(max(score, 0), 100),
                    "DTC": dtc,
                    "FLOAT (M)": fl,
                    "RISIKO": risk_label,
                    "PRIS": f"${round(s['price'], 3)}",
                    "VOLUMEN": f"{round(s['volume']/1e6, 2)}M"
                })
        # Sortér så de højeste scores ligger øverst
        return sorted(results, key=lambda x: x['SCORE'], reverse=True)
    except: return []
        
