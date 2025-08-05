#!/usr/bin/env python3
"""
Debug Enhanced Memory System - Step by Step
Find exactly where the memory system is failing
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add backend directory to path
sys.path.append('/app/backend')

async def debug_enhanced_memory():
    """Debug enhanced memory system step by step"""
    print("🔍 Debugging Enhanced Memory System")
    print("=" * 50)
    
    try:
        # Step 1: Import and create instance
        print("1️⃣ Importing Enhanced Memory System...")
        from enhanced_message_memory import EnhancedMessageMemory
        
        memory = EnhancedMessageMemory()
        print("   ✅ EnhancedMessageMemory instance created")
        
        # Step 2: Test MongoDB connection directly
        print("\n2️⃣ Testing MongoDB Connection...")
        try:
            await memory._test_connection()
            print("   ✅ MongoDB connection test passed")
        except Exception as e:
            print(f"   ❌ MongoDB connection test failed: {e}")
        
        # Step 3: Test Redis initialization
        print("\n3️⃣ Testing Redis Initialization...")
        try:
            await memory._initialize_redis()
            print(f"   📊 Redis connected: {memory.redis_connected}")
        except Exception as e:
            print(f"   ❌ Redis initialization failed: {e}")
        
        # Step 4: Test index creation
        print("\n4️⃣ Testing Index Creation...")
        try:
            await memory._ensure_mongo_indexes()
            print(f"   📊 Indexes created: {memory._indexes_created}")
        except Exception as e:
            print(f"   ❌ Index creation failed: {e}")
        
        # Step 5: Full initialization
        print("\n5️⃣ Testing Full Initialization...")
        try:
            init_result = await memory.initialize()
            print(f"   📊 Initialization result: {init_result}")
        except Exception as e:
            print(f"   ❌ Full initialization failed: {e}")
        
        # Step 6: Test health status
        print("\n6️⃣ Testing Health Status...")
        try:
            health = await memory.get_health_status()
            print(f"   📊 Health Status: {json.dumps(health, indent=2)}")
        except Exception as e:
            print(f"   ❌ Health status failed: {e}")
        
        # Step 7: Test message save with detailed error handling
        print("\n7️⃣ Testing Message Save...")
        session_id = "debug_session_test"
        
        try:
            # Test the safe database operation directly
            print("   Testing safe database operation...")
            
            # Prepare message document manually
            message_doc = {
                "session_id": session_id,
                "role": "user",
                "content": "My name is Arpit",
                "timestamp": datetime.utcnow(),
                "metadata": {"test": True},
                "indexed": True,
                "message_id": "test_message_123"
            }
            
            # Try direct insert
            result = await memory._safe_db_operation(
                memory.messages_collection.insert_one,
                message_doc,
                timeout=10.0
            )
            
            if result:
                print(f"   ✅ Direct database insert successful: {result.inserted_id}")
                
                # Now test the full save_message method
                save_result = await memory.save_message(
                    session_id=session_id,
                    role="assistant", 
                    content="Hello Arpit! Nice to meet you.",
                    metadata={"test": True}
                )
                
                if save_result:
                    print("   ✅ Full save_message method successful")
                else:
                    print("   ❌ Full save_message method failed")
                
            else:
                print("   ❌ Direct database insert failed")
                
        except Exception as e:
            print(f"   ❌ Message save test failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 8: Test context retrieval
        print("\n8️⃣ Testing Context Retrieval...")
        try:
            context = await memory.get_context_for_ai(session_id)
            print(f"   📋 Context retrieved: {len(context)} characters")
            print(f"   📝 Context preview: {context[:200]}...")
            print(f"   🔍 Contains 'Arpit': {'Arpit' in context}")
        except Exception as e:
            print(f"   ❌ Context retrieval failed: {e}")
        
        # Step 9: Test conversation history
        print("\n9️⃣ Testing Conversation History...")
        try:
            history = await memory.get_conversation_history(session_id)
            print(f"   📚 History retrieved: {len(history)} messages")
            for i, msg in enumerate(history):
                print(f"   Message {i+1}: {msg.get('role', 'unknown')} - {msg.get('content', '')[:50]}...")
        except Exception as e:
            print(f"   ❌ Conversation history failed: {e}")
        
        print("\n✅ Enhanced Memory System Debug Completed!")
        
    except Exception as e:
        print(f"❌ Critical error during debug: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await debug_enhanced_memory()

if __name__ == "__main__":
    asyncio.run(main())