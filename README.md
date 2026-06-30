# Multi-Source Candidate Data Transformer

A Python and Streamlit application that extracts, normalizes, merges, and transforms candidate information from multiple sources (Resume PDF, Recruiter CSV, and JSON configuration) into a unified canonical candidate profile.

## Live Demo

**Application:** https://candidatetransformer-profileanlayzer.streamlit.app/

## GitHub Repository

https://github.com/yaminimk15/Candidate-Data-Transformer

---

## Features

- Resume PDF parsing
- Recruiter CSV processing
- Candidate profile generation
- Data normalization
- Confidence scoring
- Provenance tracking
- JSON output generation
- Configurable projection layer

---

## Project Structure

```
Candidate-Data-Transformer/
│
├── app/
├── config/
├── data/
├── tests/
├── requirements.txt
└── README.md
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/yaminimk15/Candidate-Data-Transformer.git
```

Navigate to the project:

```bash
cd Candidate-Data-Transformer
```

Install the required packages:

```bash
pip install -r requirements.txt
```

---

## Run the Application

```bash
streamlit run app/ui/streamlit_app.py
```

The application will open in your browser at:

```
http://localhost:8501
```

---

## Sample Inputs

- Resume PDF
- Recruiter CSV
- Projection Configuration (JSON)

---

## Sample Output

The application generates a canonical candidate profile in JSON format containing:

- Personal Information
- Skills
- Experience
- Education
- Confidence Scores
- Provenance Tracking
- Overall Confidence

---

## Testing

Run the test suite using:

```bash
pytest
```

---

## Technologies Used

- Python
- Streamlit
- Pandas
- PDFPlumber
- BeautifulSoup
- RapidFuzz
- phonenumbers
- JSON Schema

---

## Author

**Yamini M K**

GitHub: https://github.com/yaminimk15
