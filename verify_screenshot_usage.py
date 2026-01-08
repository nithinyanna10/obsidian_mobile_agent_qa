"""
Verify Screenshot Usage - Check which screenshots are sent to LLM vs just taken
"""
import sqlite3
import os
from pathlib import Path

def analyze_screenshot_usage(db_path="benchmark.db", screenshots_dir="run"):
    """Analyze which screenshots were actually sent to LLM"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print("=" * 80)
    print("SCREENSHOT USAGE ANALYSIS")
    print("=" * 80)
    print()
    
    # Get all steps with screenshots
    steps = conn.execute("""
        SELECT run_id, step_idx, subgoal, action_type, before_png, after_png, ui_xml
        FROM steps
        WHERE before_png IS NOT NULL OR after_png IS NOT NULL
        ORDER BY run_id, step_idx
    """).fetchall()
    
    print(f"Found {len(steps)} steps with screenshots")
    print()
    
    # Count screenshots
    screenshots_taken = set()
    screenshots_in_api = set()
    
    for step in steps:
        if step["before_png"]:
            screenshots_taken.add(step["before_png"])
        if step["after_png"]:
            screenshots_taken.add(step["after_png"])
        
        # Screenshots are sent to API if they're in the step (before/after)
        # The actual API call includes the screenshot in image_url
        # We can't tell from the database which were sent, but we know:
        # - If a step has before_png/after_png, it might have been sent
        # - But only if that step triggered an API call
        
        # Check if this step had an API call (planner/supervisor calls)
        # We can't determine this from the database alone, but we can check:
        # - Steps with action_type that require vision (tap, type, etc.) likely sent screenshots
        if step["action_type"] in ["tap", "type", "focus", "swipe"]:
            if step["before_png"]:
                screenshots_in_api.add(step["before_png"])
            if step["after_png"]:
                screenshots_in_api.add(step["after_png"])
    
    # Count actual screenshot files
    screenshot_files = set()
    if os.path.exists(screenshots_dir):
        for file in Path(screenshots_dir).glob("*.png"):
            screenshot_files.add(file.name)
    
    print("SCREENSHOT STATISTICS:")
    print("-" * 80)
    print(f"Screenshots taken (from steps table): {len(screenshots_taken)}")
    print(f"Screenshots potentially sent to API: {len(screenshots_in_api)}")
    print(f"Screenshot files on disk: {len(screenshot_files)}")
    print()
    
    # Get API call counts
    runs = conn.execute("""
        SELECT run_id, test_id, api_calls, tokens_in, tokens_out
        FROM runs
        WHERE final_status IS NOT NULL
        ORDER BY run_id
    """).fetchall()
    
    print("API CALLS vs SCREENSHOTS:")
    print("-" * 80)
    for run in runs:
        # Estimate: each API call with vision typically includes 1 screenshot
        # But some calls might have multiple screenshots or no screenshots
        estimated_screenshots_sent = run["api_calls"]  # Rough estimate
        print(f"Run {run['run_id'][:8]}... | Test {run['test_id']}:")
        print(f"  API calls: {run['api_calls']}")
        print(f"  Estimated screenshots sent: ~{estimated_screenshots_sent}")
        print(f"  Tokens: {run['tokens_in']:,} in, {run['tokens_out']:,} out")
        print()
    
    print("IMPORTANT:")
    print("-" * 80)
    print("Token counts come from OpenAI API responses (response.usage)")
    print("So ONLY screenshots actually sent to the API are counted.")
    print("Screenshots taken but NOT sent = 0 tokens")
    print()
    print("To verify:")
    print("1. Check OpenAI dashboard for actual token usage")
    print("2. Compare with our calculated costs")
    print("3. They should match (our counts are from API responses)")
    
    conn.close()

if __name__ == "__main__":
    analyze_screenshot_usage()

