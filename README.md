# DarijaReview Intelligence 🧃

AI-powered sentiment analysis dashboard for Algerian brand reviews in Darija, Arabic, and French.

Built for AI EXPO 2026 — House of AI @ Blida 1 University.

## What It Does
- Collects reviews from Facebook, TikTok, YouTube, Jumia
- Normalizes Darija text (Arabizi, mixed language)
- Classifies sentiment: positive / negative / neutral
- Extracts aspect-level opinions (taste, price, packaging...)
- Displays everything on a live interactive dashboard

## How To Run

### Requirements
- Python 3.11
- Windows / Mac / Linux

### Setup
```bash
git clone https://github.com/mouna0986/darija-review-intelligence
cd darija-review-intelligence
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python database/init_db.py
python scripts/ingit.py
```

### Run
Open two terminals:

Terminal 1 — API:
```bash
uvicorn api.main:app --reload
```

Terminal 2 — Dashboard:
```bash
python dashboard/app.py
```

Open browser at `http://127.0.0.1:8050`

## Project Structure
```

darija-review-intelligence/
├── api/          — FastAPI backend
├── dashboard/    — Plotly Dash frontend
├── database/     — SQLite schema and init
├── nlp/          — Normalizer and ABSA
├── scripts/      — Data ingestion and integration check
├── data/         — Raw and labeled review data

```
## Team
 Krim Mouna — Person B (Backend + Dashboard)
Djemai mohamed abdelhadi — Person A (NLP + Model)
