# API Usage Display Feature

## What Was Added

After each test completes, the system now displays a **clear summary** showing:
1. **RL Usage** - How many actions came from memory patterns (no API calls)
2. **API Calls** - How many OpenAI API calls were made
3. **Cost** - Estimated cost for the test

## Output Format

### Example 1: Test with RL Patterns (No API Calls)

```
============================================================
📊 TEST 1 USAGE SUMMARY
============================================================
💾 RL Usage: 5 action(s) from memory patterns (no API calls)
🔌 API Calls: 0 call(s) made
📈 Total Steps: 5 (5 RL + 0 API)
✅ Result: 100% RL usage - No API calls needed!
💰 Estimated Cost: $0.00 (all from RL memory)
============================================================
```

### Example 2: Test with Mixed Usage (Some RL, Some API)

```
============================================================
📊 TEST 2 USAGE SUMMARY
============================================================
💾 RL Usage: 3 action(s) from memory patterns (no API calls)
🔌 API Calls: 2 call(s) made
📈 Total Steps: 5 (3 RL + 2 API)
✅ Result: 60% RL usage, 2 API call(s)
💰 Estimated Cost: $0.012345
============================================================
```

### Example 3: Test with No RL Patterns (All API)

```
============================================================
📊 TEST 3 USAGE SUMMARY
============================================================
🔌 API Calls: 7 call(s) made
📈 Total Steps: 7 (all used API)
💡 No RL patterns available - all actions used OpenAI API
💰 Estimated Cost: $0.045678
============================================================
```

## How It Works

1. **Tracking**: Each action is checked for the `_from_memory` flag
   - If `_from_memory = True` → Action came from RL memory (no API call)
   - If `_from_memory = False/None` → Action used OpenAI API

2. **Counting**: 
   - `memory_actions_count` = Actions from memory
   - `api_calls` = Actual OpenAI API calls made (from logger)
   - `step_count` = Total steps taken

3. **Display**: After each test completes, shows:
   - RL usage count
   - API call count
   - Percentage breakdown
   - Estimated cost

## Benefits

- **Clear visibility** into cost savings from RL
- **Easy to see** which tests benefit from memory patterns
- **Cost tracking** per test
- **Helps identify** tests that need more RL patterns

## Location in Code

- **Tracking**: `main.py` line ~146-147 (counts memory actions)
- **Display**: `main.py` line ~367-397 (shows summary after test)

## Next Run

When you run `main.py`, you'll see this summary after **each test** completes, making it easy to see:
- Which tests used RL (saved money!)
- Which tests still need API calls
- Total cost per test
