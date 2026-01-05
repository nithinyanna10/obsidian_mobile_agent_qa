"""
ADB Tools for Android Device Interaction
Provides functions to interact with Android devices via ADB commands
"""
import subprocess
import time


def adb(cmd):
    """
    Execute an ADB command
    
    Args:
        cmd: ADB command string (e.g., "shell input tap 100 200")
    
    Returns:
        subprocess.CompletedProcess result
    """
    full_cmd = ["adb"] + cmd.split()
    result = subprocess.run(full_cmd, check=True, capture_output=True, text=True)
    return result


def tap(x, y):
    """
    Tap at coordinates (x, y) on the screen
    
    Args:
        x: X coordinate
        y: Y coordinate
    """
    adb(f"shell input tap {x} {y}")
    time.sleep(0.5)  # Small delay for UI to respond


def type_text(text):
    """
    Type text into the current input field
    
    Args:
        text: Text to type (spaces will be converted to %s for ADB)
    """
    # Replace spaces with %s for ADB input text command
    escaped_text = text.replace(" ", "%s")
    adb(f"shell input text {escaped_text}")
    time.sleep(0.5)


def type_text_slow(text):
    """
    Type text character by character (slower, more reliable)
    
    Args:
        text: Text to type character by character
    """
    import subprocess
    for char in text:
        if char == ' ':
            subprocess.run(["adb", "shell", "input", "text", "%s"], check=False)
        else:
            subprocess.run(["adb", "shell", "input", "text", char], check=False)
        time.sleep(0.08)  # Delay between characters


def keycombination(code1, code2):
    """
    Send a key combination (e.g., Ctrl+A)
    
    Args:
        code1: First key code (e.g., 113 for CTRL)
        code2: Second key code (e.g., 29 for A)
    """
    adb(f"shell input keyevent {code1} {code2}")
    time.sleep(0.3)


def keyevent(code):
    """
    Send a key event to the device
    
    Args:
        code: Key event code (e.g., 66 for ENTER, 4 for BACK, 67 for DELETE, 113 for CTRL+A, 123 for MOVE_END)
    """
    adb(f"shell input keyevent {code}")
    time.sleep(0.5)


def clear_text():
    """
    Clear text in current input field
    Selects all and deletes
    """
    keyevent(113)  # KEYCODE_CTRL_A (select all)
    time.sleep(0.2)
    keyevent(67)   # KEYCODE_DEL (delete)
    time.sleep(0.3)


def swipe(x1, y1, x2, y2, duration=300):
    """
    Swipe from (x1, y1) to (x2, y2)
    
    Args:
        x1: Start X coordinate
        y1: Start Y coordinate
        x2: End X coordinate
        y2: End Y coordinate
        duration: Swipe duration in milliseconds
    """
    adb(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
    time.sleep(1.5)  # Wait for swipe to complete


def long_press(x, y, duration=800):
    """
    Long press at coordinates (x, y)
    
    Args:
        x: X coordinate
        y: Y coordinate
        duration: Press duration in milliseconds (default 800ms)
    """
    # Long press is implemented as swipe from same point to same point with duration
    adb(f"shell input swipe {x} {y} {x} {y} {duration}")
    time.sleep(0.5)


def open_app(package_name):
    """
    Open an app by package name
    
    Args:
        package_name: Android package name (e.g., "md.obsidian")
    """
    adb(f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
    time.sleep(3)  # Wait for app to launch


def get_screen_size():
    """
    Get device screen size (width, height)
    
    Returns:
        Tuple of (width, height) or None if failed
    """
    try:
        result = adb("shell wm size")
        # Output format: "Physical size: 1080x2400" or "Override size: 1080x2400"
        output = result.stdout.strip()
        if "x" in output:
            size_str = output.split("x")[-1].split()[0] if "x" in output else output.split()[-1]
            if "x" in output:
                parts = output.split("x")
                width = int(parts[0].split()[-1])
                height = int(parts[1].split()[0])
                return (width, height)
    except:
        pass
    return None


def dump_ui():
    """
    Dump UI hierarchy using UIAutomator
    
    Returns:
        XML ElementTree root or None if failed
    """
    try:
        result = adb("shell uiautomator dump /dev/tty")
        # Try to get XML from stdout
        xml_output = result.stdout
        
        # If stdout is empty, try reading from /sdcard/window_dump.xml
        if not xml_output or len(xml_output) < 100:
            try:
                result = adb("shell uiautomator dump /sdcard/window_dump.xml")
                result = adb("shell cat /sdcard/window_dump.xml")
                xml_output = result.stdout
            except:
                pass
        
        if xml_output and len(xml_output) > 100:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(xml_output)
            return root
    except Exception as e:
        # XML dump failed - device might not be connected or app not running
        # This is OK, we'll handle it gracefully
        pass
    return None


def get_ui_text():
    """
    Get all visible text from UI using UIAutomator dump
    
    Returns:
        List of text strings visible on screen
    """
    root = dump_ui()
    if root is None:
        return []
    
    texts = []
    for node in root.iter("node"):
        text = node.attrib.get('text', '').strip()
        if text:
            texts.append(text)
        # Also check content-desc for accessibility text
        content_desc = node.attrib.get('content-desc', '').strip()
        if content_desc and content_desc != text:
            texts.append(content_desc)
        # Add resource-id if it contains meaningful info (not just package names)
        resource_id = node.attrib.get('resource-id', '').strip()
        if resource_id and ':' in resource_id:
            # Extract meaningful part (after last colon)
            meaningful_id = resource_id.split(':')[-1]
            if meaningful_id and len(meaningful_id) > 2:
                texts.append(meaningful_id)
    
    return texts


def find_element_by_text(text):
    """
    Find UI element by text using UIAutomator dump
    Tries multiple search strategies for better matching
    Handles XML dump failures gracefully
    
    Args:
        text: Text to search for (case-insensitive partial match)
    
    Returns:
        Bounds string like "[96,1344][984,1476]" or None if not found
    """
    root = dump_ui()
    if root is None:
        # XML dump failed (device not connected or app not running)
        # This is OK - we'll fall back to coordinates if provided
        return None
    
    text_lower = text.lower().strip()
    
    # SPECIAL HANDLING: "use this folder" - must match exact phrase, NOT "create new folder"
    if "use this folder" in text_lower:
        # First pass: look for exact "use this folder" phrase
        for node in root.iter("node"):
            node_text = node.attrib.get("text", "").lower().strip()
            content_desc = node.attrib.get("content-desc", "").lower().strip()
            # Must contain "use this folder" but NOT "create" or "new"
            if ("use this folder" in node_text or "use this folder" in content_desc) and \
               "create" not in node_text and "new" not in node_text:
                bounds = node.attrib.get("bounds")
                if bounds and bounds != "[0,0][0,0]":
                    return bounds
        # If exact not found, try just "use this" (but still avoid "create new")
        for node in root.iter("node"):
            node_text = node.attrib.get("text", "").lower().strip()
            content_desc = node.attrib.get("content-desc", "").lower().strip()
            if ("use this" in node_text or "use this" in content_desc) and \
               "create" not in node_text and "new" not in node_text:
                bounds = node.attrib.get("bounds")
                if bounds and bounds != "[0,0][0,0]":
                    return bounds
        # If still not found, return None to avoid matching wrong button
        return None
    
    # Try exact match first, then partial match
    search_terms = [text_lower]
    # Add word-based searches
    words = [w for w in text_lower.split() if len(w) > 2]
    search_terms.extend(words)
    
    # Also try common button text variations
    if "internvault" in text_lower or "intern vault" in text_lower:
        search_terms.extend(["internvault", "intern vault", "vault"])
    if "get started" in text_lower or "started" in text_lower:
        search_terms.extend(["get started", "started", "get", "begin"])
    if "create" in text_lower and "vault" in text_lower:
        search_terms.extend(["create", "new vault", "create vault", "vault"])
    if "enter" in text_lower and "vault" in text_lower:
        search_terms.extend(["enter vault", "enter", "open vault", "open"])
    if "create" in text_lower and "note" in text_lower:
        search_terms.extend(["create", "new note", "create note", "note"])
    if "appearance" in text_lower:
        # For appearance, prioritize exact "appearance" match and exclude "settings"
        # First pass: look for exact "appearance" text (not "settings")
        for node in root.iter("node"):
            node_text = node.attrib.get("text", "").lower().strip()
            content_desc = node.attrib.get("content-desc", "").lower().strip()
            # Must contain "appearance" but NOT "settings"
            if ("appearance" in node_text or "appearance" in content_desc) and \
               "settings" not in node_text and "settings" not in content_desc:
                bounds = node.attrib.get("bounds")
                if bounds and bounds != "[0,0][0,0]":
                    return bounds
        # If exact not found, try theme/color/display as fallback
        search_terms.extend(["theme", "color", "display"])
    if "app storage" in text_lower or ("storage" in text_lower and "app" in text_lower):
        # Priority: find "app storage" or "internal storage" (NOT device storage)
        search_terms.extend(["app storage", "internal storage", "app", "internal"])
        # Explicitly avoid "device storage" - don't add it to search terms
    
    # For InternVault, prioritize exact text match over partial matches
    if "internvault" in text_lower:
        # First pass: look for exact "internvault" text match (vault name, not "enter vault" button)
        for node in root.iter("node"):
            node_text = node.attrib.get("text", "").lower().strip()
            # Match "internvault" but NOT "enter vault" - vault name should be standalone
            if "internvault" in node_text and "enter" not in node_text:
                bounds = node.attrib.get("bounds")
                if bounds and bounds != "[0,0][0,0]":
                    return bounds
        # Second pass: if exact match not found, try any "internvault" match
        for node in root.iter("node"):
            node_text = node.attrib.get("text", "").lower().strip()
            if "internvault" in node_text:
                bounds = node.attrib.get("bounds")
                if bounds and bounds != "[0,0][0,0]":
                    return bounds
    
    # Special handling for "app storage" - must NOT match "device storage"
    if "app storage" in text_lower or ("storage" in text_lower and "app" in text_lower):
        # First pass: look for "app storage" or "internal storage" (NOT device storage)
        for node in root.iter("node"):
            node_text = node.attrib.get("text", "").lower().strip()
            content_desc = node.attrib.get("content-desc", "").lower().strip()
            # Must contain "app" or "internal" but NOT "device"
            if (("app storage" in node_text or "internal storage" in node_text or 
                 "app storage" in content_desc or "internal storage" in content_desc) and
                "device" not in node_text and "device" not in content_desc):
                bounds = node.attrib.get("bounds")
                if bounds and bounds != "[0,0][0,0]":
                    return bounds
        # Second pass: try just "app" or "internal" (but still avoid device)
        for node in root.iter("node"):
            node_text = node.attrib.get("text", "").lower().strip()
            content_desc = node.attrib.get("content-desc", "").lower().strip()
            if (("app" in node_text or "internal" in node_text or 
                 "app" in content_desc or "internal" in content_desc) and
                "device" not in node_text and "device" not in content_desc):
                bounds = node.attrib.get("bounds")
                if bounds and bounds != "[0,0][0,0]":
                    return bounds
    
    # General search: try all search terms
    for search_term in search_terms:
        for node in root.iter("node"):
            node_text = node.attrib.get("text", "").lower().strip()
            content_desc = node.attrib.get("content-desc", "").lower().strip()
            resource_id = node.attrib.get("resource-id", "").lower()
            
            # Check if search term matches text, content-desc, or resource-id
            if (search_term in node_text or 
                search_term in content_desc or 
                search_term in resource_id):
                bounds = node.attrib.get("bounds")
                if bounds and bounds != "[0,0][0,0]":
                    return bounds
    
    return None


def find_element_by_attribute(attr_name, attr_value, partial_match=True):
    """
    Find UI element by attribute (content-desc, resource-id, etc.)
    
    Args:
        attr_name: Attribute name (e.g., "content-desc", "resource-id")
        attr_value: Value to search for (case-insensitive)
        partial_match: If True, match if value contains search term
    
    Returns:
        Bounds string like "[96,1344][984,1476]" or None if not found
    """
    root = dump_ui()
    if root is None:
        return None
    
    search_value = attr_value.lower().strip()
    
    for node in root.iter("node"):
        attr_val = node.attrib.get(attr_name, "").lower().strip()
        if attr_val:
            if partial_match:
                if search_value in attr_val:
                    bounds = node.attrib.get("bounds")
                    if bounds and bounds != "[0,0][0,0]":
                        return bounds
            else:
                if search_value == attr_val:
                    bounds = node.attrib.get("bounds")
                    if bounds and bounds != "[0,0][0,0]":
                        return bounds
    
    return None


def find_element_by_attribute(attr_name, attr_value, partial_match=True):
    """
    Find UI element by attribute (content-desc, resource-id, etc.)
    
    Args:
        attr_name: Attribute name (e.g., "content-desc", "resource-id")
        attr_value: Value to search for (case-insensitive)
        partial_match: If True, match if value contains search term
    
    Returns:
        Bounds string like "[96,1344][984,1476]" or None if not found
    """
    root = dump_ui()
    if root is None:
        return None
    
    search_value = attr_value.lower().strip()
    
    for node in root.iter("node"):
        attr_val = node.attrib.get(attr_name, "").lower().strip()
        if attr_val:
            if partial_match:
                if search_value in attr_val:
                    bounds = node.attrib.get("bounds")
                    if bounds and bounds != "[0,0][0,0]":
                        return bounds
            else:
                if search_value == attr_val:
                    bounds = node.attrib.get("bounds")
                    if bounds and bounds != "[0,0][0,0]":
                        return bounds
    
    return None


def get_screen_size():
    """
    Get device screen size (width, height)
    
    Returns:
        Tuple of (width, height) or None if failed
    """
    try:
        result = adb("shell wm size")
        # Output format: "Physical size: 1080x2400" or "Override size: 1080x2400"
        output = result.stdout.strip()
        if "x" in output:
            # Parse "1080x2400" format
            parts = output.split("x")
            if len(parts) >= 2:
                width_str = parts[0].split()[-1] if " " in parts[0] else parts[0]
                height_str = parts[1].split()[0] if " " in parts[1] else parts[1]
                width = int(width_str)
                height = int(height_str)
                return (width, height)
    except:
        pass
    return None


def bounds_to_center(bounds):
    """
    Convert bounds string to center coordinates
    
    Args:
        bounds: Bounds string like "[96,1344][984,1476]"
    
    Returns:
        Tuple of (x, y) center coordinates or (None, None) if invalid
    """
    try:
        # Parse bounds: "[x1,y1][x2,y2]"
        bounds = bounds.replace("[", "").replace("]", ",")
        coords = [int(x) for x in bounds.split(",") if x.strip()]
        if len(coords) >= 4:
            x1, y1, x2, y2 = coords[0], coords[1], coords[2], coords[3]
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            return (center_x, center_y)
    except:
        pass
    return (None, None)


def detect_current_screen():
    """
    Detect current screen/activity using package and activity name
    
    Returns:
        Dictionary with screen type and other info
    """
    try:
        result = adb("shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'")
        output = result.stdout
        
        # Try to extract package and activity
        if "md.obsidian" in output:
            if "FileActivity" in output:
                return {"current_screen": "vault_home", "package": "md.obsidian", "activity": "FileActivity"}
            elif "EditorActivity" in output or "NoteEditorActivity" in output:
                return {"current_screen": "note_editor", "package": "md.obsidian"}
            elif "WelcomeActivity" in output or "SetupActivity" in output:
                return {"current_screen": "welcome_setup", "package": "md.obsidian"}
            elif "VaultSelectionActivity" in output:
                return {"current_screen": "vault_selection", "package": "md.obsidian"}
        
        return {"current_screen": "unknown"}
    except:
        return {"current_screen": "unknown"}


def get_current_package_and_activity():
    """
    Get current package and activity name
    
    Returns:
        Dictionary with package and activity, or None if failed
    """
    try:
        result = adb("shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'")
        output = result.stdout
        
        # Extract package/activity from output
        # Format: "mCurrentFocus=Window{... package/activity}"
        if "/" in output:
            parts = output.split("/")
            if len(parts) >= 2:
                package_part = parts[0].split()[-1] if " " in parts[0] else parts[0]
                activity_part = parts[1].split()[0].split("}")[0] if "}" in parts[1] else parts[1].split()[0]
                
                return {
                    "package": package_part.strip(),
                    "activity": activity_part.strip()
                }
    except:
        pass
    return None


def reset_app(package_name="md.obsidian"):
    """
    Reset app state by clearing app data
    Useful for ensuring clean state between tests
    
    Args:
        package_name: Android package name (e.g., "md.obsidian")
    """
    try:
        adb(f"shell pm clear {package_name}")
        time.sleep(2)  # Wait for reset to complete
    except Exception as e:
        print(f"  ⚠️  Failed to reset app: {e}")
