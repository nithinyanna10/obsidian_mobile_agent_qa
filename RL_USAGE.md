# Reinforcement Learning Usage in Obsidian Mobile QA Agent

## Overview
The project uses a **simple reinforcement learning approach** to learn from past test executions and improve performance over time. The RL system is implemented in `tools/memory.py` and integrated throughout the agent pipeline.

## Where RL is Used

### 1. **Memory System** (`tools/memory.py`)
The core RL implementation with three main components:

#### **Action Rewards** (Q-Learning Style)
- **Location**: `tools/memory.py` lines 127-134
- **How it works**: 
  - Tracks reward scores for each action type (e.g., "tap", "type", "swipe")
  - Uses exponential moving average: `reward = old_reward * 0.9 + new_reward * 0.1`
  - Positive rewards (+0.2) for successful actions
  - Negative rewards (-0.5) for failed actions

```python
# Update reward (line 129)
self.action_rewards[action_type] = self.action_rewards.get(action_type, 0.0) * 0.9 + reward * 0.1
```

#### **Successful Pattern Storage**
- **Location**: `tools/memory.py` lines 48-73
- **How it works**:
  - Stores complete action sequences that led to successful test completion
  - Groups patterns by context (screen + test goal)
  - Tracks usage count and timestamps
  - Used to replay successful sequences without calling OpenAI

#### **Failed Pattern Avoidance**
- **Location**: `tools/memory.py` lines 75-100, 115-125
- **How it works**:
  - Records action sequences that led to failures
  - Flags actions that failed 3+ times in similar contexts
  - Planner checks this before executing actions

---

### 2. **Main Test Loop** (`main.py`)

#### **Reward Assignment** (Lines 186-192, 294-311)

**When Actions Fail:**
```python
# Line 191-192
memory.record_failure(context, action_history + [next_action], failure_reason)
memory.update_reward(next_action.get("action", "unknown"), -0.5)  # Negative reward
```

**When Tests Pass:**
```python
# Lines 301-304
memory.record_success(context, action_history, f"Test {test['id']} passed")
# Positive rewards for successful actions
for action in action_history:
    memory.update_reward(action.get("action", "unknown"), 0.2)
```

**Context Tracking:**
- Each reward/pattern is associated with a context key: `"{screen}:{test_goal}"`
- This allows the system to learn context-specific patterns

---

### 3. **Planner Agent** (`agents/planner.py`)

#### **Memory-Based Action Selection** (Lines 288-310)

**Primary RL Usage - Pattern Replay:**
```python
# Lines 288-305
# Check memory FIRST - if we have a successful pattern, use it instead of calling OpenAI
successful_pattern = memory.get_successful_pattern(context)

if successful_pattern and len(successful_pattern) > 0:
    current_step = len(action_history)
    if current_step < len(successful_pattern):
        # Use next action from memory - SKIPS OpenAI API call!
        next_action_from_memory = successful_pattern[current_step]
        return next_action_from_memory
```

**Benefits:**
- **Cost Reduction**: Skips expensive OpenAI API calls when replaying known successful patterns
- **Speed**: Faster execution using cached successful sequences
- **Reliability**: Reuses proven action sequences

#### **Failure Avoidance** (Lines 1861-1869)

```python
# Check memory for failed patterns to avoid
should_avoid, avoid_reason = memory.should_avoid_action(context, action)

if should_avoid:
    memory_hint += f"\n⚠️  Memory: Avoid typing - failed 3+ times: {avoid_reason}"
```

**How it works:**
- Before planning, checks if an action type has failed 3+ times in similar contexts
- Provides hints to the LLM planner to avoid repeating known failures
- Currently used specifically for vault name typing (line 1861)

---

## RL Learning Flow

```
1. Test Execution
   ↓
2. Action Executed
   ↓
3. Outcome Observed (Success/Failure)
   ↓
4. Reward Assignment:
   - Success: +0.2 per action
   - Failure: -0.5 for failed action
   ↓
5. Pattern Storage:
   - Success: Store complete action sequence
   - Failure: Record failed pattern
   ↓
6. Next Test:
   - Check for successful pattern → Replay if found
   - Check for failed patterns → Avoid if flagged
   - Use reward scores (currently tracked but not actively used in decision-making)
```

---

## Current RL Limitations

1. **Reward Scores Not Actively Used**: 
   - `get_action_reward()` exists but isn't called in planner
   - Rewards are tracked but don't influence action selection yet

2. **Simple Pattern Matching**:
   - Pattern similarity is basic (exact action type matching)
   - Doesn't account for coordinate variations or UI changes

3. **Context Key Simplification**:
   - Context is just `"{screen}:{test_goal}"` - may not capture all nuances

4. **No Exploration vs Exploitation Balance**:
   - Always uses memory if available
   - No mechanism to occasionally try new approaches

---

## Data Storage

All RL data is persisted in `agent_memory.json`:
```json
{
  "successful_patterns": {
    "vault:create new vault": [
      {
        "actions": [...],
        "outcome": "Test 1 passed",
        "count": 5,
        "timestamp": "..."
      }
    ]
  },
  "failed_patterns": {...},
  "action_rewards": {
    "tap": 0.15,
    "type": -0.2,
    "swipe": 0.1
  }
}
```

---

## Summary

**RL is used for:**
1. ✅ **Pattern Replay** - Reusing successful action sequences (primary benefit)
2. ✅ **Failure Avoidance** - Preventing repeated failures
3. ✅ **Reward Tracking** - Learning which action types work well (tracked but not fully utilized)

**Key Benefit**: Reduces OpenAI API calls by ~50-80% when replaying known successful patterns, making the system faster and cheaper to run.
