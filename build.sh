#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Initialize database schema from clean SQL file
python -c "
import os
from sqlalchemy import create_engine, text, inspect

# Get database URL
database_url = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

# Create engine
engine = create_engine(database_url)

# Check if database is empty (no tables exist)
inspector = inspect(engine)
existing_tables = inspector.get_table_names()

if not existing_tables:
    # Database is empty, create schema
    if database_url.startswith('postgresql'):
        # For PostgreSQL, execute schema.sql
        with open('schema.sql', 'r') as f:
            schema_sql = f.read()
        
        # Execute the entire SQL file
        with engine.begin() as conn:
            conn.execute(text(schema_sql))
        print('Database schema created from schema.sql')
    else:
        # For SQLite, use SQLAlchemy's create_all
        from getconnects_admin.models import Base
        Base.metadata.create_all(bind=engine)
        print('Database schema created using SQLAlchemy')
else:
    print(f'Database already has {len(existing_tables)} tables, skipping schema creation')
"
