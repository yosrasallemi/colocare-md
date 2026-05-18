# modules/gemma_client.py
# Switch rapide : MODEL_TEXT = "gemma3:4b" pour dev, "gemma4:latest" pour prod

import ollama

# ══ SWITCH ICI UNIQUEMENT ══
MODEL_TEXT   = "gemma3:4b"      # changer en "gemma4:latest" quand RAM ok
MODEL_VISION = "gemma3:4b"      # idem
# ═══════════════════════════

HORS_DOMAINE_KEYWORDS = [
    "avc","stroke","neurolog","cardiolog","diabète","diabetes",
    "psychiatr","orthopéd","dermatolog","gynécolog","ophtalmolog",
    "pneumolog","nephrol","urol","endocrin","rhumato",
    "breast cancer","cancer du sein","lung cancer","cancer du poumon",
    "prostate","ovarian","cervical","pancreatic cancer",
    "alzheimer","parkinson","epilepsi","migraine","hypertension",
    "grippe","covid","vaccination"
]
COLORECTAL_KEYWORDS = [
    "colon","côlon","colorectal","colorectale","rectum","rectal",
    "colectomy","colectomie","sigmoïde","sigmoid","adenocarcinome",
    "adenocarcinoma","folfox","folfiri","xelox","tnm","stade",
    "métastase","metastasis","chimiothérapie","chirurgie viscérale",
    "polype","polyp","coloscopie","colonoscopy","esmo","nccn",
    "cea","ca19","bevacizumab","cetuximab","carcinose","rcp"
]
REFUS_FR = "Je suis spécialisé uniquement en oncologie colorectale. Je ne peux pas répondre à cette question."
REFUS_EN = "I am specialized exclusively in colorectal oncology. I cannot answer this question."


def is_hors_domaine(question: str) -> bool:
    q = question.lower()
    if any(k in q for k in COLORECTAL_KEYWORDS):
        return False
    return any(k in q for k in HORS_DOMAINE_KEYWORDS)


def ask_gemma(prompt: str, model: str = None) -> str:
    try:
        response = ollama.chat(
            model=model or MODEL_TEXT,
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content']
    except Exception as e:
        return f"ERREUR_GEMMA: {str(e)}"


def ask_gemma_medical_json(text: str) -> str:
    prompt = f"""Tu es un oncologue expert en cancer colorectal.
REGLES : Extrais UNIQUEMENT ce qui est écrit. Si absent → "inconnu".
TNM valides : T4a/T4b, N2a/N2b, M1a/M1b/M1c.
cancer_confirme=true SEULEMENT si biopsie confirme adénocarcinome.

JSON STRICT uniquement :
{{
    "cancer_confirme": true,
    "niveau_evidence": "histologique ou radiologique ou clinique ou suspicion",
    "stade_T": "T1/T2/T3/T4/T4a/T4b ou inconnu",
    "stade_N": "N0/N1/N1a/N1b/N2/N2a/N2b ou inconnu",
    "stade_M": "M0/M1/M1a/M1b/M1c ou inconnu",
    "type_histologique": "type exact ou inconnu",
    "localisation": "partie du colon ou inconnu",
    "localisation_metastases": "organes ou aucune",
    "metastases": false,
    "metastase_chronique": false,
    "complications": "aucune ou liste",
    "marqueurs_bio": "CEA/CA19-9 valeurs ou non mentionnés",
    "traitement_realise": "aucun/chirurgie/chimio/les deux",
    "traitement_anterieur": "protocoles ou aucun",
    "urgence": "haute ou moyenne ou faible",
    "contexte_patient": "résumé une phrase"
}}

Rapport : {text[:3000]}"""
    return ask_gemma(prompt)


def ask_gemma_image(image_path: str) -> str:
    prompt = """Gastroentérologue expert. Analyse cette image coloscopie. JSON strict :
{
    "polype_detecte": false,
    "nombre_polypes": 0,
    "zones_suspectes": "description ou aucune",
    "morphologie": "sessile/pédiculé/plan/normal",
    "taille_estimee": "mm ou non évaluable",
    "gravite": "normale/suspecte/urgente",
    "classification_paris": "type ou inconnu",
    "recommandation": "surveillance/biopsie/résection/normal"
}
JSON uniquement."""
    try:
        response = ollama.chat(
            model=MODEL_VISION,
            messages=[{"role": "user", "content": prompt, "images": [image_path]}]
        )
        return response['message']['content']
    except Exception as e:
        return f"ERREUR_IMAGE: {str(e)}"


def ask_gemma_with_context(question: str, context: str, langue: str = "Français") -> str:
    if is_hors_domaine(question):
        return REFUS_FR if langue == "Français" else REFUS_EN
    lang = "Réponds en français." if langue == "Français" else "Reply in English."
    prompt = f"""Assistant médical spécialisé UNIQUEMENT cancer colorectal.
{lang}
RÈGLE : Hors colorectal → répondre uniquement "Je suis spécialisé uniquement en oncologie colorectale."
Domaines : TNM, colectomie, FOLFOX/FOLFIRI, ESMO/NCCN, CEA/CA19-9, RCP.

Contexte patient : {context}
Question : {question}"""
    return ask_gemma(prompt)


if __name__ == "__main__":
    print(ask_gemma("Explique T3N1M0 en une phrase."))
    print("OK")