import pandas as pd
import sqlite3
import os
from datetime import datetime

DB_PATH = "database/reviews.db"


def import_from_csv(filepath: str):
    """
    Imports reviews from a CSV file into the database.

    Expected CSV columns:
        text      — the review text (required)
        platform  — facebook / tiktok / youtube / jumia (optional, default: 'manual')
        sentiment — positive / negative / neutral (optional, leave empty if unknown)
        engagement_score — number of likes/reactions (optional, default: 0)
        review_date — YYYY-MM-DD format (optional, default: today)
    """

    print(f" Reading file: {filepath}")

    if not os.path.exists(filepath):
        print(f" File not found: {filepath}")
        return

    try:
        df = pd.read_csv(filepath, encoding="utf-8-sig")
    except Exception as e:
        print(f" Could not read CSV: {e}")
        return

    print(f"  Found {len(df)} rows")

    # Make sure required column exists
    if "text" not in df.columns:
        print(" CSV must have a 'text' column")
        return

    # Fill optional columns with defaults if missing
    if "platform" not in df.columns:
        df["platform"] = "manual"
    if "sentiment" not in df.columns:
        df["sentiment"] = None
    if "engagement_score" not in df.columns:
        df["engagement_score"] = 0
    if "review_date" not in df.columns:
        df["review_date"] = datetime.now().strftime("%Y-%m-%d")

    # Clean up
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 3]  # Remove empty/tiny rows
    df["engagement_score"] = pd.to_numeric(
        df["engagement_score"], errors="coerce"
    ).fillna(0).astype(int)

    # Save to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    saved = 0
    skipped = 0

    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO reviews (platform, text, sentiment, engagement_score, review_date)
                VALUES (?, ?, ?, ?, ?)
            """, (
                row["platform"],
                row["text"],
                row["sentiment"] if pd.notna(row["sentiment"]) else None,
                int(row["engagement_score"]),
                row["review_date"]
            ))
            saved += 1
        except Exception as e:
            print(f"    Skipped row: {e}")
            skipped += 1

    conn.commit()
    conn.close()

    print(f" Imported {saved} reviews")
    if skipped:
        print(f"Skipped {skipped} rows")


if __name__ == "__main__":
    # Default: looks for data/labeled/reviews.csv
    import sys
    filepath = sys.argv[1] if len(sys.argv) > 1 else "data/labeled/reviews.csv"
    import_from_csv(filepath)