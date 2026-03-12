import base64
import requests
import streamlit as st
from auth import get_t212_credentials
import yfinance as yf




st.title("📈 ABP Trade Position Sizer")
st.caption("Risk-first position sizing based on price targets, stop loss, and MACD signals.")

st.divider()

# ── Inputs ──────────────────────────────────────────────────────────────────
st.subheader("Trade Inputs")

if "live_price" not in st.session_state:
    st.session_state.live_price = 42.0

if "portfolio_value" not in st.session_state:
    st.session_state.portfolio_value = 12500.0

ticker_col, btn_col, price_col = st.columns([3, 1, 2])
with ticker_col:
    ticker = st.text_input("Ticker Symbol", value="AAPL", placeholder="e.g. AAPL, TSLA, MSFT").upper()
with btn_col:
    st.write("")
    fetch = st.button("Get Live Price", use_container_width=True)

if fetch and ticker:
    data = yf.Ticker(ticker).fast_info
    price = getattr(data, "last_price", None) or getattr(data, "regular_market_price", None)
    if price:
        st.session_state.live_price = round(float(price), 2)
        st.success(f"Live price for **{ticker}**: ${st.session_state.live_price:.2f}")
    else:
        st.error(f"Could not fetch price for '{ticker}'. Check the ticker symbol.")

with price_col:
    CurrentPrice = st.number_input("Current Price ($)", min_value=0.01, value=st.session_state.live_price, step=0.01, format="%.2f")

col2, col3 = st.columns(2)
with col2:
    PriceTarget = st.number_input("Price Target ($)", min_value=0.01, value=52.0, step=0.01, format="%.2f")
with col3:
    StopLoss = st.number_input("Stop Loss ($)", min_value=0.01, value=39.0, step=0.01, format="%.2f")

t212_col1, t212_col2 = st.columns([2, 1])
with t212_col1:
    t212_env = st.radio("Trading212 Environment", ["Live", "Demo"], horizontal=True)
with t212_col2:
    st.write("")
    load_account = st.button("Load Portfolio Value", use_container_width=True)

if load_account:
    api_key, api_secret = get_t212_credentials()
    if not api_key:
        st.error("No Trading212 credentials found. Please save them on the Settings page.")
        st.stop()
    encoded = base64.b64encode(f"{api_key}:{api_secret or ''}".encode()).decode()
    base_url   = "https://live.trading212.com" if t212_env == "Live" else "https://demo.trading212.com"
    try:
        resp = requests.get(
            f"{base_url}/api/v0/equity/account/cash",
            headers={"Authorization": f"Basic {encoded}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        cost_basis = float(data["invested"])
        cash = float(data["free"])
        ppl = float(data.get("ppl", 0))
        stock_value = cost_basis + ppl
        conservative_value = round(min(cost_basis, stock_value) + cash, 2)
        st.session_state.portfolio_value = conservative_value
        label = "cost basis" if cost_basis <= stock_value else "stock value"
        st.success(
            f"Portfolio loaded: £{conservative_value:,.2f} "
            f"({label} £{min(cost_basis, stock_value):,.2f} + cash £{cash:,.2f})"
        )
    except requests.HTTPError:
        st.error(f"API error {resp.status_code}: {resp.text}")
    except Exception as e:
        st.error(f"Failed to load account data: {e}")

col4, col5 = st.columns(2)
with col4:
    PortfolioValue = st.number_input("Portfolio Value ($)", min_value=1.0, value=st.session_state.portfolio_value, step=100.0, format="%.2f")
with col5:
    MaxLoss_pct = st.slider("Max Acceptable Loss (% of portfolio)", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

col6, col7 = st.columns(2)
with col6:
    MACD_Monthly = st.selectbox("MACD Monthly Signal", options=[0, 1, 2], index=0,
                                 help="0 = Weak/Bearish, 1 = Neutral, 2 = Strong/Bullish")
with col7:
    MACD_Weekly = st.selectbox("MACD Weekly Signal", options=[0, 1, 2], index=0,
                                help="0 = Weak/Bearish, 1 = Neutral, 2 = Strong/Bullish")

st.divider()

# ── Calculate button ─────────────────────────────────────────────────────────
if st.button("Calculate Position Size", type="primary", use_container_width=True):

    # ── Input validation ──────────────────────────────────────────────────────
    errors = []
    if StopLoss >= CurrentPrice:
        errors.append("Stop Loss must be **below** the Current Price.")
    if PriceTarget <= CurrentPrice:
        errors.append("Price Target must be **above** the Current Price.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        # ── Calculations ──────────────────────────────────────────────────────
        def pct_change(old, new):
            return (new - old) / old

        ImpliedUpside   = pct_change(CurrentPrice, PriceTarget)
        ImpliedDownside = abs(pct_change(CurrentPrice, StopLoss))
        R2R             = ImpliedUpside / ImpliedDownside

        MaxLoss = (MaxLoss_pct / 100) * PortfolioValue

        MACD_Score = MACD_Weekly + MACD_Monthly
        macd_lookup = {0: 2.0, 1: 1.5, 2: 1.0}
        DownsideRiskFactor = macd_lookup[MACD_Score]

        UpsideRewardFactor = R2R / 2 if DownsideRiskFactor == 1.0 else 1.0
        AdjustmentFactor   = UpsideRewardFactor / DownsideRiskFactor

        InvestmentValue     = MaxLoss / ImpliedDownside
        InvestmentValue_Adj = InvestmentValue * AdjustmentFactor

        # ── Warnings ─────────────────────────────────────────────────────────
        if R2R < 2:
            st.warning(f"⚠️ Weak risk/reward ratio ({R2R:.2f}:1). A ratio of at least 2:1 is generally recommended.")

        # ── Trade summary ─────────────────────────────────────────────────────
        st.subheader("Trade Summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("Current Price", f"${CurrentPrice:.2f}")
        m2.metric("Price Target", f"${PriceTarget:.2f}", delta=f"+{ImpliedUpside*100:.1f}%")
        m3.metric("Stop Loss", f"${StopLoss:.2f}", delta=f"-{ImpliedDownside*100:.1f}%", delta_color="inverse")

        st.divider()

        # ── Step-by-step report ───────────────────────────────────────────────
        st.subheader("Step-by-Step Breakdown")

        with st.expander("Step 1 — Upside & Downside Percentages", expanded=True):
            st.markdown(f"""
- **Implied Upside** = (Target − Current) ÷ Current
  = (${PriceTarget:.2f} − ${CurrentPrice:.2f}) ÷ ${CurrentPrice:.2f} = **{ImpliedUpside*100:.2f}%**

- **Implied Downside** = |( Stop − Current) ÷ Current|
  = |(${StopLoss:.2f} − ${CurrentPrice:.2f}) ÷ ${CurrentPrice:.2f}| = **{ImpliedDownside*100:.2f}%**
""")

        with st.expander("Step 2 — Risk / Reward Ratio", expanded=True):
            st.markdown(f"""
- **R:R** = Implied Upside ÷ Implied Downside
  = {ImpliedUpside*100:.2f}% ÷ {ImpliedDownside*100:.2f}% = **{R2R:.2f} : 1**

For every 1% of downside risk, you have **{R2R:.2f}%** of upside potential.
""")

        with st.expander("Step 3 — Maximum Acceptable Loss", expanded=True):
            st.markdown(f"""
- **Max Loss ($)** = Max Loss % × Portfolio Value
  = {MaxLoss_pct:.1f}% × ${PortfolioValue:,.2f} = **${MaxLoss:,.2f}**

You are willing to lose no more than **${MaxLoss:,.2f}** on this trade.
""")

        with st.expander("Step 4 — MACD Score & Downside Risk Factor", expanded=True):
            st.markdown(f"""
- **MACD Score** = Monthly ({MACD_Monthly}) + Weekly ({MACD_Weekly}) = **{MACD_Score}**

| MACD Score | Downside Risk Factor |
|---|---|
| 0 (Weak) | 2.0× |
| 1 (Neutral) | 1.5× |
| 2 (Strong) | 1.0× |

→ Score of **{MACD_Score}** → Downside Risk Factor = **{DownsideRiskFactor}×**
A higher factor means weaker momentum confirmation, so the position size is reduced more aggressively.
""")

        with st.expander("Step 5 — Upside Reward Factor", expanded=True):
            if DownsideRiskFactor == 1.0:
                st.markdown(f"""
- MACD Score is 2 (strong confirmation), so reward factor scales with the R:R ratio.
- **Upside Reward Factor** = R:R ÷ 2 = {R2R:.2f} ÷ 2 = **{UpsideRewardFactor:.4f}**
""")
            else:
                st.markdown(f"""
- MACD Score is below 2, so the reward factor is held at a conservative baseline.
- **Upside Reward Factor** = **{UpsideRewardFactor:.1f}** (flat, no amplification)
""")

        with st.expander("Step 6 — Adjustment Factor", expanded=True):
            st.markdown(f"""
- **Adjustment Factor** = Upside Reward Factor ÷ Downside Risk Factor
  = {UpsideRewardFactor:.4f} ÷ {DownsideRiskFactor} = **{AdjustmentFactor:.4f}**

This factor scales the base position size up or down based on the combined MACD signal.
""")

        with st.expander("Step 7 — Base Investment Value", expanded=True):
            st.markdown(f"""
- **Base Investment** = Max Loss ÷ Implied Downside
  = ${MaxLoss:,.2f} ÷ {ImpliedDownside:.4f} = **${InvestmentValue:,.2f}**

This is the raw position size at which hitting the stop loss would cost exactly ${MaxLoss:,.2f}.
""")

        with st.expander("Step 8 — Adjusted Investment Value", expanded=True):
            st.markdown(f"""
- **Adjusted Investment** = Base Investment × Adjustment Factor
  = ${InvestmentValue:,.2f} × {AdjustmentFactor:.4f} = **${InvestmentValue_Adj:,.2f}**

The base position is scaled by the MACD-driven adjustment factor.
""")

        st.divider()

        # ── Final recommendation ──────────────────────────────────────────────
        st.subheader("Final Recommendation")
        st.success(f"### Suggested Position Size: ${InvestmentValue_Adj:,.2f}")

        shares = InvestmentValue_Adj / CurrentPrice
        actual_loss = shares * (CurrentPrice - StopLoss)
        actual_loss_pct = actual_loss / PortfolioValue * 100

        r1, r2, r3 = st.columns(3)
        r1.metric("Shares to Buy", f"{shares:.1f}")
        r2.metric("Loss if Stopped Out", f"${actual_loss:,.2f}")
        r3.metric("Portfolio Risk", f"{actual_loss_pct:.2f}%")

