"""
Screenshot Tools for Android Device
Captures screenshots from connected Android device via ADB
"""
import subprocess
import os
from pathlib import Path


def take_screenshot(name):
    """
    Take a screenshot from the connected Android device
    
    Args:
        name: Output filename (will be saved in screenshots/ directory)
    
    Returns:
        Path to the saved screenshot
    """
    import time
    # Ensure screenshots directory exists
    screenshot_dir = Path("screenshots")
    screenshot_dir.mkdir(exist_ok=True)
    
    # Full path to save screenshot
    output_path = screenshot_dir / name
    
    # Take screenshot using ADB with retry
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with open(output_path, "wb") as f:
                result = subprocess.run(
                    ["adb", "exec-out", "screencap", "-p"],
                    stdout=f,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=10
                )
            # Verify screenshot was created and has content
            if output_path.exists() and output_path.stat().st_size > 0:
                return str(output_path)
            else:
                raise Exception("Screenshot file is empty")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, Exception) as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            else:
                # Last attempt failed - check if device is connected
                check_result = subprocess.run(
                    ["adb", "devices"],
                    capture_output=True,
                    text=True
                )
                raise Exception(f"Failed to take screenshot after {max_retries} attempts: {e}. ADB devices: {check_result.stdout}")
    
    return str(output_path)


def ensure_screenshots_dir():
    """Ensure the screenshots directory exists"""
    Path("screenshots").mkdir(exist_ok=True)

