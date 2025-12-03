import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from getconnects_admin.models import engine
    from sqlalchemy import text
    
    print("Attempting to connect to database...")
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1')).scalar()
        print(f"Connection Successful! Result: {result}")
except Exception as e:
    print(f"Connection Failed: {e}")
    sys.exit(1)
