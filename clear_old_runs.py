"""
Clear all runs from the database (use with caution!)
"""
import sqlite3

conn = sqlite3.connect("benchmark.db")

print("=" * 80)
print("CLEARING ALL RUNS FROM DATABASE")
print("=" * 80)
print()

# Count before
count_before = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
print(f"Runs before: {count_before}")

if count_before > 0:
    # Delete all runs (cascades to steps and assertions)
    conn.execute("DELETE FROM runs")
    conn.commit()
    print(f"✓ Deleted {count_before} runs")
else:
    print("✓ Database already empty")

# Count after
count_after = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
print(f"Runs after: {count_after}")

conn.close()
print("\n✓ Database cleared!")

