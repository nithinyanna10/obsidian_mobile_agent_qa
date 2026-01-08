"""
Benchmark Runner - Run multiple trials of tests with logging
"""
import argparse
from datetime import datetime
from main import run_test_suite
from tools.benchmark_logger import BenchmarkLogger
from tools.metrics_computer import MetricsComputer
from config import OPENAI_MODEL
import json


def run_benchmark(
    model: str,
    experiment_id: str,
    num_trials: int = 5,
    db_path: str = "benchmark.db"
):
    """
    Run benchmark with multiple trials
    
    Args:
        model: Model identifier (e.g., "gpt-4o", "gpt-4o-mini")
        experiment_id: Experiment identifier
        num_trials: Number of trials per test
        db_path: Path to SQLite database
    """
    logger = BenchmarkLogger(db_path=db_path, experiment_id=experiment_id)
    
    from tests.qa_tests import QA_TESTS
    
    config = {
        "max_steps": 20,
        "temperature": 0.1,
        "model": OPENAI_MODEL
    }
    
    print(f"\n{'=' * 80}")
    print(f"BENCHMARK: {experiment_id}")
    print(f"Model: {model}")
    print(f"Trials per test: {num_trials}")
    print(f"{'=' * 80}\n")
    
    for test in QA_TESTS:
        test_id = test["id"]
        should = "PASS" if test["should_pass"] else "FAIL"
        
        print(f"\n{'=' * 80}")
        print(f"Test {test_id}: {test['text']}")
        print(f"Expected: {should}")
        print(f"Running {num_trials} trials...")
        print(f"{'=' * 80}\n")
        
        for trial in range(1, num_trials + 1):
            print(f"\n--- Trial {trial}/{num_trials} ---\n")
            
            # Start run logging
            run_id = logger.start_run(
                trial_num=trial,
                model=model,
                test_id=test_id,
                should=should,
                config=config
            )
            
            try:
                # Run the test (this will need to be modified to integrate with logger)
                # For now, we'll call the existing run_test_suite but need to integrate logging
                result = run_single_test_with_logging(test, logger)
                
                # End run logging
                final_status = "PASS" if result.get("passed") else "FAIL"
                failure_reason = result.get("failure_reason")
                
                logger.end_run(final_status=final_status, failure_reason=failure_reason)
                
            except Exception as e:
                logger.end_run(
                    final_status="FAIL",
                    failure_reason=f"EXCEPTION: {str(e)}"
                )
                print(f"❌ Trial {trial} failed with exception: {e}")
    
    logger.close()
    
    # Compute and print metrics
    print(f"\n{'=' * 80}")
    print("COMPUTING METRICS...")
    print(f"{'=' * 80}\n")
    
    computer = MetricsComputer(db_path)
    computer.print_metrics_report(experiment_id=experiment_id, model=model)


def run_single_test_with_logging(test, logger):
    """Run a single test with logging integrated"""
    # This is a placeholder - you'll need to integrate logger into main.py
    # For now, just call the existing function
    from main import run_test_suite
    # TODO: Integrate logger into the main execution loop
    return {"passed": False, "failure_reason": "NOT_IMPLEMENTED"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run QA agent benchmark")
    parser.add_argument("--model", type=str, required=True, help="Model identifier")
    parser.add_argument("--experiment-id", type=str, help="Experiment ID (default: auto-generated)")
    parser.add_argument("--trials", type=int, default=5, help="Number of trials per test")
    parser.add_argument("--db", type=str, default="benchmark.db", help="Database path")
    
    args = parser.parse_args()
    
    experiment_id = args.experiment_id or f"bench_v1_{datetime.now().strftime('%Y_%m_%d')}"
    
    run_benchmark(
        model=args.model,
        experiment_id=experiment_id,
        num_trials=args.trials,
        db_path=args.db
    )

