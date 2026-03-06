import streamlit as st
from supabase import create_client, Client
from cryptography.fernet import Fernet


# ── Internal helpers ──────────────────────────────────────────────────────────

def _fernet() -> Fernet:
    key = st.secrets["encryption"]["fernet_key"]
    return Fernet(key.encode() if isinstance(key, str) else key)


def init_supabase() -> Client:
    if "supabase_client" not in st.session_state:
        st.session_state.supabase_client = create_client(
            st.secrets["supabase"]["url"],
            st.secrets["supabase"]["key"],
        )
    return st.session_state.supabase_client


# ── Auth UI ───────────────────────────────────────────────────────────────────

def show_auth_ui() -> None:
    supabase = init_supabase()

    st.title("Sign in")
    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        email    = st.text_input("Email",    key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log in", key="login_btn"):
            try:
                resp = supabase.auth.sign_in_with_password(
                    {"email": email, "password": password}
                )
                st.session_state.auth_user    = resp.user
                st.session_state.auth_session = resp.session
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab_register:
        email    = st.text_input("Email",            key="reg_email")
        password = st.text_input("Password",         type="password", key="reg_password")
        confirm  = st.text_input("Confirm password", type="password", key="reg_confirm")
        if st.button("Create account", key="reg_btn"):
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    resp = supabase.auth.sign_up(
                        {"email": email, "password": password}
                    )
                    if resp.session:
                        st.session_state.auth_user    = resp.user
                        st.session_state.auth_session = resp.session
                        st.rerun()
                    else:
                        st.info("Account created. Check your email to confirm, then log in.")
                except Exception as e:
                    st.error(f"Registration failed: {e}")


# ── Auth gate ─────────────────────────────────────────────────────────────────

def require_auth() -> None:
    if "auth_user" not in st.session_state or st.session_state.auth_user is None:
        show_auth_ui()
        st.stop()


# ── Logout ────────────────────────────────────────────────────────────────────

def logout() -> None:
    supabase = init_supabase()
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    for key in ["auth_user", "auth_session", "supabase_client",
                "portfolio_cash", "portfolio_positions", "portfolio_env",
                "portfolio_value", "live_price"]:
        st.session_state.pop(key, None)
    st.rerun()


# ── Credential helpers ────────────────────────────────────────────────────────

def _user_id() -> str:
    return st.session_state.auth_user.id


def get_t212_credentials() -> tuple:
    """Return decrypted (api_key, api_secret) or (None, None) if not saved."""
    supabase = init_supabase()
    f        = _fernet()

    try:
        row  = (
            supabase.table("user_settings")
            .select("t212_api_key, t212_api_secret")
            .eq("id", _user_id())
            .single()
            .execute()
        )
        data = row.data
        if not data or not data.get("t212_api_key"):
            return None, None

        api_key    = f.decrypt(data["t212_api_key"].encode()).decode()
        api_secret = f.decrypt(data["t212_api_secret"].encode()).decode() if data.get("t212_api_secret") else None
        return api_key, api_secret

    except Exception:
        return None, None


def save_t212_credentials(api_key: str, api_secret: str) -> None:
    """Encrypt and upsert Trading212 credentials for the logged-in user."""
    supabase = init_supabase()
    f        = _fernet()

    encrypted_key    = f.encrypt(api_key.encode()).decode()
    encrypted_secret = f.encrypt(api_secret.encode()).decode()

    supabase.table("user_settings").upsert({
        "id":              _user_id(),
        "t212_api_key":    encrypted_key,
        "t212_api_secret": encrypted_secret,
    }).execute()
