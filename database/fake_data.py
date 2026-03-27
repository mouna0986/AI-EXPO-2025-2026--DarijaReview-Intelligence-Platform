import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "database/reviews.db"

FAKE_REVIEWS = [
    ("facebook", "رامي بنين بزاف، الطعم ممتاز", "positive", 0.92, 450),
    ("tiktok", "الثمن غالي شوية ولكن الجودة تستاهل", "neutral", 0.74, 1200),
    ("facebook", "ma3jbni l packaging, kibir bzaf", "negative", 0.81, 89),
    ("jumia", "top qualité, je recommande fortement", "positive", 0.88, 34),
    ("tiktok", "الڤولة خايبة، ما نشريش مرة أخرى", "negative", 0.79, 3400),
    ("youtube", "3jebni ramy, les saveurs sont bonnes", "positive", 0.85, 210),
    ("facebook", "ما لقيتش فالحانوت، توزيع عيان", "negative", 0.77, 67),
    ("jumia", "prix correct pour la qualité", "positive", 0.83, 12),
    ("tiktok", "الطعم مليح والعلبة زوينة", "positive", 0.91, 5600),
    ("facebook", "غالي على المنتج هذا، يستاهلش", "negative", 0.86, 230),
]

FAKE_ASPECTS = [
    (1, "taste", "positive"),
    (2, "price", "negative"),
    (2, "taste", "positive"),
    (3, "packaging", "negative"),
    (5, "taste", "negative"),
    (7, "availability", "negative"),
    (9, "taste", "positive"),
    (9, "packaging", "positive"),
    (10, "price", "negative"),
]

FAKE_PRICES = [
    ("Ramy", "Jus Mangue 1L", 180, "jumia"),
    ("Ramy", "Jus Orange 1L", 170, "jumia"),
    ("Ramy", "Lait 1L", 145, "ouedkniss"),
    ("Competitor A", "Jus Mangue 1L", 155, "jumia"),
    ("Competitor B", "Jus Orange 1L", 160, "ouedkniss"),
]

def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for platform, text, sentiment, confidence, engagement in FAKE_REVIEWS:
        days_ago = random.randint(1, 30)
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO reviews (platform, text, sentiment, confidence, engagement_score, review_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (platform, text, sentiment, confidence, engagement, date))

    for review_id, aspect, polarity in FAKE_ASPECTS:
        cursor.execute("""
            INSERT INTO aspects (review_id, aspect, polarity)
            VALUES (?, ?, ?)
        """, (review_id, aspect, polarity))

    for brand, product, price, source in FAKE_PRICES:
        cursor.execute("""
            INSERT INTO prices (brand, product, price_dzd, source)
            VALUES (?, ?, ?, ?)
        """, (brand, product, price, source))

    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(FAKE_REVIEWS)} reviews, {len(FAKE_ASPECTS)} aspects, {len(FAKE_PRICES)} prices")

if __name__ == "__main__":
    seed()