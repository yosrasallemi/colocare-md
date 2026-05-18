# modules/diagnosis_validator.py

def validate_diagnosis(text: str, medical_data: dict) -> dict:

    cancer_confirme = medical_data.get("cancer_confirme", False)
    niveau_evidence = medical_data.get("niveau_evidence", "inconnu")

    T = medical_data.get("stade_T", "inconnu").upper()
    N = medical_data.get("stade_N", "inconnu").upper()
    M = medical_data.get("stade_M", "inconnu").upper()
    metastases = medical_data.get("metastases", False)

    tnm_valides_T = ["T1", "T2", "T3", "T4", "T4A", "T4B"]
    tnm_valides_N = ["N1", "N1A", "N1B", "N2", "N2A", "N2B"]
    tnm_valides_M = ["M1", "M1A", "M1B", "M1C"]

    tnm_confirme = (
        T in tnm_valides_T or
        N in tnm_valides_N or
        M in tnm_valides_M or
        metastases is True
    )

    if tnm_confirme:
        cancer_confirme = True
        if M in tnm_valides_M or metastases:
            niveau_evidence = "histologique"
        else:
            niveau_evidence = niveau_evidence if niveau_evidence != "inconnu" else "radiologique"

    text_lower = text.lower()

    keywords_confirmes = [
        "adenocarcinoma", "adénocarcinome", "carcinoma", "malignant", "malin",
        "cancer", "tumor confirmed", "t1", "t2", "t3", "t4",
        "stage iii", "stage iv", "colorectal cancer", "colon cancer"
    ]

    keywords_benins = [
        "no malignancy", "pas de malignité", "negative biopsy",
        "biopsie négative", "benign polyp", "polype bénin"
    ]

    has_cancer_kw = any(k in text_lower for k in keywords_confirmes)
    has_benign_kw = any(k in text_lower for k in keywords_benins)

    confidence_score = 0
    if tnm_confirme:
        confidence_score += 60
    if cancer_confirme:
        confidence_score += 20
    if niveau_evidence == "histologique":
        confidence_score += 15
    elif niveau_evidence == "radiologique":
        confidence_score += 10
    if has_cancer_kw:
        confidence_score += 10
    if has_benign_kw:
        confidence_score -= 25

    confidence_score = max(0, min(100, confidence_score))

    if confidence_score >= 60:
        status = "confirme"
        message = "Cancer colorectal confirmé — Pipeline oncologique activé"
        activate_pipeline = True
    elif confidence_score >= 35:
        status = "suspect"
        message = "Cancer colorectal suspecté — Validation histologique recommandée"
        activate_pipeline = True
    else:
        status = "non_confirme"
        message = "Cancer colorectal non confirmé dans ce document"
        activate_pipeline = False

    return {
        "status": status,
        "confidence": confidence_score,
        "message": message,
        "activate_pipeline": activate_pipeline,
        "niveau_evidence": niveau_evidence,
        "tnm_detecte": tnm_confirme,
        "avertissement": None if status == "confirme" else f"⚠️ {message}"
    }


def check_data_completeness(data: dict) -> dict:
    champs_critiques = ["stade_T", "stade_N", "stade_M", "type_histologique", "localisation"]

    inconnus = [
        c for c in champs_critiques
        if data.get(c, "inconnu") in ["inconnu", "", None]
    ]

    taux = round((len(champs_critiques) - len(inconnus)) / len(champs_critiques) * 100)

    if taux >= 80:
        fiabilite = "haute"
        action = "Décision fiable"
    elif taux >= 50:
        fiabilite = "modérée"
        action = "Compléter le dossier recommandé"
    else:
        fiabilite = "faible"
        action = "RCP obligatoire — données insuffisantes"

    return {
        "taux_completude": taux,
        "champs_manquants": inconnus,
        "fiabilite": fiabilite,
        "action_recommandee": action,
        "rcp_force": taux < 50
    }