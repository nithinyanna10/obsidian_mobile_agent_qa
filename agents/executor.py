"""
Executor Agent - Execute Single Action
Executes exactly ONE action and takes screenshot
Uses UIAutomator to find real coordinates when LLM provides generic ones
Never assumes success
"""
from tools.adb_tools import tap, type_text, keyevent, swipe, open_app, find_element_by_text, bounds_to_center, dump_ui, get_ui_text
from tools.screenshot import take_screenshot
from config import OBSIDIAN_PACKAGE
import time


def execute_action(action):
    """
    Execute exactly ONE action
    Uses UIAutomator to find real coordinates if LLM gives generic ones
    
    Args:
        action: Dictionary with action type and parameters
    
    Returns:
        Dictionary with execution status and screenshot path
    """
    action_type = action.get("action", "").lower()
    description = action.get("description", "")
    
    try:
        if action_type == "tap":
            # Check if this is an app icon tap (should use open_app instead)
            if "app icon" in description.lower() or ("obsidian" in description.lower() and "icon" in description.lower()):
                print(f"  📱 Converting app icon tap to open_app")
                open_app(OBSIDIAN_PACKAGE)
                time.sleep(3)
            else:
                x = action.get("x", 0)
                y = action.get("y", 0)
                
                # If coordinates are generic (100, 200) or invalid, try UIAutomator
                if (x == 100 and y == 200) or x == 0 or y == 0:
                    print(f"  🔍 Generic coordinates detected, using UIAutomator to find: {description}")
                    
                    # Extract search text from description
                    desc_lower = description.lower()
                    search_texts = []
                    
                    if "create" in desc_lower and "vault" in desc_lower:
                        search_texts = ["create", "vault", "new vault", "create vault"]
                    elif "get started" in desc_lower or "started" in desc_lower:
                        search_texts = ["get started", "started", "begin"]
                    elif "enter" in desc_lower and "vault" in desc_lower:
                        search_texts = ["enter vault", "enter", "open vault", "open"]
                    elif "allow" in desc_lower or "permission" in desc_lower:
                        search_texts = ["allow", "ok", "permit", "accept"]
                    elif "continue" in desc_lower:
                        search_texts = ["continue", "next"]
                    elif "settings" in desc_lower or "setting" in desc_lower:
                        search_texts = ["settings", "setting", "gear", "menu", "options"]
                    elif "appearance" in desc_lower:
                        search_texts = ["appearance", "theme", "color", "display"]
                    elif "create" in desc_lower and "note" in desc_lower:
                        search_texts = ["create", "note", "new note", "add note", "+", "new"]
                    elif "tap to create" in desc_lower and "note" in desc_lower:
                        # For "Tap to create new note" - find create note button
                        search_texts = ["create", "note", "new note", "add", "+"]
                    elif "use this folder" in desc_lower or "this folder" in desc_lower:
                        search_texts = ["use this folder", "use", "this", "folder", "select"]
                    elif "internvault" in desc_lower:
                        # Priority: find InternVault vault name first (exact match)
                        # Try to find the actual vault name text, not "enter vault" button
                        search_texts = ["internvault", "intern vault"]
                        # Don't include generic "vault" as it might match wrong elements
                    elif "enter" in desc_lower and "vault" in desc_lower:
                        # Try to find vault name "InternVault" first, then "USE THIS FOLDER"
                        search_texts = ["internvault", "intern vault", "use this folder", "vault", "enter", "open"]
                    elif "enter existing vault" in desc_lower or ("enter" in desc_lower and "vault" in desc_lower and "existing" in desc_lower):
                        # Try to find vault name or "USE THIS FOLDER" button
                        search_texts = ["internvault", "use this folder", "vault", "enter", "open"]
                    elif "stop creating" in desc_lower or "existing vault" in desc_lower:
                        # Find vault name or enter button
                        search_texts = ["internvault", "use this folder", "vault", "enter"]
                    elif "close" in desc_lower and "button" in desc_lower:
                        # For settings - try back key instead of close button
                        search_texts = ["back", "close", "cancel", "done"]
                    else:
                        # Extract key words
                        words = [w for w in description.split() if len(w) > 2]
                        search_texts = [w.lower() for w in words[:3]]
                    
                    # Try to find element by text
                    found = False
                    for search_text in search_texts:
                        bounds = find_element_by_text(search_text)
                        if bounds:
                            tap_x, tap_y = bounds_to_center(bounds)
                            if tap_x and tap_y:
                                x, y = tap_x, tap_y
                                print(f"  ✓ Found element '{search_text}' at ({x}, {y})")
                                found = True
                                break
                    
                    if not found:
                        # If coordinates are invalid (0,0) or generic, fail instead of tapping nothing
                        if x == 0 and y == 0:
                            return {
                                "status": "failed",
                                "reason": f"Element not found for '{description}' and no valid coordinates provided",
                                "action": action
                            }
                        print(f"  ⚠️  Could not find element by text, using provided coordinates ({x}, {y})")
                
                # Validate coordinates before tapping
                if x <= 0 or y <= 0:
                    return {
                        "status": "failed",
                        "reason": f"Invalid coordinates ({x}, {y}) for '{description}'",
                        "action": action
                    }
                
                print(f"  👆 Tap: {description} at ({x}, {y})")
                tap(x, y)
                time.sleep(1.5)  # Wait for UI to update
            
        elif action_type == "type":
            text = action.get("text", "")
            print(f"  ⌨️  Type: {description} - '{text}'")
            
            # First, focus the input field by tapping it (if we can find it)
            # Try to find EditText field using UIAutomator
            try:
                root = dump_ui()
                if root:
                    for node in root.iter("node"):
                        class_name = node.attrib.get("class", "").lower()
                        if "edittext" in class_name:
                            bounds = node.attrib.get("bounds")
                            if bounds and bounds != "[0,0][0,0]":
                                tap_x, tap_y = bounds_to_center(bounds)
                                if tap_x and tap_y:
                                    print(f"  📍 Focusing input field at ({tap_x}, {tap_y})")
                                    tap(tap_x, tap_y)
                                    time.sleep(0.5)
                                    # Clear existing text: select all and delete
                                    keyevent(113)  # KEYCODE_CTRL_A (select all)
                                    time.sleep(0.2)
                                    keyevent(67)   # KEYCODE_DEL (delete)
                                    time.sleep(0.3)
                                    break
            except:
                pass  # If we can't find input field, just try typing anyway
            
            # Type the text
            type_text(text)
            time.sleep(1.5)  # Wait for text to appear
            
            # Verify text was entered (optional check)
            try:
                ui_text = get_ui_text()
                if text.lower() in " ".join(ui_text).lower():
                    print(f"  ✓ Verified: '{text}' appears in UI")
                else:
                    print(f"  ⚠️  Warning: '{text}' may not have been entered correctly")
            except:
                pass
            
        elif action_type == "key":
            code = action.get("code", 0)
            print(f"  ⌨️  Key: {description} (code: {code})")
            keyevent(code)
            time.sleep(2)  # Wait for key event to process
            
        elif action_type == "swipe":
            x1 = action.get("x1", 0)
            y1 = action.get("y1", 0)
            x2 = action.get("x2", 0)
            y2 = action.get("y2", 0)
            print(f"  👉 Swipe: {description} from ({x1}, {y1}) to ({x2}, {y2})")
            swipe(x1, y1, x2, y2)
            time.sleep(1.5)  # Wait for swipe to complete
            
        elif action_type == "wait":
            seconds = action.get("seconds", 1)
            print(f"  ⏳ Wait: {description} ({seconds}s)")
            time.sleep(seconds)
            
        elif action_type == "open_app":
            app = action.get("app", OBSIDIAN_PACKAGE)
            print(f"  📱 Open app: {app}")
            open_app(app)
            time.sleep(3)  # Wait for app to load
            
        elif action_type == "assert":
            print(f"  ✓ Assert: {description}")
            # No execution needed, just mark as assertion
            
        elif action_type == "fail":
            reason = action.get("reason", "Unknown reason")
            print(f"  ❌ FAIL: {reason}")
            return {
                "status": "failed",
                "reason": reason,
                "action": action
            }
            
        else:
            return {
                "status": "failed",
                "reason": f"Unknown action type: {action_type}",
                "action": action
            }
        
        # Take screenshot after action (visual confirmation)
        screenshot_path = take_screenshot(f"after_action_{int(time.time())}.png")
        
        return {
            "status": "executed",
            "action": action,
            "screenshot": screenshot_path
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "action": action
        }
