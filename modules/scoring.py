# modules/scoring.py

def calculate_priority_score(data: dict) -> dict:

    score = 0
    factors = []

    T = data.get("stade_T", "inconnu").upper()
    N = data.get("stade_N", "inconnu").upper()
    M = data.get("stade_M", "inconnu").upper()
    metastases = data.get("metastases", False)
    urgence = data.get("urgence", "").lower()

    if M == "M0":
        metastases = False

    # Facteur T
    if T.startswith("T4"):
        score += 30
        factors.append("T4 : invasion organes adjacents (+30)")
    elif T.startswith("T3"):
        score += 22
        factors.append("T3 : dépasse la paroi colique (+22)")
    elif T.startswith("T2"):
        score += 12
        factors.append("T2 : atteinte musculeuse (+12)")
    elif T.startswith("T1"):
        score += 6
        factors.append("T1 : atteinte sous-muqueuse (+6)")

    # Facteur N
    if N.startswith("N2"):
        score += 20
        factors.append("N2 : 4+ ganglions envahis (+20)")
    elif N.startswith("N1"):
        score += 12
        factors.append("N1 : 1-3 ganglions envahis (+12)")

    # Facteur M
    if M.startswith("M1") or metastases is True:
        score += 25
        factors.append("M1 : métastases à distance (+25)")

    # Urgence
    if urgence == "haute":
        score += 15
        factors.append("Urgence clinique haute (+15)")
    elif urgence == "moyenne":
        score += 7
        factors.append("Urgence clinique moyenne (+7)")

    # Complications
    complications = str(data.get("complications", "")).lower()
    if "obstruction" in complications:
        score += 10
        factors.append("Obstruction intestinale (+10)")
    if "perforation" in complications:
        score += 15
        factors.append("Perforation digestive (+15)")
    if "bleeding" in complications or "hémorragie" in complications:
        score += 8
        factors.append("Saignement actif (+8)")

    # Pédiatrique
    contexte = str(data.get("contexte_patient", "")).lower()
    if any(k in contexte for k in ["adolescent", "pediatric", "child", "enfant", "jeune"]):
        score += 10
        factors.append("Contexte pédiatrique (+10)")

    # Carcinose péritonéale
    comp_str = str(data.get("complications", "")).lower()
    loc_meta = str(data.get("localisation_metastases", "")).lower()
    if "peritoneal" in comp_str or "carcinose" in comp_str or "peritoneal" in loc_meta:
        score += 15
        factors.append("Carcinose péritonéale (+15)")
    if "peritonitis" in comp_str or "péritonite" in comp_str:
        score += 12
        factors.append("Péritonite — urgence chirurgicale (+12)")

    # Métastases multi-organes
    if M.startswith("M1") or metastases:
        meta_str = str(data.get("localisation_metastases", "")).lower()
        organes = sum(1 for k in ["foie", "liver", "poumon", "lung", "os", "bone", "cerveau", "brain"] if k in meta_str)
        if organes >= 2:
            score += 10
            factors.append(f"Métastases multi-organes ({organes} sites) (+10)")

    # Type histologique agressif
    type_histo = str(data.get("type_histologique", "")).lower()
    if any(k in type_histo for k in ["signet", "mucinous", "mucineux", "poorly"]):
        score += 8
        factors.append("Type histologique agressif (+8)")

    score = min(score, 100)

    if score >= 70:
        niveau = "urgent"
        label = "🔴 URGENT"
        delai = "Intervention < 24h"
    elif score >= 40:
        niveau = "semi_urgent"
        label = "🟠 SEMI-URGENT"
        delai = "Intervention < 72h"
    else:
        niveau = "stable"
        label = "🟢 STABLE"
        delai = "Planification possible"

    return {
        "score": score,
        "niveau": niveau,
        "label": label,
        "delai": delai,
        "facteurs": factors,
        "summary": f"Patient classé {niveau.upper()} avec un score clinique de {score}/100.",
        "human_validation_required": True
    }