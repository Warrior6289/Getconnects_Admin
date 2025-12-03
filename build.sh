#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Run migrations - use 'heads' (plural) to handle multiple migration heads
alembic upgrade heads
