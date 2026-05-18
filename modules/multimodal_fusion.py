# modules/multimodal_fusion.py

def fuse_analysis(
    text_data: dict,
    image_data: dict = None,
    bio_data: dict = None
) -> dict:

    sources = []
    fusion_score = 0

    if text_data.get("extraction_status") == "success":
        sources.append("rapport_textuel")
        fusion_score += 50

    if image_data and image_data.get("analyse_status") == "success":
        sources.append("imagerie_colonoscopie")
        fusion_score += 30

        polype_image = image_data.get("polype_detecte", False)
        cancer_texte = text_data.get("cancer_confirme", False)

        if polype_image and cancer_texte:
            fusion_score += 10
        elif polype_image and not cancer_texte:
            text_data["niveau_evidence"] = "radiologique"

    if bio_data:
        sources.append("marqueurs_biologiques")
        fusion_score += 20

    synthese = {
        "sources_analysees": sources,
        "fusion_score": min(fusion_score, 100),
        "fiabilite_globale": (
            "haute" if fusion_score >= 70
            else "modérée" if fusion_score >= 40
            else "faible"
        ),
        "donnees_fusionnees": {
            **text_data,
            "image_analysis": image_data or {},
            "bio_analysis": bio_data or {}
        }
    }

    if image_data and image_data.get("polype_detecte"):
        synthese["donnees_fusionnees"]["imagerie_compatible"] = True
        synthese["donnees_fusionnees"]["zones_imagerie"] = image_data.get("zones_suspectes", "")

    return synthese
