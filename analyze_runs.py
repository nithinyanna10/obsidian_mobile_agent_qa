"""
Analyze runs in the database to understand what's stored
"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect("benchmark.db")
conn.row_factory = sqlite3.Row

print("=" * 80)
print("DATABASE RUN ANALYSIS")
print("=" * 80)
print()

# Group by experiment and trial
print("Runs grouped by experiment_id and trial_num:")
print("-" * 80)
trials = conn.execute("""
    SELECT experiment_id, trial_num, 
           COUNT(*) as total_runs,
           COUNT(DISTINCT test_id) as unique_tests,
           GROUP_CONCAT(DISTINCT test_id) as test_ids,
           MIN(started_at) as first_run,
           MAX(started_at) as last_run
    FROM runs
    WHERE final_status IS NOT NULL
    GROUP BY experiment_id, trial_num
    ORDER BY trial_num, MIN(started_at)
""").fetchall()

for trial in trials:
    print(f"Experiment: {trial['experiment_id']}")
    print(f"  Trial: {trial['trial_num']}")
    print(f"  Total runs: {trial['total_runs']}")
    print(f"  Unique tests: {trial['unique_tests']}")
    print(f"  Test IDs: {trial['test_ids']}")
    print(f"  First run: {trial['first_run']}")
    print(f"  Last run: {trial['last_run']}")
    print()

# Show all runs with details
print("\nAll completed runs (ordered by time):")
print("-" * 80)
runs = conn.execute("""
    SELECT run_id, test_id, should, final_status, started_at, experiment_id, trial_num
    FROM runs
    WHERE final_status IS NOT NULL
    ORDER BY started_at
""").fetchall()

for run in runs:
    status_icon = "✓" if run['final_status'] == run['should'] else "✗"
    print(f"{status_icon} Test {run['test_id']} | should={run['should']} | got={run['final_status']} | {run['started_at']}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)

# Count by should_pass
should_pass = conn.execute("""
    SELECT COUNT(*) as count
    FROM runs
    WHERE should='PASS' AND final_status IS NOT NULL
""").fetchone()['count']

should_fail = conn.execute("""
    SELECT COUNT(*) as count
    FROM runs
    WHERE should='FAIL' AND final_status IS NOT NULL
""").fetchone()['count']

print(f"Runs where should='PASS': {should_pass}")
print(f"Runs where should='FAIL': {should_fail}")
print(f"Total completed runs: {should_pass + should_fail}")

conn.close()

