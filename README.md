# EIA Data Coal Analysis

Analysis was performed using the `coal_generation_capacities.csv` file. This file is created automatically by running `run.py`.

TODO: present findings here

## Fetch EIA Data, Create The DB, & Export Coal Data to CSV

Register for a free EIA API key at eia.gov/opendata, then create a .env file at python/.env:

```text
EIA_API_KEY="your_key_here"
```

```bash

cd python

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

python run.py
```

### Project Structure

```text
coal-analysis-powerbi/
├── python/
│   ├── run.py    # Main process
│   ├── .env
│   ├── requirements.txt
│   ├── scripts/
│   │   └── export_for_powerbi.py
│   ├── utils/
│   │   ├── logger.py
│   │   ├── file_utils.py
│   │   ├── year_validator.py
│   │   └── validator.py
│   └── db/
│       ├── connection.py
│       └── generation_capacities.py
│
└── data/
    ├── raw/         # Unprocessed JSON file
    ├── processed/   # Exported CSV data
    └── eia.db
```
