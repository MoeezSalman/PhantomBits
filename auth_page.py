"""
PhantomBits – split-screen login / register page.

Usage in app.py (after st.set_page_config and after LOGO_SVG is defined):

    from auth_page import render_auth_page

    if st.session_state.user is None:
        render_auth_page(LOGO_SVG)
        st.stop()
"""

from __future__ import annotations
import streamlit as st
from modules.auth_db import create_user, authenticate, generate_rsa_keypair

AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');

/* Page: no sidebar, centred card */
section[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] { display: none !important; }
.block-container { max-width: 1120px !important; padding-top: 2.2rem !important; }

/* The white outer card */
.st-key-auth_card {
    background: #ffffff;
    border: 1px solid rgba(15,60,50,.12);
    border-radius: 28px;
    padding: 10px;
    box-shadow: 0 30px 80px -34px rgba(15,60,50,.45);
}

/* Left dark brand panel */
.auth-left {
    min-height: 640px;
    border-radius: 20px;
    padding: 2rem 2.2rem;
    display: flex; flex-direction: column; justify-content: space-between;
    background:
        radial-gradient(520px 360px at 12% 18%, rgba(13,148,136,.28), transparent 65%),
        linear-gradient(165deg, #183530 0%, #0c1c1a 70%);
}
.auth-brand { display: flex; align-items: center; gap: .65rem; }
.auth-logo { width: 34px; height: 34px; border-radius: 9px; overflow: hidden; }
.auth-logo svg { display: block; width: 100%; height: 100%; }
.auth-brand-name { font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.1rem; color: #fff !important; }

.auth-headline {
    font-family: 'Sora', sans-serif; font-weight: 800;
    font-size: clamp(2rem, 3.4vw, 2.7rem); line-height: 1.12; letter-spacing: -0.02em;
    color: #fff !important; margin-bottom: 1.8rem;
}
.auth-headline em { font-style: normal; color: #2dd4bf !important; }

.auth-feature { display: flex; gap: .85rem; margin-bottom: 1.15rem; align-items: flex-start; }
.auth-feature-icon {
    flex: 0 0 34px; height: 34px; border-radius: 50%;
    display: grid; place-items: center;
    background: rgba(45,212,191,.12); border: 1px solid rgba(45,212,191,.25);
}
.auth-feature b { display: block; font-size: .95rem; color: #fff !important; font-weight: 600; }
.auth-feature span { display: block; font-size: .8rem; color: rgba(255,255,255,.6) !important; line-height: 1.45; }
.auth-foot { font-size: .72rem; color: rgba(255,255,255,.4) !important; }

/* Right form side */
.st-key-auth_form { padding: 3.2rem 2.6rem 1rem; }
.auth-title { font-family: 'Sora', sans-serif; font-weight: 800; font-size: 1.7rem; color: #10231f !important; margin-bottom: .2rem; }
.auth-sub { color: #5a6b66 !important; font-size: .92rem; margin-bottom: 1.4rem; }
.auth-switch { text-align: center; color: #5a6b66 !important; font-size: .88rem; margin-top: 1.2rem; }

.st-key-auth_form [data-testid="stForm"] { border: 0 !important; padding: 0 !important; }
.st-key-auth_form label p { font-size: .82rem !important; font-weight: 600 !important; color: #10231f !important; }
.st-key-auth_form input { background: #f6f8f8 !important; height: 2.9rem; }

/* Solid teal primary button (replaces the gradient + shimmer used elsewhere) */
.st-key-auth_card button[kind^="primary"] {
    background: #0f766e !important; box-shadow: none !important;
    border-radius: 10px !important; padding: .7rem 1rem !important;
}
.st-key-auth_card button[kind^="primary"]:hover { background: #0d6b64 !important; transform: none !important; }
.st-key-auth_card button[kind^="primary"]::after { display: none !important; }

/* "Create an account" / "Sign in" text-style link button */
.st-key-auth_card button[kind="tertiary"] {
    color: #0f766e !important; font-weight: 700; margin: 0 auto; display: block;
}
.st-key-auth_card button[kind="tertiary"] p { color: #0f766e !important; font-weight: 700; }

@media (max-width: 900px) {
    .auth-left { display: none; }
    .st-key-auth_form { padding: 1.5rem 1rem; }
}
</style>
"""

# Small inline icons (lucide paths) for the feature list
def _icon(path: str) -> str:
    return (
        "<svg width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='#2dd4bf' "
        "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>" + path + "</svg>"
    )

ICON_LOCK = _icon("<rect width='18' height='11' x='3' y='11' rx='2'/><path d='M7 11V7a5 5 0 0 1 10 0v4'/>")
ICON_IMAGE = _icon("<rect width='18' height='18' x='3' y='3' rx='2'/><circle cx='9' cy='9' r='2'/><path d='m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21'/>")
ICON_SCAN = _icon("<path d='M3 7V5a2 2 0 0 1 2-2h2'/><path d='M17 3h2a2 2 0 0 1 2 2v2'/><path d='M21 17v2a2 2 0 0 1-2 2h-2'/><path d='M7 21H5a2 2 0 0 1-2-2v-2'/><circle cx='12' cy='12' r='3'/>")


def _left_panel(logo_svg: str) -> str:
    return f"""
<div class="auth-left">
  <div class="auth-brand">
    <div class="auth-logo">{logo_svg}</div>
    <div class="auth-brand-name">PhantomBits</div>
  </div>

  <div>
    <div class="auth-headline">Hide messages<br>in <em>plain sight</em>.</div>
    <div class="auth-feature">
      <div class="auth-feature-icon">{ICON_LOCK}</div>
      <div><b>End-to-end encrypted</b><span>AES-256-GCM for the message, RSA for the password.</span></div>
    </div>
    <div class="auth-feature">
      <div class="auth-feature-icon">{ICON_IMAGE}</div>
      <div><b>Invisible embedding</b><span>Data is written into the least significant bits of a PNG.</span></div>
    </div>
    <div class="auth-feature">
      <div class="auth-feature-icon">{ICON_SCAN}</div>
      <div><b>Built-in steganalysis</b><span>Header checks and RS analysis flag tampered images.</span></div>
    </div>
  </div>

  <div class="auth-foot">Secure image steganography &amp; steganalysis</div>
</div>
"""


def _login_view() -> None:
    st.markdown('<div class="auth-title">Welcome back</div>'
                '<div class="auth-sub">Sign in to your account to continue</div>',
                unsafe_allow_html=True)

    with st.form("login_form", border=False):
        gmail = st.text_input("Email address", placeholder="name@gmail.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Sign in", type="primary", width="stretch")

    if submitted:
        user = authenticate(gmail.strip(), password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Invalid email or password.")

    st.markdown('<div class="auth-switch">Don’t have an account?</div>', unsafe_allow_html=True)
    if st.button(
        "Create an account",
        type="tertiary",
        key="go_register",
        width="stretch"
    ):
        st.session_state.auth_mode = "register"
        st.rerun()


def _register_view() -> None:
    st.markdown('<div class="auth-title">Create your account</div>'
                '<div class="auth-sub">We’ll generate your encryption keys on sign-up</div>',
                unsafe_allow_html=True)

    with st.form("register_form", border=False):
        gmail = st.text_input("Email address", placeholder="name@gmail.com")
        password = st.text_input("Password", type="password", placeholder="At least 6 characters")
        password2 = st.text_input("Confirm password", type="password", placeholder="Repeat password")
        submitted = st.form_submit_button("Create account & generate keys", type="primary", width="stretch")

    if submitted:
        gmail = gmail.strip()
        if not gmail or "@" not in gmail:
            st.error("Enter a valid email address.")
        elif password != password2:
            st.error("Passwords do not match.")
        elif len(password) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            try:
                public_pem, private_pem = generate_rsa_keypair()
                user = create_user(gmail, password, public_pem)
                # The Dashboard shows the private key + download button right after sign-up.
                st.session_state.private_key = private_pem
                st.session_state.user = user
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Registration failed: {e}")

    st.markdown('<div class="auth-switch">Already have an account?</div>', unsafe_allow_html=True)
    if st.button(
        "Sign in",
        type="tertiary",
        key="go_login",
        width="stretch"
    ):
        st.session_state.auth_mode = "login"
        st.rerun()


def render_auth_page(logo_svg: str) -> None:
    """Draw the split-screen auth page. Call st.stop() after it in app.py."""
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    st.session_state.setdefault("auth_mode", "login")

    with st.container(key="auth_card"):
        left, right = st.columns([1.05, 1], gap="small")
        with left:
            st.markdown(_left_panel(logo_svg), unsafe_allow_html=True)
        with right:
            with st.container(key="auth_form"):
                if st.session_state.auth_mode == "login":
                    _login_view()
                else:
                    _register_view()