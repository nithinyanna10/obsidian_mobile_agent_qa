"""
Test different API patterns to see which works
"""
from config import GEMINI_API_KEY, GEMINI_MODEL

print("Testing API patterns...\n")

# Pattern 1: Current approach (google.generativeai)
print("1. Testing: import google.generativeai as genai")
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content("Say hello in one sentence.")
    print(f"   ✅ SUCCESS: {response.text}")
except Exception as e:
    print(f"   ❌ FAILED: {e}")

print()

# Pattern 2: Client-based approach (if available)
print("2. Testing: genai.Client() pattern")
try:
    import google.generativeai as genai
    # Try Client-based API (newer versions might support this)
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents="Say hello in one sentence."
    )
    print(f"   ✅ SUCCESS: {response.text}")
except AttributeError:
    print("   ⚠️  Client API not available in this version")
except Exception as e:
    print(f"   ❌ FAILED: {e}")

print()

# Pattern 3: Direct import (incorrect but testing)
print("3. Testing: from google import genai (likely incorrect)")
try:
    from google import genai
    print("   ⚠️  This import worked, but may not be the correct package")
except ImportError as e:
    print(f"   ✅ Expected failure: {e} (this is correct - use google.generativeai)")

print("\n" + "="*60)
print("RECOMMENDATION: Use Pattern 1 (current approach)")
print("="*60)

