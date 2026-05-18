# app.py — ColoCare MD 
# Landing + About + Guide + App clinique + Vision Lab YOLO
 
import streamlit as st
import json
import os
import time
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
 
from modules.pipeline import run_pipeline
from modules.rules_engine import get_esmo_guideline
from modules.image_analyzer import get_image_recommendation
from modules.prognosis_engine import analyze_postop
from modules.gemma_client import ask_gemma_with_context, ask_gemma

from modules.database import (
    save_patient, get_all_patients, get_patient_by_id,
    update_patient_status, update_validation_medecin,
    update_patient_notes, delete_patient_db, add_log,
    save_conversation_db, get_all_conversations_db, delete_conversation_db
)
 
from modules.conversation_memory import (
    create_conversation, add_message, get_context_summary
)
 
# ══════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════
st.set_page_config(
    page_title="ColoCare MD",
    page_icon="assets/logos/logo.png" if os.path.exists("assets/logos/logo.png") else "🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════
# CSS GLOBAL
# ══════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
 
:root {
    --primary: #2F80ED;
    --primary-light: #D5E6FB;
    --dark: #181D27;
    --secondary: #525252;
    --bg: #FAFAFA;
    --white: #FFFFFF;
    --border: #E8EDF2;
    --shadow: 0 2px 12px rgba(47,128,237,0.08);
    --shadow-md: 0 8px 32px rgba(47,128,237,0.12);
    --radius: 16px;
    --radius-sm: 8px;
}
 
* { font-family: 'Poppins', sans-serif; box-sizing: border-box; }
 
html, body, .stApp { background: var(--bg) !important; }
 
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none !important; }
 
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}
 
/* ── SIDEBAR APP ── */
[data-testid="stSidebar"] {
    background: var(--white) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: var(--shadow) !important;
}
 
/* ── METRICS ── */
[data-testid="stMetric"] {
    background: var(--white) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    padding: 16px !important;
    box-shadow: var(--shadow) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: var(--secondary) !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: var(--primary) !important;
}
 
/* ── BUTTONS ── */
.stButton > button {
    border-radius: var(--radius-sm) !important;
    font-family: 'Poppins', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    padding: 8px 18px !important;
    border: 1px solid var(--border) !important;
    background: var(--white) !important;
    color: var(--dark) !important;
    transition: all 0.15s ease !important;
    box-shadow: var(--shadow) !important;
}
.stButton > button:hover {
    background: var(--primary-light) !important;
    border-color: var(--primary) !important;
    color: var(--primary) !important;
}
[data-testid="baseButton-primary"] {
    background: var(--primary) !important;
    color: white !important;
    border-color: var(--primary) !important;
}
[data-testid="baseButton-primary"]:hover {
    background: #1a6fd4 !important;
    color: white !important;
}
 
/* ── INPUTS ── */
.stTextInput > div > div,
.stSelectbox > div > div,
.stTextArea > div > div {
    border-radius: var(--radius-sm) !important;
    border-color: var(--border) !important;
    background: var(--white) !important;
    font-family: 'Poppins', sans-serif !important;
}
 
/* ── ALERTS ── */
[data-testid="stAlert"] {
    border-radius: var(--radius-sm) !important;
    font-size: 0.875rem !important;
}
 
/* ── EXPANDER ── */
[data-testid="stExpander"] {
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border) !important;
    background: var(--white) !important;
}
 
/* ── DATAFRAME ── */
[data-testid="stDataFrame"] {
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border) !important;
    overflow: hidden !important;
}
 
/* ── CHAT ── */
.stChatMessage {
    background: var(--white) !important;
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border) !important;
    margin: 8px 0 !important;
}
 
/* ── PROGRESS ── */
.stProgress > div > div { background-color: var(--primary) !important; }
 
/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
 
hr { border-color: var(--border) !important; }
 
/* ── LANDING PAGE SPECIFIC ── */
.topbar {
    background: var(--primary);
    color: white;
    text-align: center;
    padding: 10px;
    font-size: 0.85rem;
    font-weight: 500;
    letter-spacing: 0.02em;
}
 
.navbar {
    background: var(--white);
    padding: 14px 48px;
    display: flex;
    align-items: center;
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 100;
}
 
.hero-section {
    position: relative;
    width: 100%;
    height: 640px;
    overflow: hidden;
    background: linear-gradient(135deg, #D5E6FB 0%, #EEF5FD 50%, #D5E6FB 100%);
}
 
.hero-img {
    width: 100%;
    height: 640px;
    object-fit: cover;
    display: block;
}
 
.hero-overlay {
    position: absolute;
    top: 0; left: 0;
    width: 50%;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 64px 48px;
}
 
.hero-title {
    font-size: 48px;
    font-weight: 700;
    color: var(--dark);
    line-height: 1.2;
    margin-bottom: 20px;
}
 
.hero-desc {
    font-size: 18px;
    color: var(--secondary);
    line-height: 1.7;
    margin-bottom: 36px;
    max-width: 480px;
}
 
.btn-primary-html {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--primary);
    color: white !important;
    padding: 14px 28px;
    border-radius: var(--radius-sm);
    font-size: 16px;
    font-weight: 600;
    text-decoration: none;
    cursor: pointer;
    border: none;
    transition: background 0.15s ease;
}
 
.btn-primary-html:hover { background: #1a6fd4; }
 
.section-content {
    max-width: 1100px;
    margin: 0 auto;
    padding: 64px 48px;
}
 
.section-title {
    font-size: 36px;
    font-weight: 700;
    color: var(--dark);
    margin-bottom: 16px;
}
 
.section-text {
    font-size: 18px;
    color: var(--secondary);
    line-height: 1.8;
    max-width: 800px;
}
 
.card-blue {
    background: var(--primary-light);
    border-radius: var(--radius);
    padding: 64px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 48px;
    margin-bottom: 24px;
    overflow: hidden;
}
 
.card-blue-content { flex: 1; }
 
.card-blue-title {
    font-size: 36px;
    font-weight: 700;
    color: var(--dark);
    margin-bottom: 12px;
}
 
.card-blue-subtitle {
    font-size: 18px;
    color: var(--secondary);
    margin-bottom: 28px;
    line-height: 1.6;
}
 
.card-blue-img {
    flex: 0 0 340px;
    max-width: 340px;
    border-radius: var(--radius-sm);
    overflow: hidden;
}
 
.card-blue-img img {
    width: 100%;
    height: 260px;
    object-fit: cover;
    border-radius: var(--radius-sm);
}
 
.footer-landing {
    background: var(--primary-light);
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    font-size: 14px;
    color: var(--secondary);
    font-weight: 500;
}
 
/* ── ABOUT / GUIDE PAGES ── */
.page-hero {
    width: 100%;
    height: 470px;
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, #2F80ED 0%, #1a5fbf 100%);
}
 
.page-hero-img {
    width: 100%;
    height: 470px;
    object-fit: cover;
    display: block;
    opacity: 0.35;
}
 
.page-hero-text {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    color: white;
    width: 90%;
}
 
.page-hero-text h1 {
    font-size: 72px;
    font-weight: 700;
    color: white !important;
    margin: 0;
    line-height: 1.1;
    text-shadow: 0 2px 20px rgba(0,0,0,0.3);
}
 
.page-content {
    max-width: 860px;
    margin: 0 auto;
    padding: 64px 48px;
}
 
.page-content h2 {
    font-size: 32px !important;
    font-weight: 700 !important;
    color: var(--dark) !important;
    margin-top: 48px !important;
    margin-bottom: 16px !important;
}
 
.page-content p {
    font-size: 18px;
    color: var(--secondary);
    line-height: 1.8;
    margin-bottom: 20px;
}
 
.page-content ul {
    font-size: 17px;
    color: var(--secondary);
    line-height: 1.9;
}
 
.page-content li { margin-bottom: 6px; }
 
.step-number {
    color: var(--primary);
    font-weight: 600;
    font-size: 16px;
    margin-bottom: 4px;
}
 
.disclaimer-box {
    background: #F8FAFC;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 20px 24px;
    font-size: 15px;
    color: var(--secondary);
    font-style: italic;
    margin: 40px 0;
    line-height: 1.7;
}
 
.buttons-row {
    display: flex;
    gap: 16px;
    margin-top: 48px;
    flex-wrap: wrap;
}
 
.guide-img-full {
    width: 100%;
    height: auto;
    border-radius: var(--radius);
    margin: 48px 0;
    display: block;
}
 
.limits-title {
    font-size: 36px;
    font-weight: 700;
    color: var(--dark);
    margin-bottom: 12px;
}
 
.limits-subtitle {
    color: var(--primary);
    font-size: 16px;
    font-weight: 500;
    margin-bottom: 20px;
}
 
/* ── APP CARDS ── */
.patient-card {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 16px 20px;
    margin-bottom: 8px;
    box-shadow: var(--shadow);
    transition: box-shadow 0.15s ease;
}
.patient-card.urgent { border-left: 4px solid #DC2626; }
.patient-card.semi-urgent { border-left: 4px solid #D97706; }
.patient-card.stable { border-left: 4px solid #059669; }
 
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
}
.badge-urgent { background: #FEE2E2; color: #DC2626; }
.badge-warning { background: #FEF3C7; color: #B45309; }
.badge-success { background: #D1FAE5; color: #059669; }
.badge-info { background: var(--primary-light); color: var(--primary); }
 
/* ── TOP BAR APP ── */
.app-topbar {
    background: var(--primary);
    color: white;
    text-align: center;
    padding: 8px;
    font-size: 0.8rem;
    font-weight: 500;
}
 
@media (max-width: 768px) {
    .hero-title { font-size: 28px; }
    .hero-overlay { width: 100%; padding: 32px 24px; }
    .card-blue { flex-direction: column; padding: 32px 24px; }
    .card-blue-img { flex: none; max-width: 100%; }
    .section-content { padding: 40px 24px; }
    .page-content { padding: 40px 24px; }
    .page-hero-text h1 { font-size: 40px !important; }
    .card-blue-title { font-size: 24px; }
    .section-title { font-size: 26px; }
}
</style>
""", unsafe_allow_html=True)
 
# ══════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════
if "current_page" not in st.session_state:
    st.session_state.current_page = "landing"
if "current_patient_id" not in st.session_state:
    st.session_state.current_patient_id = None
if "conversation" not in st.session_state:
    st.session_state.conversation = create_conversation()
if "langue" not in st.session_state:
    st.session_state.langue = "Français"
if "app_page" not in st.session_state:
    st.session_state.app_page = "dashboard"
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
if "pending_patient_id" not in st.session_state:
    st.session_state.pending_patient_id = None
if "pending_notes" not in st.session_state:
    st.session_state.pending_notes = ""
 
# ══════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════
def get_urgency_emoji(score):
    if score >= 70: return "🔴"
    elif score >= 40: return "🟠"
    return "🟢"
 
def get_urgency_class(score):
    if score >= 70: return "urgent"
    elif score >= 40: return "semi-urgent"
    return "stable"
 
def go_to(page):
    st.session_state.current_page = page
    st.rerun()
 
def go_to_app(page="dashboard"):
    st.session_state.current_page = "app"
    st.session_state.app_page = page
    st.rerun()
 
def img_tag(path, alt="", style=""):
    if os.path.exists(path):
        return f'<img src="/{path}" alt="{alt}" style="{style}">'
    return f'<div style="background:#D5E6FB;border-radius:8px;height:200px;display:flex;align-items:center;justify-content:center;color:#2F80ED;font-weight:600;">{alt}</div>'
 
def logo_tag(height=50):
    logo_path = "assets/logos/logo.png"
    if os.path.exists(logo_path):
        return f'<img src="/{logo_path}" alt="ColoCare MD" style="height:{height}px;">'
    return '<span style="font-size:1.4rem;font-weight:700;color:#2F80ED;">🏥 ColoCare MD</span>'
 
def start_icon():
    icon_path = "assets/icons/start.svg"
    if os.path.exists(icon_path):
        return f'<img src="/{icon_path}" alt="" style="width:18px;height:18px;vertical-align:middle;">'
    return "🚀"

# ════════════════════════════════════════════════════════════════
# ══════════════════ PAGE LANDING ════════════════════════════════
# ════════════════════════════════════════════════════════════════
if st.session_state.current_page == "landing":

    import base64, os
    import streamlit.components.v1 as components

    def img_b64(path: str) -> str:
        if not os.path.exists(path):
            return ""
        ext = path.split(".")[-1].lower()
        mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
        with open(path, "rb") as f:
            return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"

    logo_src  = img_b64("assets/logos/logo.png")
    hero_src  = img_b64("assets/images/home1.png")
    card1_src = img_b64("assets/images/home2.svg")
    card2_src = img_b64("assets/images/home3.svg")

    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background:#fff !important; padding:0 !important; }
    [data-testid="stHeader"],[data-testid="stToolbar"],
    [data-testid="stDecoration"],footer,#MainMenu { display:none !important; }
    .block-container { padding:0 !important; max-width:100% !important; }
    [data-testid="stVerticalBlock"] { gap:0 !important; }
    [data-testid="element-container"] { padding:0 !important; margin:0 !important; }
    div[data-testid="stButton"] { display:none !important; }
    iframe { display:block !important; border:none !important; }
    </style>
    """, unsafe_allow_html=True)

    if st.button("Commencer", type="primary", key="hero_start"):
        go_to_app("dashboard")
    if st.button("Consulter", key="guide_btn"):
        go_to("guide")
    if st.button("En savoir plus", key="about_btn"):
        go_to("about")

    html_page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Poppins',sans-serif;background:#fff;color:#181D27;overflow-x:hidden}}
.topbar{{width:100%;height:34px;background:#2F80ED;color:#fff;
  font-size:15px;font-weight:500;display:flex;align-items:center;justify-content:center;
  letter-spacing:0.01em}}
.navbar{{width:100%;height:63px;background:#fff;
    box-shadow:0 1px 1px rgba(0,0,0,0.18);
    display:flex;align-items:center;padding:0 70px;}}
.navbar img{{height:200px;width:auto;object-fit:contain;display:block;margin-top:7px;}}
.hero{{position:relative;width:100%;height:640px;overflow:hidden;
  background:linear-gradient(135deg,#D5E6FB 0%,#EEF5FD 100%)}}
.hero-bg{{position:absolute;inset:0;width:100%;height:100%;
  object-fit:cover;object-position:center right;display:block}}
.hero-overlay{{position:absolute;left:66px;top:148px;
  width:480px;z-index:2;display:flex;flex-direction:column;align-items:flex-start}}
.hero-title{{font-weight:700;font-size:44px;line-height:1.12;
  letter-spacing:-0.04em;color:#0B0262;margin-bottom:18px}}
.hero-desc{{font-weight:400;font-size:18px;line-height:28px;
  letter-spacing:-0.01em;color:#3E3E3E;margin-bottom:32px}}
.btn-start{{display:inline-flex;align-items:center;gap:8px;
  background:#227FFC;color:#fff;font-family:'Poppins',sans-serif;
  font-size:15px;font-weight:600;padding:13px 24px;border-radius:8px;
  border:none;cursor:pointer;height:48px;
  box-shadow:0 4px 14px rgba(34,127,252,.3);
  transition:background .2s,transform .15s}}
.btn-start:hover{{background:#1a6fd4;transform:translateY(-1px)}}
.section{{padding:72px 112px 52px;background:#fff}}
.section h2{{font-weight:600;font-size:40px;line-height:1.15;
  letter-spacing:-.05em;color:#181D27;margin-bottom:16px}}
.section p{{font-weight:400;font-size:18px;line-height:28px;
  letter-spacing:-.01em;color:#525252;max-width:900px}}
.cards{{padding:0 112px 60px;display:flex;flex-direction:column;gap:28px}}
.card{{position:relative;background:#D5E6FB;border-radius:16px;
  padding:56px 64px;display:flex;flex-direction:row;
  align-items:flex-start;overflow:hidden;min-height:300px;
  box-shadow:0 4px 24px rgba(47,128,237,.08);
  transition:box-shadow .25s,transform .2s}}
.card:hover{{box-shadow:0 8px 36px rgba(47,128,237,.16);transform:translateY(-2px)}}
.card-content{{position:relative;z-index:2;display:flex;flex-direction:column;
  align-items:flex-start;gap:14px;max-width:560px}}
.card-title{{font-weight:700;font-size:36px;line-height:1.15;
  letter-spacing:-.04em;color:#212121}}
.card-sub{{font-weight:400;font-size:18px;line-height:28px;
  letter-spacing:-.01em;color:#262626}}
.btn-card{{display:inline-flex;align-items:center;justify-content:center;
  background:#2F80ED;color:#fff;font-family:'Poppins',sans-serif;
  font-size:15px;font-weight:600;padding:12px 22px;border-radius:8px;
  border:1px solid #2F80ED;cursor:pointer;height:48px;min-width:120px;margin-top:8px;
  box-shadow:0 1px 2px rgba(10,13,18,.05);transition:background .2s,transform .15s}}
.btn-card:hover{{background:#1a6fd4;border-color:#1a6fd4;transform:translateY(-1px)}}
.card-img{{position:absolute;right:40px;top:-60px;width:52%;height:115%;z-index:1;overflow:visible;}}
.card-img img{{position:absolute;width:110%;height:110%;object-fit:contain;object-position:right top;display:block;}}
.footer{{width:100%;height:120px;background:#D5E6FB;margin-top:24px;
  display:flex;align-items:center;justify-content:center}}
.footer span{{font-weight:400;font-size:16px;color:#000;text-align:center}}
@keyframes up{{from{{opacity:0;transform:translateY(18px)}}to{{opacity:1;transform:translateY(0)}}}}
.hero-title{{animation:up .6s ease both}}
.hero-desc{{animation:up .6s .12s ease both}}
.btn-start{{animation:up .6s .24s ease both}}
</style>
</head>
<body>
<div class="topbar">Copilote clinique IA propulsé par Gemma 4</div>
<div class="navbar">
  <img src="{logo_src}" alt="ColoCare MD">
</div>
<div class="hero">
  <img class="hero-bg" src="{hero_src}" alt="">
  <div class="hero-overlay">
    <h1 class="hero-title">Copilote clinique IA<br>en oncologie colorectale</h1>
    <p class="hero-desc">Une plateforme d'aide à la décision médicale basée sur Gemma 4,<br>
    fonctionnant 100% en local pour les hôpitaux francophones.</p>
    <button class="btn-start" onclick="
      var btns = window.parent.document.querySelectorAll('button');
      btns.forEach(function(b){{ if(b.innerText.includes('Commencer')) b.click(); }});
    ">⏱&nbsp;&nbsp;Commencer</button>
  </div>
</div>
<div class="section">
  <h2>Copilote clinique IA</h2>
  <p>ColoCare MD automatise l'analyse clinique des rapports médicaux grâce à Gemma 4,
  avec extraction TNM, recommandations basées sur les guidelines ESMO/NCCN,
  priorisation intelligente des cas, explicabilité des décisions,
  génération de résumés RCP et assistance conversationnelle spécialisée
  en oncologie colorectale.</p>
</div>
<div class="cards">
  <div class="card">
    <div class="card-content">
      <div class="card-title">Votre guide d'utilisation</div>
      <div class="card-sub">Guide complet en 6 étapes</div>
      <button class="btn-card" onclick="
        var btns = window.parent.document.querySelectorAll('button');
        btns.forEach(function(b){{ if(b.innerText.trim()==='Consulter') b.click(); }});
      ">Consulter</button>
    </div>
    <div class="card-img"><img src="{card1_src}" alt="Guide"></div>
  </div>
  <div class="card" style="min-height:340px">
    <div class="card-content">
      <div class="card-title">À propos</div>
      <div class="card-sub">Une plateforme d'intelligence artificielle médicale développée dans le cadre
        du Gemma 4 Good Hackathon 2026,
        dédiée au cancer colorectal pour le monde francophone.</div>
      <button class="btn-card" onclick="
        var btns = window.parent.document.querySelectorAll('button');
        btns.forEach(function(b){{ if(b.innerText.trim()==='En savoir plus') b.click(); }});
      ">En savoir plus</button>
    </div>
    <div class="card-img"><img src="{card2_src}" alt="À propos"></div>
  </div>
</div>
<div class="footer">
  <span>ColoCare MD — Gemma 4 Good Hackathon 2026 | Google × Kaggle</span>
</div>
<script>
function resize(){{
  window.parent.postMessage({{
    isStreamlitMessage:true,
    type:'streamlit:setFrameHeight',
    height:document.documentElement.scrollHeight
  }},'*');
}}
window.addEventListener('load',function(){{setTimeout(resize,100)}});
new ResizeObserver(resize).observe(document.body);
</script>
</body>
</html>"""
    components.html(html_page, height=1900, scrolling=False)

# ════════════════════════════════════════════════════════════════
# ══════════════════ PAGE ABOUT ══════════════════════════════════
# ════════════════════════════════════════════════════════════════
elif st.session_state.current_page == "about":

    import base64, os
    import streamlit.components.v1 as components

    def img_b64_page(path: str) -> str:
        if not os.path.exists(path):
            return ""
        ext = path.split(".")[-1].lower()
        mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
        with open(path, "rb") as f:
            return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"

    logo_src  = img_b64_page("assets/logos/logo.png")
    about_src = img_b64_page("assets/images/about.png")

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
    div[data-testid="stButton"]        { display: none !important; }
    [data-testid="stHeader"]           { display: none !important; }
    [data-testid="stToolbar"]          { display: none !important; }
    [data-testid="stDecoration"]       { display: none !important; }
    footer                             { display: none !important; }
    #MainMenu                          { display: none !important; }
    .stApp                                        { padding: 0 !important; margin: 0 !important; }
    .stApp > div                                  { padding: 0 !important; margin: 0 !important; }
    [data-testid="stAppViewContainer"]            { padding: 0 !important; margin: 0 !important; background: #fff !important; }
    [data-testid="stAppViewContainer"] > section { padding: 0 !important; margin: 0 !important; }
    section[data-testid="stMain"]                 { padding: 0 !important; margin: 0 !important; }
    section[data-testid="stMain"] > div           { padding: 0 !important; margin: 0 !important; }
    .block-container                              { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
    [data-testid="stVerticalBlock"]               { gap: 0 !important; }
    [data-testid="element-container"]             { padding: 0 !important; margin: 0 !important; }
    iframe {
        display: block !important; vertical-align: top !important;
        margin: 0 !important; padding: 0 !important;
        border: none !important; margin-top: -6px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <script>
    (function() {
        function scrollTop() {
            try {
                var targets = [
                    window.parent.document.querySelector('section[data-testid="stMain"]'),
                    window.parent.document.querySelector('[data-testid="stAppViewContainer"]'),
                    window.parent.document.body,
                    window.parent.document.documentElement
                ];
                targets.forEach(function(el) { if (el) el.scrollTop = 0; });
                window.parent.scrollTo(0, 0);
            } catch(e) {}
        }
        scrollTop();
        setTimeout(scrollTop, 80);
        setTimeout(scrollTop, 250);
        setTimeout(scrollTop, 500);
    })();
    </script>
    """, unsafe_allow_html=True)

    if st.button("Commencer", key="about_start"):
        go_to_app("dashboard")
    if st.button("Retour", key="about_back"):
        go_to("landing")

    hero_img_tag = f'<img class="pg-hero-bg" src="{about_src}" alt="">' if about_src else ""

    about_html = f"""<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; font-family: 'Poppins', sans-serif; background: #fff; overflow-x: hidden; }}
.pg-topbar {{ width: 100%; height: 34px; background: #2F80ED; color: #fff; font-size: 15px; font-weight: 500; display: flex; align-items: center; justify-content: center; margin: 0; padding: 0; }}
.pg-navbar {{ width: 100%; height: 63px; background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,0.15); display: flex; align-items: center; padding: 0 55px; margin: 0; }}
.pg-navbar img {{ height: 200px; width: auto; object-fit: contain; display: block; margin-top: 7px; }}
.pg-hero {{ position: relative; width: 100%; height: 280px; overflow: hidden; background: #2F80ED; display: flex; align-items: center; justify-content: center; }}
.pg-hero-bg {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center; opacity: 0.18; transform: scale(1.6); display: block; }}
.pg-hero-text {{ position: absolute; z-index: 2; width: 100%; text-align: center; }}
.pg-hero-text h1 {{ font-family: 'Poppins', sans-serif; font-weight: 800; font-size: 64px; line-height: 1.1; color: #fff; margin: 0; }}
.pg-content {{ width: 100%; padding: 60px 120px; font-family: 'Poppins', sans-serif; }}
.pg-content h2 {{ font-size: 28px; font-weight: 700; color: #181D27; margin: 45px 0 18px; text-align: left; }}
.pg-content h2:first-child {{ margin-top: 0; }}
.pg-content p {{ font-size: 18px; line-height: 1.8; color: #444; margin-bottom: 28px; text-align: left; }}
.pg-disclaimer {{ margin-top: 45px; color: #777; font-size: 16px; font-style: italic; background: #F8FAFC; border: 1px solid #E8EDF2; border-radius: 8px; padding: 20px 24px; line-height: 1.7; text-align: left; }}
.pg-btn-row {{ padding: 32px 120px 0; display: flex; gap: 16px; }}
.pg-btn-primary {{ display: inline-flex; align-items: center; justify-content: center; background: #227FFC; color: #fff; font-family: 'Poppins', sans-serif; font-size: 15px; font-weight: 600; padding: 12px 28px; border-radius: 8px; border: none; cursor: pointer; height: 48px; min-width: 140px; box-shadow: 0 4px 14px rgba(34,127,252,0.28); transition: background .2s, transform .15s; }}
.pg-btn-primary:hover {{ background: #1a6fd4; transform: translateY(-1px); }}
.pg-btn-secondary {{ display: inline-flex; align-items: center; justify-content: center; background: #fff; color: #227FFC; font-family: 'Poppins', sans-serif; font-size: 15px; font-weight: 600; padding: 12px 28px; border-radius: 8px; border: 2px solid #227FFC; cursor: pointer; height: 48px; min-width: 140px; transition: background .2s, transform .15s; }}
.pg-btn-secondary:hover {{ background: #EEF5FD; transform: translateY(-1px); }}
.pg-footer {{ width: 100%; height: 120px; background: #D5E6FB; margin-top: 64px; margin-bottom: 0; display: flex; align-items: center; justify-content: center; }}
.pg-footer span {{ font-family: 'Poppins', sans-serif; font-size: 15px; font-weight: 500; color: #525252; text-align: center; }}
</style>
</head>
<body>
<div class="pg-topbar">Copilote clinique IA propulsé par Gemma 4</div>
<div class="pg-navbar"><img src="{logo_src}" alt="ColoCare MD"></div>
<div class="pg-hero">
  {hero_img_tag}
  <div class="pg-hero-text"><h1>À propos de ColoCare MD</h1></div>
</div>
<div class="pg-content">
  <h2>A propos de ColoCare MD</h2>
  <p>Une plateforme d'intelligence artificielle médicale développée pour le Gemma 4 Good Hackathon 2026, dédiée au cancer colorectal dans le monde francophone.</p>
  <h2>Le problème que nous résolvons</h2>
  <p>Le cancer colorectal est le deuxième cancer le plus mortel au monde, avec 1,9 million de nouveaux cas par an selon l'OMS. En Tunisie, son incidence a doublé en une décennie, passant à plus de 4 000 nouveaux cas enregistrés en 2024. Ce phénomène touche l'ensemble du Maghreb et de l'Afrique du Nord francophone : Maroc, Algérie, Tunisie, où les systèmes de santé font face à une pression croissante.</p>
  <p>Nos hôpitaux disposent de médecins excellents. Chirurgiens viscéraux, oncologues, gastroentérologues — leur expertise est réelle et reconnue. Mais la surcharge de travail constitue un défi majeur : un médecin dans un service d'oncologie tunisien peut recevoir 15 à 25 nouveaux dossiers par jour, chacun nécessitant entre 30 et 60 minutes d'analyse manuelle pour croiser les rapports de pathologie, d'imagerie, de biologie et de coloscopie.</p>
  <p>Dans ce contexte, chaque minute devient critique. Un retard dans le triage ou l'interprétation d'un dossier peut entraîner une progression tumorale, la perte d'une fenêtre thérapeutique importante, ou une décision clinique prise sous une forte contrainte de temps.</p>
  <h2>Notre réponse : ColoCare MD</h2>
  <p>ColoCare MD est un copilote clinique IA offline spécialisé en oncologie colorectale. Construit sur Gemma 4 via Ollama, il fonctionne entièrement en local, sans connexion internet, sans transfert de données vers le cloud — c'est une caractéristique essentielle pour la conformité aux réglementations de confidentialité médicale.</p>
  <p>L'application permet au médecin d'uploader en quelques secondes les documents disponibles d'un patient : rapport de pathologie, compte rendu opératoire, scanner, analyses biologiques et reçoit en retour une synthèse structurée : stade TNM extrait automatiquement, score de priorité calculé selon les guidelines ESMO/NCCN, orientation thérapeutique recommandée, explication complète de chaque décision IA, et résumé RCP prêt pour la réunion multidisciplinaire.</p>
  <h2>Pourquoi l'offline est crucial</h2>
  <p>Dans de nombreux hôpitaux publics tunisiens et maghrébins, la connectivité internet est instable, les politiques de sécurité informatique interdisent l'envoi de données médicales vers des serveurs externes, et les budgets d'infrastructure cloud sont inexistants. ColoCare MD est conçu pour ces réalités. Il tourne sur n'importe quel ordinateur de bureau hospitalier standard, sans abonnement, sans données transmises, sans dépendance externe.</p>
  <h2>L'IA au service du médecin, pas à sa place</h2>
  <p>Nous croyons fermement que l'intelligence artificielle doit augmenter les capacités du médecin sans jamais se substituer à son expertise. Chaque recommandation de ColoCare MD est associée à une justification explicite, un niveau de confiance et un processus de validation humaine obligatoire. La décision finale appartient toujours au médecin.</p>
  <h2>Contexte du Hackathon</h2>
  <p>Ce projet est développé pour le Gemma 4 Good Hackathon organisé par Google et Kaggle en 2026, dans le cadre de la catégorie Health &amp; Sciences. L'objectif est de démontrer comment les modèles Gemma open source peuvent créer un impact clinique réel, mesurable et accessible dans des contextes à ressources limitées.</p>
  <div class="pg-disclaimer">ColoCare MD est un prototype de recherche. Il n'est pas certifié médicalement et nécessite une validation clinique avant tout usage en environnement hospitalier réel.</div>
</div>
<div class="pg-btn-row">
  <button class="pg-btn-primary" onclick="window.parent.document.querySelectorAll('button').forEach(function(b){{if(b.innerText.trim()==='Commencer')b.click();}});">Commencer</button>
  <button class="pg-btn-secondary" onclick="window.parent.document.querySelectorAll('button').forEach(function(b){{if(b.innerText.trim()==='Retour')b.click();}});">Retour</button>
</div>
<div class="pg-footer"><span>ColoCare MD — Gemma 4 Good Hackathon 2026 | Google × Kaggle</span></div>
<script>
(function() {{
    window.scrollTo(0, 0);
    function scrollParentTop() {{
        try {{
            ['section[data-testid="stMain"]','[data-testid="stAppViewContainer"]','.main','.block-container'].forEach(function(sel) {{
                var el = window.parent.document.querySelector(sel);
                if (el) el.scrollTop = 0;
            }});
            window.parent.document.documentElement.scrollTop = 0;
            window.parent.document.body.scrollTop = 0;
            window.parent.scrollTo(0, 0);
        }} catch(e) {{}}
    }}
    scrollParentTop();
    setTimeout(scrollParentTop, 80);
    setTimeout(scrollParentTop, 300);
    var booted = false;
    function resize() {{
        window.parent.postMessage({{isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:document.documentElement.scrollHeight}},'*');
    }}
    window.addEventListener('load', function() {{
        scrollParentTop();
        setTimeout(function() {{ resize(); booted = true; setTimeout(scrollParentTop, 120); }}, 200);
    }});
    new ResizeObserver(function() {{ if (!booted) return; resize(); }}).observe(document.body);
}})();
</script>
</body>
</html>"""

    components.html(about_html, height=1900, scrolling=True)

# ════════════════════════════════════════════════════════════════
# ══════════════════ PAGE GUIDE ══════════════════════════════════
# ════════════════════════════════════════════════════════════════
elif st.session_state.current_page == "guide":

    import base64, os
    import streamlit.components.v1 as components

    def img_b64_page(path: str) -> str:
        if not os.path.exists(path):
            return ""
        ext = path.split(".")[-1].lower()
        mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
        with open(path, "rb") as f:
            return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"

    logo_src  = img_b64_page("assets/logos/logo.png")
    about_src = img_b64_page("assets/images/about.png")
    guide_src = img_b64_page("assets/images/guide.png")

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
    div[data-testid="stButton"]        { display: none !important; }
    [data-testid="stHeader"]           { display: none !important; }
    [data-testid="stToolbar"]          { display: none !important; }
    [data-testid="stDecoration"]       { display: none !important; }
    footer                             { display: none !important; }
    #MainMenu                          { display: none !important; }
    .stApp                                        { padding: 0 !important; margin: 0 !important; }
    .stApp > div                                  { padding: 0 !important; margin: 0 !important; }
    [data-testid="stAppViewContainer"]            { padding: 0 !important; margin: 0 !important; background: #fff !important; }
    [data-testid="stAppViewContainer"] > section { padding: 0 !important; margin: 0 !important; }
    section[data-testid="stMain"]                 { padding: 0 !important; margin: 0 !important; }
    section[data-testid="stMain"] > div           { padding: 0 !important; margin: 0 !important; }
    .block-container                              { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
    [data-testid="stVerticalBlock"]               { gap: 0 !important; }
    [data-testid="element-container"]             { padding: 0 !important; margin: 0 !important; }
    iframe {
        display: block !important; vertical-align: top !important;
        margin: 0 !important; padding: 0 !important;
        border: none !important; margin-top: -6px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <script>
    (function() {
        function scrollTop() {
            try {
                var targets = [
                    window.parent.document.querySelector('section[data-testid="stMain"]'),
                    window.parent.document.querySelector('[data-testid="stAppViewContainer"]'),
                    window.parent.document.body,
                    window.parent.document.documentElement
                ];
                targets.forEach(function(el) { if (el) el.scrollTop = 0; });
                window.parent.scrollTo(0, 0);
            } catch(e) {}
        }
        scrollTop();
        setTimeout(scrollTop, 80);
        setTimeout(scrollTop, 250);
        setTimeout(scrollTop, 500);
    })();
    </script>
    """, unsafe_allow_html=True)

    if st.button("Commencer", type="primary", key="guide_start"):
        go_to_app("dashboard")
    if st.button("Retour", key="guide_back"):
        go_to("landing")

    hero_img_tag  = f'<img class="pg-hero-bg" src="{about_src}" alt="">' if about_src else ""
    guide_img_tag = f'<img src="{guide_src}" alt="Guide" style="width:100%;height:auto;display:block;margin:0;">' if guide_src else ""

    guide_html = f"""<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; font-family: 'Poppins', sans-serif; background: #fff; overflow-x: hidden; }}
.pg-topbar {{ width: 100%; height: 34px; background: #2F80ED; color: #fff; font-size: 15px; font-weight: 500; display: flex; align-items: center; justify-content: center; margin: 0; padding: 0; }}
.pg-navbar {{ width: 100%; height: 63px; background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,0.15); display: flex; align-items: center; padding: 0 55px; margin: 0; }}
.pg-navbar img {{ height: 200px; width: auto; object-fit: contain; display: block; margin-top: 7px; }}
.pg-hero {{ position: relative; width: 100%; height: 280px; overflow: hidden; background: #2F80ED; display: flex; align-items: center; }}
.pg-hero-bg {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center; opacity: 0.18; transform: scale(1.6); display: block; }}
.pg-hero-text {{ position: absolute; z-index: 2; width: 100%; text-align: center; }}
.pg-hero-text h1 {{ font-family: 'Poppins', sans-serif; font-weight: 800; font-size: 64px; line-height: 1.1; color: #fff; margin: 0; }}
.pg-content {{ width: 100%; padding: 60px 120px; font-family: 'Poppins', sans-serif; }}
.pg-content h2 {{ font-size: 28px; font-weight: 700; color: #181D27; margin: 40px 0 12px; text-align: left; }}
.pg-content h2:first-child {{ margin-top: 0; }}
.pg-content p {{ font-size: 17px; color: #525252; line-height: 1.8; margin: 0 0 16px; text-align: left; }}
.pg-content ul {{ font-size: 17px; color: #525252; line-height: 1.8; margin: 0 0 16px; padding-left: 24px; }}
.pg-content li {{ margin-bottom: 4px; text-align: left; }}
.pg-step {{ color: #2F80ED; font-weight: 600; font-size: 16px; margin: 28px 0 6px; text-align: left; font-family: 'Poppins', sans-serif; }}
.pg-limits-title {{ font-size: 32px; font-weight: 700; color: #181D27; margin: 0 0 8px; font-family: 'Poppins', sans-serif; }}
.pg-limits-sub {{ color: #2F80ED; font-size: 15px; font-weight: 500; margin: 0 0 20px; font-family: 'Poppins', sans-serif; }}
.pg-disclaimer {{ background: #F8FAFC; border: 1px solid #E8EDF2; border-radius: 8px; padding: 20px 24px; font-size: 15px; color: #94A3B8; font-style: italic; margin: 32px 0 0; line-height: 1.7; }}
.pg-btn-row {{ padding: 32px 120px 0; display: flex; gap: 16px; }}
.pg-btn-primary {{ display: inline-flex; align-items: center; justify-content: center; background: #227FFC; color: #fff; font-family: 'Poppins', sans-serif; font-size: 15px; font-weight: 600; padding: 12px 28px; border-radius: 8px; border: none; cursor: pointer; height: 48px; min-width: 140px; box-shadow: 0 4px 14px rgba(34,127,252,0.28); transition: background .2s, transform .15s; }}
.pg-btn-primary:hover {{ background: #1a6fd4; transform: translateY(-1px); }}
.pg-btn-secondary {{ display: inline-flex; align-items: center; justify-content: center; background: #fff; color: #227FFC; font-family: 'Poppins', sans-serif; font-size: 15px; font-weight: 600; padding: 12px 28px; border-radius: 8px; border: 2px solid #227FFC; cursor: pointer; height: 48px; min-width: 140px; transition: background .2s, transform .15s; }}
.pg-btn-secondary:hover {{ background: #EEF5FD; transform: translateY(-1px); }}
.pg-footer {{ width: 100%; height: 120px; background: #D5E6FB; margin-top: 64px; margin-bottom: 0; display: flex; align-items: center; justify-content: center; }}
.pg-footer span {{ font-family: 'Poppins', sans-serif; font-size: 15px; font-weight: 500; color: #525252; text-align: center; }}
</style>
</head>
<body>
<div class="pg-topbar">Copilote clinique IA propulsé par Gemma 4</div>
<div class="pg-navbar"><img src="{logo_src}" alt="ColoCare MD"></div>
<div class="pg-hero">
  {hero_img_tag}
  <div class="pg-hero-text"><h1>Votre guide d'utilisation</h1></div>
</div>
<div class="pg-content">
  <h2>Workflow complet en 6 étapes</h2>
  <div class="pg-step">1. Créer un nouveau dossier patient</div>
  <p>Cliquez sur le bouton "Ajouter patient" en haut à droite du Dashboard. Attribuez un identifiant anonymisé au patient (ex: Dossier_2024_001). Sélectionnez le type de dossier : Bilan initial, Post-opératoire, Suivi chimio, ou Récidive.</p>
  <div class="pg-step">2. Uploader les documents médicaux</div>
  <p>L'application accepte plusieurs types de fichiers simultanément :</p>
  <ul>
    <li>Fichiers PDF : rapports de pathologie, comptes rendus opératoires, discharge summaries, lettres de consultation</li>
    <li>Fichiers TXT : notes cliniques, rapports d'imagerie exportés</li>
    <li>Images JPG/PNG : images de coloscopie pour analyse visuelle</li>
  </ul>
  <p>Plus vous fournissez de documents, plus l'analyse sera précise et complète.</p>
  <div class="pg-step">3. Lancer l'analyse Gemma 4</div>
  <p>Cliquez sur "Lancer l'analyse complète". Le pipeline modulaire s'exécute en 10 étapes indépendantes :</p>
  <ul>
    <li>Lecture et nettoyage des documents</li>
    <li>Extraction des données cliniques (TNM, métastases, biomarqueurs, complications)</li>
    <li>Validation diagnostique (cancer colorectal confirmé ou non ?)</li>
    <li>Vérification de la complétude du dossier</li>
    <li>Calcul du score de priorité clinique (0-100)</li>
    <li>Décision d'orientation thérapeutique</li>
    <li>Génération de l'explication médicale (Explainability)</li>
    <li>Calcul du risque de récidive</li>
    <li>Analyse des images (si uploadées)</li>
    <li>Fusion multimodale des données</li>
  </ul>
  <div class="pg-step">4. Interpréter les résultats</div>
  <p>L'analyse produit un tableau de bord clinique complet :</p>
  <ul>
    <li>Score de priorité : de 0 (stable) à 100 (urgence vitale)</li>
    <li>Stade TNM extrait automatiquement avec validation</li>
    <li>Orientation recommandée : Chirurgie, Oncologie, ou RCP multidisciplinaire</li>
    <li>Guidelines ESMO 2023 applicables au stade détecté</li>
    <li>Explainability : quelles preuves, quelles règles, quelle confiance</li>
    <li>Risque de récidive estimé</li>
  </ul>
  <div class="pg-step">5. Valider ou modifier la décision</div>
  <p>Le médecin dispose de trois actions :</p>
  <ul>
    <li>✅ Valider : la décision IA est confirmée</li>
    <li>❌ Rejeter : la décision est écartée</li>
    <li>✏️ Modifier : mode édition pour corriger le résumé clinique ou les notes d'orientation</li>
  </ul>
  <div class="pg-step">6. Générer le résumé RCP</div>
  <p>Dans la page "Dossier patient", cliquez sur "Générer résumé RCP". Gemma 4 génère automatiquement un résumé structuré comprenant :</p>
  <ul>
    <li>Présentation du cas en 2-3 phrases</li>
    <li>Éléments cliniques clés</li>
    <li>Question posée à la RCP</li>
    <li>Spécialistes à convoquer</li>
    <li>Examens complémentaires suggérés</li>
    <li>Recommandation préliminaire selon ESMO</li>
  </ul>
  <p>Le résumé peut être téléchargé en format texte et utilisé directement en réunion.</p>
</div>
{guide_img_tag}
<div class="pg-content" style="padding-top:48px;">
  <div class="pg-limits-title">Limites à connaître</div>
  <div class="pg-limits-sub">ColoCare MD est un prototype de recherche avec certaines limites importantes</div>
  <ul style="font-size:17px;color:#525252;line-height:1.8;padding-left:24px;margin:0 0 16px;">
    <li>L'extraction TNM peut être imprécise sur les stades très avancés (T4a, T4b, M1b, M1c).</li>
    <li>Les performances dépendent de la qualité et de la complétude des documents fournis.</li>
    <li>Le système ne remplace en aucun cas une évaluation médicale humaine.</li>
  </ul>
  <div class="pg-disclaimer">ColoCare MD est un prototype de recherche. Il n'est pas certifié médicalement et nécessite une validation clinique avant tout usage en environnement hospitalier réel.</div>
</div>
<div class="pg-btn-row">
  <button class="pg-btn-primary" onclick="window.parent.document.querySelectorAll('button').forEach(function(b){{if(b.innerText.trim()==='Commencer')b.click();}});">Commencer</button>
  <button class="pg-btn-secondary" onclick="window.parent.document.querySelectorAll('button').forEach(function(b){{if(b.innerText.trim()==='Retour')b.click();}});">Retour</button>
</div>
<div class="pg-footer"><span>ColoCare MD — Gemma 4 Good Hackathon 2026 | Google × Kaggle</span></div>
<script>
(function() {{
    window.scrollTo(0, 0);
    function scrollParentTop() {{
        try {{
            ['section[data-testid="stMain"]','[data-testid="stAppViewContainer"]','.main','.block-container'].forEach(function(sel) {{
                var el = window.parent.document.querySelector(sel);
                if (el) el.scrollTop = 0;
            }});
            window.parent.document.documentElement.scrollTop = 0;
            window.parent.document.body.scrollTop = 0;
            window.parent.scrollTo(0, 0);
        }} catch(e) {{}}
    }}
    scrollParentTop();
    setTimeout(scrollParentTop, 80);
    setTimeout(scrollParentTop, 300);
    var booted = false;
    function resize() {{
        window.parent.postMessage({{isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:document.documentElement.scrollHeight}},'*');
    }}
    window.addEventListener('load', function() {{
        scrollParentTop();
        setTimeout(function() {{ resize(); booted = true; setTimeout(scrollParentTop, 120); }}, 200);
    }});
    new ResizeObserver(function() {{ if (!booted) return; resize(); }}).observe(document.body);
}})();
</script>
</body>
</html>"""

    components.html(guide_html, height=2800, scrolling=True)

# ════════════════════════════════════════════════════════════════
# ══════════════════ APPLICATION CLINIQUE ════════════════════════
# ════════════════════════════════════════════════════════════════
elif st.session_state.current_page == "app":

    # ── FIX 4d : Sidebar stable ──────────────────────────────────
    st.markdown("""
    <style>

   /* Sidebar reset */
   section[data-testid="stSidebar"]{
    display:block !important;
    visibility:visible !important;
    opacity:1 !important;
    transform:none !important;
    left:0 !important;
    margin-left:0 !important;
    width:280px !important;
    background:#ffffff !important;
    border-right:1px solid #E5E7EB !important;
    }

    section[data-testid="stSidebar"] > div{
     display:block !important;
     visibility:visible !important;
     opacity:1 !important;
     width:280px !important;
    }

    /* Main content */
    .block-container{
      max-width:1200px !important;
      padding-top:1rem !important;
    }  

    </style>
    """, unsafe_allow_html=True)

    # Urgents count
    all_patients_global = get_all_patients()
    urgents_count = len([
        p for p in all_patients_global
        if p.get("score", 0) >= 70 and p.get("statut") == "actif"
    ])

    # ── SIDEBAR ──────────────────────────────────────────────────
    with st.sidebar:
        if os.path.exists("assets/logos/logo.png"):
            st.image("assets/logos/logo.png", width=120)
        else:
            st.markdown('<div style="font-size:1.2rem;font-weight:700;color:#2F80ED;padding:16px 0 8px;">🏥 ColoCare MD</div>', unsafe_allow_html=True)

        st.divider()

        # ── FIX 4a : Vision Lab supprimé ──
        nav_items = [
            ("", "Home", "dashboard"),
            ("", "Dossier patient", "dossier"),
        ]

        for icon, label, page_key in nav_items:
            is_active = st.session_state.app_page == page_key
            btn_label = f"{' ' if is_active else ''}{icon} {label}"
            if st.button(btn_label, key=f"nav_{page_key}", use_container_width=True):
                st.session_state.app_page = page_key
                st.rerun()

        st.divider()

        st.markdown('<div style="font-size:0.72rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.06em;padding:4px 0 8px;">Assistant clinique</div>', unsafe_allow_html=True)

        col_asst, col_plus = st.columns([3, 1])
        with col_plus:
            if st.button("＋", key="new_conv_sb", help="Nouvelle discussion"):
                save_conversation_db(st.session_state.conversation)
                st.session_state.conversation = create_conversation()
                st.session_state.app_page = "assistant"
                st.rerun()
        with col_asst:
            if st.button(" Assistant", key="nav_assistant", use_container_width=True):
                st.session_state.app_page = "assistant"
                st.rerun()

        saved_convs = get_all_conversations_db()
        for i, conv in enumerate(saved_convs[:6]):
            is_active_conv = conv["id"] == st.session_state.conversation.get("id", "")
            dot = "🟢" if is_active_conv else "⚪"
            col_cv, col_del = st.columns([4, 1])
            with col_cv:
                short_title = conv['titre'][:18] + "..." if len(conv['titre']) > 18 else conv['titre']
                if st.button(f"{dot} d{i+1} — {short_title}", key=f"cv_{conv['id']}", use_container_width=True):
                    save_conversation_db(st.session_state.conversation)
                    st.session_state.conversation = conv
                    st.session_state.app_page = "assistant"
                    st.rerun()
            with col_del:
                if st.button("×", key=f"del_cv_{conv['id']}"):
                    delete_conversation_db(conv["id"])
                    st.rerun()

        st.divider()

        if urgents_count > 0:
            st.markdown(f"""
            <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:10px 12px;margin-bottom:8px;">
                <span style="color:#DC2626;font-weight:600;font-size:0.82rem;">🔴 {urgents_count} patient(s) urgent(s)</span>
            </div>
            """, unsafe_allow_html=True)

        st.session_state.langue = st.selectbox("🌐", ["Français", "English"], label_visibility="collapsed")

        st.divider()
        st.markdown('<div style="font-size:0.72rem;color:#94A3B8;line-height:1.5;padding:4px 0;">⚠️ AI decision support only<br>Le médecin valide toujours.</div>', unsafe_allow_html=True)

        if st.button("🏠 Accueil", use_container_width=True, key="back_home"):
            go_to("landing")

    # ── FIX 4b : Navbar blanche (remplace topbar bleue) ──────────
    col_nav1, col_nav2 = st.columns([3, 2])
    with col_nav1:
        page_titles = {
            "dashboard": "Dashboard",
            "dossier": "Dossier patient",
            "assistant": "Assistant clinique",
            "nouveau": "Nouveau patient",
        }
        st.markdown(f"""
        <div style="padding:12px 0 4px;">
            <span style="font-family:Poppins,sans-serif;font-size:1.4rem;font-weight:700;color:#181D27;">
                {page_titles.get(st.session_state.app_page, 'ColoCare MD')}
            </span>
        </div>
        """, unsafe_allow_html=True)
    with col_nav2:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        nav_right_c1, nav_right_c2 = st.columns([1, 2])
        with nav_right_c1:
            if urgents_count > 0:
                st.markdown(f"""
                <div style="position:relative;display:inline-block;padding:8px 12px;
                            background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;cursor:pointer;">
                    🔔
                    <span style="position:absolute;top:-4px;right:-4px;background:#DC2626;
                                 color:white;border-radius:50%;width:18px;height:18px;
                                 font-size:0.6rem;display:flex;align-items:center;
                                 justify-content:center;font-weight:700;">{urgents_count}</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown('<div style="padding:8px 12px;">🔔</div>', unsafe_allow_html=True)
        with nav_right_c2:
            if st.button("＋ Ajouter patient", type="primary", key="add_patient_top"):
                st.session_state.app_page = "nouveau"
                st.rerun()

    st.divider()

    # ════════════════════════════════
    # DASHBOARD
    # ════════════════════════════════
    if st.session_state.app_page == "dashboard":

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filtre_statut = st.selectbox("Statut", ["actif", "traite", "tous"], key="f_statut")
        with col2:
            filtre_urgence = st.selectbox("Urgence", ["tous", "urgent", "semi_urgent", "stable"], key="f_urg")
        with col3:
            filtre_stage = st.selectbox("Stage", ["tous", "Stage I", "Stage II", "Stage III", "Stage IV"], key="f_stage")
        with col4:
            filtre_orient = st.selectbox("Spécialité", ["tous", "chirurgie", "chirurgie_chimio", "chirurgie_urgente", "oncologie", "incertain"], key="f_orient")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        patients = get_all_patients(filtre_statut if filtre_statut != "tous" else None)

        if filtre_urgence != "tous":
            ranges = {"urgent": (70, 100), "semi_urgent": (40, 69), "stable": (0, 39)}
            lo, hi = ranges[filtre_urgence]
            patients = [p for p in patients if lo <= p.get("score", 0) <= hi]
        if filtre_stage != "tous":
            patients = [p for p in patients if p.get("stage_group") == filtre_stage]
        if filtre_orient != "tous":
            patients = [p for p in patients if p.get("orientation") == filtre_orient]

        if not patients:
            st.markdown("""
            <div style="text-align:center;padding:80px 40px;color:#94A3B8;">
                <div style="font-size:3rem;margin-bottom:16px;">📋</div>
                <div style="font-size:1.1rem;font-weight:500;color:#525252;margin-bottom:8px;">Aucun patient trouvé</div>
                <div style="font-size:0.875rem;">Cliquez sur "+ Ajouter patient" pour commencer.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # ── FIX 4e : métriques sans doublons ──
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Total patients", len(patients))
            with c2: st.metric("En attente validation", len([p for p in patients if p.get("validation_medecin") == "en_attente"]))
            with c3: st.metric("Traités", len([p for p in patients if p.get("statut") == "traite"]))

            if len(patients) > 1:
                scores = [p.get("score", 0) for p in patients]
                noms = [p.get("nom", "?")[:10] for p in patients]
                colors = ["#DC2626" if s >= 70 else "#D97706" if s >= 40 else "#059669" for s in scores]
                fig = go.Figure(go.Bar(
                    x=noms, y=scores, marker_color=colors,
                    marker_line_width=0, text=scores, textposition="outside"
                ))
                fig.update_layout(
                    plot_bgcolor="white", paper_bgcolor="white",
                    font_family="Poppins", yaxis_range=[0, 115], height=200,
                    margin=dict(t=16, b=8, l=8, r=8), showlegend=False,
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#F1F5F9")
                )
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            for patient in patients:
                score = patient.get("score", 0)
                emoji = get_urgency_emoji(score)
                urg_class = get_urgency_class(score)
                val = patient.get("validation_medecin", "en_attente")
                is_traite = patient.get("statut") == "traite"

                val_badge = '<span class="badge badge-success">✓ Validé</span>' if val == "validé" else \
                            '<span class="badge badge-urgent">✗ Rejeté</span>' if val == "rejeté" else \
                            '<span class="badge badge-info">En attente</span>'
                traite_badge = '<span class="badge badge-success">✓ Traité</span>' if is_traite else ""

                st.markdown(f"""
                <div class="patient-card {urg_class}">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                                <span>{emoji}</span>
                                <span style="font-weight:600;color:#181D27;font-size:0.95rem;">{patient.get('nom','?')}</span>
                                <code style="background:#F1F5F9;padding:2px 8px;border-radius:4px;font-size:0.78rem;color:#2F80ED;">{patient.get('stade','?')}</code>
                                <span style="font-size:0.8rem;color:#94A3B8;">{patient.get('stage_group','?')}</span>
                            </div>
                            <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
                                {val_badge} {traite_badge}
                                <span style="font-size:0.8rem;color:#525252;">Score <strong>{score}/100</strong></span>
                                <span style="font-size:0.8rem;color:#525252;">•</span>
                                <span style="font-size:0.8rem;color:#525252;">{patient.get('delai','?')}</span>
                                <span style="font-size:0.8rem;color:#94A3B8;">•</span>
                                <span style="font-size:0.8rem;color:#94A3B8;">{patient.get('date_analyse','?')}</span>
                            </div>
                        </div>
                        <div style="font-size:0.8rem;color:#94A3B8;">{patient.get('orientation','?')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                with col2:
                    if st.button("Ouvrir →", key=f"open_{patient['id']}"):
                        st.session_state.current_patient_id = patient["id"]
                        st.session_state.app_page = "dossier"
                        st.rerun()
                with col3:
                    if not is_traite:
                        if st.button("✓ Traité", key=f"traite_{patient['id']}"):
                            update_patient_status(patient["id"], "traite")
                            add_log(patient["id"], "marque_traite")
                            st.rerun()
                with col4:
                    if st.button("🗑", key=f"del_btn_{patient['id']}"):
                        st.session_state[f"confirm_{patient['id']}"] = True
                        st.rerun()
                with col5:
                    if st.session_state.get(f"confirm_{patient['id']}", False):
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("Oui", key=f"yes_{patient['id']}"):
                                delete_patient_db(patient["id"])
                                st.session_state.pop(f"confirm_{patient['id']}", None)
                                st.rerun()
                        with c2:
                            if st.button("Non", key=f"no_{patient['id']}"):
                                st.session_state.pop(f"confirm_{patient['id']}", None)
                                st.rerun()

    # ════════════════════════════════
    # NOUVEAU PATIENT — FIX 4c
    # ════════════════════════════════
    elif st.session_state.app_page == "nouveau":

        from datetime import datetime
        import re

        # ── Si résultats en attente de validation médecin ──
        if st.session_state.get("pending_patient_id"):
            pid = st.session_state.pending_patient_id
            from modules.database import load_pending_analysis, delete_pending_analysis

            pa = load_pending_analysis(pid)

            if not pa:
                st.error("Analyse temporaire introuvable.")
                st.session_state.pending_patient_id = None
                st.rerun()

            medical_data  = pa.get("medical_data", {})
            score_data    = pa.get("score_data", {})
            orientation   = pa.get("orientation", {})
            explanation   = pa.get("explanation", {})
            recurrence    = pa.get("recurrence", {})
            image_results = pa.get("image_results", [])
            validation    = pa.get("validation", {})
            completude    = pa.get("completude", {})
            elapsed       = pa.get("elapsed", 0)
            patient_nom   = pa.get("patient_nom", "?")
            patient_type  = pa.get("patient_type", "?")

            st.markdown(f'<div style="font-size:.8rem;color:#94A3B8;margin:8px 0;">Analyse terminée ({elapsed}s)</div>', unsafe_allow_html=True)
            st.info("**Les résultats ci-dessous ne sont pas encore enregistrés.** Validez pour sauvegarder.")

            vs = validation.get("status", "")
            if vs == "non_confirme": st.error(f"❌ {validation.get('message','')}")
            elif vs == "suspect": st.warning(f"⚠️ {validation.get('message','')}")
            else: st.success(f"✅ {validation.get('message','')}")

            ct = completude.get("taux_completude", 0)
            if completude.get("fiabilite") == "faible":
                st.error(f"⚠️ Complétude : {ct}% — Manquants : {', '.join(completude.get('champs_manquants',[]))}")
            elif completude.get("fiabilite") == "modérée":
                st.warning(f"⚠️ Complétude : {ct}%")
            else:
                st.success(f"✅ Complétude : {ct}%")

            st.divider()

            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Score priorité", f"{score_data.get('score',0)}/100")
            with c2: st.metric("TNM", f"{medical_data.get('stade_T','?')}{medical_data.get('stade_N','?')}{medical_data.get('stade_M','?')}")
            with c3: st.metric("Stage", orientation.get("stage_group","?"))
            with c4: st.metric("Confiance IA", f"{orientation.get('confidence',0)}%")

            st.divider()
            st.markdown("## Rapport clinique")

            st.markdown("### Résumé clinique")
            st.markdown(f'<div style="background:#F8FAFC;border-left:4px solid #2F80ED;border-radius:0 8px 8px 0;padding:16px 20px;font-size:.95rem;color:#181D27;line-height:1.7;">{explanation.get("resume_clinique","Non disponible")}</div>', unsafe_allow_html=True)

            if medical_data.get("traitement_anterieur") not in ["aucun","inconnu",None,""]:
                st.markdown(f'<div style="background:#FEF3C7;border-radius:8px;padding:10px 14px;margin:12px 0;font-size:.875rem;color:#92400E;">Traitements antérieurs : {medical_data.get("traitement_anterieur")}</div>', unsafe_allow_html=True)

            st.markdown("### Données cliniques")
            c1, c2 = st.columns(2)
            with c1:
                niv = score_data.get("niveau","stable")
                if niv == "urgent": st.error(f"URGENT — {score_data.get('delai','')}")
                elif niv == "semi_urgent": st.warning(f"SEMI-URGENT — {score_data.get('delai','')}")
                else: st.success(f"STABLE — {score_data.get('delai','')}")
                st.markdown("**Facteurs de priorité**")
                for f in score_data.get("facteurs",[]): st.markdown(f"- {f}")
            with c2:
                dec = orientation.get("decision","")
                box = f"**{orientation.get('specialite','')}**\n\nProtocole : {orientation.get('protocole','')}\n\nDélai : {orientation.get('delai','')}"
                if "chirurgie" in dec: st.error(box)
                elif dec == "oncologie": st.warning(box)
                else: st.info(box)
                if orientation.get("rcp_requis"): st.warning("RCP multidisciplinaire requise")

            st.markdown("### Guidelines ESMO 2023")
            esmo = get_esmo_guideline(orientation.get("stage_group","Stage inconnu"))
            st.markdown(f"""<div style="background:#EFF6FF;border-left:4px solid #2F80ED;border-radius:0 8px 8px 0;padding:16px 20px;font-size:.875rem;color:#525252;line-height:1.8;">
<strong>Référence :</strong> {esmo['reference']}<br>
<strong>Chimio :</strong> {esmo['recommandation_chimio']}<br>
<strong>Survie 5 ans :</strong> {esmo['survie_5ans']}<br>
<strong>Surveillance :</strong> {esmo['surveillance']}</div>""", unsafe_allow_html=True)

            st.markdown("### Explainability")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Preuves dans le dossier**")
                for p in explanation.get("preuves_dossier",[]): st.markdown(f"- {p}")
            with c2:
                st.markdown("**Règles cliniques activées**")
                for r in explanation.get("regles_activees",[]): st.markdown(f"- {r}")
            st.markdown(f"**Confiance IA :** {explanation.get('confiance_label','')} — {explanation.get('confiance_explication','')}")
            st.markdown(f"**Raison :** {explanation.get('raison_principale','')}")

            if image_results:
                st.markdown("### Résultats imagerie")
                for ir in image_results:
                    if ir.get("type") == "yolo":
                        yr = ir.get("yolo", {})
                        rr = ir.get("rapport", {})
                        polype = yr.get("polype_detecte", False)
                        conf   = yr.get("confidence_max", 0)
                        risque = yr.get("risque","inconnu").upper()
                        if polype:
                            st.error(f"Lésion détectée — {yr.get('nombre_polypes',0)} polype(s) — Confiance : {conf:.0%} — Risque : {risque}")
                        else:
                            st.success(f"Aucune lésion détectée — Confiance : {conf:.0%}")
                        if rr.get("resume_clinique"):
                            st.markdown(f'<div style="background:#F8FAFC;border-radius:8px;padding:12px 16px;font-size:.875rem;color:#181D27;">{rr.get("resume_clinique","")}</div>', unsafe_allow_html=True)
                    else:
                        reco = get_image_recommendation(ir)
                        st.markdown(f"**{ir.get('filename','')}** — {reco}")

            st.divider()
            st.markdown("### Notes du médecin (optionnel)")
            notes_medecin = st.text_area(
                "Annotations ou corrections",
                value=st.session_state.get("pending_notes",""),
                height=80,
                placeholder="Ajoutez vos observations avant de valider..."
            )
            st.session_state.pending_notes = notes_medecin

            st.divider()
            st.markdown("### Validation médecin")
            st.warning("**Aucune donnée n'est enregistrée avant votre validation.**")

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Valider et enregistrer", type="primary", use_container_width=True):
                    from modules.database import delete_pending_analysis
                    patient_record = {
                        "id": pid,
                        "nom": patient_nom,
                        "type": patient_type,
                        "date_analyse": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "statut": "actif",
                        "score": score_data.get("score",0),
                        "stade": f"{medical_data.get('stade_T','?')}{medical_data.get('stade_N','?')}{medical_data.get('stade_M','?')}",
                        "stage_group": orientation.get("stage_group","Inconnu"),
                        "orientation": orientation.get("decision","incertain"),
                        "delai": orientation.get("delai","À définir"),
                        "urgence": score_data.get("label",""),
                        "docs_count": pa.get("docs_count",0),
                        "images_count": pa.get("images_count",0),
                        "validation_medecin": "validé",
                        "validation_date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "medical_data": {**medical_data, "notes_medecin": notes_medecin},
                        "score_data": score_data,
                        "orientation_data": orientation,
                        "explanation": explanation,
                        "recurrence": recurrence,
                        "validation": validation,
                        "completude": completude,
                        "image_results": [],
                        "fusion": pa.get("fusion",{})
                    }
                    save_patient(patient_record)
                    add_log(pid, "valide_enregistre", f"Score:{score_data.get('score',0)}")
                    delete_pending_analysis(pid)
                    st.session_state.pending_patient_id = None
                    st.session_state.pending_notes = ""
                    st.session_state.current_patient_id = pid
                    st.session_state.app_page = "dossier"
                    st.rerun()
            with c2:
                if st.button("Rejeter et enregistrer", use_container_width=True):
                    from modules.database import delete_pending_analysis
                    patient_record = {
                        "id": pid,
                        "nom": patient_nom,
                        "type": patient_type,
                        "date_analyse": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "statut": "actif",
                        "score": score_data.get("score",0),
                        "stade": f"{medical_data.get('stade_T','?')}{medical_data.get('stade_N','?')}{medical_data.get('stade_M','?')}",
                        "stage_group": orientation.get("stage_group","Inconnu"),
                        "orientation": orientation.get("decision","incertain"),
                        "delai": orientation.get("delai","À définir"),
                        "urgence": score_data.get("label",""),
                        "docs_count": pa.get("docs_count",0),
                        "images_count": pa.get("images_count",0),
                        "validation_medecin": "rejeté",
                        "medical_data": {**medical_data, "notes_medecin": notes_medecin},
                        "score_data": score_data,
                        "orientation_data": orientation,
                        "explanation": explanation,
                        "recurrence": recurrence,
                        "validation": validation,
                        "completude": completude,
                        "image_results": [],
                        "fusion": pa.get("fusion",{})
                    }
                    save_patient(patient_record)
                    add_log(pid, "rejete_enregistre")
                    delete_pending_analysis(pid)
                    st.session_state.pending_patient_id = None
                    st.session_state.pending_notes = ""
                    st.session_state.app_page = "dashboard"
                    st.rerun()
            with c3:
                if st.button("Annuler sans enregistrer", use_container_width=True):
                    from modules.database import delete_pending_analysis
                    delete_pending_analysis(pid)
                    st.session_state.pending_patient_id = None
                    st.session_state.pending_notes = ""
                    st.rerun()

            st.stop()

        # ── FORMULAIRE UPLOAD ──────────────────────────────────────
        c1, c2 = st.columns(2)
        with c1:
            patient_nom = st.text_input("Identifiant patient (anonymisé)", placeholder="Ex: Dossier_2024_001")
        with c2:
            patient_type = st.selectbox("Type de dossier", ["Bilan initial","Post-opératoire","Suivi chimio","Récidive"])

        if not patient_nom:
            st.markdown('<div style="color:#D97706;font-size:.8rem;">Renseignez un identifiant patient pour continuer.</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Documents médicaux** (PDF ou TXT)")
            uploaded_docs = st.file_uploader("docs", type=["pdf","txt"], accept_multiple_files=True, key="docs_new", label_visibility="collapsed")
            if uploaded_docs: st.markdown(f'<div style="font-size:.8rem;color:#059669;">✓ {len(uploaded_docs)} fichier(s)</div>', unsafe_allow_html=True)
        with c2:
            st.markdown("**Images médicales** (JPG/PNG — coloscopie)")
            uploaded_images = st.file_uploader("imgs", type=["jpg","jpeg","png"], accept_multiple_files=True, key="imgs_new", label_visibility="collapsed")
            if uploaded_images: st.markdown(f'<div style="font-size:.8rem;color:#059669;">✓ {len(uploaded_images)} image(s)</div>', unsafe_allow_html=True)

        has_docs = bool(uploaded_docs)
        has_imgs = bool(uploaded_images)

        if patient_nom and (has_docs or has_imgs):
            if has_docs and has_imgs:   scn_label = "Texte + Images (fusion multimodale)"
            elif has_docs:               scn_label = "Texte uniquement"
            else:                        scn_label = "Image uniquement (YOLO)"
            st.markdown(f'<div style="font-size:.85rem;color:#2F80ED;font-weight:500;margin-bottom:8px;">Scénario : {scn_label}</div>', unsafe_allow_html=True)

            if st.button("Lancer l'analyse complète", type="primary", use_container_width=True):
                progress = st.progress(0, "Initialisation...")
                t0 = time.time()
                try:
                    progress.progress(20, "Analyse en cours...")
                    result = run_pipeline(
                        text_files=uploaded_docs if has_docs else None,
                        image_files=uploaded_images if has_imgs else None
                    )
                    progress.progress(100, "Terminé")
                    elapsed = round(time.time() - t0, 2)

                    safe_nom = re.sub(r'[^a-zA-Z0-9_]', '_', patient_nom)
                    pid = f"{safe_nom}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                    result["patient_nom"]  = patient_nom
                    result["patient_type"] = patient_type
                    result["elapsed"]      = elapsed
                    result["docs_count"]   = len(uploaded_docs) if has_docs else 0
                    result["images_count"] = len(uploaded_images) if has_imgs else 0

                    from modules.database import save_pending_analysis
                    save_pending_analysis(pid, result)
                    st.session_state.pending_patient_id = pid
                    st.session_state.pending_notes = ""
                    st.rerun()

                except Exception as e:
                    st.error(f"Erreur pipeline : {str(e)}")
                    st.info("Vérifiez qu'Ollama est démarré : `ollama serve`")

    # ════════════════════════════════
    # DOSSIER PATIENT
    # ════════════════════════════════
    elif st.session_state.app_page == "dossier":

        all_p = get_all_patients()
        if not all_p:
            st.info("Aucun patient. Cliquez sur '+ Ajouter patient'.")
            st.stop()

        options = {
            f"{get_urgency_emoji(p.get('score',0))} {p['nom']} — {p.get('stage_group','?')} — {p.get('score',0)}/100": p["id"]
            for p in all_p
        }
        default_idx = 0
        if st.session_state.current_patient_id:
            vals = list(options.values())
            if st.session_state.current_patient_id in vals:
                default_idx = vals.index(st.session_state.current_patient_id)

        selected_label = st.selectbox("Sélectionner un patient", list(options.keys()), index=default_idx)
        selected_id = options[selected_label]
        patient = get_patient_by_id(selected_id)

        if not patient:
            st.error("Dossier introuvable.")
            st.stop()

        st.session_state.current_patient_id = selected_id

        med = patient.get("medical_data", {})
        score_data = patient.get("score_data", {})
        orientation = patient.get("orientation_data", {})
        explanation = patient.get("explanation", {})
        recurrence = patient.get("recurrence", {})
        val_med = patient.get("validation_medecin", "en_attente")

        col1, col2, col3, col4, col5 = st.columns([4, 1, 1, 1, 1])
        with col1:
            st.markdown(f"""
            <div style="padding:8px 0;">
                <div style="font-size:1.1rem;font-weight:600;color:#181D27;">{patient['nom']}</div>
                <div style="font-size:0.8rem;color:#94A3B8;">{patient.get('type_dossier','?')} • Analysé le {patient.get('date_analyse','?')} • {patient.get('docs_count',0)} doc(s)</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            btn_label = "↺ Actif" if patient.get("statut") == "traite" else "✓ Traité"
            if st.button(btn_label, key="toggle_statut"):
                new_s = "actif" if patient.get("statut") == "traite" else "traite"
                update_patient_status(selected_id, new_s)
                st.rerun()
        with col3:
            if st.button("✏️ Modifier"):
                st.session_state.edit_mode = True
                st.rerun()
        with col4:
            if st.button("🗑 Suppr."):
                st.session_state["confirm_del_dossier"] = True
                st.rerun()
        with col5:
            if val_med == "en_attente":
                if st.button("✅ Valider"):
                    update_validation_medecin(selected_id, "validé")
                    add_log(selected_id, "validation", "validé")
                    st.rerun()

        if st.session_state.get("confirm_del_dossier", False):
            st.warning("⚠️ Supprimer définitivement ?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Confirmer"):
                    delete_patient_db(selected_id)
                    st.session_state.pop("confirm_del_dossier", None)
                    st.session_state.current_patient_id = None
                    st.session_state.app_page = "dashboard"
                    st.rerun()
            with c2:
                if st.button("❌ Annuler"):
                    st.session_state.pop("confirm_del_dossier", None)
                    st.rerun()

        if patient.get("statut") == "traite":
            st.markdown('<span class="badge badge-success">✓ Traitement terminé</span>', unsafe_allow_html=True)

        if val_med == "validé":
            st.markdown(f'<div style="background:#F0FDF4;border:1px solid #A7F3D0;border-radius:8px;padding:10px 14px;margin:8px 0;font-size:0.85rem;color:#065F46;">✅ <strong>Validé par médecin</strong> — {patient.get("validation_date","")}</div>', unsafe_allow_html=True)
        elif val_med == "rejeté":
            st.markdown('<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:10px 14px;margin:8px 0;font-size:0.85rem;color:#DC2626;">❌ <strong>Décision rejetée</strong></div>', unsafe_allow_html=True)

        if st.session_state.get("edit_mode", False):
            st.markdown("---")
            st.markdown("### ✏️ Mode modification")
            edit_resume = st.text_area("Résumé clinique", value=explanation.get("resume_clinique",""), height=100)
            edit_notes = st.text_area("Notes d'orientation médecin", value=orientation.get("notes_medecin",""), height=80)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 Enregistrer", type="primary"):
                    update_patient_notes(selected_id, "resume_clinique", edit_resume)
                    update_patient_notes(selected_id, "orientation_notes", edit_notes)
                    add_log(selected_id, "modification_medecin")
                    st.session_state.edit_mode = False
                    st.rerun()
            with c2:
                if st.button("Annuler"):
                    st.session_state.edit_mode = False
                    st.rerun()

        st.divider()

        st.markdown("## Timeline clinique")
        timeline = []
        if med.get("traitement_anterieur") not in ["aucun","inconnu",None,""]:
            timeline.append(("🔵", f"Traitement antérieur : {med.get('traitement_anterieur')}"))
        timeline.append(("📋", f"Analyse ColoCare MD — {patient.get('date_analyse','?')}"))
        timeline.append(("🎯", f"Orientation : {orientation.get('decision','?')} — {orientation.get('delai','?')}"))
        if orientation.get("rcp_requis"): timeline.append(("📋", "RCP requise"))
        if val_med == "validé": timeline.append(("👨‍⚕️", f"Validé — {patient.get('validation_date','')}"))
        elif val_med == "rejeté": timeline.append(("⚠️", "Décision rejetée"))

        for icon, text in timeline:
            st.markdown(f"""
            <div style="display:flex;gap:12px;margin-bottom:12px;align-items:flex-start;">
                <div style="width:8px;height:8px;border-radius:50%;background:#2F80ED;margin-top:6px;flex-shrink:0;"></div>
                <div style="font-size:0.875rem;color:#525252;">{icon} {text}</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        st.markdown("## Tableau synthétique")
        synth = {
            "Paramètre": ["Stade T","Stade N","Stade M","Stage global","Score priorité","Risque récidive","Confiance IA","Métastases"],
            "Valeur": [
                med.get("stade_T","?"), med.get("stade_N","?"), med.get("stade_M","?"),
                orientation.get("stage_group","?"),
                f"{score_data.get('score',0)}/100",
                recurrence.get("niveau_risque","?"),
                f"{orientation.get('confidence',0)}%",
                "OUI ⚠️" if med.get("metastases") else "NON ✅"
            ],
            "Statut": [
                "✅" if med.get("stade_T","inconnu") not in ["inconnu","?",""] else "⚠️",
                "✅" if med.get("stade_N","inconnu") not in ["inconnu","?",""] else "⚠️",
                "✅" if med.get("stade_M","inconnu") not in ["inconnu","?",""] else "⚠️",
                "✅","✅","✅","✅",
                "⚠️" if med.get("metastases") else "✅"
            ]
        }
        st.dataframe(pd.DataFrame(synth), use_container_width=True, hide_index=True)

        st.divider()
        st.info(explanation.get("resume_clinique",""))

        col1, col2 = st.columns(2)
        with col1:
            niveau = score_data.get("niveau","stable")
            if niveau == "urgent": st.error(f"🔴 URGENT — {score_data.get('delai','')}")
            elif niveau == "semi_urgent": st.warning(f"🟠 SEMI-URGENT — {score_data.get('delai','')}")
            else: st.success(f"🟢 STABLE — {score_data.get('delai','')}")
        with col2:
            decision = orientation.get("decision","")
            box = f"**{orientation.get('specialite','')}**\n\n{orientation.get('protocole','')}\n\nDélai : {orientation.get('delai','')}"
            if "chirurgie" in decision: st.error(box)
            elif decision == "oncologie": st.warning(box)
            else: st.info(box)

        st.markdown("## Guidelines ESMO 2023")
        esmo = get_esmo_guideline(orientation.get("stage_group","Stage inconnu"))
        st.markdown(f"""
        <div style="background:#EFF6FF;border-left:4px solid #2F80ED;border-radius:0 8px 8px 0;padding:16px 20px;">
            <div style="font-weight:600;color:#181D27;margin-bottom:8px;">{esmo['reference']}</div>
            <div style="font-size:0.875rem;color:#525252;line-height:1.8;">
                <strong>Chimio :</strong> {esmo['recommandation_chimio']}<br>
                <strong>Survie 5 ans :</strong> {esmo['survie_5ans']}<br>
                <strong>Surveillance :</strong> {esmo['surveillance']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("## Raisonnement clinique")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Preuves :**")
            for p in explanation.get("preuves_dossier",[]): st.markdown(f"✓ {p}")
        with col2:
            st.markdown("**Règles :**")
            for r in explanation.get("regles_activees",[]): st.markdown(f"⚖️ {r}")
            st.markdown(f"**Raison :** {explanation.get('raison_principale','')}")

        st.divider()
        st.markdown("## Résumé RCP")
        st.markdown('<div style="font-size:0.85rem;color:#525252;margin-bottom:16px;">Assistant préparatoire à la Réunion de Concertation Pluridisciplinaire.</div>', unsafe_allow_html=True)

        if st.button("🏥 Générer résumé RCP", type="primary"):
            ctx_rcp = f"Patient {patient['nom']}, stade {med.get('stade_T','?')}{med.get('stade_N','?')}{med.get('stade_M','?')}, {orientation.get('stage_group','?')}, score {score_data.get('score',0)}/100"
            with st.spinner("Génération..."):
                rcp = ask_gemma(f"""Génère un résumé RCP complet oncologie colorectale.
Données : {ctx_rcp}. Type : {med.get('type_histologique','?')}. Métastases : {med.get('localisation_metastases','aucune')}.
Format : ## 1. Présentation ## 2. Données clés ## 3. Question RCP ## 4. Spécialistes ## 5. Examens ## 6. Recommandation ESMO""")
            st.markdown(rcp)
            st.download_button("⬇️ RCP", data=rcp, file_name=f"rcp_{patient['nom']}.txt", mime="text/plain")

        if val_med == "en_attente":
            st.divider()
            st.markdown("## Validation médecin")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Valider décision", type="primary"):
                    update_validation_medecin(selected_id, "validé")
                    add_log(selected_id, "validation", "validé")
                    st.rerun()
            with col2:
                if st.button("❌ Rejeter"):
                    update_validation_medecin(selected_id, "rejeté")
                    add_log(selected_id, "validation", "rejeté")
                    st.rerun()
            with col3:
                if st.button("✅ Marquer traité"):
                    update_patient_status(selected_id, "traite")
                    add_log(selected_id, "statut", "traite")
                    st.rerun()

    # ════════════════════════════════
    # ASSISTANT CLINIQUE
    # ════════════════════════════════
    elif st.session_state.app_page == "assistant":

        all_p = get_all_patients()
        patient_opts = {"Aucun patient (général)": None}
        patient_opts.update({
            f"{get_urgency_emoji(p.get('score',0))} {p['nom']} — {p.get('stage_group','?')}": p["id"]
            for p in all_p
        })

        sel_label = st.selectbox("Contexte patient", list(patient_opts.keys()))
        sel_id = patient_opts[sel_label]
        ctx = "Aucun patient — réponses génériques."

        if sel_id:
            p = get_patient_by_id(sel_id)
            if p:
                med_ctx = p.get("medical_data", {})
                ctx = (f"Patient : {p['nom']} | Stade : {med_ctx.get('stade_T','?')}{med_ctx.get('stade_N','?')}{med_ctx.get('stade_M','?')} | "
                       f"Stage : {p.get('stage_group','?')} | Score : {p.get('score',0)}/100 | "
                       f"Orientation : {p.get('orientation','?')} | Type : {med_ctx.get('type_histologique','?')} | "
                       f"Métastases : {med_ctx.get('localisation_metastases','aucune')} | "
                       f"Traitements antérieurs : {med_ctx.get('traitement_anterieur','aucun')}")
                st.success(f"📋 Contexte : {p['nom']} — {p.get('stage_group','?')}")
        else:
            st.info("💡 Sélectionnez un patient pour des réponses contextualisées.")

        st.divider()

        for msg in st.session_state.conversation.get("messages", []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if sel_id:
            if st.button("📋 Générer résumé RCP rapide"):
                with st.spinner("Génération RCP..."):
                    rcp = ask_gemma_with_context(
                        f"Génère résumé RCP court : présentation, éléments clés, question RCP, spécialistes.",
                        ctx, st.session_state.langue
                    )
                st.markdown(rcp)
                add_message(st.session_state.conversation, "assistant", f"**RCP:**\n\n{rcp}")
                save_conversation_db(st.session_state.conversation, sel_id or "")
                st.download_button("⬇️ RCP", data=rcp, file_name="resume_rcp.txt", mime="text/plain")

        if question := st.chat_input("Posez votre question en oncologie colorectale..."):
            add_message(st.session_state.conversation, "user", question)
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
                with st.spinner("Analyse..."):
                    hist = get_context_summary(st.session_state.conversation)
                    response = ask_gemma_with_context(question, f"{ctx}\n\nHistorique:\n{hist}", st.session_state.langue)
                st.markdown(response)
            add_message(st.session_state.conversation, "assistant", response)
            save_conversation_db(st.session_state.conversation, sel_id or "")
            st.rerun()