# Benchmark Integration Complete

## Overview

The benchmark logging system is now fully integrated into the QA agent. Every action, step, API call, and assertion is automatically logged to SQLite when you run tests.

## What's Logged Automatically

### 1. **Run Information**
- Model identifier
- Test ID and expected result (PASS/FAIL)
- Start/end times and duration
- Final status and failure reason
- Configuration (temperature, max_steps, etc.)

### 2. **Every Step/Action**
- Subgoal description
- Action type (tap, type, swipe, etc.)
- Action source (XML, VISION, FALLBACK_COORDS)
- Before/after screenshots
- UI XML dump
- Intended check and success status
- Error type (if any)

### 3. **API Calls**
- Tokens in/out
- Cost estimation
- Rate limit tracking

### 4. **Assertions**
- Assertion type (ui_text_contains, element_exists, icon_color_is)
- Expected vs observed
- Pass/fail status
- Evidence path

## Usage

### Basic Usage (Logging Enabled by Default)

```bash
# Run tests with automatic logging
python main.py

# Run with model identifier for benchmarking
python main.py --model gpt-4o --experiment-id "my_experiment_v1" --trial 1

# Disable logging
python main.py --no-logging
```

### View Metrics

```bash
# View all metrics
python view_metrics.py

# Filter by experiment
python view_metrics.py --experiment-id "bench_v1_2026_01_07"

# Filter by model
python view_metrics.py --model gpt-4o
```

### Run Benchmarks (Multiple Trials)

```bash
# Run 5 trials per test
python run_benchmark.py --model gpt-4o --trials 5

# Custom experiment ID
python run_benchmark.py --model gpt-4o --experiment-id "my_benchmark" --trials 5
```

## Database Location

All data is stored in `benchmark.db` (SQLite database) in the project root.

## Integration Points

1. **main.py**: Initializes logger, logs runs, steps, and assertions
2. **agents/planner.py**: Logs all OpenAI API calls with token usage
3. **agents/executor.py**: Returns action_source and intended_success (partially integrated - needs full coverage)
4. **agents/supervisor.py**: Logs API calls and returns assertions

## Action Source Tracking

The executor tracks how elements were found:
- **XML**: Found via UIAutomator XML search
- **VISION**: Found via LLM vision analysis
- **FALLBACK_COORDS**: Used fallback coordinates

This is partially integrated. To fully track action_source for all actions, you'll need to update all return statements in `executor.py` to include `action_source` and `intended_success`.

## Next Steps

1. **Complete Executor Integration**: Update all return statements in `executor.py` to include `action_source` and `intended_success`
2. **Test the Integration**: Run a test and verify data is being logged
3. **View Metrics**: Use `view_metrics.py` to see the logged data
4. **Run Benchmarks**: Use `run_benchmark.py` for multiple trials

## Example: Checking Logged Data

```python
from tools.benchmark_db import BenchmarkDB

db = BenchmarkDB("benchmark.db")
metrics = db.get_metrics()
print(metrics)
```

## Notes

- Logging is enabled by default
- Database is created automatically on first run
- All screenshots and XML dumps are stored with paths in the database
- Token counting is approximate (based on message length)
- Cost estimation uses GPT-4o pricing ($5/1M input, $15/1M output tokens)

