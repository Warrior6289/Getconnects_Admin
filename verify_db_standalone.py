import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load .env
load_dotenv()

database_url = os.getenv("DATABASE_URL")
print(f"Testing connection to: {database_url.split('@')[1] if '@' in database_url else 'UNKNOWN'}")

try:
    engine = create_engine(database_url)
    print("Attempting to connect to database...")
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1')).scalar()
        print(f"Connection Successful! Result: {result}")
except Exception as e:
    print(f"Connection Failed: {e}")
    sys.exit(1)
