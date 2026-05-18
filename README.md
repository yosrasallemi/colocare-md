# 🏥 ColoCare MD

AI Clinical Copilot for Colorectal Cancer Care

Built for the Gemma 4 Good Hackathon (Google × Kaggle)

---

## Problem

Colorectal cancer remains one of the leading causes of cancer-related mortality worldwide. Healthcare professionals often need to analyze multiple pathology reports, imaging studies, colonoscopy findings, and clinical information before making treatment decisions.

In some healthcare environments, increasing workloads, limited infrastructure, and unstable connectivity can create additional challenges.

---

## Solution

ColoCare MD is an offline AI-powered clinical assistant designed to support physicians in colorectal cancer workflows.

ColoCare MD uses **Gemma 4 via Ollama** to:

### Main capabilities

- Medical report understanding and automatically analyze medical PDF reports
- Colonoscopy lesion detection
- Priority scoring
- Fully offline deployment
- Extract structured clinical data (JSON)
- Apply ESMO/TNM clinical rules
- Calculate priority scores (0–100)
- Recommend surgical or oncological orientation
- Explain every decision (Explainability Layer)
- Require physician validation (Human-in-the-loop)

---

## Architecture

Medical reports  
or  
Medical images  
or  
Medical reports + Medical images  

↓

YOLO lesion detection  

↓

Gemma 4 analysis  

↓

Clinical report generation  

↓

Physician validation  

---

## Features

### Medical report analysis

- Extract structured clinical information
- Generate clinical summaries
- Identify important findings

### Image analysis

- Colonoscopy lesion detection
- Visual support for physicians

### Clinical assistance

- Priority scoring
- Specialist orientation
- Explainable recommendations

### Human-in-the-loop

- Physicians validate all final decisions

---

## Installation

### Clone repository

```bash
git clone https://github.com/yosrasallemi/colocare-md.git

cd colocare-md
```

### Install Python dependencies

```bash
pip install -r requirements.txt
```

### Install Ollama

Download and install Ollama:

https://ollama.com

### Download Gemma

```bash
ollama pull gemma4
```

(or use another Gemma model depending on available resources)

### Run the application

```bash
streamlit run app.py
```

### Requirements

- Python 3.11+
- Ollama
- Gemma model
- Streamlit

---

## Datasets

Datasets used during development:

- MIMIC-IV Note (discharge summaries + radiology)
- Kvasir dataset
- HyperKvasir segmented-images for testing
- MTSamples clinical reports
- 30 PubMed clinical case reports
- Synthetic patient examples for application testing

Datasets are referenced for research purposes and are not included in this repository.

---

## Future Work

- Multilingual support
- Expanded medical specialties
- Additional imaging modalities
- Improved clinical workflows
- Appointment scheduling
- Improved physician experience and interface usability
- Scalability improvements for broader healthcare environments
- Gemma fine-tuning for clinical tasks
- Post-operative outcome prediction and follow-up support after surgical interventions

---

## Hackathon

- **Competition:** Gemma 4 Good Hackathon — Google/Kaggle 2026
- **Track:** Health & Sciences
- **Technology:** Gemma 4 via Ollama (offline/edge deployment)

---

## Medical Disclaimer

This system provides AI clinical decision support only.

ColoCare MD is not designed to replace physicians.

Physicians remain responsible for all final medical decisions. 
