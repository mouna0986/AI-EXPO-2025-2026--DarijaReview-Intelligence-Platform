import sqlite3
import os

DB_PATH = "database/reviews.db"

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    with open("database/schema.sql", "r") as f:
        sql = f.read()
    
    cursor.executescript(sql)
    conn.commit()
    conn.close()
    print(" :3 Database created successfully at", DB_PATH)

if __name__ == "__main__":
    init_database()