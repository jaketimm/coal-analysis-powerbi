"""
Generation capacities database read/write operations
─────────────────────────
insert_yearly_generation_capacities(records)
get_generation_capacities_state_list
"""

import sqlite3
from pathlib import Path

from db.connection import get_connection
from utils.logger import get_logger
from utils.year_validator import validate_period
logger = get_logger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "eia.db"


# yearly_generation_capacities table — writes 
def insert_yearly_generation_capacities(records: list[dict]) -> int:
    """
    Create and update the yearly_generation_capacities table.
    Returns the number of rows inserted.

    All energy values are in megawatts (MW).
    """

    def _to_float(val):
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS yearly_generation_capacities (
                period                      INTEGER NOT NULL,
                state                       TEXT    NOT NULL,
                state_description           TEXT    NOT NULL,
                energy_source_id        TEXT,
                energy_source_description TEXT,
                capability        REAL,
                PRIMARY KEY (period, state, energy_source_id)
            )
        """)

        # Validate periods before processing
        valid_records = []
        for r in records:
            try:
                validate_period(r["period"])
                valid_records.append(r)
            except ValueError as e:
                logger.error("Skipping record with invalid period: %s", e)
                continue

        rows = [
            (
                int(r["period"]),
                r["stateId"],
                r["stateDescription"],
                r["energysourceid"],
                r["energySourceDescription"],
                _to_float(r.get("capability")),
            )
            for r in valid_records
        ]

        # Only add rows with a new PRIMARY KEY (period, state, energy_source_id)
        cur.executemany(
            """
            INSERT OR IGNORE INTO yearly_generation_capacities
                (period, state, state_description,
                 energy_source_id, energy_source_description,
                 capability)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        conn.commit()
        inserted = conn.total_changes
        conn.close()
        return inserted

    except sqlite3.Error as exc:
        logger.error("SQLite error in insert_yearly_generation_capacities: %s", exc)
        raise
    except Exception as exc:
        logger.error("Unexpected error in insert_yearly_generation_capacities: %s", exc)
        raise


# yearly_generation_capacities table — reads
def get_generation_capacities_state_list() -> list[sqlite3.Row]:
    """
    Return all state codes and descriptions available for generation capacities.
    Used to populate the state filter dropdown.
    """
    try:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT DISTINCT state, state_description
            FROM yearly_generation_capacities
            WHERE state NOT IN ('US', 'DC')
            ORDER BY state_description ASC
            """
        ).fetchall()
        conn.close()
        return rows
    except sqlite3.Error as exc:
        logger.error("SQLite error in get_generation_capacities_state_list: %s", exc)
        raise
    except Exception as exc:
        logger.error("Unexpected error in get_generation_capacities_state_list: %s", exc)
        raise


