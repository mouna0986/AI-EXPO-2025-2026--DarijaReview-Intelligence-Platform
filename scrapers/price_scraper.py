import requests
import sqlite3
import json
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup

DB_PATH = "database/reviews.db"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-DZ,fr;q=0.9,ar;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


SEARCH_TERMS = [
    "jus ramy",
    "ramy jus",
    "jus de fruit algérie",
    "nectar algérie",
]

COMPETITOR_BRANDS = [
    "ramy", "tchina", "candia", "soummam",
    "ifrui", "hamoud", "tropical", "touja"
]


#HELPER FONCTIONS

def clean_price(price_text: str) -> float:
    
    if not price_text:
        return 0.0
    
    cleaned = ""
    for char in price_text:
        if char.isdigit() or char in ".,":
            cleaned += char
    
    cleaned = cleaned.replace(",", "").replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def detect_brand(product_name: str) -> str:
    
    name_lower = product_name.lower()
    for brand in COMPETITOR_BRANDS:
        if brand in name_lower:
            return brand.capitalize()
    return "Unknown"


def save_prices_to_db(prices: list):
    """Save collected prices to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    saved = 0
    for item in prices:
        try:
            cursor.execute("""
                INSERT INTO prices (brand, product, price_dzd, source)
                VALUES (?, ?, ?, ?)
            """, (
                item["brand"],
                item["product"],
                item["price_dzd"],
                item["source"]
            ))
            saved += 1
        except Exception as e:
            print(f"  Could not save price: {e}")

    conn.commit()
    conn.close()
    print(f"Saved {saved} prices to database")


def save_prices_to_json(prices: list):
    """Backup prices to JSON file."""
    os.makedirs("data/raw", exist_ok=True)
    filepath = "data/raw/prices_raw.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(prices, f, ensure_ascii=False, indent=2)
    print(f"📁 Raw prices saved to {filepath}")


#JUMIA
def scrape_jumia(search_term: str) -> list:
   
    prices = []

    # Build the search URL
    # Jumia's search URL format: /catalog/?q=your+search+term
    query = search_term.replace(" ", "+")
    url = f"https://www.jumia.com.dz/catalog/?q={query}"

    print(f"  🔍 Searching Jumia: '{search_term}'")

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)

        if response.status_code != 200:
            print(f"  ⚠️  Jumia returned status {response.status_code}")
            return prices

        soup = BeautifulSoup(response.text, "lxml")

        # Jumia product cards are inside <article> tags with class 'prd'
        product_cards = soup.find_all("article", class_="prd")

        print(f"  Found {len(product_cards)} products")

        for card in product_cards[:10]:  
            try:
                # Product name
                name_el = card.find("h3", class_="name")
                if not name_el:
                    name_el = card.find("h3")
                name = name_el.text.strip() if name_el else "Unknown Product"

                # Price
                price_el = card.find("div", class_="prc")
                if not price_el:
                    price_el = card.find("span", class_="prc")
                price_text = price_el.text.strip() if price_el else "0"
                price = clean_price(price_text)

                
                if price > 0:
                    brand = detect_brand(name)
                    prices.append({
                        "brand": brand,
                        "product": name[:100],  
                        "price_dzd": price,
                        "source": "jumia"
                    })

            except Exception as e:
                continue

        # Be polite :3 — wait between requests
        time.sleep(2)

    except requests.exceptions.Timeout:
        print("  ⚠️  Jumia request timed out")
    except requests.exceptions.ConnectionError:
        print("  ⚠️  Could not connect to Jumia")
    except Exception as e:
        print(f"  ⚠️  Jumia scraper error: {e}")

    return prices


# OUEDKNISS

def scrape_ouedkniss(search_term: str) -> list:
  
    prices = []

    query = search_term.replace(" ", "+")
    url = f"https://www.ouedkniss.com/search?q={query}&category=alimentation"

    print(f"  🔍 Searching Ouedkniss: '{search_term}'")

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)

        if response.status_code != 200:
            print(f"  ⚠️  Ouedkniss returned status {response.status_code}")
            return prices

        soup = BeautifulSoup(response.text, "lxml")

        # Ouedkniss listing cards
        # we look for price patterns
        listings = soup.find_all("div", class_=lambda x: x and "announcement" in x.lower())

        if not listings:
            # Try alternative selectors
            listings = soup.find_all("article")

        print(f"  Found {len(listings)} listings")

        for listing in listings[:10]:
            try:
                # Try to find product title
                title_el = listing.find(["h2", "h3", "a"])
                name = title_el.text.strip() if title_el else "Unknown"

                # Try to find price — look for 'DA' currency indicator
                price_el = listing.find(
                    string=lambda text: text and "DA" in text and any(c.isdigit() for c in text)
                )
                if not price_el:
                    price_el = listing.find(["span", "div"],
                                            class_=lambda x: x and "price" in str(x).lower())

                price_text = price_el if isinstance(price_el, str) else (
                    price_el.text if price_el else "0"
                )
                price = clean_price(price_text)

                if price > 0 and len(name) > 3:
                    brand = detect_brand(name)
                    prices.append({
                        "brand": brand,
                        "product": name[:100],
                        "price_dzd": price,
                        "source": "ouedkniss"
                    })

            except Exception:
                continue

        time.sleep(2)

    except requests.exceptions.Timeout:
        print("  ⚠️  Ouedkniss request timed out")
    except requests.exceptions.ConnectionError:
        print("  ⚠️  Could not connect to Ouedkniss")
    except Exception as e:
        print(f"  ⚠️  Ouedkniss scraper error: {e}")

    return prices



def import_prices_from_csv(filepath: str = "data/labeled/prices.csv"):
    """
    Import prices from a manually filled CSV.
    Use this when scrapers fail or you want
    to guarantee specific products are in the data.
    """
    import pandas as pd

    if not os.path.exists(filepath):
        print(f"  ⚠️  No price CSV found at {filepath}")
        print("      Creating template...")
        create_price_csv_template(filepath)
        return []

    try:
        df = pd.read_csv(filepath, encoding="utf-8-sig")
        prices = []

        for _, row in df.iterrows():
            prices.append({
                "brand": str(row.get("brand", "Unknown")).strip(),
                "product": str(row.get("product", "Unknown")).strip(),
                "price_dzd": float(row.get("price_dzd", 0)),
                "source": str(row.get("source", "manual")).strip()
            })

        print(f"  ✅ Loaded {len(prices)} prices from CSV")
        return prices

    except Exception as e:
        print(f"  ❌ Could not read price CSV: {e}")
        return []


def create_price_csv_template(filepath: str):
    """Creates a template CSV for manual price entry."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    template = """brand,product,price_dzd,source
Ramy,Jus Mangue 1L,180,jumia
Ramy,Jus Orange 1L,170,jumia
Ramy,Jus Pomme 1L,170,jumia
Ramy,Lait 1L,145,supermarche
Ramy,Jus Multifruits 1L,175,jumia
Competitor A,Jus Mangue 1L,155,jumia
Competitor A,Jus Orange 1L,150,jumia
Competitor B,Jus Mangue 1L,165,ouedkniss
Competitor B,Lait 1L,135,supermarche
Competitor C,Jus Orange 1L,160,jumia
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"  📋 Template created at {filepath}")
    print("     Fill it with real prices from your phone, then run again.")




def run_price_collection():
    print("=" * 50)
    print("PRICE INTELLIGENCE COLLECTOR")
    print("=" * 50)

    all_prices = []

    #Importing from manual CSV 
    print("\n📋 Step 1: Loading manual prices from CSV...")
    csv_prices = import_prices_from_csv()
    all_prices.extend(csv_prices)

    #  Jumia 
    print("\n🛒 Step 2: Scraping Jumia Algeria...")
    for term in SEARCH_TERMS[:2]:  
        jumia_prices = scrape_jumia(term)
        all_prices.extend(jumia_prices)
        time.sleep(3)  # Wait between searches

    # ouedkniss
    print("\n🛒 Step 3: Scraping Ouedkniss...")
    for term in SEARCH_TERMS[:2]:
        ouedkniss_prices = scrape_ouedkniss(term)
        all_prices.extend(ouedkniss_prices)
        time.sleep(3)

    #  Deduplicate 
    print(f"\n🔄 Deduplicating {len(all_prices)} collected prices...")
    seen = set()
    unique_prices = []
    for p in all_prices:
        key = f"{p['brand']}_{p['product']}_{p['source']}"
        if key not in seen:
            seen.add(key)
            unique_prices.append(p)

    print(f"  ✅ {len(unique_prices)} unique prices after deduplication")

    # sauvgarde
    if unique_prices:
        save_prices_to_json(unique_prices)
        save_prices_to_db(unique_prices)
    else:
        print("\n⚠️  No prices collected.")
        print("    Fill data/labeled/prices.csv manually and run again.")

    return unique_prices


if __name__ == "__main__":
    run_price_collection()