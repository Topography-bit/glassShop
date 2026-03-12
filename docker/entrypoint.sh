#!/bin/sh
set -e

until alembic upgrade head; do
  echo "Database is not ready yet, retrying migrations in 3 seconds..."
  sleep 3
done

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
