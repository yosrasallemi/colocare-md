# create_demo_patients.py

import os

os.makedirs("data/sample_patients/patient_001", exist_ok=True)
os.makedirs("data/sample_patients/patient_002", exist_ok=True)
os.makedirs("data/sample_patients/patient_003", exist_ok=True)
os.makedirs("data/sample_patients/patient_004", exist_ok=True)

p001_emergency = """
EMERGENCY ROOM REPORT
Date: 2024-03-15 | Department: Emergency Surgery
Patient: Male, 62 years old
Chief Complaint: Severe abdominal pain 3 days, rectal bleeding, inability to pass stool.
Vital Signs: BP 110/70, HR 98, Temp 37.8C
CT Scan Emergency: Large obstructing mass in sigmoid colon. Partial large bowel obstruction.
No free air. No distant metastases.
CEA: 18.5 ng/mL (elevated). CA19-9: 45 U/mL (elevated).
Clinical Impression: Suspected sigmoid colon cancer with partial bowel obstruction. High urgency.
Plan: Emergency surgical consultation. NPO. IV fluids. Bowel decompression.
"""

p001_pathology = """
SURGICAL PATHOLOGY REPORT
Specimen: Sigmoid colon resection
Patient: Male, 62 years | Date: 2024-03-17
MICROSCOPIC DESCRIPTION:
Moderately differentiated adenocarcinoma (Grade 2).
Tumor invades through muscularis propria into pericolorectal tissues.
Lymphovascular invasion: PRESENT.
TUMOR STAGING (AJCC/UICC 8th Edition):
Primary tumor (pT): pT3
Regional lymph nodes (pN): pN1a — 1 of 18 lymph nodes positive
Distant metastasis (pM): M0
OVERALL STAGE: Stage IIIA (pT3N1aM0)
MSI Status: pMMR. KRAS: Wild-type. BRAF: Wild-type.
CONCLUSION: Moderately differentiated sigmoid colon adenocarcinoma, pT3N1aM0, Stage IIIA.
Complete resection (R0). Recommend adjuvant chemotherapy discussion.
"""

p001_operative = """
OPERATIVE REPORT
Procedure: Laparoscopic Sigmoid Colectomy
Surgeon: Dr. Ahmed Ben Salah, Visceral Surgery
Date: 2024-03-17
PRE-OPERATIVE DIAGNOSIS: Sigmoid colon cancer with partial obstruction
POST-OPERATIVE DIAGNOSIS: Moderately differentiated adenocarcinoma sigmoid, pT3N1aM0
ESTIMATED BLOOD LOSS: 180 mL. COMPLICATIONS: None intraoperative.
End-to-end colorectal anastomosis performed. No residual tumor visible.
"""

p001_discharge = """
DISCHARGE SUMMARY
Patient: Male, 62 years | Admission: 2024-03-15 | Discharge: 2024-03-24
PRINCIPAL DIAGNOSIS: Sigmoid colon adenocarcinoma, pT3N1aM0, Stage IIIA
ADJUVANT TREATMENT PLAN: FOLFOX chemotherapy x12 cycles (6 months).
CEA at discharge: 6.2 ng/mL (improving from 18.5).
FOLLOW-UP: Oncology visit 2 weeks. CT every 6 months. CEA every 3 months.
PROGNOSIS: Stage IIIA with adjuvant chemotherapy — 5-year survival approximately 65%.
"""

p002_consultation = """
ONCOLOGY CONSULTATION REPORT
Patient: Female, 58 years | Date: 2024-04-10
TUMOR ASSESSMENT:
Primary: Large mass ascending colon 6.2 x 4.8 cm
Histology: Moderately differentiated adenocarcinoma
Molecular: KRAS wild-type, BRAF wild-type
STAGING CT SCAN:
- Primary tumor: Ascending colon, 6.2 cm, T4a
- Regional lymph nodes: Multiple enlarged N2b (>4 nodes)
- Liver metastases: Multiple bilateral, largest 3.5 cm — M1a
FINAL STAGING: T4aN2bM1a — Stage IV (metastatic colorectal cancer)
CEA: 245 ng/mL. CA19-9: 180 U/mL.
TREATMENT PLAN: FOLFOX + Bevacizumab first-line.
PROGNOSIS: Stage IV. Median OS 24-30 months with modern chemotherapy.
"""

p003_followup = """
POST-OPERATIVE FOLLOW-UP REPORT — 6 MONTHS
Patient: Male, 55 years | Date: 2024-05-20
ORIGINAL DIAGNOSIS: Ascending colon adenocarcinoma, well differentiated, pT2N0M0, Stage I
Surgery: Right hemicolectomy — January 2024
PATHOLOGY: pT2N0M0 — well differentiated. 0 of 22 lymph nodes positive. MSI-H.
SURVEILLANCE RESULTS:
CT Abdomen/Pelvis: No evidence of recurrence or metastatic disease.
CEA: 2.1 ng/mL (normal). CA19-9: 12 U/mL (normal).
ASSESSMENT: Complete remission. No evidence of disease at 6 months.
Estimated 5-year disease-free survival: >90%.
FOLLOW-UP: CT every 6 months. CEA every 3 months. Colonoscopy at 1 year.
"""

p004_recurrence = """
ONCOLOGY REPORT — SUSPECTED RECURRENCE
Patient: Female, 67 years | Date: 2024-06-15
Previous: Sigmoid colon adenocarcinoma T3N2M0 — treated 2022
HISTORY: pT3N2aM0 treated with laparoscopic sigmoidectomy + FOLFOX x12 cycles.
Declared disease-free December 2022.
CT SCAN FINDINGS:
- Previous anastomosis: Thickening suspicious — 2.8 cm lesion
- Liver: 2 new lesions (1.2 cm right lobe, 0.8 cm left lobe)
- Peritoneum: 2-3 small nodules suspicious peritoneal carcinomatosis
CEA: 45.6 ng/mL (was 2.8 ng/mL — significant rise). CA19-9: 89 U/mL.
BIOPSY: Metastatic adenocarcinoma. KRAS: Mutant (G12D).
STAGING: Recurrent colorectal cancer, Stage IV — T_recurrence N2 M1b
COMPLICATIONS: Peritoneal carcinomatosis suspected.
Prior treatment: FOLFOX x12 cycles (completed 2022).
MULTIDISCIPLINARY DISCUSSION REQUIRED — URGENT RCP
Decision pending: FOLFIRI + Bevacizumab vs clinical trial.
HIPEC eligibility evaluation needed.
"""

files_to_create = {
    "data/sample_patients/patient_001/01_emergency_report.txt": p001_emergency,
    "data/sample_patients/patient_001/02_pathology_report.txt": p001_pathology,
    "data/sample_patients/patient_001/03_operative_report.txt": p001_operative,
    "data/sample_patients/patient_001/04_discharge_summary.txt": p001_discharge,
    "data/sample_patients/patient_002/01_oncology_consultation.txt": p002_consultation,
    "data/sample_patients/patient_003/01_followup_6months.txt": p003_followup,
    "data/sample_patients/patient_004/01_recurrence_report.txt": p004_recurrence,
}

for path, content in files_to_create.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"✅ Créé : {path}")

print("\n🎉 4 dossiers patients simulés créés !")
print("→ Patient 001 : Homme 62 ans — Stade IIIA T3N1M0 — Score attendu ~75/100 🔴")
print("→ Patient 002 : Femme 58 ans — Stade IV T4aN2bM1a — Score attendu ~92/100 🔴")
print("→ Patient 003 : Homme 55 ans — Stade I T2N0M0 — Score attendu ~18/100 🟢")
print("→ Patient 004 : Femme 67 ans — Récidive Stade IV — Score attendu ~85/100 🔴")