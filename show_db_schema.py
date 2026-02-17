"""
Show Database Schema - Display the SQLite database schema in a readable format
"""
import sqlite3
import argparse
from typing import List, Dict


def get_table_schema(conn: sqlite3.Connection, table_name: str) -> List[Dict]:
    """Get schema information for a specific table"""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = []
    for row in cursor.fetchall():
        columns.append({
            'cid': row[0],
            'name': row[1],
            'type': row[2],
            'notnull': row[3],
            'default_value': row[4],
            'pk': row[5]
        })
    return columns


def get_indexes(conn: sqlite3.Connection, table_name: str) -> List[Dict]:
    """Get index information for a specific table"""
    cursor = conn.execute(f"PRAGMA index_list({table_name})")
    indexes = []
    for row in cursor.fetchall():
        index_name = row[1]
        unique = row[2]
        # Get index columns
        index_info = conn.execute(f"PRAGMA index_info({index_name})").fetchall()
        columns = [col[2] for col in index_info]
        indexes.append({
            'name': index_name,
            'unique': unique,
            'columns': columns
        })
    return indexes


def get_foreign_keys(conn: sqlite3.Connection, table_name: str) -> List[Dict]:
    """Get foreign key information for a specific table"""
    cursor = conn.execute(f"PRAGMA foreign_key_list({table_name})")
    fks = []
    for row in cursor.fetchall():
        fks.append({
            'id': row[0],
            'seq': row[1],
            'table': row[2],
            'from': row[3],
            'to': row[4],
            'on_update': row[5],
            'on_delete': row[6],
            'match': row[7]
        })
    return fks


def format_schema(conn: sqlite3.Connection, table_name: str) -> str:
    """Format schema for a table"""
    output = []
    output.append(f"\n{'=' * 80}")
    output.append(f"TABLE: {table_name}")
    output.append(f"{'=' * 80}\n")
    
    # Get columns
    columns = get_table_schema(conn, table_name)
    output.append("COLUMNS:")
    output.append("-" * 80)
    output.append(f"{'Name':<25} {'Type':<20} {'Nullable':<10} {'Default':<15} {'PK'}")
    output.append("-" * 80)
    
    for col in columns:
        nullable = "NO" if col['notnull'] else "YES"
        default = str(col['default_value']) if col['default_value'] is not None else "NULL"
        pk = "✓" if col['pk'] else ""
        output.append(f"{col['name']:<25} {col['type']:<20} {nullable:<10} {default:<15} {pk}")
    
    # Get indexes
    indexes = get_indexes(conn, table_name)
    if indexes:
        output.append(f"\nINDEXES:")
        output.append("-" * 80)
        for idx in indexes:
            unique_str = "UNIQUE" if idx['unique'] else "NON-UNIQUE"
            cols_str = ", ".join(idx['columns'])
            output.append(f"  {idx['name']} ({unique_str}) ON: {cols_str}")
    
    # Get foreign keys
    fks = get_foreign_keys(conn, table_name)
    if fks:
        output.append(f"\nFOREIGN KEYS:")
        output.append("-" * 80)
        for fk in fks:
            output.append(f"  {fk['from']} → {fk['table']}.{fk['to']}")
            if fk['on_delete']:
                output.append(f"    ON DELETE: {fk['on_delete']}")
            if fk['on_update']:
                output.append(f"    ON UPDATE: {fk['on_update']}")
    
    return "\n".join(output)


def show_all_tables(conn: sqlite3.Connection):
    """Show all tables in the database"""
    cursor = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    return tables


def main():
    parser = argparse.ArgumentParser(description="Show database schema")
    parser.add_argument("--db", type=str, default="benchmark.db", help="Database path")
    parser.add_argument("--table", type=str, help="Show schema for specific table only")
    parser.add_argument("--sql", action="store_true", help="Show CREATE TABLE SQL statements")
    
    args = parser.parse_args()
    
    conn = sqlite3.connect(args.db)
    
    print("=" * 80)
    print("DATABASE SCHEMA")
    print("=" * 80)
    print(f"Database: {args.db}")
    print()
    
    if args.sql:
        # Show CREATE TABLE statements
        cursor = conn.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        for table_name, sql in cursor.fetchall():
            print(f"\n{'=' * 80}")
            print(f"CREATE TABLE: {table_name}")
            print(f"{'=' * 80}\n")
            print(sql)
            print(";")
    else:
        # Show formatted schema
        tables = show_all_tables(conn)
        
        if args.table:
            if args.table in tables:
                print(format_schema(conn, args.table))
            else:
                print(f"❌ Table '{args.table}' not found!")
                print(f"Available tables: {', '.join(tables)}")
        else:
            # Show all tables
            for table in tables:
                print(format_schema(conn, table))
    
    # Show table statistics
    print(f"\n{'=' * 80}")
    print("TABLE STATISTICS")
    print(f"{'=' * 80}\n")
    tables = show_all_tables(conn)
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<30} {count:>10} rows")
    
    conn.close()
    print(f"\n{'=' * 80}")


if __name__ == "__main__":
    main()
