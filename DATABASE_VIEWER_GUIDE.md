# Database Viewer Guide

## Overview

The SQLite database (`benchmark.db`) stores all test run data with comprehensive metrics. Use the tools below to view and analyze the data.

## Database Schema

### Tables

1. **`runs`** - Main test run records
   - `run_id` (PRIMARY KEY)
   - `experiment_id`, `trial_num`, `test_id`
   - `reasoning_llm_model`, `vision_llm_model`
   - `final_status`, `failure_reason`
   - `steps_count`, `duration_ms`
   - `tokens_in`, `tokens_out`, `api_calls`, `cost_usd`
   - `started_at`, `ended_at`
   - `config_json` (full configuration)

2. **`steps`** - Individual action steps
   - `run_id`, `step_idx` (PRIMARY KEY)
   - `action_type`, `action_source`, `subgoal`
   - `intended_success`, `error_type`
   - `before_png`, `after_png`, `ui_xml`
   - `action_json` (full action data)

3. **`assertions`** - Verification checks
   - `run_id`, `step_idx`
   - `assertion_type`, `expected`, `observed`
   - `passed`, `evidence_path`

## Tools

### 1. View Latest Run

**Command:**
```bash
python3 view_latest_run.py
```

**What it shows:**
- Run information (ID, test, status, timestamps)
- Model information (reasoning + vision models)
- Performance metrics (steps, duration, tokens, cost)
- Failure reason (if failed)
- All steps with details
- Assertions/verifications
- Configuration used

**Options:**
```bash
# View specific run by ID
python3 view_latest_run.py --run-id <run_id>

# List recent runs
python3 view_latest_run.py --list 10

# Use different database
python3 view_latest_run.py --db custom.db
```

### 2. Show Database Contents

**Command:**
```bash
python3 show_db_contents.py
```

**Options:**
```bash
# Show summary only
python3 show_db_contents.py --summary

# Show detailed runs
python3 show_db_contents.py --runs --limit 20

# Show specific table
python3 show_db_contents.py --table runs --limit 10
python3 show_db_contents.py --table steps --limit 50
python3 show_db_contents.py --table assertions --limit 20
```

### 3. Batch Analysis (JSON Files)

**Command:**
```bash
python3 batch_analyze.py
```

Analyzes episode JSON files in `results/` directory (created by `main.py`).

## Example Usage

### View Latest Run
```bash
python3 view_latest_run.py
```

**Output:**
```
================================================================================
LATEST TEST RUN
================================================================================

📊 RUN INFORMATION
--------------------------------------------------------------------------------
Run ID:        3cc325db-a17c-43d8-8d68-4acae9a08d1a
Experiment:    bench_v1_2026_01_23
Trial:         1
Test ID:       4
Expected:      FAIL
Status:        FAIL
Started:       2026-01-23 17:56:00
Ended:         2026-01-23 18:00:22

🤖 MODEL INFORMATION
--------------------------------------------------------------------------------
Reasoning Model:  gpt-4o (openai)
Vision Model:     gpt-4o (openai)

⚡ PERFORMANCE METRICS
--------------------------------------------------------------------------------
Steps Taken:    7
Duration:       262.41 seconds (262408 ms)
API Calls:      7
Tokens In:      8,844
Tokens Out:     1,455
Total Tokens:   10,299
Cost:           $0.066045
...
```

### List Recent Runs
```bash
python3 view_latest_run.py --list 5
```

**Output:**
```
====================================================================================================
RECENT RUNS (Last 5)
====================================================================================================

Run ID       Test   Model                     Status   Steps    Cost         Started             
----------------------------------------------------------------------------------------------------
3cc325db...  4      gpt-4o                    FAIL     7        $0.0660      2026-01-23 17:56:00 
0b151cd1...  3      gpt-4o                    FAIL     2        $0.0148      2026-01-23 17:55:07 
95e49ce8...  2      gpt-4o                    PASS     5        $0.0404      2026-01-23 17:52:14 
c258ef95...  1      gpt-4o                    PASS     7        $0.2290      2026-01-23 17:47:15 
```

## SQL Queries

You can also query the database directly:

```python
import sqlite3

conn = sqlite3.connect('benchmark.db')
conn.row_factory = sqlite3.Row

# Get latest run
cursor = conn.execute("""
    SELECT * FROM runs 
    ORDER BY started_at DESC 
    LIMIT 1
""")
latest = cursor.fetchone()

# Get all steps for a run
cursor = conn.execute("""
    SELECT * FROM steps 
    WHERE run_id = ? 
    ORDER BY step_idx
""", (latest['run_id'],))
steps = cursor.fetchall()

# Get pass rate by model
cursor = conn.execute("""
    SELECT reasoning_llm_model,
           COUNT(*) as total,
           SUM(CASE WHEN final_status='PASS' THEN 1 ELSE 0 END) as passed
    FROM runs
    GROUP BY reasoning_llm_model
""")
stats = cursor.fetchall()
```

## Key Metrics Tracked

- **Performance**: Steps, duration, API calls
- **Cost**: Token usage, cost per run
- **Success**: Pass/fail rates, failure reasons
- **Actions**: Action types, sources, success rates
- **Verification**: Assertions, expected vs observed
- **Configuration**: Full config for each run

## Integration

The database is automatically populated when you run:
```bash
python3 main.py
```

All runs are logged to `benchmark.db` with comprehensive metrics.
