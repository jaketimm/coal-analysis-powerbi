"""
Fetch EIA State Electricity Profiles — Generating Capacities data.
All energy values are in megawatts (MW).
"""

import requests

from db.generation_capacities import (
    insert_yearly_generation_capacities,
    insert_yearly_coal_generation_capacities
)
from db.connection import table_exists
from utils.file_utils import data_is_fresh, load_json_cache, save_json_cache
from utils.logger import get_logger
from utils.validator import detect_schema_drift
from config import API_KEY, BASE_URL, DATA_DIR, DB_PATH, BATCH_SIZE, REQUEST_TIMEOUT


logger = get_logger(__name__)

# Endpoint-specific configuration
ROUTE = "electricity/state-electricity-profiles/capability/data"
JSON_FILE = DATA_DIR / "raw" / "eia_generation_capacities.json"
FIELDS = ["capability"]
START_YEAR = "1990"
END_YEAR = "2024"

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


def _build_params(offset: int = 0) -> dict:
    """Build query parameters for the API request."""
    params = {
        "api_key": API_KEY,
        "frequency": "annual",
        "start": START_YEAR,
        "end": END_YEAR,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": offset,
        "length": BATCH_SIZE,
        "facets[producertypeid][]": "TOT",
    }
    for i, field in enumerate(FIELDS):
        params[f"data[{i}]"] = field
    return params


def _fetch_all_records() -> list[dict]:
    """Page through the API until all records are collected."""
    url = f"{BASE_URL}/{ROUTE}/"
    all_records: list[dict] = []
    offset = 0

    while True:
        params = _build_params(offset)
        logger.info("Requesting EIA data at offset=%d …", offset)

        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
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


def _get_or_fetch_data() -> list[dict]:
    """Load from cache if fresh, otherwise fetch from API."""
    if data_is_fresh(JSON_FILE):
        logger.info("Using cached data from %s", JSON_FILE)
        return load_json_cache(JSON_FILE)
    
    logger.info("Fetching EIA generation capacities data (%s–%s) …", START_YEAR, END_YEAR)
    records = _fetch_all_records()
    
    if not records:
        logger.error("No records returned — double-check your API key and date range.")
        raise ValueError("EIA API returned no records.")
    
    return records


def _validate_schema(records: list[dict]) -> None:
    """Validate data schema and raise if drift detected."""
    if not detect_schema_drift(EXPECTED_FIELDS, records):
        logger.error("Schema drift detected in EIA data")
        raise RuntimeError("EIA data varied from expected schema")


def _insert_to_db(records: list[dict]) -> None:
    """Save data to cache and insert into database."""
    save_json_cache(JSON_FILE, records, FIELDS, units="megawatts")
    
    row_count = insert_yearly_generation_capacities(records)
    logger.info("Inserted %d rows into yearly_generation_capacities.", row_count)


def fetch_raw_eia_capacities_data() -> None:
    """Fetch yearly generation capacities data from the EIA API and populate the database."""
    
    if not API_KEY:
        logger.error("EIA_API_KEY is not set. Add it to your .env file.")
        raise RuntimeError("EIA_API_KEY is not set.")

    # Check if we can skip the entire process
    if data_is_fresh(JSON_FILE):
        if DB_PATH.exists() and table_exists("yearly_generation_capacities"):
            logger.info("Data is fresh and DB table exists — skipping fetch.")
            return
        
        logger.warning("Data is fresh but table or DB is missing — rebuilding from cache.")
        records = load_json_cache(JSON_FILE)
        row_count = insert_yearly_generation_capacities(records)
        logger.info("Inserted %d rows into yearly_generation_capacities.", row_count)
        return

    # Fetch, validate, and store new data
    records = _get_or_fetch_data()
    _validate_schema(records)
    _insert_to_db(records)


def create_coal_generation_capacities_table() -> None:
    """Create the yearly_coal_generation_capacities table by filtering for coal records."""
    row_count = insert_yearly_coal_generation_capacities()
    logger.info("Inserted %d rows into yearly_coal_generation_capacities.", row_count)
    