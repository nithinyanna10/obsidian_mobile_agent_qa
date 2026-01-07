"""
Benchmark Database - SQLite logging for QA agent metrics
Stores runs, steps, and assertions for comprehensive benchmarking
"""
import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
import os


class BenchmarkDB:
    """SQLite database for logging QA agent runs and metrics"""
    
    def __init__(self, db_path: str = "benchmark.db"):
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database with schema"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Create runs table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                experiment_id TEXT,
                trial_num INTEGER,
                model TEXT,
                test_id INTEGER,
                should TEXT,
                started_at TEXT,
                ended_at TEXT,
                duration_ms INTEGER,
                final_status TEXT,
                failure_reason TEXT,
                steps_count INTEGER,
                recovery_count INTEGER DEFAULT 0,
                crash_detected INTEGER DEFAULT 0,
                rate_limit_fail INTEGER DEFAULT 0,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                api_calls INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                reasoning_llm_provider TEXT,
                reasoning_llm_model TEXT,
                vision_llm_provider TEXT,
                vision_llm_model TEXT,
                config_hash TEXT,
                config_json TEXT
            )
        """)
        
        # Create steps table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS steps (
                run_id TEXT,
                step_idx INTEGER,
                subgoal TEXT,
                action_type TEXT,
                action_source TEXT,
                action_json TEXT,
                before_hash TEXT,
                after_hash TEXT,
                screen_changed INTEGER DEFAULT 0,
                intended_check TEXT,
                intended_success INTEGER DEFAULT 0,
                retry_idx INTEGER DEFAULT 0,
                error_type TEXT,
                before_png TEXT,
                after_png TEXT,
                ui_xml TEXT,
                PRIMARY KEY (run_id, step_idx),
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        
        # Create assertions table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS assertions (
                run_id TEXT,
                step_idx INTEGER,
                assertion_type TEXT,
                expected TEXT,
                observed TEXT,
                passed INTEGER,
                evidence_path TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        
        # Create indexes for performance
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_model ON runs(model)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_test ON runs(test_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_experiment ON runs(experiment_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_steps_run ON steps(run_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_assertions_run ON assertions(run_id)")
        
        self.conn.commit()
    
    def start_run(
        self,
        run_id: str,
        experiment_id: str,
        trial_num: int,
        model: str,
        test_id: int,
        should: str,
        reasoning_llm_provider: str,
        reasoning_llm_model: str,
        vision_llm_provider: str,
        vision_llm_model: str,
        config: Dict[str, Any]
    ) -> str:
        """Start a new run and return run_id"""
        config_json = json.dumps(config, sort_keys=True)
        config_hash = hashlib.sha256(config_json.encode()).hexdigest()
        
        self.conn.execute("""
            INSERT INTO runs (
                run_id, experiment_id, trial_num, model, test_id, should,
                started_at, reasoning_llm_provider, reasoning_llm_model,
                vision_llm_provider, vision_llm_model, config_hash, config_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, experiment_id, trial_num, model, test_id, should,
            datetime.utcnow().isoformat(), reasoning_llm_provider, reasoning_llm_model,
            vision_llm_provider, vision_llm_model, config_hash, config_json
        ))
        self.conn.commit()
        return run_id
    
    def end_run(
        self,
        run_id: str,
        final_status: str,
        failure_reason: Optional[str] = None,
        steps_count: int = 0,
        recovery_count: int = 0,
        crash_detected: bool = False,
        rate_limit_fail: bool = False,
        tokens_in: int = 0,
        tokens_out: int = 0,
        api_calls: int = 0,
        cost_usd: float = 0.0
    ):
        """End a run and update final metrics"""
        started_at = self.conn.execute(
            "SELECT started_at FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()["started_at"]
        
        started = datetime.fromisoformat(started_at)
        ended = datetime.utcnow()
        duration_ms = int((ended - started).total_seconds() * 1000)
        
        self.conn.execute("""
            UPDATE runs SET
                ended_at = ?,
                duration_ms = ?,
                final_status = ?,
                failure_reason = ?,
                steps_count = ?,
                recovery_count = ?,
                crash_detected = ?,
                rate_limit_fail = ?,
                tokens_in = ?,
                tokens_out = ?,
                api_calls = ?,
                cost_usd = ?
            WHERE run_id = ?
        """, (
            ended.isoformat(), duration_ms, final_status, failure_reason,
            steps_count, recovery_count, int(crash_detected), int(rate_limit_fail),
            tokens_in, tokens_out, api_calls, cost_usd, run_id
        ))
        self.conn.commit()
    
    def log_step(
        self,
        run_id: str,
        step_idx: int,
        subgoal: str,
        action_type: str,
        action_source: str,
        action_json: Dict[str, Any],
        before_hash: Optional[str] = None,
        after_hash: Optional[str] = None,
        screen_changed: bool = False,
        intended_check: Optional[str] = None,
        intended_success: bool = False,
        retry_idx: int = 0,
        error_type: Optional[str] = None,
        before_png: Optional[str] = None,
        after_png: Optional[str] = None,
        ui_xml: Optional[str] = None
    ):
        """Log a step/action"""
        self.conn.execute("""
            INSERT INTO steps (
                run_id, step_idx, subgoal, action_type, action_source, action_json,
                before_hash, after_hash, screen_changed, intended_check,
                intended_success, retry_idx, error_type, before_png, after_png, ui_xml
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, step_idx, subgoal, action_type, action_source, json.dumps(action_json),
            before_hash, after_hash, int(screen_changed), intended_check,
            int(intended_success), retry_idx, error_type, before_png, after_png, ui_xml
        ))
        self.conn.commit()
    
    def log_assertion(
        self,
        run_id: str,
        step_idx: Optional[int],
        assertion_type: str,
        expected: str,
        observed: str,
        passed: bool,
        evidence_path: Optional[str] = None
    ):
        """Log an assertion evaluation"""
        self.conn.execute("""
            INSERT INTO assertions (
                run_id, step_idx, assertion_type, expected, observed, passed, evidence_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (run_id, step_idx, assertion_type, expected, observed, int(passed), evidence_path))
        self.conn.commit()
    
    def get_metrics(self, experiment_id: Optional[str] = None, model: Optional[str] = None):
        """Get comprehensive metrics"""
        where_clause = "WHERE 1=1"
        params = []
        
        if experiment_id:
            where_clause += " AND experiment_id = ?"
            params.append(experiment_id)
        if model:
            where_clause += " AND model = ?"
            params.append(model)
        
        # Pass rate (Should-PASS)
        pass_rate = self.conn.execute(f"""
            SELECT model,
                   AVG(CASE WHEN final_status='PASS' THEN 1.0 ELSE 0.0 END) AS pass_rate,
                   COUNT(*) AS total_runs
            FROM runs
            {where_clause} AND should='PASS'
            GROUP BY model
        """, params).fetchall()
        
        # Correct-fail detection (Should-FAIL)
        fail_rate = self.conn.execute(f"""
            SELECT r.model,
                   AVG(
                     CASE WHEN r.final_status='FAIL' AND EXISTS (
                          SELECT 1 FROM assertions a
                          WHERE a.run_id=r.run_id AND a.passed=0
                     )
                     THEN 1.0 ELSE 0.0 END
                   ) AS correct_fail_rate,
                   COUNT(*) AS total_runs
            FROM runs r
            {where_clause} AND r.should='FAIL'
            GROUP BY r.model
        """, params).fetchall()
        
        # Steps and time per test
        efficiency = self.conn.execute(f"""
            SELECT model,
                   AVG(steps_count) AS avg_steps,
                   AVG(duration_ms) AS avg_duration_ms,
                   COUNT(*) AS total_runs
            FROM runs
            {where_clause}
            GROUP BY model
        """, params).fetchall()
        
        # Stuck/loop rate
        stuck_rate = self.conn.execute(f"""
            SELECT model,
                   AVG(CASE WHEN failure_reason='STUCK_LOOP' THEN 1.0 ELSE 0.0 END) AS stuck_rate,
                   COUNT(*) AS total_runs
            FROM runs
            {where_clause}
            GROUP BY model
        """, params).fetchall()
        
        # XML vs Vision usage
        action_source_stats = self.conn.execute(f"""
            SELECT r.model, s.action_source,
                   COUNT(*) AS taps,
                   AVG(CASE WHEN s.intended_success=1 THEN 1.0 ELSE 0.0 END) AS tap_success
            FROM steps s
            JOIN runs r ON r.run_id=s.run_id
            {where_clause.replace('runs', 'r')} AND s.action_type IN ('tap_xy','tap_text')
            GROUP BY r.model, s.action_source
        """, params).fetchall()
        
        return {
            "pass_rate": [dict(row) for row in pass_rate],
            "fail_rate": [dict(row) for row in fail_rate],
            "efficiency": [dict(row) for row in efficiency],
            "stuck_rate": [dict(row) for row in stuck_rate],
            "action_source_stats": [dict(row) for row in action_source_stats]
        }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

