"""
PhantomBits – main Streamlit application (redesigned UI)
Member 1: Dashboard + navigation + Encode page
"""

from __future__ import annotations
import io
import html
import urllib.parse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import streamlit as st
from streamlit_searchbox import st_searchbox

from auth_page import render_auth_page
from PIL import Image, ImageDraw, ImageChops

import numpy as np
import pandas as pd
from modules.steganalysis import rs_analysis, header_check
from modules.evaluation import evaluate_embedding, clean_baseline
from modules.visuals import (
    lsb_planes, plane_view, results_table,
    rs_chart, psnr_chart, fill_chart,
)
from modules.auth_db import (
    search_users_by_gmail,
    get_user_by_gmail,
    encrypt_with_public_key,
    decrypt_with_private_key,
)
import base64

# Our modules
from modules.crypto import encrypt_message, decrypt_message
from modules.steganography import encode_message, extract_message
from utils.image_utils import load_image, max_payload_bytes, calculate_psnr


# ---------------------------------------------------------------------------
# Gmail credentials for sending stego images
# ---------------------------------------------------------------------------
GMAIL_USER = st.secrets["GMAIL_USER"]
GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
def make_favicon() -> Image.Image:
    """Teal tile with a padlock whose body shows a picture (matches the sidebar logo)."""
    s = 128
    k = s / 44
    teal = (13, 148, 136, 255)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=30, fill=teal)

    # shackle
    w = round(3.4 * k)
    d.arc((14 * k, 7 * k, 30 * k, 23 * k), 180, 360, fill="white", width=w)
    d.line((14 * k, 15 * k, 14 * k, 21 * k), fill="white", width=w)
    d.line((30 * k, 15 * k, 30 * k, 21 * k), fill="white", width=w)

    # lock body
    body = (9 * k, 19 * k, 35 * k, 39 * k)
    d.rounded_rectangle(body, radius=4 * k, fill="white")

    # picture inset
    inset = (12 * k, 22.5 * k, 32 * k, 35.5 * k)
    d.rounded_rectangle(inset, radius=2 * k, fill=(205, 238, 234, 255))
    layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.ellipse(((17 - 2) * k, (27.5 - 2) * k, (17 + 2) * k, (27.5 + 2) * k), fill=teal)
    pts = [(12, 35.5), (12, 33), (17, 29.5), (21, 32.5), (25, 28.5), (32, 33.5), (32, 35.5)]
    ld.polygon([(x * k, y * k) for x, y in pts], fill=teal)
    ld.rectangle((28.2 * k, 23.8 * k, 30.8 * k, 26.4 * k), fill=(245, 158, 11, 255))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle(inset, radius=2 * k, fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    return Image.alpha_composite(img, layer)


st.set_page_config(
    page_title="PhantomBits",
    page_icon=make_favicon(),
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar logo
LOGO_SVG = """
<svg viewBox="0 0 44 44" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="pbg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0d9488"/><stop offset="1" stop-color="#0f766e"/>
    </linearGradient>
    <clipPath id="pbpic"><rect x="12" y="22.5" width="20" height="13" rx="2"/></clipPath>
  </defs>
  <rect width="44" height="44" fill="url(#pbg)"/>
  <path d="M14 21V15a8 8 0 0 1 16 0v6" fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round"/>
  <rect x="9" y="19" width="26" height="20" rx="4" fill="#fff"/>
  <rect x="12" y="22.5" width="20" height="13" rx="2" fill="#cdeeea"/>
  <g clip-path="url(#pbpic)" fill="#0d9488">
    <circle cx="17" cy="27.5" r="2"/>
    <path d="M12 35.5V33l5-3.5 4 3 4-4 7 5v2z"/>
  </g>
  <rect x="28.2" y="23.8" width="2.6" height="2.6" rx=".4" fill="#f59e0b"/>
</svg>
"""

# ---------------------------------------------------------------------------
# Authentication gate
# ---------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None          # will hold the MongoDB user doc
if "private_key" not in st.session_state:
    st.session_state.private_key = None   # only kept in memory / after download

if st.session_state.user is None:
    render_auth_page(LOGO_SVG)
    st.stop()

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

.stApp {
    background:
        radial-gradient(900px 500px at 85% -10%, rgba(13,148,136,.28), transparent 60%),
        radial-gradient(700px 480px at -5% 30%, rgba(245,158,11,.14), transparent 60%),
        radial-gradient(800px 500px at 50% 110%, rgba(15,118,110,.10), transparent 60%),
        var(--ink);
}
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.5rem; max-width: 1150px; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #eef4f2 100%);
    border-right: 1px solid var(--line);
}

.pb-brand { display:flex; align-items:center; gap:.7rem; margin-bottom:.2rem; }
.pb-logo {
    width:42px; height:42px; flex:0 0 42px; border-radius:12px; overflow:hidden;
    box-shadow: 0 3px 10px rgba(15,60,50,.18);
}
.pb-logo svg { display:block; width:100%; height:100%; }
.pb-brand-name { font-family:'Sora',sans-serif; font-weight:800; font-size:1.25rem; }
.pb-tag { color: var(--muted); font-size:.85rem; margin-bottom:1.2rem; }

.pb-hero {
    position:relative; overflow:hidden;
    border:1px solid var(--line); border-radius:28px;
    padding:3.2rem 3rem; margin-bottom:1.6rem;
    background: linear-gradient(135deg, rgba(13,148,136,.16), rgba(255,255,255,.6) 55%, rgba(15,118,110,.08));
    backdrop-filter: blur(14px);
}
.pb-hero::after {
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

.pb-flow { display:grid; grid-template-columns: repeat(4, 1fr); gap:1rem; margin-top:.6rem; }
.pb-step { border-left:2px solid var(--violet); padding:.2rem 0 .2rem 1rem; }
.pb-step b { font-family:'Sora',sans-serif; display:block; margin-bottom:.2rem; }
.pb-step span { color:var(--muted); font-size:.9rem; }
@media (max-width: 800px) { .pb-flow { grid-template-columns: 1fr 1fr; } .pb-hero { padding:2rem 1.4rem; } }

.pb-head h1 { font-size:2.2rem; font-weight:800; margin:0 0 .3rem; }
.pb-head p { color:var(--muted); margin:0 0 1.4rem; font-size:1.02rem; }
.pb-section { font-family:'Sora',sans-serif; font-weight:700; font-size:1.05rem; margin:.2rem 0 .8rem; }

.pb-stats { display:grid; grid-template-columns: repeat(3, 1fr); gap:1rem; margin:1.2rem 0; }
.pb-stat { border:1px solid var(--line); border-radius:16px; padding:1rem 1.2rem; background:rgba(255,255,255,.75); }
.pb-stat small { color:var(--muted); font-size:.82rem; }
.pb-stat div { font-family:'Sora',sans-serif; font-size:1.7rem; font-weight:700; margin-top:.15rem; }
.pb-stat .good { color: var(--teal); }
.pb-bar { height:6px; border-radius:99px; background:rgba(15,60,50,.10); margin-top:.6rem; overflow:hidden; }
.pb-bar > span { display:block; height:100%; background: linear-gradient(90deg, var(--violet), var(--pink)); }

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 20px; border-color: var(--line);
    background: rgba(255,255,255,.7);
}
.stTextArea textarea, .stTextInput input {
    background: rgba(255,255,255,.95) !important; color: var(--mist) !important;
    border: 1px solid var(--line) !important; border-radius: 12px !important;
}
/* Original decrypted message - expands naturally */
.pb-original-message {
    background: rgba(255,255,255,.95);
    color: var(--mist);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1.2rem;
    width: 100%;
    box-sizing: border-box;

    white-space: pre-wrap;
    overflow-wrap: anywhere;
    word-break: break-word;

    line-height: 1.7;
    font-family: 'DM Mono', monospace;
    font-size: .95rem;
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

@keyframes pb-rise { from { opacity:0; transform: translateY(18px); } to { opacity:1; transform:none; } }
@keyframes pb-shift { 0% { background-position: 0% 50%; } 100% { background-position: 200% 50%; } }
@keyframes pb-float { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(30px,-24px) scale(1.12); } }
@keyframes pb-drift { from { background-position: 0 0; } to { background-position: 44px 44px; } }
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

:root { color-scheme: light; }
.stApp, .stApp label, .stApp [data-testid="stWidgetLabel"] p,
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stImageCaption"],
.stApp div[role="radiogroup"] label p, .stApp .pb-chip { color: var(--mist) !important; }
.stApp .pb-card p, .stApp .pb-hero p, .stApp .pb-head p, .stApp .pb-step span,
.stApp .pb-stat small, .stApp .pb-tag,
.stApp [data-testid="stFileUploaderDropzone"] span,
.stApp [data-testid="stFileUploaderDropzone"] small { color: var(--muted) !important; }
.stApp .pb-card h3, .stApp .pb-step b, .stApp .pb-section, .stApp .pb-head h1,
.stApp .pb-brand-name, .stApp .pb-stat div { color: var(--mist) !important; }
.stApp .pb-stat .good { color: var(--teal) !important; }
.stApp .pb-hero h1 { color: transparent !important; -webkit-text-fill-color: transparent; }
.pb-card, .pb-stat, .pb-chip { box-shadow: 0 12px 30px -20px rgba(15,60,50,.45); }
.pb-card:hover { box-shadow: 0 20px 44px -18px rgba(13,148,136,.45); }
div[data-testid="stVerticalBlockBorderWrapper"] { box-shadow: 0 12px 30px -22px rgba(15,60,50,.4); }
section[data-testid="stSidebar"] { box-shadow: 8px 0 30px -24px rgba(15,60,50,.4); }
#MainMenu, footer { visibility: hidden; }

.stApp [data-testid="stTabs"] [role="tab"],
.stApp [data-testid="stTabs"] [role="tab"] *,
.stApp button[data-baseweb="tab"] p { color: #10231f !important; opacity: 1 !important; font-weight: 600; }
.stApp [data-testid="stTabs"] [role="tab"][aria-selected="true"],
.stApp [data-testid="stTabs"] [role="tab"][aria-selected="true"] * { color: #0d9488 !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar navigation style
# ---------------------------------------------------------------------------
NAV_CSS = """
<style>
section[data-testid="stSidebar"] .stButton { margin-bottom: .3rem; }
.stApp section[data-testid="stSidebar"] .stButton > button {
    width: 100%; justify-content: flex-start; gap: .7rem;
    padding: .65rem .9rem !important; border-radius: 12px;
    background: transparent !important; border: 1px solid transparent !important;
    box-shadow: none !important; transform: none !important;
    transition: background .18s ease, border-color .18s ease;
}
.stApp section[data-testid="stSidebar"] .stButton > button > div {
    justify-content: flex-start; width: 100%; gap: .7rem;
}
.stApp section[data-testid="stSidebar"] .stButton > button::after { display: none !important; }
.stApp section[data-testid="stSidebar"] .stButton > button p {
    color: #10231f !important; font-weight: 600; font-size: .95rem; margin: 0;
}
.stApp section[data-testid="stSidebar"] .stButton > button span[data-testid="stIconMaterial"] {
    color: #5a6b66 !important; font-size: 1.35rem;
}
.stApp section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(13,148,136,.10) !important; border-color: var(--line) !important;
}
.stApp section[data-testid="stSidebar"] .stButton > button:hover span[data-testid="stIconMaterial"] {
    color: #0d9488 !important;
}
.stApp section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(90deg, rgba(13,148,136,.28), rgba(245,158,11,.12)) !important;
    border-color: rgba(13,148,136,.5) !important;
}
.stApp section[data-testid="stSidebar"] .stButton > button[kind="primary"] p { color: #0f766e !important; }
.stApp section[data-testid="stSidebar"] .stButton > button[kind="primary"] span[data-testid="stIconMaterial"] {
    color: #0d9488 !important;
}

/* Logout button */
.stApp section[data-testid="stSidebar"] .st-key-logout_container div[data-testid="stButton"] > button[kind="primary"] {
    background: #0f766e !important;
    background-color: #0f766e !important;
    border: 1px solid #0f766e !important;
    color: #ffffff !important;
    box-shadow: none !important;
}

/* Logout text */
.stApp section[data-testid="stSidebar"] .st-key-logout_container div[data-testid="stButton"] > button p {
    color: #ffffff !important;
}

/* Logout icon */
.stApp section[data-testid="stSidebar"] .st-key-logout_container div[data-testid="stButton"] > button span[data-testid="stIconMaterial"] {
    color: #ffffff !important;
}

/* Hover */
.stApp section[data-testid="stSidebar"] .st-key-logout_container div[data-testid="stButton"] > button:hover {
    background: #0d6b64 !important;
    background-color: #0d6b64 !important;
    border-color: #0d6b64 !important;
}

</style>
"""
st.markdown(NAV_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Card icons
# ---------------------------------------------------------------------------
ICON_PATHS = {
    "lock": "<rect width='18' height='11' x='3' y='11' rx='2'/><path d='M7 11V7a5 5 0 0 1 10 0v4'/>",
    "unlock": "<rect width='18' height='11' x='3' y='11' rx='2'/><path d='M7 11V7a5 5 0 0 1 9.9-1'/>",
    "scan": (
        "<path d='M3 7V5a2 2 0 0 1 2-2h2'/><path d='M17 3h2a2 2 0 0 1 2 2v2'/>"
        "<path d='M21 17v2a2 2 0 0 1-2 2h-2'/><path d='M7 21H5a2 2 0 0 1-2-2v-2'/>"
        "<circle cx='12' cy='12' r='3'/><path d='m16 16-1.9-1.9'/>"
    ),
    "image": (
        "<rect width='18' height='18' x='3' y='3' rx='2'/><circle cx='9' cy='9' r='2'/>"
        "<path d='m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21'/>"
    ),
    "chart": "<path d='M3 3v16a2 2 0 0 0 2 2h16'/><path d='M18 17V9'/><path d='M13 17V5'/><path d='M8 17v-3'/>",
    "tool": (
        "<path d='M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94"
        "l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94z'/>"
    ),
}


def icon_svg(name: str, size: int = 24) -> str:
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' viewBox='0 0 24 24' "
        "fill='none' stroke='#0d9488' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
        f"{ICON_PATHS[name]}</svg>"
    )


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="pb-head"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )

def search_recipient_gmails(term: str) -> list[str]:
    """Called on every keystroke by the searchbox."""
    if not term:
        return []

    return [r["gmail"] for r in search_users_by_gmail(term)]


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
NAV_ITEMS = [
    ("Dashboard", ":material/dashboard:"),
    ("Encode Message", ":material/lock:"),
    ("Decode Message", ":material/lock_open:"),
    ("Manage Keys", ":material/key:"),
    ("Image Analysis", ":material/image_search:"),
    ("Performance Evaluation", ":material/bar_chart:"),
]

with st.sidebar:
    st.markdown(
        f'<div class="pb-brand"><div class="pb-logo">{LOGO_SVG}</div>'
        '<div class="pb-brand-name">PhantomBits</div></div>'
        '<div class="pb-tag">Secure image steganography &amp; steganalysis</div>',
        unsafe_allow_html=True,
    )

    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"

    for name, icon in NAV_ITEMS:
        is_active = st.session_state.page == name
        if st.button(
            name,
            icon=icon,
            key=f"nav_{name}",
            type="primary" if is_active else "secondary",
            width="stretch",
        ):
            st.session_state.page = name
            st.rerun()

    page = st.session_state.page
    st.markdown("<br>", unsafe_allow_html=True)

# Logged-in user info
    if st.session_state.user:
        st.markdown(
            f"<div style='font-size:0.85rem;color:#5a6b66;margin-bottom:8px;'>"
            f"Logged in as<br><b>{st.session_state.user['gmail']}</b></div>",
            unsafe_allow_html=True,
        )
    with st.container(key="logout_container"):
        if st.button(
            "Logout",
            icon=":material/logout:",
            type="primary",
            use_container_width=True,
            key="logout_button",
        ):
            st.session_state.user = None
            st.session_state.private_key = None
            st.session_state.pop("stego_result", None)
            st.rerun()


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
        ("lock", "Encode", "Encrypt a message with a password and hide it inside an image."),
        ("unlock", "Decode", "Recover and decrypt a hidden message from a stego image."),
        ("scan", "Analyse", "Check whether an image may contain hidden data."),
    ]
    for col, (icon, title, text) in zip((c1, c2, c3), cards):
        with col:
            st.markdown(
                f'<div class="pb-card"><div class="pb-icon">{icon_svg(icon)}</div>'
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
# 2. ENCODE MESSAGE
# ---------------------------------------------------------------------------
elif page == "Encode Message":
    page_header(
        "Encode message",
        "Encrypt a message with AES-GCM, hide it in a PNG, and encrypt the password with the recipient's public key.",
    )

    left, right = st.columns([1, 1], gap="large")

    with left:
        # 1. Cover image
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
                    uploaded.seek(0)
                except Exception:
                    uploaded.seek(0)

        # 2. Recipient search
        with st.container(border=True):
            st.markdown('<div class="pb-section">2 · Recipient</div>', unsafe_allow_html=True)

            selected_gmail = st_searchbox(
                search_recipient_gmails,
                label="",
                placeholder="Start typing a Gmail…",
                key="recipient_searchbox",
            )

            selected_user = get_user_by_gmail(selected_gmail) if selected_gmail else None

            if selected_user:
                st.text_area(
                    "Recipient Public Key",
                    value=selected_user["public_key"],
                    height=140,
                    disabled=True,
                )

        # 3. Secret & password
        with st.container(border=True):
            st.markdown('<div class="pb-section">3 · Secret & password</div>', unsafe_allow_html=True)
            message = st.text_area(
                "Secret message",
                height=130,
                placeholder="Type the confidential text you want to hide…",
            )
            password = st.text_input(
                "Password for AES encryption",
                type="password",
                help="This password is used for AES. It will be encrypted with the selected user's public key before sending.",
            )
            go = st.button("Encrypt & hide", type="primary", use_container_width=True)

    with right:
        if "stego_result" in st.session_state:
            result = st.session_state.stego_result

            st.success("Message encrypted and hidden.")

            st.markdown(
                f"""
<div class="pb-stats">
<div class="pb-stat"><small>PSNR</small><div class="good">{result['psnr']:.2f} dB</div></div>
<div class="pb-stat"><small>Payload</small><div>{result['payload']} B</div></div>
<div class="pb-stat"><small>Capacity used</small><div>{result['used']:.1f}%</div>
<div class="pb-bar"><span style="width:{min(result['used'], 100):.1f}%"></span></div></div>
</div>
""",
                unsafe_allow_html=True,
            )
            st.caption("PSNR above 40 dB is usually imperceptible to the eye.")

            col_a, col_b = st.columns(2)
            with col_a:
                st.image(result["cover"], caption="Original", use_container_width=True)
            with col_b:
                st.image(result["stego"], caption="Stego image", use_container_width=True)

            st.download_button(
                label="Download stego image",
                data=result["png_bytes"],
                file_name="phantom_stego.png",
                mime="image/png",
                use_container_width=True,
            )

            # ---------- Send via Email ----------
            st.markdown("---")
            st.markdown("### Send the stego image + encrypted password")

            if st.button("✉️ Email to recipient", use_container_width=True, type="primary"):
                st.session_state.show_email_dialog = True

            @st.dialog("Send via Email")
            def email_dialog():
                default_email = result.get("recipient_gmail", "")
                st.markdown(
                    "The stego image and the **encrypted password** will be sent to the selected user."
                )
                receiver_email = st.text_input(
                    "Recipient Gmail",
                    value=default_email,
                    placeholder="friend@gmail.com",
                )

                col_send, col_cancel = st.columns(2)
                with col_send:
                    if st.button("Send Image", type="primary", use_container_width=True):
                        if not receiver_email or "@" not in receiver_email:
                            st.error("Please enter a valid email address.")
                        else:
                            try:
                                msg = MIMEMultipart()
                                msg["From"] = GMAIL_USER
                                msg["To"] = receiver_email
                                msg["Subject"] = "PhantomBits – Stego Image + Encrypted Password"

                                body = (
                                    "Hello,\n\n"
                                    "I've encoded a secret message inside the attached image using PhantomBits.\n\n"
                                    "ENCRYPTED PASSWORD (copy this and paste it on the Decode page):\n"
                                    f"{result.get('encrypted_password_b64', '')}\n\n"
                                    "On the Decode page:\n"
                                    "1. Upload this image\n"
                                    "2. Upload / paste your private key\n"
                                    "3. Paste the encrypted password above\n"
                                    "4. Click Extract & decrypt\n\n"
                                    "— Sent from PhantomBits"
                                )
                                msg.attach(MIMEText(body, "plain"))

                                image_part = MIMEImage(result["png_bytes"], name="phantom_stego.png")
                                msg.attach(image_part)

                                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                                    server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                                    server.send_message(msg)

                                st.success(f"✅ Image + encrypted password sent to **{receiver_email}**!")
                                st.balloons()
                            except Exception as e:
                                st.error(f"Failed to send email: {e}")
                with col_cancel:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state.show_email_dialog = False
                        st.rerun()

            if st.session_state.get("show_email_dialog", False):
                email_dialog()

        elif not go:
            st.markdown(
                f'<div class="pb-card"><div class="pb-icon">{icon_svg("image")}</div>'
                "<h3>Your stego image will appear here</h3>"
                "<p>Select a recipient, add a PNG, a message and a password, then click "
                "<b>Encrypt &amp; hide</b>.</p></div>",
                unsafe_allow_html=True,
            )

    # ---------- Run encoding ----------
    if go:
        if not uploaded:
            st.error("Upload a PNG image first.")
        elif not selected_user:
            st.error("Please search and select a recipient first.")
        elif not message.strip():
            st.error("Enter a message to hide.")
        elif not password:
            st.error("Enter a password.")
        else:
            try:
                cover = load_image(uploaded)
                capacity = max_payload_bytes(cover)

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
                    with st.spinner("Embedding data into image…"):
                        stego = encode_message(cover, encrypted)

                    # Encrypt the AES password with recipient's public key
                    encrypted_pw = encrypt_with_public_key(password, selected_user["public_key"])
                    encrypted_pw_b64 = base64.b64encode(encrypted_pw).decode()

                    psnr = calculate_psnr(cover, stego)
                    used = 100 * len(encrypted) / capacity

                    buf = io.BytesIO()
                    stego.save(buf, format="PNG")
                    png_bytes = buf.getvalue()

                    st.session_state.stego_result = {
                        "cover": cover,
                        "stego": stego,
                        "psnr": psnr,
                        "payload": len(encrypted),
                        "used": used,
                        "png_bytes": png_bytes,
                        "encrypted_password_b64": encrypted_pw_b64,
                        "recipient_gmail": selected_user["gmail"],
                    }
                    st.rerun()

            except Exception as e:
                st.error(f"Encoding failed: {e}")
    


# ---------------------------------------------------------------------------
# 3. DECODE MESSAGE
# ---------------------------------------------------------------------------
elif page == "Decode Message":
    page_header(
        "Decode message",
        "Upload the stego image, your private key, and the encrypted password to recover the secret.",
    )

    left, right = st.columns([1, 1], gap="large")

    with left:
        # 1. Stego image
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

        # 2. Encrypted password (from the email)
        with st.container(border=True):
            st.markdown('<div class="pb-section">2 · Encrypted password</div>', unsafe_allow_html=True)
            encrypted_pw_b64 = st.text_input(
                "Encrypted password (base64)",
                placeholder="Paste the long base64 string that was sent with the image",
                help="This was encrypted with your public key. Only your private key can decrypt it.",
            )

        # 3. Private key
        with st.container(border=True):
            st.markdown('<div class="pb-section">3 · Your Private Key</div>', unsafe_allow_html=True)
            private_key_file = st.file_uploader(
                "Upload your private key",
                type=["txt"],
                help="The private key file you downloaded when you created your account.",
            )
            private_key_text = st.text_area(
                "Or paste private key here",
                height=150,
                placeholder="-----BEGIN PRIVATE KEY-----\n...",
            )

            # Prefer uploaded file
            if private_key_file is not None:
                private_key_pem = private_key_file.read().decode()
            else:
                private_key_pem = private_key_text.strip()

            go = st.button("Extract & decrypt", type="primary", use_container_width=True)

    with right:
        if not go:
            st.markdown(
                f'<div class="pb-card"><div class="pb-icon">{icon_svg("unlock")}</div>'
                "<h3>Decrypted message will appear here</h3>"
                "<p>Upload the stego PNG, paste the encrypted password from the email, "
                "and provide your private key, then click <b>Extract &amp; decrypt</b>.</p></div>",
                unsafe_allow_html=True,
            )
        else:
            if not uploaded:
                st.error("Upload a stego PNG first.")
            elif not encrypted_pw_b64:
                st.error("Paste the encrypted password that was sent in the email.")
            elif not private_key_pem:
                st.error("Upload or paste your private key.")
            else:
                try:
                    # Step 1: Decrypt the AES password using private key
                    with st.spinner("Decrypting password with private key…"):
                        encrypted_pw = base64.b64decode(encrypted_pw_b64)
                        real_password = decrypt_with_private_key(encrypted_pw, private_key_pem)

                    # Step 2: Extract the hidden payload from the image
                    stego = load_image(uploaded)
                    with st.spinner("Extracting hidden payload…"):
                        encrypted = extract_message(stego)

                    st.info(f"Extracted encrypted payload: **{len(encrypted)}** bytes")

                    # Step 3: Decrypt the message with the recovered AES password
                    with st.spinner("Decrypting message (AES-GCM)…"):
                        message = decrypt_message(encrypted, real_password)

                    st.success("Message successfully recovered and verified.")

                    st.markdown("### Original message")

                    st.markdown(
                        f'<div class="pb-original-message">{html.escape(message)}</div>',
                        unsafe_allow_html=True
                    )

                except ValueError as e:
                    # This catches both wrong private key and wrong AES password / corrupted data
                    st.error("Password is wrong (or private key is incorrect).")
                    st.caption(str(e))
                except Exception as e:
                    st.error(f"Extraction / decryption error: {e}")
    
# ---------------------------------------------------------------------------
# MY KEYS
# ---------------------------------------------------------------------------
elif page == "Manage Keys":
    page_header(
        "Manage keys",
        "Your RSA key pair. Share the public key, and keep the private key to yourself.",
    )

    user = st.session_state.user
    username = user["gmail"].split("@")[0]

    # Public key
    with st.container(border=True):
        st.markdown('<div class="pb-section">Public key</div>', unsafe_allow_html=True)
        st.caption("Stored on the server. Other users use it to encrypt passwords for you.")

        st.code(user["public_key"], language="text")

        st.download_button(
            "Download public key",
            data=user["public_key"],
            file_name=f"phantombits_public_key_{username}.txt",
            mime="text/plain",
            key="dl_public_key",
        )

    # Private key
    with st.container(border=True):
        st.markdown('<div class="pb-section">Private key</div>', unsafe_allow_html=True)
        st.caption("Not stored on the server. You need it on the Decode page to read messages sent to you.")

        if st.session_state.private_key:
            st.code(st.session_state.private_key, language="text")

            st.download_button(
                "Download private key",
                data=st.session_state.private_key,
                file_name=f"phantombits_private_key_{username}.txt",
                mime="text/plain",
                key="dl_private_key",
            )

            st.warning(
                "This key is only kept in this session. Download it now. "
                "If you lose it, messages sent to you can never be decrypted."
            )
        else:
            st.info(
                "Your private key isn't available in this session. "
                "Use the .txt file you downloaded when you created your account, "
                "and keep it somewhere safe."
            )

# ---------------------------------------------------------------------------
# 4. IMAGE ANALYSIS
# ---------------------------------------------------------------------------
elif page == "Image Analysis":
    page_header(
        "Image analysis",
        "Check an image for statistical signs of hidden data.",
    )

    with st.container(border=True):
        st.markdown('<div class="pb-section">1 · Image to analyse</div>', unsafe_allow_html=True)
        up_col, btn_col = st.columns([3, 1], gap="large", vertical_alignment="center")
        with up_col:
            analysis_file = st.file_uploader(
                "Upload a PNG image", type=["png"], key="analysis_upload",
                label_visibility="collapsed",
            )
        with btn_col:
            run = st.button("Analyse image", type="primary", width="stretch")

    if not run:
        st.markdown(
            f'<div class="pb-card"><div class="pb-icon">{icon_svg("scan")}</div>'
            "<h3>Your analysis will appear here</h3>"
            "<p>Upload a PNG and select <b>Analyse image</b>. "
            "Two checks look for traces of LSB hiding: a header check "
            "and RS analysis.</p></div>",
            unsafe_allow_html=True,
        )
    elif not analysis_file:
        st.error("Upload a PNG image first.")
    else:
        try:
            img = load_image(analysis_file)
            with st.spinner("Analysing image…"):
                head = header_check(img)
                rs = rs_analysis(img)

            rs_flag = rs["max_rate"] >= 0.30
            final_rate = rs["rates"][-1]

            if head["found"]:
                st.error(
                    f"PhantomBits hidden data found: a valid header announces "
                    f"a payload of {head['length']} bytes."
                )
            elif rs_flag:
                st.warning("Possible hidden data detected (RS analysis).")
            else:
                st.success("No strong sign of hidden data.")

            head_text = "Found" if head["found"] else "Not found"
            size_text = f"{head['length']:,} B" if head["found"] else "–"
            st.markdown(
                f"""
<div class="pb-stats" style="grid-template-columns: repeat(4, 1fr);">
<div class="pb-stat"><small>Header check</small><div>{head_text}</div></div>
<div class="pb-stat"><small>Hidden payload</small><div>{size_text}</div></div>
<div class="pb-stat"><small>RS peak (highest point)</small><div>{rs["max_rate"] * 100:.1f}%</div></div>
<div class="pb-stat"><small>RS at 100% scanned</small><div>{final_rate * 100:.2f}%</div></div>
</div>
""",
                unsafe_allow_html=True,
            )
            st.caption(
                "The header check finds PhantomBits messages of any length. RS needs longer "
                "messages (about 500 characters or more); its peak is the early, noisy part "
                "of the curve, and the value at 100% scanned is the settled estimate."
            )

            with st.container(border=True):
                st.markdown('<div class="pb-section">RS estimated embedding rate along the image</div>',
                            unsafe_allow_html=True)
                st.altair_chart(rs_chart(rs), width="stretch")
                st.caption("Read it from the right: the flat end is the reliable estimate. "
                           "The dashed amber line is the 0.30 detection threshold.")

            with st.container(border=True):
                st.markdown('<div class="pb-section">LSB planes</div>',
                            unsafe_allow_html=True)
                planes = lsb_planes(img)
                length = head["length"] if head["found"] else None
                for tab, (name, plane) in zip(st.tabs(list(planes)), planes.items()):
                    with tab:
                        st.image(
                            plane_view(plane, length),
                            caption=(f"LSB plane – {name}. Red circle = hidden data "
                                     f"({head['length']:,} bytes)." if length else
                                     f"LSB plane – {name}."),
                            width="stretch",
                        )

        except Exception as e:
            st.error(f"Analysis failed: {e}")


# ---------------------------------------------------------------------------
# 5. PERFORMANCE EVALUATION
# ---------------------------------------------------------------------------
elif page == "Performance Evaluation":
    page_header(
        "Performance evaluation",
        "Measure how invisible the hiding is and how well it can be detected.",
    )

    with st.container(border=True):
        st.markdown('<div class="pb-section">1 · Original cover image</div>', unsafe_allow_html=True)
        up_col, btn_col = st.columns([3, 1], gap="large", vertical_alignment="center")
        with up_col:
            eval_file = st.file_uploader(
                "Upload an original PNG (with nothing hidden)", type=["png"], key="eval_upload",
                label_visibility="collapsed",
            )
        with btn_col:
            run_eval = st.button("Run evaluation", type="primary", width="stretch")
        st.caption("Use an original image, not one that already holds a hidden message.")

    if not run_eval:
        st.markdown(
            f'<div class="pb-card"><div class="pb-icon">{icon_svg("chart")}</div>'
            "<h3>Your results will appear here</h3>"
            "<p>The app hides random data in your image at 5% up to 100% of its capacity, "
            "then measures image quality (PSNR, MSE, SSIM) and checks whether "
            "the header check and RS analysis can detect it.</p></div>",
            unsafe_allow_html=True,
        )
    elif not eval_file:
        st.error("Upload a PNG image first.")
    else:
        try:
            cover = load_image(eval_file)
            with st.spinner("Running evaluation (this can take a little while)…"):
                rows = evaluate_embedding(cover)
                base = clean_baseline(cover)

            st.success("Evaluation finished.")

            base_text = "Not detected" if not (base["rs_detected"] or base["header_detected"]) else "Detected"
            st.markdown(
                f"""
<div class="pb-stats">
<div class="pb-stat"><small>PSNR at 5% fill</small><div class="good">{rows[0]["psnr"]:.1f} dB</div></div>
<div class="pb-stat"><small>PSNR at 100% fill</small><div>{rows[-1]["psnr"]:.1f} dB</div></div>
<div class="pb-stat"><small>Original image</small><div>{base_text}</div></div>
</div>
""",
                unsafe_allow_html=True,
            )

            with st.container(border=True):
                st.markdown('<div class="pb-section">Results by fill level</div>', unsafe_allow_html=True)
                st.dataframe(results_table(rows), hide_index=True, width="stretch")

            c1, c2 = st.columns(2, gap="medium")
            with c1:
                with st.container(border=True):
                    st.markdown('<div class="pb-section">Image quality (PSNR) vs fill</div>',
                                unsafe_allow_html=True)
                    st.altair_chart(psnr_chart(rows), width="stretch")
            with c2:
                with st.container(border=True):
                    st.markdown('<div class="pb-section">RS peak rate vs fill</div>',
                                unsafe_allow_html=True)
                    st.altair_chart(fill_chart(rows, "rs_rate_pct"), width="stretch")

        except Exception as e:
            st.error(f"Evaluation failed: {e}")