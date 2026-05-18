# modules/prognosis_engine.py

import json
from modules.gemma_client import ask_gemma


def analyze_postop(text: str) -> dict:
    prompt = f"""Tu es un oncologue expert. Analyse ce document post-opératoire.
Réponds UNIQUEMENT en JSON strict :
{{
    "resection_complete": true,
    "marges_saines": true,
    "ganglions_examines": 0,
    "ganglions_positifs": 0,
    "risque_recidive": "faible ou modéré ou élevé",
    "chimio_adjuvante_necessaire": false,
    "protocole_adjuvant": "FOLFOX ou aucun ou à discuter",
    "frequence_suivi": "3 mois ou 6 mois",
    "prochain_examen": "coloscopie ou scanner ou CEA ou les trois",
    "survie_estimee_5ans": "90% ou selon stade",
    "recommandations": "liste des recommandations principales"
}}
Document : {text[:2000]}"""

    raw = ask_gemma(prompt)
    try:
        clean = raw.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > start:
            clean = clean[start:end]
        return json.loads(clean)
    except:
        return {
            "erreur": "Parsing JSON échoué",
            "risque_recidive": "non déterminé",
            "chimio_adjuvante_necessaire": False,
            "recommandations": "Consultation oncologique recommandée",
            "reponse_brute": raw[:300]
        }


def calculate_recurrence_risk(data: dict, orientation: dict) -> dict:
    stage = orientation.get("stage_group", "Stage inconnu")
    T = data.get("stade_T", "inconnu").upper()
    N = data.get("stade_N", "inconnu").upper()

    risk_score = 0
    factors = []

    if stage == "Stage IV":
        risk_score += 70
        factors.append("Stage IV métastatique (+70)")
    elif stage == "Stage III":
        risk_score += 45
        factors.append("Stage III ganglionnaire (+45)")
    elif stage == "Stage II":
        risk_score += 20
        factors.append("Stage II localement avancé (+20)")
    elif stage == "Stage I":
        risk_score += 8
        factors.append("Stage I précoce (+8)")

    if T in ["T4", "T4A", "T4B"]:
        risk_score += 15
        factors.append("T4 invasion organes adjacents (+15)")
    if N in ["N2", "N2A", "N2B"]:
        risk_score += 10
        factors.append("N2 envahissement ganglionnaire étendu (+10)")
    if data.get("metastases"):
        risk_score += 20
        factors.append("Métastases détectées (+20)")

    risk_score = min(risk_score, 100)

    if risk_score >= 60:
        niveau_risque = "Élevé"
        couleur = "rouge"
    elif risk_score >= 30:
        niveau_risque = "Modéré"
        couleur = "orange"
    else:
        niveau_risque = "Faible"
        couleur = "vert"

    return {
        "risk_score": risk_score,
        "niveau_risque": niveau_risque,
        "couleur": couleur,
        "facteurs": factors,
        "chimio_adjuvante_recommandee": risk_score >= 40,
        "frequence_surveillance": "3 mois" if risk_score >= 60 else "6 mois"
    }