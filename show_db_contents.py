"""
Show Database Contents - Display the actual data in SQLite database tables
"""
import sqlite3
import argparse
from typing import List, Dict
import json


def format_table_data(conn: sqlite3.Connection, table_name: str, limit: int = None):
    """Format and display table data"""
    conn.row_factory = sqlite3.Row
    
    # Get column names
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    
    # Build query
    query = f"SELECT * FROM {table_name}"
    if limit:
        query += f" LIMIT {limit}"
    
    # Get data
    cursor = conn.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        print(f"\n{table_name}: No data")
        return
    
    # Calculate column widths
    col_widths = {}
    for col in columns:
        col_widths[col] = max(len(col), 15)  # Minimum width
    
    for row in rows:
        for col in columns:
            value = row[col]
            if value is None:
                value = "NULL"
            elif isinstance(value, str) and len(value) > 50:
                value = value[:47] + "..."
            else:
                value = str(value)
            col_widths[col] = max(col_widths[col], len(value))
    
    # Print header
    print(f"\n{'=' * 100}")
    print(f"TABLE: {table_name}")
    if limit:
        print(f"Showing first {limit} rows")
    print(f"{'=' * 100}\n")
    
    # Print column headers
    header = " | ".join([col.ljust(col_widths[col]) for col in columns])
    print(header)
    print("-" * len(header))
    
    # Print rows
    for row in rows:
        values = []
        for col in columns:
            value = row[col]
            if value is None:
                value = "NULL"
            elif isinstance(value, str) and len(value) > 50:
                value = value[:47] + "..."
            else:
                value = str(value)
            values.append(value.ljust(col_widths[col]))
        print(" | ".join(values))
    
    # Get total count
    total = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    print(f"\nTotal rows: {total}")
    if limit and total > limit:
        print(f"(Showing {limit} of {total} rows)")


def show_runs_summary(conn: sqlite3.Connection):
    """Show summary of runs table"""
    conn.row_factory = sqlite3.Row
    
    print(f"\n{'=' * 100}")
    print("RUNS SUMMARY")
    print(f"{'=' * 100}\n")
    
    # Group by model
    cursor = conn.execute("""
        SELECT reasoning_llm_model, 
               COUNT(*) as total_runs,
               SUM(CASE WHEN final_status='PASS' THEN 1 ELSE 0 END) as passed,
               SUM(CASE WHEN final_status='FAIL' THEN 1 ELSE 0 END) as failed,
               AVG(cost_usd) as avg_cost,
               SUM(cost_usd) as total_cost
        FROM runs
        WHERE reasoning_llm_model IS NOT NULL
        GROUP BY reasoning_llm_model
        ORDER BY reasoning_llm_model
    """)
    
    print(f"{'Model':<40} {'Runs':<10} {'Passed':<10} {'Failed':<10} {'Avg Cost':<15} {'Total Cost':<15}")
    print("-" * 100)
    
    for row in cursor.fetchall():
        print(f"{row['reasoning_llm_model']:<40} {row['total_runs']:<10} {row['passed']:<10} {row['failed']:<10} ${row['avg_cost'] or 0:<14.4f} ${row['total_cost'] or 0:<14.2f}")


def show_detailed_runs(conn: sqlite3.Connection, limit: int = 20):
    """Show detailed runs data"""
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute(f"""
        SELECT run_id, experiment_id, trial_num, reasoning_llm_model, test_id, 
               should, final_status, steps_count, duration_ms, cost_usd, 
               tokens_in, tokens_out, api_calls, started_at
        FROM runs
        ORDER BY started_at DESC
        LIMIT {limit}
    """)
    
    rows = cursor.fetchall()
    
    if not rows:
        print("\nNo runs found")
        return
    
    print(f"\n{'=' * 150}")
    print("DETAILED RUNS (Most Recent)")
    print(f"{'=' * 150}\n")
    
    # Print header
    headers = ['Run ID', 'Experiment', 'Trial', 'Model', 'Test', 'Should', 'Status', 
               'Steps', 'Time (ms)', 'Cost', 'Tokens In', 'Tokens Out', 'Calls', 'Started']
    print(" | ".join([h.ljust(12) for h in headers]))
    print("-" * 150)
    
    for row in rows:
        run_id_short = row['run_id'][:8] + "..." if row['run_id'] else "N/A"
        exp_id = row['experiment_id'] or "N/A"
        if exp_id and len(exp_id) > 10:
            exp_id = exp_id[:7] + "..."
        model = row['reasoning_llm_model'] or "N/A"
        if model and len(model) > 15:
            model = model[:12] + "..."
        
        values = [
            run_id_short.ljust(12),
            str(exp_id).ljust(12),
            str(row['trial_num'] or "N/A").ljust(12),
            model.ljust(12),
            str(row['test_id'] or "N/A").ljust(12),
            str(row['should'] or "N/A").ljust(12),
            str(row['final_status'] or "N/A").ljust(12),
            str(row['steps_count'] or "N/A").ljust(12),
            str(row['duration_ms'] or "N/A").ljust(12),
            f"${row['cost_usd'] or 0:.4f}".ljust(12),
            str(row['tokens_in'] or 0).ljust(12),
            str(row['tokens_out'] or 0).ljust(12),
            str(row['api_calls'] or 0).ljust(12),
            str(row['started_at'] or "N/A")[:19].ljust(12) if row['started_at'] else "N/A".ljust(12)
        ]
        print(" | ".join(values))


def main():
    parser = argparse.ArgumentParser(description="Show database contents")
    parser.add_argument("--db", type=str, default="benchmark.db", help="Database path")
    parser.add_argument("--table", type=str, help="Show contents of specific table")
    parser.add_argument("--limit", type=int, default=50, help="Limit number of rows to show")
    parser.add_argument("--summary", action="store_true", help="Show summary only")
    parser.add_argument("--runs", action="store_true", help="Show detailed runs data")
    
    args = parser.parse_args()
    
    conn = sqlite3.connect(args.db)
    
    print("=" * 100)
    print("DATABASE CONTENTS")
    print("=" * 100)
    print(f"Database: {args.db}")
    print()
    
    if args.summary:
        show_runs_summary(conn)
    elif args.runs:
        show_detailed_runs(conn, args.limit)
    elif args.table:
        format_table_data(conn, args.table, args.limit)
    else:
        # Show all tables
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Show summary first
        show_runs_summary(conn)
        
        # Show each table
        for table in tables:
            format_table_data(conn, table, args.limit)
    
    conn.close()
    print(f"\n{'=' * 100}")


if __name__ == "__main__":
    main()
