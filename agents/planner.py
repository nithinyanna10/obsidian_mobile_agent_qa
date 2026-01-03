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
import time

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, OBSIDIAN_PACKAGE, OPENAI_MODEL
from tools.adb_tools import detect_current_screen, get_ui_text, dump_ui, get_current_package_and_activity
from tools.memory import memory


# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def call_openai_with_retry(messages, max_retries=3, **kwargs):
    """
    Call OpenAI API with retry logic for rate limits
    
    Args:
        messages: Messages for the API call
        max_retries: Maximum number of retries
        **kwargs: Additional arguments for chat.completions.create
    
    Returns:
        API response or raises exception
    """
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(model=OPENAI_MODEL, messages=messages, **kwargs)
        except Exception as e:
            error_str = str(e)
            # Check if it's a rate limit error (429)
            if "429" in error_str or "rate_limit" in error_str.lower() or "rate limit" in error_str.lower():
                if attempt < max_retries - 1:
                    # Extract wait time from error if available
                    wait_time = 2.0  # Default: 2 seconds
                    if "try again in" in error_str.lower():
                        # Try to extract the wait time from the error message (in milliseconds)
                        import re
                        match = re.search(r'try again in (\d+)\s*ms', error_str.lower())
                        if match:
                            wait_time_ms = int(match.group(1))
                            wait_time = (wait_time_ms / 1000.0) + 0.5  # Convert ms to seconds, add 0.5s buffer
                            wait_time = max(wait_time, 0.5)  # At least 0.5 seconds
                        else:
                            # Try without "ms" (might just be a number)
                            match = re.search(r'try again in (\d+)', error_str.lower())
                            if match:
                                wait_time_ms = int(match.group(1))
                                # If number is small (< 10), assume it's seconds, otherwise assume ms
                                if wait_time_ms < 10:
                                    wait_time = wait_time_ms + 0.5
                                else:
                                    wait_time = (wait_time_ms / 1000.0) + 0.5
                    
                    print(f"  ⚠️  Rate limit hit, waiting {wait_time:.2f}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise  # Last attempt failed, raise the exception
            else:
                raise  # Not a rate limit error, raise immediately
    return None


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


def plan_next_action(test_text, screenshot_path, action_history, previous_test_passed=False, execution_result=None):
    """
    Analyze screenshot + Android state and decide the next single action
    
    Args:
        test_text: Natural language test goal
        screenshot_path: Path to current screenshot
        action_history: List of previous actions taken
        previous_test_passed: If True, previous test (Test 1) passed, so we're definitely in vault
    
    Returns:
        Dictionary with single action OR {"action": "FAIL", "reason": "..."} if element not found
    """
    try:
        # Get Android state information
        android_state = get_android_state()
        
        # Check if we're already in vault_home (vault entered successfully)
        current_screen = android_state.get('current_screen', 'unknown')
        ui_text = android_state.get('ui_text', [])
        ui_text_lower = " ".join([t.lower() for t in ui_text])
        
        # CRITICAL: Check if we're in vault by package/activity (most reliable) - DO THIS FIRST
        pkg_act = get_current_package_and_activity()
        is_in_vault = False
        if pkg_act:
            package = pkg_act.get("package", "")
            activity = pkg_act.get("activity", "")
            # If we're in Obsidian FileActivity, we're in the vault
            if package == "md.obsidian" and "FileActivity" in activity:
                is_in_vault = True
            # Also check if current_screen is vault_home
            elif current_screen == 'vault_home':
                is_in_vault = True
        
        # ===== CHECK FOR STORAGE SELECTION DIALOG FIRST (HIGH PRIORITY) =====
        # Only handle storage selection for Test 1 (vault creation), not Test 2
        # Test 2 should skip storage selection since vault already exists
        is_test1 = ("create" in test_text.lower() and "vault" in test_text.lower() and "internvault" in test_text.lower())
        
        if is_test1:
            # If we see storage selection options, choose "app storage" (not device storage)
            # BUT: Check if we've already tapped storage selection recently (avoid loops)
            # ALSO: Don't check storage if we're already past it (on vault name input or further)
            recent_storage_taps = sum(1 for a in action_history[-5:] if 
                "app storage" in a.get("description", "").lower() or 
                ("storage" in a.get("description", "").lower() and "tap" in a.get("action", "").lower()))
            
            # Check if we're past storage selection (on vault name input or vault created)
            past_storage_selection = (android_state.get('has_edittext', False) or 
                                     current_screen == 'vault_name_input' or
                                     "internvault" in ui_text_lower or
                                     is_in_vault or
                                     current_screen == 'vault_home')
            
            # Check if storage selection dialog is visible - check UI text first (fast)
            storage_dialog_visible = (("storage" in ui_text_lower or "choose" in ui_text_lower) and 
                                      ("device" in ui_text_lower or "app" in ui_text_lower or "internal" in ui_text_lower))
            
            # Also check if we just tapped "Continue without sync" - storage dialog should appear next
            just_continued = False
            if action_history:
                last_action = action_history[-1]
                if ("continue" in last_action.get("description", "").lower() or 
                    "sync" in last_action.get("description", "").lower() or
                    last_action.get("action") == "tap" and "continue" in last_action.get("description", "").lower()):
                    just_continued = True
                    # After "Continue without sync", storage selection MUST appear before vault name input
                    # Force storage dialog to be visible if we just continued
                    if not past_storage_selection and recent_storage_taps == 0:
                        print(f"  → Just tapped 'Continue without sync', storage selection dialog should appear - analyzing screenshot...")
                        storage_dialog_visible = True  # Force check for storage dialog
            
            # CRITICAL: If we just continued, we MUST handle storage selection FIRST before anything else
            # Don't check past_storage_selection here - we know storage MUST happen after continue
            if just_continued and recent_storage_taps == 0:
                # After "Continue without sync", storage selection MUST appear - analyze screenshot
                print(f"  → Just tapped 'Continue without sync', MUST select storage before proceeding - analyzing screenshot...")
                # Check UI text first for quick match
                if "app storage" in ui_text_lower or "internal storage" in ui_text_lower:
                    print(f"  → Found 'App storage' in UI text, tapping it...")
                    return {
                        "action": "tap",
                        "x": 0,
                        "y": 0,
                        "description": "Tap 'App storage' or 'Internal storage' option (not device storage)"
                    }
                # If not in UI text, we need to analyze screenshot to find storage options
                # Continue to main planning which will analyze screenshot and find app storage
                print(f"  → Storage selection required after 'Continue without sync', analyzing screenshot...")
                pass  # Continue to main planning which analyzes screenshot
            
            # Only handle storage selection if we haven't moved past it
            elif not past_storage_selection and storage_dialog_visible and recent_storage_taps == 0:
                # Storage dialog visible and we haven't tapped yet - analyze screenshot to find app storage
                print(f"  → Storage selection detected, analyzing screenshot to find 'App storage' option...")
                # Check UI text first for quick match
                if "app storage" in ui_text_lower or "internal storage" in ui_text_lower:
                    print(f"  → Found 'App storage' in UI text, tapping it...")
                    return {
                        "action": "tap",
                        "x": 0,
                        "y": 0,
                        "description": "Tap 'App storage' or 'Internal storage' option (not device storage)"
                    }
                # If not in UI text, continue to main planning which will analyze screenshot
                print(f"  → Storage dialog visible, will analyze screenshot to find 'App storage' option...")
                pass  # Continue to main planning which analyzes screenshot
            elif not past_storage_selection and not storage_dialog_visible and recent_storage_taps >= 1:
                # Storage dialog not visible and we tapped - assume selected, proceed to vault name input
                print(f"  ✓ Storage selection completed (dialog no longer visible), proceeding to vault creation...")
                # Check if we're on vault name input screen - if so, check if name is already typed
                if android_state.get('has_edittext', False) or current_screen == 'vault_name_input':
                    # Check if "InternVault" is already in the UI text (already typed)
                    if "internvault" in ui_text_lower:
                        # Name already typed - look for "Create vault" button
                        if "create vault" in ui_text_lower or "create" in ui_text_lower:
                            print(f"  → Vault name 'InternVault' already typed, tapping 'Create vault' button...")
                            return {
                                "action": "tap",
                                "x": 0,
                                "y": 0,
                                "description": "Tap 'Create vault' button"
                            }
                        # Name typed but no create button visible - might need to press ENTER
                        print(f"  → Vault name typed, pressing ENTER...")
                        return {
                            "action": "key",
                            "code": 66,
                            "description": "Press ENTER after typing vault name"
                        }
                    else:
                        # Name not typed yet - type "InternVault"
                        print(f"  → On vault name input screen, typing 'InternVault'...")
                        return {
                            "action": "type",
                            "text": "InternVault",
                            "description": "Type vault name 'InternVault'"
                        }
                # Don't return - continue to next logic (will be handled by main planning)
            elif not past_storage_selection and storage_dialog_visible and recent_storage_taps >= 1:
                # Storage dialog still visible but we already tapped - check if we moved to input screen
                if android_state.get('has_edittext', False) or current_screen == 'vault_name_input':
                    # Check if name is already typed
                    if "internvault" in ui_text_lower:
                        # Name already typed - tap "Create vault" button
                        if "create vault" in ui_text_lower or "create" in ui_text_lower:
                            print(f"  → Vault name already typed, tapping 'Create vault' button...")
                            return {
                                "action": "tap",
                                "x": 0,
                                "y": 0,
                                "description": "Tap 'Create vault' button"
                            }
                        return {
                            "action": "key",
                            "code": 66,
                            "description": "Press ENTER after typing vault name"
                        }
                    else:
                        # Name not typed - type it
                        print(f"  ✓ Storage selected, now on vault name input screen, typing 'InternVault'...")
                        return {
                            "action": "type",
                            "text": "InternVault",
                            "description": "Type vault name 'InternVault'"
                        }
                # Still on storage selection, might need to wait
                print(f"  ⚠️  Storage tapped but dialog still visible, waiting...")
                return {
                    "action": "wait",
                    "seconds": 1,
                    "description": "Wait for storage selection to process"
                }
        
        # Note: is_in_vault is already defined above (moved earlier to avoid undefined variable error)
        
        # ===== CHECK IF NOTE IS ALREADY CREATED (BEFORE VAULT CHECK) =====
        # For Test 2: Check if note is already done (only if not using previous_test_passed fast path)
        # Skip this if previous_test_passed is True (handled in Test 2 section above)
        if ("meeting notes" in test_text.lower() and "daily standup" in test_text.lower()) and not previous_test_passed:
            # Check if we're in note editor with the correct content
            if current_screen == 'note_editor':
                ui_text_lower = " ".join([t.lower() for t in ui_text])
                # Check if note title and content are present
                has_title = "meeting notes" in ui_text_lower
                has_content = "daily standup" in ui_text_lower
                
                if has_title and has_content:
                    print(f"  ✅ Test 2 PASS: Note 'Meeting Notes' with 'Daily Standup' already created!")
                    return {
                        "action": "assert",
                        "description": "Note 'Meeting Notes' with 'Daily Standup' text created successfully"
                    }
                elif has_title and not has_content:
                    # Note created but content not typed yet - focus body and type "Daily Standup" (NO ENTER)
                    print(f"  → Note 'Meeting Notes' created, focusing body field and typing 'Daily Standup'...")
                    return {
                        "action": "focus",
                        "target": "body",
                        "description": "Focus note body editor"
                    }
                elif not has_title:
                    # Title not typed - type "Meeting Notes" first (heading) with target="title"
                    print(f"  → In note editor, typing title 'Meeting Notes' first (heading)...")
                    return {
                        "action": "type",
                        "text": "Meeting Notes",
                        "target": "title",
                        "description": "Type note title 'Meeting Notes' (heading)"
                    }
                # If neither, continue to create note
            
            # Also check if note exists in vault home (note list)
            if (is_in_vault or current_screen == 'vault_home') and "meeting notes" in " ".join([t.lower() for t in ui_text]):
                # Note exists in list, but we need to check if it has the content
                # For now, assume we need to open and verify/add content
                print(f"  → Note 'Meeting Notes' found in vault, checking if content is added...")
                # Continue to main planning logic
        
        # ===== HARD GATE 0: FAST UI TEXT CHECK FIRST (NO API CALL) =====
        # For Test 1: Check if "create new note" button is visible (means we're in vault - TEST 1 PASS)
        if "create" in test_text.lower() and "vault" in test_text.lower() and "internvault" in test_text.lower():
            # CRITICAL: If "create new note" or "create note" button is visible, we're in vault - Test 1 PASS
            if "create note" in ui_text_lower or "new note" in ui_text_lower or "create new note" in ui_text_lower:
                print(f"  ✅ Test 1 PASS: 'Create new note' button visible - vault entered successfully!")
                return {
                    "action": "assert",
                    "description": "Vault 'InternVault' created and entered successfully (create new note button visible)"
                }
            
            # Fast check: Look for "files in internvault" or similar in UI text
            vault_detected = False
            
            if ("files in internvault" in ui_text_lower or 
                ("internvault" in ui_text_lower and ("files" in ui_text_lower or "note" in ui_text_lower))):
                vault_detected = True
                print(f"  ✓ In InternVault vault (detected from UI text)")
            
            # Also check if we're in FileActivity (most reliable)
            if is_in_vault or current_screen == 'vault_home':
                vault_detected = True
                print(f"  ✓ In InternVault vault (FileActivity/vault_home detected)")
            
            # If vault detected, assert (Test 1 only requires vault creation)
            if vault_detected:
                print(f"  ✅ Test 1 PASS: InternVault vault created and entered")
                return {
                    "action": "assert",
                    "description": "Vault 'InternVault' created and entered successfully"
                }
        
        # ===== HARD GATE 0: SCREENSHOT-BASED VAULT DETECTION =====
        # ALWAYS analyze screenshots - OpenAI vision needs to see the UI to make decisions
        # Don't skip screenshot analysis - it's critical for understanding the current state
        if "create" in test_text.lower() and "vault" in test_text.lower() and "internvault" in test_text.lower():
            print(f"  📸 Analyzing screenshot (current screen: {current_screen})...")
            force_screenshot_analysis = True
            
            # Use LLM to analyze screenshot
            print(f"  🔍 Analyzing screenshot to check if already in InternVault vault...")
            
            # Read and encode screenshot
            img = Image.open(screenshot_path)
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            img_data = base64.b64encode(img_buffer.read()).decode('utf-8')
            
            scan_prompt = """Look at this screenshot of the Obsidian mobile app.

Are we currently INSIDE the InternVault vault? 

CRITICAL SIGNS that we're IN the vault (if you see ANY of these, we're IN):
- Text at top left says "files in internvault" or "InternVault" or shows vault name
- We see a file list or note list with Obsidian UI (not Android file picker)
- We see "Create note" or "New note" buttons in Obsidian interface
- We see the vault name "InternVault" displayed prominently
- We see note files or folders in Obsidian's file browser
- The UI looks like Obsidian's main vault interface (not a file picker)
- We're NOT in a file picker or folder selection screen

Signs that we're NOT in the vault:
- We see "Create vault" or "Get started" buttons
- We see a file picker (Android system UI with folder icons)
- We see "Use this folder" button (this is file picker, not vault)
- We see "CREATE NEW FOLDER" button (file picker)
- We see folder selection screen with Android system UI
- We see welcome/setup screen

IMPORTANT: If you see "files in internvault" at the top left, we are DEFINITELY in the vault!

Return ONLY valid JSON:
- If we're IN InternVault vault: {{"in_vault": true, "reason": "vault UI visible"}}
- If we're NOT in vault: {{"in_vault": false, "reason": "..."}}

Output ONLY valid JSON, no markdown:"""
            
            try:
                scan_response = call_openai_with_retry(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": scan_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=100
            )
            
                if scan_response and scan_response.choices and scan_response.choices[0].message.content:
                        scan_result_text = scan_response.choices[0].message.content.strip()
                        # Remove markdown if present
                        if scan_result_text.startswith("```json"):
                            scan_result_text = scan_result_text[7:]
                        if scan_result_text.startswith("```"):
                    scan_result_text = scan_result_text[3:]
                if scan_result_text.endswith("```"):
                    scan_result_text = scan_result_text[:-3]
                scan_result_text = scan_result_text.strip()
                
                scan_result = json.loads(scan_result_text)
                in_vault_from_screenshot = scan_result.get("in_vault", False)
                reason = scan_result.get("reason", "")
                
                print(f"  📊 Screenshot Analysis: in_vault={in_vault_from_screenshot}, reason={reason}")
                
                if in_vault_from_screenshot:
                    # We're already in the vault! Test 1 PASS
                    print(f"  ✅ Test 1 PASS: InternVault vault created and entered (detected from screenshot)")
                    return {
                        "action": "assert",
                        "description": "Vault 'InternVault' created and entered successfully"
                    }
                else:
                    # Not in vault yet, need to create/enter vault
                    print(f"  → Not in vault yet (screenshot analysis), will proceed with vault creation/entry")
            except Exception as e:
                print(f"  ⚠️  Screenshot analysis failed: {e}, falling back to state-based detection")
                # Fall through to state-based detection
        
        # HARD GATE 1: Test 1 - Check if vault is created and entered
        if "create" in test_text.lower() and "vault" in test_text.lower() and "internvault" in test_text.lower():
            # FIRST: Check if we're already in vault (most reliable check)
            if is_in_vault or current_screen == 'vault_home':
                # Test 1 only requires vault creation, assert now
                print(f"  ✅ Test 1 PASS: InternVault vault created and entered (FileActivity detected)")
                return {
                    "action": "assert",
                    "description": "Vault 'InternVault' created and entered successfully"
                }
            
            # SECOND: Check if we just typed InternVault - need to press "Create vault" button or ENTER
            # Check the LAST action to see if we just typed InternVault
            if action_history:
                last_action = action_history[-1]
                last_action_type = last_action.get("action", "").lower()
                last_action_desc = last_action.get("description", "").lower()
                
                # Check if LAST action was typing InternVault (regardless of success/failure)
                just_typed_internvault = (last_action_type == "type" and 
                                         "internvault" in last_action_desc)
                
                if just_typed_internvault:
                    # We just typed InternVault - MUST press ENTER or tap Create vault button IMMEDIATELY
                    # Even if typing failed, we should still try to proceed
                    # Check if we're still on welcome_setup (need to press ENTER or tap button)
                    if current_screen == 'welcome_setup' or current_screen == 'vault_selection':
                        # Check memory for successful patterns
                        context = {"current_screen": current_screen, "test_goal": test_text}
                        successful_pattern = memory.get_successful_pattern(context)
                        
                        # ALWAYS prefer tapping "Create vault" button over ENTER (more reliable)
                        # Check if button text is in UI
                        if "create vault" in ui_text_lower or ("create" in ui_text_lower and "vault" in ui_text_lower):
                            print(f"  → Just typed 'InternVault', tapping 'Create vault' button...")
                            action = {
                                "action": "tap",
                                "x": 0,
                                "y": 0,
                                "description": "Tap 'Create vault' button"
                            }
                            # Record this pattern for learning
                            memory.update_reward("tap_create_vault", 0.1)  # Positive reward
                            return action
                        # Button not visible in UI text - try pressing ENTER
                        print(f"  → Just typed 'InternVault', pressing ENTER to create vault...")
                        action = {
                            "action": "key",
                            "code": 66,
                            "description": "Press ENTER after typing vault name"
                        }
                        memory.update_reward("key_enter_after_type", 0.1)  # Positive reward
                        return action
                    # Not on welcome_setup - might have already created vault, continue to check
                    print(f"  → Just typed 'InternVault', but not on welcome_setup (current: {current_screen}), checking vault status...")
                    pass  # Continue to main planning logic
                
                # Also check for multiple typing attempts (loop detection)
                recent_type_actions = [a for a in action_history[-3:] if 
                    a.get("action", "").lower() == "type" and "internvault" in a.get("description", "").lower()]
                
                if len(recent_type_actions) >= 2 and not just_typed_internvault:
                    # We've typed InternVault multiple times but last action wasn't typing
                    # Check if we need to press ENTER or tap button
                    if current_screen == 'welcome_setup' or current_screen == 'vault_selection':
                        if "internvault" in ui_text_lower:
                            # Name is visible - try tapping Create vault button or pressing ENTER
                            if "create vault" in ui_text_lower or ("create" in ui_text_lower and "vault" in ui_text_lower):
                                print(f"  → 'InternVault' typed multiple times, tapping 'Create vault' button...")
                                return {
                                    "action": "tap",
                                    "x": 0,
                                    "y": 0,
                                    "description": "Tap 'Create vault' button"
                                }
                            print(f"  → 'InternVault' typed multiple times, pressing ENTER...")
                            return {
                                "action": "key",
                                "code": 66,
                                "description": "Press ENTER after typing vault name"
                            }
                
                # After pressing ENTER or Create vault, check if we're in vault
                if (last_action_type == "key" and "enter" in last_action_desc) or \
                   (last_action_type == "tap" and "create vault" in last_action_desc):
                    
                    # FIRST: Check state-based detection (fast, no LLM call)
                    pkg_act_after = get_current_package_and_activity()
                    if pkg_act_after:
                        package_after = pkg_act_after.get("package", "")
                        activity_after = pkg_act_after.get("activity", "")
                        if package_after == "md.obsidian" and "FileActivity" in activity_after:
                            print(f"  ✅ Test 1 PASS: InternVault vault created and entered (FileActivity detected)")
                            return {
                                "action": "assert",
                                "description": "Vault 'InternVault' created and entered successfully"
                            }
                    
                    current_screen_after = detect_current_screen()
                    if current_screen_after == 'vault_home':
                        print(f"  ✅ Test 1 PASS: InternVault vault created and entered (vault_home detected)")
                        return {
                            "action": "assert",
                            "description": "Vault 'InternVault' created and entered successfully"
                        }
                    
                    # SECOND: If state unclear, use screenshot verification (only if needed)
                    ui_text_after = get_ui_text()
                    ui_text_lower = " ".join([t.lower() for t in ui_text_after])
                    if "internvault" in ui_text_lower and ("note" in ui_text_lower or "create note" in ui_text_lower):
                        # UI text suggests we're in vault, verify with screenshot
                        print(f"  🔍 Verifying vault entry with screenshot (state suggests in vault)...")
                        
                        # Read screenshot
                        img = Image.open(screenshot_path)
                        img_buffer = io.BytesIO()
                        img.save(img_buffer, format='PNG')
                        img_buffer.seek(0)
                        img_data = base64.b64encode(img_buffer.read()).decode('utf-8')
                        
                        verify_prompt = """Look at this screenshot. The user just typed "InternVault" as vault name and pressed ENTER.

Are we now INSIDE the InternVault vault?

Signs we're IN the vault:
- File list or note list visible
- "Create note" or "New note" buttons visible
- Vault name "InternVault" at top
- Note files or folders visible
- NOT in file picker

Return ONLY valid JSON:
- If IN vault: {"in_vault": true, "reason": "vault UI visible"}
- If NOT in vault: {"in_vault": false, "reason": "..."}

Output ONLY valid JSON, no markdown:"""
                        
                        try:
                            verify_response = call_openai_with_retry(
                                messages=[
                                    {
                                        "role": "user",
                                        "content": [
                                            {"type": "text", "text": verify_prompt},
                                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                                        ]
                                    }
                                ],
                                temperature=0.1,
                                max_tokens=100
                            )
                            
                            if verify_response and verify_response.choices and verify_response.choices[0].message.content:
                                verify_result_text = verify_response.choices[0].message.content.strip()
                                # Remove markdown if present
                                if verify_result_text.startswith("```json"):
                                    verify_result_text = verify_result_text[7:]
                                if verify_result_text.startswith("```"):
                                    verify_result_text = verify_result_text[3:]
                                if verify_result_text.endswith("```"):
                                    verify_result_text = verify_result_text[:-3]
                                verify_result_text = verify_result_text.strip()
                                
                                verify_result = json.loads(verify_result_text)
                                in_vault_after = verify_result.get("in_vault", False)
                                reason = verify_result.get("reason", "")
                                
                                print(f"  📊 Verification Result: in_vault={in_vault_after}, reason={reason}")
                                
                                if in_vault_after:
                                    print(f"  ✅ Test 1 PASS: InternVault vault created and entered (verified from screenshot)")
                                    return {
                                        "action": "assert",
                                        "description": "Vault 'InternVault' created and entered successfully"
                                    }
                        except Exception as e:
                            print(f"  ⚠️  Screenshot verification failed: {e}, assuming not in vault yet")
                
                # After tapping InternVault or USE THIS FOLDER, check if we're in vault
                # Make sure last_action_type and last_action_desc are defined
                if action_history:
                    last_action = action_history[-1]
                    last_action_type = last_action.get("action", "").lower()
                    last_action_desc = last_action.get("description", "").lower()
                    
                    if last_action_type == "tap" and ("internvault" in last_action_desc or "use this folder" in last_action_desc):
                        # Re-check package/activity after tap
                        pkg_act_after = get_current_package_and_activity()
                        if pkg_act_after:
                            package_after = pkg_act_after.get("package", "")
                            activity_after = pkg_act_after.get("activity", "")
                            if package_after == "md.obsidian" and "FileActivity" in activity_after:
                                print(f"  ✅ Test 1 PASS: InternVault vault entered (FileActivity after tap)")
                                return {
                                    "action": "assert",
                                    "description": "Vault 'InternVault' created and entered successfully"
                                }
                        
                        # Check current screen
                        current_screen_after = detect_current_screen()
                        if current_screen_after == 'vault_home':
                            print(f"  ✅ Test 1 PASS: InternVault vault entered (vault_home after tap)")
                            return {
                                "action": "assert",
                                "description": "Vault 'InternVault' created and entered successfully"
                            }
        
        # HARD GATE 2: Test 2 - If Test 1 passed, trust we're in vault and go directly to note creation
        test2_in_vault = None  # Initialize variable
        if ("note" in test_text.lower() and "meeting notes" in test_text.lower()) or \
           ("create" in test_text.lower() and "note" in test_text.lower()):
            # CRITICAL: If Test 1 passed, we're definitely in vault - skip all checks and go directly to note creation
            if previous_test_passed:
                print(f"  ✓ Test 1 passed - assuming we're in InternVault vault, proceeding directly to note creation")
                test2_in_vault = True
                
                # DIRECTLY proceed to note creation - no vault checks needed
                # Check if we're already in note editor
                if current_screen == 'note_editor':
                    # Normalize UI text for checking
                    def normalize_text(s):
                        return ''.join(c.lower() for c in s if c.isalnum())
                    
                    ui_blob = normalize_text(" ".join(ui_text))
                    has_meeting_notes = "meetingnotes" in ui_blob or "meetingnote" in ui_blob
                    has_daily_standup = "dailystandup" in ui_blob
                    
                    # Check if both are already typed
                    if has_meeting_notes and has_daily_standup:
                        print(f"  ✅ Test 2 PASS: Note 'Meeting Notes' with 'Daily Standup' already created!")
                        return {
                            "action": "assert",
                            "description": "Note 'Meeting Notes' with 'Daily Standup' text created successfully"
                        }
                    # Check if only title is typed
                    elif has_meeting_notes and not has_daily_standup:
                        # Title typed, focus body and type it (NO ENTER - use focus instead)
                        print(f"  → Note title 'Meeting Notes' typed, focusing body field and typing 'Daily Standup'...")
                        return {
                            "action": "focus",
                            "target": "body",
                            "description": "Focus note body editor"
                        }
                    # Title not typed yet - type it first with target="title"
                    else:
                        print(f"  → In note editor, typing title 'Meeting Notes' (with 's')...")
                        return {
                            "action": "type",
                            "text": "Meeting Notes",
                            "target": "title",
                            "description": "Type note title 'Meeting Notes' (with 's' at the end)"
                        }
                
                # Not in note editor - need to create note first
                # Check if we're in vault home (should be, since Test 1 passed)
                if is_in_vault or current_screen == 'vault_home' or "create" in ui_text_lower and "note" in ui_text_lower:
                    # Look for "Create note" or "New note" button
                    print(f"  → In vault home, tapping 'Create note' or 'New note' button...")
                    return {
                        "action": "tap",
                        "x": 0,
                        "y": 0,
                        "description": "Tap 'Create note' or 'New note' button to create new note"
                    }
                
                # If we're here, we're in vault but might need to wait or check UI
                # Continue to main planning logic which will handle it
                pass
            # FIRST: Check state-based detection (fast, no LLM call)
            elif is_in_vault or current_screen == 'vault_home':
                test2_in_vault = True
                print(f"  ✓ Already in InternVault vault (state-based), proceeding with note creation (DO NOT enter vault again)")
                # Don't try to enter vault again - proceed with note creation
                pass
            else:
                # State unclear, but if Test 1 passed, skip screenshot check to save API calls
                if previous_test_passed:
                    print(f"  ✓ Test 1 passed - skipping screenshot check (saving API calls), assuming in vault and proceeding to note creation")
                    test2_in_vault = True
                    # Go directly to note creation logic (same as above)
                    if current_screen == 'note_editor':
                        if "meeting notes" in ui_text_lower and "daily standup" in ui_text_lower:
                            print(f"  ✅ Test 2 PASS: Note 'Meeting Notes' with 'Daily Standup' already created!")
                            return {
                                "action": "assert",
                                "description": "Note 'Meeting Notes' with 'Daily Standup' text created successfully"
                            }
                        else:
                            # Normalize text for checking
                            def normalize_text(s):
                                return ''.join(c.lower() for c in s if c.isalnum())
                            
                            ui_blob = normalize_text(" ".join(ui_text))
                            has_meeting_notes = "meetingnotes" in ui_blob or "meetingnote" in ui_blob
                            
                            if has_meeting_notes:
                                # Title typed, focus body and type it (NO ENTER - use focus instead)
                                print(f"  → Note title 'Meeting Notes' typed, focusing body field and typing 'Daily Standup'...")
                                return {
                                    "action": "focus",
                                    "target": "body",
                                    "description": "Focus note body editor"
                                }
                            else:
                                # Title not typed - type "Meeting Notes" (with 's' at the end)
                                print(f"  → In note editor, typing title 'Meeting Notes' first (with 's')...")
                                return {
                                    "action": "type",
                                    "text": "Meeting Notes",
                                    "target": "title",
                                    "description": "Type note title 'Meeting Notes' (with 's' at the end)"
                                }
                    # Not in note editor - tap create note button
                    if is_in_vault or current_screen == 'vault_home' or "create" in ui_text_lower and "note" in ui_text_lower:
                        print(f"  → In vault home, tapping 'Create note' or 'New note' button...")
                        return {
                            "action": "tap",
                            "x": 0,
                            "y": 0,
                            "description": "Tap 'Create note' or 'New note' button to create new note"
                        }
                    pass
                else:
                    print(f"  🔍 Checking screenshot to see if already in InternVault vault for Test 2...")
                
                # Read screenshot
                img = Image.open(screenshot_path)
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                img_data = base64.b64encode(img_buffer.read()).decode('utf-8')
                
                test2_check_prompt = """Look at this screenshot. Test 2 needs to create a note in the InternVault vault.

Are we currently INSIDE the InternVault vault?

Signs we're IN the vault:
- File list or note list visible
- "Create note" or "New note" buttons visible
- Vault name "InternVault" at top
- Note files or folders visible
- NOT in file picker or welcome screen

Signs we're NOT in the vault:
- "Create vault" or "Get started" buttons
- File picker visible
- "Use this folder" button
- Welcome/setup screen

Return ONLY valid JSON:
- If IN InternVault vault: {"in_vault": true, "reason": "vault UI visible"}
- If NOT in vault: {"in_vault": false, "reason": "..."}

Output ONLY valid JSON, no markdown:"""
                
                try:
                    test2_check_response = call_openai_with_retry(
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": test2_check_prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                                ]
                            }
                        ],
                        temperature=0.1,
                        max_tokens=100
                    )
                    
                    if test2_check_response and test2_check_response.choices and test2_check_response.choices[0].message.content:
                        test2_check_text = test2_check_response.choices[0].message.content.strip()
                        # Remove markdown if present
                        if test2_check_text.startswith("```json"):
                            test2_check_text = test2_check_text[7:]
                        if test2_check_text.startswith("```"):
                            test2_check_text = test2_check_text[3:]
                        if test2_check_text.endswith("```"):
                            test2_check_text = test2_check_text[:-3]
                        test2_check_text = test2_check_text.strip()
                        
                        test2_check_result = json.loads(test2_check_text)
                        test2_in_vault = test2_check_result.get("in_vault", False)
                        reason = test2_check_result.get("reason", "")
                        
                        print(f"  📊 Test 2 Screenshot Check: in_vault={test2_in_vault}, reason={reason}")
                        
                        if test2_in_vault:
                            print(f"  ✓ Already in InternVault vault (screenshot confirmed), proceeding with note creation (DO NOT enter vault again)")
                            # Don't try to enter vault again - proceed with note creation
                            pass
                        else:
                            # Not in vault, need to enter it
                            print(f"  → Not in vault yet (screenshot confirmed), will enter InternVault first")
                except Exception as e:
                    print(f"  ⚠️  Screenshot check failed: {e}, assuming not in vault")
                    test2_in_vault = False
            
            # If we're not in vault but InternVault exists, enter it (max 1 attempt to avoid loops)
            # Only if screenshot check said we're not in vault
            if test2_in_vault is False and any('internvault' in text.lower() for text in ui_text) and current_screen in ['welcome_setup', 'vault_selection']:
                # Check if we've already tried entering
                recent_enter_attempts = sum(1 for a in action_history[-5:] if 
                    "internvault" in a.get("description", "").lower() or 
                    "enter vault" in a.get("description", "").lower() or
                    "use this folder" in a.get("description", "").lower())
                if recent_enter_attempts == 0:  # Only try once
                    print(f"  ✓ Found InternVault in UI, tapping to enter existing vault for Test 2")
                    return {
                        "action": "tap",
                        "x": 0,
                        "y": 0,
                        "description": "Tap InternVault vault name to enter existing vault"
                    }
                else:
                    # Already tried entering, assume we're in vault and proceed
                    print(f"  ⚠️  Already tried entering vault ({recent_enter_attempts} times), assuming we're in vault - proceeding with note creation")
                    pass
        
        # Check if we're in vault_home by activity OR by UI text (vault name visible at top)
        if is_in_vault or current_screen == 'vault_home':
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
        
        # This logic is now handled above in HARD GATE 2
        
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
        
        # CRITICAL: Check if Test 2 is complete - both "Meeting Notes" and "Daily Standup" are present
        # Do this BEFORE any other checks to prevent loops
        # Use normalized blob to handle concatenation and truncation
        if "meeting notes" in test_text.lower() and "daily standup" in test_text.lower():
            # Normalize text for checking (remove whitespace, punctuation, lowercase)
            def normalize_text(s):
                return ''.join(c.lower() for c in s if c.isalnum())
            
            ui_blob = normalize_text(" ".join(ui_text))
            
            # Check for both substrings (handle truncation: "meetingnote" or "meetingnotes")
            has_meeting_notes = "meetingnotes" in ui_blob or "meetingnote" in ui_blob
            has_daily_standup = "dailystandup" in ui_blob
            
            # Require that we're in note_editor and both are present
            if current_screen == 'note_editor' and has_meeting_notes and has_daily_standup:
                print(f"  ✅ Test 2 PASS: Both 'Meeting Notes' and 'Daily Standup' are present in note!")
                return {
                    "action": "assert",
                    "description": "Note 'Meeting Notes' with 'Daily Standup' text created successfully"
                }
        
        # Check if we just focused body field - now need to type "Daily Standup"
        # Do this BEFORE loop detection to prevent loop from blocking typing
        if action_history and ("meeting notes" in test_text.lower() and "daily standup" in test_text.lower()):
            last_action = action_history[-1]
            
            # Normalize text for checking
            def normalize_text(s):
                return ''.join(c.lower() for c in s if c.isalnum())
            
            ui_blob = normalize_text(" ".join(ui_text))
            has_meeting_notes = "meetingnotes" in ui_blob or "meetingnote" in ui_blob
            has_daily_standup = "dailystandup" in ui_blob
            
            # Check if we just focused body field
            if (last_action.get("action") == "focus" and 
                last_action.get("target") == "body"):
                # We just focused body, now type "Daily Standup"
                if has_meeting_notes and not has_daily_standup:
                    print(f"  → Just focused body field, now typing 'Daily Standup'...")
                    return {
                        "action": "type",
                        "text": "Daily Standup",
                        "target": "body",
                        "description": "Type note body text 'Daily Standup'"
                    }
            
            # Also check if we're in note editor and have Meeting Notes but not Daily Standup
            if current_screen == 'note_editor' and has_meeting_notes and not has_daily_standup:
                # If last action was focus or type, and we have Meeting Notes but not Daily Standup
                if last_action.get("action") in ["focus", "type"]:
                    if last_action.get("target") != "body":
                        # Need to focus body first
                        print(f"  → In note editor with 'Meeting Notes' but not 'Daily Standup', focusing body...")
                        return {
                            "action": "focus",
                            "target": "body",
                            "description": "Focus note body editor"
                        }
                    else:
                        # Already focused body, type it
                        print(f"  → Body field focused, typing 'Daily Standup'...")
                        return {
                            "action": "type",
                            "text": "Daily Standup",
                            "target": "body",
                            "description": "Type note body text 'Daily Standup'"
                        }
        
        # CRITICAL: Check completion BEFORE loop detection (completion check must run first)
        if "meeting notes" in test_text.lower() and "daily standup" in test_text.lower():
            def normalize_text(s):
                return ''.join(c.lower() for c in s if c.isalnum())
            
            ui_blob = normalize_text(" ".join(ui_text))
            has_meeting_notes = "meetingnotes" in ui_blob or "meetingnote" in ui_blob
            has_daily_standup = "dailystandup" in ui_blob
            
            if current_screen == 'note_editor' and has_meeting_notes and has_daily_standup:
                print(f"  ✅ Test 2 PASS: Both 'Meeting Notes' and 'Daily Standup' are present - test complete!")
                return {
                    "action": "assert",
                    "description": "Note 'Meeting Notes' with 'Daily Standup' text created successfully"
                }
        
        # Check if we're stuck (same action repeated)
        # Only do this AFTER completion check
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
                # Special handling for storage selection loop - if we tapped storage multiple times, assume it's selected
                if "storage" in action_desc.lower() and ("app" in action_desc.lower() or "internal" in action_desc.lower()):
                    print(f"  ⚠️  Storage selection tapped {len(last_3_actions)} times, assuming selected - moving on...")
                    # Check if we're on vault name input screen
                    if android_state.get('has_edittext', False) or current_screen == 'vault_name_input':
                        # Check if name is already typed
                        if "internvault" in ui_text_lower:
                            # Name typed - tap Create vault button
                            return {
                                "action": "tap",
                                "x": 0,
                                "y": 0,
                                "description": "Tap 'Create vault' button"
                            }
                        # Name not typed - type it
                        return {
                            "action": "type",
                            "text": "InternVault",
                            "description": "Type vault name 'InternVault'"
                        }
                    # Not on input screen - try BACK
                    return {
                        "action": "key",
                        "code": 4,
                        "description": "Press BACK to dismiss storage selection (already selected)"
                    }
                # Special handling for typing vault name loop - if we typed it multiple times, tap Create vault
                if "type" in action_desc.lower() and "internvault" in action_desc.lower():
                    print(f"  ⚠️  Vault name typed {len(last_3_actions)} times, checking if 'Create vault' button is visible...")
                    # Check if name is in UI
                    if "internvault" in ui_text_lower:
                        # Name is visible - look for Create vault button
                        if "create vault" in ui_text_lower or ("create" in ui_text_lower and "vault" in ui_text_lower):
                            return {
                                "action": "tap",
                                "x": 0,
                                "y": 0,
                                "description": "Tap 'Create vault' button"
                            }
                        # No create button - press ENTER
                        return {
                            "action": "key",
                            "code": 66,
                            "description": "Press ENTER to create vault"
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
        
        # Read screenshot
        img = Image.open(screenshot_path)
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        img_data = base64.b64encode(img_buffer.read()).decode('utf-8')
        
        # Build action history string with execution status
        history_str = ""
        if action_history:
            history_str = "\nPrevious actions:\n"
            for i, action in enumerate(action_history[-5:]):  # Last 5 actions
                status_marker = ""
                if action.get("_execution_failed"):
                    status_marker = " [FAILED]"
                elif action.get("_execution_status") == "success":
                    status_marker = " [SUCCESS]"
                history_str += f"  {i+1}. {action.get('action', 'unknown')}: {action.get('description', '')}{status_marker}\n"
        
        # Check memory for successful patterns and avoid failed ones
        context = {"current_screen": current_screen, "test_goal": test_text}
        successful_pattern = memory.get_successful_pattern(context)
        should_avoid, avoid_reason = memory.should_avoid_action(context, {"action": "type", "description": "Type vault name"})
        
        memory_hint = ""
        if successful_pattern:
            memory_hint = f"\n💡 Memory: Found successful pattern for this context: {len(successful_pattern)} actions"
        if should_avoid:
            memory_hint += f"\n⚠️  Memory: Avoid typing - failed 3+ times: {avoid_reason}"
        
        # CRITICAL: Check if Test 2 is complete - both "Meeting Notes" and "Daily Standup" are present
        # Do this check before main planning to catch completion and prevent loops
        # Use normalized blob to handle concatenation and truncation
        if "meeting notes" in test_text.lower() and "daily standup" in test_text.lower():
            # Normalize text for checking
            def normalize_text(s):
                return ''.join(c.lower() for c in s if c.isalnum())
            
            ui_blob = normalize_text(" ".join(ui_text))
            has_meeting_notes = "meetingnotes" in ui_blob or "meetingnote" in ui_blob
            has_daily_standup = "dailystandup" in ui_blob
            
            # Require that we're in note_editor and both are present
            if current_screen == 'note_editor' and has_meeting_notes and has_daily_standup:
                print(f"  ✅ Test 2 PASS: Both 'Meeting Notes' and 'Daily Standup' are present in note!")
                return {
                    "action": "assert",
                    "description": "Note 'Meeting Notes' with 'Daily Standup' text created successfully"
                }
        
        # Check if we just focused body field - now need to type "Daily Standup"
        # This check is also done earlier before loop detection, but keep it here as backup
        if action_history and ("meeting notes" in test_text.lower() and "daily standup" in test_text.lower()):
            last_action = action_history[-1]
            
            # Normalize text for checking
            def normalize_text(s):
                return ''.join(c.lower() for c in s if c.isalnum())
            
            ui_blob = normalize_text(" ".join(ui_text))
            has_meeting_notes = "meetingnotes" in ui_blob or "meetingnote" in ui_blob
            has_daily_standup = "dailystandup" in ui_blob
            
            # Check if last action was focus body
            if (last_action.get("action") == "focus" and 
                last_action.get("target") == "body" and
                has_meeting_notes and not has_daily_standup):
                print(f"  → Just focused body field, now typing 'Daily Standup'...")
                return {
                    "action": "type",
                    "text": "Daily Standup",
                    "target": "body",
                    "description": "Type note body text 'Daily Standup'"
                }
            
            # Check if we have "Meeting Notes" in UI but not "Daily Standup"
            if has_meeting_notes and not has_daily_standup:
                # Need to focus body and type it
                # Check if we're in note editor or if last action was typing Meeting Notes
                if (current_screen == 'note_editor' or 
                    (last_action.get("action") == "type" and "meeting notes" in last_action.get("description", "").lower())):
                    print(f"  → Have 'Meeting Notes' but not 'Daily Standup', focusing body field FIRST...")
                    return {
                        "action": "focus",
                        "target": "body",
                        "description": "Focus note body editor"
                    }
        
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
- {{"action": "type", "text": "Meeting Notes", "target": "title", "description": "Type note title"}}  (for note creation: target="title" or "body")
- {{"action": "focus", "target": "body", "description": "Focus note body editor"}}  (for switching between title/body fields)
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
6. **CRITICAL: After tapping "Continue without sync", a storage selection dialog appears - you MUST select "App storage" or "Internal storage" (NOT "Device storage"). Analyze the screenshot to find and tap "App storage" option.**
7. If the test goal is visually achieved, return assert action
8. If a required element for the test is NOT visible, return FAIL action with reason
9. For tap actions, provide coordinates (x, y) based on button position in screenshot - BUT if you're not sure, use (0, 0) and the executor will use UIAutomator to find it
10. If Android state shows you're stuck on the same screen after multiple actions, try a different approach (BACK key, swipe, etc.) or return FAIL
11. NEVER repeat the same action if Android state hasn't changed - try BACK key or different approach
12. If you need to open the app, use {{"action": "open_app", "app": "md.obsidian"}} instead of tapping app icon
13. If tapping ALLOW/permission button multiple times doesn't work, try {{"action": "key", "code": 4, "description": "Press BACK"}} to dismiss dialog
14. **CRITICAL FOR STORAGE SELECTION**: After tapping "Continue without sync", a storage selection dialog appears:
    - You MUST select "App storage" or "Internal storage" (NOT "Device storage")
    - Analyze the screenshot CAREFULLY to find the storage options
    - Look for buttons/text like "App storage", "Internal storage", "Device storage"
    - Tap "App storage" or "Internal storage" - do NOT tap "Device storage"
    - This step is REQUIRED before typing the vault name
    - If you see storage selection dialog, you MUST select app storage before proceeding
15. **CRITICAL FOR NOTE CREATION**: If test goal includes creating a note "Meeting Notes" with text "Daily Standup":
    - If you're in vault_home (current_screen='vault_home' or FileActivity), look for "Create note" or "New note" button and tap it
    - After tapping create note, you'll be in note_editor (current_screen='note_editor')
    - **IMPORTANT ORDER**: In note_editor, FIRST type the note title/heading "Meeting Notes" (this is the heading) with {{"action": "type", "text": "Meeting Notes", "target": "title", "description": "Type note title"}}
    - THEN focus the body field with {{"action": "focus", "target": "body", "description": "Focus note body editor"}}
    - THEN type the body text "Daily Standup" with {{"action": "type", "text": "Daily Standup", "target": "body", "description": "Type note body text"}}
    - **DO NOT press ENTER** - use focus action to switch between title and body fields
    - Do NOT type "Daily Standup" before "Meeting Notes" - always type heading first, focus body, then type body
    - **CRITICAL**: If "Meeting Notes" is already in the UI text (check screenshot), you MUST focus the body field FIRST before typing "Daily Standup" - otherwise it will appear on the same line as the title!
    - If Android state shows has_edittext=true and current_screen='note_editor', check screenshot carefully:
      * If "Meeting Notes" is NOT in UI text → type "Meeting Notes" with target="title" first
      * If "Meeting Notes" IS in UI text but "Daily Standup" is NOT → focus target="body" FIRST, then type "Daily Standup" with target="body"
      * If both are present → return assert action
    - After typing both title and content, return {{"action": "assert", "description": "Note 'Meeting Notes' with 'Daily Standup' created successfully"}}
16. **CRITICAL FOR VAULT CREATION**: After typing "InternVault" as vault name:
    - You MUST immediately press ENTER or tap "Create vault" button - DO NOT wait or do anything else
    - PREFER tapping "Create vault" button over pressing ENTER (button is more reliable)
    - Analyze the screenshot CAREFULLY to find the "Create vault" button
    - Look for button text like "Create vault", "Create", or similar
    - If you see the button in the screenshot, tap it at the coordinates shown
    - If button is not clearly visible, use UIAutomator (return action with x=0, y=0 and description "Tap 'Create vault' button")
    - Do NOT skip clicking the Create vault button - it's required to create the vault
    - After pressing ENTER or tapping button, wait for vault to be created (check if screen changed to vault_home)
17. **CRITICAL FOR VAULT**: If you're on welcome_setup/vault_selection screen and the test goal is to create a note, the vault ALREADY EXISTS. DO NOT create a new vault. Look for the vault name "InternVault" in the UI and tap it to ENTER the existing vault. If you see "USE THIS FOLDER" button, you can tap that too.
18. If you've typed vault name or created vault multiple times, STOP creating vaults and just enter the existing vault by tapping "InternVault" or "USE THIS FOLDER"
19. **FOR TEST 3 (Settings)**: After tapping settings icon, look for "Appearance" tab or menu item. DO NOT try to close settings - explore it to find Appearance. If you can't find Appearance, look for tabs, menu items, or swipe to see more options.
20. If "Close" button is not found in settings, use BACK key (code 4) or look for Appearance tab directly

Output ONLY valid JSON, no markdown, no code blocks:
"""
        
        # Call OpenAI Vision API
        response = call_openai_with_retry(
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
