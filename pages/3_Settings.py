import streamlit as st
from auth import get_t212_credentials, save_t212_credentials




st.title("⚙️ Settings")
st.subheader("Trading212 Credentials")
st.caption(
    "Your API key and secret are encrypted before being stored. "
    "They are never saved in plain text."
)

existing_key, existing_secret = get_t212_credentials()

with st.form("t212_form"):
    api_key    = st.text_input("Trading212 API Key",    value=existing_key    or "", type="password")
    api_secret = st.text_input("Trading212 API Secret", value=existing_secret or "", type="password")
    submitted  = st.form_submit_button("Save credentials")

if submitted:
    if not api_key:
        st.error("API key cannot be empty.")
    else:
        try:
            save_t212_credentials(api_key, api_secret or "")
            st.success("Credentials saved successfully.")
        except Exception as e:
            st.error(f"Failed to save credentials: {e}")
