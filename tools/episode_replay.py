"""
Episode Replay System
Replays saved test episodes step-by-step for debugging
"""
import json
import os
import time
from typing import Dict, Any, Optional
from agents.executor import execute_action
from tools.screenshot import take_screenshot

class EpisodeReplayer:
    """Replays saved test episodes"""
    
    def __init__(self, interactive: bool = True, delay: float = 1.0):
        """
        Initialize replayer
        
        Args:
            interactive: If True, wait for user input between steps
            delay: Delay in seconds between steps (non-interactive mode)
        """
        self.interactive = interactive
        self.delay = delay
    
    def replay_episode(self, episode_path: str) -> bool:
        """
        Replay an episode from JSON file
        
        Args:
            episode_path: Path to episode JSON file
            
        Returns:
            True if replay successful
        """
        if not os.path.exists(episode_path):
            print(f"❌ Episode file not found: {episode_path}")
            return False
        
        with open(episode_path, 'r') as f:
            episode_data = json.load(f)
        
        print("=" * 60)
        print("EPISODE REPLAY")
        print("=" * 60)
        print(f"Task: {episode_data.get('test_id', 'Unknown')}")
        print(f"Test: {episode_data.get('test_text', 'Unknown')}")
        print(f"Status: {episode_data.get('status', 'Unknown')}")
        print(f"Steps: {episode_data.get('steps_taken', 0)}")
        print("=" * 60)
        print()
        
        # Get action history
        action_history = episode_data.get('action_history', [])
        
        if not action_history:
            print("⚠️  No action history found in episode")
            return False
        
        print(f"Replaying {len(action_history)} steps...")
        print()
        
        for i, action in enumerate(action_history, 1):
            print(f"--- Step {i}/{len(action_history)} ---")
            print(f"Action: {action.get('action', 'unknown')}")
            print(f"Description: {action.get('description', '')}")
            
            if self.interactive:
                user_input = input("\nPress Enter to execute, 'q' to quit, 's' to skip to non-interactive: ").strip()
                if user_input.lower() == 'q':
                    print("\nReplay cancelled by user")
                    return False
                elif user_input.lower() == 's':
                    print("Switching to non-interactive mode...")
                    self.interactive = False
            else:
                time.sleep(self.delay)
            
            # Execute action
            try:
                result = execute_action(action)
                print(f"✓ Action executed: {result.get('status', 'unknown')}")
                
                if result.get('screenshot'):
                    print(f"  Screenshot: {result['screenshot']}")
            except Exception as e:
                print(f"❌ Action execution failed: {e}")
            
            print()
        
        print("=" * 60)
        print("Replay completed!")
        print("=" * 60)
        return True


def replay_episode_file(episode_path: str, interactive: bool = True, delay: float = 1.0):
    """
    Convenience function to replay an episode file
    
    Args:
        episode_path: Path to episode JSON file
        interactive: If True, wait for user input between steps
        delay: Delay in seconds between steps (non-interactive mode)
    """
    replayer = EpisodeReplayer(interactive=interactive, delay=delay)
    replayer.replay_episode(episode_path)
