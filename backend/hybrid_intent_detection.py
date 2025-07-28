import os
import json
import asyncio
import logging
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv()
logger = logging.getLogger(__name__)

class ModelChoice(Enum):
    GROQ = "groq"
    CLAUDE = "claude"

class HybridAIChat:
    """
    Hybrid AI Chat system that intelligently routes between Claude Sonnet and Groq
    based on the type of task being performed.
    """
    
    def __init__(self):
        # Initialize Groq LLM (for intent detection and structured tasks)
        self.groq_llm = ChatOpenAI(
            temperature=0,
            openai_api_key=os.getenv("GROQ_API_KEY"),
            model="llama3-8b-8192",
            base_url="https://api.groq.com/openai/v1"
        )
        
        # Claude API key
        self.claude_api_key = os.getenv("CLAUDE_API_KEY")
        if not self.claude_api_key:
            logger.error("CLAUDE_API_KEY not found in environment variables")
            
        # Task routing configuration
        self.claude_tasks = {
            "general_chat", "send_email", "generate_post_prompt_package", 
            "friendly_draft", "creative_content", "emotional_response"
        }
        
        self.groq_tasks = {
            "intent_detection", "structured_parsing", "logical_reasoning",
            "data_extraction", "quick_analysis"
        }
        
    def _determine_model(self, task_type: str) -> ModelChoice:
        """
        Intelligently route tasks between Claude and Groq based on task type.
        
        Args:
            task_type (str): The type of task being performed
            
        Returns:
            ModelChoice: Which model to use for the task
        """
        if task_type in self.claude_tasks:
            return ModelChoice.CLAUDE
        elif task_type in self.groq_tasks:
            return ModelChoice.GROQ
        else:
            # Default to Claude for unknown tasks (better for general conversation)
            return ModelChoice.CLAUDE
            
    async def _get_claude_response(self, prompt: str, system_message: str = None) -> str:
        """
        Get response from Claude Sonnet using emergentintegrations.
        
        Args:
            prompt (str): User prompt
            system_message (str): System message for Claude
            
        Returns:
            str: Claude's response
        """
        try:
            # Create unique session ID for this conversation
            session_id = f"elva_claude_{uuid.uuid4().hex[:8]}"
            
            # Initialize Claude chat
            claude_chat = LlmChat(
                api_key=self.claude_api_key,
                session_id=session_id,
                system_message=system_message or "You are Elva AI – a friendly, emotionally intelligent assistant."
            ).with_model("anthropic", "claude-3-5-sonnet-20241022").with_max_tokens(4096)
            
            # Create user message
            user_message = UserMessage(text=prompt)
            
            # Get response
            response = await claude_chat.send_message(user_message)
            return response
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            # Fallback to Groq if Claude fails
            return await self._get_groq_response(prompt, system_message)
            
    async def _get_groq_response(self, prompt: str, system_message: str = None) -> str:
        """
        Get response from Groq using LangChain.
        
        Args:
            prompt (str): User prompt
            system_message (str): System message for Groq
            
        Returns:
            str: Groq's response
        """
        try:
            # Create prompt template
            if system_message:
                prompt_template = ChatPromptTemplate.from_messages([
                    ("system", system_message),
                    ("user", "{input}")
                ])
            else:
                prompt_template = ChatPromptTemplate.from_messages([
                    ("user", "{input}")
                ])
            
            # Create chain and get response
            chain = prompt_template | self.groq_llm
            response = chain.invoke({"input": prompt})
            return response.content
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return "⚠️ I'm experiencing technical difficulties. Please try again."

    async def detect_intent(self, user_input: str) -> dict:
        """
        Detect user intent using Groq for fast, structured reasoning.
        
        Args:
            user_input (str): User's input message
            
        Returns:
            dict: Parsed intent data
        """
        logger.info(f"🧠 Intent Detection (Groq): {user_input}")
        
        # Intent detection is a structured, logical task - use Groq
        system_message = """You are an AI assistant that detects user intent and extracts structured JSON for different tasks.

CRITICAL INSTRUCTIONS:
- Respond with ONLY valid JSON, no additional text or explanations
- All JSON must be complete and properly formatted
- Do not add any text before or after the JSON
- For all intents except general_chat, populate ALL fields with realistic content

You can detect the following intents:
1. send_email
2. create_event
3. add_todo
4. set_reminder
5. generate_post_prompt_package
6. general_chat

Examples of COMPLETE JSON responses:

For "Send an email to John about the meeting":
{{
  "intent": "send_email",
  "recipient_name": "John",
  "recipient_email": "",
  "subject": "Meeting Update",
  "body": "Hi John,\\n\\nI wanted to update you about our upcoming meeting. Please let me know if you have any questions.\\n\\nBest regards"
}}

For "Create a team meeting for tomorrow at 2pm":
{{
  "intent": "create_event",
  "event_title": "Team Meeting",
  "date": "tomorrow",
  "time": "2:00 PM",
  "participants": ["team@company.com"],
  "location": "Conference Room"
}}

For "Remind me to call the client":
{{
  "intent": "set_reminder",
  "reminder_text": "Call client about project status",
  "reminder_time": "",
  "reminder_date": "today"
}}

For "Add finish the report to my todo list":
{{
  "intent": "add_todo",
  "task": "Finish the quarterly report",
  "due_date": ""
}}

For "Post about AI on LinkedIn":
{{
  "intent": "linkedin_post",
  "topic": "Artificial Intelligence",
  "category": "Technology",
  "post_content": "Excited to share insights about AI advancements! #AI #Technology"
}}

For anything else:
{{
  "intent": "general_chat",
  "message": "original user message"
}}

REMEMBER: Return ONLY the JSON object, nothing else."""

        try:
            response = await self._get_groq_response(user_input, system_message)
            
            # Extract JSON from the response
            content = response.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as json_err:
                    logger.error(f"JSON decode error: {json_err}")
                    # Fallback to general chat
                    return {"intent": "general_chat", "message": user_input}
            else:
                return {"intent": "general_chat", "message": user_input}
                
        except Exception as e:
            logger.error(f"Intent detection error: {e}")
            return {"intent": "general_chat", "message": user_input, "error": str(e)}

    async def generate_friendly_draft(self, intent_data: dict) -> str:
        """
        Generate friendly, human-like drafts using Claude for emotional intelligence.
        
        Args:
            intent_data (dict): Structured intent data
            
        Returns:
            str: Friendly draft message
        """
        intent_type = intent_data.get("intent", "general_chat")
        logger.info(f"💝 Friendly Draft Generation (Claude): {intent_type}")
        
        # Draft generation requires emotional intelligence - use Claude
        system_message = """You are Elva AI – a friendly, emotionally intelligent assistant that converts structured intent data into warm, human-friendly messages.

Your responses should be:
- Warm and personable
- Professional when appropriate
- Emotionally aware and considerate
- Clear and helpful

Respond based on intent type:

- send_email → Draft a friendly, professional email
- linkedin_post → Create an engaging professional LinkedIn post
- create_event / add_todo / set_reminder → Provide a warm summary of the task
- general_chat → Respond naturally and helpfully

Return plain text responses that feel genuinely human and caring.

Examples:

For email intent: 
"✉️ I've prepared a thoughtful email draft for [recipient]. Here's what I'm suggesting:

Subject: [subject]
Body: [body content]

Feel free to review and let me know if you'd like me to adjust the tone or add anything!"

For LinkedIn post:
"📱 Here's an engaging LinkedIn post I've crafted for you:

[post content]

This should help you connect with your professional network while showcasing your expertise!"

For reminders/todos:
"⏰ I'll make sure you remember [task details]. This sounds important, so I'll help you stay on top of it!"
"""

        try:
            input_text = f"Please create a friendly draft based on this intent data: {json.dumps(intent_data)}"
            response = await self._get_claude_response(input_text, system_message)
            return response
            
        except Exception as e:
            logger.error(f"Draft generation error: {e}")
            return "⚠️ I had trouble creating that draft. Could you try again?"

    async def handle_general_chat(self, user_input: str) -> str:
        """
        Handle general conversation using Claude for warm, human-like responses.
        
        Args:
            user_input (str): User's chat message
            
        Returns:
            str: Claude's friendly response
        """
        logger.info(f"💬 General Chat (Claude): {user_input}")
        
        # General conversation requires emotional intelligence - use Claude
        system_message = """You are Elva AI – a friendly, warm, and helpful AI assistant. 

Your personality:
- Genuinely caring and emotionally intelligent
- Professional but approachable
- Helpful and solution-oriented
- Naturally conversational

You can help users with:
- Sending emails (professional or personal)
- Creating calendar events and meetings
- Setting reminders and managing todos
- Writing LinkedIn posts
- General conversation and questions

Always respond in a warm, human-like way that makes users feel heard and supported. Keep responses concise but meaningful."""

        try:
            response = await self._get_claude_response(user_input, system_message)
            return response
            
        except Exception as e:
            logger.error(f"General chat error: {e}")
            return "🤖 I'm having a bit of trouble right now. Could you try asking me again?"

    def format_intent_for_webhook(self, intent_data: dict, user_id: str, session_id: str) -> dict:
        """
        Format intent data for webhook transmission (uses Groq for structured processing).
        
        Args:
            intent_data (dict): Intent data to format
            user_id (str): User identifier
            session_id (str): Session identifier
            
        Returns:
            dict: Formatted webhook data
        """
        from datetime import datetime
        return {
            "user_id": user_id,
            "session_id": session_id,
            "intent": intent_data.get("intent"),
            "data": intent_data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

# Global instance for the hybrid AI system
hybrid_ai = HybridAIChat()

# Async wrapper functions for backward compatibility
async def detect_intent(user_input: str) -> dict:
    """Detect intent using Groq for fast reasoning."""
    return await hybrid_ai.detect_intent(user_input)

async def generate_friendly_draft(intent_data: dict) -> str:
    """Generate friendly drafts using Claude for emotional intelligence."""
    return await hybrid_ai.generate_friendly_draft(intent_data)

async def handle_general_chat(user_input: str) -> str:
    """Handle general chat using Claude for warm responses."""
    return await hybrid_ai.handle_general_chat(user_input)

def format_intent_for_webhook(intent_data: dict, user_id: str, session_id: str) -> dict:
    """Format intent data for webhook."""
    return hybrid_ai.format_intent_for_webhook(intent_data, user_id, session_id)

# Sync wrapper functions for backward compatibility with existing code
def detect_intent_sync(user_input: str) -> dict:
    """Synchronous wrapper for detect_intent."""
    return asyncio.run(detect_intent(user_input))

def generate_friendly_draft_sync(intent_data: dict) -> str:
    """Synchronous wrapper for generate_friendly_draft."""
    return asyncio.run(generate_friendly_draft(intent_data))

def handle_general_chat_sync(user_input: str) -> str:
    """Synchronous wrapper for handle_general_chat."""
    return asyncio.run(handle_general_chat(user_input))