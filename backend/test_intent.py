import asyncio
import sys
import os
sys.path.append('/app/backend')

from advanced_hybrid_ai import AdvancedHybridAI

async def test_intent_detection():
    ai = AdvancedHybridAI()
    
    test_messages = [
        "Send an email to john@example.com about the project update",
        "Can you send an email to sarah@company.com regarding the meeting",
        "I need to email my client about the proposal",
        "Draft an email to the team about tomorrow's presentation",
        "Hello, how are you?"
    ]
    
    for msg in test_messages:
        print(f"\n🧪 Testing: '{msg}'")
        try:
            intent_data = await ai._groq_intent_detection(msg)
            print(f"✅ Result: {intent_data}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_intent_detection())