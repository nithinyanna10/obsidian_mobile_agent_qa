"""
View Benchmark Metrics - Display metrics from SQLite database
"""
import argparse
from tools.metrics_computer import MetricsComputer


def main():
    parser = argparse.ArgumentParser(description="View benchmark metrics")
    parser.add_argument("--db", type=str, default="benchmark.db", help="Database path")
    parser.add_argument("--experiment-id", type=str, help="Filter by experiment ID")
    parser.add_argument("--model", type=str, help="Filter by model")
    
    args = parser.parse_args()
    
    computer = MetricsComputer(db_path=args.db)
    computer.print_metrics_report(
        experiment_id=args.experiment_id,
        model=args.model
    )


if __name__ == "__main__":
    main()

