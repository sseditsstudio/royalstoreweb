import sqlite3

def init_db():
    conn = sqlite3.connect("royal.db")
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact TEXT UNIQUE NOT NULL, -- email or phone number
            role TEXT DEFAULT 'user',
            verified BOOLEAN DEFAULT 0,
            otp TEXT
        )
    ''')

    # Products table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            price REAL NOT NULL,
            available BOOLEAN DEFAULT 1,
            image_url TEXT
        )
    ''')

    # Search History
    c.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            search_query TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Orders
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            delivery_type TEXT,
            address TEXT,
            distance REAL,
            delivery_charge REAL,
            subtotal REAL,
            total REAL,
            unique_code TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Banners
    c.execute('''
        CREATE TABLE IF NOT EXISTS banners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            image_url TEXT,
            active BOOLEAN DEFAULT 1
        )
    ''')

    conn.commit()

    # Create admin user if not exists
    c.execute("SELECT id FROM users WHERE contact = 'siddharths1003@gmail.com'")
    admin = c.fetchone()
    if not admin:
        c.execute("INSERT INTO users (contact, role, verified) VALUES ('siddharths1003@gmail.com', 'admin', 1)")
    
    # Prepopulate some products
    products = [
        ("Apple", 150.0, "https://loremflickr.com/400/300/apple,fruit"),
        ("Milk", 60.0, "https://loremflickr.com/400/300/milk"),
        ("Bread", 40.0, "https://loremflickr.com/400/300/bread"),
        ("Eggs", 80.0, "https://loremflickr.com/400/300/eggs"),
    ]
    for p in products:
        c.execute("INSERT OR IGNORE INTO products (name, price, image_url) VALUES (?, ?, ?)", p)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
