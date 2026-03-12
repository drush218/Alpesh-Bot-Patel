import base64, requests, pandas as pd, streamlit as st, time
from datetime import datetime, timezone
from auth import get_t212_credentials, get_deposit_stats, save_deposit_stats

st.title(chr(128188) + " Portfolio Overview")
st.caption("Live positions and allocation from Trading212.")
st.divider()

load_btn = st.button("Load Portfolio", type="primary")

if load_btn:
    api_key, api_secret = get_t212_credentials()
    if not api_key:
        st.error("No Trading212 credentials found. Please save them on the Settings page.")
        st.stop()
    encoded  = base64.b64encode(f"{api_key}:{api_secret or ''}".encode()).decode()
    base_url = "https://live.trading212.com"
    headers  = {"Authorization": f"Basic {encoded}"}
    try:
        cash_resp = requests.get(f"{base_url}/api/v0/equity/account/cash", headers=headers, timeout=10)
        pos_resp  = requests.get(f"{base_url}/api/v0/equity/portfolio",    headers=headers, timeout=10)
        cash_resp.raise_for_status()
        pos_resp.raise_for_status()
        st.session_state.portfolio_cash      = cash_resp.json()
        st.session_state.portfolio_positions = pos_resp.json()
    except requests.HTTPError as e:
        st.error(f"API error {e.response.status_code}: {e.response.text}")
        st.stop()
    except Exception as e:
        st.error(f"Failed to load portfolio: {e}")
        st.stop()
    deposit_stats = get_deposit_stats()
    now_iso       = datetime.now(timezone.utc).isoformat()
    is_stale      = deposit_stats is None or (
        datetime.now(timezone.utc) - datetime.fromisoformat(deposit_stats["cached_at"])
    ).total_seconds() > 86400

    if is_stale:
        incremental   = deposit_stats is not None and deposit_stats.get("last_tx_fetched_at")
        since_iso     = deposit_stats["last_tx_fetched_at"] if incremental else None
        label         = "Updating deposit history..." if incremental else "Fetching deposit history (first time, may take a moment)..."

        status_text   = st.empty()
        status_text.info(label)
        try:
            net_delta   = 0.0
            first_date  = None if not incremental else deposit_stats.get("first_deposit_date", "")
            pages       = 0
            next_path   = "/api/v0/equity/history/transactions?limit=50"
            done        = False

            while next_path and not done:
                resp = requests.get(f"https://live.trading212.com{next_path}", headers=headers, timeout=20)
                resp.raise_for_status()
                data  = resp.json()
                items = data.get("items", [])
                pages += 1
                status_text.info(f"{label}  Page {pages}, {pages * 50} transactions scanned...")

                for tx in items:
                    tx_type = tx.get("type", "")
                    amount  = float(tx.get("amount", 0))
                    date    = tx.get("dateTime", "")
                    # Stop once we reach transactions we've already counted
                    if since_iso and date and date <= since_iso:
                        done = True
                        break
                    if tx_type == "DEPOSIT" and amount >= 5:
                        net_delta += amount
                    elif tx_type == "WITHDRAW":
                        net_delta -= abs(amount)
                    elif tx_type == "TRANSFER":
                        net_delta += amount  # positive = transfer in, negative = transfer out
                    if not incremental and tx_type in ("DEPOSIT", "WITHDRAW", "TRANSFER") and date:
                        if first_date is None or date < first_date:
                            first_date = date

                raw_next = data.get("nextPagePath")
                if raw_next and not raw_next.startswith("/"):
                    raw_next = f"/api/v0/equity/history/transactions?{raw_next}"
                next_path = raw_next if not done else None

                if next_path:
                    remaining = int(resp.headers.get("x-ratelimit-remaining", 1))
                    if remaining <= 1:
                        reset_at = int(resp.headers.get("x-ratelimit-reset", 0))
                        wait     = max(0, reset_at - time.time()) + 0.5
                        status_text.info(f"Rate limit reached — resuming in {wait:.0f}s...")
                        time.sleep(wait)
                    else:
                        time.sleep(0.2)

            new_total      = (deposit_stats["total_deposited"] if incremental else 0.0) + net_delta
            new_first_date = first_date or ""
            save_deposit_stats(new_total, new_first_date, now_iso)
            deposit_stats  = {"total_deposited": new_total, "first_deposit_date": new_first_date,
                               "cached_at": now_iso, "last_tx_fetched_at": now_iso}
            status_text.empty()
        except Exception as e:
            status_text.empty()
            st.warning(f"Could not fetch deposit history: {e}")
            deposit_stats = deposit_stats  # use stale cache if available
    st.session_state.deposit_stats = deposit_stats

if "portfolio_cash" not in st.session_state:
    st.info("Click **Load Portfolio** to begin.")
    st.stop()

cash      = st.session_state.portfolio_cash
positions = st.session_state.portfolio_positions
invested   = float(cash.get("invested", 0))
free_cash  = float(cash.get("free", 0))
ppl        = float(cash.get("ppl", 0))
total      = float(cash.get("total", invested + free_cash + ppl))

st.subheader("Account Summary")
deposit_stats = st.session_state.get("deposit_stats")
if deposit_stats and deposit_stats.get("total_deposited"):
    deposited  = deposit_stats["total_deposited"]
    raw_return = total - deposited
    pct_return = raw_return / deposited * 100
    first_date_str = deposit_stats.get("first_deposit_date", "")
    years = None
    if first_date_str:
        try:
            first_dt = datetime.fromisoformat(first_date_str.replace("Z", "+00:00"))
            years    = (datetime.now(timezone.utc) - first_dt).days / 365.25
        except Exception:
            years = None
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Portfolio Value", f"£{total:,.2f}")
    r2.metric("Net Deposited",   f"£{deposited:,.2f}")
    r3.metric("Total Return",    f"£{raw_return:+,.2f}", delta=f"{pct_return:+.2f}%", delta_color="normal")
    if years and years > 0:
        cagr = ((total / deposited) ** (1 / years) - 1) * 100
        r4.metric("Annualised (CAGR)", f"{cagr:.2f}%", delta=f"over {years:.1f} yrs", delta_color="off")
    else:
        r4.metric("Annualised (CAGR)", "N/A")
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Cost Basis",     f"${invested:,.2f}")
    m2.metric("Cash",           f"${free_cash:,.2f}", delta=f"{free_cash/total*100:.1f}% of portfolio")
    m3.metric("Unrealised P&L", f"${ppl:,.2f}", delta=f"{ppl/invested*100:.1f}%" if invested else None, delta_color="normal")
else:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Portfolio Value", f"${total:,.2f}")
    m2.metric("Cost Basis",      f"${invested:,.2f}")
    m3.metric("Cash",            f"${free_cash:,.2f}", delta=f"{free_cash/total*100:.1f}% of portfolio")
    m4.metric("Unrealised P&L",  f"${ppl:,.2f}", delta=f"{ppl/invested*100:.1f}%" if invested else None, delta_color="normal")

st.divider()
st.subheader("Holdings")

if not positions:
    st.info("No open positions found.")
else:
    rows = []
    for p in positions:
        qty        = float(p.get("quantity", 0))
        avg_price  = float(p.get("averagePrice", 0))
        curr_price = float(p.get("currentPrice", 0))
        value      = qty * curr_price
        cost       = qty * avg_price
        pos_ppl    = float(p.get("ppl", value - cost))
        ppl_pct    = (pos_ppl / cost * 100) if cost else 0
        rows.append({
            "Ticker": p.get("ticker", ""), "Qty": round(qty, 4),
            "Avg Price": avg_price, "Curr Price": curr_price,
            "Cost ($)": round(cost, 2), "Value ($)": round(value, 2),
            "P&L ($)": round(pos_ppl, 2), "P&L (%)": round(ppl_pct, 2),
            "% of Portfolio": 0,
        })
    rows.append({"Ticker": "CASH", "Qty": "-", "Avg Price": "-", "Curr Price": "-",
                 "Value ($)": round(free_cash, 2), "P&L ($)": "-", "P&L (%)": "-", "% of Portfolio": 0})
    display_total = sum(r["Value ($)"] for r in rows if isinstance(r["Value ($)"], (int, float)))
    for r in rows:
        if isinstance(r["Value ($)"], (int, float)) and display_total:
            r["% of Portfolio"] = round(r["Value ($)"] / display_total * 100, 2)
    df = pd.DataFrame(rows).sort_values("% of Portfolio", ascending=False).reset_index(drop=True)
    table_cols = ["Ticker", "Qty", "Avg Price", "Curr Price", "Value ($)", "P&L ($)", "P&L (%)"]
    st.dataframe(df[table_cols], use_container_width=True, hide_index=True, column_config={
        "P&L ($)":    st.column_config.NumberColumn("P&L ($)",    format="$%.2f"),
        "Value ($)":  st.column_config.NumberColumn("Value ($)",  format="$%.2f"),
        "Avg Price":  st.column_config.NumberColumn("Avg Price",  format="$%.2f"),
        "Curr Price": st.column_config.NumberColumn("Curr Price", format="$%.2f"),
        "P&L (%)":    st.column_config.NumberColumn("P&L (%)",    format="%.2f%%"),
    })

    # ── Allocation chart ──────────────────────────────────────────────────────
    st.subheader("Allocation")
    import plotly.graph_objects as go
    import yfinance as yf

    @st.cache_data(ttl=86400, show_spinner=False)
    def _company_name(ticker):
        clean = ticker.split("_")[0]
        try:
            info = yf.Ticker(clean).info
            return info.get("longName") or info.get("shortName") or clean
        except Exception:
            return clean

    sort_by = st.radio("Sort by", ["Size", "A-Z"], horizontal=True, key="alloc_sort")
    stocks = df[df["Ticker"] != "CASH"].copy()
    stocks = (stocks.sort_values("% of Portfolio", ascending=True)
              if sort_by == "Size" else stocks.sort_values("Ticker", ascending=False))
    stocks["Cost (%)"] = (stocks["Cost ($)"] / display_total * 100).round(1)
    stocks["Company"]  = stocks["Ticker"].apply(_company_name)

    BLUE  = "rgba(99,102,241,0.85)"
    TRACK = "rgba(150,150,150,0.18)"

    fig = go.Figure()

    # Background track pill
    fig.add_trace(go.Bar(
        x=[100] * len(stocks), y=stocks["Ticker"], orientation="h",
        marker=dict(color=TRACK, cornerradius=8),
        showlegend=False, hoverinfo="skip",
    ))

    # Allocation bar — no text, labels handled by annotations on the track
    fig.add_trace(go.Bar(
        x=stocks["% of Portfolio"], y=stocks["Ticker"], orientation="h",
        marker=dict(color=BLUE, cornerradius=8),
        showlegend=False,
        hovertemplate="<b>%{y}</b><br>Allocation: %{x:.1f}%<extra></extra>",
    ))

    # Cost-basis dot + callout
    fig.add_trace(go.Scatter(
        x=stocks["Cost (%)"], y=stocks["Ticker"],
        mode="markers+text",
        marker=dict(size=11, color="white", symbol="circle",
                    line=dict(color="rgba(60,60,60,0.7)", width=1.5)),
        text=[f"  {v:.1f}%" for v in stocks["Cost (%)"]],
        textposition="middle right",
        textfont=dict(size=11, color="#111827", family="Inter, system-ui, sans-serif"),
        showlegend=False,
        hovertemplate="<b>%{y}</b><br>Cost basis: %{x:.1f}% of portfolio<extra></extra>",
    ))

    # Left annotations: company name (truncated) + grey ticker
    for _, row in stocks.iterrows():
        display_ticker = row["Ticker"].split("_")[0]
        name = row["Company"]
        short_name = name if len(name) <= 22 else name[:21] + "…"
        fig.add_annotation(
            xref="paper", yref="y",
            x=0, y=row["Ticker"],
            text=(f"<b>{short_name}</b>"
                  f"<br><span style='color:#9ca3af;font-size:10px'>{display_ticker}</span>"),
            showarrow=False, xanchor="right", xshift=-10,
            font=dict(size=12, family="Inter, system-ui, sans-serif", color="#111827"),
            align="right",
        )

    # Right annotations: inside grey track, right-aligned to its edge
    for _, row in stocks.iterrows():
        pnl = row["P&L (%)"]
        pct = row["% of Portfolio"]
        pnl_color = "#16a34a" if pnl >= 0 else "#dc2626"
        fig.add_annotation(
            xref="x", yref="y",
            x=100, y=row["Ticker"],
            text=(f"<span style='color:#374151'><b>{pct:.1f}%</b></span>"
                  f"<span style='color:#d1d5db'>  |  </span>"
                  f"<span style='color:{pnl_color}'>{pnl:+.1f}%</span>"),
            showarrow=False, xanchor="right", xshift=-12,
            font=dict(size=12, family="Inter, system-ui, sans-serif"),
            align="right",
        )

    # Header labels above the right annotations
    fig.add_annotation(
        xref="x", yref="paper",
        x=100, y=1.0,
        text=(f"<span style='color:#6b7280;font-size:11px'>Allocation</span>"
              f"<span style='color:#d1d5db'>  |  </span>"
              f"<span style='color:#6b7280;font-size:11px'>P&L</span>"),
        showarrow=False, xanchor="right", xshift=-12, yanchor="bottom",
        font=dict(size=11, family="Inter, system-ui, sans-serif"),
        align="right",
    )

    fig.update_layout(
        barmode="overlay",
        xaxis=dict(range=[0, 100], showticklabels=False,
                   showgrid=False, zeroline=False, fixedrange=True),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        height=max(320, len(stocks) * 64),
        margin=dict(l=160, r=150, t=30, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        bargap=0.40,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Bars = % of portfolio  \u00b7  White dot = cost-basis allocation")
