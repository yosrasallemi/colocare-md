# modules/yolo_detector.py
# Détection YOLO + rapport Gemma 4 

import os
import json
import numpy as np
from modules.gemma_client import ask_gemma

# Chemin du modèle YOLO entraîné
YOLO_MODEL_PATH = "models/best.pt"

# Seuil de confiance pour détection
CONFIDENCE_THRESHOLD = 0.25


def load_yolo_model():
    """Charge le modèle YOLO une seule fois"""
    try:
        from ultralytics import YOLO
        if not os.path.exists(YOLO_MODEL_PATH):
            return None, f"Modèle YOLO non trouvé : {YOLO_MODEL_PATH}"
        model = YOLO(YOLO_MODEL_PATH)
        return model, None
    except ImportError:
        return None, "ultralytics non installé — pip install ultralytics"
    except Exception as e:
        return None, str(e)


def detect_polyps_yolo(image_path: str) -> dict:
    """
    Détection YOLO de polypes sur une image de coloscopie.
    Retourne les détections avec bounding boxes et scores de confiance.
    """
    model, error = load_yolo_model()

    if model is None:
        return {
            "yolo_disponible": False,
            "erreur": error,
            "detections": [],
            "polype_detecte": False,
            "nombre_polypes": 0,
            "confidence_max": 0.0
        }

    try:
        results = model(image_path, conf=CONFIDENCE_THRESHOLD, verbose=False)

        detections = []
        confidence_max = 0.0

        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                xyxy = box.xyxy[0].tolist()

                detections.append({
                    "confidence": round(conf, 3),
                    "class": cls,
                    "class_name": "polyp",
                    "bbox": {
                        "x1": round(xyxy[0], 1),
                        "y1": round(xyxy[1], 1),
                        "x2": round(xyxy[2], 1),
                        "y2": round(xyxy[3], 1)
                    }
                })

                if conf > confidence_max:
                    confidence_max = conf

        polype_detecte = len(detections) > 0

        # Classification du risque selon confiance
        if not polype_detecte:
            risque = "faible"
            gravite = "normale"
        elif confidence_max >= 0.85:
            risque = "élevé"
            gravite = "urgente"
        elif confidence_max >= 0.60:
            risque = "modéré"
            gravite = "suspecte"
        else:
            risque = "incertain"
            gravite = "suspecte"

        return {
            "yolo_disponible": True,
            "polype_detecte": polype_detecte,
            "nombre_polypes": len(detections),
            "confidence_max": round(confidence_max, 3),
            "risque": risque,
            "gravite": gravite,
            "detections": detections,
            "erreur": None
        }

    except Exception as e:
        return {
            "yolo_disponible": True,
            "polype_detecte": False,
            "nombre_polypes": 0,
            "confidence_max": 0.0,
            "risque": "inconnu",
            "gravite": "indeterminee",
            "detections": [],
            "erreur": str(e)
        }


def generate_clinical_report_gemma4(yolo_result: dict, image_path: str = None) -> str:
    """
    Génère un rapport clinique complet avec Gemma 4
    basé sur les résultats YOLO.
    """
    nb = yolo_result.get("nombre_polypes", 0)
    conf = yolo_result.get("confidence_max", 0)
    risque = yolo_result.get("risque", "inconnu")
    gravite = yolo_result.get("gravite", "indeterminee")
    polype = yolo_result.get("polype_detecte", False)
    detections = yolo_result.get("detections", [])

    # Construire le contexte pour Gemma 4
    if polype:
        detection_context = f"""
Le système YOLO a détecté {nb} lésion(s) suspecte(s).
Confiance maximale : {conf:.0%}
Niveau de risque estimé : {risque}
Gravité : {gravite}
Détails des détections : {json.dumps(detections, indent=2)}
"""
    else:
        detection_context = """
Le système YOLO n'a détecté aucune lésion suspecte sur cette image.
Confiance : analyse négative.
"""

    prompt = f"""Tu es un gastroentérologue expert en endoscopie colorectale.

Un système d'intelligence artificielle (YOLO) a analysé une image de coloscopie.
Voici les résultats de détection :

{detection_context}

Génère un rapport clinique structuré en JSON strict :
{{
    "resume_clinique": "description médicale en 2-3 phrases",
    "lesion_caracteristiques": {{
        "morphologie_probable": "sessile ou pédiculé ou plan ou non applicable",
        "taille_estimee": "estimation ou non évaluable",
        "localisation_probable": "description ou non précisée",
        "aspect_endoscopique": "description ou normal"
    }},
    "evaluation_risque": {{
        "niveau": "faible ou modéré ou élevé",
        "score_malignite": "faible ou modéré ou élevé",
        "classification_paris_probable": "type ou non applicable"
    }},
    "recommandations_specialiste": [
        "recommandation 1",
        "recommandation 2"
    ],
    "examen_complementaire": "biopsie ou polypectomie ou surveillance ou coloscopie contrôle",
    "urgence_prise_en_charge": "immediate ou planifiee ou surveillance",
    "explication_patient": "explication simple en langage accessible",
    "disclaimer": "Ce rapport est généré par IA à titre indicatif uniquement. Le gastroentérologue valide la décision finale."
}}

Réponds UNIQUEMENT avec le JSON."""

    raw = ask_gemma(prompt)

    # Parser la réponse
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
            "resume_clinique": raw[:300] if raw else "Rapport non généré",
            "lesion_caracteristiques": {},
            "evaluation_risque": {"niveau": risque},
            "recommandations_specialiste": ["Consultation gastroentérologue recommandée"],
            "examen_complementaire": "biopsie si lésion confirmée",
            "urgence_prise_en_charge": "planifiee",
            "explication_patient": "Une analyse a été effectuée. Votre médecin vous expliquera les résultats.",
            "disclaimer": "Ce rapport est généré par IA. Le médecin valide la décision finale."
        }


def analyze_image_full_pipeline(image_path: str) -> dict:
    """
    Pipeline complet : YOLO → Gemma 4 → Rapport clinique
    """
    # Étape 1 — Détection YOLO
    yolo_result = detect_polyps_yolo(image_path)

    # Étape 2 — Rapport Gemma 4
    clinical_report = generate_clinical_report_gemma4(yolo_result, image_path)

    # Étape 3 — Résultat fusionné
    return {
        "yolo": yolo_result,
        "rapport_gemma4": clinical_report,
        "pipeline": "YOLO + Gemma 4",
        "image_path": image_path
    }


def draw_detections_on_image(image_path: str, yolo_result: dict) -> str:
    """
    Dessine les bounding boxes sur l'image et sauvegarde.
    Retourne le chemin de l'image annotée.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        detections = yolo_result.get("detections", [])

        for det in detections:
            bbox = det["bbox"]
            conf = det["confidence"]
            x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]

            # Couleur selon confiance
            if conf >= 0.85:
                color = "#DC2626"   # rouge — haute confiance
            elif conf >= 0.60:
                color = "#D97706"   # orange — confiance modérée
            else:
                color = "#2563EB"   # bleu — faible confiance

            # Dessiner bounding box
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

            # Label confiance
            label = f"Polyp {conf:.0%}"
            draw.rectangle([x1, y1 - 20, x1 + len(label) * 7, y1], fill=color)
            draw.text((x1 + 2, y1 - 18), label, fill="white")

        # Sauvegarder image annotée
        os.makedirs("temp_annotated", exist_ok=True)
        base_name = os.path.basename(image_path)
        output_path = f"temp_annotated/annotated_{base_name}"
        img.save(output_path)
        return output_path

    except Exception as e:
        return image_path  # Retourner image originale si erreur


def get_benchmark_metrics() -> dict:
    """
    Métriques de validation du modèle YOLO
    (résultats du benchmark.py)
    """
    return {
        "true_positives": 41,
        "false_negatives": 1,
        "true_negatives": 11,
        "false_positives": 2,
        "accuracy": 0.95,
        "sensitivity": 0.98,
        "specificity": 0.85,
        "total_images_tested": 55,
        "dataset": "Kvasir-SEG",
        "model": "YOLOv8 custom trained"
    }