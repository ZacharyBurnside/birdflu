import os
import re
from datetime import datetime
from typing import Optional
import requests
import pandas as pd
from bs4 import BeautifulSoup
import mysql.connector

# --- Configuration ---
MYSQL_CONFIG = {
    'host':     os.getenv('DB_HOST', 'zburnside.mysql.pythonanywhere-services.com'),
    'user':     os.getenv('DB_USER', 'zburnside'),
    'password': os.getenv('DB_PASS', 'Bearsocks24!'),
    'database': os.getenv('DB_NAME', 'zburnside$golfnow'),
}

TAGGSTAR_URL = (
    'https://api.us-east-2.taggstar.com/api/v2/'
    'key/tractorsupplycom/category/visit?detail=true'
)
TAGGSTAR_PAYLOAD = {
    "visitor": {
        "sessionId": "b5a258db-50a3-11f0-8832-cbb4ec33af90",
        "id":         "b5a258db-50a3-11f0-8832-cbb4ec33af90",
    },
    "category": "-",
    "products": [
        "124145499","135974199","187448499","137965999","162013699","162014099",
        "162015999","147491199","124145799","162012999","124162099","162015699",
        "124166599","135971399","126253899","130532699","124162699","130535799",
        "124168099","134853599","134853699","170039899","130536099","124163299",
        "135975099","124163599","147491799","124164199","130536199","129248699",
        "135973299","162014799","124165699","135450699","124164799","135972199",
        "124166299","130534799","135973099","147492099","125263899","135976199",
        "130536299"
    ],
    "client":     {"expectedSiteConfigVersion": "40/4", "deviceType": "mobile"},
    "experience": {"id": "treatment-v1"},
}

def extract_days(html: str) -> Optional[int]:
    if not isinstance(html, str):
        return None
    text = BeautifulSoup(html, 'html.parser').get_text()
    m = re.search(r'(\d+)\s+days', text)
    return int(m.group(1)) if m else None

def get_connection() -> mysql.connector.MySQLConnection:
    return mysql.connector.connect(**MYSQL_CONFIG)

def fetch_and_transform() -> pd.DataFrame:
    resp = requests.post(TAGGSTAR_URL, json=TAGGSTAR_PAYLOAD)
    resp.raise_for_status()

    df = pd.json_normalize(resp.json()['socialProof'])
    df_exploded = df.explode('messages').reset_index(drop=True)
    msgs = pd.json_normalize(df_exploded['messages'])
    result = pd.concat([df_exploded.drop(columns=['messages']), msgs], axis=1)

    result['days'] = result['message'].apply(extract_days)
    result['collection_date'] = datetime.now().date()
    result = result.rename(columns={'product.id': 'product_id'})

    # fill NaNs
    result['product_id']      = result['product_id'].fillna('')
    result['category']        = result['category'].fillna('')
    result['code']            = result['code'].fillna('')
    result['message']         = result['message'].fillna('')
    result['days']            = result['days'].fillna(0).astype(int)
    result['collection_date'] = result['collection_date']

    return result

def upsert_to_mysql(df: pd.DataFrame) -> int:
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tractor_supply_days (
      product_id      VARCHAR(50),
      category        VARCHAR(100),
      code            VARCHAR(100),
      message         TEXT,
      days            INT,
      collection_date DATE,
      PRIMARY KEY (collection_date)
    );
    """)

    insert_sql = """
    INSERT INTO tractor_supply_days
      (product_id, category, code, message, days, collection_date)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      category = VALUES(category),
      message  = VALUES(message),
      days     = VALUES(days);
    """

    data = [
        (
            row.product_id,
            row.category,
            row.code,
            row.message,
            row.days,
            row.collection_date
        )
        for row in df.itertuples(index=False)
    ]

    cursor.executemany(insert_sql, data)
    affected = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    return affected

def main():
    df = fetch_and_transform()
    count = upsert_to_mysql(df)
    print(f"Inserted {count} records into tractor_supply_days")

if __name__ == "__main__":
    main()
