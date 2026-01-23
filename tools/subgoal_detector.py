"""
Subgoal Detection System
Automatically detects and tracks subgoals for Obsidian mobile QA tasks
"""
from typing import List, Dict, Any, Optional
import re

class SubgoalDetector:
    """Detects subgoals from test descriptions and tracks progress"""
    
    # Common subgoals for Obsidian tasks
    SUBGOAL_PATTERNS = {
        "open_app": [
            r"open.*obsidian",
            r"launch.*app",
        ],
        "create_vault": [
            r"create.*vault",
            r"new.*vault",
            r"vault.*named",
        ],
        "enter_vault": [
            r"enter.*vault",
            r"open.*vault",
            r"use.*folder",
        ],
        "create_note": [
            r"create.*note",
            r"new.*note",
            r"note.*titled",
        ],
        "type_title": [
            r"title.*meeting notes",
            r"note.*title",
        ],
        "type_content": [
            r"daily standup",
            r"note.*content",
            r"body.*text",
        ],
        "open_settings": [
            r"open.*settings",
            r"navigate.*settings",
        ],
        "open_appearance": [
            r"appearance",
            r"appearance.*tab",
        ],
        "verify_element": [
            r"verify",
            r"check.*color",
            r"find.*button",
        ],
    }
    
    def __init__(self):
        self.detected_subgoals = []
        self.achieved_subgoals = []
    
    def detect_subgoals(self, test_text: str) -> List[Dict[str, Any]]:
        """
        Detect subgoals from test description
        
        Args:
            test_text: Test description
            
        Returns:
            List of detected subgoals with metadata
        """
        subgoals = []
        test_lower = test_text.lower()
        
        # Detect subgoals based on patterns
        for subgoal_type, patterns in self.SUBGOAL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, test_lower):
                    subgoals.append({
                        "type": subgoal_type,
                        "description": self._get_subgoal_description(subgoal_type, test_text),
                        "achieved": False
                    })
                    break  # Only add once per type
        
        # Add specific subgoals based on test content
        if "create" in test_lower and "vault" in test_lower:
            if "internvault" in test_lower:
                subgoals.append({
                    "type": "type_vault_name",
                    "description": "Type vault name 'InternVault'",
                    "achieved": False
                })
                subgoals.append({
                    "type": "confirm_vault_creation",
                    "description": "Confirm vault creation",
                    "achieved": False
                })
        
        if "meeting notes" in test_lower:
            subgoals.append({
                "type": "type_note_title",
                "description": "Type note title 'Meeting Notes'",
                "achieved": False
            })
        
        if "daily standup" in test_lower:
            subgoals.append({
                "type": "type_note_content",
                "description": "Type note content 'Daily Standup'",
                "achieved": False
            })
        
        if "appearance" in test_lower:
            subgoals.append({
                "type": "navigate_to_appearance",
                "description": "Navigate to Appearance settings",
                "achieved": False
            })
        
        if "print to pdf" in test_lower:
            subgoals.append({
                "type": "open_menu",
                "description": "Open note menu",
                "achieved": False
            })
            subgoals.append({
                "type": "find_print_option",
                "description": "Find Print to PDF option",
                "achieved": False
            })
        
        self.detected_subgoals = subgoals
        return subgoals
    
    def check_subgoal_achievement(self, subgoal_type: str, current_state: Dict[str, Any]) -> bool:
        """
        Check if a subgoal has been achieved based on current state
        
        Args:
            subgoal_type: Type of subgoal
            current_state: Current Android/app state
            
        Returns:
            True if subgoal achieved
        """
        screen = current_state.get("current_screen", "unknown")
        ui_text = " ".join(current_state.get("ui_text", [])).lower()
        
        achievement_map = {
            "open_app": screen != "unknown",
            "create_vault": "internvault" in ui_text and screen == "vault_home",
            "enter_vault": screen == "vault_home",
            "create_note": screen == "note_editor",
            "type_note_title": "meeting notes" in ui_text,
            "type_note_content": "daily standup" in ui_text,
            "open_settings": "settings" in ui_text or screen == "settings",
            "open_appearance": "appearance" in ui_text or screen == "appearance",
        }
        
        achieved = achievement_map.get(subgoal_type, False)
        
        if achieved and subgoal_type not in [s["type"] for s in self.achieved_subgoals]:
            self.achieved_subgoals.append({
                "type": subgoal_type,
                "description": next((s["description"] for s in self.detected_subgoals if s["type"] == subgoal_type), ""),
                "achieved": True
            })
        
        return achieved
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current subgoal progress"""
        total = len(self.detected_subgoals)
        achieved = len(self.achieved_subgoals)
        
        return {
            "total_subgoals": total,
            "achieved_subgoals": achieved,
            "completion_rate": achieved / total if total > 0 else 0.0,
            "remaining": [s for s in self.detected_subgoals if s["type"] not in [a["type"] for a in self.achieved_subgoals]]
        }
    
    def _get_subgoal_description(self, subgoal_type: str, test_text: str) -> str:
        """Get human-readable description for subgoal"""
        descriptions = {
            "open_app": "Open Obsidian app",
            "create_vault": "Create new vault",
            "enter_vault": "Enter vault",
            "create_note": "Create new note",
            "type_title": "Type note title",
            "type_content": "Type note content",
            "open_settings": "Open Settings",
            "open_appearance": "Open Appearance tab",
            "verify_element": "Verify element exists",
        }
        return descriptions.get(subgoal_type, subgoal_type.replace("_", " ").title())


# Global instance
subgoal_detector = SubgoalDetector()
