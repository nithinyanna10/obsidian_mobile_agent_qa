#!/usr/bin/env python3
"""
Batch Analysis Script
Analyzes multiple test runs for performance comparison
"""
import sys
import argparse
from tools.batch_analysis import analyze_batch

def main():
    parser = argparse.ArgumentParser(description="Analyze batch test results")
    parser.add_argument("--results-dir", default="results", help="Directory containing episode files")
    parser.add_argument("--pattern", default="*.json", help="File pattern to match")
    parser.add_argument("--export", help="Export results to JSON file")
    
    args = parser.parse_args()
    
    analyze_batch(
        results_dir=args.results_dir,
        pattern=args.pattern,
        export=args.export
    )

if __name__ == "__main__":
    main()
