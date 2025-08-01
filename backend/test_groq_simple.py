import os
import asyncio
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

async def test_groq_api():
    try:
        # Initialize Groq LLM exactly like in advanced_hybrid_ai.py
        groq_llm = ChatOpenAI(
            temperature=0,
            openai_api_key=os.getenv("GROQ_API_KEY"),
            model="llama3-8b-8192",
            base_url="https://api.groq.com/openai/v1"
        )
        
        # Simple test prompt
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Return only JSON: {{\"test\": \"success\"}}"),
            ("user", "{input}")
        ])
        
        chain = prompt_template | groq_llm
        response = chain.invoke({"input": "test"})
        
        print(f"✅ Groq API Response: {response.content}")
        
        # Test intent detection prompt
        system_message = """You are an AI assistant specialized in intent detection. Extract structured JSON data.

Intent types: send_email, general_chat

For send email: {"intent": "send_email", "recipient": "email", "subject": "subject"}
For general chat: {"intent": "general_chat", "message": "original message"}

Return ONLY the JSON object."""
        
        prompt_template2 = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", "{input}")
        ])
        
        chain2 = prompt_template2 | groq_llm
        response2 = chain2.invoke({"input": "Send an email to john@example.com about the meeting"})
        
        print(f"✅ Intent Detection Response: {response2.content}")
        
    except Exception as e:
        print(f"❌ Groq API Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_groq_api())