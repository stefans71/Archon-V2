#!/usr/bin/env python3
"""
Archon Database Initialization Script

This script initializes the Archon database schema on an external Supabase instance.
It executes SQL via docker exec into the supabase-db container.

Usage:
    python scripts/init_db.py

Prerequisites:
    - Supabase must be running at ~/supabase/docker
    - The supabase-db container must be accessible
"""

import subprocess
import sys
from pathlib import Path


def get_migration_sql_path() -> Path:
    """Get the path to the complete_setup.sql migration file."""
    migration_path = Path(__file__).parent.parent / "migration" / "complete_setup.sql"

    if not migration_path.exists():
        print(f"ERROR: Migration file not found at {migration_path}")
        sys.exit(1)

    return migration_path


def execute_migration(sql_path: Path) -> bool:
    """Execute SQL using docker exec into supabase-db container."""
    print(f"Executing migration via docker exec into supabase-db...")

    try:
        # Use docker exec to run psql inside the supabase-db container
        result = subprocess.run(
            [
                "docker", "exec", "-i", "supabase-db",
                "psql", "-U", "postgres", "-d", "postgres", "-f", "-"
            ],
            stdin=open(sql_path, "r"),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Print output
        if result.stdout:
            # Filter to show only important messages
            for line in result.stdout.split('\n'):
                if 'ERROR' in line or 'CREATE' in line or 'INSERT' in line:
                    print(line)

        if result.stderr:
            for line in result.stderr.split('\n'):
                if line.strip():
                    print(f"STDERR: {line}")

        # Check for critical errors (not just "already exists")
        if result.returncode != 0:
            # Check if all errors are just "already exists" type
            critical_errors = [
                line for line in result.stdout.split('\n')
                if 'ERROR' in line and 'already exists' not in line and 'duplicate key' not in line
            ]
            if critical_errors:
                print("\nCritical errors found:")
                for err in critical_errors:
                    print(f"  {err}")
                return False

        return True

    except subprocess.TimeoutExpired:
        print("ERROR: Migration timed out after 5 minutes")
        return False
    except FileNotFoundError:
        print("ERROR: Docker not found. Make sure Docker is installed and running.")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False


def main():
    print("=" * 60)
    print("Archon Database Initialization")
    print("=" * 60)
    print()
    print("Target: supabase-db container (PostgreSQL)")
    print()

    # Get migration file path
    sql_path = get_migration_sql_path()
    print(f"Migration file: {sql_path}")
    print()

    # Execute the migration
    success = execute_migration(sql_path)

    if success:
        print()
        print("=" * 60)
        print("Database initialization complete!")
        print("=" * 60)
        print()
        print("Note: 'already exists' messages are expected if schema was")
        print("      previously initialized. The migration is idempotent.")
        print()
        print("Next steps:")
        print("  1. Start Archon with: docker compose up -d")
        print("  2. Access the UI at: http://localhost:3737")
        print("  3. Configure your OpenAI API key in Settings")
        print()
    else:
        print()
        print("=" * 60)
        print("Database initialization FAILED")
        print("=" * 60)
        print()
        print("Troubleshooting:")
        print("  1. Ensure Supabase is running: docker ps | grep supabase")
        print("  2. Check supabase-db container: docker logs supabase-db")
        print("  3. Verify Docker permissions")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
