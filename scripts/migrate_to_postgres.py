#!/usr/bin/env python3
import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_batch
import sys


SQLITE_DB = "data/results/ruvector.db"
POSTGRES_CONN = os.getenv('DATABASE_URL', 'postgresql://trader:secret123@localhost:5432/polymarket_trading')


def get_sqlite_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [row[0] for row in cursor.fetchall()]


def migrate_table(cursor, sqlite_conn, table_name):
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        return
    
    sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in sqlite_cursor.fetchall()]
    
    placeholders = ', '.join(['%s'] * len(columns))
    cols_str = ', '.join(columns)
    
    insert_sql = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"
    
    try:
        execute_batch(cursor, insert_sql, rows)
        print(f"  Migrated {len(rows)} rows from {table_name}")
    except Exception as e:
        print(f"  Error migrating {table_name}: {e}")


def main():
    if not os.path.exists(SQLITE_DB):
        print(f"SQLite database not found: {SQLITE_DB}")
        sys.exit(1)
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    
    try:
        pg_conn = psycopg2.connect(POSTGRES_CONN)
        pg_cursor = pg_conn.cursor()
        
        tables = get_sqlite_tables(sqlite_conn)
        print(f"Found {len(tables)} tables to migrate")
        
        for table in tables:
            print(f"Migrating table: {table}")
            migrate_table(pg_cursor, sqlite_conn, table)
        
        pg_conn.commit()
        print("Migration completed successfully!")
        
        pg_cursor.close()
        pg_conn.close()
        
    except psycopg2.OperationalError as e:
        print(f"PostgreSQL connection failed: {e}")
        print("Creating new PostgreSQL database...")
        
        base_conn = psycopg2.connect(
            POSTGRES_CONN.replace('polymarket_trading', 'postgres')
        )
        base_cursor = base_conn.cursor()
        base_cursor.execute("CREATE DATABASE polymarket_trading")
        base_cursor.close()
        base_conn.close()
        
        pg_conn = psycopg2.connect(POSTGRES_CONN)
        pg_cursor = pg_conn.cursor()
        
        for table in tables:
            print(f"Migrating table: {table}")
            migrate_table(pg_cursor, sqlite_conn, table)
        
        pg_conn.commit()
        print("Migration completed!")
        
    finally:
        sqlite_conn.close()


if __name__ == "__main__":
    main()