import pandas as pd
import requests
import sqlite3
import time
import random
from datetime import datetime
import os

# ✅ Store URLs (Confirmed working)
store_urls = {
    "TX": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&category=5xszi&channel=WEB&count=24&default_purchasability_filter=true&include_dmc_dmr=true&include_sponsored=true&new_search=false&offset=0&page=%2Fc%2F5xszi&platform=desktop&pricing_store_id=758&spellcheck=true&store_ids=758&visitor_id=0194A9588F3A0201A35EF9A207BCA58D&zip=76006",
    "CA": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&category=5xszi&channel=WEB&count=24&default_purchasability_filter=true&include_dmc_dmr=true&include_sponsored=true&new_search=false&offset=0&page=%2Fc%2F5xszi&platform=desktop&pricing_store_id=3406&spellcheck=true&store_ids=3406&visitor_id=0194A9588F3A0201A35EF9A207BCA58D&zip=10021",
    "FL": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&category=5xszi&channel=WEB&count=24&default_purchasability_filter=true&include_dmc_dmr=true&include_sponsored=true&new_search=false&offset=0&page=%2Fc%2F5xszi&platform=desktop&pricing_store_id=649&spellcheck=true&store_ids=649&visitor_id=0194A9588F3A0201A35EF9A207BCA58D&zip=32789",
    "NY": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&category=5xszi&channel=WEB&count=24&default_purchasability_filter=true&include_dmc_dmr=true&include_sponsored=true&new_search=false&offset=0&page=%2Fc%2F5xszi&platform=desktop&pricing_store_id=3321&spellcheck=true&store_ids=3321&visitor_id=0193F46024750201A92C8AB94FBE0D76&zip=10028",
    "MN": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&category=5xszi&channel=WEB&count=24&default_purchasability_filter=true&include_dmc_dmr=true&include_sponsored=true&new_search=false&offset=0&page=%2Fc%2F5xszi&platform=desktop&pricing_store_id=68&spellcheck=true&store_ids=68&visitor_id=0194A9588F3A0201A35EF9A207BCA58D&zip=55106",
    "IA": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&category=5xszi&channel=WEB&count=24&default_purchasability_filter=true&include_dmc_dmr=true&include_sponsored=true&new_search=false&offset=0&page=%2Fc%2F5xszi&platform=desktop&pricing_store_id=803&spellcheck=true&store_ids=803&visitor_id=0194A9588F3A0201A35EF9A207BCA58D&zip=50001",
    "OH": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&category=5xszi&channel=WEB&count=24&default_purchasability_filter=true&include_dmc_dmr=true&include_sponsored=true&new_search=false&offset=0&page=%2Fc%2F5xszi&platform=desktop&pricing_store_id=1236&spellcheck=true&store_ids=1236&visitor_id=0194A9588F3A0201A35EF9A207BCA58D&zip=43003",
    "CO": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&category=5xszi&channel=WEB&count=24&default_purchasability_filter=true&include_dmc_dmr=true&include_sponsored=true&new_search=false&offset=0&page=%2Fc%2F5xszi&platform=desktop&pricing_store_id=1769&spellcheck=true&store_ids=1769&visitor_id=0194A9588F3A0201A35EF9A207BCA58D&zip=80303",
    "IL": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&category=5xszi&channel=WEB&count=24&default_purchasability_filter=true&include_dmc_dmr=true&include_sponsored=true&new_search=false&offset=0&page=%2Fc%2F5xszi&platform=desktop&pricing_store_id=841&spellcheck=true&store_ids=841&visitor_id=0194A9588F3A0201A35EF9A207BCA58D&zip=60629",
    "GA": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&category=5xszi&channel=WEB&count=24&default_purchasability_filter=true&include_dmc_dmr=true&include_sponsored=true&new_search=false&offset=0&page=%2Fc%2F5xszi&platform=desktop&pricing_store_id=1197&spellcheck=true&store_ids=1197&visitor_id=0194A9588F3A0201A35EF9A207BCA58D&zip=30326",
    "PA": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&category=5xszi&channel=WEB&count=24&default_purchasability_filter=true&include_dmc_dmr=true&include_sponsored=true&new_search=false&offset=0&page=%2Fc%2F5xszi&platform=desktop&pricing_store_id=2757&spellcheck=true&store_ids=2757&visitor_id=0194A9588F3A0201A35EF9A207BCA58D&zip=15206"
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
}

# ✅ Fetch Data
def fetch_data(url):
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        return response.json()
    print(f"❌ Failed to fetch data for {url} (Status {response.status_code})")
    return None

# ✅ Scrape data
def scrape_target_egg_prices():
    all_data = []
    today_date = datetime.now().strftime('%Y-%m-%d')

    for state, url in store_urls.items():
        print(f"🔍 Fetching data for {state}...")

        results = fetch_data(url)
        if not results or 'data' not in results or 'search' not in results['data'] or 'products' not in results['data']['search']:
            print(f"⚠️ No valid data for {state}, skipping.")
            continue

        for product in results['data']['search']['products']:
            tcin = product.get('tcin', 'Unknown')
            title = product.get('title', 'Unknown Product')
            current_price = product.get('price', {}).get('current_retail', None)
            regular_price = product.get('price', {}).get('regular_price', None)
            currency = product.get('price', {}).get('currency', 'USD')

            if current_price is not None:
                all_data.append({
                    'tcin': tcin,
                    'product_name': title,
                    'current_price': current_price,
                    'regular_price': regular_price,
                    'currency': currency,
                    'state': state,
                    'date': today_date
                })

        time.sleep(random.uniform(1, 3))

    return pd.DataFrame(all_data)

def save_to_database(df):
    if df.empty:
        print("⚠️ No data to save.")
        return

    db_path = "/home/zburnside/birdflu/egg_prices.db"
    table_name = 'target_eggs_all'

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ✅ Create the table if it doesn't exist (Without Dropping Existing Data)
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tcin TEXT,
        product_name TEXT,
        current_price REAL,
        regular_price REAL,
        currency TEXT,
        state TEXT,
        date TEXT
    )
    ''')

    # ✅ Always append new data (No deduplication check)
    df.to_sql(table_name, conn, if_exists='append', index=False)

    conn.commit()
    conn.close()
    print(f"✅ Successfully saved {len(df)} records to the database.")

# ✅ Run Scraper & Save to Database
if __name__ == "__main__":
    print("🚀 Scraping egg prices from Target across multiple states...")
    df = scrape_target_egg_prices()

    if not df.empty:
        print(f"📌 Saving {len(df)} records to the database...")
        save_to_database(df)
    else:
        print("⚠️ No egg price data to save.")
