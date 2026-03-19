import plotly.graph_objects as go

BLUE  = "rgba(99,102,241,0.85)"
TRACK = "rgba(150,150,150,0.18)"


def build_allocation_chart(stocks, is_mobile=False):
    """Build the allocation bar chart.

    stocks must have columns: Ticker, Company, % of Portfolio,
    Cost (%), P&L (%), Value ($), Qty
    """
    # ── Layout config per breakpoint ──────────────────────────────────────────
    if is_mobile:
        l, r        = 80, 105
        font_size   = 10
        name_max    = 12
        show_value  = False
        dot_text    = False          # hide cost-basis % label — too cramped
        ann_xref    = "paper"
        ann_x       = 1.0
        ann_xanchor = "left"
        ann_xshift  = 6
        ann_align   = "left"
    else:
        l, r        = 120, 30
        font_size   = 12
        name_max    = 18
        show_value  = True
        dot_text    = True
        ann_xref    = "x"
        ann_x       = 100
        ann_xanchor = "right"
        ann_xshift  = -12
        ann_align   = "right"

    fig = go.Figure()

    # ── Background track pill ──────────────────────────────────────────────────
    fig.add_trace(go.Bar(
        x=[100] * len(stocks), y=stocks["Ticker"], orientation="h",
        marker=dict(color=TRACK, cornerradius=8),
        showlegend=False, hoverinfo="skip",
    ))

    # ── Allocation bar ─────────────────────────────────────────────────────────
    fig.add_trace(go.Bar(
        x=stocks["% of Portfolio"], y=stocks["Ticker"], orientation="h",
        marker=dict(color=BLUE, cornerradius=8),
        showlegend=False,
        hovertemplate="<b>%{y}</b><br>Allocation: %{x:.1f}%<extra></extra>",
    ))

    # ── Cost-basis line ────────────────────────────────────────────────────────
    equity = stocks[stocks["Ticker"] != "CASH"]
    pos    = equity[equity["P&L (%)"] >= 0]
    neg    = equity[equity["P&L (%)"] < 0]

    if not pos.empty:
        fig.add_trace(go.Scatter(
            x=pos["Cost (%)"], y=pos["Ticker"],
            mode="markers+text" if dot_text else "markers",
            marker=dict(size=26, symbol="line-ns", color="white",
                        line=dict(color="white", width=2.5)),
            text=[f"{v:.1f}% " for v in pos["Cost (%)"]] if dot_text else None,
            textposition="middle left" if dot_text else None,
            textfont=dict(size=font_size, color="white",
                          family="Inter, system-ui, sans-serif"),
            showlegend=False,
            hovertemplate="<b>%{y}</b><br>Cost basis: %{x:.1f}% of portfolio<extra></extra>",
        ))
    if not neg.empty:
        fig.add_trace(go.Scatter(
            x=neg["Cost (%)"], y=neg["Ticker"],
            mode="markers+text" if dot_text else "markers",
            marker=dict(size=26, symbol="line-ns", color="#111827",
                        line=dict(color="#111827", width=2.5)),
            text=[f" {v:.1f}%" for v in neg["Cost (%)"]] if dot_text else None,
            textposition="middle right" if dot_text else None,
            textfont=dict(size=font_size, color="#111827",
                          family="Inter, system-ui, sans-serif"),
            showlegend=False,
            hovertemplate="<b>%{y}</b><br>Cost basis: %{x:.1f}% of portfolio<extra></extra>",
        ))

    # ── Left annotations: company name + ticker · qty ──────────────────────────
    for _, row in stocks.iterrows():
        display_ticker = row["Ticker"].split("_")[0]
        name       = row["Company"]
        short_name = name if len(name) <= name_max else name[:name_max - 1] + "…"
        qty        = row["Qty"]
        qty_str    = f"{qty:,.4f}".rstrip("0").rstrip(".") if isinstance(qty, float) else ""
        ticker_line = display_ticker + (f" · {qty_str}" if qty_str else "")
        fig.add_annotation(
            xref="paper", yref="y",
            x=0, y=row["Ticker"],
            text=(f"<b>{short_name}</b>"
                  f"<br><span style='color:#9ca3af;font-size:{font_size - 2}px'>"
                  f"{ticker_line}</span>"),
            showarrow=False, xanchor="right", xshift=-8,
            font=dict(size=font_size, family="Inter, system-ui, sans-serif",
                      color="#111827"),
            align="right",
        )

    # ── Right annotations: value | allocation | P&L ────────────────────────────
    sep = "<span style='color:#d1d5db'>  |  </span>"

    for _, row in stocks.iterrows():
        pnl = row["P&L (%)"]
        pct = row["% of Portfolio"]
        val = row["Value (£)"]
        val_str = f"£{val:,.0f}"

        if row["Ticker"] == "CASH" or not isinstance(pnl, (int, float)):
            if show_value:
                label = (f"<span style='color:#6b7280'>{val_str}</span>"
                         f"{sep}"
                         f"<span style='color:#374151'><b>{pct:.1f}%</b></span>")
            else:
                label = f"<span style='color:#374151'><b>{pct:.1f}%</b></span>"
        else:
            pnl_color = "#16a34a" if pnl >= 0 else "#dc2626"
            if show_value:
                label = (f"<span style='color:#6b7280'>{val_str}</span>"
                         f"{sep}"
                         f"<span style='color:#374151'><b>{pct:.1f}%</b></span>"
                         f"{sep}"
                         f"<span style='color:{pnl_color}'>{pnl:+.1f}%</span>")
            else:
                label = (f"<span style='color:#374151'><b>{pct:.1f}%</b></span>"
                         f"{sep}"
                         f"<span style='color:{pnl_color}'>{pnl:+.1f}%</span>")

        fig.add_annotation(
            xref=ann_xref, yref="y",
            x=ann_x, y=row["Ticker"],
            text=label,
            showarrow=False, xanchor=ann_xanchor, xshift=ann_xshift,
            font=dict(size=font_size, family="Inter, system-ui, sans-serif"),
            align=ann_align,
        )

    # ── Header labels ──────────────────────────────────────────────────────────
    if is_mobile:
        header = (f"<span style='color:#9ca3af;font-size:{font_size}px'>Alloc</span>"
                  f"<span style='color:#d1d5db'>  |  </span>"
                  f"<span style='color:#9ca3af;font-size:{font_size}px'>P&L</span>")
        fig.add_annotation(
            xref="paper", yref="paper",
            x=1.0, y=1.0,
            text=header,
            showarrow=False, xanchor="left", xshift=6, yanchor="bottom",
            font=dict(size=font_size, family="Inter, system-ui, sans-serif"),
        )
    else:
        header = (f"<span style='color:#6b7280;font-size:11px'>Value</span>"
                  f"<span style='color:#d1d5db'>  |  </span>"
                  f"<span style='color:#6b7280;font-size:11px'>Allocation</span>"
                  f"<span style='color:#d1d5db'>  |  </span>"
                  f"<span style='color:#6b7280;font-size:11px'>P&L</span>")
        fig.add_annotation(
            xref="x", yref="paper",
            x=100, y=1.0,
            text=header,
            showarrow=False, xanchor="right", xshift=-12, yanchor="bottom",
            font=dict(size=11, family="Inter, system-ui, sans-serif"),
            align="right",
        )

    # ── Layout ─────────────────────────────────────────────────────────────────
    fig.update_layout(
        barmode="overlay",
        xaxis=dict(range=[0, 100], showticklabels=False,
                   showgrid=False, zeroline=False, fixedrange=True),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        height=max(320, len(stocks) * 64),
        margin=dict(l=l, r=r, t=30, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        bargap=0.40,
    )

    return fig
