"""
Executor Agent - Execute Single Action
Executes exactly ONE action and takes screenshot
Uses UIAutomator to find real coordinates when LLM provides generic ones
Never assumes success
"""
from tools.adb_tools import tap, type_text, type_text_slow, keyevent, keycombination, swipe, open_app, find_element_by_text, bounds_to_center, dump_ui, get_ui_text
import xml.etree.ElementTree as ET
from tools.screenshot import take_screenshot
from config import OBSIDIAN_PACKAGE, OPENAI_API_KEY, OPENAI_MODEL
from openai import OpenAI
from PIL import Image
import base64
import io
import json
import os
import re
import time


def execute_action(action, logger=None):
    """
    Execute exactly ONE action
    Uses UIAutomator to find real coordinates if LLM gives generic ones
    
    Args:
        action: Dictionary with action type and parameters
        logger: Optional BenchmarkLogger instance for logging
    
    Returns:
        Dictionary with execution status, screenshot path, action_source, and intended_success
    """
    action_type = action.get("action", "").lower()
    description = action.get("description", "")
    action_source = "FALLBACK_COORDS"  # Default, will be updated based on how element was found
    intended_success = False  # Will be updated based on execution result
    
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
                    
                    # IMPORTANT: Check "appearance" BEFORE "settings" because descriptions often contain both
                    # e.g., "Tap 'Appearance' tab in Settings" - we want appearance, not settings
                    if "appearance" in desc_lower:
                        print(f"  🎯 APPEARANCE DETECTED in description: '{description}'")
                        # Generate UI XML dump after entering Settings (for analysis)
                        print(f"  📄 Generating UI XML dump after entering Settings...")
                        try:
                            root = dump_ui()
                            if root:
                                xml_str = ET.tostring(root, encoding='unicode')
                                os.makedirs("xml_dumps", exist_ok=True)
                                dump_file = f"xml_dumps/settings_ui_dump_{int(time.time())}.xml"
                                with open(dump_file, 'w', encoding='utf-8') as f:
                                    f.write(xml_str)
                                print(f"  ✓ UI XML dump saved to: {dump_file}")
                        except Exception as e:
                            print(f"  ⚠️  Could not generate UI dump: {e}")
                        
                        # Prioritize "appearance" - search for it first, exclude "settings"
                        print(f"  🔍 Searching specifically for 'Appearance' tab (excluding 'Settings')...")
                        # First try exact "appearance" match using XML search
                        appearance_bounds = find_element_by_text("appearance")
                        if appearance_bounds:
                            tap_x, tap_y = bounds_to_center(appearance_bounds)
                            if tap_x and tap_y:
                                action_source = "XML"
                                print(f"  ✓ Found 'Appearance' tab via XML at ({tap_x}, {tap_y})")
                                tap(tap_x, tap_y)
                                time.sleep(1.5)
                                screenshot_path = take_screenshot(f"after_action_{int(time.time())}.png")
                                # Check if we're in Appearance screen (intended success)
                                ui_text_check = get_ui_text()
                                intended_success = ui_text_check and any("appearance" in t.lower() for t in ui_text_check)
                                return {
                                    "status": "executed",
                                    "action": action,
                                    "screenshot": screenshot_path,
                                    "action_source": action_source,
                                    "intended_success": intended_success
                                }
                        
                        # If XML search failed, use ratio coordinates (0.29W, 0.385H)
                        print(f"  ⚠️  Appearance not found via XML, using ratio coordinates (0.29W, 0.385H)...")
                        from tools.adb_tools import get_screen_size
                        screen_size = get_screen_size()
                        if screen_size:
                            width, height = screen_size
                            tap_x = int(width * 0.29)  # 29% from left
                            tap_y = int(height * 0.385)  # 38.5% from top
                            print(f"  → Using ratio coordinates for Appearance tab: ({tap_x}, {tap_y})")
                            tap(tap_x, tap_y)
                            time.sleep(1.5)
                            screenshot_path = take_screenshot(f"after_action_{int(time.time())}.png")
                            return {
                                "status": "executed",
                                "action": action,
                                "screenshot": screenshot_path
                            }
                        else:
                            # Fallback to default coordinates
                            print(f"  → Screen size not available, using default coordinates (200, 580)")
                            tap(200, 580)
                            time.sleep(1.5)
                            screenshot_path = take_screenshot(f"after_action_{int(time.time())}.png")
                            return {
                                "status": "executed",
                                "action": action,
                                "screenshot": screenshot_path
                            }
                    elif "create" in desc_lower and "vault" in desc_lower:
                        search_texts = ["create", "vault", "new vault", "create vault"]
                    elif "get started" in desc_lower or "started" in desc_lower:
                        search_texts = ["get started", "started", "begin"]
                    elif "enter" in desc_lower and "vault" in desc_lower:
                        search_texts = ["enter vault", "enter", "open vault", "open"]
                    elif "allow" in desc_lower or "permission" in desc_lower:
                        search_texts = ["allow", "ok", "permit", "accept"]
                    elif "continue" in desc_lower:
                        search_texts = ["continue", "next"]
                    elif "settings" in desc_lower or "setting" in desc_lower or "gear icon" in desc_lower:
                        # For Settings gear icon, try ratio coordinates first (more reliable)
                        if "gear icon" in desc_lower or "ratio coordinates" in desc_lower:
                            from tools.adb_tools import get_screen_size
                            screen_size = get_screen_size()
                            if screen_size:
                                width, height = screen_size
                                tap_x = int(width * 0.774)  # 77.4% from left
                                tap_y = int(height * 0.102)  # 10.2% from top
                                print(f"  → Using ratio coordinates for Settings gear icon: ({tap_x}, {tap_y})")
                                
                                # Try 2-3 nearby taps if the first one misses (gear icon hitbox can be finicky)
                                nearby_offsets = [(0, 0), (-5, -5), (5, 5)]
                                for offset_x, offset_y in nearby_offsets:
                                    try_x = tap_x + offset_x
                                    try_y = tap_y + offset_y
                                    print(f"  → Tapping Settings gear icon at ({try_x}, {try_y})...")
                                    tap(try_x, try_y)
                                    time.sleep(1.0)
                                    
                                    # Check if we're now in Settings screen
                                    ui_text_check = get_ui_text()
                                    if ui_text_check and any("settings" in t.lower() for t in ui_text_check):
                                        print(f"  ✓ Successfully tapped Settings gear icon (attempt with offset {offset_x}, {offset_y})")
                                        time.sleep(1.5)  # Wait for Settings screen to fully load
                                        break
                                
                                # If we successfully tapped, return early
                                screenshot_path = take_screenshot(f"after_action_{int(time.time())}.png")
                                return {
                                    "status": "executed",
                                    "action": action,
                                    "screenshot": screenshot_path
                                }
                        
                        # Fallback to text search
                        search_texts = ["settings", "setting", "gear", "menu", "options"]
                    elif "app storage" in desc_lower or ("storage" in desc_lower and "app" in desc_lower):
                        # Priority: find "app storage" or "internal storage" (NOT device storage)
                        search_texts = ["app storage", "internal storage", "app", "internal"]
                        # Explicitly avoid "device storage"
                    elif "storage" in desc_lower:
                        # Generic storage selection - prefer app/internal over device
                        search_texts = ["app storage", "internal storage", "app", "internal", "storage"]
                    elif "create" in desc_lower and "note" in desc_lower:
                        search_texts = ["create", "note", "new note", "add note", "+", "new"]
                    elif "tap to create" in desc_lower and "note" in desc_lower:
                        # For "Tap to create new note" - find create note button
                        search_texts = ["create", "note", "new note", "add", "+"]
                    elif "top-right" in desc_lower or "menu button" in desc_lower or "three dots" in desc_lower or "hamburger" in desc_lower or ("three" in desc_lower and "button" in desc_lower and "dot" in desc_lower):
                        # For top-right menu (three dots) - search XML for "More options" button
                        # CRITICAL: This must handle everything and return - never fall through to generic search
                        print(f"  🎯 THREE DOTS MENU DETECTED - Searching for 'More options' button using XML...")
                        from tools.adb_tools import get_screen_size
                        
                        # Search XML for android.widget.Button with text "More options"
                        menu_bounds = None
                        try:
                            root = dump_ui()
                            if root:
                                for node in root.iter("node"):
                                    node_class = node.attrib.get("class", "")
                                    node_text = node.attrib.get("text", "").strip()
                                    # Look for android.widget.Button with text "More options" (case-insensitive)
                                    if (node_class == "android.widget.Button" and 
                                        node_text.lower() == "more options"):
                                        bounds = node.attrib.get("bounds", "")
                                        if bounds and bounds != "[0,0][0,0]":
                                            menu_bounds = bounds
                                            print(f"  ✓ Found 'More options' button via XML: text='{node_text}', bounds={bounds}")
                                            break
                        except Exception as e:
                            print(f"  ⚠️  XML search error: {e}")
                        
                        if menu_bounds:
                            # Parse bounds: [945,154][1042,241] -> center = (994, 197)
                            bounds_match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', menu_bounds)
                            if bounds_match:
                                x1, y1, x2, y2 = map(int, bounds_match.groups())
                                tap_x = (x1 + x2) // 2
                                tap_y = (y1 + y2) // 2
                                print(f"  ✓ Tapping 'More options' button center at ({tap_x}, {tap_y})")
                                tap(tap_x, tap_y)
                                time.sleep(2.0)  # Wait for menu to appear from below
                                
                                # After tapping, menu appears from below - scroll up and look for "Print to PDF"
                                print(f"  📜 Menu opened, scrolling up and searching for 'Print to PDF'...")
                                
                                # Take screenshot after menu opens
                                screenshot_path = take_screenshot(f"menu_opened_{int(time.time())}.png")
                                
                                # Search for "Print to PDF" in the menu
                                found_print_to_pdf = False
                                try:
                                    root = dump_ui()
                                    if root:
                                        for node in root.iter("node"):
                                            node_text = node.attrib.get("text", "").strip().lower()
                                            content_desc = node.attrib.get("content-desc", "").strip().lower()
                                            if ("print to pdf" in node_text or "export to pdf" in node_text or
                                                "print to pdf" in content_desc or "export to pdf" in content_desc):
                                                found_print_to_pdf = True
                                                print(f"  ✓ Found 'Print to PDF' in menu!")
                                                break
                                except Exception as e:
                                    print(f"  ⚠️  Error searching menu: {e}")
                                
                                # If not found, try scrolling up
                                if not found_print_to_pdf:
                                    print(f"  ⚠️  'Print to PDF' not found, scrolling up in menu...")
                                    from tools.adb_tools import get_screen_size
                                    screen_size = get_screen_size()
                                    if screen_size:
                                        width, height = screen_size
                                        # Swipe up in the menu area (center-right area)
                                        swipe_x = width // 2
                                        swipe_y1 = int(height * 0.6)  # Start from middle
                                        swipe_y2 = int(height * 0.3)  # Swipe up
                                        swipe(swipe_x, swipe_y1, swipe_x, swipe_y2)
                                        time.sleep(1.0)
                                        
                                        # Search again after scrolling
                                        try:
                                            root = dump_ui()
                                            if root:
                                                for node in root.iter("node"):
                                                    node_text = node.attrib.get("text", "").strip().lower()
                                                    content_desc = node.attrib.get("content-desc", "").strip().lower()
                                                    if ("print to pdf" in node_text or "export to pdf" in node_text or
                                                        "print to pdf" in content_desc or "export to pdf" in content_desc):
                                                        found_print_to_pdf = True
                                                        print(f"  ✓ Found 'Print to PDF' after scrolling!")
                                                        break
                                        except Exception as e:
                                            print(f"  ⚠️  Error searching menu after scroll: {e}")
                                
                                # Take final screenshot
                                screenshot_path = take_screenshot(f"after_action_{int(time.time())}.png")
                                
                                if not found_print_to_pdf:
                                    print(f"  ❌ 'Print to PDF' not found in menu - test will FAIL as expected")
                                
                                return {
                                    "status": "executed",
                                    "action": action,
                                    "screenshot": screenshot_path,
                                    "print_to_pdf_found": found_print_to_pdf
                                }
                        
                        # Fallback to ratio coordinates if XML search failed
                        print(f"  ⚠️  'More options' button not found via XML, using ratio coordinates...")
                        screen_size = get_screen_size()
                        if screen_size:
                            width, height = screen_size
                            tap_x = int(width * 0.9)  # 90% from left (top right)
                            tap_y = int(height * 0.09)  # 9% from top
                            print(f"  → Using ratio coordinates for three dots menu (top right): ({tap_x}, {tap_y})")
                            tap(tap_x, tap_y)
                            time.sleep(2.0)  # Wait for menu to appear
                            
                            # Search for Print to PDF after tapping
                            screenshot_path = take_screenshot(f"after_action_{int(time.time())}.png")
                            return {
                                "status": "executed",
                                "action": action,
                                "screenshot": screenshot_path
                            }
                        else:
                            # Final fallback to default coordinates
                            print(f"  → Screen size not available, using default top-right coordinates (994, 197)")
                            tap(994, 197)
                            time.sleep(2.0)
                            screenshot_path = take_screenshot(f"after_action_{int(time.time())}.png")
                            return {
                                "status": "executed",
                                "action": action,
                                "screenshot": screenshot_path
                            }
                        # All branches above return, so we should never reach here
                        # But if we do, return to prevent falling through to generic search
                        print(f"  ⚠️  Unexpected: three dots menu handler didn't return")
                        screenshot_path = take_screenshot(f"after_action_{int(time.time())}.png")
                        return {
                            "status": "executed",
                            "action": action,
                            "screenshot": screenshot_path
                        }
                    else:
                        # Extract key words
                        words = [w for w in description.split() if len(w) > 2]
                        search_texts = [w.lower() for w in words[:3]]
                    
                    # Try to find element by text (only if not "three dots" menu)
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
                    
                    # Special handling for top-right menu: if not found by text, use provided coordinates
                    if not found and ("top-right" in desc_lower or "menu button" in desc_lower):
                        if x > 500 and y < 300:  # Valid top-right coordinates (x > 500, y < 300)
                            print(f"  📍 Using provided top-right coordinates ({x}, {y}) for menu button")
                            found = True
                    
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
                                time.sleep(0.5)  # Wait longer for field to be focused
                except:
                    pass
            
            # Clear existing text - Mobile-safe method (no Ctrl+A)
            # Strategy: Move cursor to end → Backspace N times → Type new text
            print(f"  🗑️  Clearing existing text (mobile-safe method)...")
            try:
                # 1) Move cursor to end (KEYCODE_MOVE_END = 123)
                keyevent(123)  # KEYCODE_MOVE_END
                time.sleep(0.05)
                
                # 2) Backspace a lot (KEYCODE_DEL = 67)
                # 40 is safe for "UntitledMeeting Notes" or similar
                for _ in range(40):
                    keyevent(67)  # KEYCODE_DEL
                    time.sleep(0.01)  # Small delay between backspaces
                
                time.sleep(0.1)
                print(f"  ✓ Text cleared (moved to end + backspaced)")
            except Exception as e:
                print(f"  ⚠️  Error clearing text: {e}, proceeding anyway...")
            
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
                        # Dismiss keyboard by tapping on screen (outside input field)
                        # Tap in the middle-top area to dismiss keyboard
                        try:
                            # Get screen dimensions (approximate for most phones)
                            # Tap in safe area (middle-top) to dismiss keyboard
                            print(f"  ⌨️  Dismissing keyboard by tapping screen...")
                            tap(540, 200)  # Middle-top area, safe from keyboard
                            time.sleep(0.3)  # Wait for keyboard to dismiss
                        except:
                            pass
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
                                # Dismiss keyboard by tapping on screen
                                try:
                                    print(f"  ⌨️  Dismissing keyboard by tapping screen...")
                                    tap(540, 200)  # Middle-top area
                                    time.sleep(0.3)
                                except:
                                    pass
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
        
        elif action_type == "open_sidebar":
            # Special action: Open sidebar using ratio coordinates, then find Settings gear icon
            x = action.get("x", 88)
            y = action.get("y", 134)
            print(f"  📂 Opening sidebar at ({x}, {y})...")
            tap(x, y)
            time.sleep(2.0)  # Wait longer for sidebar to fully slide in
            
            # Generate UI XML dump after opening sidebar (for analysis)
            print(f"  📄 Generating UI XML dump after opening sidebar...")
            try:
                root = dump_ui()
                if root:
                    xml_str = ET.tostring(root, encoding='unicode')
                    # Save to file for analysis
                    os.makedirs("xml_dumps", exist_ok=True)
                    dump_file = f"xml_dumps/sidebar_ui_dump_{int(time.time())}.xml"
                    with open(dump_file, 'w', encoding='utf-8') as f:
                        f.write(xml_str)
                    print(f"  ✓ UI XML dump saved to: {dump_file}")
            except Exception as e:
                print(f"  ⚠️  Could not generate UI dump: {e}")
            
            # Take screenshot after sidebar opens (wait a bit more to ensure sidebar is fully visible)
            time.sleep(0.5)
            screenshot_path = take_screenshot(f"sidebar_opened_{int(time.time())}.png")
            
            # Try XML search first (faster and more reliable, no API cost)
            print(f"  🔍 Searching for Settings in sidebar via XML...")
            settings_tapped = False
            settings_bounds = find_element_by_text("settings")
            if settings_bounds:
                tap_x, tap_y = bounds_to_center(settings_bounds)
                if tap_x and tap_y:
                    print(f"  ✓ Found Settings via XML at ({tap_x}, {tap_y}), tapping...")
                    tap(tap_x, tap_y)
                    time.sleep(2.0)
                    settings_tapped = True
                    print(f"  ✓ Successfully tapped Settings via XML")
                    
                    # Verify we're in Settings screen using LLM vision
                    print(f"  🔍 Verifying we're in Settings screen using LLM vision...")
                    try:
                        verify_screenshot = take_screenshot(f"settings_verification_{int(time.time())}.png")
                        img = Image.open(verify_screenshot)
                        img_buffer = io.BytesIO()
                        img.save(img_buffer, format='PNG')
                        img_buffer.seek(0)
                        img_data = base64.b64encode(img_buffer.read()).decode('utf-8')
                        
                        verify_prompt = """Look at this screenshot. We just tapped the Settings icon.

Are we currently in the Settings screen? Look for:
- Settings title or header
- Settings options/tabs (like Appearance, About, etc.)
- Settings-related UI elements

Return ONLY a JSON object:
{
  "in_settings": true/false,
  "reason": "brief explanation"
}

If you see Settings screen elements, return {"in_settings": true}. Otherwise {"in_settings": false}."""
                        
                        client = OpenAI(api_key=OPENAI_API_KEY)
                        response = client.chat.completions.create(
                            model=OPENAI_MODEL,
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": verify_prompt},
                                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                                    ]
                                }
                            ],
                            max_tokens=100,
                            temperature=0.1
                        )
                        
                        response_text = response.choices[0].message.content.strip()
                        # Extract JSON
                        json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
                        if json_match:
                            verify_result = json.loads(json_match.group())
                            if verify_result.get("in_settings"):
                                print(f"  ✓ LLM confirmed: We're in Settings screen ({verify_result.get('reason', '')})")
                            else:
                                print(f"  ⚠️  LLM says we're NOT in Settings screen ({verify_result.get('reason', '')})")
                        else:
                            print(f"  ⚠️  Could not parse LLM verification response")
                    except Exception as e:
                        error_msg = str(e)
                        if "quota" in error_msg.lower() or "429" in error_msg:
                            print(f"  ⚠️  OpenAI quota exceeded, skipping verification")
                        else:
                            print(f"  ⚠️  Error verifying Settings screen: {e}")
            
            # Fallback to LLM vision only if XML search fails (to save API quota)
            if not settings_tapped:
                print(f"  ⚠️  Settings not found via XML, trying LLM vision (may use API quota)...")
                try:
                    # Read and encode screenshot
                    img = Image.open(screenshot_path)
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    img_data = base64.b64encode(img_buffer.read()).decode('utf-8')
                    
                    # Prompt to find Settings gear icon
                    settings_find_prompt = """Look at this screenshot. A sidebar has just opened from the left side of the screen.

Find the Settings gear icon in this sidebar. It should be a gear/cog icon, usually with text "Settings" next to it or below it.

Analyze the screenshot and identify:
1. Is there a Settings gear icon visible in the sidebar?
2. What are the exact coordinates (x, y) of the center of this Settings gear icon?

Return ONLY a JSON object with:
{
  "found": true/false,
  "description": "description of the Settings gear icon",
  "x": x_coordinate_of_gear_icon_center,
  "y": y_coordinate_of_gear_icon_center
}

If you cannot find it, return {"found": false}.

IMPORTANT: Return ONLY valid JSON, no markdown, no code blocks, no explanations."""
                    
                    client = OpenAI(api_key=OPENAI_API_KEY)
                    response = client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": settings_find_prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                                ]
                            }
                        ],
                        max_tokens=200,
                        temperature=0.1
                    )
                    
                    response_text = response.choices[0].message.content.strip()
                    print(f"  📝 LLM response: {response_text[:200]}...")
                    
                    # Extract JSON from response - try multiple patterns
                    settings_info = None
                    
                    # Try to find JSON in response
                    json_patterns = [
                        r'\{[^{}]*"found"[^{}]*\}',  # Simple JSON
                        r'\{[^}]+\}',  # Any JSON object
                        r'\{.*?"found".*?\}',  # JSON with "found" key
                    ]
                    
                    for pattern in json_patterns:
                        json_match = re.search(pattern, response_text, re.DOTALL)
                        if json_match:
                            try:
                                settings_info = json.loads(json_match.group())
                                break
                            except json.JSONDecodeError:
                                continue
                    
                    # If no JSON found, try parsing the whole response
                    if not settings_info:
                        try:
                            # Remove markdown code blocks if present
                            clean_text = response_text
                            if clean_text.startswith("```json"):
                                clean_text = clean_text[7:]
                            if clean_text.startswith("```"):
                                clean_text = clean_text[3:]
                            if clean_text.endswith("```"):
                                clean_text = clean_text[:-3]
                            clean_text = clean_text.strip()
                            settings_info = json.loads(clean_text)
                        except json.JSONDecodeError:
                            print(f"  ⚠️  Could not parse LLM response as JSON")
                    
                    if settings_info and settings_info.get("found") and settings_info.get("x") is not None and settings_info.get("y") is not None:
                        tap_x = int(settings_info.get("x"))
                        tap_y = int(settings_info.get("y"))
                        desc = settings_info.get("description", "Settings gear icon")
                        print(f"  ✓ LLM found Settings gear icon: {desc} at ({tap_x}, {tap_y})")
                        tap(tap_x, tap_y)
                        time.sleep(2.0)  # Wait for Settings screen to open
                        settings_tapped = True
                        print(f"  ✓ Successfully tapped Settings gear icon")
                    else:
                        print(f"  ⚠️  LLM could not find Settings gear icon (found={settings_info.get('found') if settings_info else None})")
                        
                except Exception as e:
                    error_msg = str(e)
                    if "quota" in error_msg.lower() or "429" in error_msg:
                        print(f"  ⚠️  OpenAI API quota exceeded, skipping LLM vision (fallback to ratio coordinates)...")
                    else:
                        print(f"  ⚠️  Error using LLM vision: {e}")
            
            # Fallback to ratio coordinates if XML and LLM vision both failed
            if not settings_tapped:
                print(f"  🔍 Trying ratio coordinates for Settings gear icon...")
                # Use ratio coordinates as final fallback (0.774W, 0.102H)
                from tools.adb_tools import get_screen_size
                screen_size = get_screen_size()
                if screen_size:
                    width, height = screen_size
                    tap_x = int(width * 0.774)  # 77.4% from left
                    tap_y = int(height * 0.102)  # 10.2% from top
                    print(f"  → Using ratio coordinates (0.774W, 0.102H) = ({tap_x}, {tap_y})")
                    
                    # Try 2-3 nearby taps if the first one misses (gear icon hitbox can be finicky)
                    nearby_offsets = [(0, 0), (-5, -5), (5, 5), (-5, 5), (5, -5)]
                    for offset_x, offset_y in nearby_offsets[:3]:  # Try up to 3 taps
                        try_x = tap_x + offset_x
                        try_y = tap_y + offset_y
                        print(f"  → Tapping Settings at ({try_x}, {try_y})...")
                        tap(try_x, try_y)
                        time.sleep(0.5)
                        
                        # Check if we're now in Settings screen
                        ui_text = get_ui_text()
                        if ui_text and any("settings" in t.lower() for t in ui_text):
                            print(f"  ✓ Successfully tapped Settings (attempt with offset {offset_x}, {offset_y})")
                            settings_tapped = True
                            time.sleep(1.5)  # Wait for Settings screen to fully load
                            break
                    
                    if not settings_tapped:
                        print(f"  ⚠️  Settings not found after trying ratio coordinates with retries")
            
            # If still not found, return a status indicating we need to retry
            if not settings_tapped:
                print(f"  ⚠️  WARNING: Could not find and tap Settings gear icon after opening sidebar")
                # Return status so planner knows to retry
                return {
                    "status": "partial",
                    "action": action,
                    "screenshot": take_screenshot(f"after_action_{int(time.time())}.png"),
                    "message": "Sidebar opened but Settings gear icon not found/tapped"
                }
            
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
