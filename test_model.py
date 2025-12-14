"""
Quick test script to verify Gemini model access
"""
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL

print(f"Testing Gemini API with model: {GEMINI_MODEL}")
print(f"API Key: {GEMINI_API_KEY[:20]}...")

try:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Try to list available models
    print("\n📋 Checking available models...")
    try:
        models = genai.list_models()
        available = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        print(f"Available models: {available}")
    except Exception as e:
        print(f"Could not list models: {e}")
    
    # Try to initialize the model
    print(f"\n🔧 Initializing {GEMINI_MODEL}...")
    model = genai.GenerativeModel(GEMINI_MODEL)
    print(f"✓ Model initialized successfully")
    
    # Try a simple generation
    print(f"\n🧪 Testing model with simple prompt...")
    response = model.generate_content("Say 'Hello, World!' in one sentence.")
    print(f"✓ Response received: {response.text}")
    
    print(f"\n✅ {GEMINI_MODEL} is working correctly!")
    
    # Check package version
    import google.generativeai as _genai
    try:
        import pkg_resources
        version = pkg_resources.get_distribution("google-generativeai").version
        print(f"\n📦 Package version: {version}")
        major_version = int(version.split('.')[0])
        minor_version = int(version.split('.')[1])
        if major_version < 0 or (major_version == 0 and minor_version < 5):
            print(f"⚠️  WARNING: Version {version} is too old!")
            print("   Upgrade with: pip install --upgrade google-generativeai")
            print("   You need version 0.5.x or newer for models/gemini-1.5-flash")
        else:
            print(f"✓ Version is compatible (0.5.x+)")
    except:
        pass
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"\n💡 Troubleshooting:")
    print(f"   1. Update the package: pip install --upgrade google-generativeai")
    print(f"   2. Verify your API key at: https://aistudio.google.com/app/apikey")
    print(f"   3. Check if {GEMINI_MODEL} is available for your API key")

