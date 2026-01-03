"""
Executor Agent - Execute Single Action
Executes exactly ONE action and takes screenshot
Uses UIAutomator to find real coordinates when LLM provides generic ones
Never assumes success
"""
from tools.adb_tools import tap, type_text, type_text_slow, keyevent, keycombination, swipe, open_app, find_element_by_text, bounds_to_center, dump_ui, get_ui_text
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
                        # CRITICAL: Must match exact "use this folder" phrase, NOT "create new folder"
                        # The find_element_by_text function will handle this, but prioritize exact match
                        search_texts = ["use this folder"]  # Only exact match, no partial words
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
                    elif "app storage" in desc_lower or ("storage" in desc_lower and "app" in desc_lower):
                        # Priority: find "app storage" or "internal storage" (NOT device storage)
                        search_texts = ["app storage", "internal storage", "app", "internal"]
                        # Explicitly avoid "device storage"
                    elif "storage" in desc_lower:
                        # Generic storage selection - prefer app/internal over device
                        search_texts = ["app storage", "internal storage", "app", "internal", "storage"]
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
            
        elif action_type == "focus":
            target = action.get("target", "")
            print(f"  🎯 Focus: {description} (target: {target})")
            
            try:
                root = dump_ui()
                if root:
                    edittexts = []
                    for node in root.iter("node"):
                        class_name = node.attrib.get("class", "").lower()
                        if "edittext" in class_name:
                            bounds = node.attrib.get("bounds")
                            if bounds and bounds != "[0,0][0,0]":
                                # Parse bounds to get coordinates and size
                                try:
                                    b = bounds.replace("[", "").replace("]", ",").split(",")
                                    x1, y1, x2, y2 = map(int, b[:4])
                                    center_x = (x1 + x2) // 2
                                    center_y = (y1 + y2) // 2
                                    width = x2 - x1
                                    height = y2 - y1
                                    area = width * height
                                    edittexts.append({
                                        "node": node,
                                        "bounds": bounds,
                                        "x": center_x,
                                        "y": center_y,
                                        "y1": y1,
                                        "area": area
                                    })
                                except:
                                    continue
                    
                    if edittexts:
                        selected = None
                        if target == "title":
                            # Title = smallest y (highest on screen)
                            selected = min(edittexts, key=lambda e: e["y1"])
                        elif target == "body":
                            # Body = largest y (lowest) OR largest area
                            # Prefer largest area, fallback to lowest y
                            selected = max(edittexts, key=lambda e: (e["area"], e["y1"]))
                        else:
                            # Default: first EditText found
                            selected = edittexts[0]
                        
                        if selected:
                            print(f"  📍 Focusing {target} field at ({selected['x']}, {selected['y']})")
                            tap(selected['x'], selected['y'])
                            time.sleep(0.3)
            except Exception as e:
                print(f"  ⚠️  Could not find {target} field: {e}")
            
        elif action_type == "type":
            text = action.get("text", "")
            target = action.get("target", "")  # "title" or "body"
            print(f"  ⌨️  Type: {description} - '{text}' (target: {target})")
            
            # ALWAYS tap input field first to ensure keyboard appears
            # This is critical for vault name input and other text fields
            try:
                root = dump_ui()
                if root:
                    edittexts = []
                    for node in root.iter("node"):
                        class_name = node.attrib.get("class", "").lower()
                        if "edittext" in class_name:
                            bounds = node.attrib.get("bounds")
                            if bounds and bounds != "[0,0][0,0]":
                                try:
                                    b = bounds.replace("[", "").replace("]", ",").split(",")
                                    x1, y1, x2, y2 = map(int, b[:4])
                                    center_x = (x1 + x2) // 2
                                    center_y = (y1 + y2) // 2
                                    width = x2 - x1
                                    height = y2 - y1
                                    area = width * height
                                    edittexts.append({
                                        "x": center_x,
                                        "y": center_y,
                                        "y1": y1,
                                        "area": area
                                    })
                                except:
                                    continue
                    
                    if edittexts:
                        selected = None
                        if target == "title":
                            selected = min(edittexts, key=lambda e: e["y1"])
                        elif target == "body":
                            selected = max(edittexts, key=lambda e: (e["area"], e["y1"]))
                        else:
                            # No target specified - use the first/only EditText (for vault name, etc.)
                            selected = edittexts[0]
                        
                        if selected:
                            print(f"  📍 Tapping input field at ({selected['x']}, {selected['y']}) to show keyboard...")
                            tap(selected['x'], selected['y'])
                            time.sleep(0.5)  # Wait for keyboard to appear
            except Exception as e:
                print(f"  ⚠️  Could not find input field: {e}, proceeding anyway...")
            
            # If target is specified, also focus that specific field (for note editor)
            if target:
                # Call focus action internally
                focus_action = {"action": "focus", "target": target, "description": f"Focus {target} field"}
                # Execute focus
                try:
                    root = dump_ui()
                    if root:
                        edittexts = []
                        for node in root.iter("node"):
                            class_name = node.attrib.get("class", "").lower()
                            if "edittext" in class_name:
                                bounds = node.attrib.get("bounds")
                                if bounds and bounds != "[0,0][0,0]":
                                    try:
                                        b = bounds.replace("[", "").replace("]", ",").split(",")
                                        x1, y1, x2, y2 = map(int, b[:4])
                                        center_x = (x1 + x2) // 2
                                        center_y = (y1 + y2) // 2
                                        width = x2 - x1
                                        height = y2 - y1
                                        area = width * height
                                        edittexts.append({
                                            "x": center_x,
                                            "y": center_y,
                                            "y1": y1,
                                            "area": area
                                        })
                                    except:
                                        continue
                        
                        if edittexts:
                            selected = None
                            if target == "title":
                                selected = min(edittexts, key=lambda e: e["y1"])
                            elif target == "body":
                                selected = max(edittexts, key=lambda e: (e["area"], e["y1"]))
                            else:
                                selected = edittexts[0]
                            
                            if selected:
                                print(f"  📍 Focusing {target} field at ({selected['x']}, {selected['y']})")
                                tap(selected['x'], selected['y'])
                                time.sleep(0.3)
                except:
                    pass
            
            # Clear existing text using Ctrl+A combo (better than keyevent)
            try:
                keycombination(113, 29)  # Ctrl + A
                time.sleep(0.2)
                keyevent(67)  # DEL
                time.sleep(0.3)
            except:
                # Fallback to old method
                try:
                    keyevent(113)  # KEYCODE_CTRL_A
                    time.sleep(0.2)
                    keyevent(67)   # KEYCODE_DEL
                    time.sleep(0.3)
                except:
                    pass
            
            # Type the text
            type_text(text)
            time.sleep(1.5)  # Wait for text to appear
            
            # Verify text was entered using UI dump (more reliable)
            verified = False
            try:
                root = dump_ui()
                if root:
                    # Get all text from UI dump
                    all_text = []
                    for node in root.iter("node"):
                        text_attr = node.attrib.get("text", "").strip()
                        content_desc = node.attrib.get("content-desc", "").strip()
                        if text_attr:
                            all_text.append(text_attr)
                        if content_desc:
                            all_text.append(content_desc)
                    
                    # Normalize text for comparison
                    def normalize(s):
                        return ''.join(c.lower() for c in s if c.isalnum())
                    
                    text_normalized = normalize(text)
                    ui_blob = normalize(" ".join(all_text))
                    
                    if text_normalized in ui_blob:
                        print(f"  ✓ Verified: '{text}' appears in UI")
                        verified = True
                    else:
                        print(f"  ⚠️  Warning: '{text}' not found in UI, retrying with slow typing...")
                        # Retry with slow per-character typing
                        type_text_slow(text)
                        time.sleep(1.5)
                        
                        # Verify again
                        root = dump_ui()
                        if root:
                            all_text = []
                            for node in root.iter("node"):
                                text_attr = node.attrib.get("text", "").strip()
                                content_desc = node.attrib.get("content-desc", "").strip()
                                if text_attr:
                                    all_text.append(text_attr)
                                if content_desc:
                                    all_text.append(content_desc)
                            
                            ui_blob = normalize(" ".join(all_text))
                            if text_normalized in ui_blob:
                                print(f"  ✓ Verified after retry: '{text}' appears in UI")
                                verified = True
                            else:
                                print(f"  ⚠️  Still not verified: '{text}' may not be entered correctly")
                                # Mark as failed - text not entered
                                return {
                                    "status": "failed",
                                    "reason": f"Text '{text}' not appearing in UI after multiple attempts",
                                    "action": action,
                                    "screenshot": take_screenshot(f"after_action_{int(time.time())}.png")
                                }
            except Exception as e:
                print(f"  ⚠️  Verification failed: {e}")
                # If verification fails, still return executed but mark as potentially failed
                return {
                    "status": "executed",
                    "action": action,
                    "screenshot": take_screenshot(f"after_action_{int(time.time())}.png"),
                    "warning": f"Could not verify text entry: {e}"
                }
            
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
