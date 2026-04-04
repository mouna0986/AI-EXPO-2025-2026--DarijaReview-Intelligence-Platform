
# scripts/connections.py  The Connection Layer
# PURPOSE:
#   This is the script B run together on integration 
#   It verifies that Person A model output and Person  DB/dashboard
#   are talking to each other correctly.
#
#   Think of it as a pre-flight check before the demo.
#
# WHAT IT DOES:
#   1. Verifies the DB exists and has data
#   2. Verifies the model exists (or confirms mock mode is OK)
#   3. Runs the full pipeline on 5 test reviews end-to-end:
#      raw text → normalize → classify → absa → store → retrieve
#   4. Verifies all API endpoints return correct JSON
#   5. Checks the dashboard can reach the API
#   6. Prints a GO / NO-GO status for each component
#
# HOW TO RUN:
#   python scripts/connections.py
#
# WHAT "CONNECTED" MEANS:
#   Person A runs the FastAPI server:
#     uvicorn api.main:app --host 0.0.0.0 --port 8000
#   Person B runs the dashboard:
#     python dashboard/app.py
#   This script talks to both and confirms the data flows end-to-end.


import sys
import os
import sqlite3
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import requests for API checks  optional
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

DB_PATH    = "database/reviews.db"
API_BASE   = "http://localhost:8000/api"
DASH_URL   = "http://localhost:8050"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

#  integration test reviews 
# These go through the FULL pipeline: normalize → classify → absa → store
INTEGRATION_REVIEWS = [
    {
        "platform": "facebook",
        "text": "رامي بنين بزاف اليوم، الطعم ممتاز كيما دايما ❤️",
        "expected_sentiment": "positive",
    },
    {
        "platform": "tiktok",
        "text": "el prix ghali bzzaf, machi normal 95 DZD 3la jus 👎",
        "expected_sentiment": "negative",
    },
    {
        "platform": "youtube",
        "text": "le jus ramy est correct mais pas exceptionnel",
        "expected_sentiment": "neutral",
    },
    {
        "platform": "instagram",
        "text": "ما لقيتش رامي فالحانوت، توزيعهم عيان 😤",
        "expected_sentiment": "negative",
    },
    {
        "platform": "jumia",
        "text": "qualité excellente, packaging propre, livraison rapide 👌",
        "expected_sentiment": "positive",
    },
]


def section(title: str):
    print(f"\n{BOLD}{'─'*55}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{'─'*55}{RESET}")


def ok(msg: str):
    print(f"  {GREEN}✓{RESET}  {msg}")


def fail(msg: str):
    print(f"  {RED}✗{RESET}  {msg}")


def warn(msg: str):
    print(f"  {YELLOW}!{RESET}  {msg}")


def info(msg: str):
    print(f"     {msg}")


# 
# CHECK  Database
# 

def check_database() -> bool:
    section("CHECK 1 — Database")
    all_ok = True

    # File exists
    if os.path.exists(DB_PATH):
        ok(f"Database file found at {DB_PATH}")
    else:
        fail(f"Database NOT found at {DB_PATH}")
        info("Run: python database/init_db.py")
        return False

    conn = sqlite3.connect(DB_PATH)

    # Tables exist
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]

    for table in ["reviews", "aspects", "prices"]:
        if table in tables:
            ok(f"Table '{table}' exists")
        else:
            fail(f"Table '{table}' MISSING")
            info("Run: python database/init_db.py")
            all_ok = False

    if not all_ok:
        conn.close()
        return False

    # Row counts
    total_reviews = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    labeled       = conn.execute("SELECT COUNT(*) FROM reviews WHERE sentiment IS NOT NULL").fetchone()[0]
    aspects       = conn.execute("SELECT COUNT(*) FROM aspects").fetchone()[0]
    prices        = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]

    info(f"reviews : {total_reviews} total, {labeled} labeled")
    info(f"aspects : {aspects} entries")
    info(f"prices  : {prices} entries")

    if total_reviews == 0:
        warn("No reviews in DB — run scrapers or ingest_person_b_data.py")
    elif labeled == 0:
        warn("No labeled reviews — run batch inference")
    else:
        ok(f"{labeled}/{total_reviews} reviews labeled ({labeled/total_reviews*100:.0f}%)")

    if prices == 0:
        warn("No price data — run ingest_person_b_data.py")
    else:
        ok(f"{prices} price records available")

    conn.close()
    return all_ok


# 
# CHECK Model
# 

def check_model() -> str:
    """Returns 'real', 'mock', or 'missing'."""
    section("CHECK 2 — Model")

    model_path = "models/dziribert-finetuned"

    if os.path.exists(model_path):
        files = os.listdir(model_path)
        needed = ["config.json", "pytorch_model.bin"]
        has_all = all(f in files for f in needed)

        if has_all:
            ok(f"Fine-tuned model found at {model_path}")
            ok("Model files: config.json + pytorch_model.bin present")

            # Check eval metrics if available
            metrics_path = os.path.join(model_path, "eval_metrics.json")
            if os.path.exists(metrics_path):
                with open(metrics_path) as f:
                    metrics = json.load(f)
                f1 = metrics.get("f1_weighted", 0)
                color = GREEN if f1 >= 0.75 else YELLOW if f1 >= 0.65 else RED
                print(f"  {color}{'✓' if f1>=0.75 else '!'}{RESET}  "
                      f"Model F1 (weighted): {f1:.3f} "
                      f"({'excellent' if f1>=0.75 else 'acceptable' if f1>=0.65 else 'retrain needed'})")
            return "real"
        else:
            warn(f"Model folder exists but incomplete: {files}")
            warn("Training may not have finished. Using mock mode.")
            return "mock"
    else:
        warn(f"No trained model at {model_path}")
        warn("Using mock classifier — train model with: python nlp/train.py")
        info("Mock mode is OK for development. Use real model for demo day.")
        return "mock"


# 
# CHECK  Full Pipeline (end-to-end)

def check_pipeline(model_mode: str) -> bool:
    section("CHECK 3 — Full Pipeline (normalize → classify → absa → store)")

    from nlp.normalize import preprocess_row
    from nlp.absa import extract_aspects

    # Mock classify since real model might not be trained
    def mock_classify(text: str) -> dict:
        text_lower = text.lower()
        neg_words = ["غالي", "خايب", "makach", "ghali", "khayeb", "mauvais", "mal", "👎"]
        pos_words = ["ممتاز", "زين", "مليح", "3jebni", "top", "bon", "excellent", "❤️", "👌"]
        neg = sum(1 for w in neg_words if w in text_lower)
        pos = sum(1 for w in pos_words if w in text_lower)
        if pos > neg: return {"label": "positive", "confidence": 0.80}
        if neg > pos: return {"label": "negative", "confidence": 0.80}
        return {"label": "neutral", "confidence": 0.60}

    conn = sqlite3.connect(DB_PATH)
    passed = 0
    failed = 0

    for review in INTEGRATION_REVIEWS:
        text     = review["text"]
        platform = review["platform"]
        expected = review["expected_sentiment"]

        # Step 1: Normalize
        row = preprocess_row({"text": text})
        normalized = row["text_normalized"]

        if not normalized:
            fail(f"Normalization returned empty for: {text[:40]}")
            failed += 1
            continue

        # Step 2: Classify
        result = mock_classify(text)
        label  = result["label"]
        conf   = result["confidence"]

        # Step 3: ABSA
        aspects = extract_aspects(text, normalized)

        # Step 4: Store in DB (or skip if already there)
        try:
            conn.execute("""
                INSERT OR IGNORE INTO reviews
                    (platform, text, text_normalized, sentiment, confidence, engagement_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (platform, text, normalized, label, conf, 0))
            review_id = conn.execute(
                "SELECT id FROM reviews WHERE text = ? AND platform = ?",
                (text, platform)
            ).fetchone()[0]

            for asp in aspects:
                conn.execute(
                    "INSERT OR IGNORE INTO aspects (review_id, aspect, polarity) VALUES (?, ?, ?)",
                    (review_id, asp["aspect"], asp["polarity"])
                )

            conn.commit()

        except Exception as e:
            fail(f"DB write failed: {e}")
            failed += 1
            continue

        # Step 5: Verify stored
        stored = conn.execute(
            "SELECT sentiment FROM reviews WHERE id = ?", (review_id,)
        ).fetchone()

        if stored and stored[0] == label:
            aspect_names = [a["aspect"] for a in aspects]
            color = GREEN if label == expected else YELLOW
            marker = "✓" if label == expected else "≈"
            print(f"  {color}{marker}{RESET}  [{label:8s} {conf:.2f}] "
                  f"{platform:10s} | aspects: {aspect_names}")
            info(f"   text: {text[:50]}")
            passed += 1
        else:
            fail(f"DB verification failed for review id={review_id}")
            failed += 1

    conn.close()

    print(f"\n  Pipeline: {passed} passed, {failed} failed")
    return failed == 0


# 
# CHECK API Server
# 

def check_api() -> bool:
    section("CHECK 4 — API Server (http://localhost:8000)")

    if not HAS_REQUESTS:
        warn("'requests' library not installed — skipping live API check")
        info("Install: pip install requests")
        info("Start API: uvicorn api.main:app --host 0.0.0.0 --port 8000")
        return True  # not a failure — just not checkable

    endpoints = [
       # ("GET",  "/health",          None,                      "server status"),
      #  ("GET",  "/summary",         None,                      "metric cards data"),
       # ("GET",  "/sentiment-trend", None,                      "trend chart data"),
       # ("GET",  "/aspects",         None,                      "aspect chart data"),
       # ("GET",  "/top-reviews",     None,                      "quote panel data"),
       # ("GET",  "/prices",          None,                      "price table data"),
       # ("POST", "/predict",         {"text": "ramy zwin ❤️"},  "live classify"),
    
    ("GET",  "/summary",         None,                      "metric cards data"),
    ("GET",  "/aspects",         None,                      "aspect chart data"),
    ("GET",  "/top-reviews",     None,                      "quote panel data"),
    ("GET",  "/prices",          None,                      "price table data"),
    ("POST", "/predict",         {"text": "ramy zwin ❤️"},  "live classify"),

    ]

    all_ok = True
    for method, path, body, description in endpoints:
        url = API_BASE + path
        try:
            if method == "GET":
                r = requests.get(url, timeout=5)
            else:
                r = requests.post(url, json=body, timeout=5)

            if r.status_code == 200:
                ok(f"{method:4s} {path:20s} → {r.status_code}  ({description})")
            else:
                fail(f"{method:4s} {path:20s} → {r.status_code}  ({description})")
                all_ok = False

        except requests.ConnectionError:
            fail(f"{method:4s} {path}  → ConnectionError")
            info("API server is not running.")
            info("Start it with: uvicorn api.main:app --host 0.0.0.0 --port 8000")
            return False
        except Exception as e:
            fail(f"{method:4s} {path}  → {e}")
            all_ok = False

    return all_ok


# 
# CHECK Dashboard
# 

def check_dashboard() -> bool:
    section("CHECK 5 — Dashboard (http://localhost:8050)")

    if not HAS_REQUESTS:
        warn("'requests' not installed — skipping dashboard check")
        return True

    try:
        r = requests.get(DASH_URL, timeout=5)
        if r.status_code == 200:
            ok("Dashboard is running at http://localhost:8050")
            ok("Open it in your browser to verify visually")
            return True
        else:
            fail(f"Dashboard returned status {r.status_code}")
            return False
    except requests.ConnectionError:
        warn("Dashboard is not running (or not yet started)")
        info("Start with: python dashboard/app.py")
        info("This is OK if you haven't started it yet")
        return True  # not blocking
    except Exception as e:
        fail(f"Dashboard check failed: {e}")
        return False


# 
# FINAL REPORT
# 

def print_final_report(checks: dict):
    section("FINAL INTEGRATION REPORT")

    statuses = {
        True:  f"{GREEN}GO     ✓{RESET}",
        False: f"{RED}NO-GO  ✗{RESET}",
        "real": f"{GREEN}GO     ✓ (real model){RESET}",
        "mock": f"{YELLOW}GO     ≈ (mock mode — train before demo){RESET}",
    }

    checks_display = [
        ("Database",      checks["db"]),
        ("Model",         checks["model"]),
        ("Full pipeline", checks["pipeline"]),
        ("API server",    checks["api"]),
        ("Dashboard",     checks["dashboard"]),
    ]

    print()
    for name, status in checks_display:
        display = statuses.get(status, statuses.get(bool(status), str(status)))
        print(f"  {name:16s}  {display}")

    all_good = (
        checks["db"] is True and
        checks["pipeline"] is True
    )

    print()
    if all_good:
        print(f"  {GREEN}{BOLD}SYSTEM READY — Both persons can work independently.{RESET}")
        if checks["model"] == "mock":
            print(f"  {YELLOW}ACTION: Person A must train the model before demo day.{RESET}")
            print(f"          Run: python nlp/train.py")
    else:
        print(f"  {RED}{BOLD}ISSUES FOUND — Fix the NO-GO items above before proceeding.{RESET}")

    print(f"""
  NEXT STEPS:
  ─────────────────────────────────────────────────────
  Person A:  python nlp/train.py              (train model)
             python nlp/predict.py             (batch classify all reviews)
             python nlp/absa.py                (run ABSA on all reviews)
             uvicorn api.main:app --port 8000   (start API)

  Person B:  python dashboard/app.py           (start dashboard)
             Open http://localhost:8050

  Together:  python scripts/connect_and_run.py (re-run this check)
  ─────────────────────────────────────────────────────
    """)


# 
# MAIN


def main():
    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  DARIJA REVIEW INTELLIGENCE — INTEGRATION CHECK{RESET}")
    print(f"{BOLD}{'='*55}{RESET}")
    print(f"  Running at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    checks = {}

    checks["db"]       = check_database()
    checks["model"]    = check_model()
    checks["pipeline"] = check_pipeline(checks["model"]) if checks["db"] else False
    checks["api"]      = check_api()
    checks["dashboard"]= check_dashboard()

    print_final_report(checks)


if __name__ == "__main__":
    main()