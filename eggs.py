import requests
import pandas as pd
from bs4 import BeautifulSoup
import sqlite3

url = 'https://www.urnerbarry.com/history/4850'
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
rows = soup.find_all('tr')

data = []
for row in rows:
    cols = row.find_all('td')
    if len(cols) == 3:
        date = cols[1].text.strip()  # Extract date
        price = cols[2].text.strip()  # Extract price
        data.append({'Date': date, 'Price': price})

df = pd.DataFrame(data)
df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y', errors='coerce')
df['Price'] = pd.to_numeric(df['Price'], errors='coerce')

db_path = 'urnerbarry_prices.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS price_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    price REAL
)
''')
conn.commit()

def save_to_database(dataframe):
    for _, row in dataframe.iterrows():
        cursor.execute('''
        INSERT INTO price_data (date, price)
        VALUES (?, ?)
        ''', (row['Date'].strftime('%Y-%m-%d') if pd.notnull(row['Date']) else None, row['Price']))
    conn.commit()

save_to_database(df)

query_result = pd.read_sql_query('SELECT * FROM price_data', conn)

conn.close()
