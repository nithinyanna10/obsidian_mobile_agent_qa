"""
Verify Cost Calculations - Compare with OpenAI pricing and check for accuracy
"""
import sqlite3
from tools.pricing import calculate_cost, PRICE_PER_1M

def verify_costs(db_path="benchmark.db"):
    """Verify cost calculations are correct"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print("=" * 80)
    print("COST VERIFICATION")
    print("=" * 80)
    print()
    
    print("Current Pricing Map:")
    print("-" * 80)
    for model, pricing in PRICE_PER_1M.items():
        print(f"  {model}: ${pricing['in']:.2f}/1M input, ${pricing['out']:.2f}/1M output")
    print()
    
    # Get runs with valid data
    runs = conn.execute("""
        SELECT run_id, test_id, model, tokens_in, tokens_out, api_calls, cost_usd
        FROM runs
        WHERE final_status IS NOT NULL 
          AND cost_usd IS NOT NULL
          AND tokens_in IS NOT NULL
          AND tokens_out IS NOT NULL
        ORDER BY run_id
    """).fetchall()
    
    print(f"Verifying {len(runs)} runs:")
    print("-" * 80)
    
    total_in = 0
    total_out = 0
    total_calculated_cost = 0.0
    total_stored_cost = 0.0
    
    for run in runs:
        tokens_in = run["tokens_in"]
        tokens_out = run["tokens_out"]
        stored_cost = run["cost_usd"]
        model = run["model"]
        
        # Recalculate cost
        calculated_cost = calculate_cost(model, tokens_in, tokens_out)
        
        # Check if stored cost matches calculated
        diff = abs(stored_cost - calculated_cost) if calculated_cost else 0
        match = "✓" if diff < 0.0001 else "✗"
        
        print(f"{match} Run {run['run_id'][:8]}... | Test {run['test_id']}")
        print(f"    Tokens: {tokens_in:,} in, {tokens_out:,} out")
        print(f"    Stored cost: ${stored_cost:.6f}")
        print(f"    Calculated:  ${calculated_cost:.6f}")
        if diff >= 0.0001:
            print(f"    ⚠️  Mismatch: ${diff:.6f} difference")
        print()
        
        total_in += tokens_in
        total_out += tokens_out
        total_calculated_cost += calculated_cost or 0
        total_stored_cost += stored_cost
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tokens: {total_in:,} in, {total_out:,} out")
    print(f"Total stored cost: ${total_stored_cost:.6f}")
    print(f"Total calculated cost: ${total_calculated_cost:.6f}")
    print(f"Per test average: ${total_calculated_cost/len(runs):.6f}")
    print()
    
    # Verify against OpenAI pricing
    print("VERIFICATION AGAINST OPENAI PRICING:")
    print("-" * 80)
    print("GPT-4o pricing (as of 2024):")
    print("  Input:  $5.00 per 1M tokens")
    print("  Output: $15.00 per 1M tokens")
    print()
    
    expected_cost = (total_in / 1_000_000.0 * 5.00) + (total_out / 1_000_000.0 * 15.00)
    print(f"Expected cost: ${expected_cost:.6f}")
    print(f"Calculated cost: ${total_calculated_cost:.6f}")
    
    if abs(expected_cost - total_calculated_cost) < 0.0001:
        print("✓ Cost calculation matches OpenAI pricing")
    else:
        print(f"⚠️  Difference: ${abs(expected_cost - total_calculated_cost):.6f}")
    
    conn.close()

if __name__ == "__main__":
    verify_costs()

