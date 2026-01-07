# API Call Tracking Implementation

## Overview

This document describes the accurate API call tracking and cost calculation system implemented for the benchmark logging.

## Key Principles

1. **No Guessing**: Use actual numbers from API responses
2. **Count Every Call**: Increment `api_calls` for every LLM endpoint hit, even on failures
3. **Real Token Counts**: Use `response.usage.prompt_tokens` and `response.usage.completion_tokens`
4. **Accurate Pricing**: Calculate cost from actual tokens using pricing map

## Implementation Details

### 1. API Calls Counter

**Definition**: Number of times an LLM endpoint is called in a run.

**Implementation**:
- Initialize `api_calls = 0` at run start
- Increment on every API call attempt (success or failure)
- Count rate-limited calls
- Count failed calls (with 0 tokens)

**Location**: `tools/benchmark_logger.py` - `log_api_call()` method

### 2. Token Counting

**Definition**:
- `tokens_in`: Total input/prompt tokens sent across the run
- `tokens_out`: Total output/completion tokens generated across the run

**Source**: OpenAI API response `usage` fields:
- `response.usage.prompt_tokens` (Chat Completions API)
- `response.usage.completion_tokens` (Chat Completions API)
- `response.usage.input_tokens` (Responses API)
- `response.usage.output_tokens` (Responses API)

**Implementation**:
```python
if hasattr(response, 'usage') and response.usage:
    if hasattr(response.usage, 'prompt_tokens'):
        tokens_in = response.usage.prompt_tokens
    elif hasattr(response.usage, 'input_tokens'):
        tokens_in = response.usage.input_tokens
    
    if hasattr(response.usage, 'completion_tokens'):
        tokens_out = response.usage.completion_tokens
    elif hasattr(response.usage, 'output_tokens'):
        tokens_out = response.usage.output_tokens
```

**Location**: `agents/planner.py` and `agents/supervisor.py` - `call_openai_with_retry()` function

### 3. Cost Calculation

**Definition**: Total estimated cost of all LLM calls in the run.

**Formula**:
```
cost = (tokens_in / 1_000_000) * P_in + (tokens_out / 1_000_000) * P_out
```

Where `P_in` and `P_out` are $/1M tokens for the model.

**Pricing Map**: `tools/pricing.py`
```python
PRICE_PER_1M = {
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-4o": {"in": 5.00, "out": 15.00},
    "gpt-4-turbo": {"in": 10.00, "out": 30.00},
    "gpt-4": {"in": 30.00, "out": 60.00},
    "gpt-3.5-turbo": {"in": 0.50, "out": 1.50},
}
```

**Implementation**: `tools/pricing.py` - `calculate_cost()` function

### 4. Error Handling

**Rate Limits (429)**:
- Count as API call (with 0 tokens)
- Set `rate_limit_fail = 1`
- Retry with exponential backoff

**Other Errors**:
- Count as API call (with 0 tokens)
- Log error but don't retry

**Missing Usage**:
- If `usage` field is missing, log `tokens_in = 0`, `tokens_out = 0`
- Don't fabricate token counts
- Cost will be 0 for that call

### 5. Logging Pattern

For every API call:
1. Extract tokens from `response.usage` (if available)
2. Call `logger.log_api_call(tokens_in, tokens_out, model)`
3. Logger accumulates totals and calculates cost

**Per Run Totals**:
- `runs.tokens_in`: Sum of all `tokens_in` from calls
- `runs.tokens_out`: Sum of all `tokens_out` from calls
- `runs.api_calls`: Count of all API calls
- `runs.cost_usd`: Sum of all calculated costs

## Files Modified

1. **`tools/pricing.py`**: Pricing map and cost calculation function
2. **`tools/benchmark_logger.py`**: Updated `log_api_call()` to use pricing map
3. **`agents/planner.py`**: Extract actual tokens from API response
4. **`agents/supervisor.py`**: Extract actual tokens from API response

## Verification

To verify accuracy:
1. Check that `api_calls` matches number of OpenAI API calls made
2. Verify `tokens_in` and `tokens_out` match OpenAI dashboard
3. Compare `cost_usd` with OpenAI billing (should match closely)

## Future Enhancements

1. **Per-Call Logging**: Log individual calls to a `calls` table for detailed analysis
2. **Latency Tracking**: Measure and log API call latency
3. **Image Token Counting**: For vision models, track image token usage separately
4. **Multi-Model Support**: Track costs across different models in same run

