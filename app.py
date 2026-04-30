import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

import yfinance as yf

st.set_page_config(layout="wide", page_title="COT Analyzer Dashboard", page_icon="📊", initial_sidebar_state="collapsed")

# ─────────────────────────────── MAPPINGS ────────────────────────────────────
YF_MAPPING = {
    "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE": "6C=F",
    "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE": "6S=F",
    "BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE": "6B=F",
    "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE": "6J=F",
    "EURO FX - CHICAGO MERCANTILE EXCHANGE": "6E=F",
    "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE": "6A=F",
    "NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE": "6N=F",
    "MEXICAN PESO - CHICAGO MERCANTILE EXCHANGE": "6M=F",
    "BRAZILIAN REAL - CHICAGO MERCANTILE EXCHANGE": "6L=F",
    "USD INDEX - ICE FUTURES U.S.": "DX=F",
    "S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE": "ES=F",
    "NASDAQ-100 Consolidated - CHICAGO MERCANTILE EXCHANGE": "NQ=F",
    "DJIA Consolidated - CHICAGO BOARD OF TRADE": "YM=F",
    "BITCOIN - CHICAGO MERCANTILE EXCHANGE": "BTC-USD",
    "ETHER CASH SETTLED - CHICAGO MERCANTILE EXCHANGE": "ETH-USD",
    "GOLD - COMMODITY EXCHANGE INC.": "GC=F",
    "CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE": "CL=F",
    "UST 10Y NOTE - CHICAGO BOARD OF TRADE": "ZN=F",
    "UST 5Y NOTE - CHICAGO BOARD OF TRADE": "ZF=F",
    "UST 2Y NOTE - CHICAGO BOARD OF TRADE": "ZT=F",
    "UST BOND - CHICAGO BOARD OF TRADE": "ZB=F",
    "ULTRA UST BOND - CHICAGO BOARD OF TRADE": "UB=F",
    "VIX FUTURES - CBOE FUTURES EXCHANGE": "VX=F",
    "USD/CHINESE RENMINBI-OFFSHORE  - CHICAGO MERCANTILE EXCHANGE": "CNH=F",
    "CHINESE RENMINBI-HK (CNH) - CHICAGO MERCANTILE EXCHANGE": "CNH=F",
    "BITCOIN-USD - CBOE FUTURES EXCHANGE": "BTC-USD"
}

@st.cache_data
def load_price_data(ticker, start_date, end_date):
    if not ticker:
        return pd.DataFrame()
    try:
        # Buffer the date range slightly
        start_dt = start_date - pd.Timedelta(days=30)
        end_dt = end_date + pd.Timedelta(days=7)
        data = yf.download(ticker, start=start_dt, end=end_dt, progress=False)
        if data.empty:
            return pd.DataFrame()
        # Handle multi-index columns if necessary (newer yfinance)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data[['Close']].reset_index()
    except Exception as e:
        return pd.DataFrame()

# ─────────────────────────────── DATA LOADING ────────────────────────────────
NUMERIC_COLS = [
    'Open_Interest_All', 'Change_in_Open_Interest_All',
    'Dealer_Positions_Long_All', 'Dealer_Positions_Short_All', 'Dealer_Positions_Spread_All',
    'Asset_Mgr_Positions_Long_All', 'Asset_Mgr_Positions_Short_All', 'Asset_Mgr_Positions_Spread_All',
    'Lev_Money_Positions_Long_All', 'Lev_Money_Positions_Short_All', 'Lev_Money_Positions_Spread_All',
    'Other_Rept_Positions_Long_All', 'Other_Rept_Positions_Short_All',
    'NonRept_Positions_Long_All', 'NonRept_Positions_Short_All',
    'Conc_Gross_LE_4_TDR_Long_All', 'Conc_Gross_LE_4_TDR_Short_All',
    'Conc_Gross_LE_8_TDR_Long_All', 'Conc_Gross_LE_8_TDR_Short_All',
]

@st.cache_data
def load_data():
    base_dir = os.path.join(os.path.dirname(__file__), "data")
    if not os.path.exists(base_dir):
        st.error(f"Data directory not found at {base_dir}. Please run cto.py first.")
        return pd.DataFrame()

    dfs = []
    for y in range(2010, 2030):
        fp = os.path.join(base_dir, f"cot_{y}.csv")
        if os.path.exists(fp):
            try:
                dfs.append(pd.read_csv(fp, low_memory=False))
            except Exception as e:
                st.warning(f"Failed to read {fp}: {e}")

    if not dfs:
        st.error("No yearly data files found in data.")
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    # ── Parse dates ──────────────────────────────────────────────────────────
    date_col = 'Report_Date_as_YYYY-MM-DD' if 'Report_Date_as_YYYY-MM-DD' in df.columns else 'Report_Date_as_MM_DD_YYYY'
    df['Date'] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=['Date'])

    # ── COT Report Date ──────────────────────────────────────────────────────
    # Data is as of Tuesday close. We keep this original date.
    pass

    # ── Coerce ALL numeric columns at source (prevents str > int errors later) ─
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'Market_and_Exchange_Names' in df.columns:
        df['Market_and_Exchange_Names'] = df['Market_and_Exchange_Names'].str.strip()

    df = df.sort_values(['Market_and_Exchange_Names', 'Date']).reset_index(drop=True)

    # ── Derived metrics ───────────────────────────────────────────────────────
    df['AssetMgr_Net'] = df['Asset_Mgr_Positions_Long_All'] - df['Asset_Mgr_Positions_Short_All']
    df['LevMoney_Net'] = df['Lev_Money_Positions_Long_All'] - df['Lev_Money_Positions_Short_All']
    df['Dealer_Net']   = df['Dealer_Positions_Long_All']    - df['Dealer_Positions_Short_All']
    df['NonRept_Net']  = df['NonRept_Positions_Long_All']   - df['NonRept_Positions_Short_All']
    df['Net_Spec']     = df['AssetMgr_Net'] + df['LevMoney_Net']
    df['Net_Pct']      = df['Net_Spec'] / df['Open_Interest_All']

    # Crowding Index: LevMoney long share
    lm_gross = df['Lev_Money_Positions_Long_All'] + df['Lev_Money_Positions_Short_All']
    df['Crowding']     = df['Lev_Money_Positions_Long_All'] / lm_gross.replace(0, np.nan)

    # Dealer Hedging Bias (positive = net short = bearish hedge)
    df['Dealer_Bias']  = df['Dealer_Positions_Short_All'] - df['Dealer_Positions_Long_All']

    # OI Momentum
    df['OI_Mom']       = df['Change_in_Open_Interest_All'] / df['Open_Interest_All'].replace(0, np.nan)

    # Week-over-week flow changes
    grp = 'Market_and_Exchange_Names'
    df['ΔAM']     = df.groupby(grp)['AssetMgr_Net'].diff()
    df['ΔLM']     = df.groupby(grp)['LevMoney_Net'].diff()
    df['ΔDealer'] = df.groupby(grp)['Dealer_Net'].diff()

    return df


# ─────────────────────────────── HELPERS ─────────────────────────────────────
def get_bias(pct, threshold=0.10):
    if pd.isna(pct): return "Neutral"
    if pct >  threshold * 1.5: return "🟢 Strong Bull"
    if pct >  threshold:       return "🔵 Bull"
    if pct < -threshold * 1.5: return "🔴 Strong Bear"
    if pct < -threshold:       return "🟠 Bear"
    return "⚪ Neutral"

def get_flow_signal(dam, dlm):
    try:
        dam, dlm = float(dam), float(dlm)
    except (TypeError, ValueError):
        return "Unknown"
    if pd.isna(dam) or pd.isna(dlm): return "Unknown"
    if dam > 0 and dlm > 0: return "📈 Accumulation"
    if dam < 0 and dlm < 0: return "📉 Distribution"
    return "⚡ Divergence"

def get_conc_risk(l_pct, s_pct):
    try:
        l, s = float(l_pct), float(s_pct)
    except (TypeError, ValueError):
        return "Unknown"
    if l > 60 or s > 60: return "🔴 High"
    if l > 40 or s > 40: return "🟠 Medium"
    return "🟢 Normal"

def safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return np.nan


# ─────────────────────────────── MAIN APP ────────────────────────────────────
st.title("📊 COT Positioning Analyzer")
st.caption("Commitment of Traders — Financial Futures | 2010–2026")

df_raw = load_data()
if df_raw.empty:
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Settings")
rolling_window = st.sidebar.slider("Z-Score Rolling Window (Weeks)", 26, 260, 156)
bias_threshold = st.sidebar.slider("Bias Threshold (%)", 5, 30, 10) / 100

SPOTLIGHT_MARKETS = [
    "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
    "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE",
    "BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE",
    "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
    "EURO FX - CHICAGO MERCANTILE EXCHANGE",
    "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
    "NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE",
    "MEXICAN PESO - CHICAGO MERCANTILE EXCHANGE",
    "BRAZILIAN REAL - CHICAGO MERCANTILE EXCHANGE",
    "USD INDEX - ICE FUTURES U.S.",
    "S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE",
    "NASDAQ-100 Consolidated - CHICAGO MERCANTILE EXCHANGE",
    "DJIA Consolidated - CHICAGO BOARD OF TRADE",
    "VIX FUTURES - CBOE FUTURES EXCHANGE",
    "BITCOIN - CHICAGO MERCANTILE EXCHANGE",
    "ETHER CASH SETTLED - CHICAGO MERCANTILE EXCHANGE",
    "GOLD - COMMODITY EXCHANGE INC.",
    "CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE",
    "UST 10Y NOTE - CHICAGO BOARD OF TRADE",
    "UST 5Y NOTE - CHICAGO BOARD OF TRADE",
    "UST 2Y NOTE - CHICAGO BOARD OF TRADE",
    "UST BOND - CHICAGO BOARD OF TRADE",
    "ULTRA UST BOND - CHICAGO BOARD OF TRADE",
    "USD/CHINESE RENMINBI-OFFSHORE  - CHICAGO MERCANTILE EXCHANGE",
]
avail_markets = df_raw['Market_and_Exchange_Names'].unique()
spotlight = [m for m in SPOTLIGHT_MARKETS if m in avail_markets] or list(avail_markets[:10])

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — GLOBAL MARKET OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
all_dates = sorted(df_raw['Date'].unique(), reverse=True)
selected_report_date = st.selectbox("📅 Select Report Week", options=all_dates, index=0, format_func=lambda x: x.strftime('%Y-%m-%d'))

st.header(f"1. Global Market Overview  ·  {selected_report_date.strftime('%b %d, %Y')}")

df_latest = df_raw[(df_raw['Date'] == selected_report_date) & (df_raw['Market_and_Exchange_Names'].isin(spotlight))].copy()
df_latest['Bias']        = df_latest['Net_Pct'].apply(lambda x: get_bias(x, bias_threshold))
df_latest['Flow Signal'] = df_latest.apply(lambda r: get_flow_signal(r['ΔAM'], r['ΔLM']), axis=1)
df_latest['Risk']        = df_latest.apply(lambda r: get_conc_risk(r['Conc_Gross_LE_4_TDR_Long_All'], r['Conc_Gross_LE_4_TDR_Short_All']), axis=1)

# ── A. Overview table ─────────────────────────────────────────────────────────
st.subheader("A. Market Overview Panel")
ov = df_latest[['Market_and_Exchange_Names', 'Open_Interest_All', 'Change_in_Open_Interest_All',
                 'Net_Spec', 'Net_Pct', 'Bias', 'Flow Signal', 'Risk']].copy()
ov.rename(columns={
    'Market_and_Exchange_Names': 'Market',
    'Open_Interest_All': 'OI',
    'Change_in_Open_Interest_All': 'ΔOI',
    'Net_Spec': 'Net Spec (AM+LM)',
    'Net_Pct': 'Net %'
}, inplace=True)
st.dataframe(ov, use_container_width=True, hide_index=True, column_config={
    'OI':               st.column_config.NumberColumn(format='%,.0f'),
    'ΔOI':              st.column_config.NumberColumn(format='%,.0f'),
    'Net Spec (AM+LM)': st.column_config.NumberColumn(format='%,.0f'),
    'Net %':            st.column_config.NumberColumn(format='%.2f'),
})

# ── B. Bias Heatmap ───────────────────────────────────────────────────────────
st.subheader("B. Bias Heatmap (Net % of OI)")
# Show 26 weeks leading up to the selected_report_date
hm_weeks = 26
recent_dates = sorted([d for d in df_raw['Date'].unique() if d <= selected_report_date])[-hm_weeks:]
df_hm = df_raw[(df_raw['Market_and_Exchange_Names'].isin(spotlight)) & (df_raw['Date'].isin(recent_dates))]
hm_pivot = df_hm.pivot_table(index='Market_and_Exchange_Names', columns='Date', values='Net_Pct', aggfunc='first')
hm_pivot.index = [m.split(' - ')[0][:20] for m in hm_pivot.index]
fig_hm = go.Figure(go.Heatmap(
    z=hm_pivot.values,
    x=[str(d)[:10] for d in hm_pivot.columns],
    y=hm_pivot.index.tolist(),
    colorscale='RdYlGn',
    zmid=0,
    zmin=-0.3, zmax=0.3,
    text=np.round(hm_pivot.values * 100, 1),
    texttemplate="%{text}%",
    hoverongaps=False,
))
fig_hm.update_layout(template='plotly_dark', height=320, margin=dict(l=0, r=0, t=10, b=0),
                     xaxis_tickangle=-45)
st.plotly_chart(fig_hm, use_container_width=True)

# ── D & F. Flow & Risk ───────────────────────────────────────────────────────
col_flow, col_risk = st.columns(2)
with col_flow:
    st.subheader("D. Flow Momentum Panel")
    fl = df_latest[['Market_and_Exchange_Names', 'ΔAM', 'ΔLM', 'ΔDealer', 'Flow Signal']].copy()
    fl.rename(columns={'Market_and_Exchange_Names': 'Market'}, inplace=True)
    st.dataframe(fl, use_container_width=True, hide_index=True, column_config={
        'ΔAM':    st.column_config.NumberColumn(format='%,.0f'),
        'ΔLM':    st.column_config.NumberColumn(format='%,.0f'),
        'ΔDealer': st.column_config.NumberColumn(format='%,.0f'),
    })

with col_risk:
    st.subheader("F. Concentration Risk Panel")
    cr = df_latest[['Market_and_Exchange_Names',
                     'Conc_Gross_LE_4_TDR_Long_All', 'Conc_Gross_LE_4_TDR_Short_All',
                     'Conc_Gross_LE_8_TDR_Long_All', 'Conc_Gross_LE_8_TDR_Short_All',
                     'Risk']].copy()
    cr.rename(columns={
        'Market_and_Exchange_Names': 'Market',
        'Conc_Gross_LE_4_TDR_Long_All': 'Top4 Long%',
        'Conc_Gross_LE_4_TDR_Short_All': 'Top4 Short%',
        'Conc_Gross_LE_8_TDR_Long_All': 'Top8 Long%',
        'Conc_Gross_LE_8_TDR_Short_All': 'Top8 Short%',
    }, inplace=True)
    st.dataframe(cr, use_container_width=True, hide_index=True)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — INDIVIDUAL MARKET DRILL-DOWN
# ═══════════════════════════════════════════════════════════════════════════════
st.header("2. Market Drill-Down")
# Sort all markets, but put spotlight markets at the top for convenience
other_markets = sorted([m for m in avail_markets if m not in SPOTLIGHT_MARKETS])
market_options = spotlight + other_markets
selected       = st.selectbox("Select Market", options=market_options, index=0)

df_m = df_raw[df_raw['Market_and_Exchange_Names'] == selected].copy().sort_values('Date').reset_index(drop=True)

# ── Fetch Price Data ─────────────────────────────────────────────────────────
ticker = YF_MAPPING.get(selected)
dfp = load_price_data(ticker, df_m['Date'].min(), df_m['Date'].max())

# ── Rolling Z-Scores ──────────────────────────────────────────────────────────
df_m['Net_Z']    = (df_m['Net_Spec'] - df_m['Net_Spec'].rolling(rolling_window).mean()) / df_m['Net_Spec'].rolling(rolling_window).std()
df_m['NetPct_Z'] = (df_m['Net_Pct']  - df_m['Net_Pct'].rolling(rolling_window).mean())  / df_m['Net_Pct'].rolling(rolling_window).std()

last = df_m.iloc[-1]

# ── KPI Cards ────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
oi_val      = safe_float(last['Open_Interest_All'])
doi_val     = safe_float(last['Change_in_Open_Interest_All'])
net_val     = safe_float(last['Net_Spec'])
net_pct_val = safe_float(last['Net_Pct'])
z_val       = safe_float(last['Net_Z'])

k1.metric("Open Interest", f"{oi_val:,.0f}" if not np.isnan(oi_val) else "N/A",
          f"{doi_val:+,.0f}" if not np.isnan(doi_val) else None)
k2.metric("Net Smart Money", f"{net_val:,.0f}" if not np.isnan(net_val) else "N/A")
k3.metric("Net % of OI",     f"{net_pct_val*100:.2f}%" if not np.isnan(net_pct_val) else "N/A")
k4.metric(f"Z-Score ({rolling_window}W)", f"{z_val:.2f}" if not np.isnan(z_val) else "N/A")
crowding_val = safe_float(last['Crowding'])
k5.metric("LM Crowding Index", f"{crowding_val*100:.1f}%" if not np.isnan(crowding_val) else "N/A")

# ── Signal Banner ─────────────────────────────────────────────────────────────
rising_oi  = doi_val > 0 if not np.isnan(doi_val) else False
dam_val    = safe_float(last['ΔAM'])
dlm_val    = safe_float(last['ΔLM'])
smart_val  = safe_float(last['Net_Spec'])
retail_val = safe_float(last['NonRept_Net'])
# rising_net: is the absolute net speculative position positive (net long)?  
# This correctly describes trend direction, not just weekly flow.
rising_net = smart_val > 0 if not np.isnan(smart_val) else False
divergence = ((smart_val > 0 and retail_val < 0) or (smart_val < 0 and retail_val > 0)) if (not np.isnan(smart_val) and not np.isnan(retail_val)) else False

signals = []
if rising_oi and rising_net:
    signals.append("📈 Rising OI + Rising Net Long → **Strong Trend**")
elif not rising_oi and rising_net:
    signals.append("🔄 Falling OI + Rising Net Long → **Short Covering**")
elif rising_oi and not rising_net:
    signals.append("📉 Rising OI + Falling Net Long → **Trend Weakening**")
if divergence:
    signals.append("⚡ Smart Money vs Retail Divergence → **Contrarian Setup**")
if not np.isnan(z_val):
    if z_val > 2:   signals.append("🚨 Z > +2 → **Overbought / Crowded Long**")
    elif z_val < -2: signals.append("🚨 Z < -2 → **Oversold / Crowded Short**")
if not signals:
    signals.append("✅ No extreme signals — positioning is balanced")

with st.container(border=True):
    st.markdown("**🧭 Active Signals**")
    for s in signals:
        st.markdown(f"- {s}")

# ═══════════════════════════════════════════════════════════════════════════════
# ROW 1 — Time Series + Breakdown
# ═══════════════════════════════════════════════════════════════════════════════
col_ts, col_bd = st.columns([3, 2])

with col_ts:
    st.subheader("C. Net Position Time Series")
    fig_ts = make_subplots(specs=[[{"secondary_y": True}]])
    fig_ts.add_trace(go.Scatter(x=df_m['Date'], y=df_m['AssetMgr_Net'],
                                mode='lines', name='Asset Manager', line=dict(color='#1f77b4'), line_shape='hv'), secondary_y=False)
    fig_ts.add_trace(go.Scatter(x=df_m['Date'], y=df_m['LevMoney_Net'],
                                mode='lines', name='Lev. Money', line=dict(color='#ff7f0e'), line_shape='hv'), secondary_y=False)
    fig_ts.add_trace(go.Scatter(x=df_m['Date'], y=df_m['Net_Spec'],
                                mode='lines', name='Combined Net', line=dict(width=2.5, color='white'), line_shape='hv'), secondary_y=False)
    if not dfp.empty:
        fig_ts.add_trace(go.Scatter(x=dfp['Date'], y=dfp['Close'], mode='lines', name=f'Price ({ticker})', 
                                    line=dict(color='yellow', width=1, dash='dot')), secondary_y=True)
        fig_ts.update_yaxes(title_text="Price", secondary_y=True, showgrid=False)
        
    fig_ts.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig_ts.update_layout(template='plotly_dark', hovermode='x unified',
                         height=340, margin=dict(l=0, r=0, t=30, b=0),
                         legend=dict(orientation='h', y=1.02, x=0))
    st.plotly_chart(fig_ts, use_container_width=True)

    st.subheader("G. Smart Money vs Retail")
    fig_sm = make_subplots(specs=[[{"secondary_y": True}]])
    fig_sm.add_trace(go.Scatter(x=df_m['Date'], y=df_m['Net_Spec'],
                                mode='lines', name='Smart Money (AM+LM)', line=dict(color='#2ecc71'), line_shape='hv'), secondary_y=False)
    fig_sm.add_trace(go.Scatter(x=df_m['Date'], y=df_m['NonRept_Net'],
                                mode='lines', name='Retail (Non-Rept)', line=dict(color='#e74c3c', dash='dot'), line_shape='hv'), secondary_y=False)
    if not dfp.empty:
        fig_sm.add_trace(go.Scatter(x=dfp['Date'], y=dfp['Close'], mode='lines', name='Price', 
                                    line=dict(color='yellow', width=1, dash='dot'), showlegend=False), secondary_y=True)
        fig_sm.update_yaxes(title_text="Price", secondary_y=True, showgrid=False)
        
    fig_sm.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig_sm.update_layout(template='plotly_dark', hovermode='x unified',
                         height=280, margin=dict(l=0, r=0, t=30, b=0),
                         legend=dict(orientation='h', y=1.02, x=0))
    st.plotly_chart(fig_sm, use_container_width=True)

with col_bd:
    st.subheader("B. Position Breakdown (Latest)")
    cats   = ['Dealer', 'Asset Mgr', 'Lev. Money', 'Other']
    longs  = [safe_float(last['Dealer_Positions_Long_All']),
               safe_float(last['Asset_Mgr_Positions_Long_All']),
               safe_float(last['Lev_Money_Positions_Long_All']),
               safe_float(last['Other_Rept_Positions_Long_All'])]
    shorts = [safe_float(last['Dealer_Positions_Short_All']),
               safe_float(last['Asset_Mgr_Positions_Short_All']),
               safe_float(last['Lev_Money_Positions_Short_All']),
               safe_float(last['Other_Rept_Positions_Short_All'])]
    spds   = [safe_float(last['Dealer_Positions_Spread_All']),
               safe_float(last['Asset_Mgr_Positions_Spread_All']),
               safe_float(last['Lev_Money_Positions_Spread_All']),
               0]
    fig_bd = go.Figure([
        go.Bar(name='Long',   x=cats, y=longs,  marker_color='#2ecc71'),
        go.Bar(name='Short',  x=cats, y=shorts, marker_color='#e74c3c'),
        go.Bar(name='Spread', x=cats, y=spds,   marker_color='#95a5a6'),
    ])
    fig_bd.update_layout(barmode='group', template='plotly_dark',
                         height=340, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_bd, use_container_width=True)

    st.subheader("Dealer Bias (Hedging Indicator)")
    fig_db = go.Figure()
    fig_db.add_trace(go.Scatter(x=df_m['Date'], y=df_m['Dealer_Bias'],
                                mode='lines', name='Dealer Bias', line=dict(color='#9b59b6'), line_shape='hv'))
    fig_db.add_hline(y=0, line_dash="dash", line_color="gray")
    fig_db.update_layout(template='plotly_dark', height=280,
                         margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_db, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ROW 2 — Z-Score + OI Momentum + Crowding
# ═══════════════════════════════════════════════════════════════════════════════
st.subheader("E. Positioning Extremes — Z-Score History")
col_z, col_oi, col_cr = st.columns(3)

with col_z:
    fig_z = make_subplots(specs=[[{"secondary_y": True}]])
    fig_z.add_trace(go.Scatter(x=df_m['Date'], y=df_m['Net_Z'],
                               mode='lines', name='Net Z-Score', line=dict(color='#f39c12'), line_shape='hv'), secondary_y=False)
    if not dfp.empty:
        fig_z.add_trace(go.Scatter(x=dfp['Date'], y=dfp['Close'], mode='lines', name='Price', 
                                    line=dict(color='yellow', width=1, dash='dot'), showlegend=False), secondary_y=True)
        fig_z.update_yaxes(title_text="Price", secondary_y=True, showgrid=False)
        
    fig_z.add_hrect(y0=2,  y1=5,  fillcolor='red',  opacity=0.15, line_width=0)
    fig_z.add_hrect(y0=-5, y1=-2, fillcolor='blue', opacity=0.15, line_width=0)
    fig_z.add_hline(y=2, line_dash='dash', line_color='red', annotation_text='+2σ')
    fig_z.add_hline(y=-2, line_dash='dash', line_color='blue', annotation_text='-2σ')
    fig_z.add_hline(y=0, line_dash='dot', line_color='gray')
    fig_z.update_layout(template='plotly_dark', title='Net Spec Z-Score',
                        height=300, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_z, use_container_width=True)

with col_oi:
    fig_oi = make_subplots(specs=[[{"secondary_y": True}]])
    fig_oi.add_trace(go.Bar(x=df_m['Date'], y=df_m['Open_Interest_All'],
                            name='OI', marker_color='#3498db', opacity=0.6), secondary_y=False)
    fig_oi.add_trace(go.Scatter(x=df_m['Date'], y=df_m['Change_in_Open_Interest_All'],
                                mode='lines', name='ΔOI', line=dict(color='#e67e22')), secondary_y=True)
    fig_oi.update_layout(template='plotly_dark', title='OI + ΔOI',
                         height=300, margin=dict(l=0, r=0, t=40, b=0),
                         legend=dict(orientation='h', y=1.05, x=0))
    st.plotly_chart(fig_oi, use_container_width=True)

with col_cr:
    fig_crd = go.Figure()
    fig_crd.add_trace(go.Scatter(x=df_m['Date'], y=df_m['Crowding'] * 100,
                                 mode='lines', name='LM Crowding %', line=dict(color='#1abc9c'), line_shape='hv'))
    fig_crd.add_hline(y=70, line_dash='dash', line_color='red', annotation_text='70% (crowded long)')
    fig_crd.add_hline(y=30, line_dash='dash', line_color='blue', annotation_text='30% (crowded short)')
    fig_crd.add_hline(y=50, line_dash='dot', line_color='gray')
    fig_crd.update_layout(template='plotly_dark', title='Crowding Index (LevMoney)',
                          yaxis_title='% Long', height=300,
                          margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_crd, use_container_width=True)
