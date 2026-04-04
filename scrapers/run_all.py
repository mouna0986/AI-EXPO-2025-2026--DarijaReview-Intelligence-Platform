""""
running this file lets you colllect all data in one go
it tries the live scraper, then import the data in this CSV file
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Ensure the current directory is in path

from scrapers.facebook_scraper import import_from_csv, scrape_facebook_comments

print("=" * 50)
print("darija review intelligence - data collection :3")
print("=" * 50)
#1
print("\n step1📊 importing from CSV...")
import_from_csv("data/labeled/reviews.csv")

#2
print("\n step2facebook scraper...")
print("skip with ctrl+c if you don't wanna run it now")

try :
    from scrapers.facebook_scraper import scrape_facebook
    scrape_facebook_comments()
except KeyboardInterrupt:
    print("\n Skipping Facebook scraper...")
except Exception as e:
    print(f"\n Facebook scraper error: {e}")
    print("it's okey :3, CSV data is already imprted")
    
print("\n All done! Data collection complete.")
print(" refresh your dashboard to see the updates")
    
      