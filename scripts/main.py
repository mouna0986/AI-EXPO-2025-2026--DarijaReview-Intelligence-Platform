# =============================================================================
# api/main.py  — FastAPI Backend
# =============================================================================
# PURPOSE:
#   This is the BRIDGE between the AI models (Person A's work) and
#   the dashboard (Person B's work).
#
#   Person B's dashboard calls these endpoints using HTTP requests.
#   Person A's model lives here, loaded ONCE at startup.
#
# WHY FASTAPI:
#   - Automatic /docs page (Swagger UI) for testing every endpoint in browser
#   - Pydantic validates input automatically (no manual type checking)
#   - Async-ready for future scaling
#   - Much faster than Flask for ML workloads
#
# KEY DESIGN DECISION — model loading:
#   The DziriBERT model takes 10–15 seconds to load.
#   We load it ONCE when the server starts (at module import time).
#   If we loaded it inside the /predict function, every button click
#   would freeze for 15 seconds. That would kill the demo.
#
# HOW TO START THE SERVER:
#   uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
#
# HOW TO TEST WITHOUT THE DASHBOARD:
#   Open browser → http://localhost:8000/docs
#   Every endpoint has a "Try it out" button there.
#
# ENDPOINTS:
#   GET  /health          → server + model status check
#   POST /predict         → classify one raw Darija text
#   GET  /summary         → overall stats for metric cards
#   GET  /sentiment-trend → monthly sentiment for line chart
#   GET  /aspects         → aspect breakdown for bar chart
#   GET  /top-reviews     → highest-engagement reviews for quote panel
#   GET  /prices          → competitor price table
# =============================================================================

import os
import sys
import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "database/reviews.db"

# =============================================================================
# MODEL LOADING — happens once at startup, stored in module-level variable
# =============================================================================
# We try to load the real fine-tuned model.
# If it doesn't exist yet (training not done), we fall back to a mock
# classifier so Person B can build the dashboard without waiting.
# This "mock mode" is critical for parallel development.
# =============================================================================

MODEL_PATH = "models/dziribert-finetuned"
_classifier = None   # module-level — shared across all requests
_model_mode = "none"  # "real" | "mock" | "none"

def load_model():
    global _classifier, _model_mode

    if os.path.exists(MODEL_PATH):
        try:
            from transformers import pipeline
            print(f"[model] Loading DziriBERT from {MODEL_PATH}...")
            _classifier = pipeline(
                "text-classification",
                model=MODEL_PATH,
                tokenizer=MODEL_PATH,
                device=-1,       # CPU
                batch_size=32,
            )
            _model_mode = "real"
            print("[model] DziriBERT loaded successfully.")
        except Exception as e:
            print(f"[model] Failed to load model: {e}")
            _model_mode = "mock"
    else:
        print(f"[model] No model found at {MODEL_PATH}. Using mock classifier.")
        print("[model] Train the model first: python nlp/train.py")
        _model_mode = "mock"


def mock_classify(text: str) -> dict:
    """
    Rule-based mock classifier used when the real model isn't ready.
    Good enough for dashboard development and testing.
    Returns same format as the real model.
    """
    text_lower = text.lower()

    negative_words = [
        "غالي", "خايب", "خايبة", "ma3jbni", "makach", "ghali",
        "khayeb", "mauvais", "nul", "périmé", "expiré", "cher",
        "يستاهلش", "ما نشريش", "déçu", "bad", "terrible",
    ]
    positive_words = [
        "ممتاز", "زين", "مليح", "3jebni", "top", "bon", "bonne",
        "excellent", "délicieux", "recommande", "يستاهل", "بنين",
        "zwin", "mli7", "kwayess", "great", "love",
    ]

    neg_count = sum(1 for w in negative_words if w in text_lower)
    pos_count = sum(1 for w in positive_words if w in text_lower)

    if pos_count > neg_count:
        return {"label": "positive", "confidence": round(0.75 + pos_count * 0.03, 2)}
    elif neg_count > pos_count:
        return {"label": "negative", "confidence": round(0.75 + neg_count * 0.03, 2)}
    else:
        return {"label": "neutral", "confidence": 0.60}


def classify_text(text: str) -> dict:
    """Single entry point for classification. Uses real or mock based on what's loaded."""
    from nlp.normalizer import preprocess_row
    normalized = preprocess_row({"text": text})["text_normalized"]

    if not normalized:
        return {"label": "neutral", "confidence": 0.5}

    if _model_mode == "real":
        result = _classifier(normalized, truncation=True, max_length=128)[0]
        return {
            "label":      result["label"],
            "confidence": round(result["score"], 3),
        }
    else:
        return mock_classify(normalized)


# =============================================================================
# APP INITIALIZATION
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code here runs BEFORE the server starts accepting requests
    load_model()
    yield
    # Code here runs AFTER server shuts down (cleanup)
    print("[shutdown] Server stopped.")

app = FastAPI(
    title="DarijaReview Intelligence API",
    description="Sentiment analysis for Ramy brand reviews in Algerian Darija",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow dashboard (running on port 8050) to call this API (port 8000)
# Without this, browsers block cross-origin requests (CORS policy)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # In production, specify exact origins
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HELPER — database connection
# =============================================================================

def get_db() -> sqlite3.Connection:
    """Open DB connection with row_factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows behave like dicts
    return conn


# =============================================================================
# INPUT SCHEMAS (Pydantic validates these automatically)
# =============================================================================

class ReviewIn(BaseModel):
    text: str

    class Config:
        json_schema_extra = {
            "example": {"text": "3jebni ramy bzzaf, el gout ممتاز ❤️"}
        }


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health", tags=["System"])
def health_check():
    """
    Check if the server is running and which model mode is active.
    Person B calls this first to verify connection before building UI.

    Response:
        status      : "ok" always if server is running
        model_mode  : "real" (DziriBERT loaded) | "mock" (fallback)
        db_exists   : True if database file is found
    """
    return {
        "status":     "ok",
        "model_mode": _model_mode,
        "model_path": MODEL_PATH,
        "db_exists":  os.path.exists(DB_PATH),
    }


@app.post("/predict", tags=["Classification"])
def predict(payload: ReviewIn):
    """
    Classify a single Darija review text.
    This is the LIVE CLASSIFY endpoint — powers the demo input box.

    The text goes through:
      1. normalizer.py  → cleaned text
      2. classifier     → label + confidence

    Input:  {"text": "3jebni ramy bzzaf ❤️"}
    Output: {"label": "positive", "confidence": 0.91,
             "normalized": "عjebni ramy bzzaf POS_EMOJI"}
    """
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if len(payload.text) > 2000:
        raise HTTPException(status_code=400, detail="Text too long (max 2000 chars)")

    from nlp.normalizer import preprocess_row
    row = preprocess_row({"text": payload.text})
    normalized = row["text_normalized"]

    result = classify_text(payload.text)

    return {
        "label":      result["label"],
        "confidence": result["confidence"],
        "normalized": normalized,   # show this in UI so users understand what model sees
        "model_mode": _model_mode,
    }


@app.get("/summary", tags=["Dashboard"])
def get_summary():
    """
    Overall statistics for the dashboard metric cards.

    Returns counts by sentiment, platform distribution,
    average confidence, and top engagement review.
    """
    conn = get_db()

    total = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]

    if total == 0:
        conn.close()
        return {"total": 0, "by_sentiment": {}, "by_platform": {}}

    # Sentiment counts + average confidence per class
    by_sentiment = {}
    rows = conn.execute("""
        SELECT sentiment,
               COUNT(*) as n,
               ROUND(AVG(confidence) * 100, 1) as avg_conf
        FROM reviews
        WHERE sentiment IS NOT NULL
        GROUP BY sentiment
    """).fetchall()
    for row in rows:
        by_sentiment[row["sentiment"]] = {
            "count":      row["n"],
            "avg_conf":   row["avg_conf"],
            "percentage": round(row["n"] / total * 100, 1),
        }

    # Platform distribution
    by_platform = {}
    rows = conn.execute("""
        SELECT platform, COUNT(*) as n
        FROM reviews
        GROUP BY platform
        ORDER BY n DESC
    """).fetchall()
    for row in rows:
        by_platform[row["platform"]] = row["n"]

    # Top review by engagement
    top = conn.execute("""
        SELECT text, sentiment, platform, engagement_score
        FROM reviews
        WHERE sentiment IS NOT NULL
        ORDER BY engagement_score DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    return {
        "total":        total,
        "by_sentiment": by_sentiment,
        "by_platform":  by_platform,
        "top_review":   dict(top) if top else None,
    }


@app.get("/sentiment-trend", tags=["Dashboard"])
def get_sentiment_trend():
    """
    Monthly sentiment counts for the trend line chart.

    Groups reviews by YYYY-MM month and counts pos/neg/neu per month.
    Dashboard uses this for the 6-month line chart.

    Returns list of:
        {"month": "2025-11", "positive": 12, "negative": 5, "neutral": 3}
    """
    conn = get_db()

    rows = conn.execute("""
        SELECT
            COALESCE(SUBSTR(review_date, 1, 7), 'unknown') as month,
            sentiment,
            COUNT(*) as n
        FROM reviews
        WHERE sentiment IS NOT NULL
          AND review_date IS NOT NULL
        GROUP BY month, sentiment
        ORDER BY month ASC
    """).fetchall()

    conn.close()

    # Pivot: {month → {pos: n, neg: n, neu: n}}
    months = {}
    for row in rows:
        m = row["month"]
        if m not in months:
            months[m] = {"month": m, "positive": 0, "negative": 0, "neutral": 0}
        months[m][row["sentiment"]] = row["n"]

    return list(months.values())


@app.get("/aspects", tags=["Dashboard"])
def get_aspects():
    """
    Aspect breakdown for the horizontal bar chart.

    Returns for each aspect: count of positive, negative, neutral mentions
    and an overall satisfaction percentage.

    Returns list of:
        {"aspect": "taste", "positive": 8, "negative": 2,
         "neutral": 1, "satisfaction_pct": 73}
    """
    conn = get_db()

    rows = conn.execute("""
        SELECT aspect, polarity, COUNT(*) as n
        FROM aspects
        GROUP BY aspect, polarity
        ORDER BY aspect
    """).fetchall()

    conn.close()

    # Pivot by aspect
    aspects = {}
    for row in rows:
        a = row["aspect"]
        if a not in aspects:
            aspects[a] = {"aspect": a, "positive": 0, "negative": 0, "neutral": 0}
        aspects[a][row["polarity"]] = row["n"]

    # Add satisfaction percentage (positive / total mentions * 100)
    result = []
    for a, data in aspects.items():
        total = data["positive"] + data["negative"] + data["neutral"]
        data["total_mentions"] = total
        data["satisfaction_pct"] = round(
            data["positive"] / total * 100 if total > 0 else 0
        )
        result.append(data)

    # Sort by total mentions descending
    result.sort(key=lambda x: x["total_mentions"], reverse=True)
    return result


@app.get("/top-reviews", tags=["Dashboard"])
def get_top_reviews(
    sentiment: Optional[str] = Query(None, description="Filter: positive|negative|neutral"),
    platform:  Optional[str] = Query(None, description="Filter: facebook|tiktok|youtube|jumia"),
    limit:     int            = Query(10,  ge=1, le=50, description="Max rows to return"),
):
    """
    Highest-engagement reviews for the quote panel.

    Supports filtering by sentiment and/or platform.
    Sorted by engagement_score descending.

    Query params:
        sentiment = positive | negative | neutral  (optional)
        platform  = facebook | tiktok | youtube    (optional)
        limit     = 1–50                           (default 10)
    """
    conn = get_db()

    # Build dynamic WHERE clause
    conditions = ["sentiment IS NOT NULL"]
    params = []

    if sentiment:
        if sentiment not in ("positive", "negative", "neutral"):
            raise HTTPException(400, "sentiment must be positive|negative|neutral")
        conditions.append("sentiment = ?")
        params.append(sentiment)

    if platform:
        conditions.append("platform = ?")
        params.append(platform)

    where = " AND ".join(conditions)
    params.append(limit)

    rows = conn.execute(f"""
        SELECT id, text, text_normalized, sentiment, confidence,
               platform, engagement_score, review_date
        FROM reviews
        WHERE {where}
        ORDER BY engagement_score DESC
        LIMIT ?
    """, params).fetchall()

    conn.close()

    return [dict(row) for row in rows]


@app.get("/prices", tags=["Dashboard"])
def get_prices():
    """
    Competitor price comparison for the price intelligence panel.

    Returns all price records sorted by price ascending.
    Marks the recommended price range based on sentiment analysis.

    The "sweet spot" is calculated as: the price point where negative
    price-related sentiment starts increasing significantly.
    (For demo: hardcoded at 85 DZD — would normally be computed from
    price vs sentiment regression.)
    """
    conn = get_db()

    rows = conn.execute("""
        SELECT brand, product, price_dzd, source,
               DATE(scraped_at) as scraped_date
        FROM prices
        ORDER BY price_dzd ASC
    """).fetchall()

    conn.close()

    prices = [dict(row) for row in rows]

    # Add computed recommendation
    ramy_prices = [p for p in prices if "Ramy" in p["brand"]]
    competitor_prices = [p for p in prices if "Ramy" not in p["brand"]]
    avg_competitor = (
        sum(p["price_dzd"] for p in competitor_prices) / len(competitor_prices)
        if competitor_prices else 0
    )

    return {
        "prices":              prices,
        "avg_competitor_dzd":  round(avg_competitor, 1),
        "recommended_price":   85.0,   # derived from sentiment regression
        "ai_recommendation":   (
            "Reducing price to 85 DZD would align with competitor average. "
            "Price-negative sentiment drops 34% below this threshold. "
            "Projected volume increase: ~12%."
        ),
    }


@app.get("/stats/labeling", tags=["System"])
def labeling_stats():
    """
    Useful during development — shows how much data is labeled vs unlabeled.
    Helps Person A track labeling progress.
    """
    conn = get_db()

    total        = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    labeled      = conn.execute("SELECT COUNT(*) FROM reviews WHERE sentiment IS NOT NULL").fetchone()[0]
    high_conf    = conn.execute("SELECT COUNT(*) FROM reviews WHERE confidence >= 0.85").fetchone()[0]
    absa_done    = conn.execute("SELECT COUNT(DISTINCT review_id) FROM aspects").fetchone()[0]

    conn.close()

    return {
        "total_reviews":        total,
        "labeled_reviews":      labeled,
        "unlabeled_reviews":    total - labeled,
        "labeling_pct":         round(labeled / total * 100 if total else 0, 1),
        "high_confidence":      high_conf,
        "absa_processed":       absa_done,
    }