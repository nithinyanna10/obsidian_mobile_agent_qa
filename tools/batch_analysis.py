"""
Batch Analysis Tools
Analyzes multiple test runs for performance comparison
"""
import json
import os
import glob
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime

class BatchAnalyzer:
    """Analyzes batch test results"""
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = results_dir
    
    def analyze_episodes(self, pattern: str = "*.json") -> Dict[str, Any]:
        """
        Analyze all episodes matching pattern
        
        Args:
            pattern: File pattern to match (e.g., "*.json", "test_*.json")
            
        Returns:
            Analysis results
        """
        episode_files = glob.glob(os.path.join(self.results_dir, pattern))
        
        if not episode_files:
            print(f"⚠️  No episode files found matching: {pattern}")
            return {}
        
        print(f"Analyzing {len(episode_files)} episodes...")
        
        results = {
            "total_episodes": len(episode_files),
            "successful": 0,
            "failed": 0,
            "errors": 0,
            "total_steps": 0,
            "avg_steps": 0.0,
            "test_breakdown": defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "avg_steps": 0.0}),
            "model_breakdown": defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "avg_steps": 0.0}),
            "episodes": []
        }
        
        for episode_file in episode_files:
            try:
                with open(episode_file, 'r') as f:
                    episode_data = json.load(f)
                
                test_id = episode_data.get("test_id", "unknown")
                status = episode_data.get("status", "UNKNOWN")
                steps = episode_data.get("steps_taken", 0)
                model = episode_data.get("model", "unknown")
                
                results["total_steps"] += steps
                
                # Update test breakdown
                test_breakdown = results["test_breakdown"][test_id]
                test_breakdown["total"] += 1
                if status == "PASS":
                    test_breakdown["passed"] += 1
                    results["successful"] += 1
                elif status == "FAIL":
                    test_breakdown["failed"] += 1
                    results["failed"] += 1
                else:
                    results["errors"] += 1
                
                # Update model breakdown
                model_breakdown = results["model_breakdown"][model]
                model_breakdown["total"] += 1
                if status == "PASS":
                    model_breakdown["passed"] += 1
                elif status == "FAIL":
                    model_breakdown["failed"] += 1
                
                results["episodes"].append({
                    "file": os.path.basename(episode_file),
                    "test_id": test_id,
                    "status": status,
                    "steps": steps,
                    "model": model
                })
            except Exception as e:
                print(f"⚠️  Error analyzing {episode_file}: {e}")
                results["errors"] += 1
        
        # Calculate averages
        if results["total_episodes"] > 0:
            results["avg_steps"] = results["total_steps"] / results["total_episodes"]
        
        # Calculate test averages
        for test_id, breakdown in results["test_breakdown"].items():
            if breakdown["total"] > 0:
                total_steps = sum(e["steps"] for e in results["episodes"] if e["test_id"] == test_id)
                breakdown["avg_steps"] = total_steps / breakdown["total"]
        
        # Calculate model averages
        for model, breakdown in results["model_breakdown"].items():
            if breakdown["total"] > 0:
                total_steps = sum(e["steps"] for e in results["episodes"] if e["model"] == model)
                breakdown["avg_steps"] = total_steps / breakdown["total"]
        
        return results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print analysis summary"""
        print("=" * 60)
        print("BATCH ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Total Episodes: {results['total_episodes']}")
        print(f"Successful: {results['successful']} ({results['successful']/results['total_episodes']*100:.1f}%)")
        print(f"Failed: {results['failed']} ({results['failed']/results['total_episodes']*100:.1f}%)")
        print(f"Errors: {results['errors']}")
        print(f"Average Steps: {results['avg_steps']:.1f}")
        print()
        
        print("Test Breakdown:")
        for test_id, breakdown in results["test_breakdown"].items():
            pass_rate = (breakdown["passed"] / breakdown["total"] * 100) if breakdown["total"] > 0 else 0
            print(f"  Test {test_id}: {breakdown['passed']}/{breakdown['total']} passed ({pass_rate:.1f}%) - Avg steps: {breakdown['avg_steps']:.1f}")
        print()
        
        print("Model Breakdown:")
        for model, breakdown in results["model_breakdown"].items():
            pass_rate = (breakdown["passed"] / breakdown["total"] * 100) if breakdown["total"] > 0 else 0
            print(f"  {model}: {breakdown['passed']}/{breakdown['total']} passed ({pass_rate:.1f}%) - Avg steps: {breakdown['avg_steps']:.1f}")
        print("=" * 60)
    
    def compare_models(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare performance across different models"""
        comparison = {}
        
        for model, breakdown in results["model_breakdown"].items():
            comparison[model] = {
                "pass_rate": (breakdown["passed"] / breakdown["total"] * 100) if breakdown["total"] > 0 else 0,
                "avg_steps": breakdown["avg_steps"],
                "total_runs": breakdown["total"]
            }
        
        return comparison
    
    def export_results(self, results: Dict[str, Any], output_path: str):
        """Export analysis results to JSON"""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"✓ Results exported to: {output_path}")


def analyze_batch(results_dir: str = "results", pattern: str = "*.json", export: Optional[str] = None):
    """
    Convenience function to analyze batch results
    
    Args:
        results_dir: Directory containing episode files
        pattern: File pattern to match
        export: Optional path to export results JSON
    """
    analyzer = BatchAnalyzer(results_dir)
    results = analyzer.analyze_episodes(pattern)
    
    if results:
        analyzer.print_summary(results)
        
        if export:
            analyzer.export_results(results, export)
    
    return results
