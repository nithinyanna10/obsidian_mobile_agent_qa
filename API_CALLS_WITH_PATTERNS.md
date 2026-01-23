# API Calls with Successful Patterns

## Quick Answer: **Almost 0, but not exactly 0** ⚡

When you have a successful pattern in memory, **OpenAI API calls are skipped** for those steps, but there are still some API calls that might happen.

---

## What Gets Skipped ✅

### **When Pattern Exists and Matches Current Step:**

1. **Screenshot is taken** (via ADB - this is free, local)
2. **Android state is checked** (via ADB - this is free, local)
3. **Memory pattern is loaded** (from `agent_memory.json` - free, local)
4. **Action is returned from memory** (instant, free)
5. **OpenAI API call is SKIPPED** ❌ (this is the expensive part!)

**Result:** That step costs **$0.00** in API calls! 💰

---

## What Still Happens (But Doesn't Cost Money)

### **Screenshots:**
- Screenshots are **still taken** via ADB (Android Debug Bridge)
- They're saved locally for logging/debugging
- **But they're NOT sent to OpenAI** when using memory patterns
- Cost: **$0** (local operation)

### **Android State:**
- UI XML is **still dumped** via ADB
- Current screen is **still detected** via ADB
- **But this is all local** - no API calls
- Cost: **$0** (local operation)

---

## When API Calls Still Happen

### **1. Pattern Completion Verification**
When you complete a pattern, the system might call OpenAI to verify the goal is achieved:

```python
elif current_step >= len(successful_pattern):
    # We've completed the pattern - check if test goal is achieved
    print("💾 Completed memory pattern, checking if goal achieved...")
    # Continue to normal planning to verify completion
```

**This is 1 API call** to verify completion.

### **2. New/Unknown Steps**
If the pattern doesn't cover all steps, remaining steps use OpenAI:

```
Pattern has 5 steps
You're on step 6 → Uses OpenAI (no pattern for this step)
```

### **3. Pattern Mismatch**
If the context doesn't match (different screen, different test), it falls back to OpenAI.

### **4. Final Verification**
The supervisor might use OpenAI to verify the final state.

---

## Example: "Create Vault" Test

### **First Run (No Pattern):**
```
Step 1: Screenshot → OpenAI API call → Action ✅ ($0.05)
Step 2: Screenshot → OpenAI API call → Action ✅ ($0.05)
Step 3: Screenshot → OpenAI API call → Action ✅ ($0.05)
Step 4: Screenshot → OpenAI API call → Action ✅ ($0.05)
Step 5: Screenshot → OpenAI API call → Verify ✅ ($0.05)
─────────────────────────────────────────────────────
Total: 5 API calls = ~$0.25
```

### **Second Run (Pattern Exists):**
```
Step 1: Screenshot → Memory pattern → Action ✅ ($0.00) ⚡
Step 2: Screenshot → Memory pattern → Action ✅ ($0.00) ⚡
Step 3: Screenshot → Memory pattern → Action ✅ ($0.00) ⚡
Step 4: Screenshot → Memory pattern → Action ✅ ($0.00) ⚡
Step 5: Screenshot → OpenAI API call → Verify ✅ ($0.05)
─────────────────────────────────────────────────────
Total: 1 API call = ~$0.05 (80% savings!)
```

---

## Real-World Scenario

### **Your Current Memory:**
- 4 successful patterns
- Each pattern might have 3-10 steps

### **If You Run All 4 Tests Again:**

**Without patterns:** ~20-30 API calls = ~$0.20-$0.30  
**With patterns:** ~4-8 API calls = ~$0.04-$0.08

**Savings: ~70-80%** 💰

---

## Code Evidence

From `agents/planner.py` (line ~299-307):

```python
if successful_pattern and len(successful_pattern) > 0:
    current_step = len(action_history)
    
    if current_step < len(successful_pattern):
        # Use action from memory - SKIP OpenAI call!
        next_action_from_memory = successful_pattern[current_step]
        print("💾 Using action from memory - skipping OpenAI call")
        return next_action_from_memory  # ← Returns here, never calls OpenAI!
```

**This early return means:**
- No `call_openai_with_retry()` is called
- No screenshot is sent to OpenAI
- No tokens are used
- **API call count = 0 for this step**

---

## Summary

| Scenario | API Calls | Cost |
|----------|-----------|------|
| **No pattern** | ~5-7 per test | ~$0.10-$0.15 |
| **With pattern (all steps match)** | ~1-2 per test | ~$0.02-$0.04 |
| **With pattern (partial match)** | ~2-4 per test | ~$0.04-$0.08 |

**Bottom line:** Patterns can reduce API calls by **70-90%**, but you'll still have a few calls for verification and unmatched steps.

---

## How to Check Your Savings

After running with patterns, check the database:

```bash
python3 view_latest_suite.py
```

Compare `api_calls` between:
- First run (no patterns)
- Second run (with patterns)

You should see a significant reduction! 📉
