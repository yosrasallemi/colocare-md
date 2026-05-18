# modules/image_analyzer.py


import json
import os
from modules.gemma_client import ask_gemma_image


def clean_image_json(raw: str) -> dict:
    """Parse la réponse JSON de l'analyse image"""
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
        result = json.loads(clean)
        result["analyse_status"] = "success"
        return result
    except:
        return {
            "polype_detecte": False,
            "zones_suspectes": "Analyse non concluante",
            "gravite": "indeterminee",
            "recommandation": "Analyse manuelle recommandée",
            "analyse_status": "echec",
            "reponse_brute": raw[:300]
        }


def analyze_colonoscopy_image(image_path: str) -> dict:
    """Analyse une image de coloscopie"""
    if not os.path.exists(image_path):
        return {"erreur": "Fichier image introuvable", "analyse_status": "erreur"}

    raw = ask_gemma_image(image_path)

    if raw.startswith("ERREUR_IMAGE"):
        return {
            "polype_detecte": False,
            "zones_suspectes": "Modèle non multimodal",
            "gravite": "indeterminee",
            "recommandation": "Utiliser gemma4 pour analyse images",
            "analyse_status": "modele_incompatible",
            "message": "Installez gemma4 : ollama pull gemma4"
        }

    return clean_image_json(raw)


def get_image_recommendation(result: dict) -> str:
    """Recommandation basée sur résultat image"""
    status = result.get("analyse_status", "")

    if status == "modele_incompatible":
        return "⚠️ Modèle non multimodal — ollama pull gemma4"
    if status == "erreur":
        return "❌ Erreur analyse image"

    gravite = result.get("gravite", "")
    polype = result.get("polype_detecte", False)

    if gravite == "urgente":
        return "🔴 Lésion urgente détectée — biopsie immédiate"
    elif gravite == "suspecte" or polype:
        return "🟠 Zone suspecte — biopsie recommandée"
    elif gravite == "normale":
        return "🟢 Image normale — suivi standard"
    else:
        return "🟡 Analyse inconcluante — avis spécialiste"