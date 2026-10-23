#!/bin/bash

export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export POSTGRES_DB=test
export POSTGRES_HOST=127.0.0.1
export PGUSER=postgres

export PGPASSWORD=$POSTGRES_PASSWORD


function sql() {
  echo $1 \
    | psql --host $POSTGRES_HOST --user $POSTGRES_USER postgres
}

sql "DROP DATABASE test" || true
sql "CREATE DATABASE test"

python -m alembic -q upgrade head > /tmp/alembic_err 2> /tmp/alembic_err \
  || (cat /tmp/alembic_err; exit 1)

python -m unittest discover -v
