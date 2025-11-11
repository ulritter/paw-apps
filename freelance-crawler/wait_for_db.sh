#!/bin/bash
# Wait for PostgreSQL to be ready

set -e

host="${DATABASE_URL#*@}"
host="${host%%/*}"
host="${host%%:*}"

until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$host" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "Postgres is up - executing command"
