# tests/test_normalizer.py
#   From the project root folder:
#   python tests/test_normalizer.py
#   - Every "RESULT" line should make linguistic sense
#   - Arabizi numbers (3, 7, 9) should become Arabic letters
#   - Emojis should disappear but POS_EMOJI/NEG_EMOJI token appears
#   - URLs, @mentions should disappear
#   - Text should be lowercase
#   - No crashes on weird input
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp.normalize import (
    normalize_darija,
    extract_emoji_sentiment,
    preprocess_row,
    preprocess_batch,
)

# Terminal colors for readability 
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def print_section(title: str):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")


def print_test(input_text: str, result: str, note: str):
    print(f"\n  {YELLOW}INPUT :{RESET}  {repr(input_text)}")
    print(f"  {GREEN}RESULT:{RESET}  {repr(result)}")
    print(f"  {BLUE}NOTE  :{RESET}  {note}")


def run_all_tests():

    print_section("TEST GROUP 1 — Arabizi conversion")

    arabizi_tests = [
        (
            "3jebni bzzaf ramy",
            "3 → ع (ain). Should see عجبني in output."
        ),
        (
            "ma3jbni5 el gout",
            "ma3 = ماع, 5 at end = خ. Negative phrase: I didn't like the taste."
        ),
        (
            "el prix ghali bzzaf",
            "gh → غ (ghain). 'ghali' = expensive. Should see غالي."
        ),
        (
            "chkoun yechri ramy",
            "ch → ش (shin). 'chkoun' = who. Should see شكون يشري."
        ),
        (
            "7lwa bzzaf el 9ayed",
            "7 → ح, 9 → ق. 'Sweet, very strong.' Should see حلوا and قايد."
        ),
        (
            "9al ramy top khi",
            "9 → ق, kh → خ. 'Said Ramy is top, bro.' قال and خي."
        ),
        (
            "el packaging khayeb 3la rasek",
            "kh → خ for khayeb (bad). 3la → عل. 'Packaging is bad, come on.'"
        ),
    ]

    for text, note in arabizi_tests:
        result = normalize_darija(text)
        print_test(text, result, note)

    
    # TEST Emoji Extraction

    print_section("TEST GROUP 2 — Emoji sentiment extraction")

    emoji_tests = [
        ("ramy zin ❤️",         "Should → POS_EMOJI token appended"),
        ("el prix ghali 👎",     "Should → NEG_EMOJI token appended"),
        ("ramy top 😋👌",        "Multiple pos emojis → POS_EMOJI"),
        ("mli7 chwiya 😋 bas ghali 😡", "Mixed: neg wins → NEG_EMOJI"),
        ("ramy jus",             "No emojis → no token appended"),
        ("👍👍👍",               "Only emojis → POS_EMOJI, empty text otherwise"),
    ]

    for text, note in emoji_tests:
        emoji_signal = extract_emoji_sentiment(text)
        row = preprocess_row({"text": text})
        print_test(text, row["text_normalized"], f"{note} | emoji_signal='{emoji_signal}'")

    # 
    # TEST  Noise Removal
    # 
    print_section("TEST GROUP 3 — URLs, mentions, hashtags, noise removal")

    noise_tests = [
        (
            "check https://ramy.dz/products pour les offres",
            "URL should be completely removed"
        ),
        (
            "@ramyfood el gout khayeb, ma3jbni5",
            "@mention removed, rest kept"
        ),
        (
            "#RamyJus #JusAlgérie el produit zin",
            "# symbol removed but word kept: 'ramyjus jusgérie'"
        ),
        (
            "RAMY TOP PRODUIT VRAIMENT ZIIIIN",
            "All uppercase → all lowercase"
        ),
        (
            "hhhhhhhh el gout ziiiin",
            "'hhhhhhhh' → 'hh', 'ziiiin' → 'ziin' (max 2 repetitions)"
        ),
        (
            "   ramy    jus    ",
            "Multiple spaces collapsed, leading/trailing trimmed"
        ),
    ]

    for text, note in noise_tests:
        result = normalize_darija(text)
        print_test(text, result, note)

    
    # TEST Real-world Mixed Darija
   
    
    print_section("TEST GROUP 4 — Real-world mixed Darija reviews")

    real_tests = [
        (
            "3jebni bzzaf el gout dyal ramy, walakin el thmen ghali chwiya",
            "Mixed Arabizi + French + Arabic. 'I liked Ramy's taste a lot but price is a bit expensive.'"
        ),
        (
            "el packaging jdid zwin, rani nchriha dima ldar ❤️",
            "'The new packaging is nice, I always buy it at home.' Positive."
        ),
        (
            "Machi bhal qbal, khedmtha tghayret 😡 chwiya khayba maintenant",
            "'Not like before, recipe changed, a bit bad now.' Mixed Darija/French."
        ),
        (
            "makach fi hanout, lazem ramy tzid el tawzi3 😤",
            "'Not in the store, Ramy needs to increase distribution.' Availability complaint."
        ),
        (
            "صراحة رامي أحسن من كل المشروبات الموجودة",
            "Pure Arabic. 'Honestly Ramy is the best of all available drinks.'"
        ),
        (
            "le jus ramy est vraiment délicieux, je recommande 👌",
            "Pure French. 'Ramy juice is truly delicious, I recommend it.'"
        ),
        (
            "3jebni 3jebni 3jebni 3jebni hhhh top top",
            "Repeated words/chars. Should compress: 3 occurrences → 2."
        ),
    ]

    for text, note in real_tests:
        row = preprocess_row({"text": text})
        print_test(text, row["text_normalized"], note)

    # 
    # TEST  Edge Cases 
    # 
    print_section("TEST GROUP 5 — Edge cases and bad input")

    edge_cases = [
        (None,          "None input → must return empty string, no crash"),
        ("",            "Empty string → empty string"),
        ("   ",         "Whitespace only → empty string"),
        ("123",         "Numbers only → should not crash"),
        ("😡😡😡",     "Emojis only → NEG_EMOJI token or empty"),
        ("a",           "Single char → 'a'"),
        ("." * 500,     "500 dots → empty or near-empty"),
        ("ا" * 100,    "100 Arabic alefs → should compress or keep"),
    ]

    print(f"\n  {YELLOW}Testing edge cases — none of these should crash:{RESET}")
    all_passed = True
    for text, note in edge_cases:
        try:
            result = normalize_darija(text) if text is not None else normalize_darija(None)
            status = f"{GREEN}OK{RESET}"
        except Exception as e:
            result = f"CRASHED: {e}"
            status = f"{RED}FAILED{RESET}"
            all_passed = False
        print(f"\n  [{status}] {repr(text)[:40]}")
        print(f"          → {repr(result)[:60]}")
        print(f"          {BLUE}{note}{RESET}")

    # 
    # TEST Batch Processing
    # 
    print_section("TEST GROUP 6 — Batch processing (preprocess_batch)")

    batch_input = [
        {"text": "3jebni ramy bzzaf ❤️",     "platform": "facebook"},
        {"text": "el prix ghali 👎",           "platform": "tiktok"},
        {"text": "",                           "platform": "youtube"},   # empty — should be skipped
        {"text": "   ",                        "platform": "jumia"},     # whitespace — should be skipped
        {"text": "le packaging est bien 👌",   "platform": "instagram"},
    ]

    from nlp.normalize import preprocess_batch
    results = preprocess_batch(batch_input)

    print(f"\n  Input rows:  {len(batch_input)}")
    print(f"  Output rows: {len(results)} (empty rows should be excluded)")
    print()
    for r in results:
        print(f"  [{r['platform']:10s}] {repr(r['text_normalized'])}")

    # =========================================================
    # SUMMARY
    # =========================================================
    print_section("SUMMARY — What to check")
    print(f"""
  {GREEN}✓{RESET} All Arabizi numbers (3,7,9,5,2) converted to Arabic letters
  {GREEN}✓{RESET} 'ch', 'gh', 'kh', 'dh' converted to ش غ خ ذ
  {GREEN}✓{RESET} Positive emojis → POS_EMOJI token appended
  {GREEN}✓{RESET} Negative emojis → NEG_EMOJI token appended  
  {GREEN}✓{RESET} URLs completely removed
  {GREEN}✓{RESET} @mentions removed
  {GREEN}✓{RESET} #Hashtag symbol removed, word kept
  {GREEN}✓{RESET} All text lowercased
  {GREEN}✓{RESET} Repeated chars compressed (max 2)
  {GREEN}✓{RESET} Multiple spaces collapsed
  {GREEN}✓{RESET} None/empty/bad input returns '' without crashing
  {GREEN}✓{RESET} Batch processor skips empty rows

  {YELLOW}If anything looks wrong above, fix normalizer.py before training.{RESET}
  {YELLOW}The model is only as good as the data you feed it.{RESET}
    """)


if __name__ == "__main__":
    run_all_tests()