"""
Generation capacities database read/write operations
─────────────────────────
insert_yearly_generation_capacities(records)
insert_yearly_coal_generation_capacities()
fetch_coal_generation_capacities_data()
"""

import sqlite3
from pathlib import Path

from db.connection import get_connection
from utils.logger import get_logger
from utils.year_validator import validate_period
logger = get_logger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "eia.db"


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


def insert_yearly_coal_generation_capacities() -> int:
    """Create the yearly_coal_generation_capacities table if it doesn't exist."""
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS yearly_coal_generation_capacities (
                period                      INTEGER NOT NULL,
                state                       TEXT    NOT NULL,
                state_description           TEXT    NOT NULL,
                energy_source_id        TEXT,
                capability        REAL,
                PRIMARY KEY (period, state, energy_source_id)
            )
        """)
        conn.commit()
        conn.close()
    except sqlite3.Error as exc:
        logger.error("SQLite error in create_yearly_coal_generation_capacities_table: %s", exc)
        raise
    except Exception as exc:
        logger.error("Unexpected error in create_yearly_coal_generation_capacities_table: %s", exc)
        raise


    # Fetch all coal capacities data from yearly_generation_capacities
    query = "SELECT period, state, state_description, energy_source_id, capability FROM yearly_generation_capacities WHERE energy_source_id = 'COL'"

    try:
        conn = get_connection()
        rows = conn.execute(query).fetchall()
        conn.close()
    except sqlite3.Error as exc:
        logger.error("SQLite error when fetching coal data: %s", exc)
        raise
    except Exception as exc:
        logger.error("Unexpected error when fetching coal data: %s", exc)
        raise

    # Insert coal data into yearly_coal_generation_capacities
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT OR IGNORE INTO yearly_coal_generation_capacities
                (period, state, state_description, energy_source_id, capability)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(row[0], row[1], row[2], 'COL', row[4]) for row in rows],
        )
        conn.commit()
        inserted = conn.total_changes
        conn.close()

        return inserted
    
    except sqlite3.Error as exc:
        logger.error("SQLite error inserting coal data: %s", exc)
        raise
    except Exception as exc:
        logger.error("Unexpected error inserting coal data: %s", exc)
        raise


def fetch_coal_generation_capacities_data() -> list[sqlite3.Row]:
    """Fetch coal generation capacities data with yearly changes and total context for analysis."""

    # Fetch all coal capacities data from yearly_generation_capacities, with yearly coal capability changes and total capability for context
    query = """WITH totals AS (
    SELECT state, period, ROUND(SUM(capability), 2) AS total_capability
    FROM yearly_generation_capacities
    GROUP BY state, period)

    SELECT coal.period, coal.state, coal.state_description, coal.capability AS coal_capability,
    ROUND(coal.capability - LAG(coal.capability) OVER (PARTITION BY coal.state ORDER BY coal.period), 2) AS coal_capability_change,
    ROUND(1.0 * coal.capability / totals.total_capability, 3) AS coal_percent_share,
    totals.total_capability
    FROM yearly_coal_generation_capacities coal
    JOIN totals
    ON coal.state = totals.state AND coal.period = totals.period
    ORDER BY coal.period;"""

    try:
        conn = get_connection()
        rows = conn.execute(query).fetchall()
        conn.close()

        return rows
    
    except sqlite3.Error as exc:
        logger.error("SQLite error reading coal data: %s", exc)
        raise
    except Exception as exc:
        logger.error("Unexpected error reading coal data: %s", exc)
        raise
