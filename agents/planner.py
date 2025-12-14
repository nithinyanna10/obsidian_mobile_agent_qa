"""
Planner Agent - Step-by-Step Visual Planning with Android State
After each action, analyzes screenshot + Android state and decides the next single action
"""
from openai import OpenAI
from PIL import Image
import json
import os
import sys
import base64
import io

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, OBSIDIAN_PACKAGE, OPENAI_MODEL
from tools.adb_tools import detect_current_screen, get_ui_text, dump_ui


# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def get_android_state():
    """
    Get current Android state information
    
    Returns:
        Dictionary with Android state info
    """
    state = {
        "current_screen": "unknown",
        "ui_text": [],
        "has_edittext": False
    }
    
    try:
        # Get current screen from activity
        state["current_screen"] = detect_current_screen()
        
        # Get UI text from uiautomator dump
        try:
            ui_text = get_ui_text()
            state["ui_text"] = ui_text[:20]  # Limit to first 20 items
        except:
            pass
        
        # Check for EditText (input field)
        try:
            root = dump_ui()
            if root:
                for node in root.iter("node"):
                    class_name = node.attrib.get("class", "").lower()
                    if "edittext" in class_name:
                        state["has_edittext"] = True
                        break
        except:
            pass
            
    except Exception as e:
        state["error"] = str(e)
    
    return state


def plan_next_action(test_text, screenshot_path, action_history):
    """
    Analyze screenshot + Android state and decide the next single action
    
    Args:
        test_text: Natural language test goal
        screenshot_path: Path to current screenshot
        action_history: List of previous actions taken
    
    Returns:
        Dictionary with single action OR {"action": "FAIL", "reason": "..."} if element not found
    """
    try:
        # Get Android state information
        android_state = get_android_state()
        
        # Check if we're already in vault_home (vault entered successfully)
        current_screen = android_state.get('current_screen', 'unknown')
        ui_text = android_state.get('ui_text', [])
        
        # Check if we're in vault_home by activity OR by UI text (vault name visible at top)
        if current_screen == 'vault_home':
            # We're already in vault, proceed with test goal (create note, etc.)
            # Don't try to enter vault again
            pass
        elif current_screen == 'unknown' and any('internvault' in text.lower() for text in ui_text):
            # Screen detection might be wrong, but InternVault is visible - might be in vault_home
            # Check if test goal is to create note - if so, try to proceed with note creation
            if "note" in test_text.lower() or ("create" in test_text.lower() and "note" in test_text.lower()):
                recent_enter_attempts = sum(1 for a in action_history[-3:] if "internvault" in a.get("description", "").lower() or "enter vault" in a.get("description", "").lower())
                if recent_enter_attempts >= 2:
                    # We've tried entering multiple times, assume we're in vault and proceed
                    print(f"  ⚠️  Multiple enter attempts, assuming we're in vault - proceeding with note creation")
                    return {
                        "action": "tap",
                        "x": 0,
                        "y": 0,
                        "description": "Tap to create new note (assuming we're in vault home)"
                    }
        
        # Check if InternVault exists in UI (vault already created from Test 1)
        internvault_found = any('internvault' in text.lower() and 'enter' not in text.lower() for text in ui_text)
        
        if internvault_found and current_screen in ['welcome_setup', 'vault_selection']:
            # Check if test goal is to create note (Test 2) - then vault already exists
            if "note" in test_text.lower() or ("create" in test_text.lower() and "note" in test_text.lower()):
                # Check if we've already tried to enter vault multiple times
                recent_enter_attempts = sum(1 for a in action_history[-5:] if "internvault" in a.get("description", "").lower() or "enter vault" in a.get("description", "").lower())
                if recent_enter_attempts < 2:  # Only try if we haven't tried too many times
                    print(f"  ✓ Found InternVault in UI, tapping to enter existing vault for Test 2")
                    return {
                        "action": "tap",
                        "x": 0,
                        "y": 0,
                        "description": "Tap InternVault vault name to enter existing vault"
                    }
        
        # Check if we're stuck creating vaults when we should be entering existing one
        if len(action_history) >= 2:
            recent_actions = [a.get("description", "").lower() for a in action_history[-5:]]
            vault_creation_count = sum(1 for a in recent_actions if "create vault" in a or ("type" in a and "vault" in a and "name" in a))
            enter_vault_count = sum(1 for a in recent_actions if "use this folder" in a or "enter vault" in a or "enter existing" in a or "internvault" in a)
            
            # If we've created/typed vault multiple times but keep going back to welcome_setup
            # AND we haven't successfully entered a vault yet
            if vault_creation_count >= 2 and enter_vault_count == 0 and android_state.get('current_screen') in ['welcome_setup', 'vault_selection']:
                # Vault already exists, just enter it - find "USE THIS FOLDER" or vault name
                print(f"  ⚠️  Detected vault creation loop ({vault_creation_count} times), entering existing vault instead")
                return {
                    "action": "tap",
                    "x": 0,
                    "y": 0,
                    "description": "Tap InternVault to enter existing vault (vault already created, stop creating new ones)"
                }
        
        # Check if we're stuck (same action repeated)
        if len(action_history) >= 3:
            last_3_actions = [a.get("description", "") for a in action_history[-3:]]
            if len(set(last_3_actions)) == 1:
                action_desc = last_3_actions[0]
                # Special handling for permission dialogs - if we tapped ALLOW multiple times, try BACK
                if "allow" in action_desc.lower() or "permission" in action_desc.lower():
                    return {
                        "action": "key",
                        "code": 4,
                        "description": "Press BACK to dismiss permission dialog"
                    }
                # Special handling for vault creation loop
                if "create vault" in action_desc.lower() or ("type" in action_desc.lower() and "vault" in action_desc.lower()):
                    # Try to find and tap "USE THIS FOLDER" or vault name to enter existing vault
                    return {
                        "action": "tap",
                        "x": 0,
                        "y": 0,
                        "description": "Tap InternVault to enter existing vault (stop creating new vaults)"
                    }
                # Special handling for "USE THIS FOLDER" loop - try tapping vault name instead
                if "use this folder" in action_desc.lower():
                    return {
                        "action": "tap",
                        "x": 0,
                        "y": 0,
                        "description": "Tap InternVault vault name to enter (USE THIS FOLDER not working)"
                    }
                # Special handling for "enter vault" or "InternVault" loop - assume we're in vault and proceed
                if "enter vault" in action_desc.lower() or ("internvault" in action_desc.lower() and "enter" in action_desc.lower()):
                    # If test goal is to create note, assume we're in vault and proceed
                    if "note" in test_text.lower() or ("create" in test_text.lower() and "note" in test_text.lower()):
                        print(f"  ⚠️  Enter vault loop detected, assuming we're in vault - proceeding with note creation")
                        return {
                            "action": "tap",
                            "x": 0,
                            "y": 0,
                            "description": "Tap to create new note (assuming we're in vault home)"
                        }
                    return {
                        "action": "wait",
                        "seconds": 2,
                        "description": "Wait for vault to load, then check if we're in vault home"
                    }
                return {
                    "action": "FAIL",
                    "reason": f"Stuck in loop: Repeated action '{action_desc}' 3 times. Screen: {android_state.get('current_screen')}"
                }
        
        # Read and encode screenshot
        img = Image.open(screenshot_path)
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        img_data = base64.b64encode(img_buffer.read()).decode('utf-8')
        
        # Build action history string
        history_str = ""
        if action_history:
            history_str = "\nPrevious actions:\n"
            for i, action in enumerate(action_history[-5:]):  # Last 5 actions
                history_str += f"  {i+1}. {action.get('action', 'unknown')}: {action.get('description', '')}\n"
        
        # Build Android state string
        state_str = f"""
Android State Information:
- Current Screen: {android_state.get('current_screen', 'unknown')}
- Has Input Field (EditText): {android_state.get('has_edittext', False)}
- Visible UI Text: {', '.join(android_state.get('ui_text', [])[:10])}
"""
        
        prompt = f"""You are a QA Planner agent for mobile app testing. You analyze screenshots AND Android state to decide the next action.

{state_str}

Test Goal: "{test_text}"
{history_str}

IMPORTANT: Use BOTH the screenshot AND the Android state information above to understand what's happening.

Look at the screenshot and Android state, then identify:
1. What screen is currently shown? (Check Android state: {android_state.get('current_screen')})
2. Is there an input field? (Check Android state: {android_state.get('has_edittext')})
3. What UI elements are visible? (Check Android state UI text)
4. What is the next single action needed to progress toward the test goal?

Available actions (return EXACTLY ONE):
- {{"action": "tap", "x": 100, "y": 200, "description": "Tap 'Create vault' button"}}
- {{"action": "type", "text": "InternVault", "description": "Type vault name"}}
- {{"action": "key", "code": 66, "description": "Press ENTER"}}  (66=ENTER, 4=BACK)
- {{"action": "swipe", "x1": 100, "y1": 500, "x2": 100, "y2": 200, "description": "Swipe up"}}
- {{"action": "wait", "seconds": 2, "description": "Wait for UI to load"}}
- {{"action": "assert", "description": "Test goal achieved"}}  (if test goal is visually confirmed)
- {{"action": "FAIL", "reason": "Element not found: 'Print to PDF' button"}}  (if required element is NOT visible)

CRITICAL RULES:
1. Return EXACTLY ONE action - the immediate next step
2. If Android state shows has_edittext=true, you should type text, not tap
3. If Android state shows current_screen='vault_name_input', type the vault name
4. If you see a permission dialog (e.g., "Allow access"), tap "Allow" or "OK" ONCE - if it doesn't work, try BACK key
5. If you see "Continue without sync" or similar, tap it
6. If the test goal is visually achieved, return assert action
7. If a required element for the test is NOT visible, return FAIL action with reason
8. For tap actions, provide coordinates (x, y) based on button position in screenshot - BUT if you're not sure, use (0, 0) and the executor will use UIAutomator to find it
9. If Android state shows you're stuck on the same screen after multiple actions, try a different approach (BACK key, swipe, etc.) or return FAIL
10. NEVER repeat the same action if Android state hasn't changed - try BACK key or different approach
11. If you need to open the app, use {{"action": "open_app", "app": "md.obsidian"}} instead of tapping app icon
12. If tapping ALLOW/permission button multiple times doesn't work, try {{"action": "key", "code": 4, "description": "Press BACK"}} to dismiss dialog
13. **CRITICAL FOR TEST 2**: If you're on welcome_setup/vault_selection screen and the test goal is to create a note, the vault ALREADY EXISTS from Test 1. DO NOT create a new vault. Look for the vault name "InternVault" in the UI and tap it to ENTER the existing vault. If you see "USE THIS FOLDER" button, you can tap that too. Only create NEW vaults if you see "Create vault" button and NO vault exists yet.
14. If you've typed vault name or created vault multiple times, STOP creating vaults and just enter the existing vault by tapping "InternVault" or "USE THIS FOLDER"
15. **FOR TEST 3 (Settings)**: After tapping settings icon, look for "Appearance" tab or menu item. DO NOT try to close settings - explore it to find Appearance. If you can't find Appearance, look for tabs, menu items, or swipe to see more options.
16. If "Close" button is not found in settings, use BACK key (code 4) or look for Appearance tab directly

Output ONLY valid JSON, no markdown, no code blocks:
"""
        
        # Call OpenAI Vision API
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_data}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        if not response or not response.choices or not response.choices[0].message.content:
            return {"action": "FAIL", "reason": "Empty response from LLM"}
        
        result_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        try:
            action = json.loads(result_text)
            # Validate action structure
            if "action" not in action:
                return {"action": "FAIL", "reason": "Invalid action format from LLM"}
            # Attach Android state for logging
            action["_android_state"] = android_state
            return action
        except json.JSONDecodeError:
            return {"action": "FAIL", "reason": f"Could not parse LLM response: {result_text}"}
            
    except Exception as e:
        return {"action": "FAIL", "reason": f"Planning error: {str(e)}"}
