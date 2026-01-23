# Cost Discrepancy Explanation

## The Issue

**Database shows:** $0.350  
**Your OpenAI account shows:** $0.20  
**Difference:** ~$0.15 (43% higher in database)

## Root Cause

The pricing in `tools/pricing.py` was **outdated** (from 2024). OpenAI reduced GPT-4o pricing in 2026.

### Old Pricing (in code - WRONG)
- Input: $5.00 per 1M tokens
- Output: $15.00 per 1M tokens

### New Pricing (2026 - CORRECT)
- Input: $2.50 per 1M tokens (50% reduction)
- Output: $10.00 per 1M tokens (33% reduction)

## Cost Calculation

### With OLD Pricing (what database was using):
```
Test 1: 33,796 in + 4,002 out = $0.229
Test 2: 6,735 in + 449 out = $0.040
Test 3: 2,696 in + 88 out = $0.015
Test 4: 8,844 in + 1,455 out = $0.066
─────────────────────────────────────
Total: $0.350 ❌ (WRONG - outdated pricing)
```

### With NEW Pricing (actual OpenAI pricing):
```
Test 1: 33,796 in + 4,002 out = $0.125
Test 2: 6,735 in + 449 out = $0.021
Test 3: 2,696 in + 88 out = $0.008
Test 4: 8,844 in + 1,455 out = $0.037
─────────────────────────────────────
Total: $0.190 ✅ (CORRECT - matches your $0.20 account)
```

## Fix Applied

Updated `tools/pricing.py` with correct 2026 pricing:
- `gpt-4o`: $2.50/$10.00 (was $5.00/$15.00)

## Note on Historical Data

⚠️ **Important**: Existing runs in the database were calculated with old pricing, so they show higher costs than actual. New runs will use correct pricing.

To recalculate existing costs, you would need to:
1. Recalculate costs for all runs using new pricing
2. Update the database

But for new runs going forward, costs will be accurate!

## Verification

After the fix:
- New runs will calculate: ~$0.19 for the same test suite
- Matches your OpenAI account: ~$0.20 ✅
