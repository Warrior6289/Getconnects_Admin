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
        # For PostgreSQL, execute schema.sql statement by statement
        with open('schema.sql', 'r') as f:
            schema_sql = f.read()
        
        # Split SQL into individual statements and execute them
        # Remove comments and split by semicolons
        statements = []
        current_statement = []
        in_comment = False
        
        for line in schema_sql.split('\n'):
            line = line.strip()
            # Skip empty lines and full-line comments
            if not line or line.startswith('--'):
                continue
            # Handle block comments
            if '/*' in line:
                in_comment = True
                continue
            if '*/' in line:
                in_comment = False
                continue
            if in_comment:
                continue
            
            current_statement.append(line)
            if line.endswith(';'):
                statement = ' '.join(current_statement)
                if statement.strip() and statement.strip() != ';':
                    statements.append(statement)
                current_statement = []
        
        # Execute each statement
        with engine.begin() as conn:
            for statement in statements:
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    # Ignore errors for IF NOT EXISTS
                    error_msg = str(e).lower()
                    if 'already exists' not in error_msg and 'duplicate' not in error_msg:
                        print(f'Warning: {e}')
                        raise
        print('Database schema created from schema.sql')
    else:
        # For SQLite, use SQLAlchemy's create_all
        from getconnects_admin.models import Base
        Base.metadata.create_all(bind=engine)
        print('Database schema created using SQLAlchemy')
else:
    print(f'Database already has {len(existing_tables)} tables, skipping schema creation')
"
