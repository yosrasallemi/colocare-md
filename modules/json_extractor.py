# modules/json_extractor.py

import json
from modules.gemma_client import ask_gemma_medical_json
from modules.pdf_reader import extract_medical_sections


def clean_json_response(raw: str) -> str:
    raw = raw.strip()
    # Supprimer markdown code blocks
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        parts = raw.split("```")
        if len(parts) >= 2:
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
    # Chercher le JSON entre { }
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]
    return raw.strip()


def validate_tnm(data: dict) -> dict:
    valid_T = ["T0", "T1", "T2", "T3", "T4", "T4A", "T4B", "INCONNU"]
    valid_N = ["N0", "N1", "N1A", "N1B", "N2", "N2A", "N2B", "INCONNU"]
    valid_M = ["M0", "M1", "M1A", "M1B", "M1C", "INCONNU"]

    T = str(data.get("stade_T", "inconnu")).upper().strip()
    N = str(data.get("stade_N", "inconnu")).upper().strip()
    M = str(data.get("stade_M", "inconnu")).upper().strip()

    data["stade_T"] = T if T in valid_T else "inconnu"
    data["stade_N"] = N if N in valid_N else "inconnu"
    data["stade_M"] = M if M in valid_M else "inconnu"

    # Cohérence M0 → pas de métastases
    if data["stade_M"] == "M0":
        data["metastases"] = False

    return data


def _fallback_extraction(text: str, raw_response: str) -> dict:
    """
    Fallback intelligent si Gemma ne retourne pas de JSON valide.
    Cherche les infos TNM directement dans le texte.
    """
    import re
    text_lower = text.lower()

    # Détection TNM par regex
    t_match = re.search(r'\b(p?t[0-4][ab]?)\b', text_lower)
    n_match = re.search(r'\b(p?n[0-2][ab]?)\b', text_lower)
    m_match = re.search(r'\b(p?m[01][abc]?)\b', text_lower)

    stade_T = t_match.group(1).upper().replace("P", "") if t_match else "inconnu"
    stade_N = n_match.group(1).upper().replace("P", "") if n_match else "inconnu"
    stade_M = m_match.group(1).upper().replace("P", "") if m_match else "inconnu"

    # Détection cancer confirmé
    cancer_keywords = ["adenocarcinoma", "adénocarcinome", "carcinoma", "cancer colorectal", "colon cancer"]
    cancer_confirme = any(k in text_lower for k in cancer_keywords)

    # Détection métastases
    meta_keywords = ["metastas", "métastas", "m1", "liver metastas", "hepatic metastas"]
    metastases = any(k in text_lower for k in meta_keywords) or stade_M == "M1"

    # Détection urgence
    urgence_haute = any(k in text_lower for k in ["obstruction", "perforation", "emergency", "urgence", "urgent"])
    urgence = "haute" if urgence_haute else "moyenne"

    # Détection rémission
    remission = any(k in text_lower for k in ["remission", "rémission", "no evidence of disease", "ned", "disease-free"])

    # Détection traitement antérieur
    traitement_ant = "aucun"
    if any(k in text_lower for k in ["folfox", "folfiri", "chemotherapy", "chimiothérapie"]):
        traitement_ant = "chimiothérapie (détectée dans le texte)"
    if any(k in text_lower for k in ["colectomy", "colectomie", "resection", "résection", "surgery", "chirurgie"]):
        if traitement_ant != "aucun":
            traitement_ant += " + chirurgie"
        else:
            traitement_ant = "chirurgie (détectée dans le texte)"

    return {
        "cancer_confirme": cancer_confirme,
        "niveau_evidence": "radiologique" if cancer_confirme else "suspicion",
        "stade_T": stade_T,
        "stade_N": stade_N,
        "stade_M": stade_M,
        "type_histologique": "adénocarcinome" if cancer_confirme else "inconnu",
        "localisation": "côlon" if "colon" in text_lower or "côlon" in text_lower else "inconnu",
        "localisation_metastases": "aucune" if not metastases else "à préciser",
        "metastases": metastases,
        "metastase_chronique": False,
        "complications": "aucune",
        "marqueurs_bio": "non mentionnés",
        "traitement_realise": "chirurgie" if "colectom" in text_lower else "inconnu",
        "traitement_anterieur": traitement_ant,
        "urgence": urgence,
        "contexte_patient": "Rémission complète post-traitement" if remission else "Contexte extrait automatiquement",
        "extraction_status": "fallback_regex",
        "reponse_brute": raw_response[:200]
    }


def extract_medical_json(text: str) -> dict:
    """
    Extraction avec stratégie en 2 passes :
    1. Extraction des sections médicales prioritaires
    2. Fallback regex si Gemma échoue
    """
    # Extraire les sections médicales prioritaires
    medical_text = extract_medical_sections(text)

    # Appel Gemma
    raw_response = ask_gemma_medical_json(medical_text)
    clean = clean_json_response(raw_response)

    try:
        data = json.loads(clean)
        data = validate_tnm(data)
        data["extraction_status"] = "success"
        return data

    except json.JSONDecodeError:
        # Fallback intelligent par regex
        fallback = _fallback_extraction(text, raw_response)
        fallback = validate_tnm(fallback)
        return fallback


if __name__ == "__main__":
    test = """
    Patient 65 ans. Adenocarcinoma of sigmoid colon T3N1M0 Stage IIIB.
    Moderately differentiated. Laparoscopic sigmoidectomy performed.
    2/15 lymph nodes positive. CEA 8.5 ng/mL.
    """
    result = extract_medical_json(test)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Status: {result['extraction_status']}")