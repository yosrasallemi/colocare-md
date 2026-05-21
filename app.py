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

# ════════════════════════════════════════════════════════════════
# HELPERS — à placer AVANT le bloc elif app
# ════════════════════════════════════════════════════════════════
def _do_save(pid, pa, patient_nom, patient_type, medical_data, score_data,
             orientation, explanation, recurrence, validation, completude,
             notes_medecin, val_status, redirect):
    from modules.database import delete_pending_analysis
    from datetime import datetime
    patient_record = {
        "id": pid, "nom": patient_nom, "type": patient_type,
        "date_analyse": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "statut": "actif",
        "score": score_data.get("score", 0),
        "stade": f"{medical_data.get('stade_T','?')}{medical_data.get('stade_N','?')}{medical_data.get('stade_M','?')}",
        "stage_group": orientation.get("stage_group", "Inconnu"),
        "orientation": orientation.get("decision", "incertain"),
        "delai": orientation.get("delai", "À définir"),
        "urgence": score_data.get("label", ""),
        "docs_count": pa.get("docs_count", 0),
        "images_count": pa.get("images_count", 0),
        "validation_medecin": val_status,
        "validation_date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "medical_data": {**medical_data, "notes_medecin": notes_medecin},
        "score_data": score_data,
        "orientation_data": orientation,
        "explanation": explanation,
        "recurrence": recurrence,
        "validation": validation,
        "completude": completude,
        "image_results": [],   # images jamais stockées
        "fusion": pa.get("fusion", {})
    }
    save_patient(patient_record)
    add_log(pid, f"{val_status}_enregistre", f"Score:{score_data.get('score',0)}")
    delete_pending_analysis(pid)
    st.session_state.pending_patient_id = None
    st.session_state.pending_notes = ""
    if redirect == "dossier":
        st.session_state.current_patient_id = pid
        st.session_state.app_page = "dossier"
    else:
        st.session_state.app_page = "dashboard"
    st.rerun()

_save_patient_and_redirect = _do_save 
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
if "app_page" not in st.session_state:
    st.session_state.app_page = "dashboard"
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
if "pending_patient_id" not in st.session_state:
    st.session_state.pending_patient_id = None
if "pending_notes" not in st.session_state:
    st.session_state.pending_notes = ""
if "langue" not in st.session_state:
    st.session_state.langue = "Français"
 
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

#-------- Assistant clinique ----------------# 


elif st.session_state.current_page == "app":

    
    import base64 
    import base64 as _b64

    def icon_b64(path: str) -> str:
        if not os.path.exists(path):
            return ""
        ext = path.split(".")[-1].lower()
        mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
        with open(path, "rb") as f:
            return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"
    ico_chat   = icon_b64("assets/icons/chat.png")
    ico_ajout  = icon_b64("assets/icons/ajout.svg")
    
    # ── helpers icônes ──────────────────────────────────────────
    def _icon(name, w=18, h=18, style=""):
        path = f"assets/icons/{name}"
        if not os.path.exists(path):
            return ""
        ext = path.split(".")[-1].lower()
        mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
        with open(path, "rb") as f:
            b64 = _b64.b64encode(f.read()).decode()
        return f'<img src="data:{mime};base64,{b64}" width="{w}" height="{h}" style="vertical-align:middle;{style}">'

    # ── Session state guards ─────────────────────────────────────
    if "pending_patient_id" not in st.session_state:
        st.session_state.pending_patient_id = None
    if "pending_notes" not in st.session_state:
        st.session_state.pending_notes = ""
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False

    # ── Urgents count ────────────────────────────────────────────
    all_patients_global = get_all_patients()
    urgents_count = len([
        p for p in all_patients_global
        if p.get("score", 0) >= 70 and p.get("statut") == "actif"
    ])

    # ════════════════════════════════════════════════════════════
    # CSS
    # ════════════════════════════════════════════════════════════
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Poppins:wght@500;600;700&display=swap');

    html,body,.stApp { background:#FAFAFA !important; }
    #MainMenu,footer,header,.stDeployButton { visibility:hidden !important; display:none !important; }
    .block-container { padding:0 !important; max-width:100% !important; }

    /* ── SIDEBAR always visible ── */
    section[data-testid="stSidebar"] {
        position:fixed !important;
        top:0 !important; left:0 !important;
        height:100vh !important;
        width:220px !important;
        min-width:220px !important;
        background:#FFFFFF !important;
        border-right:1px solid #F0F0F0 !important;
        box-shadow:none !important;
        z-index:1000 !important;
        overflow-y:auto !important;
        overflow-x:hidden !important;
        display:block !important;
        visibility:visible !important;
        opacity:1 !important;
        transform:none !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding:0 !important;
        width:220px !important;
    }
    /* Force sidebar visible even when collapsed */
    section[data-testid="stSidebar"][aria-expanded="false"] {
        width:220px !important;
        min-width:220px !important;
        display:block !important;
        visibility:visible !important;
        transform:none !important;
        left:0 !important;
    }
    [data-testid="collapsedControl"] {
        display:none !important;
    }

   /* Sidebar buttons normal */
   section[data-testid="stSidebar"] .stButton > button{

    opacity:1 !important;
    position:relative !important;
    width:100% !important;

    margin-top:0 !important;
    padding:6px !important;

    background:transparent !important;
    border:none !important;

    box-shadow:none !important;
    }

    /* ── Gap sidebar ── */
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:0 !important; }
    section[data-testid="stSidebar"] [data-testid="element-container"] { margin:0 !important; padding:0 !important; }

    /* ── Bouton primary ── */
    [data-testid="baseButton-primary"] {
        background:#2F80ED !important;
        color:white !important;
        border:none !important;
        border-radius:8px !important;
        padding:7px 14px !important;
        font-family:'Inter',sans-serif !important;
        font-size:.82rem !important;
        font-weight:500 !important;
        box-shadow:0 1px 4px rgba(47,128,237,.2) !important;
        opacity:1 !important;
        position:relative !important;
    }
    [data-testid="baseButton-primary"]:hover { background:#1a6fd4 !important; }

    /* ── Boutons contenu principal ── */
    .stButton > button {
        background:#FFFFFF !important;
        border:1px solid #ECEEF2 !important;
        border-radius:8px !important;
        padding:6px 14px !important;
        font-family:'Inter',sans-serif !important;
        font-size:.82rem !important;
        color:#1A1A2E !important;
        font-weight:400 !important;
        box-shadow:none !important;
        opacity:1 !important;
        position:relative !important;
        transition:background .15s !important;
    }
    .stButton > button:hover {
        background:#F5F5F5 !important;
        border-color:#D1D5DB !important;
    }
    
    .navbar{
      min-height:65px !important;
      padding:8px 20px !important;
    }
    /* ── inputs ── */
    .stTextInput>div>div,.stSelectbox>div>div,.stTextArea>div>div {
        border-radius:8px !important;
        border-color:#E8EDF2 !important;
        background:#FFFFFF !important;
        font-family:'Inter',sans-serif !important;
        font-size:.875rem !important;
    }

    /* ── metrics ── */
    [data-testid="stMetric"] {
        background:#FFFFFF !important;
        border:1px solid #F0F0F0 !important;
        border-radius:10px !important;
        padding:14px 16px !important;
    }
    [data-testid="stMetricLabel"] { font-size:.68rem !important; text-transform:uppercase; letter-spacing:.06em; color:#8A8A8A !important; font-weight:500 !important; }
    [data-testid="stMetricValue"] { font-size:1.2rem !important; font-weight:600 !important; color:#1A1A2E !important; }

    /* ── alerts ── */
    [data-testid="stAlert"] { border-radius:8px !important; font-size:.82rem !important; font-family:'Inter',sans-serif !important; }

    hr { border-color:#F0F0F0 !important; margin:12px 0 !important; }
    .stChatMessage { background:#FFFFFF !important; border:1px solid #F0F0F0 !important; border-radius:8px !important; }

    /* ── patient cards ── */
    .patient-card {
        background:#FFFFFF; border:1px solid #F0F0F0; border-radius:10px;
        padding:14px 18px; margin-bottom:8px; font-family:'Inter',sans-serif;
    }
    .patient-card.urgent      { border-left:3px solid #DC2626; }
    .patient-card.semi-urgent { border-left:3px solid #D97706; }
    .patient-card.stable      { border-left:3px solid #059669; }

    .badge { display:inline-block; padding:2px 8px; border-radius:20px; font-size:.7rem; font-weight:500; }
    .badge-urgent  { background:#FEE2E2; color:#DC2626; }
    .badge-success { background:#D1FAE5; color:#059669; }
    .badge-info    { background:#EEF5FD; color:#2F80ED; }

    /* ── rapport ── */
    .report-section { background:#FFFFFF; border:1px solid #F0F0F0; border-radius:10px; padding:18px 22px; margin-bottom:12px; font-family:'Inter',sans-serif; }
    .report-label { font-size:.68rem; font-weight:600; text-transform:uppercase; letter-spacing:.08em; color:#8A8A8A; margin-bottom:8px; }
    .report-value { font-size:.875rem; color:#1A1A2E; line-height:1.7; }
    .esmo-block { background:#F8FBFF; border-left:3px solid #2F80ED; border-radius:0 8px 8px 0; padding:12px 16px; font-size:.82rem; color:#525252; line-height:1.8; margin:8px 0; }
    .section-label { font-size:.72rem; font-weight:600; text-transform:uppercase; letter-spacing:.08em; color:#8A8A8A; margin:16px 0 6px; }

    section[data-testid="stMain"]{
      margin-left:220px !important;
      width:calc(100vw - 220px) !important;
      max-width:calc(100vw - 220px) !important;
      overflow-x:hidden !important;
      background:#FFFFFF !important;
      padding:0 !important;
    }

    
    /* largeur contenu */
    section[data-testid="stMain"] .block-container{
      max-width:calc(100vw - 260px) !important;
      overflow-x:hidden !important;
    }

    /* colonnes */
    [data-testid="column"]{
      min-width:0 !important;
       flex:1 1 auto !important;
    }

    /* selectbox */
    .stSelectbox{
      width:100% !important;
    }

    /* espace intérieur des pages */
     section[data-testid="stMain"] > div{
      padding:8px 24px 24px 24px !important;
      background:#FFFFFF !important;
    }

    /* contenu principal */
    .block-container{
      max-width:100% !important;
      padding:8px 20px 20px 20px !important;
      background:#FFFFFF !important;
    }

    /* conteneur page */
    .page-container{
      background:#FFFFFF !important;
      padding:24px !important;
      margin-top:0px !important;
      padding-top:8px !important;         
      border-radius:12px;
      margin:8px 12px 24px 12px;
    }
    div[data-testid="stVerticalBlock"]{
      gap:10px !important;
    }
                  
    /* évite que la dernière colonne sorte */
    div[data-testid="stHorizontalBlock"]{
      width:100% !important;
      gap:18px !important;
    }

    
                           
    ::-webkit-scrollbar { width:4px; }
    ::-webkit-scrollbar-thumb { background:#E8EDF2; border-radius:2px; }
    </style>
    """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════
    # SIDEBAR
    # ════════════════════════════════════════════════════════════
    # Colle ce st.markdown JUSTE AVANT la sidebar (with st.sidebar:)
    st.markdown("""
    <style>
    /* Fix page assistant — même offset que les autres pages */
    section[data-testid="stMain"] {
        margin-left: 220px !important;
        width: calc(100vw - 220px) !important;
        max-width: calc(100vw - 220px) !important;
        overflow-x: hidden !important;
    }
    section[data-testid="stMain"] > div {
        padding: 8px 24px 24px 24px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    with st.sidebar:
        logo_p = "assets/logos/logo.png"
        # Logo
        st.markdown('<div style="display:flex; justify-content:center; align-items:center; margin-top:-65px;margin-left:12px; margin-bottom:0px;padding:0;"> ''', unsafe_allow_html=True)
        
        if os.path.exists(logo_p):
              st.image(
            logo_p,
            width=250,
            use_container_width=False )
        else:
            st.markdown('<span style="font-family:Poppins,sans-serif;font-size:1rem;font-weight:700;color:#2F80ED;">ColoCare MD</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<hr style="margin:4px 16px 10px;border-color:#F0F0F0;">',unsafe_allow_html=True )

        icon_home    = _icon("home.png",    16, 16, "margin-right:8px;opacity:.65;")
        icon_dossier = _icon("dossier.png", 16, 16, "margin-right:8px;opacity:.65;")

        # ── Home ──────────────────────────────────────────────
        # ── Home ─────────────────────────────

        is_home = st.session_state.app_page == "dashboard"

        label = "🏠 Home"
        if is_home:
          label = "🏠 Home"

        if st.button(
         label,
         key="nav_dashboard_real",
        use_container_width=True
        ):
         st.session_state.app_page = "dashboard"
         st.rerun()


        # ── Dossier patient ────────────────────────────────────
        is_dos = st.session_state.app_page == "dossier"
        dos_bg = "background:#EEF5FD;border-radius:7px;" if is_dos else ""
        dos_c  = "color:#2F80ED;font-weight:500;" if is_dos else "color:#1A1A2E;font-weight:400;"
        st.markdown(f"""
        <div style="position:relative;padding:0 10px;margin-bottom:2px;">
            <div style="display:flex;align-items:center;padding:8px 10px;{dos_bg}border-radius:7px;cursor:pointer;">
                {icon_dossier}
                <span style="font-family:'Inter',sans-serif;font-size:.855rem;{dos_c}">Dossier patient</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("", key="nav_dossier_real", use_container_width=True):
            st.session_state.app_page = "dossier"
            st.rerun()

        st.markdown('<hr style="margin:6px 16px;border-color:#F0F0F0;">', unsafe_allow_html=True)

        # ── Assistant clinique ─────────────────────────────────
    
        col_lbl, col_plus = st.columns([5, 1])
        with col_lbl:
            # Label non cliquable
            st.markdown('<p style="font-size:0.7rem;font-weight:600;color:#8A8FA3;text-transform:uppercase;letter-spacing:0.06em;margin:0;padding:4px 0 2px 0;">Assistant clinique</p>', unsafe_allow_html=True)
        with col_plus:
            # Icône ＋ cliquable → nouvelle conversation
            if ico_ajout:
                st.markdown(f'<div style="padding-top:4px;cursor:pointer;"><img src="{ico_ajout}" style="width:14px;height:14px;opacity:0.55;"></div>', unsafe_allow_html=True)
            if st.button("＋", key="new_conv_sb"):
                save_conversation_db(st.session_state.conversation)
                st.session_state.conversation = create_conversation()
                st.session_state.app_page = "assistant"
                st.rerun()

        # ── Liste conversations — icône + nom, sans boutons visibles ──
        saved_convs = get_all_conversations_db()
        for i, conv in enumerate(saved_convs[:6]):
            is_active_conv = conv["id"] == st.session_state.conversation.get("id", "")
            short_title = conv['titre'][:18] + "…" if len(conv['titre']) > 18 else conv['titre']

            chat_ico = f'<img src="{ico_chat}" style="width:14px;height:14px;margin-right:7px;vertical-align:middle;opacity:{"0.9" if is_active_conv else "0.5"}">' if ico_chat else "💬 "

            col_cv, col_del = st.columns([5, 1])
            with col_cv:
                st.markdown(f"""
                <div style="display:flex;align-items:center;padding:5px 8px;border-radius:7px;
                    background:{'#EEF2FF' if is_active_conv else 'transparent'};
                    cursor:pointer;margin-bottom:1px;">
                    {chat_ico}
                    <span style="font-size:0.78rem;color:{'#3B82F6' if is_active_conv else '#1E1E1E'};
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100px;">
                        {short_title}
                    </span>
                </div>
                """, unsafe_allow_html=True)
                if st.button(short_title, key=f"cv_{conv['id']}", use_container_width=True):
                    save_conversation_db(st.session_state.conversation)
                    st.session_state.conversation = conv
                    st.session_state.app_page = "assistant"
                    st.rerun()
            with col_del:
                if st.button("×", key=f"del_cv_{conv['id']}"):
                    delete_conversation_db(conv["id"])
                    st.rerun()

        st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
        st.markdown('<hr style="border-color:#ECEEF2;margin:6px 0;">', unsafe_allow_html=True)


        st.markdown(
           """
           <div style="
             position:fixed; bottom:15px; left:12px; width:190px;padding:0; z-index:999;
            ">

           <div style="
             background:#F8F8F8;
             border-radius:12px;
             padding:14px;
             box-sizing:border-box;
           ">

           <div style="
             font-family:Inter,sans-serif;
             font-size:.78rem;
             font-weight:600;
             color:#1A1A2E;
            margin-bottom:6px;
           ">
            Attention </div>

          <div style="
            font-family:Inter,sans-serif; font-size:.72rem; color:#8A8A8A; line-height:1.6;margin-bottom:12px;">
            AI decision support only.
            Le médecin valide toujours. </div> """,

        unsafe_allow_html=True
        )


        st.markdown("</div></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════
    # NAVBAR — titre + notif + bouton dans la barre
    # ════════════════════════════════════════════════════════════
    
    nav_col1, nav_col2 = st.columns([6,2])

    with nav_col1:

      page_titles = {
        "dashboard": "Dashboard",
        "dossier": "Dossier patient",
        "assistant": "Assistant clinique",
        "nouveau": "Nouveau patient",
       }

      st.markdown(f"""
      <div style="
        background:#FFFFFF;
        border-bottom:1px solid #ECEEF2;
        padding:12px 24px;
        border-radius:10px 0 0 0;
        min-height:55px;
        display:flex;
        align-items:center;
      ">
        <span style="
            font-family:Poppins,sans-serif;
            font-size:.92rem;
            font-weight:400;
            color:#1E1E1E;
        ">
        {page_titles.get(st.session_state.app_page,'ColoCare MD')}
        </span>
      </div>
      """, unsafe_allow_html=True)


    with nav_col2:

      nav_r1, nav_r2 = st.columns([1,3])

    with nav_r1:

        notif_html = _icon("notif.png",18,18)

        badge=""

        if urgents_count > 0:
            badge = (
             f'<div style="'
             f'position:absolute;'
             f'top:-6px;'
             f'right:-6px;'
             f'background:#EF4444;'
             f'color:white;'
             f'border-radius:50%;'
             f'width:16px;'
             f'height:16px;'
             f'font-size:9px;'
             f'font-weight:700;'
             f'display:flex;'
             f'align-items:center;'
             f'justify-content:center;'
             f'">{urgents_count}</div>'
            
            )

        st.markdown(f"""
        <div style="
           background:#FFFFFF;
           border-bottom:1px solid #ECEEF2;
           min-height:55px;
           display:flex;
           align-items:flex-start;
           justify-content:flex-end;
           padding-top:8px;
           padding-right:16px;
        ">

        <div style="
            position:relative;
            padding:6px;
            cursor:pointer;
        ">
            {notif_html}
            {badge}
        </div>

        </div>
        """, unsafe_allow_html=True)

    with nav_r2:

        st.markdown(
        '<div style="padding-top:4px;">',
        unsafe_allow_html=True
        )

        if st.button(
            "＋ Ajouter patient",
            key="add_patient_top"
        ):
            st.session_state.app_page="nouveau"
            st.rerun()

        st.markdown("</div>",unsafe_allow_html=True)

    st.markdown(
    "<div style='height:10px'></div>",
    unsafe_allow_html=True
    )

    st.markdown(
    '<div style="padding:0 24px;">',
    unsafe_allow_html=True
    )


    # ════════════════════════════════════════════════════════════
    # PAGES — wrapper avec padding
    # ════════════════════════════════════════════════════════════
    st.markdown('<div class="page-container">', unsafe_allow_html=True)

    # ════════════════════════════════
    # DASHBOARD
    # ════════════════════════════════
    if st.session_state.app_page == "dashboard":

        col1, col2, col3, col4 = st.columns(4)
        with col1: filtre_statut  = st.selectbox("Statut",     ["actif","traite","tous"],                                                                    key="f_statut")
        with col2: filtre_urgence = st.selectbox("Urgence",    ["tous","urgent","semi_urgent","stable"],                                                     key="f_urg")
        with col3: filtre_stage   = st.selectbox("Stage",      ["tous","Stage I","Stage II","Stage III","Stage IV"],                                         key="f_stage")
        with col4: filtre_orient  = st.selectbox("Spécialité", ["tous","chirurgie","chirurgie_chimio","chirurgie_urgente","oncologie","incertain"],           key="f_orient")

        patients = get_all_patients(filtre_statut if filtre_statut != "tous" else None)
        if filtre_urgence != "tous":
            lo, hi = {"urgent":(70,100),"semi_urgent":(40,69),"stable":(0,39)}[filtre_urgence]
            patients = [p for p in patients if lo <= p.get("score",0) <= hi]
        if filtre_stage  != "tous": patients = [p for p in patients if p.get("stage_group") == filtre_stage]
        if filtre_orient != "tous": patients = [p for p in patients if p.get("orientation") == filtre_orient]

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        if not patients:
            st.markdown('<div style="text-align:center;padding:80px 0;color:#8A8A8A;font-family:Inter,sans-serif;font-size:.9rem;">Aucun patient — cliquez sur Ajouter patient.</div>', unsafe_allow_html=True)
        else:
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Total patients", len(patients))
            with c2: st.metric("En attente", len([p for p in patients if p.get("validation_medecin")=="en_attente"]))
            with c3: st.metric("Traités",    len([p for p in patients if p.get("statut")=="traite"]))

            if len(patients) > 1:
                scores = [p.get("score",0) for p in patients]
                noms   = [p.get("nom","?")[:10] for p in patients]
                colors = ["#DC2626" if s>=70 else "#D97706" if s>=40 else "#059669" for s in scores]
                fig = go.Figure(go.Bar(x=noms,y=scores,marker_color=colors,marker_line_width=0,text=scores,textposition="outside"))
                fig.update_layout(plot_bgcolor="white",paper_bgcolor="white",font_family="Inter",
                    yaxis_range=[0,115],height=180,margin=dict(t=8,b=8,l=8,r=8),showlegend=False,
                    xaxis=dict(showgrid=False),yaxis=dict(showgrid=True,gridcolor="#F5F5F5"))
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            for patient in patients:
                score  = patient.get("score", 0)
                uc     = get_urgency_class(score)
                emoji  = get_urgency_emoji(score)
                val    = patient.get("validation_medecin","en_attente")
                is_t   = patient.get("statut") == "traite"
                vbadge = '<span class="badge badge-success">Validé</span>'  if val=="validé" else \
                         '<span class="badge badge-urgent">Rejeté</span>'   if val=="rejeté" else \
                         '<span class="badge badge-info">En attente</span>'
                tbadge = '<span class="badge badge-success">Traité</span>'  if is_t else ""

                st.markdown(f"""
                <div class="patient-card {uc}">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                      <div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;">
                        <span style="font-size:.82rem;">{emoji}</span>
                        <span style="font-weight:500;font-size:.88rem;color:#1A1A2E;">{patient.get('nom','?')}</span>
                        <code style="background:#F5F5F5;padding:1px 7px;border-radius:4px;font-size:.72rem;color:#2F80ED;">{patient.get('stade','?')}</code>
                        <span style="font-size:.75rem;color:#8A8A8A;">{patient.get('stage_group','?')}</span>
                      </div>
                      <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
                        {vbadge} {tbadge}
                        <span style="font-size:.75rem;color:#525252;">Score <strong>{score}/100</strong> • {patient.get('delai','?')}</span>
                        <span style="font-size:.72rem;color:#8A8A8A;">{patient.get('date_analyse','?')}</span>
                      </div>
                    </div>
                    <span style="font-size:.72rem;color:#8A8A8A;">{patient.get('orientation','?')}</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                ca, cb, cc, cd = st.columns([4, 1, 1, 1])
                with cb:
                    if st.button("Ouvrir", key=f"open_{patient['id']}"):
                        st.session_state.current_patient_id = patient["id"]
                        st.session_state.app_page = "dossier"
                        st.rerun()
                with cc:
                    if not is_t:
                        if st.button("Traité", key=f"t_{patient['id']}"):
                            update_patient_status(patient["id"], "traite")
                            add_log(patient["id"], "marque_traite")
                            st.rerun()
                with cd:
                    if st.button("Suppr.", key=f"d_{patient['id']}"):
                        st.session_state[f"confirm_{patient['id']}"] = True
                        st.rerun()
                if st.session_state.get(f"confirm_{patient['id']}", False):
                    x1, x2 = st.columns(2)
                    with x1:
                        if st.button("Confirmer", key=f"y_{patient['id']}"):
                            delete_patient_db(patient["id"])
                            st.session_state.pop(f"confirm_{patient['id']}", None)
                            st.rerun()
                    with x2:
                        if st.button("Annuler", key=f"n_{patient['id']}"):
                            st.session_state.pop(f"confirm_{patient['id']}", None)
                            st.rerun()

    # ════════════════════════════════
    # NOUVEAU PATIENT
    # ════════════════════════════════
    elif st.session_state.app_page == "nouveau":

        from datetime import datetime
        import re

        # ── RÉSULTATS EN ATTENTE ─────────────────────────────────
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
            scenario      = pa.get("scenario", "text")

            is_image_only = (scenario == "image_only")

            st.markdown(f'<div style="font-size:.75rem;color:#8A8A8A;margin-bottom:10px;">Patient : {patient_nom} • Analyse terminée ({elapsed}s)</div>', unsafe_allow_html=True)

            # ════════════════════════════════════════════════════
            # SCÉNARIO IMAGE UNIQUEMENT
            # ════════════════════════════════════════════════════
            if is_image_only:
                st.info("Analyse basée sur imagerie uniquement. Aucun document clinique fourni.")

                if image_results:
                    for ir in image_results:
                        yolo_r    = ir.get("yolo", ir)
                        rapport_r = ir.get("rapport", {})
                        polype    = yolo_r.get("polype_detecte", False)
                        conf      = yolo_r.get("confidence_max", 0)
                        risque    = yolo_r.get("risque", "inconnu")
                        fname     = ir.get("filename", "image")
                        detections = yolo_r.get("detections", [])

                        st.markdown(f'<div style="font-size:.82rem;font-weight:500;color:#525252;margin-bottom:8px;">{fname}</div>', unsafe_allow_html=True)

                        # ── Image annotée YOLO ──────────────────
                        annotated_path = ir.get("annotated_path", "")
                        original_path  = ir.get("original_path", "")

                        if annotated_path and os.path.exists(annotated_path):
                            st.markdown('<div class="section-label">Détection YOLO — Image annotée</div>', unsafe_allow_html=True)
                            col_img1, col_img2 = st.columns(2)
                            with col_img1:
                                st.markdown('<div style="font-size:.72rem;color:#8A8A8A;margin-bottom:4px;">Image originale</div>', unsafe_allow_html=True)
                                if original_path and os.path.exists(original_path):
                                    st.image(original_path, use_container_width=True)
                            with col_img2:
                                st.markdown('<div style="font-size:.72rem;color:#8A8A8A;margin-bottom:4px;">Détections YOLO</div>', unsafe_allow_html=True)
                                st.image(annotated_path, use_container_width=True)
                        elif original_path and os.path.exists(original_path):
                            st.markdown('<div class="section-label">Image analysée</div>', unsafe_allow_html=True)
                            st.image(original_path, use_container_width=True)

                        # Bounding boxes info
                        if detections:
                            st.markdown('<div class="section-label">Détections</div>', unsafe_allow_html=True)
                            for det in detections:
                                det_conf  = det.get("confidence", 0)
                                det_class = det.get("class_name", "lésion")
                                st.markdown(f'<div style="font-size:.82rem;color:#525252;padding:3px 0;">· {det_class} — Confiance : <strong>{det_conf:.0%}</strong></div>', unsafe_allow_html=True)

                        c1, c2, c3 = st.columns(3)
                        with c1: st.metric("Lésion détectée", "OUI" if polype else "NON")
                        with c2: st.metric("Confiance max", f"{conf:.0%}" if conf > 0 else "—")
                        with c3: st.metric("Niveau de risque", risque.upper() if risque != "inconnu" else "—")

                        # Rapport Gemma
                        if rapport_r.get("resume_clinique"):
                            st.markdown('<div class="report-section"><div class="report-label">Analyse Gemma 4</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="report-value">{rapport_r.get("resume_clinique","")}</div>', unsafe_allow_html=True)
                            if rapport_r.get("recommandations_specialiste"):
                                st.markdown('<div style="margin-top:10px;"><div class="report-label">Orientation suggérée</div>', unsafe_allow_html=True)
                                for reco in rapport_r.get("recommandations_specialiste", []):
                                    st.markdown(f'<div style="font-size:.82rem;color:#525252;">→ {reco}</div>', unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True)
                            examen = rapport_r.get("examen_complementaire","")
                            if examen:
                                st.markdown(f'<div style="margin-top:6px;font-size:.82rem;color:#525252;"><strong>Examen complémentaire :</strong> {examen}</div>', unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)

                        st.markdown('<div style="font-size:.72rem;color:#8A8A8A;font-style:italic;margin-top:8px;padding:10px 14px;background:#F8F8F8;border-radius:6px;">Ce système fournit une aide à la décision basée sur l\'imagerie. Un bilan clinique complet est requis pour tout diagnostic.</div>', unsafe_allow_html=True)
                else:
                    st.warning("Aucun résultat d'imagerie disponible.")

                st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
                st.markdown('<div class="section-label">Notes du médecin</div>', unsafe_allow_html=True)
                notes_medecin = st.text_area("", value=st.session_state.get("pending_notes",""),
                    height=70, placeholder="Observations avant validation...", label_visibility="collapsed")
                st.session_state.pending_notes = notes_medecin

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                st.markdown('<div class="section-label">Validation</div>', unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("Valider et enregistrer", type="primary", use_container_width=True, key="val_img"):
                        _do_save(pid, pa, patient_nom, patient_type, medical_data, score_data,
                                 orientation, explanation, recurrence, validation, completude,
                                 notes_medecin, "validé", "dossier")
                with c2:
                    if st.button("Rejeter", use_container_width=True, key="rej_img"):
                        _do_save(pid, pa, patient_nom, patient_type, medical_data, score_data,
                                 orientation, explanation, recurrence, validation, completude,
                                 notes_medecin, "rejeté", "dashboard")
                with c3:
                    if st.button("Annuler", use_container_width=True, key="ann_img"):
                        from modules.database import delete_pending_analysis
                        delete_pending_analysis(pid)
                        st.session_state.pending_patient_id = None
                        st.session_state.pending_notes = ""
                        st.rerun()
                st.stop()

            # ════════════════════════════════════════════════════
            # SCÉNARIO TEXTE (± images)
            # ════════════════════════════════════════════════════
            st.info("Résultats en attente de validation. Aucune donnée n'est enregistrée avant votre confirmation.")

            vs = validation.get("status","")
            if vs == "non_confirme": st.error(validation.get('message',''))
            elif vs == "suspect":    st.warning(validation.get('message',''))
            else:                    st.success(validation.get('message',''))

            ct  = completude.get("taux_completude", 0)
            fib = completude.get("fiabilite","")
            if fib == "faible":   st.error(f"Complétude : {ct}% — Manquants : {', '.join(completude.get('champs_manquants',[]))}")
            elif fib == "modérée": st.warning(f"Complétude : {ct}%")
            else:                  st.success(f"Complétude : {ct}%")

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Score priorité", f"{score_data.get('score',0)}/100")
            with c2: st.metric("TNM", f"{medical_data.get('stade_T','?')}{medical_data.get('stade_N','?')}{medical_data.get('stade_M','?')}")
            with c3: st.metric("Stage", orientation.get("stage_group","?"))
            with c4: st.metric("Confiance IA", f"{orientation.get('confidence',0)}%")

            st.divider()

            # ── RAPPORT MÉDICAL ──────────────────────────────────
            st.markdown('<div class="section-label">Rapport clinique</div>', unsafe_allow_html=True)

            # Section A
            st.markdown('<div class="report-section"><div class="report-label">Section A — Données cliniques du patient</div>', unsafe_allow_html=True)
            resume = explanation.get("resume_clinique","Non disponible")
            st.markdown(f'<div class="report-value" style="margin-bottom:10px;">{resume}</div>', unsafe_allow_html=True)
            preuves = explanation.get("preuves_dossier",[])
            if preuves:
                st.markdown('<div style="font-size:.72rem;font-weight:600;color:#8A8A8A;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Éléments identifiés</div>', unsafe_allow_html=True)
                for p in preuves:
                    st.markdown(f'<div style="font-size:.82rem;color:#525252;padding:2px 0;">· {p}</div>', unsafe_allow_html=True)
            if medical_data.get("traitement_anterieur") not in ["aucun","inconnu",None,""]:
                st.markdown(f'<div style="margin-top:6px;font-size:.82rem;color:#D97706;"><strong>Traitements antérieurs :</strong> {medical_data.get("traitement_anterieur")}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Section B
            stage_g  = orientation.get("stage_group","Stage inconnu")
            decision = orientation.get("decision","incertain")
            rcp_pts  = []
            if medical_data.get("metastases"): rcp_pts.append("Évaluation de la résécabilité des métastases")
            if stage_g in ["Stage III","Stage IV"]: rcp_pts.append("Indication et protocole de chimiothérapie adjuvante")
            if decision == "chirurgie_urgente": rcp_pts.append("Urgence chirurgicale — décision opératoire immédiate")
            if orientation.get("rcp_requis"): rcp_pts.append("Validation multidisciplinaire de la stratégie thérapeutique")
            if not rcp_pts: rcp_pts.append("Discussion de la stratégie de surveillance post-thérapeutique")

            st.markdown('<div class="report-section"><div class="report-label">Section B — Points de discussion RCP</div>', unsafe_allow_html=True)
            for pt in rcp_pts:
                st.markdown(f'<div style="font-size:.82rem;color:#525252;padding:2px 0;">· {pt}</div>', unsafe_allow_html=True)
            spec = orientation.get("specialite","")
            if spec: st.markdown(f'<div style="margin-top:6px;font-size:.82rem;color:#2F80ED;font-weight:500;">Spécialité recommandée : {spec}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Section C
            protocole = orientation.get("protocole","")
            delai     = orientation.get("delai","")
            regles    = explanation.get("regles_activees",[])

            st.markdown('<div class="report-section"><div class="report-label">Section C — Recommandations thérapeutiques</div>', unsafe_allow_html=True)
            if protocole:
                st.markdown(f"""
                <div style="background:#F8FBFF;border-radius:8px;padding:12px 14px;margin-bottom:8px;">
                    <div style="font-size:.72rem;font-weight:600;color:#2F80ED;margin-bottom:3px;">Recommandation :</div>
                    <div style="font-size:.85rem;color:#1A1A2E;font-weight:500;">{protocole}</div>
                    <div style="font-size:.72rem;color:#8A8A8A;margin-top:6px;">Preuves : {", ".join(regles[:3]) if regles else "Voir section A"}</div>
                    <div style="font-size:.75rem;color:#8A8A8A;margin-top:4px;">Délai : {delai}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown('<div style="font-size:.82rem;color:#8A8A8A;font-style:italic;">Informations insuffisantes. Consultation RCP requise.</div>', unsafe_allow_html=True)
            rr = recurrence.get("risk_score",0)
            nr = recurrence.get("niveau_risque","Non calculé")
            st.markdown(f'<div style="margin-top:8px;font-size:.82rem;color:#525252;"><strong>Risque de récidive estimé :</strong> {nr} ({rr}/100)</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Section D — ESMO
            from modules.rules_engine import get_esmo_guideline
            esmo = get_esmo_guideline(stage_g)
            st.markdown(f"""
            <div class="report-section">
                <div class="report-label">Section D — Recommandations ESMO 2023 (information générale)</div>
                <div style="font-size:.72rem;color:#8A8A8A;font-style:italic;margin-bottom:8px;">Ces recommandations sont génériques et ne se substituent pas à l'évaluation clinique personnalisée.</div>
                <div class="esmo-block">
                    <strong>Référence :</strong> {esmo['reference']}<br>
                    <strong>Chimio :</strong> {esmo['recommandation_chimio']}<br>
                    <strong>Survie 5 ans :</strong> {esmo['survie_5ans']}<br>
                    <strong>Surveillance :</strong> {esmo['surveillance']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Images si présentes
            if image_results:
                st.markdown('<div class="report-section"><div class="report-label">Résultats imagerie</div>', unsafe_allow_html=True)
                for ir in image_results:
                    yr   = ir.get("yolo", ir)
                    rr2  = ir.get("rapport", {})
                    pol  = yr.get("polype_detecte", False)
                    conf = yr.get("confidence_max", 0)
                    if pol:
                        st.markdown(f'<div style="font-size:.82rem;color:#DC2626;">Lésion détectée — {yr.get("nombre_polypes",0)} polype(s) — Confiance {conf:.0%}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div style="font-size:.82rem;color:#059669;">Aucune lésion détectée — Confiance {conf:.0%}</div>', unsafe_allow_html=True)
                    if rr2.get("resume_clinique"):
                        st.markdown(f'<div style="font-size:.82rem;color:#525252;margin-top:4px;">{rr2.get("resume_clinique","")}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div style="font-size:.72rem;color:#8A8A8A;font-style:italic;padding:10px 14px;background:#F8F8F8;border-radius:8px;margin-top:4px;line-height:1.6;">Ce système fournit une aide à la décision clinique assistée par IA et ne remplace pas le jugement médical.</div>', unsafe_allow_html=True)

            st.divider()

            # Notes médecin
            st.markdown('<div class="section-label">Notes du médecin</div>', unsafe_allow_html=True)
            notes_medecin = st.text_area("", value=st.session_state.get("pending_notes",""),
                height=70, placeholder="Annotations ou corrections avant validation...", label_visibility="collapsed")
            st.session_state.pending_notes = notes_medecin

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown('<div class="section-label">Validation</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Valider et enregistrer", type="primary", use_container_width=True, key="val_txt"):
                    _do_save(pid, pa, patient_nom, patient_type, medical_data, score_data,
                             orientation, explanation, recurrence, validation, completude,
                             notes_medecin, "validé", "dossier")
            with c2:
                if st.button("Rejeter et enregistrer", use_container_width=True, key="rej_txt"):
                    _do_save(pid, pa, patient_nom, patient_type, medical_data, score_data,
                             orientation, explanation, recurrence, validation, completude,
                             notes_medecin, "rejeté", "dashboard")
            with c3:
                if st.button("Annuler sans enregistrer", use_container_width=True, key="ann_txt"):
                    from modules.database import delete_pending_analysis
                    delete_pending_analysis(pid)
                    st.session_state.pending_patient_id = None
                    st.session_state.pending_notes = ""
                    st.rerun()

            st.stop()

        # ── FORMULAIRE UPLOAD ────────────────────────────────────
        c1, c2 = st.columns(2)
        with c1: patient_nom  = st.text_input("Identifiant patient (anonymisé)", placeholder="Ex: Dossier_2024_001")
        with c2: patient_type = st.selectbox("Type de dossier", ["Bilan initial","Post-opératoire","Suivi chimio","Récidive"])

        if not patient_nom:
            st.markdown('<div style="font-size:.78rem;color:#D97706;margin-top:-6px;">Identifiant requis.</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-label">Documents médicaux (PDF ou TXT)</div>', unsafe_allow_html=True)
            uploaded_docs = st.file_uploader("docs", type=["pdf","txt"], accept_multiple_files=True, key="docs_new", label_visibility="collapsed")
            if uploaded_docs: st.markdown(f'<div style="font-size:.78rem;color:#059669;">✓ {len(uploaded_docs)} fichier(s)</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="section-label">Images médicales (JPG/PNG)</div>', unsafe_allow_html=True)
            uploaded_images = st.file_uploader("imgs", type=["jpg","jpeg","png"], accept_multiple_files=True, key="imgs_new", label_visibility="collapsed")
            if uploaded_images: st.markdown(f'<div style="font-size:.78rem;color:#059669;">✓ {len(uploaded_images)} image(s)</div>', unsafe_allow_html=True)

        has_docs = bool(uploaded_docs)
        has_imgs = bool(uploaded_images)

        if patient_nom and (has_docs or has_imgs):
            scn = "Texte + Images" if (has_docs and has_imgs) else ("Texte uniquement" if has_docs else "Image uniquement (YOLO)")
            st.markdown(f'<div style="font-size:.78rem;color:#2F80ED;font-weight:500;margin-bottom:8px;">Scénario : {scn}</div>', unsafe_allow_html=True)

            if st.button("Lancer l'analyse complète", type="primary", use_container_width=True):
                progress = st.progress(0, "Initialisation...")
                t0 = time.time()
                try:
                    progress.progress(20, "Analyse en cours...")
                    result = run_pipeline(
                        text_files=uploaded_docs  if has_docs else None,
                        image_files=uploaded_images if has_imgs else None
                    )
                    progress.progress(100, "Terminé")
                    elapsed = round(time.time() - t0, 2)
                    safe_nom = re.sub(r'[^a-zA-Z0-9_]', '_', patient_nom)
                    pid = f"{safe_nom}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    result["patient_nom"]  = patient_nom
                    result["patient_type"] = patient_type
                    result["elapsed"]      = elapsed
                    result["docs_count"]   = len(uploaded_docs)  if has_docs else 0
                    result["images_count"] = len(uploaded_images) if has_imgs else 0
                    from modules.database import save_pending_analysis
                    save_pending_analysis(pid, result)
                    st.session_state.pending_patient_id = pid
                    st.session_state.pending_notes = ""
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {str(e)}")
                    st.info("Vérifiez qu'Ollama est démarré : `ollama serve`")

    # ════════════════════════════════
    # DOSSIER PATIENT
    # ════════════════════════════════
    elif st.session_state.app_page == "dossier":

        all_p = get_all_patients()
        if not all_p:
            st.markdown('<div style="text-align:center;padding:60px;color:#8A8A8A;font-size:.9rem;">Aucun patient. Cliquez sur Ajouter patient.</div>', unsafe_allow_html=True)
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

        selected_label = st.selectbox("", list(options.keys()), index=default_idx, label_visibility="collapsed")
        selected_id    = options[selected_label]
        patient        = get_patient_by_id(selected_id)
        if not patient:
            st.error("Dossier introuvable.")
            st.stop()

        st.session_state.current_patient_id = selected_id

        med         = patient.get("medical_data", {})
        score_data  = patient.get("score_data", {})
        orientation = patient.get("orientation_data", {})
        explanation = patient.get("explanation", {})
        recurrence  = patient.get("recurrence", {})
        val_med     = patient.get("validation_medecin", "en_attente")

        # En-tête
        c1, c2, c3, c4, c5 = st.columns([4, 1, 1, 1, 1])
        with c1:
            st.markdown(f'<div style="padding:6px 0;"><div style="font-size:.92rem;font-weight:600;color:#1A1A2E;">{patient["nom"]}</div><div style="font-size:.72rem;color:#8A8A8A;">{patient.get("type_dossier","?")} • {patient.get("date_analyse","?")} • {patient.get("docs_count",0)} doc(s)</div></div>', unsafe_allow_html=True)
        with c2:
            lbl = "Actif" if patient.get("statut") == "traite" else "Traité"
            if st.button(lbl, key="tog_s"):
                update_patient_status(selected_id, "actif" if patient.get("statut") == "traite" else "traite")
                st.rerun()
        with c3:
            if st.button("Modifier", key="edit_btn"):
                st.session_state.edit_mode = True
                st.rerun()
        with c4:
            if st.button("Supprimer", key="del_dos"):
                st.session_state["cdel"] = True
                st.rerun()
        with c5:
            if val_med == "en_attente":
                if st.button("Valider", key="val_dos_header", type="primary"):
                    update_validation_medecin(selected_id, "validé")
                    add_log(selected_id, "validation", "validé")
                    st.rerun()

        if st.session_state.get("cdel", False):
            st.warning("Supprimer définitivement ?")
            x1, x2 = st.columns(2)
            with x1:
                if st.button("Confirmer", key="cdel_yes"):
                    delete_patient_db(selected_id)
                    st.session_state.pop("cdel", None)
                    st.session_state.current_patient_id = None
                    st.session_state.app_page = "dashboard"
                    st.rerun()
            with x2:
                if st.button("Annuler", key="cdel_no"):
                    st.session_state.pop("cdel", None)
                    st.rerun()

        if patient.get("statut") == "traite":
            st.markdown('<span class="badge badge-success">Traitement terminé</span>', unsafe_allow_html=True)
        if val_med == "validé":
            st.markdown(f'<div style="background:#F0FDF4;border:1px solid #A7F3D0;border-radius:6px;padding:8px 12px;margin:6px 0;font-size:.78rem;color:#065F46;">Validé par médecin — {patient.get("validation_date","")}</div>', unsafe_allow_html=True)
        elif val_med == "rejeté":
            st.markdown('<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:6px;padding:8px 12px;margin:6px 0;font-size:.78rem;color:#DC2626;">Décision rejetée</div>', unsafe_allow_html=True)

        # Mode modification
        if st.session_state.get("edit_mode", False):
            st.markdown("---")
            st.markdown('<div class="section-label">Mode modification</div>', unsafe_allow_html=True)
            edit_resume = st.text_area("Résumé clinique", value=explanation.get("resume_clinique",""), height=90)
            edit_notes  = st.text_area("Notes médecin",  value=med.get("notes_medecin",""), height=70)
            x1, x2 = st.columns(2)
            with x1:
                if st.button("Enregistrer", type="primary"):
                    update_patient_notes(selected_id, "resume_clinique", edit_resume)
                    update_patient_notes(selected_id, "orientation_notes", edit_notes)
                    try:
                        import sqlite3, json as _json
                        conn_fix = sqlite3.connect("colocare_md.db")
                        cur_fix  = conn_fix.cursor()
                        cur_fix.execute("SELECT donnees FROM patients WHERE id=?", (selected_id,))
                        row = cur_fix.fetchone()
                        if row:
                            donnees = _json.loads(row[0])
                            if "medical_data" in donnees:
                                donnees["medical_data"]["notes_medecin"] = edit_notes
                            donnees["explanation"] = {**donnees.get("explanation",{}), "resume_clinique": edit_resume}
                            cur_fix.execute("UPDATE patients SET donnees=? WHERE id=?", (_json.dumps(donnees, ensure_ascii=False), selected_id))
                            conn_fix.commit()
                        conn_fix.close()
                    except Exception as e:
                        st.warning(f"Mise à jour partielle : {e}")
                    add_log(selected_id, "modification_medecin")
                    st.session_state.edit_mode = False
                    st.rerun()
            with x2:
                if st.button("Annuler"):
                    st.session_state.edit_mode = False
                    st.rerun()

        st.divider()

        # Métriques
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Score",    f"{score_data.get('score',0)}/100")
        with c2: st.metric("TNM",      f"{med.get('stade_T','?')}{med.get('stade_N','?')}{med.get('stade_M','?')}")
        with c3: st.metric("Stage",    orientation.get("stage_group","?"))
        with c4: st.metric("Récidive", recurrence.get("niveau_risque","?"))

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Résumé clinique
        st.markdown('<div class="report-section"><div class="report-label">Résumé clinique</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="report-value">{explanation.get("resume_clinique","")}</div>', unsafe_allow_html=True)
        if med.get("notes_medecin"):
            st.markdown(f'<div style="margin-top:6px;font-size:.78rem;color:#2F80ED;"><strong>Note médecin :</strong> {med.get("notes_medecin")}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Urgence + Orientation
        c1, c2 = st.columns(2)
        with c1:
            niv = score_data.get("niveau","stable")
            if niv == "urgent":       st.error(f"URGENT — {score_data.get('delai','')}")
            elif niv == "semi_urgent": st.warning(f"SEMI-URGENT — {score_data.get('delai','')}")
            else:                     st.success(f"STABLE — {score_data.get('delai','')}")
        with c2:
            dec = orientation.get("decision","")
            box = f"**{orientation.get('specialite','')}**\n\n{orientation.get('protocole','')}\n\nDélai : {orientation.get('delai','')}"
            if "chirurgie" in dec: st.error(box)
            elif dec == "oncologie": st.warning(box)
            else:                   st.info(box)

        # ESMO
        from modules.rules_engine import get_esmo_guideline
        esmo = get_esmo_guideline(orientation.get("stage_group","Stage inconnu"))
        st.markdown(f'<div class="esmo-block"><strong>ESMO {esmo["reference"]}</strong><br>Chimio : {esmo["recommandation_chimio"]}<br>Survie 5 ans : {esmo["survie_5ans"]}</div>', unsafe_allow_html=True)

        # Explainability
        st.markdown('<div class="report-section"><div class="report-label">Raisonnement clinique</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div style="font-size:.72rem;font-weight:600;color:#8A8A8A;margin-bottom:4px;">Preuves</div>', unsafe_allow_html=True)
            for p in explanation.get("preuves_dossier",[]): st.markdown(f'<div style="font-size:.82rem;color:#525252;">· {p}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div style="font-size:.72rem;font-weight:600;color:#8A8A8A;margin-bottom:4px;">Règles activées</div>', unsafe_allow_html=True)
            for r in explanation.get("regles_activees",[]): st.markdown(f'<div style="font-size:.82rem;color:#525252;">· {r}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Timeline
        st.markdown('<div class="section-label">Timeline</div>', unsafe_allow_html=True)
        tl = []
        if med.get("traitement_anterieur") not in ["aucun","inconnu",None,""]:
            tl.append(f"Traitement antérieur : {med.get('traitement_anterieur')}")
        tl.append(f"Analyse — {patient.get('date_analyse','?')}")
        tl.append(f"Orientation : {orientation.get('decision','?')} — {orientation.get('delai','?')}")
        if val_med == "validé": tl.append(f"Validé — {patient.get('validation_date','')}")
        elif val_med == "rejeté": tl.append("Décision rejetée")
        for tx in tl:
            st.markdown(f'<div style="display:flex;gap:8px;margin-bottom:7px;align-items:flex-start;font-size:.82rem;color:#525252;"><div style="width:6px;height:6px;border-radius:50%;background:#2F80ED;margin-top:5px;flex-shrink:0;"></div>{tx}</div>', unsafe_allow_html=True)

        # RCP
        st.divider()
        st.markdown('<div class="section-label">Résumé RCP</div>', unsafe_allow_html=True)
        if st.button("Générer résumé RCP", type="primary", key="gen_rcp"):
            ctx_r = f"Patient {patient['nom']}, {med.get('stade_T','?')}{med.get('stade_N','?')}{med.get('stade_M','?')}, {orientation.get('stage_group','?')}, score {score_data.get('score',0)}/100"
            with st.spinner("Génération..."):
                rcp = ask_gemma(f"""Génère un résumé RCP oncologie colorectale.
Données : {ctx_r}. Type : {med.get('type_histologique','?')}. Métastases : {med.get('localisation_metastases','aucune')}.
## 1. Présentation ## 2. Données clés ## 3. Question RCP ## 4. Spécialistes ## 5. Examens ## 6. Recommandation ESMO""")
            st.markdown(rcp)
            st.download_button("Télécharger RCP", data=rcp, file_name=f"rcp_{patient['nom']}.txt", mime="text/plain")

        # Validation dossier
        if val_med == "en_attente":
            st.divider()
            st.markdown('<div class="section-label">Validation médecin</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Valider la décision", type="primary", key="val_dos2"):
                    update_validation_medecin(selected_id, "validé")
                    add_log(selected_id, "validation", "validé")
                    st.rerun()
            with c2:
                if st.button("Rejeter", key="rej_dos2"):
                    update_validation_medecin(selected_id, "rejeté")
                    add_log(selected_id, "validation", "rejeté")
                    st.rerun()
            with c3:
                if st.button("Marquer traité", key="trt_dos2"):
                    update_patient_status(selected_id, "traite")
                    add_log(selected_id, "statut", "traite")
                    st.rerun()

    elif st.session_state.app_page == "assistant":

        # Fix critique : forcer le offset du contenu principal
        # quand sidebar est position:fixed
        st.markdown(
            '<div id="assistant-fix"></div>'
            '<style>'
            '#assistant-fix ~ * { margin-left: 0 !important; }'
            'section[data-testid="stMain"] {'
            '    margin-left: 220px !important;'
            '    padding-left: 0 !important;'
            '}'
            '</style>',
            unsafe_allow_html=True
        )

        all_p = get_all_patients()
        patient_opts = {"Aucun patient (général)": None}
        patient_opts.update({
            f"{get_urgency_emoji(p.get('score',0))} {p['nom']} — {p.get('stage_group','?')}": p["id"]
            for p in all_p
        })

        sel_label = st.selectbox("Contexte patient", list(patient_opts.keys()))
        sel_id    = patient_opts[sel_label]
        ctx       = "Aucun patient — réponses génériques."

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
                        "Génère résumé RCP court : présentation, éléments clés, question RCP, spécialistes.",
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
                    hist     = get_context_summary(st.session_state.conversation)
                    response = ask_gemma_with_context(question, f"{ctx}\n\nHistorique:\n{hist}", st.session_state.langue)
                st.markdown(response)
            add_message(st.session_state.conversation, "assistant", response)
            save_conversation_db(st.session_state.conversation, sel_id or "")
            st.rerun()