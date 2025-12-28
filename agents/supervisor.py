"""
Supervisor Agent - Visual Verification
Compares final screenshot with test expectation
PASS only if visual goal is met
"""
from PIL import Image
import os
import sys
import base64
import io
import json
import time

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.ollama_client import call_ollama_vision


def verify(test_text, screenshot_path, expected_result=None):
    """
    Verify if test passed or failed by comparing screenshot with test expectation
    
    Args:
        test_text: Original test case description
        screenshot_path: Path to final screenshot
        expected_result: Optional expected result (True = should pass, False = should fail)
    
    Returns:
        Dictionary with verification result
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

Output format (JSON):
{{
    "verdict": "PASS" or "FAIL",
    "reason": "Brief explanation based on what you see in the screenshot",
    "details": "More detailed analysis"
}}

Be specific about what you see in the screenshot.
"""
        
        # Call Ollama Vision API
        result_text = call_ollama_vision(
            prompt=prompt,
            image_base64=img_data,
            temperature=0.1
        )
        
        if not result_text:
            return {
                "verdict": "ERROR",
                "reason": "Empty response from model",
                "details": "No content in API response"
            }
        
        result_text = result_text.strip()
        
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
