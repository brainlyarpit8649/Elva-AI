#!/usr/bin/env python3
"""
Debug Save Message Method
Find exactly why save_message is failing
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add backend directory to path
sys.path.append('/app/backend')

async def debug_save_message():
    """Debug save_message method step by step"""
    print("🔍 Debugging save_message Method")
    print("=" * 50)
    
    try:
        from enhanced_message_memory import EnhancedMessageMemory
        
        memory = EnhancedMessageMemory()
        await memory.initialize()
        
        session_id = "debug_save_test"
        
        # Step 1: Test _test_connection directly
        print("1️⃣ Testing _test_connection()...")
        try:
            connection_result = await memory._test_connection()
            print(f"   📊 Connection test result: {connection_result}")
            print(f"   📊 Connection tested flag: {memory._connection_tested}")
        except Exception as e:
            print(f"   ❌ Connection test failed: {e}")
        
        # Step 2: Test duplicate check
        print("\n2️⃣ Testing duplicate check...")
        try:
            existing = await memory._safe_db_operation(
                memory.messages_collection.find_one,
                {
                    "session_id": session_id,
                    "role": "user",
                    "content": "My name is Arpit"
                },
                timeout=5.0
            )
            print(f"   📊 Existing message found: {existing is not None}")
        except Exception as e:
            print(f"   ❌ Duplicate check failed: {e}")
        
        # Step 3: Test message document preparation
        print("\n3️⃣ Testing message document preparation...")
        try:
            message_doc = {
                "session_id": session_id,
                "role": "user",
                "content": "My name is Arpit",
                "timestamp": datetime.utcnow(),
                "metadata": {"test": True},
                "indexed": True,
                "message_id": "debug_test_123"
            }
            print(f"   ✅ Message document prepared: {json.dumps(message_doc, default=str, indent=2)}")
        except Exception as e:
            print(f"   ❌ Message document preparation failed: {e}")
        
        # Step 4: Test MongoDB insert with safe operation
        print("\n4️⃣ Testing MongoDB insert with safe operation...")
        try:
            mongo_result = await memory._safe_db_operation(
                memory.messages_collection.insert_one,
                message_doc,
                timeout=8.0
            )
            
            if mongo_result and mongo_result.inserted_id:
                print(f"   ✅ MongoDB insert successful: {mongo_result.inserted_id}")
            else:
                print(f"   ❌ MongoDB insert failed: {mongo_result}")
        except Exception as e:
            print(f"   ❌ MongoDB insert with safe operation failed: {e}")
        
        # Step 5: Test full save_message method with detailed logging
        print("\n5️⃣ Testing full save_message method...")
        try:
            # Enable detailed logging
            import logging
            logging.basicConfig(level=logging.INFO)
            
            save_result = await memory.save_message(
                session_id=session_id + "_full",
                role="user",
                content="My name is Arpit Kumar",
                metadata={"test": True, "method": "full"}
            )
            
            print(f"   📊 Save message result: {save_result}")
            
            if save_result:
                print("   ✅ Full save_message method successful!")
                
                # Test context retrieval
                context = await memory.get_context_for_ai(session_id + "_full")
                print(f"   📋 Context after save: {len(context)} chars")
                print(f"   🔍 Contains 'Arpit': {'Arpit' in context}")
                
            else:
                print("   ❌ Full save_message method failed")
                
        except Exception as e:
            print(f"   ❌ Full save_message method exception: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n✅ Save Message Debug Completed!")
        
    except Exception as e:
        print(f"❌ Critical error during save message debug: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await debug_save_message()

if __name__ == "__main__":
    asyncio.run(main())