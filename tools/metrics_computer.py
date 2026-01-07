"""
Metrics Computer - Compute all benchmark metrics from SQLite database
"""
import sqlite3
from typing import Dict, List, Any, Optional
import statistics


class MetricsComputer:
    """Compute comprehensive metrics from benchmark database"""
    
    def __init__(self, db_path: str = "benchmark.db"):
        self.db_path = db_path
    
    def _get_conn(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def compute_all_metrics(
        self,
        experiment_id: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute all metrics"""
        conn = self._get_conn()
        
        where_clause = "WHERE 1=1"
        params = []
        
        if experiment_id:
            where_clause += " AND experiment_id = ?"
            params.append(experiment_id)
        if model:
            where_clause += " AND model = ?"
            params.append(model)
        
        metrics = {}
        
        # A) Test Pass Rate (Should-PASS)
        # Only count runs with non-NULL final_status
        pass_rate_rows = conn.execute(f"""
            SELECT model,
                   AVG(CASE WHEN final_status='PASS' THEN 1.0 ELSE 0.0 END) AS pass_rate,
                   COUNT(*) AS total_runs
            FROM runs
            {where_clause} AND should='PASS' AND final_status IS NOT NULL
            GROUP BY model
        """, params).fetchall()
        metrics["pass_rate"] = [dict(row) for row in pass_rate_rows]
        
        # B) Correct-Fail Detection Rate (Should-FAIL)
        # Only count runs with non-NULL final_status
        fail_rate_rows = conn.execute(f"""
            SELECT r.model,
                   AVG(
                     CASE WHEN r.final_status='FAIL' AND (
                          EXISTS (
                              SELECT 1 FROM assertions a
                              WHERE a.run_id=r.run_id AND a.passed=0
                          )
                          OR r.failure_reason IN ('ELEMENT_NOT_FOUND','ICON_COLOR_MISMATCH')
                     )
                     THEN 1.0 ELSE 0.0 END
                   ) AS correct_fail_rate,
                   COUNT(*) AS total_runs
            FROM runs r
            {where_clause} AND r.should='FAIL' AND r.final_status IS NOT NULL
            GROUP BY r.model
        """, params).fetchall()
        metrics["correct_fail_rate"] = [dict(row) for row in fail_rate_rows]
        
        # C) False Pass Rate
        # Only count runs with non-NULL final_status
        false_pass_rows = conn.execute(f"""
            SELECT model,
                   AVG(CASE WHEN final_status='PASS' THEN 1.0 ELSE 0.0 END) AS false_pass_rate,
                   COUNT(*) AS total_runs
            FROM runs
            {where_clause} AND should='FAIL' AND final_status IS NOT NULL
            GROUP BY model
        """, params).fetchall()
        metrics["false_pass_rate"] = [dict(row) for row in false_pass_rows]
        
        # D) False Fail Rate
        # Only count runs with non-NULL final_status
        false_fail_rows = conn.execute(f"""
            SELECT model,
                   AVG(CASE WHEN final_status='FAIL' THEN 1.0 ELSE 0.0 END) AS false_fail_rate,
                   COUNT(*) AS total_runs
            FROM runs
            {where_clause} AND should='PASS' AND final_status IS NOT NULL
            GROUP BY model
        """, params).fetchall()
        metrics["false_fail_rate"] = [dict(row) for row in false_fail_rows]
        
        # E) Steps per test (mean/median/p95)
        # Only count completed runs
        steps_data = conn.execute(f"""
            SELECT model, steps_count
            FROM runs
            {where_clause} AND final_status IS NOT NULL
            ORDER BY model, steps_count
        """, params).fetchall()
        
        steps_by_model = {}
        for row in steps_data:
            model = row["model"]
            steps_count = row["steps_count"]
            # Filter out None values
            if steps_count is not None:
                if model not in steps_by_model:
                    steps_by_model[model] = []
                steps_by_model[model].append(steps_count)
        
        metrics["steps_per_test"] = {}
        for model, steps_list in steps_by_model.items():
            if steps_list:  # Only compute if we have data
                metrics["steps_per_test"][model] = {
                    "mean": statistics.mean(steps_list),
                    "median": statistics.median(steps_list),
                    "p95": self._percentile(steps_list, 95)
                }
            else:
                metrics["steps_per_test"][model] = {
                    "mean": 0,
                    "median": 0,
                    "p95": 0
                }
        
        # F) Time per test (mean/median/p95)
        # Only count completed runs
        time_data = conn.execute(f"""
            SELECT model, duration_ms
            FROM runs
            {where_clause} AND final_status IS NOT NULL
            ORDER BY model, duration_ms
        """, params).fetchall()
        
        time_by_model = {}
        for row in time_data:
            model = row["model"]
            duration_ms = row["duration_ms"]
            # Filter out None values
            if duration_ms is not None:
                if model not in time_by_model:
                    time_by_model[model] = []
                time_by_model[model].append(duration_ms)
        
        metrics["time_per_test"] = {}
        for model, time_list in time_by_model.items():
            if time_list:  # Only compute if we have data
                metrics["time_per_test"][model] = {
                    "mean": statistics.mean(time_list),
                    "median": statistics.median(time_list),
                    "p95": self._percentile(time_list, 95)
                }
            else:
                metrics["time_per_test"][model] = {
                    "mean": 0,
                    "median": 0,
                    "p95": 0
                }
        
        # G) Retries per step
        retry_data = conn.execute(f"""
            SELECT r.model,
                   COUNT(*) FILTER (WHERE s.retry_idx > 0) AS retry_count,
                   COUNT(*) AS total_steps
            FROM steps s
            JOIN runs r ON r.run_id=s.run_id
            {where_clause.replace('runs', 'r')}
            GROUP BY r.model
        """, params).fetchall()
        metrics["retries_per_step"] = [dict(row) for row in retry_data]
        
        # H) Stuck/Loop rate
        # Only count completed runs
        stuck_rate_rows = conn.execute(f"""
            SELECT model,
                   AVG(CASE WHEN failure_reason='STUCK_LOOP' THEN 1.0 ELSE 0.0 END) AS stuck_rate,
                   COUNT(*) AS total_runs
            FROM runs
            {where_clause} AND final_status IS NOT NULL
            GROUP BY model
        """, params).fetchall()
        metrics["stuck_rate"] = [dict(row) for row in stuck_rate_rows]
        
        # I) Crash rate
        # Only count completed runs
        crash_rate_rows = conn.execute(f"""
            SELECT model,
                   AVG(CASE WHEN crash_detected=1 THEN 1.0 ELSE 0.0 END) AS crash_rate,
                   COUNT(*) AS total_runs
            FROM runs
            {where_clause} AND final_status IS NOT NULL
            GROUP BY model
        """, params).fetchall()
        metrics["crash_rate"] = [dict(row) for row in crash_rate_rows]
        
        # K) Tap success rate
        tap_success_rows = conn.execute(f"""
            SELECT r.model, s.action_source,
                   COUNT(*) AS total_taps,
                   AVG(CASE WHEN s.intended_success=1 THEN 1.0 ELSE 0.0 END) AS tap_success_rate
            FROM steps s
            JOIN runs r ON r.run_id=s.run_id
            {where_clause.replace('runs', 'r')} AND s.action_type IN ('tap_xy','tap_text')
            GROUP BY r.model, s.action_source
        """, params).fetchall()
        metrics["tap_success_rate"] = [dict(row) for row in tap_success_rows]
        
        # L) Text accuracy
        text_accuracy_rows = conn.execute(f"""
            SELECT r.model,
                   COUNT(*) AS total_assertions,
                   AVG(CASE WHEN a.passed=1 THEN 1.0 ELSE 0.0 END) AS text_accuracy
            FROM assertions a
            JOIN runs r ON r.run_id=a.run_id
            {where_clause.replace('runs', 'r')} AND a.assertion_type='ui_text_contains'
            GROUP BY r.model
        """, params).fetchall()
        metrics["text_accuracy"] = [dict(row) for row in text_accuracy_rows]
        
        # M) Element-find success (XML vs Vision)
        element_find_rows = conn.execute(f"""
            SELECT r.model, s.action_source,
                   COUNT(*) AS total_finds,
                   AVG(CASE WHEN s.intended_success=1 THEN 1.0 ELSE 0.0 END) AS success_rate
            FROM steps s
            JOIN runs r ON r.run_id=s.run_id
            {where_clause.replace('runs', 'r')} AND s.action_type IN ('tap_xy','tap_text')
            GROUP BY r.model, s.action_source
        """, params).fetchall()
        metrics["element_find_success"] = [dict(row) for row in element_find_rows]
        
        # N) Tokens in/out
        # Only count completed runs
        tokens_rows = conn.execute(f"""
            SELECT model,
                   SUM(tokens_in) AS total_tokens_in,
                   SUM(tokens_out) AS total_tokens_out,
                   AVG(tokens_in) AS avg_tokens_in_per_run,
                   AVG(tokens_out) AS avg_tokens_out_per_run
            FROM runs
            {where_clause} AND final_status IS NOT NULL
            GROUP BY model
        """, params).fetchall()
        metrics["tokens"] = [dict(row) for row in tokens_rows]
        
        # O) Calls per test
        # Only count completed runs
        calls_rows = conn.execute(f"""
            SELECT model,
                   AVG(api_calls) AS avg_calls_per_test,
                   SUM(api_calls) AS total_calls
            FROM runs
            {where_clause} AND final_status IS NOT NULL
            GROUP BY model
        """, params).fetchall()
        metrics["api_calls"] = [dict(row) for row in calls_rows]
        
        # P) Estimated cost
        # Only count completed runs
        cost_rows = conn.execute(f"""
            SELECT model,
                   SUM(cost_usd) AS total_cost,
                   AVG(cost_usd) AS avg_cost_per_test
            FROM runs
            {where_clause} AND final_status IS NOT NULL
            GROUP BY model
        """, params).fetchall()
        metrics["cost"] = [dict(row) for row in cost_rows]
        
        # Q) Rate-limit failures
        rate_limit_rows = conn.execute(f"""
            SELECT model,
                   AVG(CASE WHEN rate_limit_fail=1 THEN 1.0 ELSE 0.0 END) AS rate_limit_rate,
                   COUNT(*) AS total_runs
            FROM runs
            {where_clause}
            GROUP BY model
        """, params).fetchall()
        metrics["rate_limit_failures"] = [dict(row) for row in rate_limit_rows]
        
        conn.close()
        return metrics
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def print_metrics_report(self, experiment_id: Optional[str] = None, model: Optional[str] = None):
        """Print a formatted metrics report"""
        metrics = self.compute_all_metrics(experiment_id, model)
        
        print("=" * 80)
        print("BENCHMARK METRICS REPORT")
        print("=" * 80)
        
        if experiment_id:
            print(f"Experiment ID: {experiment_id}")
        if model:
            print(f"Model: {model}")
        print()
        
        # Outcome Quality
        print("OUTCOME QUALITY")
        print("-" * 80)
        if metrics["pass_rate"]:
            print("Pass Rate (Should-PASS):")
            for row in metrics["pass_rate"]:
                print(f"  {row['model']}: {row['pass_rate']:.2%} ({row['total_runs']} runs)")
        else:
            print("Pass Rate (Should-PASS): No data available")
        
        if metrics["correct_fail_rate"]:
            print("\nCorrect-Fail Detection Rate (Should-FAIL):")
            for row in metrics["correct_fail_rate"]:
                print(f"  {row['model']}: {row['correct_fail_rate']:.2%} ({row['total_runs']} runs)")
        else:
            print("\nCorrect-Fail Detection Rate (Should-FAIL): No data available")
        
        if metrics["false_pass_rate"]:
            print("\nFalse Pass Rate:")
            for row in metrics["false_pass_rate"]:
                print(f"  {row['model']}: {row['false_pass_rate']:.2%} ({row['total_runs']} runs)")
        else:
            print("\nFalse Pass Rate: No data available")
        
        if metrics["false_fail_rate"]:
            print("\nFalse Fail Rate:")
            for row in metrics["false_fail_rate"]:
                print(f"  {row['model']}: {row['false_fail_rate']:.2%} ({row['total_runs']} runs)")
        else:
            print("\nFalse Fail Rate: No data available")
        
        # Efficiency
        print("\nEFFICIENCY")
        print("-" * 80)
        if metrics["steps_per_test"]:
            print("Steps per Test:")
            for model, stats in metrics["steps_per_test"].items():
                print(f"  {model}: mean={stats['mean']:.1f}, median={stats['median']:.1f}, p95={stats['p95']:.1f}")
        else:
            print("Steps per Test: No data available")
        
        print("\nTime per Test (ms):")
        if metrics["time_per_test"]:
            for model, stats in metrics["time_per_test"].items():
                print(f"  {model}: mean={stats['mean']:.0f}, median={stats['median']:.0f}, p95={stats['p95']:.0f}")
        else:
            print("  No data available")
        
        # Robustness
        print("\nROBUSTNESS")
        print("-" * 80)
        if metrics["stuck_rate"]:
            print("Stuck/Loop Rate:")
            for row in metrics["stuck_rate"]:
                print(f"  {row['model']}: {row['stuck_rate']:.2%} ({row['total_runs']} runs)")
        else:
            print("Stuck/Loop Rate: No data available")
        
        if metrics["crash_rate"]:
            print("\nCrash Rate:")
            for row in metrics["crash_rate"]:
                print(f"  {row['model']}: {row['crash_rate']:.2%} ({row['total_runs']} runs)")
        else:
            print("\nCrash Rate: No data available")
        
        # Grounding Accuracy
        print("\nGROUNDING ACCURACY")
        print("-" * 80)
        if metrics["tap_success_rate"]:
            print("Tap Success Rate:")
            for row in metrics["tap_success_rate"]:
                print(f"  {row['model']} ({row['action_source']}): {row['tap_success_rate']:.2%} ({row['total_taps']} taps)")
        else:
            print("Tap Success Rate: No data available")
        
        if metrics["text_accuracy"]:
            print("\nText Accuracy:")
            for row in metrics["text_accuracy"]:
                print(f"  {row['model']}: {row['text_accuracy']:.2%} ({row['total_assertions']} assertions)")
        else:
            print("\nText Accuracy: No data available")
        
        # Cost
        print("\nCOST")
        print("-" * 80)
        if metrics["api_calls"]:
            print("API Calls per Test:")
            for row in metrics["api_calls"]:
                print(f"  {row['model']}: {row['avg_calls_per_test']:.1f} calls (total: {row['total_calls']})")
        else:
            print("API Calls per Test: No data available")
        
        if metrics["cost"]:
            print("\nEstimated Cost:")
            for row in metrics["cost"]:
                avg_cost = row.get('avg_cost_per_test') or 0.0
                total_cost = row.get('total_cost') or 0.0
                if avg_cost > 0 or total_cost > 0:
                    print(f"  {row['model']}: ${avg_cost:.4f} per test (total: ${total_cost:.2f})")
                else:
                    print(f"  {row['model']}: No valid cost data (all runs have invalid token counts)")
        else:
            print("\nEstimated Cost: No data available")
        
        print("=" * 80)

