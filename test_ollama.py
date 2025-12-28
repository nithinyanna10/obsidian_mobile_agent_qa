"""
Test Ollama connection and vision model
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.ollama_client import check_ollama_connection, call_ollama_vision
from config import OLLAMA_VISION_MODEL, OLLAMA_BASE_URL
from PIL import Image
import base64
import io

print("🧪 Testing Ollama Connection...")
print(f"Base URL: {OLLAMA_BASE_URL}")
print(f"Vision Model: {OLLAMA_VISION_MODEL}\n")

# Test 1: Check connection
print("1. Checking Ollama connection...")
if check_ollama_connection():
    print("   ✓ Ollama is running and accessible\n")
else:
    print("   ❌ Ollama is not running or not accessible")
    print(f"   Please start Ollama: ollama serve")
    print(f"   Or check if it's running at: {OLLAMA_BASE_URL}\n")
    sys.exit(1)

# Test 2: Create a simple test image
print("2. Creating test image...")
test_img = Image.new('RGB', (100, 100), color='red')
img_buffer = io.BytesIO()
test_img.save(img_buffer, format='PNG')
img_buffer.seek(0)
img_data = base64.b64encode(img_buffer.read()).decode('utf-8')
print("   ✓ Test image created\n")

# Test 3: Test vision model
print("3. Testing vision model...")
test_prompt = """Look at this image and describe what you see in one sentence. Return only the description, no JSON."""
try:
    print(f"   Calling {OLLAMA_VISION_MODEL}...")
    response = call_ollama_vision(
        prompt=test_prompt,
        image_base64=img_data,
        temperature=0.1
    )
    
    if response:
        print(f"   ✓ Model responded: {response[:100]}...\n")
        print("🎉 Ollama vision model is working correctly!")
    else:
        print("   ❌ Model returned empty response")
        print("   Check if the model is loaded: ollama list")
        print(f"   Pull the model if needed: ollama pull {OLLAMA_VISION_MODEL}\n")
        sys.exit(1)
        
except Exception as e:
    print(f"   ❌ Error: {str(e)}\n")
    print("   Troubleshooting:")
    print(f"   1. Check if model is available: ollama list")
    print(f"   2. Pull the model: ollama pull {OLLAMA_VISION_MODEL}")
    print(f"   3. Check Ollama logs for errors")
    sys.exit(1)

