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
        code: Key event code (e.g., 66 for ENTER, 4 for BACK, 67 for DELETE, 113 for CTRL+A)
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
        x1, y1: Start coordinates
        x2, y2: End coordinates
        duration: Swipe duration in milliseconds
    """
    adb(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
    time.sleep(0.5)


def open_app(package_name):
    """
    Open an app by package name
    
    Args:
        package_name: Android package name (e.g., "md.obsidian" for Obsidian)
    """
    adb(f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
    time.sleep(2)  # Wait for app to launch


def get_current_activity():
    """
    Get the current activity name
    
    Returns:
        Current activity name
    """
    result = adb("shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'")
    return result.stdout


def get_current_package_and_activity():
    """
    Get current package name and activity name
    
    Returns:
        Dictionary with "package" and "activity" keys, or {"package": None, "activity": None} if failed
    """
    import re
    try:
        result = adb("shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'")
        output = result.stdout
        
        # Pattern to match package/activity: "package.name/ActivityName"
        pattern = r'([\w\.]+)/([\w\.\$]+)'
        
        for line in output.split('\n'):
            if 'mCurrentFocus' in line or 'mFocusedApp' in line:
                match = re.search(pattern, line)
                if match:
                    package = match.group(1)
                    activity = match.group(2)
                    if package and activity:
                        return {"package": package, "activity": activity}
        
        # Fallback: try dumpsys activity activities
        try:
            result = subprocess.check_output(
                ["adb", "shell", "dumpsys", "activity", "activities"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=3
            )
            for line in result.split('\n'):
                if 'mResumedActivity' in line or 'mFocusedActivity' in line:
                    match = re.search(pattern, line)
                    if match:
                        package = match.group(1)
                        activity = match.group(2)
                        if package and activity:
                            return {"package": package, "activity": activity}
        except:
            pass
        
        return {"package": None, "activity": None}
    except Exception:
        return {"package": None, "activity": None}


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
        return True
    except Exception as e:
        print(f"Warning: Failed to reset app: {e}")
        return False


def dump_ui():
    """
    Dump UI hierarchy using uiautomator to /sdcard/ui.xml
    
    Returns:
        XML ElementTree root node or None if failed
    """
    import xml.etree.ElementTree as ET
    import time
    import re
    try:
        # Method 1: Try dumping to /sdcard/ui.xml
        try:
            subprocess.run(
                ["adb", "shell", "uiautomator", "dump", "/sdcard/ui.xml"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=5
            )
            time.sleep(0.5)  # Wait for file to be written
            
            # Read the XML file
            xml_data = subprocess.check_output(
                ["adb", "shell", "cat", "/sdcard/ui.xml"],
                text=True,
                timeout=5
            )
        except:
            # Method 2: Try dumping directly to stdout
            try:
                xml_data = subprocess.check_output(
                    ["adb", "shell", "uiautomator", "dump"],
                    text=True,
                    timeout=5
                )
            except:
                return None
        
        # Clean XML data
        # Remove any non-XML content before first <
        xml_start = xml_data.find('<')
        if xml_start > 0:
            xml_data = xml_data[xml_start:]
        
        # Remove any trailing non-XML content after last >
        xml_end = xml_data.rfind('>')
        if xml_end > 0:
            xml_data = xml_data[:xml_end + 1]
        
        # Remove invalid XML characters (keep only printable chars and XML special chars)
        xml_data = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\xFF\u0100-\uD7FF\uE000-\uFDCF\uFDF0-\uFFFD]', '', xml_data)
        
        # Parse XML
        try:
            root = ET.fromstring(xml_data)
            return root
        except ET.ParseError:
            # Try to fix by removing problematic attributes
            xml_data = re.sub(r'[^\x20-\x7E\n\r\t]', '', xml_data)
            root = ET.fromstring(xml_data)
            return root
            
    except Exception as e:
        return None


def get_ui_dump():
    """
    Get UI hierarchy dump using uiautomator (legacy function)
    
    Returns:
        XML string of UI hierarchy
    """
    root = dump_ui()
    if root is None:
        return ""
    import xml.etree.ElementTree as ET
    return ET.tostring(root, encoding='unicode')


def get_ui_text():
    """
    Extract visible text from UI using uiautomator dump
    
    Returns:
        List of visible text strings (non-empty only)
    """
    try:
        root = dump_ui()
        if root is None:
            return []
        texts = []
        # Iterate through all nodes in the hierarchy
        for node in root.iter():
            # Check all possible text attributes
            text = node.attrib.get('text', '').strip()
            content_desc = node.attrib.get('content-desc', '').strip()
            resource_id = node.attrib.get('resource-id', '').strip()
            class_name = node.attrib.get('class', '').strip()
            
            # Only add non-empty, meaningful text
            if text and len(text) > 0 and text not in texts:
                texts.append(text)
            if content_desc and len(content_desc) > 0 and content_desc not in texts:
                texts.append(content_desc)
            # Add resource-id if it contains meaningful info (not just package names)
            if resource_id and '/' in resource_id and resource_id not in texts:
                # Extract meaningful part (after last /)
                resource_part = resource_id.split('/')[-1]
                if len(resource_part) > 2 and resource_part not in texts:
                    texts.append(resource_part)
        return texts
    except Exception as e:
        return []


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
        search_terms.extend(["appearance", "theme", "color", "display"])
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
            if (("app" in node_text or "internal" in node_text) and
                "device" not in node_text and "device" not in content_desc and
                ("storage" in node_text or "storage" in content_desc)):
                bounds = node.attrib.get("bounds")
                if bounds and bounds != "[0,0][0,0]":
                    return bounds
        # If not found, return None to avoid matching wrong option
        return None
    
    # Second pass: general search for all other terms
    for node in root.iter("node"):
        node_text = node.attrib.get("text", "").lower().strip()
        content_desc = node.attrib.get("content-desc", "").lower().strip()
        resource_id = node.attrib.get("resource-id", "").lower()
        
        # Check if any search term matches
        for term in search_terms:
            if term and (term in node_text or term in content_desc or term in resource_id):
                bounds = node.attrib.get("bounds")
                if bounds and bounds != "[0,0][0,0]":  # Valid bounds
                    return bounds
    
    return None


def bounds_to_center(bounds):
    """
    Convert bounds string to center coordinates
    
    Args:
        bounds: String like "[96,1344][984,1476]"
    
    Returns:
        Tuple (x, y) center coordinates or (None, None) if invalid
    """
    try:
        b = bounds.replace("[", "").replace("]", ",").split(",")
        x1, y1, x2, y2 = map(int, b[:4])
        return (x1 + x2) // 2, (y1 + y2) // 2
    except Exception:
        return None, None


def detect_current_screen():
    """
    Detect the current Obsidian screen using adb shell dumpsys activity activities
    NEVER returns "unknown" if an activity is detected
    
    Returns:
        String: "welcome_setup", "vault_selection", "vault_name_input", "vault_home", "note_editor", or "unknown" (only if no activity detected)
    """
    import subprocess
    try:
        # Get current activities
        result = subprocess.check_output(
            ["adb", "shell", "dumpsys", "activity", "activities"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=3
        )
        
        # Check for Obsidian package
        if "md.obsidian" not in result:
            return "unknown"
        
        # Check for EditorActivity (note editor)
        if "md.obsidian/.EditorActivity" in result or "EditorActivity" in result:
            return "note_editor"
        
        # Check for FileActivity (vault home) - this is the main vault screen
        if "md.obsidian/.FileActivity" in result or "FileActivity" in result:
            # Double-check by looking at UI text - if we see vault name or note-related UI, we're in vault home
            try:
                ui_text = get_ui_text()
                if ui_text:
                    text_lower = " ".join(ui_text).lower()
                    # If we see vault name or note creation UI, definitely vault_home
                    if "internvault" in text_lower or "create note" in text_lower or "new note" in text_lower:
                        return "vault_home"
            except:
                pass
            return "vault_home"
        
        # Check for MainActivity or WelcomeActivity
        if "md.obsidian/.MainActivity" in result or "md.obsidian/.WelcomeActivity" in result or "MainActivity" in result:
            # Check for focused EditText to detect input screen
            try:
                focus_result = subprocess.check_output(
                    ["adb", "shell", "dumpsys", "window", "windows", "|", "grep", "-i", "EditText"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=2
                )
                # Also check if there's an active input field
                if "EditText" in focus_result or "mCurrentFocus" in focus_result:
                    # Check if EditText is focused
                    if "focused=true" in focus_result.lower() or "hasFocus" in focus_result:
                        return "vault_name_input"  # Intermediate screen for typing vault name
            except:
                pass
            
            # Try to get UI text to distinguish welcome_setup vs vault_selection
            try:
                ui_text = get_ui_text()
                if ui_text:
                    text_lower = " ".join(ui_text).lower()
                    # If we see "get started", "create", "vault" together, it's welcome setup
                    if ("get started" in text_lower or "create" in text_lower) and "vault" in text_lower:
                        return "welcome_setup"
                    # If we see vault names listed, it's vault_selection
                    if any(len(t) > 3 and t.isalnum() for t in ui_text):
                        return "vault_selection"
            except:
                pass
            
            # Default: assume welcome_setup if we can't determine (safer for first-time users)
            return "welcome_setup"
        
        # Fallback: check window focus
        try:
            focus_result = adb("shell dumpsys window windows | grep -E 'mCurrentFocus'")
            focus_output = focus_result.stdout.lower()
            
            if "md.obsidian" in focus_output:
                if "editor" in focus_output:
                    return "note_editor"
                elif "file" in focus_output:
                    return "vault_home"
                elif "main" in focus_output or "welcome" in focus_output:
                    # Check UI text to distinguish
                    ui_text = get_ui_text()
                    text_lower = " ".join(ui_text).lower()
                    if "create" in text_lower and "vault" in text_lower:
                        return "welcome_setup"
                    return "vault_selection"
        except:
            pass
        
        # If we detected Obsidian but couldn't determine screen, default to vault_selection
        return "vault_selection"
        
    except Exception:
        # Last resort: check if Obsidian is running
        try:
            focus_result = adb("shell dumpsys window windows | grep -E 'mCurrentFocus'")
            if "md.obsidian" in focus_result.stdout:
                return "vault_selection"  # Default if Obsidian is active
        except:
            pass
        return "unknown"


def detect_screen_state(package_name="md.obsidian"):
    """
    Detect current screen state based on activity detection and UI text
    
    Returns:
        Dictionary with detected state information
    """
    state = {
        "current_screen": detect_current_screen(),  # Use real activity detection
        "visible_text": [],
        "activity": "",
        "package": package_name
    }
    
    try:
        # Get activity
        activity_result = adb(f"shell dumpsys window windows | grep -E 'mCurrentFocus'")
        state["activity"] = activity_result.stdout.strip()
        
        # Get visible text (optional, for additional context)
        try:
            state["visible_text"] = get_ui_text()
        except Exception:
            state["visible_text"] = []
            
    except Exception as e:
        state["error"] = str(e)
    
    return state


def check_text_in_ui(text):
    """
    Check if text appears in current UI using UIAutomator dump
    
    Args:
        text: Text to search for (case-insensitive)
    
    Returns:
        Boolean indicating if text is found
    """
    try:
        ui_text = get_ui_text()
        text_lower = text.lower()
        for ui_item in ui_text:
            if text_lower in ui_item.lower():
                return True
        return False
    except Exception:
        return False


def check_vault_exists(vault_name):
    """
    Check if a vault exists by checking UI text (deterministic, no LLM)
    
    Args:
        vault_name: Name of the vault to check
    
    Returns:
        Boolean indicating if vault exists
    """
    # Check if vault name appears in UI
    if check_text_in_ui(vault_name):
        return True
    
    # Also check if we're in vault_home (implies vault exists)
    screen = detect_current_screen()
    if screen == "vault_home":
        return True
    
    return False


def check_note_exists(note_title):
    """
    Check if a note exists by searching UI text (deterministic, no LLM)
    
    Args:
        note_title: Title of the note to check
    
    Returns:
        Boolean indicating if note is visible
    """
    # Check if note title appears in UI
    if check_text_in_ui(note_title):
        return True
    
    # Also check if we're in note_editor (implies note exists)
    screen = detect_current_screen()
    if screen == "note_editor":
        return True
    
    return False

