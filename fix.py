import sqlite3

conn = sqlite3.connect('database/reviews.db')
conn.execute("UPDATE reviews SET sentiment = TRIM(sentiment) WHERE sentiment != TRIM(sentiment)")
conn.execute("UPDATE reviews SET platform = TRIM(platform) WHERE platform != TRIM(platform)")
conn.commit()
conn.close()
print('Done — whitespace cleaned')