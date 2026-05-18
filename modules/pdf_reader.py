# modules/pdf_reader.py

import fitz  # PyMuPDF
import re


def read_pdf_file(file_path: str) -> str:
    try:
        doc = fitz.open(file_path)
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return _clean_text("\n".join(pages))
    except Exception as e:
        return f"ERREUR lecture PDF: {str(e)}"


def read_pdf_upload(file_bytes: bytes) -> str:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return _clean_text("\n".join(pages))
    except Exception as e:
        return f"ERREUR lecture PDF: {str(e)}"


def read_txt_file(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        return f"ERREUR lecture TXT: {str(e)}"


def _clean_text(text: str) -> str:
    """
    Nettoyage intelligent — préserve les informations médicales critiques
    """
    # Supprimer caractères de contrôle sauf newlines
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
    # Normaliser les espaces multiples SANS supprimer les newlines
    text = re.sub(r'[ \t]+', ' ', text)
    # Normaliser les newlines multiples
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_medical_sections(text: str) -> str:
    """
    Extrait les sections médicales critiques du texte
    pour maximiser la qualité d'extraction TNM.
    Retourne un texte condensé avec priorité aux infos cliniques.
    """
    lines = text.split('\n')
    priority_lines = []
    normal_lines = []

    # Mots-clés critiques médicaux
    priority_keywords = [
        'tnm', 'stage', 'stade', 't1', 't2', 't3', 't4',
        'n0', 'n1', 'n2', 'm0', 'm1', 'adenocarcinoma', 'adénocarcinome',
        'carcinoma', 'cancer', 'tumor', 'tumeur', 'metastas', 'métastas',
        'folfox', 'folfiri', 'bevacizumab', 'cetuximab', 'chemotherapy',
        'colectomy', 'colectomie', 'resection', 'résection', 'surgery',
        'pathology', 'pathologie', 'histol', 'biopsy', 'biopsie',
        'cea', 'ca19', 'lymph', 'ganglion', 'node', 'margin', 'marge',
        'diagnosis', 'diagnostic', 'impression', 'conclusion', 'assessment',
        'staging', 'classification', 'grade', 'differentiat',
        'remission', 'rémission', 'recurrence', 'récidive',
        'postoperative', 'post-opératoire', 'discharge', 'sortie'
    ]

    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in priority_keywords):
            priority_lines.append(line)
        else:
            normal_lines.append(line)

    # Construire texte condensé : sections prioritaires d'abord
    priority_text = '\n'.join(priority_lines)
    normal_text = '\n'.join(normal_lines)

    # Budget : 3000 chars pour priorité + 1000 pour contexte normal
    result = priority_text[:3000]
    if len(result) < 2500 and normal_text:
        result += '\n\n' + normal_text[:1000]

    return result.strip()