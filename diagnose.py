#!/usr/bin/env python3
"""
Diagnostic script to check why the Obsidian agent stopped
"""
import sys
import subprocess

def check_python_version():
    """Check Python version"""
    print(f"Python version: {sys.version}")
    return True

def check_imports():
    """Check if required packages are installed"""
    print("\n" + "=" * 60)
    print("Checking Python Dependencies...")
    print("=" * 60)
    
    required_packages = [
        'openai',
        'PIL',  # pillow
        'cv2',  # opencv-python
        'numpy',
        'requests',
    ]
    
    missing = []
    for package in required_packages:
        try:
            if package == 'PIL':
                __import__('PIL')
            elif package == 'cv2':
                __import__('cv2')
            else:
                __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("   Install with: pip3 install -r requirements.txt")
        return False
    else:
        print("\n✓ All required packages installed")
        return True

def check_adb():
    """Check ADB connection"""
    print("\n" + "=" * 60)
    print("Checking ADB Connection...")
    print("=" * 60)
    
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
        devices = [line for line in result.stdout.split('\n') if 'device' in line and 'List' not in line]
        if devices:
            print(f"✓ ADB connected: {len(devices)} device(s)")
            for device in devices:
                print(f"  - {device}")
            return True
        else:
            print("✗ No ADB devices connected")
            return False
    except FileNotFoundError:
        print("✗ ADB not found in PATH")
        return False
    except Exception as e:
        print(f"✗ ADB error: {e}")
        return False

def check_config():
    """Check configuration"""
    print("\n" + "=" * 60)
    print("Checking Configuration...")
    print("=" * 60)
    
    try:
        from config import OPENAI_API_KEY, OBSIDIAN_PACKAGE
        if OPENAI_API_KEY and OPENAI_API_KEY != "":
            print(f"✓ OPENAI_API_KEY: {'*' * 20}...{OPENAI_API_KEY[-4:]}")
        else:
            print("✗ OPENAI_API_KEY not set")
        print(f"✓ OBSIDIAN_PACKAGE: {OBSIDIAN_PACKAGE}")
        return True
    except Exception as e:
        print(f"✗ Config error: {e}")
        return False

def main():
    print("=" * 60)
    print("Obsidian Mobile QA Agent - Diagnostic Check")
    print("=" * 60)
    
    results = {
        "Python": check_python_version(),
        "Dependencies": check_imports(),
        "ADB": check_adb(),
        "Config": check_config(),
    }
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_ok = all(results.values())
    for name, status in results.items():
        status_icon = "✓" if status else "✗"
        print(f"{status_icon} {name}")
    
    if all_ok:
        print("\n✓ All checks passed! The agent should work.")
    else:
        print("\n✗ Some checks failed. Fix the issues above.")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
