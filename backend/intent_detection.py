import os
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import json
import logging

load_dotenv()

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    temperature=0,
    openai_api_key=os.getenv("GROQ_API_KEY"),
    model="mixtral-8x7b-32768",
    base_url="https://api.groq.com/openai/v1"
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an AI that detects user intent and extracts structured data in JSON format.
    
    Focus on detecting EMAIL SENDING intents. When user wants to send an email, extract:
    - intent: "send_email"
    - recipient_name: the person's name they want to send to
    - recipient_email: email address if provided
    - subject: email subject
    - body: email content/message
    
    If the user message is not about sending email, return:
    - intent: "general_chat"
    - message: the original user message
    
    Always respond with valid JSON only, no additional text.
    
    Examples:
    User: "Send an email to John about the meeting tomorrow"
    Response: {{"intent": "send_email", "recipient_name": "John", "recipient_email": "", "subject": "Meeting Tomorrow", "body": "About the meeting tomorrow"}}
    
    User: "Hello how are you?"
    Response: {{"intent": "general_chat", "message": "Hello how are you?"}}
    """),
    ("user", "{input}")
])

def detect_intent(user_input: str) -> dict:
    """
    Detect user intent and extract structured data
    
    Args:
        user_input: The user's message
        
    Returns:
        dict: Structured intent data in JSON format
    """
    try:
        chain = prompt | llm
        response = chain.invoke({"input": user_input})
        
        # Try to parse the response as JSON
        try:
            intent_data = json.loads(response.content)
            return intent_data
        except json.JSONDecodeError:
            # If parsing fails, return as general chat
            logger.warning(f"Failed to parse LLM response as JSON: {response.content}")
            return {
                "intent": "general_chat",
                "message": user_input,
                "error": "Failed to parse intent"
            }
            
    except Exception as e:
        logger.error(f"Error in intent detection: {str(e)}")
        return {
            "intent": "general_chat",
            "message": user_input,
            "error": str(e)
        }

def format_intent_for_webhook(intent_data: dict, user_id: str, session_id: str) -> dict:
    """
    Format intent data for n8n webhook
    
    Args:
        intent_data: The detected intent data
        user_id: User identifier
        session_id: Chat session identifier
        
    Returns:
        dict: Formatted data for webhook
    """
    return {
        "user_id": user_id,
        "session_id": session_id,
        "intent": intent_data.get("intent"),
        "data": intent_data,
        "timestamp": "2024-01-01T00:00:00Z"  # This will be updated in the main handler
    }