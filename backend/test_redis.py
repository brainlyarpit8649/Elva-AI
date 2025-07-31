#!/usr/bin/env python3
import asyncio
import redis.asyncio as redis
import os
from dotenv import load_dotenv

load_dotenv()

async def test_redis():
    try:
        # Test Upstash Redis connection with SSL
        redis_url = "rediss://default:ARTGAAIjcDFjNWNlOTRjZDY5ODM0YTBjOTI2MTc3NzhmNzg3YzBkNnAxMA@brave-deer-5318.upstash.io:6379"
        print(f"Testing Redis connection with SSL: {redis_url}")
        
        client = await redis.from_url(redis_url, decode_responses=True, ssl_cert_reqs=None)
        result = await client.ping()
        print(f"✅ Redis ping successful: {result}")
        
        # Test basic operations
        await client.set("test_key", "test_value", ex=60)
        value = await client.get("test_key")
        print(f"✅ Redis set/get test: {value}")
        
        await client.close()
        print("✅ Redis connection test completed successfully")
        
    except Exception as e:
        print(f"❌ Redis SSL connection failed: {e}")
        
        # Try without SSL as fallback
        try:
            redis_url = "redis://default:ARTGAAIjcDFjNWNlOTRjZDY5ODM0YTBjOTI2MTc3NzhmNzg3YzBkNnAxMA@brave-deer-5318.upstash.io:6379"
            print(f"Trying without SSL: {redis_url}")
            
            client = await redis.from_url(redis_url, decode_responses=True)
            result = await client.ping()
            print(f"✅ Redis ping successful (no SSL): {result}")
            await client.close()
            
        except Exception as e2:
            print(f"❌ Both SSL and non-SSL Redis connections failed: {e2}")

if __name__ == "__main__":
    asyncio.run(test_redis())