# Database Viewer

## Quick View

To view the entire database (all tables, schema, and data):

```bash
python view_database.py
```

## Database Structure

The database has 3 main tables:

### 1. `runs` table
- **Purpose**: One row per test execution
- **Key columns**:
  - `run_id`: Unique identifier for each run
  - `test_id`: Test case ID (1, 2, 3, or 4)
  - `should`: Expected result ("PASS" or "FAIL")
  - `final_status`: Actual result ("PASS", "FAIL", or "ERROR")
  - `tokens_in`, `tokens_out`: Token usage
  - `cost_usd`: Cost in USD
  - `steps_count`: Number of steps taken
  - `duration_ms`: Time taken in milliseconds

### 2. `steps` table
- **Purpose**: One row per action/step during test execution
- **Key columns**:
  - `run_id`: Links to runs table
  - `step_idx`: Step number (0, 1, 2, ...)
  - `action_type`: Type of action (tap, type, wait, etc.)
  - `action_source`: How element was found (XML, VISION, FALLBACK_COORDS)
  - `before_png`, `after_png`: Screenshot paths
  - `ui_xml`: UI XML dump path

### 3. `assertions` table
- **Purpose**: One row per assertion/verification
- **Key columns**:
  - `run_id`: Links to runs table
  - `assertion_type`: Type of assertion (ui_text_contains, element_exists, icon_color_is)
  - `expected`: Expected value
  - `observed`: Actual value
  - `passed`: 1 if passed, 0 if failed

## SQL Queries

### View all runs
```sql
sqlite3 benchmark.db "SELECT run_id, test_id, should, final_status, cost_usd FROM runs ORDER BY started_at DESC;"
```

### View all steps for a run
```sql
sqlite3 benchmark.db "SELECT step_idx, action_type, action_source, subgoal FROM steps WHERE run_id='<run_id>' ORDER BY step_idx;"
```

### View all assertions
```sql
sqlite3 benchmark.db "SELECT run_id, assertion_type, expected, observed, passed FROM assertions;"
```

### Count runs by test
```sql
sqlite3 benchmark.db "SELECT test_id, COUNT(*) as count FROM runs GROUP BY test_id;"
```

## Clean Database

To clear all data:
```bash
python clear_old_runs.py
```

This will delete all runs, steps, and assertions.

