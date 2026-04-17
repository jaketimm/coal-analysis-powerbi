#!/usr/bin/env python3
"""
Fetch EIA State Electricity Profiles — Generating Capacities data
(V2 API), cache the raw JSON to data/, and create the SQLite DB.

All energy values are in megawatts (MW).
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from db.generation_capacities import insert_yearly_generation_capacities, insert_yearly_coal_generation_capacities
from db.connection import table_exists
from utils.file_utils import data_is_fresh, load_json_cache, save_json_cache
from utils.logger import get_logger
from utils.validator import detect_schema_drift


logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(".env")

# Config 
API_KEY = os.getenv("EIA_API_KEY")
BASE_URL = "https://api.eia.gov/v2"
ROUTE = "electricity/state-electricity-profiles/capability/data"

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "eia.db"
JSON_FILE = DATA_DIR / "raw" / "eia_generation_capacities.json"

FIELDS = [
    "capability",
]

START_YEAR = "1990"
END_YEAR = "2024"
BATCH_SIZE = 5000


# Expected JSON fields, used for schema validation
EXPECTED_FIELDS = {
    "period",
    "stateId",
    "stateDescription",
    "producertypeid",
    "producerTypeDescription",
    "energysourceid",
    "energySourceDescription",
    "capability",
    "capability-units",
}


# API helpers 
def build_params(offset: int = 0) -> dict:
    """Flatten nested params into the query-string format the V2 API expects."""
    params = {
        "api_key": API_KEY,
        "frequency": "annual",
        "start": START_YEAR,
        "end": END_YEAR,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": offset,
        "length": BATCH_SIZE,
        # filter to totals only (sum for all sectors, not broken down into utilities, independent producers)
        "facets[producertypeid][]": "TOT",  
    }
    for i, field in enumerate(FIELDS):
        params[f"data[{i}]"] = field
    return params


def fetch_all_records() -> list[dict]:
    """Page through the API until every record has been collected."""
    url = f"{BASE_URL}/{ROUTE}/"
    all_records: list[dict] = []
    offset = 0

    while True:
        params = build_params(offset)
        logger.info("Requesting EIA data at offset=%d …", offset)

        try:
            resp = requests.get(url, params=params, timeout=60)
            resp.raise_for_status()
        except requests.exceptions.Timeout as exc:
            logger.error("EIA API request timed out at offset=%d: %s", offset, exc)
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error("EIA API connection error at offset=%d: %s", offset, exc)
            raise
        except requests.exceptions.HTTPError as exc:
            logger.error(
                "EIA API HTTP error at offset=%d (status %s): %s",
                offset,
                exc.response.status_code if exc.response is not None else "unknown",
                exc,
            )
            raise
        except Exception as exc:
            logger.error("Unexpected error calling EIA API at offset=%d: %s", offset, exc)
            raise

        body = resp.json()
        api_resp = body.get("response", {})

        if not api_resp:
            logger.info("Unexpected response shape from EIA API: %s", str(body)[:500])
            raise ValueError("Unexpected EIA API response shape — no 'response' key.")

        records = api_resp.get("data", [])
        total = int(api_resp.get("total", 0))
        all_records.extend(records)

        logger.info(
            "Fetched %d rows from EIA API (running total: %d / %d).",
            len(records),
            len(all_records),
            total,
        )

        if not records or len(all_records) >= total:
            break

        offset += BATCH_SIZE

    return all_records


def fetch_raw_eia_capacities_data() -> None:
    """Fetch yearly generation capacities data from the EIA API and create the generation_capacities table."""

    if not API_KEY:
        logger.error("EIA_API_KEY is not set. Add it to your .env file.")
        raise RuntimeError("EIA_API_KEY is not set.")

    # If the cached JSON is fresh, check if the DB table exists and has data. 
    # If not, rebuild from the cached JSON.
    if data_is_fresh(JSON_FILE):
        if not (DB_PATH).exists() or not table_exists("yearly_generation_capacities"):
            logger.warning("Data is fresh but table or DB is missing — rebuilding from cached JSON.")
            records = load_json_cache(JSON_FILE)
            row_count = insert_yearly_generation_capacities(records)
            logger.info("Inserted %d rows into yearly_generation_capacities.", row_count)
        return

    logger.info(
        "Fetching EIA generation capacities data (%s–%s) …", START_YEAR, END_YEAR
    )
    records = fetch_all_records()

    if not records:
        logger.info("No records returned — double-check your API key and date range.")
        raise ValueError("EIA API returned no records.")
 
    # Validate schema before saving or inserting data into DB
    data_is_valid = detect_schema_drift(EXPECTED_FIELDS, records)

    if data_is_valid:
        save_json_cache(JSON_FILE, records, FIELDS, units="megawatts")

        row_count = insert_yearly_generation_capacities(records)
        logger.info("Inserted %d rows into yearly_generation_capacities.", row_count)

    else:
        logger.info("Schema drift detected, skipped updating the DB")
        raise RuntimeError("EIA data varied from expected schema")


def create_coal_generation_capacities_table() -> None:
    """Create the yearly_coal_generation_capacities table by filtering for coal records."""
    
    row_count = insert_yearly_coal_generation_capacities()
    logger.info("Inserted %d rows into yearly_coal_generation_capacities.", row_count)


# main process
def main():

    fetch_raw_eia_capacities_data()
    create_coal_generation_capacities_table()


if __name__ == "__main__":
    main()