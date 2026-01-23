#!/usr/bin/env python3
"""
View Latest Run - Shows the most recent individual test run from the database

Note: For viewing complete test suite runs (all tests together), use:
      python3 view_latest_suite.py
"""
import sqlite3
import argparse
import json
from datetime import datetime

def safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row"""
    try:
        value = row[key]
        return value if value is not None else default
    except (KeyError, IndexError):
        return default

def format_datetime(dt_str):
    """Format datetime string for display"""
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str

def show_latest_run(db_path: str = "benchmark.db", run_id: str = None):
    """Show the latest run with full details"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Get latest run
    if run_id:
        cursor = conn.execute("""
            SELECT * FROM runs WHERE run_id = ?
        """, (run_id,))
    else:
        cursor = conn.execute("""
            SELECT * FROM runs 
            ORDER BY started_at DESC 
            LIMIT 1
        """)
    
    run = cursor.fetchone()
    
    if not run:
        print("❌ No runs found in database")
        conn.close()
        return
    
    print("=" * 80)
    print("LATEST TEST RUN")
    print("=" * 80)
    print()
    
    # Run Information
    print("📊 RUN INFORMATION")
    print("-" * 80)
    print(f"Run ID:        {safe_get(run, 'run_id', 'N/A')}")
    print(f"Experiment:    {safe_get(run, 'experiment_id', 'N/A')}")
    print(f"Trial:         {safe_get(run, 'trial_num', 'N/A')}")
    print(f"Test ID:       {safe_get(run, 'test_id', 'N/A')}")
    print(f"Expected:      {safe_get(run, 'should', 'N/A')}")
    print(f"Status:        {safe_get(run, 'final_status', 'N/A')}")
    print(f"Started:       {format_datetime(safe_get(run, 'started_at'))}")
    print(f"Ended:         {format_datetime(safe_get(run, 'ended_at'))}")
    print()
    
    # Model Information
    print("🤖 MODEL INFORMATION")
    print("-" * 80)
    reasoning_model = safe_get(run, 'reasoning_llm_model', 'N/A')
    reasoning_provider = safe_get(run, 'reasoning_llm_provider', 'N/A')
    vision_model = safe_get(run, 'vision_llm_model', 'N/A')
    vision_provider = safe_get(run, 'vision_llm_provider', 'N/A')
    print(f"Reasoning Model:  {reasoning_model} ({reasoning_provider})")
    print(f"Vision Model:     {vision_model} ({vision_provider})")
    print()
    
    # Performance Metrics
    print("⚡ PERFORMANCE METRICS")
    print("-" * 80)
    duration_ms = safe_get(run, 'duration_ms', 0) or 0
    duration_sec = duration_ms / 1000.0
    steps = safe_get(run, 'steps_count', 0) or 0
    tokens_in = safe_get(run, 'tokens_in', 0) or 0
    tokens_out = safe_get(run, 'tokens_out', 0) or 0
    cost = safe_get(run, 'cost_usd', 0.0) or 0.0
    api_calls = safe_get(run, 'api_calls', 0) or 0
    
    print(f"Steps Taken:    {steps}")
    print(f"Duration:       {duration_sec:.2f} seconds ({duration_ms} ms)")
    print(f"API Calls:      {api_calls}")
    print(f"Tokens In:      {tokens_in:,}")
    print(f"Tokens Out:     {tokens_out:,}")
    print(f"Total Tokens:   {tokens_in + tokens_out:,}")
    print(f"Cost:           ${cost:.6f}")
    print()
    
    # Additional Info
    failure_reason = safe_get(run, 'failure_reason')
    if failure_reason:
        print("❌ FAILURE REASON")
        print("-" * 80)
        print(f"{failure_reason}")
        print()
    
    if safe_get(run, 'crash_detected', 0):
        print("⚠️  CRASH DETECTED: Yes")
        print()
    
    if safe_get(run, 'rate_limit_fail', 0):
        print("⚠️  RATE LIMIT FAIL: Yes")
        print()
    
    # Get steps for this run
    steps_cursor = conn.execute("""
        SELECT * FROM steps 
        WHERE run_id = ? 
        ORDER BY step_idx ASC
    """, (safe_get(run, 'run_id'),))
    
    steps = steps_cursor.fetchall()
    
    if steps:
        print("📝 STEPS DETAILS")
        print("-" * 80)
        for i, step in enumerate(steps, 1):
            print(f"\nStep {i}:")
            action_type = safe_get(step, 'action_type', 'N/A')
            subgoal = safe_get(step, 'subgoal', 'N/A')
            action_source = safe_get(step, 'action_source', 'N/A')
            intended_success = safe_get(step, 'intended_success', 0)
            error_type = safe_get(step, 'error_type')
            before_png = safe_get(step, 'before_png')
            after_png = safe_get(step, 'after_png')
            ui_xml = safe_get(step, 'ui_xml')
            
            print(f"  Action:        {action_type}")
            print(f"  Description:   {subgoal}")
            print(f"  Source:        {action_source}")
            print(f"  Success:       {bool(intended_success)}")
            
            if error_type:
                print(f"  Error:         {error_type}")
            if before_png:
                print(f"  Before Screenshot: {before_png}")
            if after_png:
                print(f"  After Screenshot:  {after_png}")
            if ui_xml:
                print(f"  UI XML:        {ui_xml}")
        print()
    
    # Get assertions for this run
    assertions_cursor = conn.execute("""
        SELECT * FROM assertions 
        WHERE run_id = ? 
        ORDER BY step_idx ASC
    """, (safe_get(run, 'run_id'),))
    
    assertions = assertions_cursor.fetchall()
    
    if assertions:
        print("✅ ASSERTIONS")
        print("-" * 80)
        for i, assertion in enumerate(assertions, 1):
            passed = safe_get(assertion, 'passed', 0)
            status = "✓" if passed else "✗"
            assertion_type = safe_get(assertion, 'assertion_type', 'N/A')
            expected = safe_get(assertion, 'expected', 'N/A')
            observed = safe_get(assertion, 'observed', 'N/A')
            print(f"{status} {assertion_type}: {expected} → {observed}")
        print()
    
    # Config
    config_json = safe_get(run, 'config_json')
    if config_json:
        try:
            config = json.loads(config_json)
            print("⚙️  CONFIGURATION")
            print("-" * 80)
            for key, value in config.items():
                print(f"  {key}: {value}")
            print()
        except:
            pass
    
    print("=" * 80)
    
    conn.close()

def list_recent_runs(db_path: str = "benchmark.db", limit: int = 10):
    """List recent runs"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute("""
        SELECT run_id, experiment_id, test_id, reasoning_llm_model, 
               final_status, steps_count, cost_usd, started_at
        FROM runs 
        ORDER BY started_at DESC 
        LIMIT ?
    """, (limit,))
    
    runs = cursor.fetchall()
    
    if not runs:
        print("❌ No runs found in database")
        conn.close()
        return
    
    print("=" * 100)
    print(f"RECENT RUNS (Last {limit})")
    print("=" * 100)
    print()
    print(f"{'Run ID':<12} {'Test':<6} {'Model':<25} {'Status':<8} {'Steps':<8} {'Cost':<12} {'Started':<20}")
    print("-" * 100)
    
    for run in runs:
        run_id_full = safe_get(run, 'run_id', '')
        run_id_short = run_id_full[:8] + "..." if len(run_id_full) > 8 else run_id_full
        model = safe_get(run, 'reasoning_llm_model', 'N/A')
        if len(model) > 24:
            model = model[:24]
        status = safe_get(run, 'final_status', 'N/A')
        steps = safe_get(run, 'steps_count', 0) or 0
        cost = safe_get(run, 'cost_usd', 0.0) or 0.0
        cost_str = f"${cost:.4f}"
        started = format_datetime(safe_get(run, 'started_at'))
        test_id = safe_get(run, 'test_id', 'N/A')
        
        print(f"{run_id_short:<12} {test_id:<6} {model:<25} {status:<8} {steps:<8} {cost_str:<12} {started:<20}")
    
    print()
    print("=" * 100)
    
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="View latest test run from database")
    parser.add_argument("--db", type=str, default="benchmark.db", help="Database path")
    parser.add_argument("--run-id", type=str, help="View specific run by ID")
    parser.add_argument("--list", type=int, metavar="N", help="List recent N runs")
    
    args = parser.parse_args()
    
    if args.list:
        list_recent_runs(args.db, args.list)
    else:
        show_latest_run(args.db, args.run_id)

if __name__ == "__main__":
    main()
