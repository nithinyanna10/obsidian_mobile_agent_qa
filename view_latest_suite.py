#!/usr/bin/env python3
"""
View Latest Test Suite - Shows the most recent complete test suite run (all tests together)
"""
import sqlite3
import argparse
import json
from datetime import datetime
from collections import defaultdict

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

def show_latest_suite(db_path: str = "benchmark.db", experiment_id: str = None, trial_num: int = None):
    """Show the latest complete test suite run"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Get latest test suite (grouped by experiment_id and trial_num)
    if experiment_id and trial_num:
        cursor = conn.execute("""
            SELECT * FROM runs 
            WHERE experiment_id = ? AND trial_num = ?
            ORDER BY test_id ASC
        """, (experiment_id, trial_num))
    else:
        # Get the latest experiment_id and trial_num
        latest = conn.execute("""
            SELECT experiment_id, trial_num, MAX(started_at) as max_start
            FROM runs
            GROUP BY experiment_id, trial_num
            ORDER BY max_start DESC
            LIMIT 1
        """).fetchone()
        
        if not latest:
            print("❌ No test suites found in database")
            conn.close()
            return
        
        cursor = conn.execute("""
            SELECT * FROM runs 
            WHERE experiment_id = ? AND trial_num = ?
            ORDER BY test_id ASC
        """, (latest['experiment_id'], latest['trial_num']))
    
    runs = cursor.fetchall()
    
    if not runs:
        print("❌ No test suite found")
        conn.close()
        return
    
    # Get suite metadata from first run
    first_run = runs[0]
    experiment_id = safe_get(first_run, 'experiment_id')
    trial_num = safe_get(first_run, 'trial_num')
    
    # Calculate suite-level metrics
    suite_start = min(safe_get(r, 'started_at') or '' for r in runs)
    suite_end = max(safe_get(r, 'ended_at') or '' for r in runs)
    
    total_steps = sum(safe_get(r, 'steps_count', 0) or 0 for r in runs)
    total_tokens_in = sum(safe_get(r, 'tokens_in', 0) or 0 for r in runs)
    total_tokens_out = sum(safe_get(r, 'tokens_out', 0) or 0 for r in runs)
    total_api_calls = sum(safe_get(r, 'api_calls', 0) or 0 for r in runs)
    total_cost = sum(safe_get(r, 'cost_usd', 0.0) or 0.0 for r in runs)
    
    # Calculate duration
    if suite_start and suite_end:
        try:
            start_dt = datetime.fromisoformat(suite_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(suite_end.replace('Z', '+00:00'))
            suite_duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
            suite_duration_sec = suite_duration_ms / 1000.0
        except:
            suite_duration_ms = 0
            suite_duration_sec = 0.0
    else:
        suite_duration_ms = 0
        suite_duration_sec = 0.0
    
    # Count results
    passed = sum(1 for r in runs if safe_get(r, 'final_status') == 'PASS')
    failed = sum(1 for r in runs if safe_get(r, 'final_status') == 'FAIL')
    errors = sum(1 for r in runs if safe_get(r, 'final_status') in ['ERROR', 'EXECUTION_ERROR'])
    
    print("=" * 80)
    print("LATEST TEST SUITE RUN")
    print("=" * 80)
    print()
    
    # Suite Information
    print("📊 SUITE INFORMATION")
    print("-" * 80)
    print(f"Experiment:    {experiment_id}")
    print(f"Trial:         {trial_num}")
    print(f"Total Tests:   {len(runs)}")
    print(f"Started:       {format_datetime(suite_start)}")
    print(f"Ended:         {format_datetime(suite_end)}")
    print(f"Duration:      {suite_duration_sec:.2f} seconds ({suite_duration_ms} ms)")
    print()
    
    # Results Summary
    print("📈 RESULTS SUMMARY")
    print("-" * 80)
    print(f"Passed:        {passed} ({passed/len(runs)*100:.1f}%)")
    print(f"Failed:        {failed} ({failed/len(runs)*100:.1f}%)")
    print(f"Errors:        {errors}")
    print()
    
    # Model Information (from first run - should be same for all)
    print("🤖 MODEL INFORMATION")
    print("-" * 80)
    reasoning_model = safe_get(first_run, 'reasoning_llm_model', 'N/A')
    reasoning_provider = safe_get(first_run, 'reasoning_llm_provider', 'N/A')
    vision_model = safe_get(first_run, 'vision_llm_model', 'N/A')
    vision_provider = safe_get(first_run, 'vision_llm_provider', 'N/A')
    print(f"Reasoning Model:  {reasoning_model} ({reasoning_provider})")
    print(f"Vision Model:     {vision_model} ({vision_provider})")
    print()
    
    # Performance Metrics
    print("⚡ PERFORMANCE METRICS")
    print("-" * 80)
    print(f"Total Steps:    {total_steps}")
    print(f"Total Duration: {suite_duration_sec:.2f} seconds")
    print(f"Total API Calls: {total_api_calls}")
    print(f"Total Tokens In:  {total_tokens_in:,}")
    print(f"Total Tokens Out: {total_tokens_out:,}")
    print(f"Total Tokens:     {total_tokens_in + total_tokens_out:,}")
    print(f"Total Cost:       ${total_cost:.6f}")
    print(f"Avg Cost/Test:    ${total_cost/len(runs):.6f}")
    print()
    
    # Individual Test Results
    print("🧪 INDIVIDUAL TEST RESULTS")
    print("-" * 80)
    print(f"{'Test':<6} {'Expected':<10} {'Status':<8} {'Steps':<8} {'Duration':<12} {'Cost':<12} {'Result'}")
    print("-" * 80)
    
    for run in runs:
        test_id = safe_get(run, 'test_id', 'N/A')
        expected = safe_get(run, 'should', 'N/A')
        status = safe_get(run, 'final_status', 'N/A')
        steps = safe_get(run, 'steps_count', 0) or 0
        duration_ms = safe_get(run, 'duration_ms', 0) or 0
        duration_sec = duration_ms / 1000.0
        cost = safe_get(run, 'cost_usd', 0.0) or 0.0
        
        # Determine result icon
        if status == 'PASS' and expected == 'PASS':
            result_icon = "✓ PASS"
        elif status == 'FAIL' and expected == 'FAIL':
            result_icon = "✓ CORRECT FAIL"
        elif status == 'PASS' and expected == 'FAIL':
            result_icon = "✗ UNEXPECTED PASS"
        elif status == 'FAIL' and expected == 'PASS':
            result_icon = "✗ FAILED"
        else:
            result_icon = f"? {status}"
        
        print(f"{test_id:<6} {expected:<10} {status:<8} {steps:<8} {duration_sec:>10.2f}s  ${cost:>10.6f}  {result_icon}")
    
    print()
    
    # Detailed Test Information
    print("📝 DETAILED TEST INFORMATION")
    print("-" * 80)
    
    for run in runs:
        test_id = safe_get(run, 'test_id', 'N/A')
        status = safe_get(run, 'final_status', 'N/A')
        failure_reason = safe_get(run, 'failure_reason')
        steps = safe_get(run, 'steps_count', 0) or 0
        duration_ms = safe_get(run, 'duration_ms', 0) or 0
        cost = safe_get(run, 'cost_usd', 0.0) or 0.0
        
        print(f"\nTest {test_id} ({status}):")
        print(f"  Steps: {steps}, Duration: {duration_ms/1000:.2f}s, Cost: ${cost:.6f}")
        
        if failure_reason:
            print(f"  Failure Reason: {failure_reason}")
        
        # Get steps for this test
        run_id = safe_get(run, 'run_id')
        steps_cursor = conn.execute("""
            SELECT COUNT(*) as step_count FROM steps WHERE run_id = ?
        """, (run_id,))
        step_count = steps_cursor.fetchone()[0]
        print(f"  Actions Logged: {step_count}")
    
    print()
    print("=" * 80)
    
    conn.close()

def list_recent_suites(db_path: str = "benchmark.db", limit: int = 10):
    """List recent test suite runs"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute("""
        SELECT experiment_id, trial_num, 
               COUNT(*) as test_count,
               SUM(CASE WHEN final_status='PASS' THEN 1 ELSE 0 END) as passed,
               SUM(CASE WHEN final_status='FAIL' THEN 1 ELSE 0 END) as failed,
               MIN(started_at) as suite_start,
               MAX(ended_at) as suite_end,
               SUM(steps_count) as total_steps,
               SUM(cost_usd) as total_cost
        FROM runs
        GROUP BY experiment_id, trial_num
        ORDER BY suite_start DESC
        LIMIT ?
    """, (limit,))
    
    suites = cursor.fetchall()
    
    if not suites:
        print("❌ No test suites found in database")
        conn.close()
        return
    
    print("=" * 120)
    print(f"RECENT TEST SUITE RUNS (Last {limit})")
    print("=" * 120)
    print()
    print(f"{'Experiment':<25} {'Trial':<8} {'Tests':<8} {'Passed':<8} {'Failed':<8} {'Steps':<8} {'Cost':<12} {'Started':<20}")
    print("-" * 120)
    
    for suite in suites:
        exp_id = safe_get(suite, 'experiment_id', 'N/A')
        if len(exp_id) > 24:
            exp_id = exp_id[:21] + "..."
        trial = safe_get(suite, 'trial_num', 'N/A')
        test_count = safe_get(suite, 'test_count', 0)
        passed = safe_get(suite, 'passed', 0)
        failed = safe_get(suite, 'failed', 0)
        total_steps = safe_get(suite, 'total_steps', 0) or 0
        total_cost = safe_get(suite, 'total_cost', 0.0) or 0.0
        started = format_datetime(safe_get(suite, 'suite_start'))
        
        print(f"{exp_id:<25} {trial:<8} {test_count:<8} {passed:<8} {failed:<8} {total_steps:<8} ${total_cost:>10.6f}  {started:<20}")
    
    print()
    print("=" * 120)
    
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="View latest test suite run (all tests together)")
    parser.add_argument("--db", type=str, default="benchmark.db", help="Database path")
    parser.add_argument("--experiment", type=str, help="View specific experiment")
    parser.add_argument("--trial", type=int, help="View specific trial number")
    parser.add_argument("--list", type=int, metavar="N", help="List recent N test suites")
    
    args = parser.parse_args()
    
    if args.list:
        list_recent_suites(args.db, args.list)
    else:
        show_latest_suite(args.db, args.experiment, args.trial)

if __name__ == "__main__":
    main()
