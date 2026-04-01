#prepare-labels.py
# PURPOSE:
#   Take raw scraped JSON files from data/raw/ and produce a clean CSV
#   that Person A opens in Excel/LibreOffice to label manually.

#   1. Reads ALL .json files from data/raw/
#   2. Normalizes every text using our normalizer
#   3. Removes exact duplicates
#   4. Removes rows that are too short to be useful
#   5. Sorts by engagement_score (high engagement = more important to label)
#   6. Adds empty 'sentiment' column for manual labeling
#   7. Saves to data/labeled/reviews_to_label.csv

#   python prepare-labels.py
#   Then we open reviews.csv in Excel
#   Fill in the 'sentiment' column: positive / negative / neutral
#   Save as data/labeled/reviews_labeled.csv


import sys
import os
import json
import glob
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from normalize import preprocess_row

#Configuration 
RAW_DIR      = "data/raw"
LABELED_DIR  = "data/labeled"
OUTPUT_FILE  = os.path.join(LABELED_DIR, "reviews_to_label.csv")

# Minimum text length after normalization to keep a row
# Below 10 chars = not enough signal for classification
MIN_TEXT_LENGTH = 10


def load_all_raw_files() -> list[dict]:
    """
    Load every .json file in data/raw/.
    Each file should be a list of review dicts.
    """
    all_reviews = []
    json_files = glob.glob(os.path.join(RAW_DIR, "*.json"))

    if not json_files:
        print(f"[ERROR] No .json files found in {RAW_DIR}/")
        print("        Run your scrapers first, or use the sample file.")
        sys.exit(1)

    for filepath in json_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle both list format and dict format
            if isinstance(data, list):
                reviews = data
            elif isinstance(data, dict) and "reviews" in data:
                reviews = data["reviews"]
            else:
                print(f"[WARN] {filename}: unexpected format, skipping")
                continue

            print(f"  Loaded {len(reviews):4d} rows from {filename}")
            all_reviews.extend(reviews)

        except json.JSONDecodeError as e:
            print(f"[WARN] {filename}: invalid JSON — {e}")
        except Exception as e:
            print(f"[WARN] {filename}: error — {e}")

    return all_reviews


def process_and_clean(reviews: list[dict]) -> pd.DataFrame:
    """
    Normalize, deduplicate, and filter the raw reviews.
    Returns a clean DataFrame ready for labeling.
    """
    print(f"\n[processing] Starting with {len(reviews)} total rows")

    # Normalize text 
    # Run every review through our normalizer to add text_normalized
    processed = []
    for review in reviews:
        row = preprocess_row(review.copy())
        processed.append(row)

    df = pd.DataFrame(processed)
    print(f"[processing] After normalization: {len(df)} rows")

    # Ensure required columns exist 
    # Some scrapers may not include all fields
    if "platform" not in df.columns:
        df["platform"] = "unknown"
    if "engagement_score" not in df.columns:
        df["engagement_score"] = 0
    if "review_date" not in df.columns:
        df["review_date"] = ""

    # Remove rows with empty normalized text 
    before = len(df)
    df = df[df["text_normalized"].notna()]
    df = df[df["text_normalized"].str.strip() != ""]
    print(f"[processing] After removing empty text: {len(df)} rows "
          f"(removed {before - len(df)})")

    # Remove rows where normalized text is too short 
    before = len(df)
    df = df[df["text_normalized"].str.len() >= MIN_TEXT_LENGTH]
    print(f"[processing] After length filter (>={MIN_TEXT_LENGTH} chars): {len(df)} rows "
          f"(removed {before - len(df)})")

    # Deduplicate on normalized text 
    # We deduplicate on NORMALIZED text, not raw text.
    # "3jebni ramy ❤️" and "3jebni ramy 😍" normalize to the same thing and we  keep only one.
    before = len(df)
    df = df.drop_duplicates(subset=["text_normalized"], keep="first")
    print(f"[processing] After deduplication: {len(df)} rows "
          f"(removed {before - len(df)} duplicates)")

    # Sort by engagement (most important first) 
    # Why? When labeling we want to label the highest-impact reviews first.

    df["engagement_score"] = pd.to_numeric(df["engagement_score"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values("engagement_score", ascending=False).reset_index(drop=True)

    # Add empty sentiment column 
    # This is the column Person A to fill it 
    df["sentiment"] = ""

    return df


def print_labeling_instructions(df: pd.DataFrame):
    """Print clear instructions for the person doing the labeling."""

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           LABELING INSTRUCTIONS FOR PERSON A                ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  File to open: data/labeled/reviews_to_label.csv            ║
║                                                              ║
║  COLUMN TO FILL: 'sentiment'                                 ║
║  Only 3 valid values — type exactly as shown:               ║
║    positive   ← reviewer likes the product                  ║
║    negative   ← reviewer complains / dislikes               ║
║    neutral    ← factual, question, ambiguous                 ║
║                                                              ║
║  LABELING RULES:                                             ║
║  ✓ positive: "3jebni", "zwin", "top", "mliih", ❤️ 😋 👌    ║
║  ✓ negative: "ghali", "khayeb", "makach", "machi zin", 👎   ║
║  ✓ neutral:  "wayin ramy?", "ramy mwjoud fi...", facts       ║
║                                                              ║
║  WHEN IN DOUBT: label 'neutral' — never guess               ║
║                                                              ║
║  TARGET: Label at least {min(500, len(df))} rows                       ║
║  Do 50 rows per session then take a 10-minute break.        ║
║  Your judgment gets lazy after 50 rows.                     ║
║                                                              ║
║  SAVE AS: data/labeled/reviews_labeled.csv                  ║
╚══════════════════════════════════════════════════════════════╝
    """)


def print_data_preview(df: pd.DataFrame):
    """Show a sample of what's in the file before labeling."""

    print("\n" + "="*70)
    print("DATA PREVIEW — First 12 rows (sorted by engagement)")
    print("="*70)

    preview_cols = ["platform", "engagement_score", "text", "text_normalized"]
    for i, row in df.head(12).iterrows():
        print(f"\n  Row {i+1:3d} | {row['platform']:10s} | {row['engagement_score']:,} reactions")
        print(f"  RAW : {str(row.get('text',''))[:80]}")
        print(f"  NORM: {str(row.get('text_normalized',''))[:80]}")

    print("\n" + "="*70)
    print("PLATFORM DISTRIBUTION")
    print("="*70)
    platform_counts = df["platform"].value_counts()
    for platform, count in platform_counts.items():
        bar = "█" * (count // 2)
        print(f"  {platform:12s} {count:4d} rows  {bar}")

    print("\n" + "="*70)
    print("LANGUAGE MIX ESTIMATE")
    print("="*70)
    # Rough estimate: count rows with Arabic characters
    has_arabic = df["text"].str.contains(r"[\u0600-\u06FF]", regex=True, na=False)
    has_latin  = df["text"].str.contains(r"[a-zA-Z]", regex=True, na=False)
    arabic_only = has_arabic & ~has_latin
    latin_only  = ~has_arabic & has_latin
    mixed       = has_arabic & has_latin

    print(f"  Arabic script only : {arabic_only.sum():4d} rows ({arabic_only.mean()*100:.0f}%)")
    print(f"  Latin/French only  : {latin_only.sum():4d} rows  ({latin_only.mean()*100:.0f}%)")
    print(f"  Mixed (Darija)     : {mixed.sum():4d} rows ({mixed.mean()*100:.0f}%)")


def main():
    print("="*60)
    print("  STEP 2: Prepare Labeling Sheet")
    print("="*60)

    # Create output directory if it doesn't exist
    os.makedirs(LABELED_DIR, exist_ok=True)

    # Load all raw files
    print(f"\n[loading] Reading files from {RAW_DIR}/")
    reviews = load_all_raw_files()

    if not reviews:
        print("[ERROR] No reviews loaded. Check your data/raw/ directory.")
        sys.exit(1)

    # Process and clean
    df = process_and_clean(reviews)

    if df.empty:
        print("[ERROR] No rows remained after cleaning. Check your raw data.")
        sys.exit(1)

    # Save to CSV
    # encoding='utf-8-sig' adds BOM so Arabic text displays correctly in Excel
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n[saved] {len(df)} rows → {OUTPUT_FILE}")

    # Print preview and instructions
    print_data_preview(df)
    print_labeling_instructions(df)


if __name__ == "__main__":
    main()