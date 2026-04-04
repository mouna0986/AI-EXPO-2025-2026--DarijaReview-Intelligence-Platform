import sqlite3

conn = sqlite3.connect('database/reviews.db')
conn.execute("UPDATE reviews SET platform = TRIM(platform)")
conn.execute("UPDATE reviews SET sentiment = TRIM(sentiment)")
conn.commit()
conn.close()
print('✅ Data cleaned')