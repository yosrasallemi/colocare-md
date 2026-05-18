# modules/pipeline.py
# Pipeline modulaire — 3 scénarios — résultats NON sauvegardés avant validation médecin

import time, os, json
from modules.pdf_reader import read_pdf_upload, read_txt_file
from modules.json_extractor import extract_medical_json
from modules.rules_engine import decide_orientation
from modules.scoring import calculate_priority_score
from modules.explainability import generate_explanation
from modules.diagnosis_validator import validate_diagnosis, check_data_completeness
from modules.image_analyzer import analyze_colonoscopy_image
from modules.prognosis_engine import calculate_recurrence_risk
from modules.multimodal_fusion import fuse_analysis


def apply_conservative_security(img_result: dict) -> dict:
    gravite  = img_result.get("gravite", "indeterminee").lower()
    status   = img_result.get("analyse_status", "")
    morpho   = img_result.get("morphologie", "").lower()
    zones    = img_result.get("zones_suspectes", "").lower()
    anomalie = any(k in morpho for k in ["sessile","pédiculé","pedunculated","plan","depressed"]) or \
               any(k in zones  for k in ["suspect","anormal","irregular","lesion"])

    if gravite == "indeterminee" or status in ["error","modele_incompatible","echec"] or anomalie:
        img_result["gravite"]        = "suspecte"
        img_result["recommandation"] = "Lésion suspecte — Validation humaine obligatoire."
        img_result["conservative_mode"] = True
        img_result["polype_detecte"] = img_result.get("polype_detecte", False) or anomalie
    return img_result


def _run_yolo(image_files: list) -> list:
    """Tente YOLO, fallback sur image_analyzer si modèle absent."""
    results = []
    yolo_ok = os.path.exists("models/best.pt")

    for img in image_files:
        fname = getattr(img, 'name', str(img))
        temp_path = f"temp_uploads/tmp_{fname}"
        os.makedirs("temp_uploads", exist_ok=True)

        try:
            if hasattr(img, 'getbuffer'):
                with open(temp_path, "wb") as f:
                    f.write(img.getbuffer())
            elif hasattr(img, 'read'):
                with open(temp_path, "wb") as f:
                    f.write(img.read())
            else:
                temp_path = img  # chemin direct

            if yolo_ok:
                from modules.yolo_detector import analyze_image_full_pipeline
                pr = analyze_image_full_pipeline(temp_path)
                r  = {
                    "type": "yolo",
                    "filename": fname,
                    "yolo": pr["yolo"],
                    "rapport": pr["rapport_gemma4"],
                    "analyse_status": "success"
                }
            else:
                r = analyze_colonoscopy_image(temp_path)
                r = apply_conservative_security(r)
                r["filename"] = fname
                r["type"] = "gemma_vision"

        except Exception as e:
            r = {
                "filename": fname, "type": "error",
                "polype_detecte": False, "gravite": "indeterminee",
                "recommandation": "Analyse manuelle requise",
                "analyse_status": "error", "error": str(e)
            }
        finally:
            if os.path.exists(temp_path) and temp_path != img:
                try: os.remove(temp_path)
                except: pass

        results.append(r)
    return results


def run_pipeline(text_files=None, image_files=None) -> dict:
    """
    3 scénarios :
      - text only   : extraction médicale complète
      - image only  : YOLO + rapport simple
      - text+image  : extraction + YOLO + fusion

    Retourne un dict de résultats à afficher.
    RIEN n'est sauvegardé en DB ici.
    """
    start   = time.time()
    errors  = []
    steps   = {}
    scenario = "unknown"

    has_text = bool(text_files)
    has_img  = bool(image_files)

    if   has_text and has_img:  scenario = "text_image"
    elif has_text:               scenario = "text_only"
    elif has_img:                scenario = "image_only"

    # ── Valeurs par défaut ──
    all_text      = ""
    medical_data  = {}
    validation    = {"status": "non_confirme", "message": "Aucun document texte fourni", "confidence": 0}
    completude    = {"taux_completude": 0, "fiabilite": "faible", "champs_manquants": [], "action_recommandee": "RCP"}
    score_data    = {"score": 0, "niveau": "stable", "label": "STABLE", "delai": "À définir", "facteurs": [], "summary": "", "human_validation_required": True}
    orientation   = {"decision": "incertain", "specialite": "RCP", "service": "RCP", "traitement": "", "protocole": "", "confidence": 0, "raison": "Données insuffisantes", "stage_group": "Stage inconnu", "delai": "RCP 5 jours", "rcp_requis": True, "human_validation_required": True, "esmo_reference": "N/A", "esmo_chimio": "N/A", "survie_5ans": "N/A", "surveillance": "N/A", "emoji": "🟡"}
    explanation   = {"preuves_dossier": [], "regles_activees": [], "resume_clinique": "", "raison_principale": "", "confiance_label": "Faible", "confiance_explication": "", "stage_group": "Stage inconnu", "validation_humaine": True}
    recurrence    = {"risk_score": 0, "niveau_risque": "Non calculé", "facteurs": [], "chimio_adjuvante_recommandee": False, "frequence_surveillance": "6 mois"}
    image_results = []
    fusion        = {}

    # ════════ TEXTE ════════
    if has_text:
        try:
            for f in text_files:
                if hasattr(f, 'read'):
                    content = f.read()
                    if f.name.endswith('.pdf'):
                        from modules.pdf_reader import read_pdf_upload
                        all_text += read_pdf_upload(content) + "\n\n"
                    else:
                        all_text += content.decode("utf-8", errors="ignore") + "\n\n"
                elif isinstance(f, str):
                    all_text += read_txt_file(f) + "\n\n"
            steps["lecture"] = {"status": "ok", "chars": len(all_text)}
        except Exception as e:
            steps["lecture"] = {"status": "error", "error": str(e)}
            errors.append(f"Lecture: {e}")

        if all_text.strip():
            try:
                from modules.pdf_reader import extract_medical_sections
                medical_data = extract_medical_json(extract_medical_sections(all_text))
                steps["extraction"] = {"status": medical_data.get("extraction_status","?"), "stade": f"{medical_data.get('stade_T','?')}{medical_data.get('stade_N','?')}{medical_data.get('stade_M','?')}"}
            except Exception as e:
                steps["extraction"] = {"status": "error", "error": str(e)}
                errors.append(f"Extraction: {e}")
                medical_data = {"cancer_confirme": False, "stade_T": "inconnu", "stade_N": "inconnu", "stade_M": "inconnu", "metastases": False, "urgence": "faible", "extraction_status": "error"}

            try: validation  = validate_diagnosis(all_text, medical_data)
            except Exception as e: errors.append(f"Validation: {e}")

            try: completude  = check_data_completeness(medical_data)
            except Exception as e: errors.append(f"Completude: {e}")

            try:
                score_data = calculate_priority_score(medical_data)
                steps["scoring"] = {"status": "ok", "score": score_data.get("score", 0)}
            except Exception as e:
                errors.append(f"Scoring: {e}")

            try:
                orientation = decide_orientation(medical_data)
                steps["orientation"] = {"status": "ok"}
            except Exception as e:
                errors.append(f"Orientation: {e}")

            try:
                explanation = generate_explanation(medical_data, orientation, score_data)
                steps["explainability"] = {"status": "ok"}
            except Exception as e:
                errors.append(f"Explainability: {e}")

            try:
                recurrence = calculate_recurrence_risk(medical_data, orientation)
                steps["recurrence"] = {"status": "ok"}
            except Exception as e:
                errors.append(f"Recurrence: {e}")

    # ════════ IMAGES ════════
    if has_img:
        try:
            image_results = _run_yolo(image_files)
            steps["imagerie"] = {"status": "ok", "count": len(image_results)}
        except Exception as e:
            steps["imagerie"] = {"status": "error", "error": str(e)}
            errors.append(f"Images: {e}")

        # Scénario image only → construire données minimales
        if not has_text and image_results:
            first = image_results[0]
            yolo_r   = first.get("yolo", first)
            rapport_r = first.get("rapport", {})
            polype = yolo_r.get("polype_detecte", False)
            gravite = yolo_r.get("gravite", "normale")

            medical_data = {
                "cancer_confirme": polype,
                "stade_T": "inconnu", "stade_N": "inconnu", "stade_M": "inconnu",
                "metastases": False,
                "urgence": "haute" if gravite == "urgente" else ("moyenne" if polype else "faible"),
                "type_histologique": "polype" if polype else "normal",
                "localisation": "côlon",
                "contexte_patient": rapport_r.get("resume_clinique", "Analyse image"),
                "extraction_status": "vision_only",
                "complications": "aucune",
                "marqueurs_bio": "non mentionnés",
                "traitement_realise": "aucun",
                "traitement_anterieur": "aucun"
            }

            try: score_data  = calculate_priority_score(medical_data)
            except: pass
            try: orientation = decide_orientation(medical_data)
            except: pass
            try: explanation = generate_explanation(medical_data, orientation, score_data)
            except: pass
            try: recurrence  = calculate_recurrence_risk(medical_data, orientation)
            except: pass
            try: validation  = validate_diagnosis("", medical_data)
            except: pass
            try: completude  = check_data_completeness(medical_data)
            except: pass

    # ════════ FUSION ════════
    if has_text and has_img and image_results:
        try:
            img_summary = None
            first = image_results[0]
            if first.get("type") == "yolo":
                img_summary = first.get("yolo", {})
            else:
                img_summary = first
            fusion = fuse_analysis(medical_data, img_summary)
            steps["fusion"] = {"status": "ok"}
        except Exception as e:
            errors.append(f"Fusion: {e}")

    elapsed = round(time.time() - start, 2)

    return {
        "scenario":      scenario,
        "pipeline_meta": {"steps": steps, "errors": errors, "elapsed": elapsed, "status": "completed" if not errors else "completed_with_errors"},
        "medical_data":  medical_data,
        "validation":    validation,
        "completude":    completude,
        "score_data":    score_data,
        "orientation":   orientation,
        "explanation":   explanation,
        "recurrence":    recurrence,
        "image_results": image_results,
        "fusion":        fusion,
        "all_text":      all_text
    }