"""
Memory and Learning System
Stores successful action patterns and learns from outcomes
"""
import json
import os
from datetime import datetime
from collections import defaultdict

MEMORY_FILE = "agent_memory.json"

class AgentMemory:
    def __init__(self):
        self.memory_file = MEMORY_FILE
        self.memory = self._load_memory()
        self.successful_patterns = self.memory.get("successful_patterns", {})
        self.failed_patterns = self.memory.get("failed_patterns", {})
        self.action_rewards = self.memory.get("action_rewards", defaultdict(float))
        
    def _load_memory(self):
        """Load memory from file"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "successful_patterns": {},
            "failed_patterns": {},
            "action_rewards": {},
            "last_updated": None
        }
    
    def _save_memory(self):
        """Save memory to file"""
        self.memory["successful_patterns"] = self.successful_patterns
        self.memory["failed_patterns"] = self.failed_patterns
        self.memory["action_rewards"] = dict(self.action_rewards)
        self.memory["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            print(f"  ⚠️  Failed to save memory: {e}")
    
    def record_success(self, context, action_sequence, outcome):
        """Record a successful action pattern"""
        context_key = self._get_context_key(context)
        
        if context_key not in self.successful_patterns:
            self.successful_patterns[context_key] = []
        
        # Clean action sequence to avoid circular references
        cleaned_actions = self._clean_action_sequence(action_sequence)
        
        pattern = {
            "actions": cleaned_actions,
            "outcome": outcome,
            "timestamp": datetime.now().isoformat(),
            "count": 1
        }
        
        # Check if similar pattern exists
        for existing in self.successful_patterns[context_key]:
            if self._patterns_similar(existing["actions"], action_sequence):
                existing["count"] += 1
                existing["timestamp"] = datetime.now().isoformat()
                return
        
        self.successful_patterns[context_key].append(pattern)
        self._save_memory()
    
    def record_failure(self, context, action_sequence, reason):
        """Record a failed action pattern"""
        context_key = self._get_context_key(context)
        
        if context_key not in self.failed_patterns:
            self.failed_patterns[context_key] = []
        
        # Clean action sequence to avoid circular references
        cleaned_actions = self._clean_action_sequence(action_sequence)
        
        pattern = {
            "actions": cleaned_actions,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "count": 1
        }
        
        # Check if similar pattern exists
        for existing in self.failed_patterns[context_key]:
            if self._patterns_similar(existing["actions"], action_sequence):
                existing["count"] += 1
                existing["timestamp"] = datetime.now().isoformat()
                return
        
        self.failed_patterns[context_key].append(pattern)
        self._save_memory()
    
    def get_successful_pattern(self, context):
        """Get a successful pattern for the given context"""
        context_key = self._get_context_key(context)
        
        # First try exact match
        if context_key in self.successful_patterns:
            patterns = self.successful_patterns[context_key]
            if patterns:
                # Return most recent and most used pattern
                best = max(patterns, key=lambda p: (p["count"], p["timestamp"]))
                return best["actions"]
        
        # If no exact match, try matching by app + test_goal (ignore screen)
        # Only match patterns from the SAME app (DuckDuckGo vs Obsidian stay separate)
        app = context.get("app", "obsidian").lower()
        test_goal = context.get("test_goal", "").lower()
        if test_goal:
            # Normalize test_goal: remove quotes, extra spaces, take first 50 chars
            normalized_goal = test_goal.replace("'", "").replace('"', '').strip()[:50]
            
            for stored_key, patterns in self.successful_patterns.items():
                # Stored key format: "app:screen:test_goal" - require same app
                parts = stored_key.split(":", 2)
                if len(parts) >= 3:
                    stored_app, stored_screen, stored_goal = parts[0], parts[1], parts[2]
                    if stored_app != app:
                        continue  # Different app - don't use Obsidian pattern for DuckDuckGo
                    stored_goal_normalized = stored_goal.replace("'", "").replace('"', '').strip()
                    
                    if stored_goal_normalized == normalized_goal and patterns:
                        best = max(patterns, key=lambda p: (p["count"], p["timestamp"]))
                        return best["actions"]
                    if (normalized_goal in stored_goal_normalized or
                        stored_goal_normalized in normalized_goal) and patterns:
                        best = max(patterns, key=lambda p: (p["count"], p["timestamp"]))
                        return best["actions"]
                # Backward compat: old keys were "screen:test_goal" (2 parts)
                elif len(parts) == 2:
                    stored_goal = parts[1]
                    stored_goal_normalized = stored_goal.replace("'", "").replace('"', '').strip()
                    if (stored_goal_normalized == normalized_goal or
                        normalized_goal in stored_goal_normalized or
                        stored_goal_normalized in normalized_goal) and patterns:
                        best = max(patterns, key=lambda p: (p["count"], p["timestamp"]))
                        return best["actions"]
        
        return None
    
    def should_avoid_action(self, context, action):
        """Check if an action should be avoided based on past failures"""
        context_key = self._get_context_key(context)
        
        if context_key in self.failed_patterns:
            for pattern in self.failed_patterns[context_key]:
                if pattern["count"] >= 3:  # Failed 3+ times
                    if action in pattern["actions"]:
                        return True, pattern["reason"]
        
        return False, None
    
    def update_reward(self, action_type, reward):
        """Update reward for an action type (reinforcement learning)"""
        self.action_rewards[action_type] = self.action_rewards.get(action_type, 0.0) * 0.9 + reward * 0.1
        self._save_memory()
    
    def get_action_reward(self, action_type):
        """Get reward score for an action type"""
        return self.action_rewards.get(action_type, 0.0)
    
    def _get_context_key(self, context):
        """Generate a key from context (app, screen, test goal). Separate keys per app (DuckDuckGo vs Obsidian)."""
        app = context.get("app", "obsidian").lower()
        screen = context.get("current_screen", "unknown")
        test_goal = context.get("test_goal", "").lower()[:50]  # First 50 chars
        return f"{app}:{screen}:{test_goal}"
    
    def _clean_action_sequence(self, action_sequence):
        """Clean action sequence to remove circular references and non-serializable data"""
        cleaned = []
        for action in action_sequence:
            if isinstance(action, dict):
                cleaned_action = {
                    "action": action.get("action"),
                    "description": action.get("description"),
                    "text": action.get("text"),
                    "target": action.get("target"),
                    "x": action.get("x"),
                    "y": action.get("y"),
                    "code": action.get("code"),
                }
                # Remove None values
                cleaned_action = {k: v for k, v in cleaned_action.items() if v is not None}
                cleaned.append(cleaned_action)
        return cleaned
    
    def _patterns_similar(self, pattern1, pattern2):
        """Check if two action patterns are similar"""
        if len(pattern1) != len(pattern2):
            return False
        
        for a1, a2 in zip(pattern1, pattern2):
            if a1.get("action") != a2.get("action"):
                return False
            # Allow some variation in coordinates
            if a1.get("action") == "tap":
                # Coordinates can vary
                pass
        
        return True

# Global memory instance
memory = AgentMemory()

