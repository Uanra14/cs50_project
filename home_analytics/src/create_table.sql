CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    neighbourhood TEXT,
    city TEXT,
    postcode TEXT,
    housenumber TEXT,
    province TEXT,
    country TEXT,
    wonen INTEGER,
    slaapkamers INTEGER,
    energielabel TEXT,
    price INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

