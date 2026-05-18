# modules/explainability.py

def generate_explanation(data: dict, orientation: dict, score_data: dict) -> dict:

    preuves = []

    if data.get("stade_T", "inconnu") not in ["inconnu", "", None]:
        preuves.append(f"Stade T détecté : {data['stade_T']}")
    if data.get("stade_N", "inconnu") not in ["inconnu", "", None]:
        preuves.append(f"Ganglions : {data['stade_N']}")
    if data.get("stade_M", "inconnu") not in ["inconnu", "", None]:
        preuves.append(f"Statut métastatique : {data['stade_M']}")
    if data.get("type_histologique", "inconnu") not in ["inconnu", "", None]:
        preuves.append(f"Type : {data['type_histologique']}")
    if data.get("localisation", "inconnu") not in ["inconnu", "", None]:
        preuves.append(f"Localisation : {data['localisation']}")
    if data.get("metastases"):
        preuves.append("⚠️ Métastases confirmées dans le dossier")
    if data.get("complications") not in ["aucune", "non déterminé", "inconnu", None, ""]:
        preuves.append(f"Complications : {data['complications']}")
    if data.get("marqueurs_bio") not in ["non mentionnés", "inconnu", None, ""]:
        preuves.append(f"Marqueurs bio : {data['marqueurs_bio']}")

    regles = score_data.get("facteurs", [])
    confidence = orientation.get("confidence", 0)

    if confidence >= 85:
        confiance_label = "Élevée ✅"
        confiance_explication = "Données suffisantes pour décision ferme"
    elif confidence >= 70:
        confiance_label = "Modérée ⚠️"
        confiance_explication = "Décision probable — examens complémentaires conseillés"
    else:
        confiance_label = "Faible ❌"
        confiance_explication = "Données insuffisantes — RCP obligatoire"

    stage_group = orientation.get("stage_group", "")
    specialite = orientation.get("specialite", "spécialité inconnue")

    resume = (
        f"Patient présentant un cancer colorectal {stage_group} "
        f"avec une orientation vers {specialite}. "
        f"Score de priorité : {score_data.get('score', 0)}/100 — "
        f"{score_data.get('label', '')}."
    )

    return {
        "preuves_dossier": preuves,
        "regles_activees": regles,
        "decision": orientation.get("decision"),
        "raison_principale": orientation.get("raison"),
        "protocole": orientation.get("protocole"),
        "confidence_score": confidence,
        "confiance_label": confiance_label,
        "confiance_explication": confiance_explication,
        "score_priorite": score_data.get("score"),
        "rcp_requis": orientation.get("rcp_requis", False),
        "stage_group": orientation.get("stage_group"),
        "validation_humaine": True,
        "resume_clinique": resume,
        "avertissement": (
            "⚠️ Cette décision est une aide au diagnostic. "
            "Le médecin valide toujours la décision finale."
        )
    }