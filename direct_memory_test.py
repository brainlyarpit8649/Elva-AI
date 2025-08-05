#!/usr/bin/env python3
"""
Minimal Memory Test - Direct Database Testing
Test the enhanced memory system directly without going through the API
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add backend directory to path
sys.path.append('/app/backend')

async def test_enhanced_memory_direct():
    """Test enhanced memory system directly"""
    print("🧪 Testing Enhanced Memory System Directly")
    print("=" * 50)
    
    try:
        # Import the enhanced memory system
        from enhanced_message_memory import initialize_enhanced_message_memory
        
        print("1️⃣ Initializing Enhanced Memory System...")
        enhanced_memory = await initialize_enhanced_message_memory()
        
        if enhanced_memory:
            print("   ✅ Enhanced Memory System initialized successfully")
            
            # Test health status
            print("\n2️⃣ Checking Health Status...")
            health = await enhanced_memory.get_health_status()
            print(f"   📊 Health Status: {json.dumps(health, indent=2)}")
            
            # Test saving a message
            print("\n3️⃣ Testing Message Save...")
            session_id = "test_session_direct"
            
            save_result = await enhanced_memory.save_message(
                session_id=session_id,
                role="user",
                content="My name is Arpit",
                metadata={"test": True}
            )
            
            if save_result:
                print("   ✅ User message saved successfully")
            else:
                print("   ❌ Failed to save user message")
                return
            
            # Save AI response
            ai_save_result = await enhanced_memory.save_message(
                session_id=session_id,
                role="assistant",
                content="Nice to meet you, Arpit! I'll remember your name.",
                metadata={"test": True}
            )
            
            if ai_save_result:
                print("   ✅ AI message saved successfully")
            else:
                print("   ❌ Failed to save AI message")
            
            # Test context retrieval
            print("\n4️⃣ Testing Context Retrieval...")
            context = await enhanced_memory.get_context_for_ai(session_id)
            print(f"   📋 Context Length: {len(context)} characters")
            print(f"   📝 Context Preview: {context[:200]}...")
            
            # Check if context contains the name
            contains_name = "Arpit" in context
            print(f"   🔍 Contains name 'Arpit': {contains_name}")
            
            # Test conversation history
            print("\n5️⃣ Testing Conversation History...")
            history = await enhanced_memory.get_conversation_history(session_id)
            print(f"   📚 History Length: {len(history)} messages")
            
            for i, msg in enumerate(history):
                print(f"   Message {i+1}: {msg['role']} - {msg['content'][:50]}...")
            
            # Test session stats
            print("\n6️⃣ Testing Session Stats...")
            stats = await enhanced_memory.get_session_stats(session_id)
            print(f"   📊 Session Stats: {json.dumps(stats, indent=2)}")
            
            # Test another message to simulate conversation flow
            print("\n7️⃣ Testing Additional Messages...")
            
            # Add more messages
            await enhanced_memory.save_message(session_id, "user", "How are you?")
            await enhanced_memory.save_message(session_id, "assistant", "I'm doing well, thank you for asking!")
            await enhanced_memory.save_message(session_id, "user", "What is my name?")
            
            # Get updated context
            updated_context = await enhanced_memory.get_context_for_ai(session_id)
            print(f"   📋 Updated Context Length: {len(updated_context)} characters")
            print(f"   🔍 Updated context contains 'Arpit': {'Arpit' in updated_context}")
            
            # Show the full context for debugging
            print("\n8️⃣ Full Context for Debugging:")
            print("   " + "="*40)
            print(updated_context)
            print("   " + "="*40)
            
            print("\n✅ Enhanced Memory System Direct Test Completed!")
            
        else:
            print("   ❌ Failed to initialize Enhanced Memory System")
            
    except Exception as e:
        print(f"   ❌ Exception during direct test: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await test_enhanced_memory_direct()

if __name__ == "__main__":
    asyncio.run(main())