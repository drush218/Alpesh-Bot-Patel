import base64, requests, pandas as pd, streamlit as st, time
from streamlit_js_eval import streamlit_js_eval
from charts import build_allocation_chart
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
        st.write("DEBUG position sample:", pos_resp.json()[0] if pos_resp.json() else "empty")
    except requests.HTTPError as e:
        st.error(f"API error {e.response.status_code}: {e.response.text}")
        st.stop()
    except Exception as e:
        st.error(f"Failed to load portfolio: {e}")
        st.stop()
    deposit_stats = get_deposit_stats()
    now_iso       = datetime.now(timezone.utc).isoformat()
    is_stale      = deposit_stats is None or (
        datetime.now(timezone.utc) - datetime.fromisoformat(deposit_stats["cached_at"]).replace(tzinfo=timezone.utc)
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

    # ── Allocation chart ──────────────────────────────────────────────────────
    st.subheader("Allocation")
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
    stocks = df.copy()
    stocks = (stocks.sort_values("% of Portfolio", ascending=True)
              if sort_by == "Size" else stocks.sort_values("Ticker", ascending=False))
    stocks["Cost (%)"] = (stocks["Cost ($)"] / display_total * 100).round(1)
    stocks["Company"]  = stocks["Ticker"].apply(lambda t: "Cash" if t == "CASH" else _company_name(t))

    screen_width = streamlit_js_eval(js_expressions="window.innerWidth", key="screen_width")
    is_mobile    = (screen_width or 1200) < 600

    fig = build_allocation_chart(stocks, is_mobile=is_mobile)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Bars = % of portfolio  \u00b7  White dot = cost-basis allocation")
