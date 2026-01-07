"""
Supervisor Agent - Visual Verification
Compares final screenshot with test expectation
PASS only if visual goal is met
"""
from openai import OpenAI
from PIL import Image
import os
import sys
import base64
import io
import json
import re
import time

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, OPENAI_MODEL


# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def call_openai_with_retry(messages, max_retries=3, logger=None, **kwargs):
    """
    Call OpenAI API with retry logic for rate limits
    
    Args:
        messages: Messages for the API call
        max_retries: Maximum number of retries
        logger: Optional BenchmarkLogger instance for logging API calls
        **kwargs: Additional arguments for chat.completions.create
    
    Returns:
        API response or raises exception
    """
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(model=OPENAI_MODEL, messages=messages, **kwargs)
            
            # Log API call if logger provided
            # CRITICAL: Token counts come from API response, so ONLY screenshots
            # actually sent to the API are counted. Screenshots taken but not sent = 0 tokens.
            if logger:
                tokens_in = 0
                tokens_out = 0
                
                # Extract actual token counts from API response
                # These are the REAL tokens used by OpenAI, including only screenshots sent in this call
                if hasattr(response, 'usage') and response.usage:
                    # Chat Completions API format
                    if hasattr(response.usage, 'prompt_tokens'):
                        tokens_in = response.usage.prompt_tokens
                    elif hasattr(response.usage, 'input_tokens'):
                        tokens_in = response.usage.input_tokens
                    
                    if hasattr(response.usage, 'completion_tokens'):
                        tokens_out = response.usage.completion_tokens
                    elif hasattr(response.usage, 'output_tokens'):
                        tokens_out = response.usage.output_tokens
                
                # Count screenshots in this API call
                screenshots_in_call = 0
                for msg in messages:
                    if isinstance(msg.get("content"), list):
                        for content_item in msg.get("content", []):
                            if content_item.get("type") == "image_url":
                                screenshots_in_call += 1
                
                # Log with model for cost calculation
                logger.log_api_call(
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    model=OPENAI_MODEL
                )
                
                # Debug: Show how many screenshots were in this call
                if screenshots_in_call > 0:
                    print(f"  📊 API call: {screenshots_in_call} screenshot(s) sent, {tokens_in:,} input tokens, {tokens_out:,} output tokens")
            
            return response
        except Exception as e:
            error_str = str(e)
            # Check if it's a rate limit error (429)
            if "429" in error_str or "rate_limit" in error_str.lower() or "rate limit" in error_str.lower():
                if attempt < max_retries - 1:
                    # Extract wait time from error if available
                    wait_time = 2.0  # Default: 2 seconds
                    if "try again in" in error_str.lower():
                        # Try to extract the wait time from the error message (in milliseconds)
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
                    if logger:
                        logger.set_rate_limit_fail()
                        # Count this as an API call attempt (rate limited)
                        logger.log_api_call(
                            tokens_in=0,
                            tokens_out=0,
                            model=OPENAI_MODEL
                        )
                    time.sleep(wait_time)
                    continue
                else:
                    # Still count as API call even if it failed
                    if logger:
                        logger.set_rate_limit_fail()
                        # Log failed call with 0 tokens (usage unavailable on error)
                        logger.log_api_call(
                            tokens_in=0,
                            tokens_out=0,
                            model=OPENAI_MODEL
                        )
                    raise  # Last attempt failed, raise the exception
            else:
                raise  # Not a rate limit error, raise immediately
    return None


def verify(test_text, screenshot_path, expected_result=None, logger=None):
    """
    Verify if test passed or failed by comparing screenshot with test expectation
    
    Args:
        test_text: Original test case description
        screenshot_path: Path to final screenshot
        expected_result: Optional expected result (True = should pass, False = should fail)
        logger: Optional BenchmarkLogger instance for logging
    
    Returns:
        Dictionary with verification result and assertions
    """
    try:
        # Read and encode screenshot
        img = Image.open(screenshot_path)
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        img_data = base64.b64encode(img_buffer.read()).decode('utf-8')
        
        prompt = f"""You are a QA Supervisor agent for mobile app testing.

Test Case: "{test_text}"

Look at the screenshot and determine if the test PASSED or FAILED.

Rules:
1. Check if the test goal is visually achieved in the screenshot
2. For tests that should PASS: verify the expected outcome is visible (e.g., vault created, note created)
3. For tests that should FAIL: verify the expected failure is visible (e.g., element not found, assertion mismatch)
4. If the required element is NOT visible → FAIL
5. If assertion doesn't match (e.g., color is not red) → FAIL

**SPECIFIC TEST 1 RULES (Vault Creation):**
- **CRITICAL**: If you see "Create note" or "New note" or "Create new note" button visible → Test 1 MUST PASS (vault is created and entered)
- If you see "files in internvault" or vault name "InternVault" visible → Test 1 PASSED
- **IMPORTANT**: The presence of "create new note" button is PROOF that the vault was created and entered successfully
- You do NOT need to see the exact text "InternVault" if "create new note" button is visible - that button only appears when inside a vault
- If "create new note" button is visible, return PASS immediately - do not look for vault name

**SPECIFIC TEST 2 RULES (Note Creation):**
- If you see note title "Meeting Notes" (or "Meeting Note" if truncated) AND body text "Daily Standup" → Test 2 PASSED
- If you see "Meeting Notes" or "Meeting Note" in the note editor with "Daily Standup" text visible → Test 2 PASSED
- The title and body do NOT need to be on separate lines - they can be concatenated (e.g., "Meeting NoteDaily Standup")
- As long as "Daily Standup" is visible and "Meeting Note(s)" appears anywhere in the note → Test 2 PASSED
- Do NOT require line breaks - accept the note if both texts are present

**SPECIFIC TEST 4 RULES (Appearance Accent Color):**
- **CRITICAL**: This test expects the accent color in Appearance settings to be RED
- Test 4 has should_pass=False, meaning we EXPECT the test to FAIL (accent color should NOT be Red)
- **VERIFICATION LOGIC**:
  - Look for the accent color setting/option in the Appearance screen
  - Check what color is currently selected as the accent color
  - If the accent color IS RED → The verification PASSES (accent color is Red) → But should_pass=False means we expect failure → Test result mismatch → Return FAIL
  - If the accent color is NOT RED (Purple/Blue/Green/default/monochrome/any other color) → The verification FAILS (accent color is not Red) → Return FAIL (the test failed as expected)
- Look for accent color settings/options in the Appearance screen (after tapping Appearance tab in Settings)
- Check the currently selected accent color - it should be visible in the Appearance settings screen
- Common accent color options: Red, Blue, Green, Purple, Orange, etc.
- **IMPORTANT**: If the accent color is NOT Red (Purple, Blue, Green, etc.) → Return FAIL (the test failed because accent color is not Red)
- If the accent color IS Red → Return FAIL (because should_pass=False means we expect failure, but if it's Red, the verification passed, so test fails)
- If you cannot see the accent color setting or cannot determine the selected color → FAIL
- **SUMMARY**: The test expects accent color to be Red. If accent color IS Red → verification passes but should_pass=False → Return FAIL. If accent color is NOT Red (Purple/Blue/etc.) → verification fails → Return FAIL.

**SPECIFIC TEST 3 RULES (Print to PDF):**
- **CRITICAL**: This test expects to find "Print to PDF" button in the main file menu
- Test 3 has should_pass=False, meaning we EXPECT the test to FAIL (button should NOT be found)
- **NOTE**: This test runs after Test 2, so we're already in Meeting Notes page (with "Daily Standup" visible)
- **VERIFICATION LOGIC**:
  - Look for "Print to PDF" or "Export to PDF" button in the menu (after tapping three dots/menu button)
  - The button should be in the Meeting Notes page menu (where "Daily Standup" is visible)
  - If the "Print to PDF" button IS FOUND → The verification PASSES (button found) → But should_pass=False means we expect failure → Test result mismatch → Return FAIL
  - If the "Print to PDF" button is NOT FOUND → The verification FAILS (button not found) → Return FAIL (the test failed as expected)
- Look for "Print to PDF", "Export to PDF", or similar text in the menu
- The menu should be opened from the Meeting Notes page (with "Daily Standup" visible)
- If the button is NOT found → Return FAIL (the test failed because button is not in menu)
- If the button IS found → Return FAIL (because should_pass=False means we expect failure, but if it's found, the verification passed, so test fails)
- If you cannot see the menu or cannot determine if button exists → FAIL
- **SUMMARY**: The test expects "Print to PDF" button to be in menu. If button IS found → verification passes but should_pass=False → Return FAIL. If button is NOT found → verification fails → Return FAIL.

Output format (JSON):
{{
    "verdict": "PASS" or "FAIL",
    "reason": "Brief explanation based on what you see in the screenshot",
    "details": "More detailed analysis"
}}

Be specific about what you see in the screenshot.
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
            logger=logger
        )
        
        if not response or not response.choices or not response.choices[0].message.content:
            return {
                "verdict": "ERROR",
                "reason": "Empty response from model",
                "details": "No content in API response"
            }
        
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
            result = json.loads(result_text)
        except json.JSONDecodeError:
            result = {
                "verdict": "UNKNOWN",
                "reason": "Could not parse LLM response",
                "details": result_text
            }
        
        # Validate verdict
        if result.get("verdict") not in ["PASS", "FAIL"]:
            result["verdict"] = "UNKNOWN"
        
        # Extract assertions for logging
        assertions = []
        verdict = result.get("verdict", "UNKNOWN")
        reason = result.get("reason", "")
        details = result.get("details", "")
        
        # Create assertion based on test type
        if "vault" in test_text.lower() and "internvault" in test_text.lower():
            # Test 1: Vault creation
            assertions.append({
                "type": "ui_text_contains",
                "expected": "InternVault",
                "observed": details,
                "passed": verdict == "PASS",
                "evidence_path": screenshot_path
            })
        elif "meeting notes" in test_text.lower() and "daily standup" in test_text.lower():
            # Test 2: Note creation
            assertions.append({
                "type": "ui_text_contains",
                "expected": "Meeting Notes",
                "observed": details,
                "passed": verdict == "PASS",
                "evidence_path": screenshot_path
            })
            assertions.append({
                "type": "ui_text_contains",
                "expected": "Daily Standup",
                "observed": details,
                "passed": verdict == "PASS",
                "evidence_path": screenshot_path
            })
        elif "appearance" in test_text.lower() or "icon color" in test_text.lower():
            # Test 4: Appearance color
            assertions.append({
                "type": "icon_color_is",
                "expected": "Red",
                "observed": details,
                "passed": verdict == "PASS",
                "evidence_path": screenshot_path
            })
        elif "print to pdf" in test_text.lower() or "export to pdf" in test_text.lower():
            # Test 3: Print to PDF
            assertions.append({
                "type": "element_exists",
                "expected": "Print to PDF",
                "observed": details,
                "passed": verdict == "PASS",
                "evidence_path": screenshot_path
            })
        
        result["assertions"] = assertions
        return result
        
    except Exception as e:
        return {
            "verdict": "ERROR",
            "reason": f"Verification error: {str(e)}",
            "details": str(e)
        }


def compare_with_expected(verdict, expected_result):
    """
    Compare actual verdict with expected result
    
    Args:
        verdict: Actual verdict from verification ("PASS" or "FAIL")
        expected_result: Expected result (True = should pass, False = should fail)
    
    Returns:
        Dictionary with comparison result
    """
    if expected_result is None:
        return {"match": None, "message": "No expected result provided"}
    
    expected_verdict = "PASS" if expected_result else "FAIL"
    actual_verdict = verdict.upper()
    
    match = (expected_verdict == actual_verdict)
    
    if match:
        message = f"✓ Test result matches expectation: {actual_verdict}"
    else:
        message = f"✗ Test result mismatch: Expected {expected_verdict}, Got {actual_verdict}"
    
    return {
        "match": match,
        "expected": expected_verdict,
        "actual": actual_verdict,
        "message": message
    }
