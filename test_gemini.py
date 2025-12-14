"""
Minimal working Gemini test (VERIFY BEFORE RUNNING AGENTS)
This verifies your API key and model access work correctly.

CORRECT API PATTERN:
- Use: import google.generativeai as genai
- NOT: from google import genai (this is incorrect)
"""
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL

print("🧪 Testing Gemini API...")
print(f"Model: {GEMINI_MODEL}")
print(f"API Key: {GEMINI_API_KEY[:20]}...\n")

try:
    # Correct pattern: configure then create GenerativeModel
    genai.configure(api_key=GEMINI_API_KEY)
    
    print(f"🔧 Initializing model: {GEMINI_MODEL}")
    model = genai.GenerativeModel(GEMINI_MODEL)
    
    print("📤 Sending test prompt...")
    resp = model.generate_content("Say hello in one sentence.")
    
    print(f"\n✅ SUCCESS!")
    print(f"Response: {resp.text}\n")
    print("🎉 Your Gemini API is working correctly!")
    print("   You can now run the full agent system with: python3 main.py")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}\n")
    print("💡 Troubleshooting:")
    print("   1. Upgrade the package: pip install --upgrade google-generativeai")
    print("   2. Verify version: pip show google-generativeai (should be 0.5.x or newer)")
    print("   3. Restart your Python process/terminal")
    print("   4. Check your API key at: https://aistudio.google.com/app/apikey")
    print("\n📝 NOTE: Use 'import google.generativeai as genai' (NOT 'from google import genai')")

