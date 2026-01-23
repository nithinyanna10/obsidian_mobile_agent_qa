#!/usr/bin/env python3
"""
Episode Replay Script
Replays saved test episodes for debugging
"""
import sys
import argparse
from tools.episode_replay import replay_episode_file

def main():
    parser = argparse.ArgumentParser(description="Replay a saved test episode")
    parser.add_argument("episode_file", help="Path to episode JSON file")
    parser.add_argument("--non-interactive", action="store_true", help="Run without user input")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between steps (non-interactive mode)")
    
    args = parser.parse_args()
    
    replay_episode_file(
        args.episode_file,
        interactive=not args.non_interactive,
        delay=args.delay
    )

if __name__ == "__main__":
    main()
