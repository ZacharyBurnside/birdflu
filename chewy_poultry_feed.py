import requests
import pandas as pd
import time
import sqlite3
from datetime import datetime

# Database details
DB_PATH = "/home/zburnside/birdflu/poultry_feed.db"  # Update with your PythonAnywhere path
TABLE_NAME = "poultry_feed_prices"

# Base URL (pagination setup)
BASE_URL = 'https://www.chewy.com/plp/api/search?catalogId=1004&count=36&from={from_val}&sort=byRelevance&groupId=951'

# Headers to mimic a real browser request
HEADERS = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    'x-dtpc': '11$41292898_26h65vHPCFWRSNTUDFBSMFPDKPCTTFVELFTMJM-0e0'
}

# Define pagination settings
products_per_page = 36  # Each page has 36 products
max_pages = 10           # Set how many pages to scrape

# Storage for collected data
all_products = []
scrape_date = datetime.now().strftime('%Y-%m-%d')  # Add a scrape date column

# Loop through pages
for page in range(max_pages):
    from_value = page * products_per_page  # Calculate pagination offset
    url = BASE_URL.format(from_val=from_value)

    print(f"Scraping page {page + 1}... {url}")  # Print progress

    response = requests.get(url, headers=HEADERS)

    # Check if response is OK
    if response.status_code != 200:
        print(f"Error fetching page {page + 1}: {response.status_code}")
        break  # Stop if we hit an error

    results = response.json()

    for product in results.get('products', []):
        all_products.append({
            'product_name': product.get('name'),  # Fixed column names (no spaces)
            'part_number': product.get('partNumber'),
            'rating_count': product.get('ratingCount'),
            'price': product.get('price'),
            'strike_price': product.get('strikePrice'),
            'strike_price_saving_pct': product.get('strikeSavingsPct'),
            'scrape_date': scrape_date
        })

    time.sleep(2)  # Add delay to avoid getting blocked

# Convert to DataFrame
df = pd.DataFrame(all_products)

# 🛠️ Store data in SQLite database
def save_to_db(df, db_path, table_name):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            part_number TEXT,
            rating_count INTEGER,
            price REAL,
            strike_price REAL,
            strike_price_saving_pct REAL,
            scrape_date TEXT
        )
    """)

    # Insert data (no deduplication)
    df.to_sql(table_name, conn, if_exists='append', index=False)

    conn.commit()
    conn.close()
    print(f"✅ Data successfully saved to {table_name} in {db_path}")

# Save DataFrame to database
save_to_db(df, DB_PATH, TABLE_NAME)
