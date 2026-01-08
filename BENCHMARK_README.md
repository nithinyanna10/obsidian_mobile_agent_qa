# Benchmark System Documentation

## Overview

The benchmark system provides comprehensive logging and metrics for QA agent performance across multiple models and trials. All data is stored in a SQLite database for easy analysis.

## Database Schema

### `runs` Table
One row per test execution (model × test × trial)

**Key Columns:**
- `run_id` (UUID) - Unique identifier
- `experiment_id` - Experiment identifier (e.g., "bench_v1_2026_01_07")
- `trial_num` - Trial number (1..K)
- `model` - Model identifier
- `test_id` - Test ID (1, 2, 3, 4)
- `should` - Expected result (PASS/FAIL)
- `final_status` - Actual result (PASS/FAIL)
- `failure_reason` - Why it failed (STUCK_LOOP, ELEMENT_NOT_FOUND, etc.)
- `steps_count` - Number of steps taken
- `duration_ms` - Total time in milliseconds
- `tokens_in`, `tokens_out` - Token usage
- `api_calls` - Number of API calls
- `cost_usd` - Estimated cost
- `reasoning_llm_provider`, `reasoning_llm_model` - LLM configuration
- `vision_llm_provider`, `vision_llm_model` - Vision model configuration
- `config_hash`, `config_json` - Full configuration

### `steps` Table
One row per action/step

**Key Columns:**
- `run_id`, `step_idx` - Foreign key to run
- `subgoal` - Planner's subgoal description
- `action_type` - tap_xy, tap_text, type_text, swipe, keyevent, wait
- `action_source` - XML, VISION, FALLBACK_COORDS
- `action_json` - Full action JSON
- `before_hash`, `after_hash` - Screenshot hashes
- `screen_changed` - 0/1 if screen changed
- `intended_check` - What we intended to check (e.g., OPEN_SETTINGS)
- `intended_success` - 0/1 if action succeeded
- `retry_idx` - 0 for first attempt, 1+ for retries
- `error_type` - Error if any
- `before_png`, `after_png`, `ui_xml` - File paths

### `assertions` Table
One row per assertion evaluation

**Key Columns:**
- `run_id`, `step_idx` - Foreign key
- `assertion_type` - ui_text_contains, element_exists, icon_color_is
- `expected`, `observed` - Expected vs actual
- `passed` - 0/1
- `evidence_path` - Optional image path

## Metrics Computed

### Outcome Quality
1. **Test Pass Rate (Should-PASS)** - % of should-pass tests that passed
2. **Correct-Fail Detection Rate (Should-FAIL)** - % of should-fail tests that correctly failed
3. **False Pass Rate** - % of should-fail tests that incorrectly passed
4. **False Fail Rate** - % of should-pass tests that incorrectly failed

### Efficiency
5. **Steps per test** - Mean, median, p95
6. **Time per test** - Mean, median, p95 (ms)
7. **Retries per step** - Average retry count

### Robustness
8. **Stuck/Loop rate** - % of runs that got stuck
9. **Crash rate** - % of runs that crashed

### Grounding Accuracy
10. **Tap success rate** - % of taps that succeeded (by source: XML/VISION)
11. **Text accuracy** - % of text assertions that passed
12. **Element-find success** - XML vs Vision success rates

### Cost
13. **Tokens in/out** - Total and average per run
14. **API calls** - Total and average per test
15. **Estimated cost** - Total and average per test ($)
16. **Rate-limit failures** - % of runs that hit rate limits

## Usage

### Running Benchmarks

```bash
# Run 5 trials of all tests with a model
python run_benchmark.py --model gpt-4o --trials 5

# With custom experiment ID
python run_benchmark.py --model gpt-4o --experiment-id "my_experiment_v1" --trials 5

# Custom database path
python run_benchmark.py --model gpt-4o --db my_benchmark.db
```

### Viewing Metrics

```bash
# View all metrics
python view_metrics.py

# Filter by experiment
python view_metrics.py --experiment-id "bench_v1_2026_01_07"

# Filter by model
python view_metrics.py --model gpt-4o

# Both filters
python view_metrics.py --experiment-id "bench_v1_2026_01_07" --model gpt-4o
```

### Direct SQL Queries

You can also query the database directly:

```python
import sqlite3
conn = sqlite3.connect("benchmark.db")
conn.row_factory = sqlite3.Row

# Example: Get pass rate by model
rows = conn.execute("""
    SELECT model,
           AVG(CASE WHEN final_status='PASS' THEN 1.0 ELSE 0.0 END) AS pass_rate
    FROM runs
    WHERE should='PASS'
    GROUP BY model
""").fetchall()

for row in rows:
    print(f"{row['model']}: {row['pass_rate']:.2%}")
```

## Integration with main.py

To integrate logging into the main execution loop, you need to:

1. Initialize logger at start of test
2. Log each step with action details
3. Log assertions when supervisor verifies
4. Track API calls and tokens
5. End run with final status

See `tools/benchmark_logger.py` for the API.

## Benchmark Protocol

For valid benchmarks:

1. **Models**: Test M different models
2. **Trials**: Run K=5 trials per test per model (minimum)
3. **Total runs**: M × (#tests) × K
4. **Randomness**: Fix temperature or log seed
5. **Reset state**: Close app → reopen → ensure correct vault between runs

## Example Workflow

```bash
# 1. Run benchmark for model 1
python run_benchmark.py --model gpt-4o --experiment-id "bench_v1" --trials 5

# 2. Run benchmark for model 2
python run_benchmark.py --model gpt-4o-mini --experiment-id "bench_v1" --trials 5

# 3. View comparison
python view_metrics.py --experiment-id "bench_v1"
```

## Failure Reasons

Common `failure_reason` values:
- `ASSERTION_FAILED` - Supervisor assertion failed
- `ELEMENT_NOT_FOUND` - Required element not found
- `STUCK_LOOP` - Got stuck in a loop
- `CRASH` - App crashed
- `RATE_LIMIT` - Hit API rate limit
- `OPENAI_ERROR` - OpenAI API error
- `MAX_STEPS_REACHED` - Hit max step limit
- `EXCEPTION` - Python exception occurred

## Action Sources

- `XML` - Found element via UIAutomator XML
- `VISION` - Found element via LLM vision
- `FALLBACK_COORDS` - Used fallback coordinates
- `MEMORY` - Used memory pattern (no API call)

