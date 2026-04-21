import requests
import pandas as pd
import sqlite3
import time
import random
from datetime import datetime

# ✅ Step 1: Fetch Store IDs and States
store_data = requests.get('https://mobileapi.lidl.com/v1/stores?').json().get('results', [])

df_stores = pd.DataFrame({
    'Store ID': [store['id'] for store in store_data],
    'State': [store['address']['state'] for store in store_data]
})

print(f"✅ Fetched {len(df_stores)} stores.")

# ✅ Step 2: Scrape Products for Each Store
base_url = "https://mobileapi.lidl.com/v1/categories/OCI2000107/products"
product_data = []
for store_id, state in zip(df_stores['Store ID'], df_stores['State']):
    url = f"{base_url}?numResults=100&offset=0&storeId={store_id}"  # Adjust offset if needed
    response = requests.get(url)
    products = response.json().get('results', [])

    if response.status_code == 200:
        for product in products:
            price_info = product.get('priceInformation', {}) or {}

            # ✅ Extract `currentPrice` correctly
            current_price_info = price_info.get('currentPrice', {}) or {}
            current_price_data = current_price_info.get('currentPrice', {}) or {}

            # ✅ Extract `regularPrice` correctly
            regular_price_info = price_info.get('regularPrice', {}) or {}
            regular_price_data = regular_price_info.get('currentPrice', {}) or {}

            product_data.append({
                'date_scraped': datetime.now().strftime('%Y-%m-%d'),
                'store_id': store_id,
                'state': state,
                'product_id': product.get('itemId', None),
                'name': product.get('name', None),
                'gtin': product.get('gtin', None),
                'description': product.get('longDescription', None),
                'current_price': current_price_data.get('value', None),  # ✅ Correct extraction
                'regular_price': regular_price_data.get('value', None),  # ✅ Correct extraction
                'base_price_text': current_price_data.get('basePriceText', None),  # ✅ Extract base price per unit
                'stock_status': product.get('stockStatusCode', None),
            })

    else:
        print(f"❌ Status Code: {response.status_code} for Store: {store_id}")

    print(f"✅ Finished processing Store: {store_id}")

    # ✅ Add delay to avoid rate-limiting
    time.sleep(random.uniform(1, 3))

df_products = pd.DataFrame(product_data)
print(f"✅ Scraped {len(df_products)} products.")

# ✅ Step 3: Save Data to SQLite Database
db_name = '/home/zburnside/birdflu/lidl_all_store.db'
db_table = 'lidl_egg_prices'

conn = sqlite3.connect(db_name)
cursor = conn.cursor()

# ✅ Create Table if Not Exists (Allows duplicates for daily tracking)
cursor.execute(f'''
CREATE TABLE IF NOT EXISTS {db_table} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_scraped TEXT,
    store_id TEXT,
    product_id TEXT,
    name TEXT,
    gtin TEXT,
    description TEXT,
    current_price REAL,
    regular_price REAL,
    currency TEXT,
    base_price_text TEXT,
    stock_status TEXT
)
''')


# ✅ Save all records (DUPLICATES ALLOWED for daily price tracking)
df_products.to_sql(db_table, conn, if_exists='append', index=False, method=None)

conn.commit()
conn.close()

print(f"✅ Saved {len(df_products)} records to {db_name} in table {db_table}.")
