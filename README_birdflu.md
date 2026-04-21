# Bird Flu Data Tracker

A multi-source data collection pipeline tracking the economic impact of the H5N1 avian flu outbreak through egg prices, poultry feed costs, chick hatchery inventory, and retail availability signals. Data is collected daily across multiple retailers and stored in SQLite and MySQL databases.

---

## What It Tracks

| Data Source | What It Measures |
|---|---|
| **Target** | Egg prices across 11 states (TX, CA, FL, NY, MN, IA, OH, CO, IL, GA, PA) |
| **Lidl** | Egg prices across all US Lidl store locations |
| **Urner Barry** | Wholesale egg price index (historical benchmark) |
| **Chewy** | Poultry feed prices — 360 products tracked |
| **Tractor Supply** | Chick availability — "sold in past X days" signals |
| **Hatchery (Ecwid)** | Live chick inventory, stock status, pricing, wholesale tiers |

---

## Why This Matters

The H5N1 bird flu outbreak devastated US poultry flocks, causing egg prices to spike to historic highs. This project tracks the downstream effects across the supply chain — from wholesale benchmark prices to what consumers actually pay at retail, and whether chick hatcheries can replenish flocks.

---

## Tech Stack

- **Python** — all scrapers and data pipelines
- **SQLite** — local storage for egg prices and feed data
- **MySQL** — hatchery inventory and Tractor Supply signals (PythonAnywhere)
- **Requests + BeautifulSoup** — HTTP scraping
- **Pandas** — data processing
- **Plotly Dash** — dashboard (birdflu.py)

---

## File Structure

```
birdflu/
├── birdflu.py                          # Dash dashboard
├── egg_price.py                        # Target egg prices (single store)
├── target_egg_states_spider.py         # Target egg prices (11 states)
├── lidl_egg_prices.py                  # Lidl egg prices (all US stores)
├── eggs.py                             # Urner Barry wholesale price scraper
├── chewy_poultry_feed.py               # Chewy poultry feed price tracker
├── tractor_supply.py                   # Tractor Supply product data
├── tractor_supply_sold_past_days_spider.py  # Chick "sold in X days" signals
├── hatchery_spider.py                  # Hatchery chick inventory (Ecwid API)
├── egg_prices.db                       # SQLite: Target + Urner Barry prices
├── lidl_all_store.db                   # SQLite: Lidl store prices
└── poultry_feed.db                     # SQLite: Chewy feed prices
```

---

## Data Collection

**Egg prices** are scraped daily by state from Target's RedSky API, capturing current price, regular price, and product name per store location.

**Lidl prices** are pulled from Lidl's mobile API across every US store, tracking current vs. regular price and stock status.

**Wholesale prices** come from Urner Barry's historical price series — the industry benchmark for shell egg pricing.

**Poultry feed** is scraped from Chewy across 360 products, tracking price, strike price, and discount percentage over time.

**Hatchery inventory** is pulled from a major US hatchery's Ecwid storefront daily — tracking which chick breeds are in stock, their prices, wholesale tier pricing, and warning stock levels.

**Tractor Supply signals** use the Taggstar social proof API to extract "X people bought this in the past Y days" signals for 43 chick-related SKUs — a proxy for consumer demand at retail farm stores.

---

## Running the Scrapers

```bash
# Egg prices by state (Target)
python target_egg_states_spider.py

# Lidl egg prices (all stores)
python lidl_egg_prices.py

# Wholesale benchmark
python eggs.py

# Poultry feed (Chewy)
python chewy_poultry_feed.py

# Hatchery inventory
python hatchery_spider.py

# Tractor Supply demand signals
python tractor_supply_sold_past_days_spider.py
```

All scrapers include retry logic and rate limiting delays to avoid being blocked.
