"""
PhantomBits – main Streamlit application (redesigned UI)
Member 1: Dashboard + navigation + Encode page
"""

from __future__ import annotations
import io

import streamlit as st
from PIL import Image

# Our modules
from modules.crypto import encrypt_message, decrypt_message
from modules.steganography import encode_message, extract_message
from utils.image_utils import load_image, max_payload_bytes, calculate_psnr


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PhantomBits",
    page_icon="👻",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Theme (CSS)
# ---------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');

:root {
    --ink: #eef4f2;
    --ink-2: #ffffff;
    --line: rgba(15,60,50, 0.16);
    --violet: #0d9488;
    --pink: #f59e0b;
    --teal: #0f766e;
    --mist: #10231f;
    --muted: #5a6b66;
}

html, body, [class*="css"], .stApp {
    font-family: 'DM Sans', sans-serif;
    color: var(--mist);
}
h1, h2, h3, h4, .pb-display {
    font-family: 'Sora', sans-serif !important;
    letter-spacing: -0.02em;
}

/* Background with soft glows */
.stApp {
    background:
        radial-gradient(900px 500px at 85% -10%, rgba(13,148,136,.28), transparent 60%),
        radial-gradient(700px 480px at -5% 30%, rgba(245,158,11,.14), transparent 60%),
        radial-gradient(800px 500px at 50% 110%, rgba(15,118,110,.10), transparent 60%),
        var(--ink);
}
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.5rem; max-width: 1150px; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #eef4f2 100%);
    border-right: 1px solid var(--line);
}
section[data-testid="stSidebar"] .stRadio > label { display: none; }
section[data-testid="stSidebar"] div[role="radiogroup"] { gap: .35rem; }
section[data-testid="stSidebar"] div[role="radiogroup"] label {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 12px;
    padding: .6rem .85rem;
    transition: all .18s ease;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: rgba(13,148,136,.10);
    border-color: var(--line);
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(90deg, rgba(13,148,136,.28), rgba(245,158,11,.12));
    border-color: rgba(13,148,136,.5);
}
section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child { display: none; }

.pb-brand { display:flex; align-items:center; gap:.7rem; margin-bottom:.2rem; }
.pb-logo {
    width:42px; height:42px; border-radius:12px; display:grid; place-items:center;
    font-size:1.4rem;
    background: linear-gradient(135deg, var(--violet), var(--pink));
    box-shadow: 0 8px 28px rgba(13,148,136,.45);
}
.pb-brand-name { font-family:'Sora',sans-serif; font-weight:800; font-size:1.25rem; }
.pb-tag { color: var(--muted); font-size:.85rem; margin-bottom:1.2rem; }
.pb-team {
    border:1px solid var(--line); border-radius:14px; padding:.9rem 1rem;
    background: rgba(255,255,255,.7); font-size:.85rem; color:var(--muted); line-height:1.7;
}
.pb-team b { color: var(--mist); font-weight:600; }

/* Hero */
.pb-hero {
    position:relative; overflow:hidden;
    border:1px solid var(--line); border-radius:28px;
    padding:3.2rem 3rem; margin-bottom:1.6rem;
    background: linear-gradient(135deg, rgba(13,148,136,.16), rgba(255,255,255,.6) 55%, rgba(15,118,110,.08));
    backdrop-filter: blur(14px);
}
.pb-hero::after {  /* faint "hidden bits" grid */
    content:""; position:absolute; inset:0; pointer-events:none;
    background-image: radial-gradient(rgba(16,35,31,.18) 1px, transparent 1.4px);
    background-size: 22px 22px;
    -webkit-mask-image: linear-gradient(90deg, transparent 35%, #000 100%);
            mask-image: linear-gradient(90deg, transparent 35%, #000 100%);
}
.pb-hero h1 {
    font-size: clamp(2.4rem, 5vw, 4rem); font-weight:800; line-height:1.05; margin:0 0 1rem;
    background: linear-gradient(95deg, #0f3d37 10%, var(--violet) 55%, var(--pink) 95%);
    -webkit-background-clip:text; background-clip:text; color:transparent;
}
.pb-hero p { max-width: 560px; color: var(--muted); font-size:1.08rem; line-height:1.65; margin:0; position:relative; z-index:1; }
.pb-chips { margin-top:1.6rem; display:flex; gap:.6rem; flex-wrap:wrap; position:relative; z-index:1; }
.pb-chip {
    padding:.4rem .85rem; border-radius:999px; font-size:.82rem; font-weight:500;
    border:1px solid var(--line); background: rgba(255,255,255,.85); color: var(--mist);
}
.pb-chip i { color: var(--teal); font-style:normal; margin-right:.35rem; }

/* Cards */
.pb-card {
    height:100%;
    border:1px solid var(--line); border-radius:20px; padding:1.5rem;
    background: linear-gradient(180deg, rgba(255,255,255,.95), rgba(255,255,255,.7));
    transition: transform .2s ease, border-color .2s ease;
}
.pb-card:hover { transform: translateY(-3px); border-color: rgba(13,148,136,.55); }
.pb-icon {
    width:46px; height:46px; border-radius:14px; display:grid; place-items:center; font-size:1.4rem;
    margin-bottom:1rem; background: rgba(13,148,136,.16); border:1px solid rgba(13,148,136,.35);
}
.pb-card h3 { margin:0 0 .4rem; font-size:1.15rem; }
.pb-card p { margin:0; color:var(--muted); font-size:.95rem; line-height:1.55; }

/* Pipeline */
.pb-flow { display:grid; grid-template-columns: repeat(4, 1fr); gap:1rem; margin-top:.6rem; }
.pb-step { border-left:2px solid var(--violet); padding:.2rem 0 .2rem 1rem; }
.pb-step b { font-family:'Sora',sans-serif; display:block; margin-bottom:.2rem; }
.pb-step span { color:var(--muted); font-size:.9rem; }
@media (max-width: 800px) { .pb-flow { grid-template-columns: 1fr 1fr; } .pb-hero { padding:2rem 1.4rem; } }

/* Page headers */
.pb-head h1 { font-size:2.2rem; font-weight:800; margin:0 0 .3rem; }
.pb-head p { color:var(--muted); margin:0 0 1.4rem; font-size:1.02rem; }
.pb-section { font-family:'Sora',sans-serif; font-weight:700; font-size:1.05rem; margin:.2rem 0 .8rem; }

/* Stat tiles */
.pb-stats { display:grid; grid-template-columns: repeat(3, 1fr); gap:1rem; margin:1.2rem 0; }
.pb-stat { border:1px solid var(--line); border-radius:16px; padding:1rem 1.2rem; background:rgba(255,255,255,.75); }
.pb-stat small { color:var(--muted); font-size:.82rem; }
.pb-stat div { font-family:'Sora',sans-serif; font-size:1.7rem; font-weight:700; margin-top:.15rem; }
.pb-stat .good { color: var(--teal); }
.pb-bar { height:6px; border-radius:99px; background:rgba(15,60,50,.10); margin-top:.6rem; overflow:hidden; }
.pb-bar > span { display:block; height:100%; background: linear-gradient(90deg, var(--violet), var(--pink)); }

/* Native widgets */
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] .pb-section) {
    border-color: var(--line);
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 20px; border-color: var(--line);
    background: rgba(255,255,255,.7);
}
.stTextArea textarea, .stTextInput input {
    background: rgba(255,255,255,.95) !important; color: var(--mist) !important;
    border: 1px solid var(--line) !important; border-radius: 12px !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--violet) !important; box-shadow: 0 0 0 3px rgba(13,148,136,.25) !important;
}
[data-testid="stFileUploaderDropzone"] {
    background: rgba(13,148,136,.07); border: 1.5px dashed rgba(13,148,136,.5); border-radius: 16px;
}
.stButton > button[kind="primary"], .stDownloadButton > button {
    border: 0; border-radius: 14px; padding: .8rem 1.2rem; font-weight:600;
    background: linear-gradient(95deg, #0d9488, #0891b2); color:#fff;
    box-shadow: 0 10px 30px rgba(13,148,136,.35); transition: transform .15s ease, box-shadow .15s ease;
}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button:hover {
    transform: translateY(-1px); box-shadow: 0 14px 36px rgba(245,158,11,.35); color:#fff;
}
div[data-testid="stImage"] img { border-radius: 16px; border: 1px solid var(--line); }
div[data-testid="stAlert"] { border-radius: 14px; }

/* ---------------- Animations ---------------- */
@keyframes pb-rise { from { opacity:0; transform: translateY(18px); } to { opacity:1; transform:none; } }
@keyframes pb-shift { 0% { background-position: 0% 50%; } 100% { background-position: 200% 50%; } }
@keyframes pb-float { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(30px,-24px) scale(1.12); } }
@keyframes pb-drift { from { background-position: 0 0; } to { background-position: 44px 44px; } }
@keyframes pb-pulse { 0%,100% { box-shadow: 0 8px 28px rgba(13,148,136,.45); } 50% { box-shadow: 0 8px 44px rgba(245,158,11,.65); } }
@keyframes pb-sweep { from { transform: translateX(-120%) skewX(-20deg); } to { transform: translateX(260%) skewX(-20deg); } }
@keyframes pb-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes pb-pop { 0% { opacity:0; transform: scale(.94); } 100% { opacity:1; transform:none; } }
@keyframes pb-blink { 0%,100% { opacity:1; } 50% { opacity:.35; } }

.pb-hero { animation: pb-rise .8s cubic-bezier(.2,.7,.2,1) both; }
.pb-hero h1 { position:relative; z-index:1; background-size: 200% auto; animation: pb-shift 7s linear infinite; }
.pb-hero::after { animation: pb-drift 9s linear infinite; }
.pb-orb {
    position:absolute; border-radius:50%; filter: blur(60px); pointer-events:none; opacity:.30;
    animation: pb-float 11s ease-in-out infinite;
}
.pb-orb.a { width:260px; height:260px; right:-60px; top:-70px; background: var(--violet); }
.pb-orb.b { width:200px; height:200px; right:180px; bottom:-90px; background: var(--pink); animation-delay:-5s; }
.pb-chip { animation: pb-pop .5s ease both; }
.pb-chip:nth-child(1) { animation-delay:.5s; } .pb-chip:nth-child(2) { animation-delay:.62s; }
.pb-chip:nth-child(3) { animation-delay:.74s; } .pb-chip:nth-child(4) { animation-delay:.86s; }
.pb-chip i { animation: pb-blink 2.4s ease-in-out infinite; }

.pb-logo { animation: pb-pulse 3.2s ease-in-out infinite; }
.pb-card { animation: pb-rise .7s cubic-bezier(.2,.7,.2,1) both; }
[data-testid="column"]:nth-child(1) .pb-card { animation-delay:.15s; }
[data-testid="column"]:nth-child(2) .pb-card { animation-delay:.30s; }
[data-testid="column"]:nth-child(3) .pb-card { animation-delay:.45s; }
.pb-card:hover { box-shadow: 0 18px 44px -16px rgba(13,148,136,.55); }
.pb-card:hover .pb-icon { transform: rotate(-6deg) scale(1.08); }
.pb-icon { transition: transform .25s ease; }

.pb-step { animation: pb-rise .6s ease both; transition: border-color .2s ease, padding-left .2s ease; }
.pb-step:nth-child(1) { animation-delay:.2s; } .pb-step:nth-child(2) { animation-delay:.35s; }
.pb-step:nth-child(3) { animation-delay:.5s; } .pb-step:nth-child(4) { animation-delay:.65s; }
.pb-step:hover { border-color: var(--pink); padding-left: 1.3rem; }

.pb-head { animation: pb-rise .6s ease both; }
.pb-stat { animation: pb-pop .5s ease both; }
.pb-stat:nth-child(2) { animation-delay:.12s; } .pb-stat:nth-child(3) { animation-delay:.24s; }
.pb-bar > span { transform-origin:left; animation: pb-grow 1.1s cubic-bezier(.2,.7,.2,1) .4s both; }
div[data-testid="stImage"] img { animation: pb-pop .6s ease both; transition: transform .3s ease; }
div[data-testid="stImage"] img:hover { transform: scale(1.02); }

.stButton > button[kind="primary"], .stDownloadButton > button { position:relative; overflow:hidden; }
.stButton > button[kind="primary"]::after, .stDownloadButton > button::after {
    content:""; position:absolute; top:0; left:0; width:35%; height:100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.35), transparent);
    transform: translateX(-120%) skewX(-20deg); animation: pb-sweep 3.6s ease-in-out infinite;
}
.stButton > button[kind="primary"]:active { transform: scale(.98); }
div[data-testid="stAlert"] { animation: pb-pop .4s ease both; }

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
}
.stButton > button[kind="primary"] p, .stDownloadButton > button p { color:#fff !important; font-weight:700; }

/* ---------------- Light theme overrides ---------------- */
:root { color-scheme: light; }
.stApp, .stApp label, .stApp [data-testid="stWidgetLabel"] p,
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stImageCaption"],
.stApp div[role="radiogroup"] label p, .stApp .pb-chip { color: var(--mist) !important; }
.stApp .pb-card p, .stApp .pb-hero p, .stApp .pb-head p, .stApp .pb-step span,
.stApp .pb-stat small, .stApp .pb-tag, .stApp .pb-team,
.stApp [data-testid="stFileUploaderDropzone"] span,
.stApp [data-testid="stFileUploaderDropzone"] small { color: var(--muted) !important; }
.stApp .pb-card h3, .stApp .pb-step b, .stApp .pb-section, .stApp .pb-head h1,
.stApp .pb-brand-name, .stApp .pb-stat div, .stApp .pb-team b { color: var(--mist) !important; }
.stApp .pb-stat .good { color: var(--teal) !important; }
.stApp .pb-hero h1 { color: transparent !important; -webkit-text-fill-color: transparent; }
.pb-card, .pb-stat, .pb-chip { box-shadow: 0 12px 30px -20px rgba(15,60,50,.45); }
.pb-card:hover { box-shadow: 0 20px 44px -18px rgba(13,148,136,.45); }
div[data-testid="stVerticalBlockBorderWrapper"] { box-shadow: 0 12px 30px -22px rgba(15,60,50,.4); }
section[data-testid="stSidebar"] { box-shadow: 8px 0 30px -24px rgba(15,60,50,.4); }
#MainMenu, footer { visibility: hidden; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="pb-head"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def placeholder_page(title: str, subtitle: str, owner: str, extra: str = "") -> None:
    page_header(title, subtitle)
    st.markdown(
        f'<div class="pb-card"><div class="pb-icon">🚧</div>'
        f"<h3>Coming soon</h3><p>This page will be implemented by {owner}. {extra}</p></div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="pb-brand"><div class="pb-logo">👻</div>'
        '<div class="pb-brand-name">PhantomBits</div></div>'
        '<div class="pb-tag">Secure image steganography &amp; steganalysis</div>',
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigate",
        options=[
            "🏠  Dashboard",
            "🔒  Encode Message",
            "🔓  Decode Message",        # Member 2
            "🔍  Image Analysis",        # Member 3
            "📊  Performance Evaluation",  # Member 3
        ],
        label_visibility="collapsed",
    )
    page = page.split("  ", 1)[1]  # strip the emoji prefix

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="pb-team"><b>Group members</b><br>'
        "Moeez Salman · 23L-3000<br>"
        "Eishah Iqbal Malik · 23L-2587<br>"
        "Muhammad Mustafa · 23L-3026</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 1. DASHBOARD
# ---------------------------------------------------------------------------
if page == "Dashboard":
    st.markdown(
        """
<div class="pb-hero">
<span class="pb-orb a"></span><span class="pb-orb b"></span>
<h1>Hide messages in plain sight.</h1>
<p>PhantomBits encrypts your secret, tucks it into the pixels of a PNG, and
checks images for signs that someone else did the same.</p>
<div class="pb-chips">
<span class="pb-chip"><i>●</i>AES-256-GCM</span>
<span class="pb-chip"><i>●</i>LSB embedding</span>
<span class="pb-chip"><i>●</i>PSNR quality check</span>
<span class="pb-chip"><i>●</i>Statistical steganalysis</span>
</div>
</div>
""",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3, gap="medium")
    cards = [
        ("🔒", "Encode", "Encrypt a message with a password and hide it inside an image."),
        ("🔓", "Decode", "Recover and decrypt a hidden message from a stego image."),
        ("🔍", "Analyse", "Check whether an image may contain hidden data."),
    ]
    for col, (icon, title, text) in zip((c1, c2, c3), cards):
        with col:
            st.markdown(
                f'<div class="pb-card"><div class="pb-icon">{icon}</div>'
                f"<h3>{title}</h3><p>{text}</p></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="pb-section">How it works</div>', unsafe_allow_html=True)
    st.markdown(
        """
<div class="pb-flow">
<div class="pb-step"><b>1. Encrypt</b><span>Your message is locked with AES-256-GCM.</span></div>
<div class="pb-step"><b>2. Hide</b><span>The ciphertext is written into the image's least significant bits.</span></div>
<div class="pb-step"><b>3. Extract</b><span>Enter the same password to pull the data back out.</span></div>
<div class="pb-step"><b>4. Analyse</b><span>Statistical tests flag images that look tampered with.</span></div>
</div>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 2. ENCODE MESSAGE  (Member 1)
# ---------------------------------------------------------------------------
elif page == "Encode Message":
    page_header(
        "Encode message",
        "Encrypt a message with AES-GCM and hide it inside a PNG image using LSB steganography.",
    )

    left, right = st.columns([1, 1], gap="large")

    with left:
        with st.container(border=True):
            st.markdown('<div class="pb-section">1 · Cover image</div>', unsafe_allow_html=True)
            uploaded = st.file_uploader(
                "Upload a PNG image (RGB)",
                type=["png"],
                help="Only lossless PNG is supported.",
                label_visibility="collapsed",
            )
            if uploaded:
                try:
                    preview = Image.open(uploaded)
                    st.image(preview, caption=f"{preview.width} × {preview.height} px", use_container_width=True)
                    uploaded.seek(0)  # reset so load_image can read it again
                except Exception:
                    uploaded.seek(0)

        with st.container(border=True):
            st.markdown('<div class="pb-section">2 · Secret & password</div>', unsafe_allow_html=True)
            message = st.text_area(
                "Secret message",
                height=130,
                placeholder="Type the confidential text you want to hide…",
            )
            password = st.text_input(
                "Password",
                type="password",
                help="This password is used to derive the AES key. Never share it.",
            )
            go = st.button("Encrypt & hide", type="primary", use_container_width=True)

    with right:
        if not go:
            st.markdown(
                '<div class="pb-card"><div class="pb-icon">👻</div>'
                "<h3>Your stego image will appear here</h3>"
                "<p>Add a PNG, a message and a password, then select <b>Encrypt &amp; hide</b>. "
                "You'll see a side-by-side comparison, the quality score and a download button.</p></div>",
                unsafe_allow_html=True,
            )
        else:
            if not uploaded:
                st.error("Upload a PNG image first.")
            elif not message.strip():
                st.error("Enter a message to hide.")
            elif not password:
                st.error("Enter a password.")
            else:
                try:
                    # 1. Load image
                    cover = load_image(uploaded)
                    capacity = max_payload_bytes(cover)

                    # 2. Encrypt
                    with st.spinner("Encrypting message…"):
                        encrypted = encrypt_message(message, password)

                    if len(encrypted) > capacity:
                        st.error(
                            f"Encrypted payload is too large for this image.\n\n"
                            f"Payload size: **{len(encrypted)}** bytes\n\n"
                            f"Image capacity: **{capacity}** bytes\n\n"
                            "Use a larger image or a shorter message."
                        )
                    else:
                        # 3. Embed
                        with st.spinner("Embedding data into image…"):
                            stego = encode_message(cover, encrypted)

                        st.success("Message encrypted and hidden.")

                        # 4. Results
                        psnr = calculate_psnr(cover, stego)
                        used = 100 * len(encrypted) / capacity
                        st.markdown(
                            f"""
<div class="pb-stats">
<div class="pb-stat"><small>PSNR</small><div class="good">{psnr:.2f} dB</div></div>
<div class="pb-stat"><small>Payload</small><div>{len(encrypted)} B</div></div>
<div class="pb-stat"><small>Capacity used</small><div>{used:.1f}%</div>
<div class="pb-bar"><span style="width:{min(used, 100):.1f}%"></span></div></div>
</div>
""",
                            unsafe_allow_html=True,
                        )
                        st.caption("PSNR above 40 dB is usually imperceptible to the eye.")

                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.image(cover, caption="Original", use_container_width=True)
                        with col_b:
                            st.image(stego, caption="Stego image", use_container_width=True)

                        buf = io.BytesIO()
                        stego.save(buf, format="PNG")
                        st.download_button(
                            label="Download stego image",
                            data=buf.getvalue(),
                            file_name="phantom_stego.png",
                            mime="image/png",
                            use_container_width=True,
                        )

                except Exception as e:
                    st.error(f"Encoding failed: {e}")


elif page == "Decode Message":
    page_header(
        "Decode message",
        "Extract the hidden payload from a stego PNG and decrypt it with AES-GCM.",
    )

    left, right = st.columns([1, 1], gap="large")

    with left:
        with st.container(border=True):
            st.markdown('<div class="pb-section">1 · Stego image</div>', unsafe_allow_html=True)
            uploaded = st.file_uploader(
                "Upload the stego PNG",
                type=["png"],
                help="The image that was produced by the Encode page.",
                label_visibility="collapsed",
            )
            if uploaded:
                try:
                    preview = Image.open(uploaded)
                    st.image(preview, caption=f"{preview.width} × {preview.height} px", use_container_width=True)
                    uploaded.seek(0)
                except Exception:
                    uploaded.seek(0)

        with st.container(border=True):
            st.markdown('<div class="pb-section">2 · Password</div>', unsafe_allow_html=True)
            password = st.text_input(
                "Password used during encoding",
                type="password",
                help="Must be exactly the same password that was used to encrypt the message.",
            )
            go = st.button("Extract & decrypt", type="primary", use_container_width=True)

    with right:
        if not go:
            st.markdown(
                '<div class="pb-card"><div class="pb-icon">🔓</div>'
                "<h3>Decrypted message will appear here</h3>"
                "<p>Upload the stego PNG, enter the correct password, then click "
                "<b>Extract &amp; decrypt</b>.</p></div>",
                unsafe_allow_html=True,
            )
        else:
            if not uploaded:
                st.error("Upload a stego PNG first.")
            elif not password:
                st.error("Enter the password.")
            else:
                try:
                    # 1. Load image
                    stego = load_image(uploaded)

                    # 2. Extract encrypted payload
                    with st.spinner("Extracting hidden payload…"):
                        encrypted = extract_message(stego)

                    st.info(f"Extracted encrypted payload: **{len(encrypted)}** bytes")

                    # 3. Decrypt + integrity check
                    with st.spinner("Decrypting (AES-GCM)…"):
                        message = decrypt_message(encrypted, password)

                    # 4. Success
                    st.success("Message successfully recovered and verified.")
                    st.markdown("### Original message")
                    st.code(message, language=None)

                except ValueError as e:
                    st.error(f"{e}")
                    st.caption("Most common causes: wrong password or the image was modified.")
                except Exception as e:
                    st.error(f"Extraction / decryption error: {e}")

elif page == "Image Analysis":
    placeholder_page(
        "Image analysis",
        "Check an image for statistical signs of hidden data.",
        "Member 3 (Steganalysis)",
    )

elif page == "Performance Evaluation":
    placeholder_page(
        "Performance evaluation",
        "Measure embedding quality and detection accuracy.",
        "Member 3 (Evaluation)",
    )