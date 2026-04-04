import sqlite3

DB_PATH = "database/reviews.db"

POSITIVE_KW = [
    "زين","مليح","ممتاز","نعجبني","3jebni","bon","bien","super","top",
    "بهية","تستاهل","يستاهل","recommande","واو","رائع","نحب","زينة",
    "waw","mzian","pos_emoji","bni","bnin","délicieux","excellent","POS_EMOJI"
]
NEGATIVE_KW = [
    "خايب","ma3jbni","غالي","mauvais","nul","ما عجبنيش","cher","déçu",
    "خسارة","ما نشريش","خايبة","مش مليح","neg_emoji","khayeb","ghali",
    "périmé","expiré","makach","introuvable","عيب","NEG_EMOJI","مش","لا لا"
]

conn = sqlite3.connect(DB_PATH)
rows = conn.execute("SELECT id, text, text_normalized FROM reviews WHERE sentiment IS NULL").fetchall()

print(f"Found {len(rows)} unlabeled reviews")

updated = 0
for row_id, text, normalized in rows:
    t = (normalized or text or "").lower()
    pos = sum(1 for kw in POSITIVE_KW if kw.lower() in t)
    neg = sum(1 for kw in NEGATIVE_KW if kw.lower() in t)

    if pos > neg:
        label = "positive"
        conf = round(min(0.70 + pos * 0.05, 0.94), 2)
    elif neg > pos:
        label = "negative"
        conf = round(min(0.70 + neg * 0.05, 0.94), 2)
    else:
        label = "neutral"
        conf = 0.65

    conn.execute(
        "UPDATE reviews SET sentiment = ?, confidence = ? WHERE id = ?",
        (label, conf, row_id)
    )
    updated += 1

conn.commit()
conn.close()
print(f"Labeled {updated} reviews")