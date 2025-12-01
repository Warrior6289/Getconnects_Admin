#!/usr/bin/env bash
set -euo pipefail

# Use a temporary SQLite database to compare models with migrations
TMP_DB=$(mktemp)
export DATABASE_URL="sqlite:///$TMP_DB"

# Apply existing migrations
alembic upgrade head >/dev/null

# Capture output from an autogeneration run
output=$(alembic revision --autogenerate -m "_migration_check" 2>&1 || true)

# Check generated revision for real changes
new_file=$(git status --porcelain migrations/versions/*.py 2>/dev/null | awk '/^\?\?/ {print $2}')
if [ -n "$new_file" ]; then
  if grep -q "pass" "$new_file"; then
    rm -f "$new_file"
  else
    cat "$new_file"
    rm -f "$new_file"
    echo "$output"
    echo "\nERROR: Pending migrations detected. Run 'alembic revision --autogenerate' and commit the result." >&2
    exit 1
  fi
fi

# Remove temporary database
rm -f "$TMP_DB"

echo "$output"
