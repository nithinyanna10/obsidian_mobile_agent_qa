# RL System Usage - How It Works When You Run

## TL;DR: **You're NOT starting from scratch!** 🎯

The RL system **persists between runs** and actively uses learned patterns to:
1. **Skip OpenAI calls** when it knows what to do
2. **Guide action selection** using reward scores
3. **Avoid failed actions** that didn't work before
4. **Continue learning** from each run

---

## How It Works

### 1. **Memory Persistence** 💾

The RL memory is stored in `agent_memory.json` and **automatically loaded** when you start a run:

```python
# On startup, memory loads from file:
memory = AgentMemory()  # Loads agent_memory.json
```

**Your current memory status:**
- ✅ 4 successful patterns (contexts where it knows what works)
- ⚠️ 10 failed patterns (actions to avoid)
- 📊 5 action types with reward scores
- 🕐 Last updated: Today (Jan 23, 2026)

### 2. **Active RL Usage During Runs** 🚀

#### **A. Pattern Matching (Saves API Calls!)**

When the planner sees a familiar context, it checks memory first:

```python
# In planner.py, line ~293
successful_pattern = memory.get_successful_pattern(context)

if successful_pattern and len(successful_pattern) > 0:
    # Use stored pattern - SKIP OpenAI call!
    next_action = successful_pattern[current_step]
    print("💾 Using action from memory - skipping OpenAI call")
```

**What this means:**
- If you've successfully completed "Create Vault" before, it will reuse those exact actions
- **No OpenAI API call needed** - saves time and money! 💰
- Only calls OpenAI if it's a new situation or pattern is complete

#### **B. Reward-Based Action Selection**

When `USE_REWARD_SELECTION=True` (in `config.py`), the planner uses reward scores:

```python
# Get reward scores for actions
tap_reward = memory.get_action_reward("tap")    # e.g., 0.200
type_reward = memory.get_action_reward("type")   # e.g., 0.200

# Include in prompt to guide LLM
reward_hint = f"💰 Reward scores: tap={tap_reward:.2f}, type={type_reward:.2f}"
```

**Your current rewards:**
- `type`: 0.200 (good!)
- `tap`: 0.200 (good!)
- `focus`: 0.198 (good!)
- `open_app`: 0.195 (good!)
- `key`: 0.020 (low - rarely used)

#### **C. Failure Avoidance**

The system remembers actions that failed 3+ times:

```python
should_avoid, reason = memory.should_avoid_action(context, action)
if should_avoid:
    # Don't try this action again!
```

---

## What Happens When You Run

### **Scenario 1: Familiar Test (Has Pattern in Memory)**

```
1. Load memory from agent_memory.json ✅
2. Check: "Have I seen this test before?" → YES
3. Get successful pattern from memory
4. Execute pattern step-by-step (NO OpenAI calls!)
5. Verify goal achieved
6. Update pattern count (if successful again)
```

**Result:** Fast, cheap, reliable! ⚡

### **Scenario 2: New Test (No Pattern in Memory)**

```
1. Load memory from agent_memory.json ✅
2. Check: "Have I seen this test before?" → NO
3. Use OpenAI to plan actions (normal flow)
4. Execute actions
5. Record outcome in memory:
   - If success → save as successful pattern
   - If failure → record as failed pattern
   - Update action rewards
6. Save to agent_memory.json
```

**Result:** Learns and saves for next time! 🧠

### **Scenario 3: Partial Pattern Match**

```
1. Load memory ✅
2. Pattern exists but we're past it → Check if goal achieved
3. If not achieved → Use OpenAI to continue
4. Update pattern with new steps if successful
```

---

## Memory File Structure

The `agent_memory.json` file contains:

```json
{
  "successful_patterns": {
    "vault_home:create vault": [
      {"action": "tap", "description": "Tap Create Vault", ...},
      {"action": "type", "text": "MyVault", ...},
      ...
    ]
  },
  "failed_patterns": {
    "settings:change theme": [
      {"action": "tap", "description": "Tap wrong button", ...}
    ]
  },
  "action_rewards": {
    "tap": 0.200,
    "type": 0.200,
    "key": 0.020
  },
  "last_updated": "2026-01-23T12:55:06.223949"
}
```

---

## Key Benefits

1. **Cost Savings** 💰
   - Reuses successful patterns → fewer OpenAI API calls
   - Your memory has 4 patterns → potential to skip many calls!

2. **Speed** ⚡
   - Pattern matching is instant (no API wait time)
   - Faster test execution for familiar scenarios

3. **Reliability** 🎯
   - Uses proven action sequences
   - Avoids actions that failed before

4. **Continuous Learning** 📈
   - Each run adds to memory
   - Gets smarter over time

---

## Configuration

Check `config.py` for RL settings:

```python
USE_REWARD_SELECTION = True  # Use reward scores in prompts
```

---

## Summary

**When you run:**
- ✅ Memory is loaded automatically
- ✅ Successful patterns are reused (saves API calls)
- ✅ Reward scores guide decisions
- ✅ Failed patterns are avoided
- ✅ New learnings are saved for next time

**You're NOT starting from scratch** - the system is using all your accumulated knowledge! 🧠✨
