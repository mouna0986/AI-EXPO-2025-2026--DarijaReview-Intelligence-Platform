from fastapi import APIRouter
from api.db import get_connection
#from api.router.db import get_connection



router = APIRouter()


@router.get("/summary")
def get_summary():
    """
    Returns overall sentiment counts.
    The dashboard uses this for the big gauge at the top.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sentiment, COUNT(*) as count
        FROM reviews
        WHERE sentiment IS NOT NULL
        GROUP BY sentiment
    """)
    rows = cursor.fetchall()
    conn.close()

    # Convert to a simple dictionary
    result = {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
    for row in rows:
        sentiment = row["sentiment"]
        count = row["count"]
        result[sentiment] = count
        result["total"] += count

    return result


@router.get("/reviews")
def get_reviews(platform: str = None, sentiment: str = None, limit: int = 50):
    """
    Returns reviews. Can filter by platform or sentiment.
    Example: /reviews?platform=facebook&sentiment=negative
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM reviews WHERE 1=1"
    params = []

    if platform:
        query += " AND platform = ?"
        params.append(platform)

    if sentiment:
        query += " AND sentiment = ?"
        params.append(sentiment)

    query += " ORDER BY engagement_score DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


@router.get("/aspects")
def get_aspects():
    """
    Returns aspect sentiment breakdown.
    Example: taste=70% positive, price=80% negative
    The dashboard uses this for the radar chart.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT aspect, polarity, COUNT(*) as count
        FROM aspects
        GROUP BY aspect, polarity
        ORDER BY aspect
    """)
    rows = cursor.fetchall()
    conn.close()

    # Group by aspect
    result = {}
    for row in rows:
        aspect = row["aspect"]
        polarity = row["polarity"]
        count = row["count"]

        if aspect not in result:
            result[aspect] = {"positive": 0, "negative": 0, "neutral": 0}
        result[aspect][polarity] = count

    return result


@router.get("/prices")
def get_prices():
    """
    Returns all price data for the competitor comparison table.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM prices ORDER BY brand, product")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


@router.get("/top-reviews")
def get_top_reviews(sentiment: str = "positive", limit: int = 3):
    """
    Returns top reviews by engagement score.
    Used for the 'What customers are saying' section in the dashboard.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT text, platform, engagement_score, sentiment
        FROM reviews
        WHERE sentiment = ?
        ORDER BY engagement_score DESC
        LIMIT ?
    """, (sentiment, limit))
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

#added on day6, may not work:
@router.post("/predict")
def predict_sentiment(payload: dict):
    """
    Live classify endpoint.
    Called by the dashboard's Analyze button.
    Uses rule-based classifier until real model is ready.
    """
    text = payload.get("text", "")
    if not text.strip():
        return {"label": "neutral", "confidence": 0.5}

    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    try:
        from nlp.normalize import normalize_darija
        normalized = normalize_darija(text)
    except Exception:
        normalized = text.lower()

    # Rule-based until real model is ready
    POSITIVE_KW = [
        "زين", "مليح", "ممتاز", "نعجبني", "3jebni",
    "bon", "bien", "super", "top",
    "بهية", "تستاهل", "يستاهل", "recommande",
    "واو", "رائع", "نحب", "زينة", "waw", "mzian",
    "délicieux", "excellent", "parfait", "bni", "bnin","pos_emoji","délicieux","excellent"
    ]
    NEGATIVE_KW = [
            "خايب", "خايبة", "غالي", "غالية", "mauvais", "nul",
    "ما عجبنيش", "ما عجبني", "ma3jebni", "ma3jebnich",
    "ma3jbni", "ma3jbnis", "cher", "déçu",
    "خسارة", "ما نشريش", "مش مليح", "khayeb", "ghali",
    "périmé", "expiré", "makach", "machi zin",
    "noo", "laa", "لا لا", "عيب", "prix bzaf","neg_emoji","khayeb","ghali",
    "makach","introuvable"
    ]
    
    
    
    
 
    "خايب", "خايبة", "غالي", "غالية", "mauvais", "nul",
    "ما عجبنيش", "ما عجبني", "ma3jebni", "ma3jebnich",
    "ma3jbni", "ma3jbnis", "cher", "déçu",
    "خسارة", "ما نشريش", "مش مليح", "khayeb", "ghali",
    "périmé", "expiré", "makach", "machi zin",
    "noo", "laa", "لا لا", "عيب", "prix bzaf", "bzzaf"


    t = normalized.lower()
    pos = sum(1 for kw in POSITIVE_KW if kw in t)
    neg = sum(1 for kw in NEGATIVE_KW if kw in t)

    if pos > neg:
        return {"label": "positive", "confidence": round(min(0.70 + pos * 0.05, 0.94), 2)}
    elif neg > pos:
        return {"label": "negative", "confidence": round(min(0.70 + neg * 0.05, 0.94), 2)}
    else:
        return {"label": "neutral", "confidence": 0.65}

#end
    return [dict(row) for row in rows]