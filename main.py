"""
Main Orchestrator - Step-by-Step Visual Planning Loop
Action → Screenshot → LLM → Action → Screenshot → ...
"""
from tests.qa_tests import QA_TESTS
from agents.planner import plan_next_action
from agents.executor import execute_action
from agents.supervisor import verify, compare_with_expected
from tools.screenshot import ensure_screenshots_dir, take_screenshot
from tools.adb_tools import reset_app
from tools.memory import memory
from config import OPENAI_API_KEY, OBSIDIAN_PACKAGE
import time
import os


def run_test_suite():
    """
    Run all QA tests using step-by-step visual planning
    """
    print("=" * 60)
    print("Obsidian Mobile QA Agent - Visual Planning Test Suite")
    print("=" * 60)
    
    # Ensure screenshots directory exists
    ensure_screenshots_dir()
    
    # Check for API key
    if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_API_KEY_HERE":
        print("\n⚠️  WARNING: OPENAI_API_KEY not configured!")
        print("Please set it in config.py or as an environment variable")
        print("\nContinuing anyway...\n")
    else:
        print(f"✓ OpenAI API key configured\n")
    
    results = []
    previous_test_passed = False  # Track if previous test passed
    
    # Reset app only before first test (tests are sequential)
    print("🔄 Resetting app state before first test...")
    reset_app(OBSIDIAN_PACKAGE)
    print("✓ App reset complete\n")
    
    for test in QA_TESTS:
        print(f"\n{'=' * 60}")
        print(f"Running Test {test['id']}: {test['text']}")
        print(f"Expected Result: {'PASS' if test['should_pass'] else 'FAIL'}")
        print(f"{'=' * 60}\n")
        
        test_result = {
            "test_id": test["id"],
            "test_text": test["text"],
            "expected": "PASS" if test["should_pass"] else "FAIL"
        }
        
        try:
            # Take initial screenshot
            screenshot_path = take_screenshot(f"test_{test['id']}_initial.png")
            action_history = []
            max_steps = 20  # Prevent infinite loops
            step_count = 0
            
            print("🔄 Starting step-by-step visual planning loop...\n")
            
            while step_count < max_steps:
                step_count += 1
                print(f"--- Step {step_count} ---")
                
                # Planner: Analyze screenshot + Android state and decide next action
                print("📋 Planning next action from screenshot + Android state...")
                # Pass previous test result to planner (for Test 2 to know Test 1 passed)
                next_action = plan_next_action(test["text"], screenshot_path, action_history, previous_test_passed=previous_test_passed)
                
                # Log what we're about to do
                action_type = next_action.get("action", "unknown")
                description = next_action.get("description", "")
                print(f"   📱 Android state: {next_action.get('_android_state', {}).get('current_screen', 'unknown')}")
                
                if next_action.get("action") == "FAIL":
                    print(f"❌ Planner returned FAIL: {next_action.get('reason', 'Unknown reason')}")
                    test_result["status"] = "FAIL"
                    test_result["reason"] = next_action.get("reason", "Planner returned FAIL")
                    break
                
                if next_action.get("action") == "assert":
                    print("✓ Test goal visually confirmed by planner")
                    # Take final screenshot for supervisor
                    screenshot_path = take_screenshot(f"test_{test['id']}_final.png")
                    break
                
                # Executor: Execute the action
                print("🤖 Executing action...")
                execution_result = execute_action(next_action)
                
                if execution_result["status"] == "failed":
                    print(f"❌ Execution failed: {execution_result.get('error', execution_result.get('reason', 'Unknown error'))}")
                    # Record failure in memory for learning
                    context = {
                        "current_screen": next_action.get('_android_state', {}).get('current_screen', 'unknown'),
                        "test_goal": test["text"]
                    }
                    memory.record_failure(context, action_history + [next_action], execution_result.get('reason', 'Unknown error'))
                    memory.update_reward(next_action.get("action", "unknown"), -0.5)  # Negative reward
                    
                    # Don't break immediately - let planner try a different approach
                    # But mark the action as failed in history
                    next_action["_execution_failed"] = True
                    next_action["_execution_reason"] = execution_result.get('reason', 'Unknown error')
                
                # Update screenshot and action history
                screenshot_path = execution_result.get("screenshot", screenshot_path)
                # Store execution result in action for planner to see
                next_action["_execution_result"] = execution_result
                next_action["_execution_status"] = execution_result.get("status", "unknown")
                action_history.append(next_action)
                
                print(f"✓ Action executed, screenshot updated\n")
                time.sleep(0.5)  # Brief pause between steps
            
            if step_count >= max_steps:
                print(f"⚠️  Reached maximum steps ({max_steps}), taking final screenshot...")
                screenshot_path = take_screenshot(f"test_{test['id']}_final.png")
            
            # Supervisor: Verify final screenshot
            print("\n🧑‍⚖️ Verifying test result from final screenshot...")
            verification = verify(test["text"], screenshot_path, test["should_pass"])
            verdict = verification.get("verdict", "UNKNOWN")
            reason = verification.get("reason", "No reason provided")
            details = verification.get("details", "")
            
            print(f"Verdict: {verdict}")
            print(f"Reason: {reason}")
            if details:
                print(f"Details: {details}")
            
            # Compare with expected result
            comparison = compare_with_expected(verdict, test["should_pass"])
            print(f"\n{comparison['message']}")
            
            # Record outcome in memory for reinforcement learning
            context = {
                "current_screen": "test_complete",
                "test_goal": test["text"]
            }
            if verdict == "PASS" and test["should_pass"]:
                # Success! Record successful pattern
                memory.record_success(context, action_history, f"Test {test['id']} passed")
                # Positive rewards for successful actions
                for action in action_history:
                    memory.update_reward(action.get("action", "unknown"), 0.2)
                print(f"  💾 Recorded successful pattern in memory")
            elif verdict == "FAIL" and not test["should_pass"]:
                # Expected failure - still a success in terms of test design
                memory.record_success(context, action_history, f"Test {test['id']} correctly failed")
            else:
                # Unexpected result - record as failure
                memory.record_failure(context, action_history, f"Test {test['id']} unexpected result: {verdict}")
            
            test_result["status"] = verdict
            test_result["verdict"] = verdict
            test_result["reason"] = reason
            test_result["details"] = details
            test_result["comparison"] = comparison
            test_result["steps_taken"] = step_count
            test_result["final_screenshot"] = screenshot_path
            
        except Exception as e:
            print(f"\n❌ Test execution error: {str(e)}")
            test_result["status"] = "ERROR"
            test_result["error"] = str(e)
        
        results.append(test_result)
        
        # Update previous_test_passed for next test
        if test_result.get("status") == "PASS" and test["id"] == 1:
            previous_test_passed = True
            print(f"  ✓ Test 1 passed - Test 2 will assume we're in vault\n")
        
        time.sleep(1)  # Brief pause between tests
    
    # Print summary
    print(f"\n{'=' * 60}")
    print("TEST SUITE SUMMARY")
    print(f"{'=' * 60}\n")
    
    passed = sum(1 for r in results if r.get("status") == "PASS")
    failed = sum(1 for r in results if r.get("status") == "FAIL")
    errors = sum(1 for r in results if r.get("status") in ["ERROR", "EXECUTION_ERROR"])
    
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Errors: {errors}\n")
    
    for result in results:
        status_icon = "✓" if result.get("status") == "PASS" else "✗" if result.get("status") == "FAIL" else "⚠"
        print(f"{status_icon} Test {result['test_id']}: {result.get('status', 'UNKNOWN')} ({result.get('steps_taken', 0)} steps)")
        if result.get("reason"):
            print(f"   {result['reason']}")
    
    print(f"\n{'=' * 60}")
    
    return results


if __name__ == "__main__":
    run_test_suite()
