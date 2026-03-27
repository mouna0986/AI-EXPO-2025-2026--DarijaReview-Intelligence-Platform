CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    text TEXT NOT NULL,
    text_normalized TEXT,
    sentiment TEXT,
    confidence REAL,
    engagement_score INTEGER DEFAULT 0,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    review_date TEXT
);

CREATE TABLE IF NOT EXISTS aspects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER REFERENCES reviews(id),
    aspect TEXT NOT NULL,
    polarity TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    product TEXT,
    price_dzd REAL,
    source TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);