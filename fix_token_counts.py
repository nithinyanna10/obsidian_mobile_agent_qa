"""
Fix Token Counts - Mark all runs with suspiciously high token counts as invalid
Based on actual OpenAI billing, token counts should be much lower
"""
import sqlite3

def fix_token_counts(db_path="benchmark.db", max_reasonable_tokens=50000):
    """
    Mark runs with unreasonably high token counts as invalid
    
    Based on actual OpenAI billing:
    - Expected cost per test: ~$0.10
    - Expected tokens per test: ~10k-20k input, ~1k-2k output
    - Anything above 50k input tokens is suspicious
    """
    conn = sqlite3.connect(db_path)
    
    print("=" * 80)
    print("FIXING TOKEN COUNTS")
    print("=" * 80)
    print()
    print(f"Marking runs with > {max_reasonable_tokens:,} input tokens as invalid")
    print("(Based on actual OpenAI billing showing ~$0.10 per test)")
    print()
    
    # Find suspicious runs
    suspicious = conn.execute("""
        SELECT run_id, test_id, tokens_in, tokens_out, cost_usd
        FROM runs
        WHERE tokens_in > ?
        AND final_status IS NOT NULL
    """, (max_reasonable_tokens,)).fetchall()
    
    print(f"Found {len(suspicious)} runs with suspicious token counts:")
    for run in suspicious:
        print(f"  Run {run[0][:8]}... | Test {run[1]} | {run[2]:,} input tokens")
    
    if suspicious:
        # Set cost to NULL for suspicious runs
        conn.execute("""
            UPDATE runs
            SET cost_usd = NULL
            WHERE tokens_in > ?
        """, (max_reasonable_tokens,))
        conn.commit()
        print()
        print(f"✓ Marked {len(suspicious)} runs as invalid (set cost_usd to NULL)")
    else:
        print("✓ No suspicious runs found")
    
    # Show remaining valid runs
    valid = conn.execute("""
        SELECT run_id, test_id, tokens_in, tokens_out, cost_usd
        FROM runs
        WHERE tokens_in <= ?
        AND final_status IS NOT NULL
        AND cost_usd IS NOT NULL
    """, (max_reasonable_tokens,)).fetchall()
    
    print()
    print(f"Valid runs ({len(valid)}):")
    total_cost = 0.0
    for run in valid:
        print(f"  Run {run[0][:8]}... | Test {run[1]} | {run[2]:,} in, {run[3]:,} out | \${run[4]:.4f}")
        total_cost += run[4] or 0
    
    if valid:
        print(f"\nTotal cost from valid runs: \${total_cost:.4f}")
        print(f"Per test: \${total_cost/len(valid):.4f}")
    else:
        print("\n⚠️  No valid runs found!")
        print("All runs have suspicious token counts.")
        print("You'll need to run new tests to get accurate data.")
    
    conn.close()

if __name__ == "__main__":
    fix_token_counts()

