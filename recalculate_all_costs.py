"""
Recalculate All Costs - Fix costs for all runs using correct pricing
"""
import sqlite3
from tools.pricing import calculate_cost

def recalculate_all_costs(db_path="benchmark.db"):
    """Recalculate costs for all runs using correct pricing"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print("=" * 80)
    print("RECALCULATING ALL COSTS")
    print("=" * 80)
    print()
    
    # Get all runs with token data
    runs = conn.execute("""
        SELECT run_id, test_id, model, tokens_in, tokens_out, cost_usd
        FROM runs
        WHERE final_status IS NOT NULL
          AND tokens_in IS NOT NULL
          AND tokens_out IS NOT NULL
        ORDER BY run_id
    """).fetchall()
    
    print(f"Recalculating costs for {len(runs)} runs...")
    print()
    
    updated_count = 0
    total_old_cost = 0.0
    total_new_cost = 0.0
    
    for run in runs:
        run_id = run["run_id"]
        model = run["model"]
        tokens_in = run["tokens_in"]
        tokens_out = run["tokens_out"]
        old_cost = run["cost_usd"] or 0.0
        
        # Recalculate using correct pricing
        new_cost = calculate_cost(model, tokens_in, tokens_out)
        
        if new_cost is None:
            print(f"⚠️  Run {run_id[:8]}... | Test {run['test_id']}: Unknown model '{model}', skipping")
            continue
        
        # Only update if cost changed significantly (more than 0.01 difference)
        if abs(old_cost - (new_cost or 0)) > 0.01:
            conn.execute("""
                UPDATE runs
                SET cost_usd = ?
                WHERE run_id = ?
            """, (new_cost, run_id))
            
            print(f"✓ Run {run_id[:8]}... | Test {run['test_id']}:")
            print(f"    Tokens: {tokens_in:,} in, {tokens_out:,} out")
            print(f"    Old cost: ${old_cost:.6f}")
            print(f"    New cost: ${new_cost:.6f}")
            print(f"    Difference: ${new_cost - old_cost:.6f}")
            print()
            
            updated_count += 1
            total_old_cost += old_cost
            total_new_cost += new_cost
        else:
            # Cost is already correct (or very close)
            total_old_cost += old_cost
            total_new_cost += (new_cost or 0)
    
    conn.commit()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Runs updated: {updated_count}")
    print(f"Total old cost: ${total_old_cost:.6f}")
    print(f"Total new cost: ${total_new_cost:.6f}")
    print(f"Difference: ${total_new_cost - total_old_cost:.6f}")
    print()
    
    if updated_count > 0:
        print("✓ Costs updated in database")
    else:
        print("✓ All costs are already correct")
    
    conn.close()

if __name__ == "__main__":
    recalculate_all_costs()

