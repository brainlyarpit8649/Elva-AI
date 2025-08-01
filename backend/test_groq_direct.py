import asyncio
import sys
import os
import json
sys.path.append('/app/backend')

from advanced_hybrid_ai import AdvancedHybridAI

async def test_groq_response():
    ai = AdvancedHybridAI()
    
    test_message = "Send an email to john@example.com about the project update"
    
    system_message = """You are an AI assistant specialized in intent detection. Extract structured JSON data.

Intent types: send_email, create_event, add_todo, set_reminder, generate_post_prompt_package, web_search, creative_writing, general_chat

Example JSON responses:
Send email: {"intent": "send_email", "recipient_name": "Name", "subject": "Subject", "body": "Content"}
General chat: {"intent": "general_chat", "message": "original message"}

Return ONLY the JSON object."""
    
    try:
        print("🧪 Testing Groq API directly...")
        response = await ai._get_groq_response(test_message, system_message)
        print(f"✅ Groq Raw Response: {response}")
        
        # Try to parse JSON
        try:
            content = response.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx + 1]
                parsed = json.loads(json_str)
                print(f"✅ Parsed JSON: {parsed}")
            else:
                print(f"❌ No valid JSON found in response")
        except Exception as parse_error:
            print(f"❌ JSON parse error: {parse_error}")
            
    except Exception as e:
        print(f"❌ Groq API Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_groq_response())