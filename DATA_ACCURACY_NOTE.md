# Data Accuracy Note

## Issue with Old Data

The database contains some runs with **incorrect token counts** from the old character-counting method. These runs have costs calculated from wrong data.

## How to Identify Bad Data

Runs with **> 500,000 input tokens** are suspicious and likely have character counts instead of actual tokens.

**Typical token counts for a test run:**
- Input: 10k-50k tokens (screenshots + prompts)
- Output: 1k-5k tokens (responses)

## Current Status

- **Run 1**: 2,488,967 input tokens - **CLEARLY WRONG** (marked as invalid)
- **Runs 2-4**: 140k-384k tokens - Possibly high but may be valid

## Solutions

### Option 1: Mark Bad Data (Recommended)
```bash
python clean_old_data.py mark
```
Sets `cost_usd = NULL` for runs with suspicious token counts. They won't be included in cost calculations.

### Option 2: Delete Bad Data
```bash
python clean_old_data.py delete
```
Permanently removes runs with incorrect token counts.

### Option 3: Re-run Tests
Run new tests - they will have **accurate token counts** from OpenAI API responses.

## New Runs Are Accurate

All new test runs use:
- ✅ Actual token counts from `response.usage.prompt_tokens` and `response.usage.completion_tokens`
- ✅ Accurate cost calculation from pricing map
- ✅ No character counting or estimates

## Verification

To verify accuracy of new runs:
1. Check token counts are reasonable (10k-50k input, 1k-5k output)
2. Compare with OpenAI dashboard
3. Costs should match OpenAI billing

