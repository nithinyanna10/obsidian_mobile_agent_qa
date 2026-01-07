"""
Clean Old Data - Remove or mark runs with incorrect token counts
"""
import sqlite3
import sys

def clean_old_data(db_path="benchmark.db", action="mark"):
    """
    Clean old data with incorrect token counts
    
    Args:
        db_path: Path to database
        action: "delete" to delete runs, "mark" to set cost to NULL, "show" to just show
    """
    conn = sqlite3.connect(db_path)
    
    # Find runs with suspiciously high token counts (> 500k input tokens)
    suspicious = conn.execute("""
        SELECT run_id, test_id, tokens_in, tokens_out, cost_usd
        FROM runs
        WHERE tokens_in > 500000
    """).fetchall()
    
    print(f"Found {len(suspicious)} runs with suspicious token counts (> 500k input tokens)")
    
    if action == "show":
        for run in suspicious:
            print(f"  Run {run[0][:8]}... | Test {run[1]} | Tokens: {run[2]:,} in")
    elif action == "mark":
        # Set cost to NULL for suspicious runs
        conn.execute("""
            UPDATE runs
            SET cost_usd = NULL
            WHERE tokens_in > 500000
        """)
        conn.commit()
        print(f"✓ Marked {len(suspicious)} runs (set cost_usd to NULL)")
    elif action == "delete":
        # Delete suspicious runs
        conn.execute("""
            DELETE FROM runs
            WHERE tokens_in > 500000
        """)
        conn.commit()
        print(f"✓ Deleted {len(suspicious)} runs with incorrect token counts")
    
    conn.close()

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "show"
    if action not in ["show", "mark", "delete"]:
        print("Usage: python clean_old_data.py [show|mark|delete]")
        sys.exit(1)
    clean_old_data(action=action)

