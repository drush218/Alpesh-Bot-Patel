import base64
import requests
import pandas as pd
import streamlit as st
from auth import require_auth, logout, get_t212_credentials

st.set_page_config(page_title="ABP Portfolio", page_icon="💼", layout="centered")

require_auth()

with st.sidebar:
    st.write(f"Signed in as: {st.session_state.auth_user.email}")
    if st.button("Log out"):
        logout()

st.title("💼 Portfolio Overview")
st.caption("Live positions and allocation from Trading212.")

st.divider()

env_col, btn_col = st.columns([2, 1])
with env_col:
    t212_env = st.radio("Trading212 Environment", ["Live", "Demo"], horizontal=True)
with btn_col:
    st.write("")
    load_btn = st.button("Load Portfolio", type="primary", use_container_width=True)

if load_btn:
    api_key, api_secret = get_t212_credentials()
    if not api_key:
        st.error("No Trading212 credentials found. Please save them on the Settings page.")
        st.stop()
    encoded  = base64.b64encode(f"{api_key}:{api_secret or ''}".encode()).decode()
    base_url = "https://live.trading212.com" if t212_env == "Live" else "https://demo.trading212.com"
    headers  = {"Authorization": f"Basic {encoded}"}

    try:
        cash_resp = requests.get(f"{base_url}/api/v0/equity/account/cash",  headers=headers, timeout=10)
        pos_resp  = requests.get(f"{base_url}/api/v0/equity/portfolio",      headers=headers, timeout=10)
        cash_resp.raise_for_status()
        pos_resp.raise_for_status()

        cash      = cash_resp.json()
        positions = pos_resp.json()

        st.session_state.portfolio_cash      = cash
        st.session_state.portfolio_positions = positions
        st.session_state.portfolio_env       = t212_env

    except requests.HTTPError as e:
        st.error(f"API error {e.response.status_code}: {e.response.text}")
        st.stop()
    except Exception as e:
        st.error(f"Failed to load portfolio: {e}")
        st.stop()

if "portfolio_cash" not in st.session_state:
    st.info("Select your environment and click **Load Portfolio** to begin.")
    st.stop()

cash      = st.session_state.portfolio_cash
positions = st.session_state.portfolio_positions

# ── Key stats ────────────────────────────────────────────────────────────────
invested   = float(cash.get("invested", 0))
free_cash  = float(cash.get("free", 0))
ppl        = float(cash.get("ppl", 0))
total      = float(cash.get("total", invested + free_cash + ppl))

st.subheader("Account Summary")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Portfolio Value", f"${total:,.2f}")
m2.metric("Cost Basis",      f"${invested:,.2f}")
m3.metric("Cash",            f"${free_cash:,.2f}", delta=f"{free_cash/total*100:.1f}% of portfolio")
m4.metric("Unrealised P&L",  f"${ppl:,.2f}",       delta=f"{ppl/invested*100:.1f}%" if invested else None,
          delta_color="normal")

st.divider()

# ── Holdings table ────────────────────────────────────────────────────────────
st.subheader("Holdings")

if not positions:
    st.info("No open positions found.")
else:
    rows = []
    for p in positions:
        qty           = float(p.get("quantity", 0))
        avg_price     = float(p.get("averagePrice", 0))
        curr_price    = float(p.get("currentPrice", 0))
        value         = qty * curr_price
        cost          = qty * avg_price
        position_ppl  = float(p.get("ppl", value - cost))
        ppl_pct       = (position_ppl / cost * 100) if cost else 0

        rows.append({
            "Ticker":         p.get("ticker", ""),
            "Qty":            round(qty, 4),
            "Avg Price":      avg_price,
            "Curr Price":     curr_price,
            "Value ($)":      round(value, 2),
            "P&L ($)":        round(position_ppl, 2),
            "P&L (%)":        round(ppl_pct, 2),
            "% of Portfolio": 0,  # calculated after all rows are built
        })

    # Add cash as its own row
    rows.append({
        "Ticker":         "CASH",
        "Qty":            "-",
        "Avg Price":      "-",
        "Curr Price":     "-",
        "Value ($)":      round(free_cash, 2),
        "P&L ($)":        "-",
        "P&L (%)":        "-",
        "% of Portfolio": 0,
    })

    # Recalculate allocation using sum of displayed values to avoid
    # cross-currency distortion (positions priced in USD/EUR vs GBP account total)
    display_total = sum(r["Value ($)"] for r in rows if isinstance(r["Value ($)"], (int, float)))
    for r in rows:
        if isinstance(r["Value ($)"], (int, float)) and display_total:
            r["% of Portfolio"] = round(r["Value ($)"] / display_total * 100, 2)

    df = pd.DataFrame(rows).sort_values("% of Portfolio", ascending=False).reset_index(drop=True)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "% of Portfolio": st.column_config.ProgressColumn(
                "% of Portfolio",
                format="%.2f%%",
                min_value=0,
                max_value=100,
            ),
            "P&L ($)": st.column_config.NumberColumn("P&L ($)", format="$%.2f"),
            "Value ($)": st.column_config.NumberColumn("Value ($)", format="$%.2f"),
            "Avg Price": st.column_config.NumberColumn("Avg Price", format="$%.2f"),
            "Curr Price": st.column_config.NumberColumn("Curr Price", format="$%.2f"),
            "P&L (%)": st.column_config.NumberColumn("P&L (%)", format="%.2f%%"),
        },
    )

    # ── Allocation bar chart ──────────────────────────────────────────────────
    st.subheader("Allocation")
    chart_df = df[["Ticker", "% of Portfolio"]].set_index("Ticker")
    st.bar_chart(chart_df)
