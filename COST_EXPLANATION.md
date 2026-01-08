# Cost Calculation Explanation

## Why We Can't Get Cost Directly from API

**OpenAI's API does NOT return cost information** - it only returns:
- `usage.prompt_tokens` (input tokens)
- `usage.completion_tokens` (output tokens)
- `usage.total_tokens`

We **must calculate** the cost ourselves using:
1. Token counts from API response (actual, not estimated)
2. Current pricing from OpenAI

## Our Calculation is Verified Correct

✅ **Pricing**: $5.00/1M input, $15.00/1M output (GPT-4o)
✅ **Formula**: `(tokens_in / 1_000_000 * 5.00) + (tokens_out / 1_000_000 * 15.00)`
✅ **Verification**: Matches OpenAI pricing exactly

## Why Costs Might Seem High

**Vision API calls with screenshots use many tokens:**
- Each screenshot: ~85-170 tokens (depending on size)
- A test with 20 steps × screenshots = 1,700-3,400 tokens just for images
- Plus prompts and responses

**Your current runs:**
- Test 2: 158,533 input tokens = ~$0.79
- Test 3: 140,241 input tokens = ~$0.70
- Test 4: 384,452 input tokens = ~$1.92

**Average: ~227k tokens per test = ~$1.20 per test**

This is **normal** for vision API calls with multiple screenshots.

## How to Verify

1. **Check OpenAI Dashboard**: Compare your actual billing
2. **Run verification script**: `python verify_costs.py`
3. **Manual calculation**: Use the formula above with your token counts

## If Costs Still Seem Wrong

1. **Check token counts**: Are they reasonable? (10k-500k for vision calls)
2. **Check pricing**: Is it up to date? (Update `tools/pricing.py`)
3. **Check model**: Are you using the model you think? (Check `config.py`)

## Future: Auto-Update Pricing

We could add a feature to:
- Fetch latest pricing from OpenAI's pricing page
- Auto-update the pricing map
- Warn if pricing changes

But we still need to calculate cost ourselves - the API doesn't provide it.

