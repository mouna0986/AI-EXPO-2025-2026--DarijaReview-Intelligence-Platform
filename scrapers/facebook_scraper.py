import time
import json
import sqlite3
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

DB_PATH = "database/reviews.db"



RAMY_FACEBOOK_URL = "https://www.facebook.com/ramy.jus"
MAX_POSTS = 5
MAX_COMMENTS_PER_POST = 20


def setup_driver():
   
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1280,800")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    # Remove the 'navigator.webdriver' flag that sites use to detect bots
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def save_to_db(reviews: list):
    """Save scraped reviews to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    saved = 0
    for review in reviews:
        try:
            cursor.execute("""
                INSERT INTO reviews (platform, text, engagement_score, review_date)
                VALUES (?, ?, ?, ?)
            """, (
                review["platform"],
                review["text"],
                review.get("engagement_score", 0),
                review.get("date", datetime.now().strftime("%Y-%m-%d"))
            ))
            saved += 1
        except Exception as e:
            print(f"  ⚠️  Could not save review: {e}")

    conn.commit()
    conn.close()
    print(f"✅ Saved {saved} reviews to database")


def save_to_json(reviews: list, filename: str = "data/raw/facebook_raw.json"):
    """Also save raw scraped data to JSON as backup."""
    os.makedirs("data/raw", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)
    print(f"📁 Raw data saved to {filename}")


def scroll_down(driver, times=3):
    """Scroll down the page to load more content."""
    for _ in range(times):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)


def scrape_facebook_comments():
  
    print("🚀 Starting Facebook scraper...")
    print("⚠️  Facebook will ask you to log in.")
    print("    Log in manually in the browser window, then the scraper continues.\n")

    driver = setup_driver()
    reviews = []

    try:
        # Open Ramy's Facebook page
        driver.get(RAMY_FACEBOOK_URL)
        print(f"📖 Opened: {RAMY_FACEBOOK_URL}")

        # Wait for the page to load
        time.sleep(4)

       
        print("⏳ Waiting for page to load (log in if prompted)...")
        try:
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
        except Exception:
            print("  Could not find articles, trying to continue anyway...")


        scroll_down(driver, times=5)
        time.sleep(2)

    
        print("🔍 Looking for posts...")
        post_links = []
        try:
            links = driver.find_elements(By.XPATH, "//a[contains(@href, '/posts/') or contains(@href, '/videos/') or contains(@href, '/photos/')]")
            post_links = list(set([
                link.get_attribute("href")
                for link in links
                if link.get_attribute("href")
            ]))[:MAX_POSTS]
        except Exception as e:
            print(f"  Could not find post links: {e}")

        print(f"  Found {len(post_links)} posts to scan")

        # Visit each post and collect comments
        for i, post_url in enumerate(post_links):
            print(f"\n📄 Post {i+1}/{len(post_links)}: {post_url[:60]}...")

            try:
                driver.get(post_url)
                time.sleep(3)
                scroll_down(driver, times=3)

               
                try:
                    more_buttons = driver.find_elements(
                        By.XPATH,
                        "//span[contains(text(), 'View') or contains(text(), 'comments')]"
                    )
                    for btn in more_buttons[:3]:
                        try:
                            btn.click()
                            time.sleep(1)
                        except Exception:
                            pass
                except Exception:
                    pass

               
                comment_elements = driver.find_elements(
                    By.XPATH,
                    "//div[@data-testid='comment']//div[@dir='auto'] | //ul//li//div[@dir='auto']"
                )

                post_comments = 0
                for element in comment_elements:
                    text = element.text.strip()

                   
                    if 5 < len(text) < 500:
                        reviews.append({
                            "platform": "facebook",
                            "text": text,
                            "engagement_score": 0,
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "source_url": post_url
                        })
                        post_comments += 1

                    if post_comments >= MAX_COMMENTS_PER_POST:
                        break

                print(f"  ✅ Collected {post_comments} comments")

            except Exception as e:
                print(f"  ❌ Error on this post: {e}")
                continue

    except Exception as e:
        print(f"❌ Scraper crashed: {e}")

    finally:
        driver.quit()

    print(f"\n📊 Total collected: {len(reviews)} reviews")

    if reviews:
        save_to_json(reviews)
        save_to_db(reviews)
    else:
        print("⚠️  No reviews collected. Use the CSV importer instead.")

    return reviews


if __name__ == "__main__":
    scrape_facebook_comments()