"""
View entire database - all tables and data
"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect("benchmark.db")
conn.row_factory = sqlite3.Row

print("=" * 80)
print("DATABASE VIEWER - ALL TABLES")
print("=" * 80)
print()

# Get all tables
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()

for table_info in tables:
    table_name = table_info['name']
    print(f"\n{'=' * 80}")
    print(f"TABLE: {table_name}")
    print(f"{'=' * 80}")
    
    # Get schema
    schema = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    print("\nSchema:")
    print("-" * 80)
    for col in schema:
        print(f"  {col['name']:20} {col['type']:15} {'NOT NULL' if col['notnull'] else 'NULL'} {'PRIMARY KEY' if col['pk'] else ''}")
    
    # Get row count
    count = conn.execute(f"SELECT COUNT(*) as cnt FROM {table_name}").fetchone()['cnt']
    print(f"\nRow count: {count}")
    
    if count > 0:
        # Get all data
        rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
        print(f"\nData ({count} rows):")
        print("-" * 80)
        
        # Print column headers
        if rows:
            headers = rows[0].keys()
            print(" | ".join(f"{h:20}" for h in headers))
            print("-" * 80)
            
            # Print rows (limit to 20 for readability)
            for i, row in enumerate(rows[:20]):
                values = []
                for h in headers:
                    val = row[h]
                    if val is None:
                        val = "NULL"
                    elif isinstance(val, str) and len(val) > 20:
                        val = val[:17] + "..."
                    values.append(str(val)[:20])
                print(" | ".join(f"{v:20}" for v in values))
            
            if len(rows) > 20:
                print(f"\n... and {len(rows) - 20} more rows")
    else:
        print("\n(No data)")

conn.close()
print("\n" + "=" * 80)
print("END OF DATABASE VIEW")
print("=" * 80)

