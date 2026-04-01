# =============================================================================
# nlp/normalizer.py
# =============================================================================
# PURPOSE:
#   Clean raw Algerian Darija text so it can be fed into DziriBERT.
#   Darija is a nightmare for NLP because one sentence can mix:
#     - Arabic script   : "الطعم زين"
#     - Arabizi         : "3jebni" (Franco-Arabic using numbers as letters)
#     - French words    : "le prix est cher"
#     - Emojis          : ❤️ 👎 😋
#     - Noise           : URLs, mentions, repeated characters
#
#   This file handles ALL of that in one clean pipeline.
#   Every other file (train.py, predict.py, absa.py) calls normalize_darija().
# =============================================================================

import re
import unicodedata
from typing import Optional


# ARABIZI MAP
# arabizi or daridja  is when Algerians write Arabic sounds using Latin letters + numbers.
# the numbers represent Arabic letters that don't exist in the Latin alphabet.
# this is EXTREMELY common in Algerian social media.
# examples of real Darija Arabizi:
#   "3jebni"    → "عجبني"   (I liked it)
#   "ma3jbni5"  → "ماعجبنيش" (I didn't like it)  -- 5/kh at end = ش sometimes
#   "7lwa"      → "حلوة"    (sweet / nice)
#   "kho"       → (bro)
#
# order matters soo we  Apply LONGER patterns first.
# "kh" must be replaced before "k", otherwise "kh" becomes "كh" instead of "خ"



ARABIZI_MAP = {
    # Multi-character patterns— MUST be processed before single chars
    "kh":  "خ",   # خ  (kha)
    "gh":  "غ",   # غ  (ghain)
    "ch":  "ش",   # ش  (shin) — very common: "chkoun"=who, "chno"=what
    "dh":  "ذ",   # ذ  (dhal)
    "th":  "ث",   # ث  (tha)  — less common but exists
    "ts":  "تس",  # تس combination

    # number to arabic letter mappings 
    "3a":  "عا",  # 3 followed by a = عا
    "3i":  "عي",  # 3 followed by i = عي
    "3o":  "عو",  # 3 followed by o = عو
    "3":   "ع",   # 3 alone = ع  (ain) — most common: "3jebni", "3la", "ma3"
    "7a":  "حا",
    "7i":  "حي",
    "7":   "ح",   # 7 = ح  (h) — "7lwa"=sweet, "7it"=wall
    "9a":  "قا",
    "9":   "ق",   # 9 = ق  ( "9arib"=near
    "2a":  "أا",
    "2":   "ء",   # 2 = ء  (hamza) — "2al"=said, "ra2is"=president
    "5":   "خ",   # 5 = خ  (alternate for kha) — "5obz"=bread, end suffix "5"
    "4":   "ش",   # 4 = ش  (alternate for shin) — less common
}


#EMOJI SENTIMENT EXTRACTION

#we extract emoji sentiment BEFORE stripping emojis.
# Why? Because "هههه 😋" means very different things than "هههه 😡"
# We convert the emoji signal into a text token .
# Token added to end of normalized text:
#   POS_EMOJI  → strong positive signal
#   NEG_EMOJI  → strong negative signal
#   (nothing)  → neutral / no relevant emoji


POSITIVE_EMOJIS = {
    "❤️", "😍", "👍", "🔥", "💯", "😋", "👌", "🥰",
    "😊", "✅", "💪", "🙌", "😄", "🤩", "💖", "♥️",
    "😁", "🥳", "👏", "💚", "💛", "🧡", "❤",
}

NEGATIVE_EMOJIS = {
    "👎", "😡", "🤮", "😤", "💀", "❌", "😒", "🙄",
    "😠", "🤢", "😞", "😔", "💔", "🚫", "⛔", "😑",
}


def extract_emoji_sentiment(text: str) -> str:
    """
    scan text for positive/negative emojis.
    Returns 'POS_EMOJI', 'NEG_EMOJI', or '' (empty string)
    Logic: negative wins if BOTH types are present.
    """
    has_pos = any(em in text for em in POSITIVE_EMOJIS)
    has_neg = any(em in text for em in NEGATIVE_EMOJIS)

    if has_neg:
        return "NEG_EMOJI"
    if has_pos:
        return "POS_EMOJI"
    return ""


# NORMALIZER


def normalize_darija(text: str) -> str:
    """
    INPUT:  any raw text from social media (Arabic, Arabizi, French, mixed)
    OUTPUT: Cleaned, normalized text ready for  tokenization

    pipeline steps (in order soooo order matters!):
        1.  Guard clause       — handle None/empty input
        2.  lowercase          — "RAMY" → "ramy"
        3.  remove URLs        — strip http links
        4.  Remove @mentions   — @ramyfood → (removed)
        5.  Keep hashtag text  — #RamyJus → ramyjus
        6.  Remove Arabic diacritics (tashkeel) — noise for classification
        7.  Apply Arabizi map  — "3jebni" → "عجبني"
        8.  Normalize repeated chars — "hhhhhh" → "hh"
        9.  Remove emojis + special chars
        10. Normalize whitespace — collapse multiple spaces
    """

    # Step 1 — Guard clause
    # Never crash on bad input. Return empty string for None/non-strings.
    if not text or not isinstance(text, str):
        return ""

    # Step 2 — Lowercase
    # Do this first so pattern matching later is case-insensitive.
    # "RAMY" and "Ramy" and "ramy" should all be treated the same.
    text = text.lower().strip()

    # Step 3 — Remove URLs
    # URLs add noise and are never meaningful for sentiment.
    # Pattern covers http, https, and bare www. links.
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"www\.\S+", "", text)

    # Step 4 — Remove @mentions
    # "@ramyfood" is just a tag, not an opinion. Remove it entirely.
    text = re.sub(r"@\w+", "", text)

    # Step 5 — Keep hashtag content, drop the #
    # "#RamyJus" becomes "ramyjus" — we want the word, not the symbol.
    # After lowercase (step 2) this is already lowercase.
    text = re.sub(r"#(\w+)", r"\1", text)

    # Step 6 — Remove Arabic diacritics (tashkeel / harakat)
    # These are the small marks above/below Arabic letters (ً ٍ ٌ ّ etc.)
    # They are pronunciation guides, not needed for sentiment classification.
    # Unicode range U+0610–U+061A and U+064B–U+065F covers them.
    text = re.sub(r"[\u0610-\u061A\u064B-\u065F]", "", text)

    # Step 7 — Apply Arabizi → Arabic conversion
    # CRITICAL: Sort by key length DESCENDING so "kh" is processed before "k".
    # If we processed "k" first, "kh" would become "كh" (wrong).
    #
    # For number-based Arabizi (3, 7, 9, 5, 2): only convert when the digit
    # is adjacent to a letter. This prevents "prix 95 DZD" from mangling "95".
    # We use a regex lookahead/lookbehind for single-digit patterns.
    DIGIT_KEYS = {"3a","3i","3o","3","7a","7i","7","9a","9","2a","2","5","4"}

    for latin, arabic in sorted(ARABIZI_MAP.items(), key=lambda x: -len(x[0])):
        if latin in DIGIT_KEYS and len(latin) == 1:
            # Only convert digit when surrounded by letters (Arabizi context)
            # e.g. "3jebni" yes, "95 DZD" no
            text = re.sub(
                r"(?<=[a-z\u0600-\u06FF])" + re.escape(latin) +
                r"|" + re.escape(latin) + r"(?=[a-z\u0600-\u06FF])",
                arabic, text
            )
        else:
            text = text.replace(latin, arabic)

    # Step 8 — Normalize repeated characters
    # Algerians write "hhhhhh" or "بززززف" for emphasis.
    # We keep max 2 repetitions — enough to signal emphasis, less noise.
    # "waaaaaw" → "waaw", "ززززين" → "ززين"
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)

    # Step 9 — Remove emojis and special characters
    # Keep: Arabic letters (U+0600–U+06FF), Latin letters, digits, spaces.
    # Remove: emojis, punctuation, symbols.
    # Note: we already extracted emoji sentiment before this step (in preprocess_row).
    text = re.sub(r"[^\w\s\u0600-\u06FF\u0750-\u077F]", " ", text)

    # Step 10 — Normalize whitespace
    # Multiple spaces, tabs, newlines → single space.
    text = re.sub(r"\s+", " ", text).strip()

    return text


# =============================================================================
# SECTION 4 — ROW PROCESSOR
# =============================================================================
# This wraps normalize_darija() for use on dict rows (from the database).
# It also handles the emoji signal injection.
# =============================================================================

def preprocess_row(row: dict) -> dict:
    """
    Process one review dict. Adds 'text_normalized' key.

    INPUT:  {"text": "3jebni ramy ❤️", "platform": "facebook", ...}
    OUTPUT: same dict + {"text_normalized": "عجبني رامي POS_EMOJI"}

    The emoji token at the end genuinely helps the model.
    A review saying "el prix ghali 😡" is more clearly negative
    than "el prix ghali" without the emoji signal.
    """
    raw_text = row.get("text", "")

    # Extract emoji sentiment BEFORE normalizing (step 9 strips emojis)
    emoji_signal = extract_emoji_sentiment(raw_text)

    # Normalize the text
    normalized = normalize_darija(raw_text)

    # Append emoji signal as a special token if present
    if emoji_signal and normalized:
        normalized = normalized + " " + emoji_signal

    # Write back to the row dict (modifies in place + returns)
    row["text_normalized"] = normalized
    return row


# =============================================================================
# SECTION 5 — BATCH PROCESSOR
# =============================================================================
# For processing lists of rows (from DB or CSV).
# =============================================================================

def preprocess_batch(rows: list[dict]) -> list[dict]:
    """
    Process a list of review dicts.
    Skips rows where text is empty after normalization.

    INPUT:  [{"text": "...", ...}, ...]
    OUTPUT: same list, each row now has "text_normalized" key
            rows with empty normalized text are EXCLUDED
    """
    processed = []
    skipped = 0

    for row in rows:
        result = preprocess_row(row.copy())  # copy() to avoid mutating original
        if result["text_normalized"]:        # skip if normalized text is empty
            processed.append(result)
        else:
            skipped += 1

    if skipped > 0:
        print(f"[normalizer] Skipped {skipped} empty rows after normalization")

    return processed