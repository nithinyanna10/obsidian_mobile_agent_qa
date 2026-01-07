# Token Count Issue - All Old Data Is Invalid

## Problem

All token counts in the database are **incorrect** - they are character counts, not actual tokens from OpenAI API responses.

## Evidence

**Your actual OpenAI billing:**
- $0.26 for 2.5 test runs
- = **$0.10 per test**

**Our database shows:**
- $1.20 per test (12x too high!)
- Token counts: 140k-384k input tokens per test

**Expected token counts:**
- Per test: ~10k-20k input tokens, ~1k-2k output tokens
- Cost: ~$0.05-$0.10 per test

## Root Cause

The old code was using **character counting** instead of actual token counts from API responses:
```python
# OLD (WRONG):
tokens_in = sum(len(str(m.get("content", ""))) for m in messages)  # Character count!

# NEW (CORRECT):
tokens_in = response.usage.prompt_tokens  # Actual tokens from API
```

## Solution

1. **All old runs marked as invalid** - They have incorrect token counts
2. **New runs will be accurate** - They use actual token counts from API responses
3. **Run new tests** - Only new tests will have correct costs

## What to Do

1. **Delete old invalid data** (optional):
   ```bash
   sqlite3 benchmark.db "DELETE FROM runs WHERE tokens_in > 50000;"
   ```

2. **Run new tests** - They will have accurate token counts and costs

3. **Verify** - Compare new costs with OpenAI dashboard (should match)

## Expected Costs for New Runs

Based on your actual billing:
- **Per test**: ~$0.10
- **Per API call**: ~$0.02-$0.03
- **Token counts**: ~10k-20k input, ~1k-2k output per test

## Verification

After running new tests, verify:
1. Token counts are reasonable (10k-50k input per test)
2. Costs match OpenAI dashboard
3. Cost per test is ~$0.10, not $1.20

