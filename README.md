# EIA Data Coal Analysis

TODO: present findings here

## Fetch EIA Data and Create The DB

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
│   ├── run.py
│   ├── .env
│   ├── requirements.txt
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── file_utils.py
│   │   ├── year_validator.py
│   │   └── validator.py
│   └── db/
│       ├── __init__.py 
│       ├── connection.py
│       └── generation_capacities.py
│
└── data/
    ├── raw/
    └── eia.db
```
