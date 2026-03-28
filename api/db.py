import sqlite3

DB_PATH = "database/reviews.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    # This line makes rows return aas dictionaries
    # instead of plain tuples — much easier to work with
    conn.row_factory = sqlite3.Row
    return conn
