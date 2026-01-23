# Database Structure Explanation

## Current Storage Structure

### How Tests Are Stored

When you run `python3 main.py`, it executes **4 tests sequentially** (Test 1, 2, 3, 4). Here's how they're stored:

**Each test = One separate run in the database**

```
Test Suite Run (experiment_id: "bench_v1_2026_01_23", trial_num: 1)
├── Run 1: Test 1 (test_id: 1) - Create vault
├── Run 2: Test 2 (test_id: 2) - Create note  
├── Run 3: Test 3 (test_id: 3) - Print to PDF
└── Run 4: Test 4 (test_id: 4) - Appearance color
```

### Database Schema

**`runs` table** - Each row = One test execution
- `run_id` (PRIMARY KEY) - Unique ID for each test run
- `experiment_id` - Groups test suites (e.g., "bench_v1_2026_01_23")
- `trial_num` - Trial number (usually 1)
- `test_id` - Which test (1, 2, 3, or 4)
- `final_status` - PASS/FAIL for that specific test
- `steps_count`, `tokens_in`, `tokens_out`, `cost_usd` - Metrics for that test
- `started_at`, `ended_at` - Timestamps for that test

**Grouping:**
- All 4 tests share the same `experiment_id` and `trial_num`
- This groups them as one "test suite run"
- But each test has its own `run_id` and metrics

## Example from Your Database

```
Latest Test Suite: bench_v1_2026_01_23, Trial 1

Run 1: test_id=1, status=PASS, steps=7, cost=$0.229
Run 2: test_id=2, status=PASS, steps=5, cost=$0.040
Run 3: test_id=3, status=FAIL, steps=2, cost=$0.015
Run 4: test_id=4, status=FAIL, steps=7, cost=$0.066

Total: 4 tests, 21 steps, $0.350 cost
```

## Is This the Right Structure?

### ✅ **Current Approach (Separate Runs) - RECOMMENDED**

**Pros:**
1. **Granular Analysis**: Can analyze each test individually
   - Which test is slowest? (Test 1: 297s)
   - Which test is most expensive? (Test 1: $0.229)
   - Which test fails most often? (Test 3, 4)

2. **Flexible Queries**: Easy to filter by test_id
   ```sql
   SELECT * FROM runs WHERE test_id = 1  -- All Test 1 runs
   SELECT AVG(cost_usd) FROM runs WHERE test_id = 2  -- Avg cost for Test 2
   ```

3. **Step-Level Tracking**: Each test's steps are linked to its run_id
   - Can see exactly what Test 1 did (7 steps)
   - Can see exactly what Test 2 did (5 steps)

4. **Independent Metrics**: Each test's performance is tracked separately
   - Test 1 might be slow (vault creation)
   - Test 2 might be fast (note creation)

5. **Suite Aggregation**: Can still calculate suite-level metrics
   ```sql
   SELECT SUM(cost_usd), SUM(steps_count) 
   FROM runs 
   WHERE experiment_id = 'bench_v1_2026_01_23' AND trial_num = 1
   ```

**Cons:**
- Need to group by experiment_id + trial_num for suite-level analysis
- Slightly more complex queries for suite metrics

### ❌ **Alternative (One Run for All Tests) - NOT RECOMMENDED**

**If stored as one run:**
- Would lose individual test metrics
- Can't analyze which test is problematic
- Can't compare Test 1 vs Test 2 performance
- Harder to debug specific test failures

## How Calculations Work

### Suite-Level Calculations (All 4 Tests Together)

```sql
-- Total cost for test suite
SELECT SUM(cost_usd) as total_cost
FROM runs
WHERE experiment_id = 'bench_v1_2026_01_23' AND trial_num = 1

-- Total steps
SELECT SUM(steps_count) as total_steps
FROM runs
WHERE experiment_id = 'bench_v1_2026_01_23' AND trial_num = 1

-- Pass rate
SELECT 
    COUNT(*) as total_tests,
    SUM(CASE WHEN final_status='PASS' THEN 1 ELSE 0 END) as passed
FROM runs
WHERE experiment_id = 'bench_v1_2026_01_23' AND trial_num = 1
```

### Test-Level Calculations (Individual Tests)

```sql
-- Average cost for Test 1 across all runs
SELECT AVG(cost_usd) as avg_cost
FROM runs
WHERE test_id = 1

-- Success rate for Test 2
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN final_status='PASS' THEN 1 ELSE 0 END) as passed
FROM runs
WHERE test_id = 2
```

## Current Structure is CORRECT ✅

The current structure is **optimal** because:

1. **Flexibility**: Can analyze at both test-level and suite-level
2. **Granularity**: Each test's performance is tracked independently
3. **Debugging**: Easy to find which specific test failed and why
4. **Comparison**: Can compare Test 1 vs Test 2 vs Test 3 vs Test 4
5. **Aggregation**: Can still calculate suite totals when needed

## Tools for Viewing

### View Complete Test Suite (All 4 Tests)
```bash
python3 view_latest_suite.py
```
Shows all 4 tests together with suite-level totals.

### View Individual Test
```bash
python3 view_latest_run.py
```
Shows the latest individual test (Test 4).

### View Specific Test in Suite
```bash
python3 view_latest_run.py --run-id <run_id>
```

## Summary

**Current Structure:**
- ✅ Each test = One run (separate row in `runs` table)
- ✅ All 4 tests grouped by `experiment_id` + `trial_num`
- ✅ Suite-level metrics calculated by aggregating runs
- ✅ Test-level metrics available per run

**This is the RIGHT approach** because it gives you:
- Individual test analysis
- Suite-level aggregation
- Flexible querying
- Detailed debugging

The database structure is well-designed for both granular and aggregate analysis!
