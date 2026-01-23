"""
Main Orchestrator - Step-by-Step Visual Planning Loop
Action → Screenshot → LLM → Action → Screenshot → ...
"""
from tests.qa_tests import QA_TESTS
from agents.planner import plan_next_action
from agents.executor import execute_action
from agents.supervisor import verify, compare_with_expected
from tools.screenshot import ensure_screenshots_dir, take_screenshot
from tools.adb_tools import reset_app, dump_ui
from tools.memory import memory
from tools.benchmark_logger import BenchmarkLogger
from tools.subgoal_detector import subgoal_detector
from config import OPENAI_API_KEY, OBSIDIAN_PACKAGE, OPENAI_MODEL, REASONING_MODEL, ENABLE_SUBGOAL_DETECTION, DISABLE_RL_FOR_BENCHMARKING
from datetime import datetime
import xml.etree.ElementTree as ET
import time
import os
import hashlib
import json


def run_test_suite(
    model: str = None,
    experiment_id: str = None,
    trial_num: int = 1,
    enable_logging: bool = True
):
    """
    Run all QA tests using step-by-step visual planning
    
    Args:
        model: Model identifier (e.g., "gpt-4o")
        experiment_id: Experiment identifier
        trial_num: Trial number
        enable_logging: Whether to enable benchmark logging
    """
    print("=" * 60)
    print("Obsidian Mobile QA Agent - Visual Planning Test Suite")
    print("=" * 60)
    
    # Initialize benchmark logger
    logger = None
    if enable_logging:
        # Use reasoning model if provided, otherwise default
        reasoning_model = model or REASONING_MODEL or OPENAI_MODEL
        vision_model = OPENAI_MODEL  # Always OpenAI for vision
        exp_id = experiment_id or f"bench_v1_{datetime.now().strftime('%Y_%m_%d')}"
        logger = BenchmarkLogger(experiment_id=exp_id)
        print(f"📊 Benchmark logging enabled: {exp_id}")
        print(f"   Vision Model: {vision_model} (OpenAI)")
        print(f"   Reasoning Model: {reasoning_model}")
        print(f"   Trial: {trial_num}")
        if DISABLE_RL_FOR_BENCHMARKING:
            print(f"   ⚠️  RL Patterns: DISABLED (fair benchmarking mode)")
        else:
            print(f"   💾 RL Patterns: ENABLED")
        print()
    
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
    
    config = {
        "max_steps": 20,
        "temperature": 0.1,
        "model": OPENAI_MODEL,
        "enable_logging": enable_logging
    }
    
    for test in QA_TESTS:
        print(f"\n{'=' * 60}")
        print(f"[TEST ID: {test['id']}] Running Test {test['id']}: {test['text']}")
        print(f"Expected Result: {'PASS' if test['should_pass'] else 'FAIL'}")
        print(f"{'=' * 60}\n")
        
        test_result = {
            "test_id": test["id"],
            "test_text": test["text"],
            "expected": "PASS" if test["should_pass"] else "FAIL"
        }
        
        # Start run logging
        run_id = None
        if logger:
            model_name = model or OPENAI_MODEL
            should = "PASS" if test["should_pass"] else "FAIL"
            run_id = logger.start_run(
                trial_num=trial_num,
                model=reasoning_model,  # Store reasoning model as the main model
                test_id=test["id"],
                should=should,
                config=config,
                reasoning_model=reasoning_model,
                vision_model=vision_model
            )
        
        try:
            # Initialize subgoal detection
            if ENABLE_SUBGOAL_DETECTION:
                subgoal_detector.detected_subgoals = []
                subgoal_detector.achieved_subgoals = []
                detected_subgoals = subgoal_detector.detect_subgoals(test["text"])
                if detected_subgoals:
                    print(f"  🎯 Detected {len(detected_subgoals)} subgoals:")
                    for sg in detected_subgoals:
                        print(f"     - {sg['description']}")
                    print()
            
            # Take initial screenshot
            screenshot_path = take_screenshot(f"test_{test['id']}_initial.png")
            before_screenshot = screenshot_path
            action_history = []
            max_steps = 20  # Prevent infinite loops
            step_count = 0
            failure_reason = None
            memory_actions_count = 0  # Track how many actions came from memory (RL)
            
            print("🔄 Starting step-by-step visual planning loop...\n")
            
            while step_count < max_steps:
                step_count += 1
                print(f"--- [TEST {test['id']}] Step {step_count} ---")
                
                # Planner: Analyze screenshot + Android state and decide next action
                print("📋 Planning next action from screenshot + Android state...")
                # Pass previous test result to planner (for Test 2 to know Test 1 passed)
                # Pass logger to planner for API call tracking
                next_action = plan_next_action(
                    test["text"], screenshot_path, action_history,
                    previous_test_passed=previous_test_passed, test_id=test["id"],
                    logger=logger
                )
                
                # Track if this action came from memory (RL)
                if next_action.get("_from_memory"):
                    memory_actions_count += 1
                
                # Log what we're about to do
                action_type = next_action.get("action", "unknown")
                description = next_action.get("description", "")
                subgoal = description
                print(f"   📱 Android state: {next_action.get('_android_state', {}).get('current_screen', 'unknown')}")
                
                if next_action.get("action") == "FAIL":
                    print(f"❌ Planner returned FAIL: {next_action.get('reason', 'Unknown reason')}")
                    failure_reason = next_action.get("reason", "Planner returned FAIL")
                    test_result["status"] = "FAIL"
                    test_result["reason"] = failure_reason
                    if logger:
                        logger.log_step(
                            subgoal=subgoal,
                            action=next_action,
                            action_source="PLANNER_FAIL",
                            before_screenshot=before_screenshot,
                            after_screenshot=screenshot_path,
                            intended_check=None,
                            intended_success=False,
                            error_type="PLANNER_FAIL"
                        )
                    break
                
                if next_action.get("action") == "assert":
                    print("✓ Test goal visually confirmed by planner")
                    # Take final screenshot for supervisor
                    screenshot_path = take_screenshot(f"test_{test['id']}_final.png")
                    if logger:
                        logger.log_step(
                            subgoal=subgoal,
                            action=next_action,
                            action_source="ASSERT",
                            before_screenshot=before_screenshot,
                            after_screenshot=screenshot_path,
                            intended_check="TEST_COMPLETE",
                            intended_success=True
                        )
                    break
                
                # Executor: Execute the action
                print("🤖 Executing action...")
                before_screenshot = screenshot_path
                execution_result = execute_action(next_action, logger=logger)
                
                # Get action source and intended success from execution result
                action_source = execution_result.get("action_source", "FALLBACK_COORDS")
                intended_success = execution_result.get("intended_success", False)
                intended_check = execution_result.get("intended_check")
                
                if execution_result["status"] == "failed":
                    print(f"❌ Execution failed: {execution_result.get('error', execution_result.get('reason', 'Unknown error'))}")
                    failure_reason = execution_result.get('reason', 'Unknown error')
                    error_type = execution_result.get("error_type", "EXECUTION_FAILED")
                    
                    # Record failure in memory for learning
                    context = {
                        "current_screen": next_action.get('_android_state', {}).get('current_screen', 'unknown'),
                        "test_goal": test["text"]
                    }
                    memory.record_failure(context, action_history + [next_action], failure_reason)
                    memory.update_reward(next_action.get("action", "unknown"), -0.5)  # Negative reward
                    
                    # Don't break immediately - let planner try a different approach
                    # But mark the action as failed in history
                    next_action["_execution_failed"] = True
                    next_action["_execution_reason"] = failure_reason
                    
                    # Log failed step
                    if logger:
                        ui_xml_path = None
                        try:
                            root = dump_ui()
                            if root:
                                xml_str = ET.tostring(root, encoding='unicode')
                                ui_xml_path = f"xml_dumps/step_{step_count}_ui.xml"
                                os.makedirs("xml_dumps", exist_ok=True)
                                with open(ui_xml_path, 'w', encoding='utf-8') as f:
                                    f.write(xml_str)
                        except:
                            pass
                        
                        logger.log_step(
                            subgoal=subgoal,
                            action=next_action,
                            action_source=action_source,
                            before_screenshot=before_screenshot,
                            after_screenshot=screenshot_path,
                            ui_xml=ui_xml_path,
                            intended_check=intended_check,
                            intended_success=False,
                            error_type=error_type
                        )
                else:
                    # Log successful step
                    if logger:
                        ui_xml_path = None
                        try:
                            root = dump_ui()
                            if root:
                                xml_str = ET.tostring(root, encoding='unicode')
                                ui_xml_path = f"xml_dumps/step_{step_count}_ui.xml"
                                os.makedirs("xml_dumps", exist_ok=True)
                                with open(ui_xml_path, 'w', encoding='utf-8') as f:
                                    f.write(xml_str)
                        except:
                            pass
                        
                        logger.log_step(
                            subgoal=subgoal,
                            action=next_action,
                            action_source=action_source,
                            before_screenshot=before_screenshot,
                            after_screenshot=execution_result.get("screenshot", screenshot_path),
                            ui_xml=ui_xml_path,
                            intended_check=intended_check,
                            intended_success=intended_success
                        )
                
                # Update screenshot and action history
                screenshot_path = execution_result.get("screenshot", screenshot_path)
                # Store execution result in action for planner to see
                next_action["_execution_result"] = execution_result
                next_action["_execution_status"] = execution_result.get("status", "unknown")
                action_history.append(next_action)
                
                # Check subgoal achievement
                if ENABLE_SUBGOAL_DETECTION and execution_result.get("status") == "executed":
                    android_state = next_action.get("_android_state", {})
                    for subgoal in subgoal_detector.detected_subgoals:
                        if not subgoal.get("achieved", False):
                            achieved = subgoal_detector.check_subgoal_achievement(subgoal["type"], android_state)
                            if achieved:
                                print(f"  🎯 Subgoal achieved: {subgoal['description']}")
                
                print(f"✓ Action executed, screenshot updated\n")
                time.sleep(0.5)  # Brief pause between steps
            
            if step_count >= max_steps:
                print(f"⚠️  Reached maximum steps ({max_steps}), taking final screenshot...")
                screenshot_path = take_screenshot(f"test_{test['id']}_final.png")
                failure_reason = "MAX_STEPS_REACHED"
            
            # Supervisor: Verify final screenshot
            print("\n🧑‍⚖️ Verifying test result from final screenshot...")
            verification = verify(test["text"], screenshot_path, test["should_pass"], logger=logger)
            verdict = verification.get("verdict", "UNKNOWN")
            reason = verification.get("reason", "No reason provided")
            details = verification.get("details", "")
            assertions = verification.get("assertions", [])
            
            print(f"Verdict: {verdict}")
            print(f"Reason: {reason}")
            if details:
                print(f"Details: {details}")
            
            # Log assertions
            if logger and assertions:
                for assertion in assertions:
                    logger.log_assertion(
                        assertion_type=assertion.get("type", "unknown"),
                        expected=assertion.get("expected", ""),
                        observed=assertion.get("observed", ""),
                        passed=assertion.get("passed", False),
                        step_idx=None,  # Final assertion
                        evidence_path=assertion.get("evidence_path")
                    )
            
            # Compare with expected result
            comparison = compare_with_expected(verdict, test["should_pass"])
            print(f"\n[TEST ID: {test['id']}] {comparison['message']}")
            
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
            
            # Add subgoal information
            if ENABLE_SUBGOAL_DETECTION:
                progress = subgoal_detector.get_progress()
                test_result["subgoals"] = {
                    "total": progress["total_subgoals"],
                    "achieved": progress["achieved_subgoals"],
                    "completion_rate": progress["completion_rate"],
                    "detected": subgoal_detector.detected_subgoals,
                    "achieved_list": subgoal_detector.achieved_subgoals
                }
            
            # End run logging
            if logger:
                final_status = "PASS" if verdict == "PASS" else "FAIL"
                logger.end_run(
                    final_status=final_status,
                    failure_reason=failure_reason or (reason if verdict == "FAIL" else None)
                )
            
            # Display API usage summary after each test
            print(f"\n{'=' * 60}")
            print(f"📊 TEST {test['id']} USAGE SUMMARY")
            print(f"{'=' * 60}")
            
            if logger:
                api_calls = logger.api_calls
                api_actions = step_count - memory_actions_count  # Steps that used API
                
                if memory_actions_count > 0:
                    print(f"💾 RL Usage: {memory_actions_count} action(s) from memory patterns (no API calls)")
                    print(f"🔌 API Calls: {api_calls} call(s) made")
                    print(f"📈 Total Steps: {step_count} ({memory_actions_count} RL + {api_actions} API)")
                    if api_calls == 0:
                        print(f"✅ Result: 100% RL usage - No API calls needed!")
                    else:
                        rl_percentage = (memory_actions_count / step_count) * 100
                        print(f"✅ Result: {rl_percentage:.0f}% RL usage, {api_calls} API call(s)")
                else:
                    print(f"🔌 API Calls: {api_calls} call(s) made")
                    print(f"📈 Total Steps: {step_count} (all used API)")
                    print(f"💡 No RL patterns available - all actions used OpenAI API")
                
                if logger.cost_usd > 0:
                    print(f"💰 Estimated Cost: ${logger.cost_usd:.6f}")
                else:
                    print(f"💰 Estimated Cost: $0.00 (all from RL memory)")
            else:
                print(f"📈 Total Steps: {step_count}")
                if memory_actions_count > 0:
                    print(f"💾 RL Usage: {memory_actions_count} action(s) from memory")
            
            print(f"{'=' * 60}\n")
            
        except Exception as e:
            print(f"\n❌ Test execution error: {str(e)}")
            test_result["status"] = "ERROR"
            test_result["error"] = str(e)
            
            # End run logging with error
            if logger:
                logger.set_crash_detected()
                logger.end_run(
                    final_status="FAIL",
                    failure_reason=f"EXCEPTION: {str(e)}"
                )
        
        results.append(test_result)
        
        # Save episode JSON file for replay and batch analysis
        try:
            os.makedirs("results", exist_ok=True)
            episode_filename = f"test_{test['id']}_{test_result.get('status', 'UNKNOWN').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            episode_path = os.path.join("results", episode_filename)
            
            # Create episode data with action history for replay
            episode_data = {
                "test_id": test["id"],
                "test_text": test["text"],
                "expected": "PASS" if test["should_pass"] else "FAIL",
                "status": test_result.get("status", "UNKNOWN"),
                "verdict": test_result.get("verdict", "UNKNOWN"),
                "reason": test_result.get("reason", ""),
                "details": test_result.get("details", ""),
                "steps_taken": test_result.get("steps_taken", 0),
                "action_history": action_history,  # Full action history for replay
                "final_screenshot": test_result.get("final_screenshot", ""),
                "model": reasoning_model,
                "vision_model": vision_model,
                "timestamp": datetime.now().isoformat(),
                "subgoals": test_result.get("subgoals", {})
            }
            
            with open(episode_path, 'w') as f:
                json.dump(episode_data, f, indent=2)
            
            print(f"  💾 Episode saved: {episode_filename}")
        except Exception as e:
            print(f"  ⚠️  Failed to save episode: {e}")
        
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
        print(f"{status_icon} [TEST ID: {result['test_id']}] Test {result['test_id']}: {result.get('status', 'UNKNOWN')} ({result.get('steps_taken', 0)} steps)")
        if result.get("reason"):
            print(f"   {result['reason']}")
    
    print(f"\n{'=' * 60}")
    
    return results


if __name__ == "__main__":
    run_test_suite()
