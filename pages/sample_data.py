"""
Sample data for the ForexWatch.lk pages.

EVERYTHING HERE IS ILLUSTRATIVE, not real market data. It lets the templates render
with realistic-looking numbers while the real data pipeline is being built.

To go live: replace the functions below with queries against your own models
(e.g. ExchangeRate, FuelPrice, CommodityPrice, StockQuote) and keep the same return
shapes, so the views and templates do not need to change. Then set DEMO_DATA=False.
"""

import csv
import datetime as dt
import io
import random
from functools import lru_cache

# --- Exchange rates ---------------------------------------------------------

BANKS = [
    "Bank of Ceylon", "People's Bank", "Commercial Bank", "Hatton National Bank",
    "Sampath Bank", "Seylan Bank", "NDB Bank", "DFCC Bank", "Nations Trust Bank", "Union Bank",
]

# code, name, flag, base buy (LKR), base sell (LKR)
CURRENCIES = [
    ("USD", "US Dollar", "🇺🇸", 298.40, 307.10),
    ("EUR", "Euro", "🇪🇺", 321.00, 333.50),
    ("GBP", "British Pound", "🇬🇧", 376.00, 390.00),
    ("AUD", "Australian Dollar", "🇦🇺", 194.00, 203.50),
    ("SGD", "Singapore Dollar", "🇸🇬", 222.00, 232.00),
    ("INR", "Indian Rupee", "🇮🇳", 3.52, 3.72),
    ("AED", "UAE Dirham", "🇦🇪", 80.30, 84.20),
    ("JPY", "Japanese Yen (100)", "🇯🇵", 197.00, 206.00),
]
CURRENCY_CODES = [c[0] for c in CURRENCIES]


def _today():
    return dt.date.today()


def _pct_change(seed, spread=0.6):
    return round(random.Random(seed).uniform(-spread, spread), 2)


def currency_overview():
    """One row per currency: average bank buy/sell and day change."""
    rows = []
    for code, name, flag, buy, sell in CURRENCIES:
        rows.append({
            "code": code, "name": name, "flag": flag,
            "buy": buy, "sell": sell,
            "change": _pct_change(f"fx-{code}-{_today()}"),
        })
    return rows


def bank_rates(code):
    """Buy/sell rates for one currency across banks, with the best rates flagged."""
    base = next(c for c in CURRENCIES if c[0] == code)
    _, _, _, base_buy, base_sell = base
    rows = []
    for bank in BANKS:
        rng = random.Random(f"{bank}-{code}-{_today()}")
        buy = base_buy * (1 + rng.uniform(-0.006, 0.004))
        sell = base_sell * (1 + rng.uniform(-0.004, 0.006))
        decimals = 3 if base_sell < 10 else 2
        rows.append({
            "bank": bank,
            "buy": round(buy, decimals),
            "sell": round(max(sell, buy + 0.01), decimals),
            "change": _pct_change(f"{bank}-{code}-chg-{_today()}", 0.5),
        })
    best_buy = max(r["buy"] for r in rows)
    best_sell = min(r["sell"] for r in rows)
    for r in rows:
        r["spread"] = round(r["sell"] - r["buy"], 3 if base_sell < 10 else 2)
        r["best_buy"] = r["buy"] == best_buy
        r["best_sell"] = r["sell"] == best_sell
    return rows


# --- Commodities --------------------------------------------------------------

# name, category, unit, price (LKR)
_COMMODITIES = [
    ("Rice - Nadu", "Staples", "kg", 245), ("Rice - Samba", "Staples", "kg", 265),
    ("Sugar - White", "Staples", "kg", 255), ("Dhal", "Staples", "kg", 290),
    ("Wheat flour", "Staples", "kg", 215), ("Coconut", "Staples", "each", 110),
    ("Big onion", "Vegetables", "kg", 320), ("Potato", "Vegetables", "kg", 380),
    ("Carrot", "Vegetables", "kg", 420), ("Tomato", "Vegetables", "kg", 280),
    ("Green chilli", "Vegetables", "kg", 600), ("Pumpkin", "Vegetables", "kg", 160),
    ("Eggs (white)", "Meat & eggs", "each", 28), ("Chicken", "Meat & eggs", "kg", 1250),
    ("Fish - Balaya", "Meat & eggs", "kg", 780), ("Fresh milk", "Dairy & other", "litre", 270),
    ("Tea (loose)", "Dairy & other", "kg", 1400), ("Coconut oil", "Dairy & other", "litre", 650),
]


def commodities():
    rows = []
    for name, category, unit, price in _COMMODITIES:
        change = _pct_change(f"com-{name}-{_today()}", 3.0)
        rows.append({
            "name": name, "category": category, "unit": unit,
            "price": price, "change": change,
        })
    return rows


# --- Fuel ---------------------------------------------------------------------

# product, CPC price, Lanka IOC price, change in last revision (LKR)
_FUEL = [
    ("Petrol 92 Octane", 309, 313, -5),
    ("Petrol 95 Octane", 349, 353, 0),
    ("Auto Diesel", 289, 293, -3),
    ("Super Diesel", 327, 331, 0),
    ("Kerosene", 185, 188, -2),
]


def fuel_prices():
    return [
        {"product": p, "cpc": cpc, "ioc": ioc, "revision": rev}
        for p, cpc, ioc, rev in _FUEL
    ]


def fuel_revision_date():
    return _today().replace(day=1)


# --- Stock market -------------------------------------------------------------

_INDICES = [("ASPI", "All Share Price Index", 17850.12), ("S&P SL20", "S&P Sri Lanka 20", 5320.45)]

# symbol, name, price (LKR), volume
_STOCKS = [
    ("JKH.N0000", "John Keells Holdings", 21.60, 1_250_000),
    ("COMB.N0000", "Commercial Bank of Ceylon", 198.50, 410_000),
    ("HNB.N0000", "Hatton National Bank", 215.25, 160_000),
    ("SAMP.N0000", "Sampath Bank", 87.40, 520_000),
    ("LOLC.N0000", "LOLC Holdings", 402.00, 95_000),
    ("DIAL.N0000", "Dialog Axiata", 11.80, 3_400_000),
    ("CTC.N0000", "Ceylon Tobacco Company", 1120.00, 12_000),
    ("DIST.N0000", "Distilleries Company", 24.30, 780_000),
    ("EXPO.N0000", "Expolanka Holdings", 118.75, 230_000),
    ("HHL.N0000", "Hemas Holdings", 98.10, 140_000),
]


def indices():
    rows = []
    for symbol, name, value in _INDICES:
        rows.append({"symbol": symbol, "name": name, "value": value,
                     "change": _pct_change(f"idx-{symbol}-{_today()}", 1.2)})
    return rows


def stocks():
    rows = []
    for symbol, name, price, volume in _STOCKS:
        rows.append({"symbol": symbol, "name": name, "price": price, "volume": volume,
                     "change": _pct_change(f"stk-{symbol}-{_today()}", 3.5)})
    return rows


# --- History series (for analytics and dataset downloads) ----------------------

# key: label, unit, current value, daily volatility, decimals, group, step (monthly revisions)
SERIES = {
    "usd_lkr": {"label": "USD / LKR (bank average, sell)", "unit": "LKR", "current": 307.10, "vol": 0.0016, "decimals": 2, "group": "Exchange rates"},
    "eur_lkr": {"label": "EUR / LKR (bank average, sell)", "unit": "LKR", "current": 333.50, "vol": 0.0020, "decimals": 2, "group": "Exchange rates"},
    "gbp_lkr": {"label": "GBP / LKR (bank average, sell)", "unit": "LKR", "current": 390.00, "vol": 0.0022, "decimals": 2, "group": "Exchange rates"},
    "petrol_92": {"label": "Petrol 92 (CPC)", "unit": "LKR/L", "current": 309, "vol": 0, "decimals": 0, "group": "Fuel", "step": True},
    "auto_diesel": {"label": "Auto Diesel (CPC)", "unit": "LKR/L", "current": 289, "vol": 0, "decimals": 0, "group": "Fuel", "step": True},
    "rice_nadu": {"label": "Rice - Nadu", "unit": "LKR/kg", "current": 245, "vol": 0.004, "decimals": 0, "group": "Commodities"},
    "sugar": {"label": "Sugar - White", "unit": "LKR/kg", "current": 255, "vol": 0.003, "decimals": 0, "group": "Commodities"},
    "aspi": {"label": "ASPI (CSE All Share)", "unit": "points", "current": 17850.12, "vol": 0.007, "decimals": 2, "group": "Stock market"},
    "sp_sl20": {"label": "S&P SL20", "unit": "points", "current": 5320.45, "vol": 0.008, "decimals": 2, "group": "Stock market"},
}
HISTORY_DAYS = 365


@lru_cache(maxsize=None)
def _history_for_day(key, day_iso):
    cfg = SERIES[key]
    rng = random.Random(key)
    n = HISTORY_DAYS
    values = [0.0] * n
    v = cfg["current"]
    # Walk backwards from today's value so the last point always equals "current".
    for i in range(n - 1, -1, -1):
        values[i] = v
        if cfg.get("step"):
            if i % 30 == 0:
                v = v / (1 + rng.uniform(-0.05, 0.05))
        else:
            v = v / (1 + rng.gauss(0, cfg["vol"]))
    today = dt.date.fromisoformat(day_iso)
    dates = [(today - dt.timedelta(days=n - 1 - i)).isoformat() for i in range(n)]
    return dates, [round(x, cfg["decimals"]) for x in values]


def history(key):
    """(dates, values) for one series, oldest first, ending today."""
    return _history_for_day(key, _today().isoformat())


def all_series():
    """Everything the analytics page needs, ready for json_script."""
    out = {}
    for key, cfg in SERIES.items():
        dates, values = history(key)
        out[key] = {
            "label": cfg["label"], "unit": cfg["unit"], "group": cfg["group"],
            "decimals": cfg["decimals"], "dates": dates, "values": values,
        }
    return out


def snapshot():
    """Four headline numbers for the landing page."""
    picks = [("usd_lkr", "USD / LKR", "rates"), ("petrol_92", "Petrol 92", "fuel"),
             ("aspi", "ASPI", "stocks"), ("rice_nadu", "Rice (Nadu)", "commodities")]
    cards = []
    for key, label, url_name in picks:
        _, values = history(key)
        prev, last = values[-2], values[-1]
        change = round((last / prev - 1) * 100, 2) if prev else 0
        cards.append({"label": label, "value": last, "unit": SERIES[key]["unit"],
                      "decimals": SERIES[key]["decimals"], "change": change, "url_name": url_name})
    return cards


# --- Datasets -------------------------------------------------------------------

DATASETS = [
    {"slug": "fx-daily", "title": "Daily exchange rates (LKR)",
     "description": "Daily bank-average USD, EUR and GBP rates against the Sri Lankan rupee.",
     "series": ["usd_lkr", "eur_lkr", "gbp_lkr"], "frequency": "Daily", "tags": ["Currency", "Banks"]},
    {"slug": "fuel-prices", "title": "Fuel prices (CPC)",
     "description": "Petrol 92 and Auto Diesel retail prices with every price revision.",
     "series": ["petrol_92", "auto_diesel"], "frequency": "Daily (changes on revision)", "tags": ["Fuel", "Energy"]},
    {"slug": "commodity-prices", "title": "Essential goods prices",
     "description": "Daily market prices for staple goods such as rice and sugar.",
     "series": ["rice_nadu", "sugar"], "frequency": "Daily", "tags": ["Commodities", "Cost of living"]},
    {"slug": "stock-indices", "title": "CSE stock indices",
     "description": "Daily closing values of the ASPI and S&P SL20 indices.",
     "series": ["aspi", "sp_sl20"], "frequency": "Daily", "tags": ["Stocks", "CSE"]},
]


def get_dataset(slug):
    return next((d for d in DATASETS if d["slug"] == slug), None)


def dataset_csv(dataset):
    """Build the CSV text for a dataset (date column plus one column per series)."""
    columns = {key: history(key) for key in dataset["series"]}
    dates = columns[dataset["series"][0]][0]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["date"] + dataset["series"])
    for i, date in enumerate(dates):
        writer.writerow([date] + [columns[key][1][i] for key in dataset["series"]])
    return buffer.getvalue()
