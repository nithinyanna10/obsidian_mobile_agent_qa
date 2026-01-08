"""
Benchmark Logger - Integrates with main.py and agents to log all metrics
"""
import uuid
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from .benchmark_db import BenchmarkDB
from config import OPENAI_MODEL, OPENAI_API_KEY
from .pricing import calculate_cost


class BenchmarkLogger:
    """Logger that integrates with the QA agent system"""
    
    def __init__(self, db_path: str = "benchmark.db", experiment_id: Optional[str] = None):
        self.db = BenchmarkDB(db_path)
        self.experiment_id = experiment_id or f"bench_v1_{datetime.now().strftime('%Y_%m_%d')}"
        self.current_run_id: Optional[str] = None
        self.current_step_idx = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.api_calls = 0
        self.cost_usd = 0.0
        self.recovery_count = 0
        self.crash_detected = False
        self.rate_limit_fail = False
        
    def start_run(
        self,
        trial_num: int,
        model: str,
        test_id: int,
        should: str,
        config: Dict[str, Any]
    ) -> str:
        """Start a new test run"""
        self.current_run_id = str(uuid.uuid4())
        self.current_step_idx = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.api_calls = 0
        self.cost_usd = 0.0
        self.recovery_count = 0
        self.crash_detected = False
        self.rate_limit_fail = False
        
        # Determine LLM providers/models
        reasoning_llm_provider = "openai" if OPENAI_API_KEY else "unknown"
        reasoning_llm_model = OPENAI_MODEL
        vision_llm_provider = "openai" if OPENAI_API_KEY else "unknown"
        vision_llm_model = OPENAI_MODEL
        
        self.db.start_run(
            run_id=self.current_run_id,
            experiment_id=self.experiment_id,
            trial_num=trial_num,
            model=model,
            test_id=test_id,
            should=should,
            reasoning_llm_provider=reasoning_llm_provider,
            reasoning_llm_model=reasoning_llm_model,
            vision_llm_provider=vision_llm_provider,
            vision_llm_model=vision_llm_model,
            config=config
        )
        
        return self.current_run_id
    
    def log_step(
        self,
        subgoal: str,
        action: Dict[str, Any],
        action_source: str,
        before_screenshot: Optional[str] = None,
        after_screenshot: Optional[str] = None,
        ui_xml: Optional[str] = None,
        intended_check: Optional[str] = None,
        intended_success: bool = False,
        retry_idx: int = 0,
        error_type: Optional[str] = None
    ):
        """Log a step/action"""
        if not self.current_run_id:
            return
        
        action_type = action.get("action", "unknown")
        
        # Calculate screen change
        screen_changed = False
        before_hash = None
        after_hash = None
        
        if before_screenshot and after_screenshot:
            try:
                import hashlib
                with open(before_screenshot, 'rb') as f:
                    before_hash = hashlib.md5(f.read()).hexdigest()
                with open(after_screenshot, 'rb') as f:
                    after_hash = hashlib.md5(f.read()).hexdigest()
                screen_changed = (before_hash != after_hash)
            except:
                pass
        
        self.db.log_step(
            run_id=self.current_run_id,
            step_idx=self.current_step_idx,
            subgoal=subgoal,
            action_type=action_type,
            action_source=action_source,
            action_json=action,
            before_hash=before_hash,
            after_hash=after_hash,
            screen_changed=screen_changed,
            intended_check=intended_check,
            intended_success=intended_success,
            retry_idx=retry_idx,
            error_type=error_type,
            before_png=before_screenshot,
            after_png=after_screenshot,
            ui_xml=ui_xml
        )
        
        self.current_step_idx += 1
    
    def log_assertion(
        self,
        assertion_type: str,
        expected: str,
        observed: str,
        passed: bool,
        step_idx: Optional[int] = None,
        evidence_path: Optional[str] = None
    ):
        """Log an assertion evaluation"""
        if not self.current_run_id:
            return
        
        self.db.log_assertion(
            run_id=self.current_run_id,
            step_idx=step_idx,
            assertion_type=assertion_type,
            expected=expected,
            observed=observed,
            passed=passed,
            evidence_path=evidence_path
        )
    
    def log_api_call(
        self,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost: Optional[float] = None,
        model: Optional[str] = None
    ):
        """
        Log an API call and accumulate tokens/cost
        
        Args:
            tokens_in: Input tokens from API response
            tokens_out: Output tokens from API response
            cost: Pre-calculated cost (if None, will calculate from tokens and model)
            model: Model identifier (required if cost is None)
        """
        self.api_calls += 1
        
        # Accumulate tokens
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        
        # Calculate cost if not provided
        if cost is None:
            if model:
                from tools.pricing import calculate_cost
                calculated_cost = calculate_cost(model, tokens_in, tokens_out)
                if calculated_cost is not None:
                    self.cost_usd += calculated_cost
            # If no model or pricing unknown, cost remains 0
        else:
            self.cost_usd += cost
    
    def increment_recovery(self):
        """Increment recovery count (back/home/relaunch)"""
        self.recovery_count += 1
    
    def set_crash_detected(self):
        """Mark that a crash was detected"""
        self.crash_detected = True
    
    def set_rate_limit_fail(self):
        """Mark that rate limit was hit"""
        self.rate_limit_fail = True
    
    def end_run(
        self,
        final_status: str,
        failure_reason: Optional[str] = None
    ):
        """End the current run"""
        if not self.current_run_id:
            return
        
        self.db.end_run(
            run_id=self.current_run_id,
            final_status=final_status,
            failure_reason=failure_reason,
            steps_count=self.current_step_idx,
            recovery_count=self.recovery_count,
            crash_detected=self.crash_detected,
            rate_limit_fail=self.rate_limit_fail,
            tokens_in=self.tokens_in,
            tokens_out=self.tokens_out,
            api_calls=self.api_calls,
            cost_usd=self.cost_usd
        )
        
        self.current_run_id = None
    
    def get_metrics(self, model: Optional[str] = None):
        """Get metrics for the experiment"""
        return self.db.get_metrics(experiment_id=self.experiment_id, model=model)
    
    def close(self):
        """Close the database"""
        self.db.close()

