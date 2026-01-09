"""
Run benchmark for a specific reasoning model
Runs 5 trials and stores results in database
"""
import argparse
import sys
from main import run_test_suite
from config import OPENAI_MODEL, REASONING_MODEL, OLLAMA_BASE_URL
import time


def main():
    parser = argparse.ArgumentParser(description="Benchmark a reasoning model")
    parser.add_argument("--reasoning-model", type=str, required=True,
                       help="Reasoning model name (e.g., 'nemotron-3-nano:30b-cloud' or 'gpt-4o')")
    parser.add_argument("--vision-model", type=str, default=OPENAI_MODEL,
                       help=f"Vision model (default: {OPENAI_MODEL})")
    parser.add_argument("--trials", type=int, default=5,
                       help="Number of trials to run (default: 5)")
    parser.add_argument("--experiment-id", type=str, default=None,
                       help="Experiment ID (default: auto-generated)")
    parser.add_argument("--ollama-url", type=str, default=OLLAMA_BASE_URL,
                       help=f"Ollama base URL (default: {OLLAMA_BASE_URL})")
    
    args = parser.parse_args()
    
    # Generate experiment ID if not provided
    from datetime import datetime
    if not args.experiment_id:
        model_short = args.reasoning_model.replace(":", "_").replace("-", "_")
        args.experiment_id = f"bench_{model_short}_{datetime.now().strftime('%Y_%m_%d')}"
    
    print("=" * 80)
    print("BENCHMARK RUNNER")
    print("=" * 80)
    print(f"Vision Model: {args.vision_model} (OpenAI)")
    print(f"Reasoning Model: {args.reasoning_model}")
    print(f"Trials: {args.trials}")
    print(f"Experiment ID: {args.experiment_id}")
    print(f"Ollama URL: {args.ollama_url}")
    print("=" * 80)
    print()
    
    # Set environment variables for the run
    import os
    os.environ["REASONING_MODEL"] = args.reasoning_model
    os.environ["OLLAMA_BASE_URL"] = args.ollama_url
    
    # Run trials
    for trial in range(1, args.trials + 1):
        print(f"\n{'=' * 80}")
        print(f"TRIAL {trial}/{args.trials}")
        print(f"{'=' * 80}\n")
        
        try:
            run_test_suite(
                model=args.reasoning_model,
                experiment_id=args.experiment_id,
                trial_num=trial,
                enable_logging=True
            )
            
            print(f"\n✓ Trial {trial} completed")
            
            # Brief pause between trials
            if trial < args.trials:
                print("Waiting 5 seconds before next trial...")
                time.sleep(5)
        
        except Exception as e:
            print(f"\n❌ Trial {trial} failed: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n{'=' * 80}")
    print("BENCHMARK COMPLETE")
    print(f"{'=' * 80}")
    print(f"Experiment ID: {args.experiment_id}")
    print(f"Trials completed: {args.trials}")
    print(f"\nView results with: python view_metrics.py --experiment-id {args.experiment_id}")


if __name__ == "__main__":
    main()


