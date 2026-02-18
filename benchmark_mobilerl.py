#!/usr/bin/env python3
"""
Benchmark GLM-4.1V-9B (MobileRL) vs GPT-4o baseline
Compares performance on Obsidian Mobile QA tests
"""
import os
import sys
import argparse
from datetime import datetime
from main import run_test_suite
from tools.benchmark_logger import BenchmarkLogger
from tools.benchmark_db import BenchmarkDB


def run_benchmark_comparison():
    """Run benchmark comparison between GLM-4.1V-9B and GPT-4o"""
    
    parser = argparse.ArgumentParser(description='Benchmark GLM-4.1V-9B vs GPT-4o')
    parser.add_argument(
        '--mobilerl-model',
        type=str,
        default='Tongyi-MAI/MAI-UI-2B',
        help='MobileRL model identifier (default: Tongyi-MAI/MAI-UI-2B)'
    )
    parser.add_argument(
        '--device',
        type=str,
        default=None,
        help='Device for MobileRL (cuda/cpu, default: auto-detect)'
    )
    parser.add_argument(
        '--baseline-model',
        type=str,
        default='gpt-4o',
        help='Baseline model for comparison (default: gpt-4o)'
    )
    parser.add_argument(
        '--trials',
        type=int,
        default=1,
        help='Number of trials per model (default: 1)'
    )
    parser.add_argument(
        '--skip-baseline',
        action='store_true',
        help='Skip baseline run (only run MobileRL)'
    )
    parser.add_argument(
        '--skip-mobilerl',
        action='store_true',
        help='Skip MobileRL run (only run baseline)'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("MobileRL Benchmark: GLM-4.1V-9B vs GPT-4o")
    print("=" * 80)
    print()
    
    results = {}
    experiment_id = f"mobilerl_bench_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run baseline (GPT-4o)
    if not args.skip_baseline:
        print("\n" + "=" * 80)
        print("RUNNING BASELINE: GPT-4o")
        print("=" * 80)
        print()
        
        # Set environment for baseline (temporary, only for this run)
        original_reasoning_model = os.environ.get("REASONING_MODEL")
        original_disable_rl = os.environ.get("DISABLE_RL_FOR_BENCHMARKING")
        
        os.environ["REASONING_MODEL"] = args.baseline_model
        os.environ["DISABLE_RL_FOR_BENCHMARKING"] = "true"  # Fair comparison
        
        baseline_results = []
        for trial in range(1, args.trials + 1):
            print(f"\n--- Baseline Trial {trial}/{args.trials} ---\n")
            # Uses existing run_test_suite() - stores to existing benchmark.db
            trial_results = run_test_suite(
                model=args.baseline_model,
                experiment_id=f"{experiment_id}_baseline",
                trial_num=trial,
                enable_logging=True  # Uses existing BenchmarkLogger -> existing DB
            )
            baseline_results.append(trial_results)
        
        # Restore original environment
        if original_reasoning_model:
            os.environ["REASONING_MODEL"] = original_reasoning_model
        elif "REASONING_MODEL" in os.environ:
            del os.environ["REASONING_MODEL"]
        
        if original_disable_rl:
            os.environ["DISABLE_RL_FOR_BENCHMARKING"] = original_disable_rl
        elif "DISABLE_RL_FOR_BENCHMARKING" in os.environ:
            del os.environ["DISABLE_RL_FOR_BENCHMARKING"]
        
        results["baseline"] = {
            "model": args.baseline_model,
            "trials": baseline_results,
            "experiment_id": f"{experiment_id}_baseline"
        }
        
        print("\n✓ Baseline runs completed (stored in benchmark.db)")
    
    # Run MobileRL (GLM-4.1V-9B)
    if not args.skip_mobilerl:
        print("\n" + "=" * 80)
        print("RUNNING MOBILERL: GLM-4.1V-9B")
        print("=" * 80)
        print()
        
        # Set environment for MobileRL (temporary, only for this run)
        original_reasoning_model = os.environ.get("REASONING_MODEL")
        original_disable_rl = os.environ.get("DISABLE_RL_FOR_BENCHMARKING")
        original_device = os.environ.get("MOBILERL_DEVICE")
        
        os.environ["REASONING_MODEL"] = args.mobilerl_model
        if args.device:
            os.environ["MOBILERL_DEVICE"] = args.device
        os.environ["DISABLE_RL_FOR_BENCHMARKING"] = "true"  # Fair comparison
        
        mobilerl_results = []
        for trial in range(1, args.trials + 1):
            print(f"\n--- MobileRL Trial {trial}/{args.trials} ---\n")
            # Uses existing run_test_suite() - stores to existing benchmark.db
            trial_results = run_test_suite(
                model=args.mobilerl_model,
                experiment_id=f"{experiment_id}_mobilerl",
                trial_num=trial,
                enable_logging=True  # Uses existing BenchmarkLogger -> existing DB
            )
            mobilerl_results.append(trial_results)
        
        # Restore original environment
        if original_reasoning_model:
            os.environ["REASONING_MODEL"] = original_reasoning_model
        elif "REASONING_MODEL" in os.environ:
            del os.environ["REASONING_MODEL"]
        
        if original_disable_rl:
            os.environ["DISABLE_RL_FOR_BENCHMARKING"] = original_disable_rl
        elif "DISABLE_RL_FOR_BENCHMARKING" in os.environ:
            del os.environ["DISABLE_RL_FOR_BENCHMARKING"]
        
        if original_device:
            os.environ["MOBILERL_DEVICE"] = original_device
        elif "MOBILERL_DEVICE" in os.environ:
            del os.environ["MOBILERL_DEVICE"]
        
        results["mobilerl"] = {
            "model": args.mobilerl_model,
            "trials": mobilerl_results,
            "experiment_id": f"{experiment_id}_mobilerl"
        }
        
        print("\n✓ MobileRL runs completed (stored in benchmark.db)")
    
    # Generate comparison report
    print("\n" + "=" * 80)
    print("BENCHMARK COMPARISON REPORT")
    print("=" * 80)
    print()
    
    if "baseline" in results and "mobilerl" in results:
        generate_comparison_report(results, experiment_id)
    elif "baseline" in results:
        generate_single_report(results["baseline"], "Baseline")
    elif "mobilerl" in results:
        generate_single_report(results["mobilerl"], "MobileRL")
    
    print("\n" + "=" * 80)
    print("Benchmark completed!")
    print("=" * 80)
    print(f"\nExperiment ID: {experiment_id}")
    print("View results in benchmark.db using:")
    print(f"  python view_latest_suite.py")


def generate_comparison_report(results, experiment_id):
    """Generate comparison report between baseline and MobileRL"""
    
    baseline = results["baseline"]
    mobilerl = results["mobilerl"]
    
    # Aggregate results across trials
    baseline_aggregate = aggregate_trial_results(baseline["trials"])
    mobilerl_aggregate = aggregate_trial_results(mobilerl["trials"])
    
    print(f"Baseline Model: {baseline['model']}")
    print(f"MobileRL Model: {mobilerl['model']}")
    print()
    
    # Test-by-test comparison
    print("TEST-BY-TEST COMPARISON:")
    print("-" * 80)
    
    test_ids = sorted(set(baseline_aggregate.keys()) | set(mobilerl_aggregate.keys()))
    
    for test_id in test_ids:
        baseline_test = baseline_aggregate.get(test_id, {})
        mobilerl_test = mobilerl_aggregate.get(test_id, {})
        
        baseline_status = baseline_test.get("status", "UNKNOWN")
        mobilerl_status = mobilerl_test.get("status", "UNKNOWN")
        
        baseline_steps = baseline_test.get("avg_steps", 0)
        mobilerl_steps = mobilerl_test.get("avg_steps", 0)
        
        print(f"\nTest {test_id}:")
        print(f"  Baseline: {baseline_status} ({baseline_steps:.1f} steps avg)")
        print(f"  MobileRL: {mobilerl_status} ({mobilerl_steps:.1f} steps avg)")
        
        if baseline_status == "PASS" and mobilerl_status == "PASS":
            print(f"  ✓ Both passed")
        elif baseline_status != "PASS" and mobilerl_status == "PASS":
            print(f"  🎯 MobileRL improved!")
        elif baseline_status == "PASS" and mobilerl_status != "PASS":
            print(f"  ⚠️  MobileRL regressed")
    
    # Overall metrics
    print("\n" + "-" * 80)
    print("OVERALL METRICS:")
    print("-" * 80)
    
    baseline_pass_rate = calculate_pass_rate(baseline_aggregate)
    mobilerl_pass_rate = calculate_pass_rate(mobilerl_aggregate)
    
    baseline_avg_steps = calculate_avg_steps(baseline_aggregate)
    mobilerl_avg_steps = calculate_avg_steps(mobilerl_aggregate)
    
    print(f"\nSuccess Rate:")
    print(f"  Baseline: {baseline_pass_rate:.1f}%")
    print(f"  MobileRL: {mobilerl_pass_rate:.1f}%")
    print(f"  Difference: {mobilerl_pass_rate - baseline_pass_rate:+.1f}%")
    
    print(f"\nAverage Steps per Test:")
    print(f"  Baseline: {baseline_avg_steps:.1f}")
    print(f"  MobileRL: {mobilerl_avg_steps:.1f}")
    print(f"  Difference: {mobilerl_avg_steps - baseline_avg_steps:+.1f}")
    
    # Query database for API cost comparison
    try:
        db = BenchmarkDB()
        
        baseline_runs = db.get_runs_by_experiment(baseline["experiment_id"])
        mobilerl_runs = db.get_runs_by_experiment(mobilerl["experiment_id"])
        
        baseline_cost = sum(r.get("cost_usd", 0) for r in baseline_runs) if baseline_runs else 0
        mobilerl_cost = sum(r.get("cost_usd", 0) for r in mobilerl_runs) if mobilerl_runs else 0
        
        print(f"\nCost (API calls):")
        print(f"  Baseline: ${baseline_cost:.6f}")
        print(f"  MobileRL: ${mobilerl_cost:.6f} (local inference - no API costs)")
        print(f"  Savings: ${baseline_cost - mobilerl_cost:.6f}")
        
    except Exception as e:
        print(f"\n⚠️  Could not fetch cost data: {e}")


def generate_single_report(results, label):
    """Generate report for single model"""
    aggregate = aggregate_trial_results(results["trials"])
    pass_rate = calculate_pass_rate(aggregate)
    avg_steps = calculate_avg_steps(aggregate)
    
    print(f"{label} Model: {results['model']}")
    print(f"Success Rate: {pass_rate:.1f}%")
    print(f"Average Steps: {avg_steps:.1f}")


def aggregate_trial_results(trials):
    """Aggregate results across multiple trials"""
    aggregated = {}
    
    for trial_results in trials:
        for test_result in trial_results:
            test_id = test_result.get("test_id")
            if not test_id:
                continue
            
            if test_id not in aggregated:
                aggregated[test_id] = {
                    "statuses": [],
                    "steps": [],
                    "test_text": test_result.get("test_text", "")
                }
            
            aggregated[test_id]["statuses"].append(test_result.get("status", "UNKNOWN"))
            aggregated[test_id]["steps"].append(test_result.get("steps_taken", 0))
    
    # Calculate averages
    for test_id, data in aggregated.items():
        statuses = data["statuses"]
        steps = data["steps"]
        
        # Most common status
        from collections import Counter
        status_counts = Counter(statuses)
        data["status"] = status_counts.most_common(1)[0][0] if status_counts else "UNKNOWN"
        data["avg_steps"] = sum(steps) / len(steps) if steps else 0
    
    return aggregated


def calculate_pass_rate(aggregate):
    """Calculate overall pass rate"""
    if not aggregate:
        return 0.0
    
    passed = sum(1 for data in aggregate.values() if data.get("status") == "PASS")
    total = len(aggregate)
    
    return (passed / total * 100) if total > 0 else 0.0


def calculate_avg_steps(aggregate):
    """Calculate average steps across all tests"""
    if not aggregate:
        return 0.0
    
    all_steps = [data.get("avg_steps", 0) for data in aggregate.values()]
    return sum(all_steps) / len(all_steps) if all_steps else 0.0


if __name__ == "__main__":
    run_benchmark_comparison()
