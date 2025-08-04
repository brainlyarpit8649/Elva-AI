#!/usr/bin/env python3
"""
Direct test of Letta memory without going through the full API
"""

import sys
import os
import asyncio

# Add backend to path
sys.path.append('/app/backend')

from letta_memory import get_letta_memory

async def test_memory_direct():
    """Test memory system directly"""
    
    try:
        # Get memory instance
        memory = get_letta_memory()
        print("✅ Memory instance created")
        
        # Test storing a fact
        store_result = await memory.chat_with_memory("Remember that I love samosas", "test_session")
        print(f"📝 Store result: {store_result}")
        
        # Test retrieving the fact  
        recall_result = await memory.chat_with_memory("What do I love to eat?", "test_session")
        print(f"🔍 Recall result: {recall_result}")
        
        # Test nickname recall
        nickname_result = await memory.chat_with_memory("What's my nickname?", "test_session") 
        print(f"👤 Nickname result: {nickname_result}")
        
        # Check memory file
        print(f"📁 Memory file exists: {memory.memory_file.exists()}")
        
        if memory.memory_file.exists():
            print(f"📊 Total facts stored: {len(memory.memory.get('facts', {}))}")
            for key, fact in memory.memory.get('facts', {}).items():
                print(f"  - {key}: {fact.get('text', '')[:50]}...")
        
    except Exception as e:
        print(f"❌ Direct test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Testing Letta Memory Directly")
    asyncio.run(test_memory_direct())
    print("✨ Direct test completed!")