import pandas as pd
import streamlit as st

from markdown_to_json import parse_analysis
from analysis_db import confirm_ingest

st.title("📥 Ingest Analysis")
st.caption("Paste a stock-analysis markdown file, review the parsed tables, then confirm to save.")
st.divider()

md = st.text_area("Analysis markdown", height=300, placeholder="# Dutch Bros (BROS) — PE & Earnings Model\n...")

if st.button("Parse", type="primary", disabled=not md.strip()):
    st.session_state.ingest_payload = parse_analysis(md)
    st.session_state.pop("ingest_result", None)

payload = st.session_state.get("ingest_payload")

if payload:
    header = payload["analysis"]
    st.divider()
    st.subheader(f"{header.get('company') or '?'} ({header.get('ticker') or '?'})")

    if payload["warnings"]:
        with st.expander(f"⚠️ {len(payload['warnings'])} warning(s)", expanded=True):
            for w in payload["warnings"]:
                st.warning(w)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Price", f"{header.get('price_raw') or '—'}")
    m2.metric("Price date", header.get("price_date") or "—")
    m3.metric("Data as of", header.get("data_currency") or "—")
    m4.metric("Exchange", header.get("exchange") or "—")
    if header.get("calibration_note"):
        st.caption(header["calibration_note"])

    if payload.get("forecast"):
        st.markdown("**Forecast** (v2 model outputs)")
        fc = pd.DataFrame(payload["forecast"])
        st.dataframe(
            fc.pivot_table(index=["scenario"], columns="fiscal_year", values="eps", aggfunc="first"),
            use_container_width=True,
        )
        with st.expander("Full forecast rows"):
            st.dataframe(fc, hide_index=True, use_container_width=True)

    if payload.get("pe_basis"):
        st.markdown("**PE from earnings**")
        st.dataframe(pd.DataFrame(payload["pe_basis"]), hide_index=True, use_container_width=True)

    if payload.get("bridge"):
        st.markdown("**Net income bridge** (BAU, long format)")
        bridge_df = pd.DataFrame(payload["bridge"])
        wide = bridge_df.pivot_table(
            index=["line_label"], columns="fiscal_year", values="value", aggfunc="first"
        ).sort_index(axis=1)
        st.dataframe(wide, use_container_width=True)

    if payload.get("scenario_drivers"):
        st.markdown("**Scenario drivers** (LOW / BAU / HIGH)")
        st.dataframe(pd.DataFrame(payload["scenario_drivers"]), hide_index=True, use_container_width=True)

    if payload.get("scenario_outcomes"):
        st.markdown("**Scenario outcomes**")
        st.dataframe(pd.DataFrame(payload["scenario_outcomes"]), hide_index=True, use_container_width=True)

    if payload.get("forward_pe"):
        st.markdown("**Forward PE**")
        fpe_df = pd.DataFrame(payload["forward_pe"])
        fpe_wide = fpe_df.pivot_table(index="scenario", columns="fiscal_year", values="pe", aggfunc="first")
        st.dataframe(fpe_wide, use_container_width=True)

    if payload.get("sensitivities"):
        st.markdown("**External-factor sensitivities**")
        st.dataframe(pd.DataFrame(payload["sensitivities"]), hide_index=True, use_container_width=True)
        if payload.get("sensitivity_anchor"):
            st.caption(payload["sensitivity_anchor"])

    if payload.get("risks"):
        st.markdown("**Risks**")
        st.dataframe(pd.DataFrame(payload["risks"]), hide_index=True, use_container_width=True)

    if payload.get("peers"):
        st.markdown("**Peers**")
        with st.expander("Peer metrics"):
            st.json(payload["peers"])

    if payload["narrative"]:
        st.markdown("**Narrative**")
        for key, text in payload["narrative"].items():
            st.markdown(f"*{key.replace('_', ' ').title()}:* {text}")

    with st.expander("Raw markdown"):
        st.code(payload["raw_markdown"], language="markdown")

    st.divider()

    ticker_ok = bool(header.get("ticker"))
    if not ticker_ok:
        st.error("Cannot save: no ticker could be parsed from the H1 heading.")

    if st.button("Confirm & Save to Supabase", type="primary", disabled=not ticker_ok):
        try:
            analysis_id, already_existed = confirm_ingest(payload)
            st.session_state.ingest_result = (analysis_id, already_existed)
        except Exception as e:
            st.error(f"Failed to save: {e}")

result = st.session_state.get("ingest_result")
if result:
    analysis_id, already_existed = result
    if already_existed:
        st.info(f"This exact analysis (same ticker + content) was already ingested — id `{analysis_id}`. Not duplicated.")
    else:
        st.success(f"Saved as the current analysis — id `{analysis_id}`.")
