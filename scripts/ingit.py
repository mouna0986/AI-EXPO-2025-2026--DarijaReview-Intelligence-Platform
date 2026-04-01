# 
# ingest_data.py
#   Psent us classified reviews in tuple format.
#   This script parses them exactly as received and inserts into the DB.
#   Also seeds the prices table with competitor data.
#
# HOW TO RUN:
#   python scripts/ingit.py
# 

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from normalize import preprocess_row

DB_PATH = "database/reviews.db"

 
# Format: (platform, text, sentiment, confidence, engagement_score)
PERSON_B_REVIEWS = [
    ("facebook", "رامي بنين بزاف، الطعم ممتاز",                  "positive", 0.92, 450),
    ("tiktok",   "الثمن غالي شوية ولكن الجودة تستاهل",           "neutral",  0.74, 1200),
    ("facebook", "ma3jbni l packaging, kibir bzaf",               "negative", 0.81, 89),
    ("jumia",    "top qualité, je recommande fortement",           "positive", 0.88, 34),
    ("tiktok",   "الڤولة خايبة، ما نشريش مرة أخرى",              "negative", 0.79, 3400),
    ("youtube",  "3jebni ramy, les saveurs sont bonnes",           "positive", 0.85, 210),
    ("facebook", "ما لقيتش فالحانوت، توزيع عيان",                "negative", 0.77, 67),
    ("jumia",    "prix correct pour la qualité",                   "positive", 0.83, 12),
    ("tiktok",   "الطعم مليح والعلبة زوينة",                      "positive", 0.91, 5600),
    ("facebook", "غالي على المنتج هذا، يستاهلش",                 "negative", 0.86, 230),
]

# ── Competitor price data or somethign like this  
PRICE_DATA = [
    ("Competitor A",    "Juice 1L",   80.0,  "Jumia DZ"),
    ("Competitor B",    "Juice 1L",   88.0,  "Ouedkniss"),
    ("Ramy (current)",  "Jus 1L",     95.0,  "Jumia DZ"),
    ("Competitor C",    "Juice 1L",  100.0,  "Local store"),
    ("Ramy (current)",  "Jus 0.5L",  55.0,  "Jumia DZ"),
    ("Competitor A",    "Juice 0.5L", 45.0,  "Jumia DZ"),
]


def ingest_reviews(conn: sqlite3.Connection) -> dict:
    inserted = 0
    skipped  = 0
    errors   = []

    for platform, text, sentiment, confidence, engagement in PERSON_B_REVIEWS:
        # Normalize the text  same pipeline as training
        row = preprocess_row({"text": text})
        normalized = row["text_normalized"]

        try:
            conn.execute("""
                INSERT INTO reviews
                    (platform, text, text_normalized, sentiment, confidence, engagement_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (platform, text, normalized, sentiment, confidence, engagement))
            inserted += 1

        except sqlite3.IntegrityError:
            # UNIQUE(platform, text) constraint  already in DB
            skipped += 1

        except Exception as e:
            errors.append(f"  '{text[:40]}' → {e}")

    conn.commit()

    return {"inserted": inserted, "skipped": skipped, "errors": errors}


def ingest_prices(conn: sqlite3.Connection) -> int:
    inserted = 0
    for brand, product, price, source in PRICE_DATA:
        conn.execute("""
            INSERT INTO prices (brand, product, price_dzd, source)
            VALUES (?, ?, ?, ?)
        """, (brand, product, price, source))
        inserted += 1
    conn.commit()
    return inserted


def verify_db(conn: sqlite3.Connection):
    """Print a quick summary of what's now in the database."""
    print("\n" + "="*55)
    print("  DATABASE VERIFICATION")
    print("="*55)

    # Total reviews
    total = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    print(f"\n  Total reviews in DB : {total}")

    # By sentiment
    print("\n  Sentiment breakdown:")
    rows = conn.execute("""
        SELECT sentiment, COUNT(*) as n,
               ROUND(AVG(confidence)*100, 1) as avg_conf
        FROM reviews
        WHERE sentiment IS NOT NULL
        GROUP BY sentiment
        ORDER BY n DESC
    """).fetchall()
    for sentiment, n, avg_conf in rows:
        bar = "█" * n
        print(f"    {sentiment:10s} {n:3d}  avg_confidence={avg_conf}%  {bar}")

    # By platform
    print("\n  Platform breakdown:")
    rows = conn.execute("""
        SELECT platform, COUNT(*) as n
        FROM reviews
        GROUP BY platform
        ORDER BY n DESC
    """).fetchall()
    for platform, n in rows:
        print(f"    {platform:12s} {n:3d} reviews")

    # Price table
    print("\n  Price intelligence:")
    rows = conn.execute("""
        SELECT brand, product, price_dzd, source
        FROM prices
        ORDER BY price_dzd
    """).fetchall()
    for brand, product, price, source in rows:
        marker = " ← Ramy" if "Ramy" in brand else ""
        print(f"    {brand:20s} {price:6.1f} DZD  ({source}){marker}")

    # Sample reviews
    print("\n  Sample from DB (top 4 by engagement):")
    rows = conn.execute("""
        SELECT platform, sentiment, confidence, engagement_score, text
        FROM reviews
        ORDER BY engagement_score DESC
        LIMIT 4
    """).fetchall()
    for platform, sentiment, conf, eng, text in rows:
        print(f"    [{sentiment:8s} {conf:.2f}] {platform:9s} "
              f"{eng:5d} react. | {text[:45]}")

    print()


def main():
    print("="*55)
    print("  INGESTING PERSON B DATA")
    print("="*55)

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found at {DB_PATH}")
        print("        Run: python database/init_db.py  first")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    # Ingest reviews
    print(f"\n[reviews] Inserting {len(PERSON_B_REVIEWS)} classified reviews...")
    result = ingest_reviews(conn)
    print(f"  Inserted : {result['inserted']}")
    print(f"  Skipped  : {result['skipped']} (already in DB)")
    if result["errors"]:
        print(f"  Errors   : {len(result['errors'])}")
        for e in result["errors"]:
            print(e)

    # Ingest prices
    print(f"\n[prices] Inserting {len(PRICE_DATA)} price records...")
    n_prices = ingest_prices(conn)
    print(f"  Inserted : {n_prices}")

    # Verify
    verify_db(conn)
    conn.close()

    print("[DONE] Data ingested successfully.")
    print("       Person A can now run batch inference on these reviews.")


if __name__ == "__main__":
    main()