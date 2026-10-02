import streamlit as st
from auth import require_auth, logout

st.set_page_config(page_title="ABP Trade Sizer", page_icon="📈", layout="centered")

require_auth()

with st.sidebar:
    st.write(f"Signed in as: {st.session_state.auth_user.email}")
    if st.button("Log out"):
        logout()

pg = st.navigation([
    st.Page("pages/1_My_Portfolio.py",        title="My Portfolio",        icon="💼"),
    st.Page("pages/2_Position_Calculator.py", title="Position Calculator", icon="📈"),
    # pages/4_Ingest_Analysis.py: disabled. Analyses are written directly via the
    # Supabase MCP connector from the Claude analysis project; this page is the
    # designated fallback if that path is ever unavailable. Keep it out of nav so
    # there is only one active write path — re-enable, don't rebuild, if needed.
    st.Page("pages/3_Settings.py",            title="Settings",            icon="⚙️"),
])
pg.run()
