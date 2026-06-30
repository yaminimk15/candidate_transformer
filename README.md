# Multi-Source Candidate Data Transformer

A Streamlit-based application that transforms candidate information from multiple sources such as resumes, recruiter CSVs, and configuration files into a unified canonical candidate profile with confidence scoring, provenance tracking, and configurable data projection.

---

## Features

- Upload Resume (PDF)
- Upload Recruiter CSV
- Upload Projection Configuration (JSON)
- Extract candidate details from multiple sources
- Normalize candidate information
- Merge candidate data using configurable merge strategies
- Confidence scoring for extracted fields
- Provenance tracking for every extracted field
- Configurable projection layer
- JSON Schema validation
- Data quality reporting
- Download final candidate profile as JSON

---

## Tech Stack

- Python 3
- Streamlit
- Pandas
- PyPDF2
- RapidFuzz
- phonenumbers
- python-dateutil
- JSON Schema

---

## Project Structure

```
Candidate-Data-Transformer/
│
├── app/
│   ├── confidence/
│   ├── constants/
│   ├── extractors/
│   ├── merger/
│   ├── models/
│   ├── normalizers/
│   ├── projection/
│   ├── reporting/
│   ├── services/
│   ├── ui/
│   └── validators/
│
├── config/
├── data/
├── tests/
├── requirements.txt
└── README.md
```

---

## How It Works

```
Resume PDF
      │
Recruiter CSV
      │
Projection Config
      │
      ▼
Data Extraction
      ▼
Normalization
      ▼
Merge & Deduplication
      ▼
Confidence & Provenance
      ▼
Projection
      ▼
Schema Validation
      ▼
Canonical Candidate Profile
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/Candidate-Data-Transformer.git
```

Navigate to the project folder:

```bash
cd Candidate-Data-Transformer
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it:

### Windows

```bash
venv\Scripts\activate
```

### Linux/macOS

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Run the Application

```bash
streamlit run app/ui/streamlit_app.py
```

---

## Input Files

- Resume (PDF)
- Recruiter CSV
- Projection Configuration (JSON)

---

## Output

The application generates a canonical candidate profile in JSON format containing:

- Candidate Information
- Skills
- Experience
- Education
- Confidence Scores
- Provenance Tracking
- Overall Confidence

---

## Assignment Highlights

- Multi-source candidate data transformation
- Configurable merge strategies
- Runtime projection layer
- Confidence scoring
- Explainable provenance tracking
- Schema validation
- Production-style data quality reporting

---

## Future Improvements

- LinkedIn API integration
- OCR support for scanned resumes
- REST API
- Docker deployment
- AI-powered skill extraction

---

## Author

**Yamini M K**

GitHub: https://github.com/yaminimk15

---

Developed as part of the **Eightfold AI Engineering Intern Assignment**.
