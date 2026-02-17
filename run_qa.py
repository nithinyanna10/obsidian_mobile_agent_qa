#!/usr/bin/env python3
"""
Run script for Obsidian Mobile QA Agent
Checks prerequisites and runs the test suite
"""
import subprocess
import sys
import os
import argparse
from main import run_test_suite

def check_adb():
    """Check if ADB is installed and device is connected"""
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
        devices = [line for line in result.stdout.split('\n') if line.strip() and 'device' in line]
        if len(devices) == 0:
            print("❌ No Android device connected!")
            print("   Please connect a device or start an emulator")
            return False
        print(f"✓ ADB found, {len(devices)} device(s) connected")
        return True
    except FileNotFoundError:
        print("❌ ADB not found!")
        print("   Install ADB: brew install android-platform-tools (macOS)")
        return False
    except Exception as e:
        print(f"❌ Error checking ADB: {e}")
        return False

def check_obsidian():
    """Check if Obsidian app is installed"""
    try:
        result = subprocess.run(
            ['adb', 'shell', 'pm', 'list', 'packages', '|', 'grep', 'obsidian'],
            capture_output=True, text=True, timeout=5, shell=True
        )
        if 'md.obsidian' in result.stdout:
            print("✓ Obsidian app found")
            return True
        else:
            # Try alternative method
            result = subprocess.run(
                ['adb', 'shell', 'pm', 'list', 'packages'],
                capture_output=True, text=True, timeout=5
            )
            if 'md.obsidian' in result.stdout:
                print("✓ Obsidian app found")
                return True
            else:
                print("❌ Obsidian app not found!")
                print("   Please install Obsidian mobile app")
                return False
    except Exception as e:
        print(f"⚠️  Could not verify Obsidian installation: {e}")
        print("   Continuing anyway...")
        return True  # Continue anyway

def check_api_key():
    """Check if OpenAI API key is configured"""
    from config import OPENAI_API_KEY
    if not OPENAI_API_KEY or OPENAI_API_KEY == "":
        print("⚠️  OPENAI_API_KEY not set!")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        print("   Or edit config.py")
        return False
    print("✓ OpenAI API key configured")
    return True

def main():
    """Main run function"""
    parser = argparse.ArgumentParser(description='Run Obsidian Mobile QA Agent')
    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='Model to use: "gpt-4o", "gpt-4o-mini", or None (default from config)'
    )
    parser.add_argument(
        '--experiment-id',
        type=str,
        default=None,
        help='Experiment ID for logging (auto-generated if not provided)'
    )
    parser.add_argument(
        '--trial',
        type=int,
        default=1,
        help='Trial number (default: 1)'
    )
    parser.add_argument(
        '--no-logging',
        action='store_true',
        help='Disable benchmark logging'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Obsidian Mobile QA Agent - Pre-flight Checks")
    print("=" * 60)
    print()
    
    # Check prerequisites
    checks = [
        ("ADB", check_adb),
        ("Obsidian App", check_obsidian),
        ("API Key", check_api_key),
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"Checking {name}...", end=" ")
        if not check_func():
            all_passed = False
        print()
    
    if not all_passed:
        print("⚠️  Some checks failed, but continuing anyway...")
        print()
    
    print("=" * 60)
    print("Starting QA Test Suite")
    if args.model:
        print(f"Model: {args.model}")
    print("=" * 60)
    print()
    
    # Run the test suite
    try:
        results = run_test_suite(
            model=args.model,  # Can be OpenAI model or None for default
            experiment_id=args.experiment_id,  # Auto-generated if None
            trial_num=args.trial,
            enable_logging=not args.no_logging
        )
        
        print("\n" + "=" * 60)
        print("Test Suite Completed!")
        print("=" * 60)
        
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  Test suite interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Error running test suite: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
