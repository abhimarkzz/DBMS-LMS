#!/bin/bash
# =============================================================================
# PostgreSQL Migration and Seed Runner
# =============================================================================
# Usage:
#   ./run_migrations.sh           — Run all migrations and seeds
#   ./run_migrations.sh migrate   — Run migrations only
#   ./run_migrations.sh seed      — Run seeds only
#   ./run_migrations.sh reset     — Drop all tables and re-run everything
# =============================================================================

set -e  # Exit immediately on error

# Load environment variables from .env if it exists
if [ -f "../../.env" ]; then
    export $(grep -v '^#' ../../.env | xargs)
fi

PGHOST="${POSTGRES_HOST:-localhost}"
PGPORT="${POSTGRES_PORT:-5432}"
PGDATABASE="${POSTGRES_DB:-lms_db}"
PGUSER="${POSTGRES_USER:-lms_user}"
PGPASSWORD="${POSTGRES_PASSWORD:-change_me_in_production}"

export PGPASSWORD

PSQL="psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE"

MIGRATIONS_DIR="$(dirname "$0")/migrations"
SEEDS_DIR="$(dirname "$0")/seeds"
VIEWS_DIR="$(dirname "$0")/views"
FUNCTIONS_DIR="$(dirname "$0")/functions"
TRIGGERS_DIR="$(dirname "$0")/triggers"

run_migrations() {
    echo "=== Running migrations ==="
    for f in "$MIGRATIONS_DIR"/[0-9]*.sql; do
        echo "  Applying: $(basename $f)"
        $PSQL -f "$f"
    done
    echo "=== Migrations complete ==="
}

run_views() {
    echo "=== Creating views ==="
    for f in "$VIEWS_DIR"/[0-9]*.sql; do
        echo "  Applying: $(basename $f)"
        $PSQL -f "$f"
    done
    echo "=== Views created ==="
}

run_functions() {
    echo "=== Creating functions ==="
    for f in "$FUNCTIONS_DIR"/[0-9]*.sql; do
        echo "  Applying: $(basename $f)"
        $PSQL -f "$f"
    done
    echo "=== Functions created ==="
}

run_triggers() {
    echo "=== Creating triggers ==="
    for f in "$TRIGGERS_DIR"/[0-9]*.sql; do
        echo "  Applying: $(basename $f)"
        $PSQL -f "$f"
    done
    echo "=== Triggers created ==="
}

run_seeds() {
    echo "=== Running seed data ==="
    for f in "$SEEDS_DIR"/[0-9]*.sql; do
        echo "  Seeding: $(basename $f)"
        $PSQL -f "$f"
    done
    echo "=== Seed data complete ==="
}

reset_database() {
    echo "!!! WARNING: This will drop all tables and re-run everything. !!!"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi
    echo "=== Resetting database ==="
    $PSQL -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO $PGUSER;"
    run_all
}

run_all() {
    run_migrations
    run_functions
    run_views
    run_triggers
    run_seeds
}

case "${1:-all}" in
    migrate)  run_migrations ;;
    seed)     run_seeds ;;
    views)    run_views ;;
    functions) run_functions ;;
    triggers) run_triggers ;;
    reset)    reset_database ;;
    all|*)    run_all ;;
esac
