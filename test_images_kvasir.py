# test_images_kvasir.py

import os
import json
from modules.image_analyzer import analyze_colonoscopy_image, get_image_recommendation
from modules.pipeline import apply_conservative_security

KVASIR_PATH = "datasets/kvasir/images"
RESULTS_PATH = "logs/kvasir_test_results.json"


def test_kvasir_batch(max_images: int = 20):
    if not os.path.exists(KVASIR_PATH):
        print(f"❌ Dossier Kvasir non trouvé : {KVASIR_PATH}")
        return

    images = [
        f for f in os.listdir(KVASIR_PATH)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ][:max_images]

    results = []
    polypes_detectes = 0
    erreurs = 0

    print(f"🔍 Test sur {len(images)} images Kvasir-SEG...")

    for i, img_name in enumerate(images):
        img_path = os.path.join(KVASIR_PATH, img_name)
        print(f"  [{i+1}/{len(images)}] {img_name}...", end=" ")

        try:
            result = analyze_colonoscopy_image(img_path)
            result = apply_conservative_security(result)

            if result.get("polype_detecte"):
                polypes_detectes += 1
                print("🔴 POLYPE")
            else:
                print(f"⚪ {result.get('gravite','?')}")

            results.append({
                "image": img_name,
                "polype_detecte": result.get("polype_detecte", False),
                "gravite": result.get("gravite", "?"),
                "recommandation": result.get("recommandation", ""),
                "conservative_mode": result.get("conservative_mode", False),
                "status": result.get("analyse_status", "?")
            })

        except Exception as e:
            erreurs += 1
            print(f"❌ Erreur: {e}")
            results.append({"image": img_name, "error": str(e)})

    total = len(results)
    taux_detection = round(polypes_detectes / total * 100, 1) if total > 0 else 0
    taux_erreur = round(erreurs / total * 100, 1) if total > 0 else 0

    summary = {
        "total_images": total,
        "polypes_detectes": polypes_detectes,
        "taux_detection": f"{taux_detection}%",
        "erreurs": erreurs,
        "taux_erreur": f"{taux_erreur}%",
        "resultats": results
    }

    os.makedirs("logs", exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n📊 RÉSULTATS KVASIR-SEG :")
    print(f"   Total : {total} images")
    print(f"   Polypes détectés : {polypes_detectes} ({taux_detection}%)")
    print(f"   Erreurs : {erreurs} ({taux_erreur}%)")
    print(f"   Résultats : {RESULTS_PATH}")

    return summary


if __name__ == "__main__":
    test_kvasir_batch(max_images=20)