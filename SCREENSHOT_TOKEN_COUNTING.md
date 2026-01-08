# Screenshot Token Counting - How It Works

## Key Point

**We ONLY count tokens for screenshots that are actually sent to OpenAI's API.**

## How It Works

### 1. Screenshots Are Taken in Many Places
- `main.py`: Initial/final screenshots
- `agents/executor.py`: After each action
- `agents/planner.py`: For verification checks

### 2. But Tokens Are Only Counted When:
- Screenshot is included in an API call (`image_url` in messages)
- API response includes `usage.prompt_tokens` and `usage.completion_tokens`
- We extract these **actual token counts from OpenAI's response**

### 3. Screenshots NOT Sent = 0 Tokens

If a screenshot is:
- ✅ Taken and sent to API → Counted in tokens
- ❌ Taken but NOT sent to API → **0 tokens** (not counted)

## Current Implementation

```python
# In call_openai_with_retry():
response = client.chat.completions.create(...)

# Extract ACTUAL token counts from API response
tokens_in = response.usage.prompt_tokens  # Real tokens from OpenAI
tokens_out = response.usage.completion_tokens  # Real tokens from OpenAI

# These counts ONLY include screenshots that were sent in this API call
```

## Verification

The token counts you see are:
- ✅ From OpenAI's actual API responses
- ✅ Only include screenshots sent to the API
- ✅ Match what OpenAI bills you

## Example

**Scenario:**
- 10 screenshots taken during a test
- 3 screenshots sent to OpenAI API
- 7 screenshots NOT sent (just stored locally)

**Token Count:**
- Only the 3 screenshots sent to API are counted
- The 7 unsent screenshots = 0 tokens

## Why Token Counts Might Seem High

Even with only sent screenshots counted:
- Vision API calls are expensive
- Each screenshot: ~85-170 tokens (depending on size)
- A test with 5 API calls × 1 screenshot each = 425-850 tokens just for images
- Plus prompts and responses

**This is normal and accurate** - we're only counting what OpenAI actually charges for.

## Debug Output

When running tests, you'll now see:
```
📊 API call: 1 screenshot(s) sent, 15,234 input tokens, 1,234 output tokens
```

This shows exactly how many screenshots were in each API call and the actual token usage.

