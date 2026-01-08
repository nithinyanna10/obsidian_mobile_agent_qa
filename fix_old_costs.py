"""
Fix Old Cost Data - Recalculate costs for runs with potentially incorrect token counts
This script identifies runs with suspiciously high token counts (likely character counts)
and marks them or recalculates if we have accurate data.
"""
import sqlite3
from tools.pricing import calculate_cost, PRICE_PER_1M

def analyze_database(db_path="benchmark.db"):
    """Analyze database for incorrect token counts"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print("=" * 80)
    print("ANALYZING DATABASE FOR INCORRECT TOKEN COUNTS")
    print("=" * 80)
    print()
    
    # Get all runs
    runs = conn.execute("""
        SELECT run_id, test_id, model, tokens_in, tokens_out, api_calls, cost_usd, final_status
        FROM runs
        WHERE final_status IS NOT NULL
        ORDER BY run_id
    """).fetchall()
    
    print(f"Found {len(runs)} completed runs\n")
    
    # Typical token counts for a test run:
    # - Input: 10k-100k tokens (screenshots + prompts)
    # - Output: 1k-10k tokens (responses)
    # Anything above 500k input tokens is suspicious (likely character count)
    
    suspicious_runs = []
    normal_runs = []
    
    for run in runs:
        tokens_in = run["tokens_in"] or 0
        tokens_out = run["tokens_out"] or 0
        
        # Flag runs with suspiciously high token counts
        if tokens_in > 500000:  # 500k+ input tokens is suspicious
            suspicious_runs.append(run)
        else:
            normal_runs.append(run)
    
    print("SUSPICIOUS RUNS (likely character counts, not tokens):")
    print("-" * 80)
    if suspicious_runs:
        for run in suspicious_runs:
            print(f"Run {run['run_id'][:8]}... | Test {run['test_id']} | "
                  f"Tokens: {run['tokens_in']:,} in, {run['tokens_out']:,} out | "
                  f"Cost: ${run['cost_usd']:.4f}")
            print(f"  ⚠️  This run likely has incorrect token counts (character counts)")
    else:
        print("  None found")
    
    print()
    print("NORMAL RUNS (token counts look reasonable):")
    print("-" * 80)
    if normal_runs:
        for run in normal_runs:
            print(f"Run {run['run_id'][:8]}... | Test {run['test_id']} | "
                  f"Tokens: {run['tokens_in']:,} in, {run['tokens_out']:,} out | "
                  f"Cost: ${run['cost_usd']:.4f}")
    else:
        print("  None found")
    
    print()
    print("RECOMMENDATION:")
    print("-" * 80)
    if suspicious_runs:
        print(f"⚠️  {len(suspicious_runs)} runs have suspiciously high token counts.")
        print("   These are likely from the old character-counting method.")
        print("   Costs for these runs are incorrect.")
        print()
        print("   Options:")
        print("   1. Delete old runs: DELETE FROM runs WHERE tokens_in > 500000;")
        print("   2. Mark as invalid: UPDATE runs SET cost_usd = NULL WHERE tokens_in > 500000;")
        print("   3. Re-run tests to get accurate data")
    else:
        print("✓ All runs have reasonable token counts")
    
    conn.close()

if __name__ == "__main__":
    analyze_database()

