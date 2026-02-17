"""
Memory and Learning System
Stores successful action patterns and learns from outcomes.
Each application (obsidian, duckduckgo, settings) has its own memory file.
"""
import json
import os
from datetime import datetime
from collections import defaultdict

MEMORY_FILE_PREFIX = "agent_memory"
MEMORY_FILE_EXT = ".json"
LEGACY_MEMORY_FILE = "agent_memory.json"


def _memory_file(app):
    """Path to memory file for the given app."""
    app_normalized = (app or "obsidian").lower().strip()
    if not app_normalized:
        app_normalized = "obsidian"
    return f"{MEMORY_FILE_PREFIX}_{app_normalized}{MEMORY_FILE_EXT}"


class AgentMemory:
    """
    Per-application memory. Each app has its own file:
    - agent_memory_obsidian.json
    - agent_memory_duckduckgo.json
    - agent_memory_settings.json
    """

    def __init__(self):
        self._cache = {}  # app -> { successful_patterns, failed_patterns, action_rewards, last_updated }

    def _get_app_data(self, app):
        """Load and return memory data for the given app (cached)."""
        app_key = (app or "obsidian").lower().strip() or "obsidian"
        if app_key not in self._cache:
            path = _memory_file(app_key)
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    self._cache[app_key] = {
                        "successful_patterns": data.get("successful_patterns", {}),
                        "failed_patterns": data.get("failed_patterns", {}),
                        "action_rewards": defaultdict(float, data.get("action_rewards", {})),
                        "last_updated": data.get("last_updated"),
                    }
                except Exception:
                    self._cache[app_key] = self._empty_app_data()
            else:
                # Migrate from legacy single file if present
                migrated = self._migrate_from_legacy(app_key)
                self._cache[app_key] = migrated if migrated else self._empty_app_data()
        return self._cache[app_key]

    def _empty_app_data(self):
        return {
            "successful_patterns": {},
            "failed_patterns": {},
            "action_rewards": defaultdict(float),
            "last_updated": None,
        }

    def _migrate_from_legacy(self, app_key):
        """If legacy agent_memory.json exists, extract this app's data and save to per-app file."""
        if not os.path.exists(LEGACY_MEMORY_FILE):
            return None
        try:
            with open(LEGACY_MEMORY_FILE, "r") as f:
                legacy = json.load(f)
        except Exception:
            return None
        successful = {}
        failed = {}
        for key, val in (legacy.get("successful_patterns") or {}).items():
            parts = key.split(":", 2)
            if len(parts) >= 3 and parts[0].lower() == app_key:
                in_file_key = f"{parts[1]}:{parts[2]}"
                successful[in_file_key] = val
            elif len(parts) == 2 and app_key == "obsidian":
                successful[key] = val
        for key, val in (legacy.get("failed_patterns") or {}).items():
            parts = key.split(":", 2)
            if len(parts) >= 3 and parts[0].lower() == app_key:
                in_file_key = f"{parts[1]}:{parts[2]}"
                failed[in_file_key] = val
            elif len(parts) == 2 and app_key == "obsidian":
                failed[key] = val
        rewards = legacy.get("action_rewards") or {}
        if not successful and not failed and not rewards:
            return None
        data = {
            "successful_patterns": successful,
            "failed_patterns": failed,
            "action_rewards": defaultdict(float, rewards if app_key == "obsidian" else {}),
            "last_updated": legacy.get("last_updated"),
        }
        self._cache[app_key] = data
        self._save_app_data(app_key)
        return data

    def _save_app_data(self, app):
        """Persist memory for the given app to its file."""
        app_key = (app or "obsidian").lower().strip() or "obsidian"
        if app_key not in self._cache:
            return
        data = self._cache[app_key]
        path = _memory_file(app_key)
        out = {
            "successful_patterns": data["successful_patterns"],
            "failed_patterns": data["failed_patterns"],
            "action_rewards": dict(data["action_rewards"]),
            "last_updated": datetime.now().isoformat(),
        }
        try:
            with open(path, "w") as f:
                json.dump(out, f, indent=2)
        except Exception as e:
            print(f"  ⚠️  Failed to save memory for app '{app_key}': {e}")

    def _context_key_for_app(self, context):
        """Key within an app's memory (screen + test_goal, no app prefix)."""
        screen = context.get("current_screen", "unknown")
        test_goal = (context.get("test_goal") or "").lower()[:50]
        return f"{screen}:{test_goal}"

    def record_success(self, context, action_sequence, outcome):
        """Record a successful action pattern for the app in context."""
        app = context.get("app", "obsidian").lower().strip() or "obsidian"
        data = self._get_app_data(app)
        key = self._context_key_for_app(context)

        if key not in data["successful_patterns"]:
            data["successful_patterns"][key] = []

        cleaned_actions = self._clean_action_sequence(action_sequence)
        pattern = {
            "actions": cleaned_actions,
            "outcome": outcome,
            "timestamp": datetime.now().isoformat(),
            "count": 1,
        }

        for existing in data["successful_patterns"][key]:
            if self._patterns_similar(existing["actions"], cleaned_actions):
                existing["count"] += 1
                existing["timestamp"] = datetime.now().isoformat()
                self._save_app_data(app)
                return

        data["successful_patterns"][key].append(pattern)
        self._save_app_data(app)

    def record_failure(self, context, action_sequence, reason):
        """Record a failed action pattern for the app in context."""
        app = context.get("app", "obsidian").lower().strip() or "obsidian"
        data = self._get_app_data(app)
        key = self._context_key_for_app(context)

        if key not in data["failed_patterns"]:
            data["failed_patterns"][key] = []

        cleaned_actions = self._clean_action_sequence(action_sequence)
        pattern = {
            "actions": cleaned_actions,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "count": 1,
        }

        for existing in data["failed_patterns"][key]:
            if self._patterns_similar(existing["actions"], cleaned_actions):
                existing["count"] += 1
                existing["timestamp"] = datetime.now().isoformat()
                self._save_app_data(app)
                return

        data["failed_patterns"][key].append(pattern)
        self._save_app_data(app)

    def get_successful_pattern(self, context):
        """Get a successful pattern for the given context (same app only)."""
        app = context.get("app", "obsidian").lower().strip() or "obsidian"
        data = self._get_app_data(app)
        key = self._context_key_for_app(context)
        patterns = data["successful_patterns"]

        if key in patterns and patterns[key]:
            best = max(patterns[key], key=lambda p: (p["count"], p["timestamp"]))
            return best["actions"]

        test_goal = (context.get("test_goal") or "").lower().strip()[:50]
        if test_goal:
            normalized_goal = test_goal.replace("'", "").replace('"', "").strip()
            for stored_key, pattern_list in patterns.items():
                if not pattern_list:
                    continue
                # stored_key is "screen:test_goal"
                parts = stored_key.split(":", 1)
                stored_goal = (parts[1] if len(parts) >= 2 else stored_key).replace("'", "").replace('"', "").strip()
                if stored_goal == normalized_goal or normalized_goal in stored_goal or stored_goal in normalized_goal:
                    best = max(pattern_list, key=lambda p: (p["count"], p["timestamp"]))
                    return best["actions"]

        return None

    def should_avoid_action(self, context, action):
        """Check if an action should be avoided based on past failures (same app only)."""
        app = context.get("app", "obsidian").lower().strip() or "obsidian"
        data = self._get_app_data(app)
        key = self._context_key_for_app(context)

        if key in data["failed_patterns"]:
            for pattern in data["failed_patterns"][key]:
                if pattern["count"] >= 3:
                    if action in pattern["actions"]:
                        return True, pattern["reason"]
        return False, None

    def update_reward(self, action_type, reward, app="obsidian"):
        """Update reward for an action type for the given app."""
        app_key = (app or "obsidian").lower().strip() or "obsidian"
        data = self._get_app_data(app_key)
        data["action_rewards"][action_type] = (
            data["action_rewards"].get(action_type, 0.0) * 0.9 + reward * 0.1
        )
        self._save_app_data(app_key)

    def get_action_reward(self, action_type, app="obsidian"):
        """Get reward score for an action type for the given app."""
        app_key = (app or "obsidian").lower().strip() or "obsidian"
        data = self._get_app_data(app_key)
        return data["action_rewards"].get(action_type, 0.0)

    def _clean_action_sequence(self, action_sequence):
        """Clean action sequence to remove circular references and non-serializable data."""
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
                    "element": action.get("element"),
                }
                cleaned_action = {k: v for k, v in cleaned_action.items() if v is not None}
                cleaned.append(cleaned_action)
        return cleaned

    def _patterns_similar(self, pattern1, pattern2):
        """Check if two action patterns are similar."""
        if len(pattern1) != len(pattern2):
            return False
        for a1, a2 in zip(pattern1, pattern2):
            if a1.get("action") != a2.get("action"):
                return False
        return True


# Global memory instance (per-app data is loaded/saved by app key)
memory = AgentMemory()
