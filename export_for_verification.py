"""
Export Data for OpenAI Dashboard Verification
Export token usage and costs in a format you can compare with OpenAI dashboard
"""
import sqlite3
import csv
from datetime import datetime
from tools.pricing import calculate_cost

def export_for_verification(db_path="benchmark.db", output_file="openai_verification.csv"):
    """Export run data for comparison with OpenAI dashboard"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    runs = conn.execute("""
        SELECT run_id, test_id, model, started_at, ended_at,
               tokens_in, tokens_out, api_calls, cost_usd
        FROM runs
        WHERE final_status IS NOT NULL
          AND tokens_in IS NOT NULL
          AND tokens_out IS NOT NULL
        ORDER BY started_at
    """).fetchall()
    
    # Write to CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Run ID', 'Test ID', 'Model', 'Started At', 'Ended At',
            'Input Tokens', 'Output Tokens', 'Total Tokens', 'API Calls',
            'Calculated Cost (USD)', 'Cost per 1K Tokens'
        ])
        
        total_in = 0
        total_out = 0
        total_cost = 0.0
        
        for run in runs:
            tokens_in = run["tokens_in"]
            tokens_out = run["tokens_out"]
            total_tokens = tokens_in + tokens_out
            cost = run["cost_usd"] or calculate_cost(run["model"], tokens_in, tokens_out) or 0.0
            cost_per_1k = (cost / total_tokens * 1000) if total_tokens > 0 else 0
            
            writer.writerow([
                run["run_id"],
                run["test_id"],
                run["model"],
                run["started_at"],
                run["ended_at"],
                tokens_in,
                tokens_out,
                total_tokens,
                run["api_calls"],
                f"{cost:.6f}",
                f"{cost_per_1k:.6f}"
            ])
            
            total_in += tokens_in
            total_out += tokens_out
            total_cost += cost
        
        # Summary row
        writer.writerow([])
        writer.writerow(['TOTAL', '', '', '', '', total_in, total_out, total_in + total_out, '', f"{total_cost:.6f}", ''])
    
    print(f"✓ Exported {len(runs)} runs to {output_file}")
    print(f"\nSummary:")
    print(f"  Total Input Tokens:  {total_in:,}")
    print(f"  Total Output Tokens: {total_out:,}")
    print(f"  Total Cost:          ${total_cost:.6f}")
    print(f"\nTo verify:")
    print(f"  1. Go to https://platform.openai.com/usage")
    print(f"  2. Filter by date range matching your runs")
    print(f"  3. Compare token counts and costs")
    print(f"  4. Our calculation should match OpenAI's billing")
    
    conn.close()

if __name__ == "__main__":
    export_for_verification()

