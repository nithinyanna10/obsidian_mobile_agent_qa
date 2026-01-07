# Cost Calculation Fix

## Issue
The cost calculation was using character counts instead of actual token counts from OpenAI API responses, leading to incorrect cost estimates.

## Fix Applied

### 1. **Use Actual Token Counts**
Changed from character counting to using actual token counts from OpenAI API:
- **Before**: `tokens_in = sum(len(str(m.get("content", ""))) for m in messages)` (character count)
- **After**: `tokens_in = response.usage.prompt_tokens` (actual tokens)

### 2. **Correct Pricing**
Updated to use correct GPT-4o pricing (as of 2024):
- **Input tokens**: $5.00 per 1 million tokens
- **Output tokens**: $15.00 per 1 million tokens

### 3. **Filter Incomplete Runs**
Updated metrics queries to only count runs with `final_status IS NOT NULL` to exclude incomplete runs from calculations.

## Impact

### Existing Data
- Old runs in the database have incorrect token counts (character counts instead of tokens)
- These will show incorrect costs, but new runs will be accurate

### New Runs
- All new runs will use actual token counts from OpenAI API
- Costs will be calculated accurately based on real usage

## Verification

To verify correct token counting:
1. Check that `tokens_in` and `tokens_out` match OpenAI API response `usage.prompt_tokens` and `usage.completion_tokens`
2. Cost should be: `(tokens_in / 1_000_000 * 5.00) + (tokens_out / 1_000_000 * 15.00)`

## Run Count Accuracy

The metrics now correctly show:
- **Should-PASS runs**: Only completed runs with `should='PASS'` and `final_status IS NOT NULL`
- **Should-FAIL runs**: Only completed runs with `should='FAIL'` and `final_status IS NOT NULL`
- Incomplete runs (NULL final_status) are excluded from all metrics

