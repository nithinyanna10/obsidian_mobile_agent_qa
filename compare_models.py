"""
Compare all benchmarked models with colorful graphs
"""
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from collections import defaultdict
import argparse
import os

# Set style for better-looking graphs
plt.style.use('seaborn-v0_8-darkgrid')
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52BE80']

def get_all_models(db_path="benchmark.db"):
    """Get all unique models from database"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    models = conn.execute("""
        SELECT DISTINCT reasoning_llm_model as model
        FROM runs
        WHERE reasoning_llm_model IS NOT NULL
        ORDER BY reasoning_llm_model
    """).fetchall()
    
    conn.close()
    return [row['model'] for row in models]

def get_metrics_for_model(db_path, model):
    """Get all metrics for a specific model"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    metrics = {}
    
    # Pass rate (Should-PASS)
    # Use the latest run per test to avoid counting duplicates
    pass_rate = conn.execute("""
        WITH latest_runs AS (
            SELECT run_id, test_id, trial_num, final_status,
                   ROW_NUMBER() OVER (PARTITION BY test_id, trial_num ORDER BY started_at DESC) as rn
            FROM runs
            WHERE reasoning_llm_model = ? AND should='PASS' AND final_status IS NOT NULL
        )
        SELECT AVG(CASE WHEN final_status='PASS' THEN 1.0 ELSE 0.0 END) AS pass_rate,
               COUNT(*) AS total_runs
        FROM latest_runs
        WHERE rn = 1
    """, (model,)).fetchone()
    metrics['pass_rate'] = pass_rate['pass_rate'] if pass_rate and pass_rate['total_runs'] > 0 else 0.0
    metrics['pass_runs'] = pass_rate['total_runs'] if pass_rate else 0
    
    # Correct fail rate (Should-FAIL)
    fail_rate = conn.execute("""
        SELECT AVG(CASE WHEN final_status='FAIL' THEN 1.0 ELSE 0.0 END) AS correct_fail_rate,
               COUNT(*) AS total_runs
        FROM runs
        WHERE reasoning_llm_model = ? AND should='FAIL' AND final_status IS NOT NULL
    """, (model,)).fetchone()
    metrics['correct_fail_rate'] = fail_rate['correct_fail_rate'] if fail_rate and fail_rate['total_runs'] > 0 else 0.0
    metrics['fail_runs'] = fail_rate['total_runs'] if fail_rate else 0
    
    # Steps (use latest run per test to avoid duplicates)
    steps = conn.execute("""
        WITH latest_runs AS (
            SELECT run_id, test_id, trial_num, steps_count,
                   ROW_NUMBER() OVER (PARTITION BY test_id, trial_num ORDER BY started_at DESC) as rn
            FROM runs
            WHERE reasoning_llm_model = ? AND final_status IS NOT NULL AND steps_count IS NOT NULL
        )
        SELECT AVG(steps_count) AS avg_steps,
               MIN(steps_count) AS min_steps,
               MAX(steps_count) AS max_steps
        FROM latest_runs
        WHERE rn = 1
    """, (model,)).fetchone()
    metrics['avg_steps'] = steps['avg_steps'] if steps and steps['avg_steps'] else 0.0
    metrics['min_steps'] = steps['min_steps'] if steps and steps['min_steps'] else 0
    metrics['max_steps'] = steps['max_steps'] if steps and steps['max_steps'] else 0
    
    # Time (use latest run per test to avoid duplicates)
    time_data = conn.execute("""
        WITH latest_runs AS (
            SELECT run_id, test_id, trial_num, duration_ms,
                   ROW_NUMBER() OVER (PARTITION BY test_id, trial_num ORDER BY started_at DESC) as rn
            FROM runs
            WHERE reasoning_llm_model = ? AND final_status IS NOT NULL AND duration_ms IS NOT NULL
        )
        SELECT AVG(duration_ms) AS avg_time,
               MIN(duration_ms) AS min_time,
               MAX(duration_ms) AS max_time
        FROM latest_runs
        WHERE rn = 1
    """, (model,)).fetchone()
    metrics['avg_time'] = time_data['avg_time'] if time_data and time_data['avg_time'] else 0.0
    metrics['min_time'] = time_data['min_time'] if time_data and time_data['min_time'] else 0
    metrics['max_time'] = time_data['max_time'] if time_data and time_data['max_time'] else 0
    
    # Cost (use latest run per test to avoid duplicates)
    cost = conn.execute("""
        WITH latest_runs AS (
            SELECT run_id, test_id, trial_num, cost_usd,
                   ROW_NUMBER() OVER (PARTITION BY test_id, trial_num ORDER BY started_at DESC) as rn
            FROM runs
            WHERE reasoning_llm_model = ? AND final_status IS NOT NULL AND cost_usd IS NOT NULL
        )
        SELECT SUM(cost_usd) AS total_cost,
               AVG(cost_usd) AS avg_cost
        FROM latest_runs
        WHERE rn = 1
    """, (model,)).fetchone()
    metrics['total_cost'] = cost['total_cost'] if cost and cost['total_cost'] else 0.0
    metrics['avg_cost'] = cost['avg_cost'] if cost and cost['avg_cost'] else 0.0
    
    # Tokens (use latest run per test to avoid duplicates)
    tokens = conn.execute("""
        WITH latest_runs AS (
            SELECT run_id, test_id, trial_num, tokens_in, tokens_out,
                   ROW_NUMBER() OVER (PARTITION BY test_id, trial_num ORDER BY started_at DESC) as rn
            FROM runs
            WHERE reasoning_llm_model = ? AND final_status IS NOT NULL
        )
        SELECT SUM(tokens_in) AS total_tokens_in,
               SUM(tokens_out) AS total_tokens_out,
               AVG(tokens_in) AS avg_tokens_in,
               AVG(tokens_out) AS avg_tokens_out
        FROM latest_runs
        WHERE rn = 1
    """, (model,)).fetchone()
    metrics['total_tokens_in'] = tokens['total_tokens_in'] if tokens and tokens['total_tokens_in'] else 0
    metrics['total_tokens_out'] = tokens['total_tokens_out'] if tokens and tokens['total_tokens_out'] else 0
    metrics['avg_tokens_in'] = tokens['avg_tokens_in'] if tokens and tokens['avg_tokens_in'] else 0.0
    metrics['avg_tokens_out'] = tokens['avg_tokens_out'] if tokens and tokens['avg_tokens_out'] else 0.0
    
    # API calls (use latest run per test to avoid duplicates)
    api_calls = conn.execute("""
        WITH latest_runs AS (
            SELECT run_id, test_id, trial_num, api_calls,
                   ROW_NUMBER() OVER (PARTITION BY test_id, trial_num ORDER BY started_at DESC) as rn
            FROM runs
            WHERE reasoning_llm_model = ? AND final_status IS NOT NULL
        )
        SELECT SUM(api_calls) AS total_calls,
               AVG(api_calls) AS avg_calls
        FROM latest_runs
        WHERE rn = 1
    """, (model,)).fetchone()
    metrics['total_calls'] = api_calls['total_calls'] if api_calls and api_calls['total_calls'] else 0
    metrics['avg_calls'] = api_calls['avg_calls'] if api_calls and api_calls['avg_calls'] else 0.0
    
    # Total runs (use latest run per test to avoid duplicates)
    total_runs = conn.execute("""
        WITH latest_runs AS (
            SELECT run_id, test_id, trial_num,
                   ROW_NUMBER() OVER (PARTITION BY test_id, trial_num ORDER BY started_at DESC) as rn
            FROM runs
            WHERE reasoning_llm_model = ? AND final_status IS NOT NULL
        )
        SELECT COUNT(*) AS total
        FROM latest_runs
        WHERE rn = 1
    """, (model,)).fetchone()
    metrics['total_runs'] = total_runs['total'] if total_runs else 0
    
    conn.close()
    return metrics

def create_comparison_graphs(models_data, output_dir="graphs"):
    """Create colorful comparison graphs"""
    os.makedirs(output_dir, exist_ok=True)
    
    models = list(models_data.keys())
    n_models = len(models)
    
    # Create figure with subplots
    fig = plt.figure(figsize=(20, 12))
    
    # 1. Pass Rate Comparison
    ax1 = plt.subplot(2, 3, 1)
    pass_rates = [models_data[m]['pass_rate'] * 100 for m in models]
    bars1 = ax1.barh(models, pass_rates, color=colors[:n_models])
    ax1.set_xlabel('Pass Rate (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Pass Rate (Should-PASS Tests)', fontsize=14, fontweight='bold', pad=20)
    ax1.set_xlim(0, 100)
    ax1.grid(axis='x', alpha=0.3)
    # Add value labels
    for i, (bar, rate) in enumerate(zip(bars1, pass_rates)):
        ax1.text(rate + 1, i, f'{rate:.1f}%', va='center', fontweight='bold')
    
    # 2. Average Steps per Test
    ax2 = plt.subplot(2, 3, 2)
    avg_steps = [models_data[m]['avg_steps'] for m in models]
    bars2 = ax2.barh(models, avg_steps, color=colors[:n_models])
    ax2.set_xlabel('Average Steps', fontsize=12, fontweight='bold')
    ax2.set_title('Average Steps per Test', fontsize=14, fontweight='bold', pad=20)
    ax2.grid(axis='x', alpha=0.3)
    # Add value labels
    for i, (bar, steps) in enumerate(zip(bars2, avg_steps)):
        ax2.text(steps + 0.5, i, f'{steps:.1f}', va='center', fontweight='bold')
    
    # 3. Average Time per Test
    ax3 = plt.subplot(2, 3, 3)
    avg_times = [models_data[m]['avg_time'] / 1000 for m in models]  # Convert to seconds
    bars3 = ax3.barh(models, avg_times, color=colors[:n_models])
    ax3.set_xlabel('Average Time (seconds)', fontsize=12, fontweight='bold')
    ax3.set_title('Average Time per Test', fontsize=14, fontweight='bold', pad=20)
    ax3.grid(axis='x', alpha=0.3)
    # Add value labels
    for i, (bar, time) in enumerate(zip(bars3, avg_times)):
        ax3.text(time + 1, i, f'{time:.1f}s', va='center', fontweight='bold')
    
    # 4. Cost Comparison
    ax4 = plt.subplot(2, 3, 4)
    total_costs = [models_data[m]['total_cost'] for m in models]
    bars4 = ax4.barh(models, total_costs, color=colors[:n_models])
    ax4.set_xlabel('Total Cost (USD)', fontsize=12, fontweight='bold')
    ax4.set_title('Total Cost Comparison', fontsize=14, fontweight='bold', pad=20)
    ax4.grid(axis='x', alpha=0.3)
    # Add value labels
    for i, (bar, cost) in enumerate(zip(bars4, total_costs)):
        if cost > 0:
            ax4.text(cost + 0.01, i, f'${cost:.2f}', va='center', fontweight='bold')
    
    # 5. Token Usage (Input + Output)
    ax5 = plt.subplot(2, 3, 5)
    tokens_in = [models_data[m]['total_tokens_in'] / 1000 for m in models]  # Convert to thousands
    tokens_out = [models_data[m]['total_tokens_out'] / 1000 for m in models]
    x = np.arange(n_models)
    width = 0.35
    bars5a = ax5.barh(x - width/2, tokens_in, width, label='Input Tokens', color='#FF6B6B')
    bars5b = ax5.barh(x + width/2, tokens_out, width, label='Output Tokens', color='#4ECDC4')
    ax5.set_yticks(x)
    ax5.set_yticklabels(models)
    ax5.set_xlabel('Tokens (thousands)', fontsize=12, fontweight='bold')
    ax5.set_title('Token Usage Comparison', fontsize=14, fontweight='bold', pad=20)
    ax5.legend()
    ax5.grid(axis='x', alpha=0.3)
    
    # 6. API Calls
    ax6 = plt.subplot(2, 3, 6)
    total_calls = [models_data[m]['total_calls'] for m in models]
    bars6 = ax6.barh(models, total_calls, color=colors[:n_models])
    ax6.set_xlabel('Total API Calls', fontsize=12, fontweight='bold')
    ax6.set_title('Total API Calls', fontsize=14, fontweight='bold', pad=20)
    ax6.grid(axis='x', alpha=0.3)
    # Add value labels
    for i, (bar, calls) in enumerate(zip(bars6, total_calls)):
        ax6.text(calls + 1, i, f'{int(calls)}', va='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/model_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved comparison graph to {output_dir}/model_comparison.png")
    
    # Create a detailed metrics table graph
    fig2, ax = plt.subplots(figsize=(16, 10))
    ax.axis('tight')
    ax.axis('off')
    
    # Prepare table data
    table_data = []
    headers = ['Model', 'Pass Rate', 'Avg Steps', 'Avg Time (s)', 'Total Cost ($)', 'Total Tokens', 'Total Calls', 'Runs']
    
    for model in models:
        data = models_data[model]
        table_data.append([
            model[:30],  # Truncate long model names
            f"{data['pass_rate']*100:.1f}%",
            f"{data['avg_steps']:.1f}",
            f"{data['avg_time']/1000:.1f}s",
            f"${data['total_cost']:.2f}",
            f"{(data['total_tokens_in'] + data['total_tokens_out'])/1000:.1f}K",
            f"{int(data['total_calls'])}",
            f"{data['total_runs']}"
        ])
    
    table = ax.table(cellText=table_data, colLabels=headers, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)
    
    # Style the header
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#4ECDC4')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Alternate row colors
    for i in range(1, len(table_data) + 1):
        for j in range(len(headers)):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#F0F0F0')
            else:
                table[(i, j)].set_facecolor('white')
    
    plt.title('Model Comparison - Detailed Metrics', fontsize=16, fontweight='bold', pad=20)
    plt.savefig(f'{output_dir}/model_comparison_table.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved metrics table to {output_dir}/model_comparison_table.png")
    
    plt.close('all')

def main():
    parser = argparse.ArgumentParser(description="Compare all benchmarked models with colorful graphs")
    parser.add_argument("--db", type=str, default="benchmark.db", help="Database path")
    parser.add_argument("--output-dir", type=str, default="graphs", help="Output directory for graphs")
    args = parser.parse_args()
    
    print("=" * 80)
    print("MODEL COMPARISON - COLORFUL GRAPHS")
    print("=" * 80)
    print()
    
    # Get all models
    models = get_all_models(args.db)
    if not models:
        print("❌ No models found in database!")
        return
    
    print(f"Found {len(models)} models:")
    for model in models:
        print(f"  • {model}")
    print()
    
    # Get metrics for each model
    print("Computing metrics for each model...")
    models_data = {}
    for model in models:
        print(f"  Computing metrics for {model}...")
        models_data[model] = get_metrics_for_model(args.db, model)
    
    print()
    print("Creating colorful comparison graphs...")
    create_comparison_graphs(models_data, args.output_dir)
    
    print()
    print("=" * 80)
    print("COMPARISON COMPLETE!")
    print("=" * 80)
    print(f"Graphs saved to: {args.output_dir}/")
    print(f"  • model_comparison.png - 6 comparison charts")
    print(f"  • model_comparison_table.png - Detailed metrics table")

if __name__ == "__main__":
    main()

