"""
Minimal working OpenAI test (VERIFY BEFORE RUNNING AGENTS)
This verifies your API key and model access work correctly.
"""
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

print("🧪 Testing OpenAI API...")
print(f"Model: {OPENAI_MODEL}")
print(f"API Key: {OPENAI_API_KEY[:20]}...\n")

try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    print(f"🔧 Testing text generation...")
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "user",
                "content": "Say hello in one sentence."
            }
        ],
        temperature=0.3
    )
    
    if response and response.choices and response.choices[0].message.content:
        print(f"\n✅ SUCCESS!")
        print(f"Response: {response.choices[0].message.content}\n")
        print("🎉 Your OpenAI API is working correctly!")
        print("   You can now run the full agent system with: python3 main.py")
    else:
        print("\n❌ ERROR: Empty response from API")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}\n")
    print("💡 Troubleshooting:")
    print("   1. Verify your API key is correct in config.py")
    print("   2. Check your OpenAI account has credits/quota")
    print("   3. Verify the model name is correct (gpt-4o or gpt-4o-mini)")

