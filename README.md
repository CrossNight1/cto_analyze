# COT Analyzer Dashboard

A Streamlit + Plotly dashboard for analyzing **CFTC Commitment of Traders (COT) Financial Futures** data, with Yahoo Finance price overlays for signal validation.

---

## Project Structure

```
cto_analyze/
├── app.py          # Streamlit dashboard application
├── data/           # Downloaded yearly CSVs (cot_2010.csv … cot_2026.csv)
├── cto.py          # Data download script (CFTC → data/)
└── README.md       # This file
```

---

## Quick Start

### 1. Download COT Data

```bash
cd /Users/leoinv/Documents/CODE
../.venv/bin/python cto_analyze/cto.py
```

This downloads yearly ZIP files from CFTC for 2010–2026 and saves them as individual CSVs in `cto_analyze/data/`. Each file is self-contained and format-compatible.

> **Re-run any time** to refresh data. The script will overwrite the yearly files with the latest weekly data.

### 2. Launch the Dashboard

```bash
~/Documents/CODE/run_dashboard.sh
```

Or directly:

```bash
cd /Users/leoinv/Documents/CODE
../.venv/bin/streamlit run cto_analyze/app.py
```

Dashboard opens at `http://localhost:8501`.

---

## Data Source

**CFTC Traders in Financial Futures (TFF) Report**
- URL: `https://www.cftc.gov/files/dea/history/com_fin_txt_{YEAR}.zip`
- Released every **Friday** for the prior Tuesday's close.
- Coverage: All major CME, CBOT, ICE, and CBOE financial futures.
- Format: `Combined` (futures + options combined positions).

### Participant Categories

| Category | Who They Are | Behavior |
|---|---|---|
| **Dealer** | Banks, prime brokers | Hedgers — usually contrarian to the market |
| **Asset Manager (AM)** | Pension funds, mutual funds | Trend followers — large, slow-moving |
| **Leveraged Money (LM)** | Hedge funds, CTAs | Fast money — opportunistic, reactive |
| **Other Reportable** | Other large traders | Mixed — corporate hedgers, etc. |
| **Non-Reportable** | Retail traders | Small, usually wrong at extremes |

---

## Methodology

### Derived Metrics

All metrics are computed from raw CFTC position data. The formulas below exactly mirror what is implemented in `load_data()` in `app.py`.

#### 1. Net Position (per category)

```
AssetMgr_Net = Asset_Mgr_Long - Asset_Mgr_Short
LevMoney_Net = Lev_Money_Long - Lev_Money_Short
Dealer_Net   = Dealer_Long    - Dealer_Short
NonRept_Net  = NonRept_Long   - NonRept_Short
```

**Interpretation:** Positive = net long (bullish bias), Negative = net short (bearish bias).

#### 2. Combined Smart Money Net (Net_Spec)

```
Net_Spec = AssetMgr_Net + LevMoney_Net
```

**Rationale:** Asset Managers and Leveraged Money together represent the "speculative" (directional) market participants. Dealers are excluded because they are primarily hedgers whose positions are structurally opposite to their clients.

#### 3. Net % of Open Interest (Net_Pct)

```
Net_Pct = Net_Spec / Open_Interest_All
```

**Why normalize by OI?** Raw contract numbers are not comparable across markets or even across time for the same market as OI scales up/down. Net_Pct gives a standardized [-1, +1] range that is directly comparable.

#### 4. Directional Bias Signal

```
if Net_Pct >  threshold * 1.5  → "Strong Bull"
if Net_Pct >  threshold        → "Bull"
if Net_Pct < -threshold * 1.5  → "Strong Bear"
if Net_Pct < -threshold        → "Bear"
else                           → "Neutral"
```

> **Default threshold = 10%** (adjustable in the sidebar). "Strong" = 1.5× the threshold.

#### 5. Crowding Index (Leveraged Money)

```
Crowding = LevMoney_Long / (LevMoney_Long + LevMoney_Short)
```

**Range:** 0 to 1 (displayed as 0%–100%).
- `> 70%` → Crowded long — squeeze risk if price reverses.
- `< 30%` → Crowded short — squeeze risk if price rallies.
- `~50%` → Balanced positioning.

> This is a pure Leveraged Money metric (hedge funds / CTAs), making it a reliable fast-money sentiment gauge.

#### 6. Dealer Hedging Bias

```
Dealer_Bias = Dealer_Short - Dealer_Long
```

**Interpretation:** Dealers are structural hedgers — when this is **positive (high)**, dealers are net short, which typically means they are hedging large client long books → clients are bullish, creating a contrarian warning. When **negative**, dealers are net long, hedging client short books.

> ⚠️ Dealer Bias is NOT a direct directional signal. It is a **contrarian confirmation** tool: extreme Dealer_Bias opposite to Net_Spec suggests positioning may be approaching an inflection point.

#### 7. Week-over-Week Flow Changes (ΔAM, ΔLM, ΔDealer)

```
ΔAM     = AssetMgr_Net(t) - AssetMgr_Net(t-1)
ΔLM     = LevMoney_Net(t) - LevMoney_Net(t-1)
ΔDealer = Dealer_Net(t)   - Dealer_Net(t-1)
```

**Flow Signal Logic:**
```
ΔAM > 0 AND ΔLM > 0  → "Accumulation" (both smart money groups buying)
ΔAM < 0 AND ΔLM < 0  → "Distribution" (both smart money groups selling)
divergence            → "Divergence" (AM and LM disagree — unstable)
```

> Divergence between AM (slow, trend-following) and LM (fast, tactical) is often seen at turning points.

#### 8. Z-Score (Positioning Extremes)

```
Z = (Net_Spec - rolling_mean(Net_Spec, N)) / rolling_std(Net_Spec, N)
```

**Default lookback window: 156 weeks (3 years)**, adjustable via the sidebar.

**Interpretation:**
```
Z > +2  → Overbought (statistically extreme long positioning)
Z < -2  → Oversold  (statistically extreme short positioning)
```

> Z-scores measure how many standard deviations current positioning sits above or below its own historical average. This is the most reliable "crowding" metric because it is fully context-adjusted per market.

#### 9. OI Momentum

```
OI_Mom = Change_in_OI / Open_Interest
```

Computed but used contextually in signal generation. Rising OI validates trend conviction; falling OI suggests position unwinding.

#### 10. Concentration Risk

```
Source: Conc_Gross_LE_4_TDR_Long_All, Conc_Gross_LE_4_TDR_Short_All
        Conc_Gross_LE_8_TDR_Long_All, Conc_Gross_LE_8_TDR_Short_All
```

These CFTC-provided fields show what percentage of total long or short OI is controlled by the top 4 and top 8 largest traders.

```
> 60% → "High" concentration risk (squeeze potential)
> 40% → "Medium" (watch closely)
≤ 40% → "Normal"
```

---

## Signal Logic (Active Signals Panel)

The **Active Signals** box in the drill-down section fires based on the most recent report week for the selected market:

| Signal | Trigger Condition | Interpretation |
|---|---|---|
| 📈 Strong Trend | Rising OI + Net_Spec > 0 | New money entering, smart money is net long — trend likely continuing |
| 🔄 Short Covering | Falling OI + Net_Spec > 0 | Smart money net long but OI declining — shorts being covered, not new longs |
| 📉 Trend Weakening | Rising OI + Net_Spec < 0 | New money entering but smart money is net short — possible distribution |
| ⚡ Contrarian Setup | Smart Money and Retail on opposite sides | Classic contrarian setup — retail has been historically wrong at extremes |
| 🚨 Overbought | Z-Score > +2 | Positioning is statistically extreme long — watch for reversal |
| 🚨 Oversold | Z-Score < -2 | Positioning is statistically extreme short — watch for squeeze |

> **Note on "Strong Trend" vs "Short Covering":** The distinction between real accumulation and short covering is critical. Rising OI + bullish Net_Spec is a stronger, more durable signal. Falling OI + bullish Net_Spec indicates position liquidation (shorts covering), which can produce a violent but short-lived rally.

---

## Dashboard Panels

### Section 1: Global Market Overview

- **📅 Report Week Selector** — Browse any historical CFTC report week. All panels in Section 1 update to that week's snapshot.
- **A. Market Overview Table** — OI, ΔOI, Net Spec, Net %, Bias, Flow Signal, Concentration Risk for all spotlight markets side by side.
- **B. Bias Heatmap** — 26-week rolling heatmap of Net_Pct across all spotlight markets. Green = net long, Red = net short. Useful for spotting cross-market rotation.
- **D. Flow Momentum Table** — Weekly ΔAM, ΔLM, ΔDealer with Accumulation / Distribution / Divergence signal.
- **F. Concentration Risk Table** — Top 4 and Top 8 trader concentration percentages for long and short sides.

### Section 2: Market Drill-Down

- **KPI Cards** — Open Interest, Net Smart Money, Net % of OI, Z-Score, Crowding Index.
- **🧭 Active Signals** — Auto-fired signals based on latest data.
- **C. Net Position Time Series** — Full history of AM Net, LM Net, and Combined Net (left Y-axis) with price overlay (right Y-axis, yellow dotted line from Yahoo Finance).
- **G. Smart Money vs Retail** — Smart Money (AM+LM) vs Non-Reportable (retail) net positions with price overlay.
- **B. Position Breakdown** — Latest week grouped bar chart showing Long / Short / Spread for all 4 participant categories.
- **Dealer Bias** — Historical dealer net short bias. Spikes indicate large hedging activity (contrarian).
- **E. Z-Score** — Full Z-score history with ±2σ bands and price overlay.
- **OI + ΔOI** — Bar chart of open interest with weekly change overlay on secondary axis.
- **Crowding Index** — LevMoney long share % over time with 30%/70% extreme lines.

---

## Price Data (Yahoo Finance)

Price data is fetched via `yfinance` for supported instruments. It is cached per session.

| COT Market | Yahoo Finance Ticker |
|---|---|
| EURO FX | 6E=F |
| BRITISH POUND STERLING | 6B=F |
| JAPANESE YEN | 6J=F |
| CANADIAN DOLLAR | 6C=F |
| AUSTRALIAN DOLLAR | 6A=F |
| SWISS FRANC | 6S=F |
| NZ DOLLAR | 6N=F |
| MEXICAN PESO | 6M=F |
| BRAZILIAN REAL | 6L=F |
| USD INDEX | DX=F |
| S&P 500 Consolidated | ES=F |
| NASDAQ-100 Consolidated | NQ=F |
| DJIA Consolidated | YM=F |
| GOLD | GC=F |
| CRUDE OIL | CL=F |
| UST 10Y NOTE | ZN=F |
| UST 5Y NOTE | ZF=F |
| UST 2Y NOTE | ZT=F |
| UST BOND | ZB=F |
| ULTRA UST BOND | UB=F |
| BITCOIN | BTC-USD |
| ETHER | ETH-USD |
| VIX FUTURES | VX=F |

> If Yahoo Finance data is unavailable for a market, the chart silently renders without the price line.

---

## Key Analytical Insights to Look For

### High-Confidence Signals
1. **Z-score > +2 AND Dealer_Bias rising sharply** → Crowded long + hedging pressure → high probability of short-term reversal.
2. **Z-score < -2 AND Crowding < 30%** → Crowded short + LM fully positioned short → squeeze setup.
3. **Net_Spec rising AND OI rising** → "Smart money conviction" — strongest trend signal.
4. **Smart Money vs Retail divergence at extremes** → Retail is wrong at turning points historically.

### Warning Signs
- **Divergence Flow Signal** (AM buying, LM selling or vice versa) = regime uncertainty, wait for resolution.
- **High concentration (>60%)** = a few large players dominate. Thin markets prone to gap moves if they exit.
- **Falling OI while Net_Spec is at extremes** = unwinding, not new positioning — reliability decreases.

---

## Settings (Sidebar)

| Setting | Default | Effect |
|---|---|---|
| Z-Score Rolling Window | 156 weeks (3Y) | Longer = smoother baseline, fewer signals. Shorter = more sensitive. |
| Bias Threshold | 10% | Net% of OI required to classify as Bull/Bear. Adjust per market volatility. |

---

## Dependencies

```
streamlit
plotly
pandas
numpy
yfinance
```

All installed in `/Users/leoinv/Documents/CODE/.venv`.
