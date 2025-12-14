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
    # Ensure screenshots directory exists
    screenshot_dir = Path("screenshots")
    screenshot_dir.mkdir(exist_ok=True)
    
    # Full path to save screenshot
    output_path = screenshot_dir / name
    
    # Take screenshot using ADB
    with open(output_path, "wb") as f:
        subprocess.run(
            ["adb", "exec-out", "screencap", "-p"],
            stdout=f,
            check=True
        )
    
    return str(output_path)


def ensure_screenshots_dir():
    """Ensure the screenshots directory exists"""
    Path("screenshots").mkdir(exist_ok=True)

