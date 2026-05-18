# modules/database.py
# Base SQLite locale — persistance complète
# FIX : doublons patients, champs manquants, conversations liées patients

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "colocare_md.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialise toutes les tables"""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id TEXT PRIMARY KEY,
            nom TEXT NOT NULL,
            type_dossier TEXT,
            date_analyse TEXT,
            statut TEXT DEFAULT 'actif',
            score INTEGER DEFAULT 0,
            stade TEXT,
            stage_group TEXT,
            orientation TEXT,
            delai TEXT,
            urgence_label TEXT,
            docs_count INTEGER DEFAULT 0,
            images_count INTEGER DEFAULT 0,
            validation_medecin TEXT DEFAULT 'en_attente',
            validation_date TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            patient_id TEXT UNIQUE,
            medical_data TEXT,
            score_data TEXT,
            orientation_data TEXT,
            explanation TEXT,
            recurrence TEXT,
            validation TEXT,
            completude TEXT,
            image_results TEXT,
            fusion TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            patient_id TEXT DEFAULT '',
            titre TEXT,
            date TEXT,
            messages TEXT DEFAULT '[]',
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            patient_id TEXT,
            action TEXT,
            details TEXT
        )
    """)

    conn.commit()
    conn.close()


# ══════════════════════════════════════════
# PATIENTS CRUD — FIX doublons via INSERT OR REPLACE
# ══════════════════════════════════════════

def save_patient(patient_record: dict):
    """Sauvegarde ou met à jour un patient — pas de doublon"""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT OR REPLACE INTO patients
        (id, nom, type_dossier, date_analyse, statut, score,
         stade, stage_group, orientation, delai, urgence_label,
         docs_count, images_count, validation_medecin, validation_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        patient_record["id"],
        patient_record["nom"],
        patient_record.get("type", "Bilan initial"),
        patient_record.get("date_analyse", datetime.now().strftime("%d/%m/%Y %H:%M")),
        patient_record.get("statut", "actif"),
        patient_record.get("score", 0),
        patient_record.get("stade", ""),
        patient_record.get("stage_group", ""),
        patient_record.get("orientation", ""),
        patient_record.get("delai", ""),
        patient_record.get("urgence", ""),
        patient_record.get("docs_count", 0),
        patient_record.get("images_count", 0),
        patient_record.get("validation_medecin", "en_attente"),
        patient_record.get("validation_date", ""),
        datetime.now().isoformat()
    ))

    # FIX : INSERT OR REPLACE sur analyses aussi pour éviter doublons
    c.execute("""
        INSERT OR REPLACE INTO analyses
        (id, patient_id, medical_data, score_data, orientation_data,
         explanation, recurrence, validation, completude, image_results, fusion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        patient_record["id"],
        patient_record["id"],
        json.dumps(patient_record.get("medical_data", {}), ensure_ascii=False),
        json.dumps(patient_record.get("score_data", {}), ensure_ascii=False),
        json.dumps(patient_record.get("orientation_data", {}), ensure_ascii=False),
        json.dumps(patient_record.get("explanation", {}), ensure_ascii=False),
        json.dumps(patient_record.get("recurrence", {}), ensure_ascii=False),
        json.dumps(patient_record.get("validation", {}), ensure_ascii=False),
        json.dumps(patient_record.get("completude", {}), ensure_ascii=False),
        json.dumps(patient_record.get("image_results", []), ensure_ascii=False),
        json.dumps(patient_record.get("fusion", {}), ensure_ascii=False)
    ))

    conn.commit()
    conn.close()


def get_all_patients(statut_filter: str = None) -> list:
    """Récupère tous les patients triés par score décroissant"""
    conn = get_connection()
    c = conn.cursor()

    if statut_filter and statut_filter != "tous":
        c.execute("""
            SELECT p.*, a.medical_data, a.score_data, a.orientation_data,
                   a.explanation, a.recurrence, a.validation, a.completude,
                   a.image_results, a.fusion
            FROM patients p
            LEFT JOIN analyses a ON p.id = a.patient_id
            WHERE p.statut = ?
            ORDER BY p.score DESC
        """, (statut_filter,))
    else:
        c.execute("""
            SELECT p.*, a.medical_data, a.score_data, a.orientation_data,
                   a.explanation, a.recurrence, a.validation, a.completude,
                   a.image_results, a.fusion
            FROM patients p
            LEFT JOIN analyses a ON p.id = a.patient_id
            ORDER BY p.score DESC
        """)

    rows = c.fetchall()
    conn.close()

    patients = []
    for row in rows:
        p = dict(row)
        for field in ["medical_data", "score_data", "orientation_data",
                      "explanation", "recurrence", "validation",
                      "completude", "image_results", "fusion"]:
            if p.get(field):
                try:
                    p[field] = json.loads(p[field])
                except:
                    p[field] = {} if field != "image_results" else []
            else:
                p[field] = {} if field != "image_results" else []
        patients.append(p)

    return patients


def get_patient_by_id(patient_id: str) -> dict:
    """Récupère un patient par son ID"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT p.*, a.medical_data, a.score_data, a.orientation_data,
               a.explanation, a.recurrence, a.validation, a.completude,
               a.image_results, a.fusion
        FROM patients p
        LEFT JOIN analyses a ON p.id = a.patient_id
        WHERE p.id = ?
    """, (patient_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return None

    p = dict(row)
    for field in ["medical_data", "score_data", "orientation_data",
                  "explanation", "recurrence", "validation",
                  "completude", "image_results", "fusion"]:
        if p.get(field):
            try:
                p[field] = json.loads(p[field])
            except:
                p[field] = {} if field != "image_results" else []
        else:
            p[field] = {} if field != "image_results" else []
    return p


def update_patient_status(patient_id: str, statut: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE patients SET statut = ? WHERE id = ?", (statut, patient_id))
    conn.commit()
    conn.close()


def update_validation_medecin(patient_id: str, validation: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE patients SET validation_medecin = ?, validation_date = ? WHERE id = ?",
        (validation, datetime.now().strftime("%d/%m/%Y %H:%M"), patient_id)
    )
    conn.commit()
    conn.close()


def update_patient_notes(patient_id: str, field: str, value: str):
    """Met à jour un champ d'analyse patient (pour le mode modification médecin)"""
    conn = get_connection()
    c = conn.cursor()
    # Récupérer les données existantes
    c.execute("SELECT orientation_data, explanation FROM analyses WHERE patient_id = ?", (patient_id,))
    row = c.fetchone()
    if row:
        try:
            orientation = json.loads(row[0]) if row[0] else {}
            explanation = json.loads(row[1]) if row[1] else {}
        except:
            orientation = {}
            explanation = {}

        if field == "resume_clinique":
            explanation["resume_clinique"] = value
            c.execute("UPDATE analyses SET explanation = ? WHERE patient_id = ?",
                      (json.dumps(explanation, ensure_ascii=False), patient_id))
        elif field == "orientation_notes":
            orientation["notes_medecin"] = value
            c.execute("UPDATE analyses SET orientation_data = ? WHERE patient_id = ?",
                      (json.dumps(orientation, ensure_ascii=False), patient_id))

    conn.commit()
    conn.close()


def delete_patient_db(patient_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM analyses WHERE patient_id = ?", (patient_id,))
    c.execute("DELETE FROM conversations WHERE patient_id = ?", (patient_id,))
    c.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════
# CONVERSATIONS CRUD
# ══════════════════════════════════════════

def save_conversation_db(conversation: dict, patient_id: str = ""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO conversations
        (id, patient_id, titre, date, messages, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        conversation["id"],
        patient_id or "",
        conversation.get("titre", "Nouvelle discussion"),
        conversation.get("date", ""),
        json.dumps(conversation.get("messages", []), ensure_ascii=False),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def get_all_conversations_db(patient_id: str = None) -> list:
    conn = get_connection()
    c = conn.cursor()
    if patient_id:
        c.execute(
            "SELECT * FROM conversations WHERE patient_id = ? ORDER BY created_at DESC",
            (patient_id,)
        )
    else:
        c.execute("SELECT * FROM conversations ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()

    convs = []
    for row in rows:
        conv = dict(row)
        try:
            conv["messages"] = json.loads(conv.get("messages", "[]"))
        except:
            conv["messages"] = []
        convs.append(conv)
    return convs


def delete_conversation_db(conv_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()


def add_log(patient_id: str, action: str, details: str = ""):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO logs (date, patient_id, action, details) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), patient_id, action, details)
    )
    conn.commit()
    conn.close()

# ── AJOUTER à la fin de database.py ──

def save_pending_analysis(patient_id: str, result: dict):
    """
    Sauvegarde temporaire en mémoire (session).
    Utilisé AVANT validation médecin.
    Ne touche PAS à la vraie table patients.
    """
    import json, os
    os.makedirs("temp_uploads", exist_ok=True)
    path = f"temp_uploads/pending_{patient_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        # Exclure all_text (trop lourd)
        to_save = {k: v for k, v in result.items() if k != "all_text"}
        json.dump(to_save, f, ensure_ascii=False)


def load_pending_analysis(patient_id: str) -> dict:
    """Charge l'analyse temporaire."""
    import json
    path = f"temp_uploads/pending_{patient_id}.json"
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_pending_analysis(patient_id: str):
    """Supprime le fichier temporaire après validation."""
    path = f"temp_uploads/pending_{patient_id}.json"
    if os.path.exists(path):
        try: os.remove(path)
        except: pass
# Initialisation automatique au import
init_database()
