# modules/rules_engine.py

ESMO_GUIDELINES = {
    "Stage I": {
        "reference": "ESMO Guidelines 2023 — Section 5.1",
        "recommandation_chimio": "Pas de chimiothérapie adjuvante recommandée",
        "survie_5ans": "90%+",
        "surveillance": "Coloscopie à 1 an, puis tous les 5 ans. CEA tous les 3 mois (2 ans)."
    },
    "Stage II": {
        "reference": "ESMO Guidelines 2023 — Section 5.2",
        "recommandation_chimio": "Chirurgie seule. Chimio adjuvante si facteurs haut risque (T4, occlusion, perforation).",
        "survie_5ans": "75-85%",
        "surveillance": "CT tous les 6 mois (3 ans). CEA tous les 3 mois (2 ans)."
    },
    "Stage III": {
        "reference": "ESMO Guidelines 2023 — Section 5.3",
        "recommandation_chimio": "FOLFOX x12 cycles (6 mois) — obligatoire",
        "survie_5ans": "40-70%",
        "surveillance": "CT tous les 6 mois (3 ans). CEA tous les 3 mois (3 ans)."
    },
    "Stage IV": {
        "reference": "ESMO Guidelines 2023 — Section 5.4",
        "recommandation_chimio": "FOLFOX/FOLFIRI + Bevacizumab (KRAS sauvage: + Cetuximab)",
        "survie_5ans": "10-15%",
        "surveillance": "Réévaluation après 4 cycles. Bilan résécabilité hépatique."
    },
    "Stage inconnu": {
        "reference": "Bilan complémentaire nécessaire",
        "recommandation_chimio": "RCP multidisciplinaire obligatoire",
        "survie_5ans": "Non estimable",
        "surveillance": "À définir après staging complet"
    }
}


def get_stage_group(T: str, N: str, M: str) -> str:
    T = T.upper()
    N = N.upper()
    M = M.upper()

    if M in ["M1", "M1A", "M1B", "M1C"]:
        return "Stage IV"
    if T in ["T1", "T2"] and N == "N0":
        return "Stage I"
    if T in ["T3", "T4", "T4A", "T4B"] and N == "N0":
        return "Stage II"
    if N in ["N1", "N1A", "N1B", "N2", "N2A", "N2B"]:
        return "Stage III"
    return "Stage inconnu"


def get_esmo_guideline(stage_group: str) -> dict:
    return ESMO_GUIDELINES.get(stage_group, ESMO_GUIDELINES["Stage inconnu"])


def decide_orientation(data: dict) -> dict:
    T = data.get("stade_T", "inconnu").upper()
    N = data.get("stade_N", "inconnu").upper()
    M = data.get("stade_M", "inconnu").upper()
    metastases = data.get("metastases", False)
    metastase_chronique = data.get("metastase_chronique", False)
    urgence = data.get("urgence", "moyenne").lower()

    if M == "M0":
        metastases = False

    stage_group = get_stage_group(T, N, M)
    esmo = get_esmo_guideline(stage_group)

    # RÈGLE 1 — Urgence vitale
    if urgence == "haute" and not metastases:
        return {
            "decision": "chirurgie_urgente",
            "emoji": "🔴",
            "specialite": "Chirurgien Viscéral — URGENCE",
            "service": "Bloc Opératoire Urgences",
            "traitement": "Chirurgie d'urgence immédiate",
            "protocole": "Colectomie en urgence / Stomie de décharge",
            "confidence": 95,
            "ai_confidence": "high",
            "raison": "Urgence vitale — obstruction ou perforation détectée",
            "stage_group": stage_group,
            "summary": "Patient nécessitant chirurgie urgente immédiate.",
            "delai": "IMMÉDIAT — < 24h",
            "rcp_requis": False,
            "human_validation_required": True,
            "esmo_reference": esmo["reference"],
            "esmo_chimio": esmo["recommandation_chimio"],
            "survie_5ans": esmo["survie_5ans"],
            "surveillance": esmo["surveillance"]
        }

    # RÈGLE 2 — Métastases → Oncologie
    if metastases or M in ["M1", "M1A", "M1B", "M1C"]:
        return {
            "decision": "oncologie",
            "emoji": "🟠",
            "specialite": "Oncologue Médical",
            "service": "Service d'Oncologie Médicale",
            "traitement": "Chimiothérapie systémique",
            "protocole": esmo["recommandation_chimio"],
            "confidence": 88,
            "ai_confidence": "medium",
            "raison": "Métastases à distance (M1) — prise en charge oncologique",
            "stage_group": stage_group,
            "summary": "Cancer colorectal métastatique — traitement oncologique systémique.",
            "delai": "Dans les 72h" if not metastase_chronique else "Consultation planifiée",
            "rcp_requis": True,
            "human_validation_required": True,
            "esmo_reference": esmo["reference"],
            "esmo_chimio": esmo["recommandation_chimio"],
            "survie_5ans": esmo["survie_5ans"],
            "surveillance": esmo["surveillance"]
        }

    # RÈGLE 3 — Stade I
    if T in ["T1", "T2"] and N == "N0":
        return {
            "decision": "chirurgie",
            "emoji": "🔴",
            "specialite": "Chirurgien Viscéral et Digestif",
            "service": "Service de Chirurgie Viscérale",
            "traitement": "Résection chirurgicale curative",
            "protocole": "Colectomie laparoscopique",
            "confidence": 92,
            "ai_confidence": "high",
            "raison": f"Tumeur localisée {T}{N}M0 — résécable curativement",
            "stage_group": stage_group,
            "summary": "Cancer colorectal localisé — chirurgie curative indiquée.",
            "delai": "Programmée dans les 2 semaines",
            "rcp_requis": False,
            "human_validation_required": True,
            "esmo_reference": esmo["reference"],
            "esmo_chimio": esmo["recommandation_chimio"],
            "survie_5ans": esmo["survie_5ans"],
            "surveillance": esmo["surveillance"]
        }

    # RÈGLE 4 — Stade III
    if T in ["T3", "T4", "T4A", "T4B"] and N in ["N1", "N1A", "N1B", "N2", "N2A", "N2B"]:
        return {
            "decision": "chirurgie_chimio",
            "emoji": "🔴",
            "specialite": "Chirurgien Viscéral + Oncologue Médical",
            "service": "Chirurgie Viscérale + Oncologie",
            "traitement": "Chirurgie puis chimiothérapie adjuvante",
            "protocole": esmo["recommandation_chimio"],
            "confidence": 85,
            "ai_confidence": "medium",
            "raison": f"Stade III {T}{N}M0 — traitement multimodal nécessaire",
            "stage_group": stage_group,
            "summary": "Cancer colorectal stade III — chirurgie suivie de chimiothérapie adjuvante.",
            "delai": "Chirurgie dans les 72h si urgence sinon 2 semaines",
            "rcp_requis": True,
            "human_validation_required": True,
            "esmo_reference": esmo["reference"],
            "esmo_chimio": esmo["recommandation_chimio"],
            "survie_5ans": esmo["survie_5ans"],
            "surveillance": esmo["surveillance"]
        }

    # RÈGLE 5 — Stade II
    if T in ["T3", "T4", "T4A", "T4B"] and N == "N0":
        return {
            "decision": "chirurgie",
            "emoji": "🔴",
            "specialite": "Chirurgien Viscéral et Digestif",
            "service": "Service de Chirurgie Viscérale",
            "traitement": "Résection chirurgicale — Chimio si facteurs haut risque",
            "protocole": esmo["recommandation_chimio"],
            "confidence": 82,
            "ai_confidence": "medium",
            "raison": f"Stade II {T}N0M0 — chirurgie avec évaluation chimio adjuvante",
            "stage_group": stage_group,
            "summary": "Cancer colorectal stade II — chirurgie curative avec évaluation oncologique.",
            "delai": "Dans les 2 semaines",
            "rcp_requis": True,
            "human_validation_required": True,
            "esmo_reference": esmo["reference"],
            "esmo_chimio": esmo["recommandation_chimio"],
            "survie_5ans": esmo["survie_5ans"],
            "surveillance": esmo["surveillance"]
        }

    # RÈGLE 6 — Incertain
    return {
        "decision": "incertain",
        "emoji": "🟡",
        "specialite": "Réunion de Concertation Pluridisciplinaire",
        "service": "RCP Oncologie Colorectale",
        "traitement": "Examens complémentaires + discussion RCP",
        "protocole": "Bilan complémentaire nécessaire",
        "confidence": 50,
        "ai_confidence": "low",
        "raison": "Données insuffisantes pour décision thérapeutique ferme",
        "stage_group": stage_group,
        "summary": "Cas complexe — validation multidisciplinaire obligatoire.",
        "delai": "RCP dans les 5 jours ouvrables",
        "rcp_requis": True,
        "human_validation_required": True,
        "esmo_reference": esmo["reference"],
        "esmo_chimio": esmo["recommandation_chimio"],
        "survie_5ans": esmo["survie_5ans"],
        "surveillance": esmo["surveillance"]
    }