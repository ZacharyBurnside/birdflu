import requests
import sqlite3
from datetime import datetime

# SQLite Database Setup
db_path = 'egg_prices.db'  # Define the path to the SQLite database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create a table to store egg price data if it doesn't already exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS egg_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tcin TEXT,
    price REAL,
    date TEXT
)
''')
conn.commit()

# Function to scrape egg price data from Target
def scrape_target_egg_prices():
    url = 'https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&category=5xszi&channel=WEB&count=24&default_purchasability_filter=true&include_dmc_dmr=true&include_sponsored=true&new_search=false&offset=0&page=%2Fc%2F5xszi&platform=desktop&pricing_store_id=1897&spellcheck=true&store_ids=1897%2C1006%2C3339%2C3320%2C2007&useragent=Mozilla%2F5.0+%28Macintosh%3B+Intel+Mac+OS+X+10_15_7%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Chrome%2F131.0.0.0+Safari%2F537.36&visitor_id=0193F46024750201A92C8AB94FBE0D76&zip=20746'

    header = {'user-agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'}

    response = requests.get(url, headers = header)
    if response.status_code != 200:
        print(f"Failed to fetch data: {response.status_code}")
        return []

    results = response.json()

    # Extract relevant data
    all_parsed_data = []
    if 'data' in results and 'search' in results['data'] and 'products' in results['data']['search']:
        for product in results['data']['search']['products']:
            tcin = product.get('tcin', 'Unknown')
            current_retail = product.get('price', {}).get('current_retail', None)
            todays_date = datetime.now().strftime('%Y-%m-%d')

            if current_retail:  # Only save data with a valid price
                parsed_data = {
                    'TCIN': tcin,
                    'Current Retail': current_retail,
                    'Date': todays_date
                }
                all_parsed_data.append(parsed_data)
    return all_parsed_data

# Function to save data to the database
def save_to_database(data):
    for record in data:
        cursor.execute('''
        INSERT INTO egg_prices (tcin, price, date)
        VALUES (?, ?, ?)
        ''', (record['TCIN'], record['Current Retail'], record['Date']))
    conn.commit()

# Main Execution
if __name__ == "__main__":
    print("Scraping egg prices from Target...")
    egg_prices = scrape_target_egg_prices()
    if egg_prices:
        print(f"Saving {len(egg_prices)} records to the database.")
        save_to_database(egg_prices)
        print("Data saved successfully!")
    else:
        print("No egg price data to save.")

# Close the database connection
conn.close()





