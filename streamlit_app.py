import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- 1. KONFIGURACE (Obnova každých 30 sekund) ---
st.set_page_config(page_title="NEURAL ALPHA SCANNER PRO", layout="wide")
st_autorefresh(interval=30000, key="global_refresh") 

st.markdown("""
    <style>
    .main { background-color: #050505; }
    [data-testid="stMetricValue"] { color: #00ffcc; font-family: 'Courier New', monospace; font-size: 1.6rem; }
    .stAlert { border: 2px solid #ff4b4b; background-color: #1a0000; padding: 20px; border-radius: 10px; }
    .trade-command { font-size: 1.4rem; font-weight: bold; color: #00ff00; text-transform: uppercase; border: 2px dashed #00ff00; padding: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SBĚR DAT (2 dny pro plynulost grafu) ---
def get_market_data():
    symbols = {
        "GOLD": "GC=F",
        "OIL": "CL=F",
        "USD_INDEX": "DX-Y.NYB", 
        "USDCAD": "CAD=X",
        "VIX": "^VIX"
    }
    # Stahujeme 2 dny po 5 minutách
    data = yf.download(list(symbols.values()), period="2d", interval="5m", progress=False)['Close']
    inv_map = {v: k for k, v in symbols.items()}
    return data.rename(columns=inv_map).ffill()

# --- 3. LOGIKA ANOMÁLIÍ S POKYNY PRO TRADING ---
def check_signals(df):
    if len(df) < 10: return []
    last = df.iloc[-1]
    prev = df.iloc[-6] 
    sig = []
    
    # Zlato vs Dolar
    usd_m = (last['USD_INDEX'] - prev['USD_INDEX']) / prev['USD_INDEX']
    gold_m = (last['GOLD'] - prev['GOLD']) / prev['GOLD']
    
    if usd_m < -0.001 and gold_m < 0.0005:
        sig.append({"A": "GOLD", "T": "🚀 BÝČÍ ANOMÁLIE", "R": "Dolar padá, ale Zlato stojí!", "ACTION": "KUPUJ ZLATO (BUY) NA XTB", "URL": "https://xstation5.xtb.com"})
    elif usd_m > 0.001 and gold_m > -0.0005:
        sig.append({"A": "GOLD", "T": "📉 MEDVĚDÍ ANOMÁLIE", "R": "Dolar roste, ale Zlato nepadá!", "ACTION": "PRODÁVEJ ZLATO (SELL) NA XTB", "URL": "https://xstation5.xtb.com"})
    
    # Ropa vs CAD
    oil_m = (last['OIL'] - prev['OIL']) / prev['OIL']
    cad_m = (last['USDCAD'] - prev['USDCAD']) / prev['USDCAD']
    if oil_m > 0.005 and cad_m > -0.0005:
        sig.append({"A": "OIL.WTI", "T": "🔥 ROPA/CAD SIGNÁL", "R": "Ropa letí, ale CAD spí!", "ACTION": "PRODÁVEJ USD/CAD (SELL) NA XTB", "URL": "https://xstation5.xtb.com"})
    
    return sig

# --- 4. UI ZOBRAZENÍ ---
st.title("🧠 Neural Intelligence: Multi-Asset Scanner")

try:
    df = get_market_data()
    signals = check_signals(df)

    # VÝPOČET ČASU (Bezpečná metoda bez pytz)
    last_time = df.index[-1]
    # Posuneme čas o 1 hodinu (na náš aktuální středoevropský čas)
    time_str = (last_time + pd.Timedelta(hours=1)).strftime("%H:%M:%S")

    # OPRAVENÁ HORNÍ LIŠTA (Přístup přes indexy [0] až [4])
    m = st.columns(5)
    m[0].metric("Dolar Index", f"{df['USD_INDEX'].iloc[-1]:.2f}", f"{(df['USD_INDEX'].pct_change().iloc[-1]*100):.2f}%")
    m[1].metric("Zlato (GC)", f"{df['GOLD'].iloc[-1]:.1f}", f"{(df['GOLD'].pct_change().iloc[-1]*100):.2f}%")
    m[2].metric("Ropa (WTI)", f"{df['OIL'].iloc[-1]:.2f}", f"{(df['OIL'].pct_change().iloc[-1]*100):.2f}%")
    m[3].metric("USD/CAD", f"{df['USDCAD'].iloc[-1]:.4f}", f"{(df['USDCAD'].pct_change().iloc[-1]*100):.2f}%")
    m[4].metric("VIX (Strach)", f"{df['VIX'].iloc[-1]:.2f}", f"{(df['VIX'].pct_change().iloc[-1]*100):.2f}%")

    st.markdown(f"<p style='text-align: right; color: #ffcc00; font-weight: bold;'>⏰ Poslední cena z burzy: {time_str}</p>", unsafe_allow_html=True)

    if signals:
        st.audio("https://www.soundjay.com", autoplay=True)
        for s in signals:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.error(f"### {s['T']} na {s['A']}")
                st.info(s['R'])
            with c2:
                st.markdown(f"<div class='trade-command'>{s['ACTION']}</div>", unsafe_allow_html=True)
                st.link_button(f"PŘEJÍT NA XTB", s['URL'])
    else:
        st.success("✅ Trh je v rovnováze. Žádné anomálie.")

    # --- GRAF KORELACÍ ---
    st.markdown("### 📊 Intermarket Dynamika (Relativní pohyb %)")
    clean_df = df.dropna().last('12h') 
    norm = (clean_df / clean_df.iloc[0]) * 100
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=norm.index, y=norm['GOLD'], name="Zlato", line=dict(color='#FFD700', width=3)))
    fig.add_trace(go.Scatter(x=norm.index, y=norm['OIL'], name="Ropa", line=dict(color='#FFFFFF', width=3)))
    fig.add_trace(go.Scatter(x=norm.index, y=norm['USD_INDEX'], name="Dolar Index", line=dict(color='#0080FF', width=2, dash='dot')))
    
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=10, r=10, t=10, b=10),
                      yaxis=dict(autorange=True, fixedrange=False))
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.warning(f"Načítám data z burzy... ({e})")
