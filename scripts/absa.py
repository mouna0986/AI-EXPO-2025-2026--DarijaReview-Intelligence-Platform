
# absa.py  — Aspect-Based Sentiment Analysis
#   Regular sentiment classification gives ONE label per review: pos/neg/neu.

#   A review like "الطعم ممتاز ولكن الثمن غالي" is both positive AND negative
#   depending on which ASPECT you're looking at:
#     → taste     : positive
#     → price     : negative
#
#   ABSA extracts WHICH aspects are mentioned and HOW the reviewer feels
#   about EACH ONE independently.
#
# APPROACH:
#   We use a RULE-BASED approach, not a neural model.
#   Why? We have 8 days. A neural ABSA model needs weeks of labeled data.
#
#   The pipeline for each review:
#     1. Tokenize (split into words)
#     2. For each aspect, check if any aspect keyword appears
#     3. For each aspect found, look at surrounding words (window ±4 words)
#     4. Check if those surrounding words contain positive or negative signals
#     5. Store result: (review_id, aspect, polarity)
#
# ASPECTS WE TRACK (:
#   taste         — الطعم، ڤولة، gout, saveur
#   price         — الثمن، غالي، prix, cher
#   packaging     — العلبة، l'emballage, packaging
#   availability  — توزيع، makach, introuvable
#   freshness     — طازج، frais, périmé, date
#   quality       — جودة، qualité, quality

import re
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "database/reviews.db"

# 
#  ASPECT LEXICON
# Covers Arabic, French, Arabizi and common misspellings.
# Each entry is a list of keywords that signal that aspect is being discussed.
# 

ASPECT_LEXICON = {
    "taste": [
        # Arabic
        "الطعم", "طعمو", "طعمها", "طعمه", "ڤولة", "ڤولتها", "الذوق",
        "حلو", "حلوة", "حلاوة", "لذيذ", "لذيذة",
        # Arabizi
        "gout", "goût", "3jebni", "ma3jbni", "7lwa", "zwin", "zwina",
        "khayeb", "khayba", "bni", "bnin",
        # French
        "saveur", "saveurs", "goût", "délicieux", "délicieuse",
        "sucré", "sucrée", "naturel", "naturelle", "artificiel",
    ],
    "price": [
        # Arabic
        "الثمن", "ثمنو", "السعر", "سعرو", "غالي", "غالية", "رخيص", "رخيصة",
        # Arabizi / French mix
        "ghali", "ghalia", "prix", "cher", "chère", "coût",
        "abordable", "pas cher", "trop cher", "yestahel", "yestahel5",
        "ma yestahel5", "يستاهل", "يستاهلش", "يستهلش",
        # DZD mentions signal price discussion
        "dzd", "دج", "دينار",
    ],
    "packaging": [
        # Arabic
        "العلبة", "علبتها", "الغطاء", "الغطا", "القارورة", "القنينة",
        "التصميم", "الشكل",
        # Arabizi / French
        "packaging", "emballage", "bouteille", "bouchon",
        "design", "jdid", "جديد",
        "kibir", "sghir", "كبير", "صغير",
    ],
    "availability": [
        # Arabic
        "توزيع", "الحانوت", "الدكان", "ما لقيتش", "ما نلقاش",
        "مقطوع", "introuvable",
        # Arabizi / French
        "makach", "ma lqi5", "ma lqit5", "mawjoud", "mawjouda5",
        "disponible", "indisponible", "livraison", "stock",
        "hanout", "supermarché", "monoprix", "magasin",
    ],
    "freshness": [
        # Arabic
        "طازج", "طازجة", "تاريخ", "منتهي", "صلاحية",
        # French
        "frais", "fraîche", "périmé", "périmée", "date", "expir",
        "expiré", "expirée", "dlc",
    ],
    "quality": [
        # Arabic
        "جودة", "جودتها", "نوعية",
        # French / Arabizi
        "qualité", "quality", "kwayess", "kwaysa", "mli7", "mliha",
        "khayeb", "khayba",  # also taste — context decides
    ],
}

#
# POLARITY SIGNALS
# Words that flip sentiment in the CONTEXT of an aspect mention.
# We look at the 4 words before and after each aspect keyword.

POSITIVE_SIGNALS = {
    # Arabic
    "ممتاز", "ممتازة", "زين", "زينة", "مليح", "مليحة", "كويس", "كويسة",
    "أحسن", "رائع", "رائعة", "بنين", "يستاهل",
    # Arabizi
    "zwin", "zwina", "mli7", "mliha", "kwayess", "kwaysa", "top",
    "3jebni", "7lwa", "bnin", "bni", "yestahel",
    # French
    "bon", "bonne", "bien", "excellent", "excellente", "délicieux",
    "délicieuse", "parfait", "parfaite", "recommande", "naturel",
    "abordable", "correct", "correcte", "super", "génial",
    # English
    "good", "great", "best", "love", "excellent", "amazing",
    # Emoji tokens (added by normalizer)
    "pos_emoji",
}

NEGATIVE_SIGNALS = {
    # Arabic
    "خايب", "خايبة", "غالي", "غالية", "سيء", "سيئة",
    "ما نشريش", "ما نعاودش", "منتهي", "مقطوع",
    # Arabizi
    "khayeb", "khayba", "ghali", "ghalia", "ma3jbni",
    "machi zin", "machi mli7",
    # French
    "mauvais", "mauvaise", "cher", "chère", "déçu", "déçue",
    "inacceptable", "nul", "nulle", "périmé", "expiré",
    "trop sucré", "artificiel", "plastique",
    # English
    "bad", "terrible", "worst", "hate", "awful",
    # Emoji tokens
    "neg_emoji",
    # Negation markers  if these appear before a positive word, it flips
    "ما", "مش", "مچي", "machi", "pas", "ne", "non",
}

NEGATION_MARKERS = {"ما", "مش", "مچي", "machi", "pas", "ne", "non", "ma", "machi"}

# CORE EXTRACTION FUNCTION


def extract_aspects(text: str, normalized_text: str = None) -> list[dict]:
    """

    INPUT:
        text            : raw review text (used for display)
        normalized_text : cleaned text from normalizer (used for matching)
                          if None, we normalize text ourselves

    OUTPUT:
        List of dicts, one per aspect found:
        [
            {"aspect": "price",  "polarity": "negative", "confidence": 0.8},
            {"aspect": "taste",  "polarity": "positive", "confidence": 0.9},
        ]

    HOW IT WORKS:
        1. Split normalized text into tokens (words)
        2. For each aspect category, check if any keyword appears
        3. When a keyword is found, extract a CONTEXT WINDOW of ±4 tokens
        4. Count positive and negative signals in that window
        5. Handle negation (ما + positive = negative)
        6. Assign polarity based on signal counts
    """
    if not normalized_text:
        from normalize import normalize_darija
        normalized_text = normalize_darija(text)

    if not normalized_text:
        return []

    # Tokenize  split on whitespace, lowercase
    tokens = normalized_text.lower().split()
    n_tokens = len(tokens)
    results = []
    seen_aspects = set()  # avoid duplicate aspect entries per review

    for aspect, keywords in ASPECT_LEXICON.items():
        if aspect in seen_aspects:
            continue

        # Find positions of aspect keywords in the token list
        keyword_positions = []
        for i, token in enumerate(tokens):
            for kw in keywords:
                if kw.lower() in token or token in kw.lower():
                    keyword_positions.append(i)
                    break

        if not keyword_positions:
            continue  # this aspect not mentioned in this review

        # For each keyword position, build a context window
        pos_score = 0
        neg_score = 0

        for pos in keyword_positions:
            window_start = max(0, pos - 4)
            window_end   = min(n_tokens, pos + 5)
            window_tokens = tokens[window_start:window_end]

            # Check each window token for sentiment signals
            for j, w_token in enumerate(window_tokens):
                # Check positive signals
                for sig in POSITIVE_SIGNALS:
                    if sig.lower() in w_token or w_token in sig.lower():
                        # Check for negation in the 2 tokens before this one
                        preceding = window_tokens[max(0, j-2):j]
                        if any(neg.lower() in p for neg in NEGATION_MARKERS for p in preceding):
                            neg_score += 1  # negated positive = negative
                        else:
                            pos_score += 1
                        break

                # Check negative signals
                for sig in NEGATIVE_SIGNALS:
                    if sig.lower() in w_token or w_token in sig.lower():
                        neg_score += 1
                        break

        # Determine polarity
        if pos_score == 0 and neg_score == 0:
            polarity = "neutral"
            confidence = 0.5
        elif pos_score > neg_score:
            polarity = "positive"
            confidence = round(min(0.95, 0.6 + (pos_score - neg_score) * 0.1), 2)
        elif neg_score > pos_score:
            polarity = "negative"
            confidence = round(min(0.95, 0.6 + (neg_score - pos_score) * 0.1), 2)
        else:
            # Tie → neutral
            polarity = "neutral"
            confidence = 0.5

        results.append({
            "aspect":     aspect,
            "polarity":   polarity,
            "confidence": confidence,
        })
        seen_aspects.add(aspect)

    return results


#  BATCH RUNNER (writes results to DB)


def run_absa_on_all_reviews(db_path: str = DB_PATH):
    """
    Run ABSA on every review in the database that has a sentiment.
    Skips reviews already processed (have entries in aspects table).
    Writes results to the aspects table.

    Call this AFTER batch sentiment inference is done.
    """
    conn = sqlite3.connect(db_path)

    # Get reviews that haven't been ABSA-processed yet
    # We check: review_id NOT IN (SELECT review_id FROM aspects)
    reviews = conn.execute("""
        SELECT r.id, r.text, r.text_normalized
        FROM reviews r
        WHERE r.sentiment IS NOT NULL
          AND r.id NOT IN (SELECT DISTINCT review_id FROM aspects)
    """).fetchall()

    if not reviews:
        print("[absa] No new reviews to process.")
        conn.close()
        return

    print(f"[absa] Processing {len(reviews)} reviews...")

    total_aspects = 0
    for review_id, text, normalized in reviews:
        aspects = extract_aspects(text, normalized)

        for asp in aspects:
            conn.execute("""
                INSERT INTO aspects (review_id, aspect, polarity)
                VALUES (?, ?, ?)
            """, (review_id, asp["aspect"], asp["polarity"]))
            total_aspects += 1

    conn.commit()
    conn.close()
    print(f"[absa] Done. Extracted {total_aspects} aspect entries.")


# 
# QUICK TEST ()
# 

if __name__ == "__main__":
    TEST_REVIEWS = [
        (
            "رامي بنين بزاف، الطعم ممتاز",
            "Should find: taste=positive"
        ),
        (
            "الثمن غالي شوية ولكن الجودة تستاهل",
            "Should find: price=negative, quality=positive"
        ),
        (
            "ma3jbni l packaging, kibir bzaf",
            "Should find: packaging=negative"
        ),
        (
            "top qualité, je recommande fortement",
            "Should find: quality=positive"
        ),
        (
            "الڤولة خايبة، ما نشريش مرة أخرى",
            "Should find: taste=negative"
        ),
        (
            "produit expiré reçu, date dépassée de 2 semaines",
            "Should find: freshness=negative"
        ),
        (
            "ما لقيتش فالحانوت، توزيع عيان",
            "Should find: availability=negative"
        ),
        (
            "الطعم مليح والعلبة زوينة",
            "Should find: taste=positive, packaging=positive"
        ),
    ]

    print("="*60)
    print("  ABSA EXTRACTION TEST")
    print("="*60)

    for text, expectation in TEST_REVIEWS:
        aspects = extract_aspects(text, text)
        print(f"\nTEXT    : {text}")
        print(f"EXPECT  : {expectation}")
        if aspects:
            for a in aspects:
                print(f"FOUND   : {a['aspect']:15s} → {a['polarity']:10s} (conf={a['confidence']})")
        else:
            print("FOUND   : (no aspects detected)")

    print("\n" + "="*60)
    print("Running on DB reviews...")
    run_absa_on_all_reviews()

    # Show summary
    conn = sqlite3.connect(DB_PATH)
    print("\nAspect summary in DB:")
    rows = conn.execute("""
        SELECT aspect, polarity, COUNT(*) as n
        FROM aspects
        GROUP BY aspect, polarity
        ORDER BY aspect, polarity
    """).fetchall()
    for aspect, polarity, n in rows:
        print(f"  {aspect:15s} {polarity:10s} {n} reviews")
    conn.close()