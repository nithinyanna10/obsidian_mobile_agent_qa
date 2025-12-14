#!/bin/bash

# Setup script for Obsidian Mobile QA Agent

echo "🔧 Setting up Obsidian Mobile QA Agent..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "✓ Python found: $(python3 --version)"

# Check ADB
if ! command -v adb &> /dev/null; then
    echo "⚠️  ADB not found. Please install Android Platform Tools."
    echo "   macOS: brew install android-platform-tools"
    echo "   Or download from: https://developer.android.com/studio/releases/platform-tools"
else
    echo "✓ ADB found: $(adb version | head -n 1)"
fi

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Check for API key
echo ""
if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  GEMINI_API_KEY environment variable not set."
    echo "   Get your API key from: https://aistudio.google.com/app/apikey"
    echo "   Then run: export GEMINI_API_KEY='your-api-key-here'"
else
    echo "✓ GEMINI_API_KEY is set"
fi

# Check ADB connection
echo ""
echo "📱 Checking ADB connection..."
if adb devices | grep -q "device$"; then
    echo "✓ Android device connected"
    DEVICE=$(adb devices | grep "device$" | head -n 1 | cut -f1)
    echo "   Device ID: $DEVICE"
else
    echo "⚠️  No Android device found. Please:"
    echo "   1. Connect your Android device via USB"
    echo "   2. Enable USB debugging"
    echo "   3. Or start an Android emulator"
fi

# Check Obsidian installation
echo ""
echo "📱 Checking Obsidian installation..."
if adb shell pm list packages | grep -q "md.obsidian"; then
    echo "✓ Obsidian app found"
else
    echo "⚠️  Obsidian app not found. Please install Obsidian on your device."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run tests:"
echo "  python3 main.py"
echo ""

