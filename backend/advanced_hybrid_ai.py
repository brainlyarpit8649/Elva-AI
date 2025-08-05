import os
import json
import asyncio
import logging
import uuid
import re
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from emergentintegrations.llm.chat import LlmChat, UserMessage
from mcp_integration import get_mcp_service

load_dotenv()
logger = logging.getLogger(__name__)

class ModelChoice(Enum):
    GROQ = "groq"
    CLAUDE = "claude"
    BOTH_SEQUENTIAL = "both_sequential"  # Use both models in sequence
    HYBRID_PARALLEL = "hybrid_parallel"  # Use both models and merge results

@dataclass
class TaskClassification:
    """Advanced task classification with multiple dimensions"""
    primary_intent: str
    emotional_complexity: str  # low, medium, high
    professional_tone_required: bool
    creative_requirement: str  # none, low, medium, high
    technical_complexity: str  # simple, moderate, complex
    response_length: str  # short, medium, long
    user_engagement_level: str  # informational, conversational, interactive
    context_dependency: str  # none, session, historical
    reasoning_type: str  # logical, emotional, creative, analytical

@dataclass
class RoutingDecision:
    """Routing decision with explanation"""
    primary_model: ModelChoice
    confidence: float  # 0.0 to 1.0
    reasoning: str
    fallback_model: Optional[ModelChoice] = None
    use_context_enhancement: bool = False

class AdvancedHybridAI:
    """
    Advanced Hybrid AI system with sophisticated task classification and routing
    """
    
    def __init__(self):
        # Initialize models
        self.groq_llm = ChatOpenAI(
            temperature=0,
            openai_api_key=os.getenv("GROQ_API_KEY"),
            model="llama3-8b-8192",
            base_url="https://api.groq.com/openai/v1"
        )
        
        self.claude_api_key = os.getenv("CLAUDE_API_KEY")
        if not self.claude_api_key:
            logger.error("CLAUDE_API_KEY not found in environment variables")
        
        # Conversation history for context-aware routing
        self.conversation_history = {}
        
        # Advanced routing configuration
        self.routing_rules = self._initialize_routing_rules()
        
    def is_direct_automation_intent(self, intent: str) -> bool:
        """Check if an intent should bypass AI response generation and go directly to automation"""
        direct_automation_intents = [
            "web_search",  # Direct web search using Google Search API
            "check_linkedin_notifications",
            "check_gmail_inbox",
            "check_gmail_unread", 
            "email_inbox_check",  # Added new intent for natural language email checking
            # Enhanced Gmail intents
            "summarize_gmail_emails",  # Summarize N latest emails with count limit
            "search_gmail_emails",     # Search emails with natural language queries
            "categorize_gmail_emails", # Categorize emails by type
            "scrape_price", 
            "scrape_product_listings",
            "linkedin_job_alerts",
            "check_website_updates",
            "monitor_competitors", 
            "scrape_news_articles",
            # Weather intents - instant responses, no approval needed
            "get_current_weather",
            "get_weather_forecast", 
            "get_air_quality_index",
            "get_weather_alerts",
            "get_sun_times"
        ]
        return intent in direct_automation_intents

    def get_automation_status_message(self, intent: str) -> str:
        """Get appropriate status message for automation intent"""
        status_messages = {
            "web_search": "🔍 Searching the web for information...",
            "check_linkedin_notifications": "🔔 Checking LinkedIn notifications...",
            "check_gmail_inbox": "📧 Checking Gmail inbox...",
            "check_gmail_unread": "📧 Checking Gmail unread emails...",
            "email_inbox_check": "📧 Checking your inbox for unread emails...",
            # Enhanced Gmail status messages
            "summarize_gmail_emails": "📧 Summarizing your latest emails...",
            "search_gmail_emails": "🔍 Searching through your Gmail...",
            "categorize_gmail_emails": "📊 Categorizing your emails...",
            "scrape_price": "💰 Searching for current prices...",
            "scrape_product_listings": "🛒 Scraping product listings...",
            "linkedin_job_alerts": "💼 Checking LinkedIn job alerts...",
            "check_website_updates": "🔍 Monitoring website updates...",
            "monitor_competitors": "📊 Analyzing competitor data...",
            "scrape_news_articles": "📰 Gathering latest news...",
            # Weather status messages
            "get_current_weather": "🌦️ Fetching current weather conditions...",
            "get_weather_forecast": "📅 Retrieving weather forecast...",
            "get_air_quality_index": "🌬️ Checking air quality levels...",
            "get_weather_alerts": "⚠️ Checking for weather alerts...",
            "get_sun_times": "🌅 Getting sunrise and sunset times..."
        }
        return status_messages.get(intent, "🔍 Searching the web...")

    def _initialize_routing_rules(self) -> Dict[str, Any]:
        """Initialize sophisticated routing rules"""
        return {
            # Intent-based primary routing - ALL GROQ NOW
            "intent_routing": {
                "general_chat": {"model": ModelChoice.GROQ, "confidence": 0.9},
                "send_email": {"model": ModelChoice.GROQ, "confidence": 0.85},
                "generate_post_prompt_package": {"model": ModelChoice.GROQ, "confidence": 0.85},
                "create_event": {"model": ModelChoice.GROQ, "confidence": 0.8},
                "add_todo": {"model": ModelChoice.GROQ, "confidence": 0.7},
                "set_reminder": {"model": ModelChoice.GROQ, "confidence": 0.7},
                "web_search": {"model": ModelChoice.GROQ, "confidence": 0.95},
                "complex_analysis": {"model": ModelChoice.GROQ, "confidence": 0.8},
                "creative_writing": {"model": ModelChoice.GROQ, "confidence": 0.9},
                "technical_explanation": {"model": ModelChoice.GROQ, "confidence": 0.8},
                # Enhanced Gmail intents with count limiting and search
                "summarize_gmail_emails": {"model": ModelChoice.GROQ, "confidence": 0.9, "direct_automation": True},
                "search_gmail_emails": {"model": ModelChoice.GROQ, "confidence": 0.9, "direct_automation": True},
                "categorize_gmail_emails": {"model": ModelChoice.GROQ, "confidence": 0.85, "direct_automation": True},
                "gmail_smart_actions": {"model": ModelChoice.GROQ, "confidence": 0.8},
                # New web automation intents
                "web_scraping": {"model": ModelChoice.GROQ, "confidence": 0.9},
                "linkedin_insights": {"model": ModelChoice.GROQ, "confidence": 0.85},
                "email_automation": {"model": ModelChoice.GROQ, "confidence": 0.8},

                "data_extraction": {"model": ModelChoice.GROQ, "confidence": 0.85},
                
                # Direct automation intents (bypass AI response/approval)
                "check_linkedin_notifications": {"model": ModelChoice.GROQ, "confidence": 0.9, "direct_automation": True},
                "check_gmail_inbox": {"model": ModelChoice.GROQ, "confidence": 0.9, "direct_automation": True},
                "check_gmail_unread": {"model": ModelChoice.GROQ, "confidence": 0.9, "direct_automation": True},
                "email_inbox_check": {"model": ModelChoice.GROQ, "confidence": 0.9, "direct_automation": True},
                "scrape_price": {"model": ModelChoice.GROQ, "confidence": 0.9, "direct_automation": True},
                "scrape_product_listings": {"model": ModelChoice.GROQ, "confidence": 0.9, "direct_automation": True},
                "linkedin_job_alerts": {"model": ModelChoice.GROQ, "confidence": 0.9, "direct_automation": True},
                "check_website_updates": {"model": ModelChoice.GROQ, "confidence": 0.8, "direct_automation": True},
                "monitor_competitors": {"model": ModelChoice.GROQ, "confidence": 0.8, "direct_automation": True},
                "scrape_news_articles": {"model": ModelChoice.GROQ, "confidence": 0.8, "direct_automation": True},
                # Weather intents (direct automation - instant responses)
                "get_current_weather": {"model": ModelChoice.GROQ, "confidence": 0.95, "direct_automation": True},
                "get_weather_forecast": {"model": ModelChoice.GROQ, "confidence": 0.95, "direct_automation": True},
                "get_air_quality_index": {"model": ModelChoice.GROQ, "confidence": 0.9, "direct_automation": True},
                "get_weather_alerts": {"model": ModelChoice.GROQ, "confidence": 0.9, "direct_automation": True},
                "get_sun_times": {"model": ModelChoice.GROQ, "confidence": 0.9, "direct_automation": True}
            },
            
            # Emotional complexity routing - ALL GROQ NOW
            "emotional_routing": {
                "high": ModelChoice.GROQ,    # Groq can handle emotional intelligence
                "medium": ModelChoice.GROQ,  # Groq for medium emotional processing  
                "low": ModelChoice.GROQ      # Groq for minimal emotional processing
            },
            
            # Professional tone routing
            "professional_routing": {
                "business_formal": ModelChoice.CLAUDE,  # Professional but warm
                "technical_formal": ModelChoice.GROQ,   # Precise and structured
                "casual_friendly": ModelChoice.CLAUDE   # Conversational and warm
            },
            
            # Creative requirement routing
            "creative_routing": {
                "high": ModelChoice.CLAUDE,      # High creativity needed
                "medium": ModelChoice.CLAUDE,    # Some creativity helpful
                "low": ModelChoice.GROQ,         # Minimal creativity needed
                "none": ModelChoice.GROQ         # No creativity required
            }
        }

    async def analyze_task_classification(self, user_input: str, session_id: str) -> TaskClassification:
        """
        Advanced task classification using AI analysis with conversation context
        """
        logger.info(f"🔍 Advanced Task Classification with Context: {user_input[:50]}...")
        
        try:
            # First, get the intent using our working intent detection
            intent_data = await self._groq_intent_detection(user_input)
            primary_intent = intent_data.get("intent", "general_chat")
            
            logger.info(f"🎯 Detected intent: {primary_intent}")
            
            # Get conversation context for better classification
            # Note: Using MCP context instead of conversation_memory
            conversation_context = ""
            
            # Enhanced classification prompt with context and detected intent
            classification_prompt = f"""
{f"Previous conversation context: {conversation_context}" if conversation_context else ""}

Current request: "{user_input}"
Detected intent: "{primary_intent}"

Based on the detected intent "{primary_intent}" and the user request, classify this across multiple dimensions:

Return JSON with these exact fields:
- primary_intent: "{primary_intent}" (use this exact value)
- emotional_complexity: low/medium/high (how much emotional intelligence is needed)
- professional_tone_required: true/false (business context vs casual)
- creative_requirement: none/low/medium/high (how much creativity is needed)
- technical_complexity: simple/moderate/complex (technical depth required)
- response_length: short/medium/long (expected response length)
- user_engagement_level: informational/conversational/interactive (type of interaction)
- context_dependency: none/session/historical (how much context is needed)
- reasoning_type: logical/emotional/creative/analytical (primary reasoning approach)

Guidelines by intent type:
- send_email, generate_post_prompt_package: professional_tone_required=true, creative_requirement=medium
- create_event, add_todo, set_reminder: professional_tone_required=true, reasoning_type=logical
- general_chat: emotional_complexity=medium, reasoning_type=emotional
- creative_writing: creative_requirement=high, reasoning_type=creative

Be precise and consider nuances in the request and any context from previous messages.
"""

            try:
                response = await self._get_groq_response(
                    classification_prompt, 
                    "You are an advanced task classifier with conversation awareness. Return only valid JSON."
                )
                
                # Parse the JSON response
                try:
                    classification_data = json.loads(response.strip())
                    # Ensure primary_intent matches our detected intent
                    classification_data["primary_intent"] = primary_intent
                    classified = TaskClassification(**classification_data)
                    logger.info(f"✅ Classification complete: {classified.primary_intent} (complexity: {classified.emotional_complexity})")
                    return classified
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Classification parsing error: {e}")
                    return self._get_default_classification_with_intent(user_input, primary_intent)
                
            except Exception as e:
                logger.error(f"Groq classification error: {e}")
                return self._get_default_classification_with_intent(user_input, primary_intent)
                
        except Exception as e:
            logger.error(f"Task classification error: {e}")
            return self._get_default_classification(user_input)

    def _get_default_classification(self, user_input: str) -> TaskClassification:
        """
        Get default classification when AI analysis fails
        """
        return TaskClassification(
            primary_intent="general_chat",
            emotional_complexity="medium",
            professional_tone_required=False,
            creative_requirement="low",
            technical_complexity="simple",
            response_length="medium",
            user_engagement_level="conversational",
            context_dependency="none",
            reasoning_type="emotional"
        )

    def _get_default_classification_with_intent(self, user_input: str, primary_intent: str) -> TaskClassification:
        """
        Get default classification with specific intent when AI analysis fails
        """
        # Set appropriate defaults based on intent type
        if primary_intent in ["send_email", "generate_post_prompt_package"]:
            return TaskClassification(
                primary_intent=primary_intent,
                emotional_complexity="medium",
                professional_tone_required=True,
                creative_requirement="medium",
                technical_complexity="simple",
                response_length="medium",
                user_engagement_level="interactive",
                context_dependency="session",
                reasoning_type="creative"
            )
        elif primary_intent in ["create_event", "add_todo", "set_reminder"]:
            return TaskClassification(
                primary_intent=primary_intent,
                emotional_complexity="low",
                professional_tone_required=True,
                creative_requirement="low",
                technical_complexity="simple",
                response_length="short",
                user_engagement_level="informational",
                context_dependency="none",
                reasoning_type="logical"
            )
        else:  # general_chat and others
            return TaskClassification(
                primary_intent=primary_intent,
                emotional_complexity="medium",
                professional_tone_required=False,
                creative_requirement="low",
                technical_complexity="simple",
                response_length="medium",
                user_engagement_level="conversational",
                context_dependency="none",
                reasoning_type="emotional"
            )

    def _calculate_routing_decision(self, classification: TaskClassification, session_id: str) -> RoutingDecision:
        """
        Calculate optimal routing decision based on sophisticated analysis
        """
        factors = []
        
        # Intent-based scoring
        intent_rule = self.routing_rules["intent_routing"].get(classification.primary_intent, 
                                                              {"model": ModelChoice.CLAUDE, "confidence": 0.5})
        primary_model = intent_rule["model"]
        base_confidence = intent_rule["confidence"]
        factors.append(f"Intent '{classification.primary_intent}' suggests {primary_model.value}")
        
        # Emotional complexity adjustment
        if classification.emotional_complexity == "high":
            if primary_model != ModelChoice.CLAUDE:
                primary_model = ModelChoice.CLAUDE
                base_confidence = min(base_confidence + 0.2, 1.0)
                factors.append("High emotional complexity → Claude")
        elif classification.emotional_complexity == "low" and classification.reasoning_type == "logical":
            if primary_model == ModelChoice.CLAUDE:
                primary_model = ModelChoice.GROQ
                base_confidence = min(base_confidence + 0.1, 1.0)
                factors.append("Low emotion + logical reasoning → Groq")
        
        # Professional tone with creativity
        if classification.professional_tone_required and classification.creative_requirement in ["medium", "high"]:
            primary_model = ModelChoice.BOTH_SEQUENTIAL
            base_confidence = min(base_confidence + 0.15, 1.0)
            factors.append("Professional + Creative → Sequential (Groq→Claude)")
        
        # Technical complexity considerations
        if classification.technical_complexity == "complex" and classification.reasoning_type == "analytical":
            if primary_model == ModelChoice.CLAUDE:
                primary_model = ModelChoice.GROQ
                base_confidence = min(base_confidence + 0.1, 1.0)
                factors.append("Complex technical analysis → Groq")
        
        # Response length and engagement
        if classification.response_length == "long" and classification.user_engagement_level == "conversational":
            if primary_model == ModelChoice.GROQ:
                primary_model = ModelChoice.CLAUDE
                base_confidence = min(base_confidence + 0.1, 1.0)
                factors.append("Long conversational response → Claude")
        
        # Context dependency
        if classification.context_dependency in ["session", "historical"]:
            # Check if we have conversation history
            if session_id in self.conversation_history:
                base_confidence = min(base_confidence + 0.05, 1.0)
                factors.append("Context available → Enhanced confidence")
        
        # Creative requirement override (but preserve sequential routing for specific intents)
        if classification.creative_requirement == "high":
            if primary_model != ModelChoice.CLAUDE and primary_model != ModelChoice.BOTH_SEQUENTIAL:
                primary_model = ModelChoice.CLAUDE
                base_confidence = min(base_confidence + 0.15, 1.0)
                factors.append("High creativity requirement → Claude")
            elif primary_model == ModelChoice.BOTH_SEQUENTIAL:
                # Keep sequential routing for intents that need content synchronization
                factors.append("High creativity with sequential routing preserved")
        
        # Determine fallback
        fallback_model = None
        if primary_model == ModelChoice.CLAUDE:
            fallback_model = ModelChoice.GROQ
        elif primary_model == ModelChoice.GROQ:
            fallback_model = ModelChoice.CLAUDE
            
        reasoning = " | ".join(factors)
        
        return RoutingDecision(
            primary_model=primary_model,
            confidence=base_confidence,
            reasoning=reasoning,
            fallback_model=fallback_model,
            use_context_enhancement=True  # Always enable context enhancement for better responses
        )

    def _update_conversation_history(self, session_id: str, user_input: str, classification: TaskClassification):
        """Update conversation history for context-aware routing"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
            
        self.conversation_history[session_id].append({
            "message": user_input,
            "classification": classification,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        # Keep only last 10 messages for performance
        if len(self.conversation_history[session_id]) > 10:
            self.conversation_history[session_id] = self.conversation_history[session_id][-10:]

    async def _get_context_enhanced_prompt(self, user_input: str, session_id: str) -> str:
        """Generate context-enhanced prompt using conversation history"""
        if session_id not in self.conversation_history or not self.conversation_history[session_id]:
            return user_input
            
        recent_context = self.conversation_history[session_id][-3:]  # Last 3 messages
        
        context_summary = "Recent conversation context:\n"
        for i, ctx in enumerate(recent_context, 1):
            context_summary += f"{i}. User: {ctx['message'][:100]}...\n"
        
        enhanced_prompt = f"{context_summary}\nCurrent request: {user_input}"
        return enhanced_prompt

    async def _get_claude_response(self, prompt: str, system_message: str = None, enhanced_context: bool = False) -> str:
        """Enhanced Claude response with better error handling"""
        try:
            session_id = f"elva_claude_enhanced_{uuid.uuid4().hex[:8]}"
            
            default_system = "You are Elva AI – a sophisticated, emotionally intelligent assistant that provides warm, professional, and contextually aware responses."
            
            claude_chat = LlmChat(
                api_key=self.claude_api_key,
                session_id=session_id,
                system_message=system_message or default_system
            ).with_model("anthropic", "claude-3-5-sonnet-20241022").with_max_tokens(4096)
            
            user_message = UserMessage(text=prompt)
            response = await claude_chat.send_message(user_message)
            return response
            
        except Exception as e:
            logger.error(f"Enhanced Claude API error: {e}")
            return await self._get_groq_response(prompt, system_message)

    async def _get_groq_response(self, prompt: str, system_message: str = None) -> str:
        """Enhanced Groq response with better error handling"""
        try:
            if system_message:
                prompt_template = ChatPromptTemplate.from_messages([
                    ("system", system_message),
                    ("user", "{input}")
                ])
            else:
                prompt_template = ChatPromptTemplate.from_messages([
                    ("user", "{input}")
                ])
            
            chain = prompt_template | self.groq_llm
            response = chain.invoke({"input": prompt})
            return response.content
            
        except Exception as e:
            logger.error(f"Enhanced Groq API error: {e}")
            return "⚠️ I'm experiencing technical difficulties with my reasoning engine. Please try again."

    async def _execute_sequential_routing(self, user_input: str, classification: TaskClassification, session_id: str, full_conversation_context: str = "") -> Tuple[dict, str]:
        """Execute sequential routing: Groq → Claude with content synchronization and full context"""
        logger.info("🔄 Sequential Routing: Groq → Claude (Content Synchronized with Full Context)")
        
        # Step 1: Groq for intent detection and basic structure
        intent_data = await self._groq_intent_detection(user_input)
        
        # Step 2: Claude for content generation with full conversation context
        enhanced_prompt = user_input
        if full_conversation_context:
            enhanced_prompt = f"{full_conversation_context}\n\nCurrent request: {user_input}"
        elif classification.context_dependency != "none":
            enhanced_prompt = await self._get_context_enhanced_prompt(user_input, session_id)
        
        # Generate Claude response with content extraction instructions
        system_message = self._generate_claude_system_message_with_extraction(classification, intent_data)
        claude_response = await self._get_claude_response(enhanced_prompt, system_message)
        
        # Step 3: Extract the actual content from Claude's response and synchronize with intent_data
        synchronized_intent_data = await self._synchronize_content_fields(intent_data, claude_response, classification)
        
        return synchronized_intent_data, claude_response

    def _generate_claude_system_message_with_extraction(self, classification: TaskClassification, intent_data: dict) -> str:
        """Generate system message for Claude with content extraction requirements"""
        base_message = "You are Elva AI – a sophisticated AI assistant."
        
        # Add personality based on classification
        if classification.emotional_complexity == "high":
            base_message += " You are particularly empathetic and emotionally intelligent."
        
        if classification.professional_tone_required:
            base_message += " Maintain a professional yet warm tone in your responses."
        
        if classification.creative_requirement in ["medium", "high"]:
            base_message += " Feel free to be creative and engaging in your responses."
        
        # Add intent-specific guidance with content extraction
        intent = intent_data.get("intent", "general_chat")
        if intent == "send_email":
            base_message += """ 
            
CRITICAL: When drafting emails, structure your response EXACTLY as follows:

✉️ Here's a draft email for [recipient]:

Subject: [exact subject line]
Body: [exact email content that will be used]

The content you write for Subject and Body will be used EXACTLY as written in the approval modal. Make sure the body is complete and ready to send."""
            
        elif intent == "generate_post_prompt_package":
            base_message += """ 
            
CRITICAL: When helping prepare a LinkedIn post prompt package, structure your response EXACTLY as follows:

📝 **Post Description**
[Write this as if YOU achieved what the user accomplished - use FIRST PERSON "I" perspective. Explain to the other AI what you accomplished with enhanced technical context. Examples:

- For "I built a calculator": "I developed a fully functional calculator application using modern web technologies. This project demonstrates my proficiency in JavaScript programming, DOM manipulation, responsive design principles, and user interface development. The calculator includes error handling, memory functions, and clean architecture - showcasing my problem-solving skills and attention to user experience that are highly valued in frontend development roles."

- For "I got certified in cybersecurity": "I successfully completed a cybersecurity certification from Infosys Springboard, a comprehensive program covering network security, threat analysis, ethical hacking, and security protocols. This certification validates my expertise in identifying vulnerabilities, implementing security measures, and understanding compliance frameworks - critical skills in today's digital landscape where cybersecurity professionals are in high demand across all industries."

Write as if YOU accomplished it so the other AI generates a natural first-person LinkedIn post.]

🤖 **AI Instructions**  
[Write direct, specific instructions to the AI that will generate the LinkedIn post. Analyze the user's topic and create tailored commands. Examples:

- For projects: "Write a concise LinkedIn post about the user's [specific project]. Focus on the key technologies used (mention specific languages/frameworks), highlight the challenges you overcame and solutions implemented. Include emojis like 💻🔧🚀 and use hashtags such as #WebDevelopment #JavaScript #ProjectShowcase #Learning."

- For achievements/certificates: "Create a celebratory LinkedIn post about earning [specific certification] from [institution]. Emphasize the key skills gained, mention how this advances their career goals, and express excitement for applying these skills. Use emojis like 🎓🛡️✨ and hashtags like #CertificationEarned #CyberSecurity #ProfessionalGrowth #Learning."

- For career milestones: "Craft a professional announcement about [specific career update]. Express gratitude, highlight relevant skills and experience, show enthusiasm for new opportunities. Include emojis like 🎉💼🌟 and hashtags like #NewBeginnings #CareerGrowth #Grateful #Opportunity."

Make the instructions DIRECT commands to the AI, specific to their exact situation. Include precise emoji and hashtag recommendations.]

DO NOT generate the actual LinkedIn post content. Only provide the enhanced description and direct AI instructions."""
            
        elif intent == "creative_writing":
            base_message += """ 
            
CRITICAL: When creating creative content, provide the exact content that will be used.

✨ Here's your creative content:

[exact content that will be used - make it complete and ready to use]

The content you generate will be used EXACTLY as written in the approval modal."""
            
        elif intent in ["add_todo", "set_reminder"]:
            base_message += " Be encouraging and supportive when helping with task management. Provide clear, actionable descriptions."
        
        return base_message

    async def _synchronize_content_fields(self, intent_data: dict, claude_response: str, classification: TaskClassification) -> dict:
        """Synchronize content fields between Claude response and intent data to ensure unified content"""
        intent = intent_data.get("intent", "general_chat")
        
        try:
            if intent == "send_email":
                # Extract subject and body from Claude's response for perfect synchronization
                subject_match = re.search(r'Subject:\s*(.+)', claude_response)
                # Enhanced body extraction - capture everything after "Body:" until next section or end
                body_match = re.search(r'Body:\s*(.*?)(?:\n\nThe content|$)', claude_response, re.DOTALL)
                
                if subject_match:
                    extracted_subject = subject_match.group(1).strip()
                    intent_data["subject"] = extracted_subject
                    logger.info(f"📧 Subject synchronized: {extracted_subject}")
                    
                if body_match:
                    extracted_body = body_match.group(1).strip()
                    intent_data["body"] = extracted_body
                    logger.info(f"📧 Body synchronized: {len(extracted_body)} characters")
                    
            elif intent == "generate_post_prompt_package":
                # Extract Post Description and AI Instructions from Claude's response
                desc_match = re.search(r'📝.*?Post Description.*?\n+(.*?)(?=🤖|$)', claude_response, re.DOTALL)
                instructions_match = re.search(r'🤖.*?AI Instructions.*?\n+(.*?)(?=DO NOT|$)', claude_response, re.DOTALL)
                
                if desc_match:
                    extracted_desc = desc_match.group(1).strip()
                    intent_data["post_description"] = extracted_desc
                    logger.info(f"📝 Post description extracted: {len(extracted_desc)} characters")
                    
                if instructions_match:
                    extracted_instructions = instructions_match.group(1).strip()
                    intent_data["ai_instructions"] = extracted_instructions
                    logger.info(f"🤖 AI instructions extracted: {len(extracted_instructions)} characters")
                    
            elif intent == "creative_writing":
                # Enhanced LinkedIn post content extraction with multiple fallback patterns
                content_patterns = [
                    # Pattern 1: Content after 📱 emoji with various formats
                    r'📱.*?:\s*\n+(.*?)(?:\n\n(?:This|Feel free|Let me know)|$)',
                    # Pattern 2: Content after "Here's" with various formats  
                    r'Here\'s.*?:\s*\n+(.*?)(?:\n\n(?:This|Feel free|Let me know)|$)',
                    # Pattern 3: Quoted content anywhere in response
                    r'"([^"]{50,})"',  # Look for substantial quoted content (50+ chars)
                    # Pattern 4: Content between blank lines (main content block)
                    r'\n\n([^"]+?)\n\n',
                    # Pattern 5: Everything after first sentence if it's an intro
                    r'^[^.!?]+[.!?]\s*\n+(.*?)(?:\n\nThis|$)',
                ]
                
                extracted_content = None
                for i, pattern in enumerate(content_patterns, 1):
                    match = re.search(pattern, claude_response, re.DOTALL | re.IGNORECASE)
                    if match:
                        candidate_content = match.group(1).strip()
                        # Validate content quality (not just intro text)
                        if len(candidate_content) > 20 and not candidate_content.lower().startswith(('here', 'i\'ve', 'let me')):
                            extracted_content = candidate_content
                            logger.info(f"📱 Pattern {i} matched for {intent}")
                            break
                
                # Final fallback: Extract main content block (skip first line if it's intro)
                if not extracted_content:
                    lines = [line.strip() for line in claude_response.split('\n') if line.strip()]
                    if len(lines) > 1:
                        # Skip intro line, take substantial content
                        content_lines = []
                        start_found = False
                        for line in lines[1:]:  # Skip first line
                            # Stop at explanatory text
                            if any(phrase in line.lower() for phrase in ['this should', 'feel free', 'let me know', 'hope this']):
                                break
                            # Skip emoji lines or short connector lines
                            if len(line) > 10 and not line.startswith('📱') and not line.startswith('✨'):
                                content_lines.append(line)
                                start_found = True
                            elif start_found and line:  # Include short lines within content
                                content_lines.append(line)
                        
                        if content_lines:
                            extracted_content = '\n'.join(content_lines).strip()
                            logger.info(f"📱 Fallback extraction for {intent}")
                
                # Store the unified content
                if extracted_content:
                    # Clean up extracted content
                    extracted_content = extracted_content.replace('""', '"').strip()
                    
                    if intent == "creative_writing":
                        intent_data["content"] = extracted_content
                        logger.info(f"🎯 Creative content unified: {len(extracted_content)} characters")
                else:
                    logger.warning(f"⚠️ Could not extract unified content for {intent}, using original")
                        
            elif intent == "set_reminder":
                # Extract reminder details with better pattern matching
                reminder_patterns = [
                    r'remind you[^"]*"([^"]+)"',
                    r'reminder[^:]*:\s*"([^"]+)"',
                    r'reminder[^:]*:\s*([^"]+?)(?:\n|$)'
                ]
                
                for pattern in reminder_patterns:
                    reminder_match = re.search(pattern, claude_response, re.IGNORECASE)
                    if reminder_match:
                        intent_data["reminder_text"] = reminder_match.group(1).strip()
                        logger.info(f"⏰ Reminder text synchronized")
                        break
                    
            elif intent == "add_todo":
                # Extract task details with better pattern matching
                task_patterns = [
                    r'task[^"]*"([^"]+)"',
                    r'todo[^:]*:\s*"([^"]+)"',
                    r'todo[^:]*:\s*([^"]+?)(?:\n|$)'
                ]
                
                for pattern in task_patterns:
                    task_match = re.search(pattern, claude_response, re.IGNORECASE)
                    if task_match:
                        intent_data["task"] = task_match.group(1).strip()
                        logger.info(f"✅ Task text synchronized")
                        break
            
            logger.info(f"🔗 Content Synchronized: {intent} - All fields unified with Claude response")
            return intent_data
            
        except Exception as e:
            logger.error(f"Content synchronization error: {e}")
            # Return original intent data if synchronization fails
            return intent_data

    def _generate_claude_system_message(self, classification: TaskClassification, intent_data: dict) -> str:
        """Generate contextual system message for Claude based on classification"""
        base_message = "You are Elva AI – a sophisticated AI assistant."
        
        # Add personality based on classification
        if classification.emotional_complexity == "high":
            base_message += " You are particularly empathetic and emotionally intelligent."
        
        if classification.professional_tone_required:
            base_message += " Maintain a professional yet warm tone in your responses."
        
        if classification.creative_requirement in ["medium", "high"]:
            base_message += " Feel free to be creative and engaging in your responses."
        
        # Add intent-specific guidance
        intent = intent_data.get("intent", "general_chat")
        if intent == "send_email":
            base_message += " When drafting emails, focus on clarity, professionalism, and appropriate tone."
        elif intent == "generate_post_prompt_package":
            base_message += " For LinkedIn post preparation, help gather project details and create structured instructions for AI generation."
        elif intent in ["add_todo", "set_reminder"]:
            base_message += " Be encouraging and supportive when helping with task management."
        
        return base_message

    async def _groq_intent_detection(self, user_input: str) -> dict:
        """Groq-specific intent detection with enhanced prompting and pre-processing"""
        
        # Pre-process for common Gmail patterns
        user_input_lower = user_input.lower().strip()
        gmail_patterns = {
            "check my gmail inbox": {"intent": "check_gmail_inbox", "user_email": "brainlyarpit8649@gmail.com", "include_unread_only": False},
            "check my inbox": {"intent": "check_gmail_inbox", "user_email": "brainlyarpit8649@gmail.com", "include_unread_only": False},
            "show me my inbox": {"intent": "check_gmail_inbox", "user_email": "brainlyarpit8649@gmail.com", "include_unread_only": False},
            "check gmail inbox": {"intent": "check_gmail_inbox", "user_email": "brainlyarpit8649@gmail.com", "include_unread_only": False},
            "check my email": {"intent": "check_gmail_inbox", "user_email": "brainlyarpit8649@gmail.com", "include_unread_only": False},
            "show me my emails": {"intent": "check_gmail_inbox", "user_email": "brainlyarpit8649@gmail.com", "include_unread_only": False},
            "any unread emails?": {"intent": "check_gmail_unread", "user_email": "brainlyarpit8649@gmail.com"},
            "show unread emails": {"intent": "check_gmail_unread", "user_email": "brainlyarpit8649@gmail.com"},
            "check unread emails": {"intent": "check_gmail_unread", "user_email": "brainlyarpit8649@gmail.com"}
        }
        
        # Check for exact matches first
        if user_input_lower in gmail_patterns:
            logger.info(f"🎯 Direct Gmail pattern match: {user_input_lower} → {gmail_patterns[user_input_lower]['intent']}")
            return gmail_patterns[user_input_lower]
        
        # Check for partial matches
        for pattern, intent_data in gmail_patterns.items():
            if pattern in user_input_lower or user_input_lower in pattern:
                logger.info(f"🎯 Partial Gmail pattern match: {user_input_lower} contains '{pattern}' → {intent_data['intent']}")
                return intent_data
        
        system_message = """You are an AI assistant specialized in intent detection. Extract structured JSON data.

CRITICAL INSTRUCTIONS:
- Return ONLY valid JSON
- All JSON must be complete and properly formatted  
- For all intents except general_chat, populate ALL fields with realistic content
- PAY SPECIAL ATTENTION TO GMAIL INTENTS - many user phrases should map to Gmail intents

Intent types: send_email, create_event, add_todo, set_reminder, generate_post_prompt_package, web_search, creative_writing, web_research, linkedin_insights, email_automation, data_extraction, check_linkedin_notifications, check_gmail_inbox, check_gmail_unread, email_inbox_check, summarize_gmail_emails, search_gmail_emails, categorize_gmail_emails, gmail_smart_actions, scrape_price, scrape_product_listings, linkedin_job_alerts, check_website_updates, monitor_competitors, scrape_news_articles, get_current_weather, get_weather_forecast, get_air_quality_index, get_weather_alerts, get_sun_times, general_chat

GMAIL INTENT MAPPING (CRITICAL):
"Check my Gmail inbox" → {{"intent": "check_gmail_inbox", "user_email": "brainlyarpit8649@gmail.com", "include_unread_only": false}}
"Check my inbox" → {{"intent": "check_gmail_inbox", "user_email": "brainlyarpit8649@gmail.com", "include_unread_only": false}}
"Show me my inbox" → {{"intent": "check_gmail_inbox", "user_email": "brainlyarpit8649@gmail.com", "include_unread_only": false}}
"check gmail inbox" → {{"intent": "check_gmail_inbox", "user_email": "brainlyarpit8649@gmail.com", "include_unread_only": false}}
"Show unread emails" → {{"intent": "check_gmail_unread", "user_email": "brainlyarpit8649@gmail.com"}}
"Any unread emails?" → {{"intent": "check_gmail_unread", "user_email": "brainlyarpit8649@gmail.com"}}
"Check my email" → {{"intent": "check_gmail_inbox", "user_email": "brainlyarpit8649@gmail.com", "include_unread_only": false}}
"Show me my emails" → {{"intent": "check_gmail_inbox", "user_email": "brainlyarpit8649@gmail.com", "include_unread_only": false}}

Example JSON responses:

Send email: {{"intent": "send_email", "recipient_name": "Name", "subject": "Subject", "body": "Content"}}
Create event: {{"intent": "create_event", "event_title": "Title", "date": "Date", "time": "Time"}}
Add todo: {{"intent": "add_todo", "task": "Task description", "due_date": "Date"}}
Set reminder: {{"intent": "set_reminder", "reminder_text": "Text", "reminder_date": "Date"}}
LinkedIn post: {{"intent": "generate_post_prompt_package", "topic": "Topic", "project_name": "Project name", "project_type": "Type"}}
Web search: {{"intent": "web_search", "query": "search query terms", "search_type": "general"}}
Creative writing: {{"intent": "creative_writing", "content": "Creative content", "topic": "Topic"}}

Web research (SuperAGI): 
Research/trending topics: {{"intent": "web_research", "research_query": "trending AI topics this week", "research_type": "trending_analysis", "focus_area": "artificial intelligence"}}

ENHANCED GMAIL INTENTS (NEW):

Gmail Summarization with Count Limiting:
"Summarize my last 5 emails" → {{"intent": "summarize_gmail_emails", "count": 5, "time_filter": "latest", "include_unread_only": false}}
"Summarize my recent unread emails" → {{"intent": "summarize_gmail_emails", "count": 10, "time_filter": "recent", "include_unread_only": true}}
"Give me a summary of today's emails" → {{"intent": "summarize_gmail_emails", "count": 20, "time_filter": "today", "include_unread_only": false}}

Gmail Search with Natural Language:
"Find emails from John about the project report" → {{"intent": "search_gmail_emails", "sender": "John", "keywords": ["project", "report"], "search_query": "from:John project report", "max_results": 10}}
"Show me emails from last week about meetings" → {{"intent": "search_gmail_emails", "time_filter": "last_week", "keywords": ["meeting", "meetings"], "search_query": "meeting", "max_results": 15}}
"Search for emails with attachments from Sarah" → {{"intent": "search_gmail_emails", "sender": "Sarah", "has_attachment": true, "search_query": "from:Sarah has:attachment", "max_results": 10}}

Gmail Categorization:
"Categorize my emails" → {{"intent": "categorize_gmail_emails", "categories": ["work", "personal", "promotions", "social", "important"], "count": 20, "time_filter": "recent"}}
"Show me work emails vs personal emails" → {{"intent": "categorize_gmail_emails", "categories": ["work", "personal"], "count": 15, "focus_categories": ["work", "personal"]}}

Gmail Smart Actions (needs approval):
"Mark my last 3 promotional emails as read" → {{"intent": "gmail_smart_actions", "action": "mark_as_read", "target_count": 3, "email_category": "promotions", "confirmation_required": true}}
"Archive all emails from newsletters" → {{"intent": "gmail_smart_actions", "action": "archive", "target_filter": "newsletters", "confirmation_required": true}}
"Reply to Sarah's latest email" → {{"intent": "gmail_smart_actions", "action": "reply", "target_sender": "Sarah", "target_count": 1, "confirmation_required": true}}

Web automation (traditional - only for specific URL scraping): 
LinkedIn insights: {{"intent": "linkedin_insights", "insight_type": "notifications/profile_views/connections", "email": "linkedin_email", "password": "password"}}
Email automation: {{"intent": "email_automation", "provider": "outlook/yahoo/gmail", "email": "email", "password": "password", "action": "check_inbox/send_email"}}

Data extraction: {{"intent": "data_extraction", "url": "URL", "data_fields": ["field1", "field2"], "selectors": {{"field": "selector"}}}}

Direct automation (no approval needed):
Check LinkedIn notifications: {{"intent": "check_linkedin_notifications", "account_type": "personal/business"}}
Check Gmail inbox: {{"intent": "check_gmail_inbox", "user_email": "brainlyarpit8649@gmail.com", "include_unread_only": false}}
Check Gmail unread: {{"intent": "check_gmail_unread", "user_email": "brainlyarpit8649@gmail.com"}}
Email inbox check: {{"intent": "email_inbox_check", "user_email": "brainlyarpit8649@gmail.com", "check_type": "unread"}}
Scrape price: {{"intent": "scrape_price", "product": "product name", "platform": "amazon/flipkart/ebay", "search_query": "search terms"}}
Scrape product listings: {{"intent": "scrape_product_listings", "category": "category", "platform": "website", "filters": {{"price_range": "range", "brand": "brand"}}}}
LinkedIn job alerts: {{"intent": "linkedin_job_alerts", "job_title": "title", "location": "location"}}
Check website updates: {{"intent": "check_website_updates", "website": "website_name", "section": "section to monitor"}}
Monitor competitors: {{"intent": "monitor_competitors", "company": "company_name", "data_type": "pricing/products/news"}}
Scrape news articles: {{"intent": "scrape_news_articles", "topic": "news topic", "source": "news source"}}

WEATHER INTENTS:
Current weather: {{"intent": "get_current_weather", "location": "location name"}}
Weather forecast: {{"intent": "get_weather_forecast", "location": "location name", "days": 3}}  
Air quality: {{"intent": "get_air_quality_index", "location": "location name"}}
Weather alerts: {{"intent": "get_weather_alerts", "location": "location name"}}
Sun times: {{"intent": "get_sun_times", "location": "location name"}}

WEATHER EXAMPLES:
"What's the weather in Paris?" → {{"intent": "get_current_weather", "location": "Paris"}}
"Current weather in Delhi" → {{"intent": "get_current_weather", "location": "Delhi"}}
"How hot is it in Mumbai right now?" → {{"intent": "get_current_weather", "location": "Mumbai"}}
"Is it raining in London?" → {{"intent": "get_current_weather", "location": "London"}}
"Weather update for New York" → {{"intent": "get_current_weather", "location": "New York"}}
"Forecast for London tomorrow" → {{"intent": "get_weather_forecast", "location": "London", "days": 1}}
"7-day weather in Tokyo" → {{"intent": "get_weather_forecast", "location": "Tokyo", "days": 7}}
"What's the weather this weekend in Goa?" → {{"intent": "get_weather_forecast", "location": "Goa", "days": 3}}
"Will it rain tomorrow in Dubai?" → {{"intent": "get_weather_forecast", "location": "Dubai", "days": 1}}
"Next 3 days weather in Sydney" → {{"intent": "get_weather_forecast", "location": "Sydney", "days": 3}}
"Air quality in Delhi today" → {{"intent": "get_air_quality_index", "location": "Delhi"}}
"Is it safe to jog outside in Beijing?" → {{"intent": "get_air_quality_index", "location": "Beijing"}}
"AQI in Los Angeles right now" → {{"intent": "get_air_quality_index", "location": "Los Angeles"}}
"Are there any weather warnings in Miami?" → {{"intent": "get_weather_alerts", "location": "Miami"}}
"Storm alerts for Florida" → {{"intent": "get_weather_alerts", "location": "Florida"}}
"Is there a heatwave alert in Madrid?" → {{"intent": "get_weather_alerts", "location": "Madrid"}}
"When is sunrise in Paris today?" → {{"intent": "get_sun_times", "location": "Paris"}}
"Sunset time in San Francisco" → {{"intent": "get_sun_times", "location": "San Francisco"}}

General chat: {{"intent": "general_chat", "message": "original message"}}

Return ONLY the JSON object."""

        try:
            response = await self._get_groq_response(user_input, system_message)
            
            # Enhanced JSON extraction
            content = response.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx + 1]
                return json.loads(json_str)
            else:
                return {"intent": "general_chat", "message": user_input}
                
        except Exception as e:
            logger.error(f"Enhanced intent detection error: {e}")
            return {"intent": "general_chat", "message": user_input, "error": str(e)}

    async def process_message(self, user_input: str, session_id: str, memory_context: str = "") -> Tuple[dict, str, RoutingDecision]:
        """
        Enhanced message processing with conversation memory integration.
        
        Args:
            user_input: User's input message
            session_id: Session identifier for context retrieval
            memory_context: Conversation context from enhanced Redis+MongoDB hybrid system
            
        Returns:
            Tuple of (intent_data, response_text, routing_decision)
        """
        logger.info(f"🚀 Processing message with enhanced conversation context: {user_input[:50]}...")
        
        try:
            # PRIORITY 1: Use enhanced memory context passed from server.py
            full_conversation_context = ""
            if memory_context:
                full_conversation_context = memory_context
                logger.info(f"💾 Using enhanced Redis+MongoDB conversation context ({len(memory_context)} chars)")
            else:
                logger.warning("⚠️ No enhanced memory context provided - responses may lack conversational continuity")
            
            # Add MCP context for additional context with timeout protection
            try:
                mcp_service = get_mcp_service()
                mcp_context = await asyncio.wait_for(
                    mcp_service.get_context_for_prompt(session_id),
                    timeout=10.0
                )
                if mcp_context:
                    full_conversation_context += f"\n\n=== ADDITIONAL MCP CONTEXT ===\n{mcp_context}"
                    logger.info(f"📚 Added MCP context to conversation memory")
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Timeout retrieving MCP context for session {session_id}")
            except Exception as e:
                logger.warning(f"Could not retrieve MCP context: {e}")
            
            # Step 1: Analyze task classification
            classification = await self.analyze_task_classification(user_input, session_id)
            
            # Step 2: Check for direct automation intents first
            # Get intent quickly to check if it needs direct automation
            try:
                quick_intent_data = await self._groq_intent_detection(user_input)
                quick_intent = quick_intent_data.get("intent", "general_chat")
                
                # Handle direct automation intents immediately
                if self.is_direct_automation_intent(quick_intent):
                    logger.info(f"🤖 Direct automation intent detected: {quick_intent}")
                    
                    # Import and use direct automation handler
                    try:
                        from direct_automation_handler import direct_automation_handler
                        automation_result = await direct_automation_handler.process_direct_automation(
                            quick_intent_data, 
                            session_id, 
                            username=None, 
                            conversation_context=full_conversation_context
                        )
                        
                        if automation_result["success"]:
                            response_text = automation_result["message"]
                            intent_data = quick_intent_data
                            intent_data.update({
                                "automation_success": True,
                                "execution_time": automation_result["execution_time"],
                                "automation_data": automation_result["data"]
                            })
                            
                            # Create simple routing decision for direct automation
                            routing_decision = RoutingDecision(
                                primary_model=ModelChoice.GROQ,
                                confidence=0.95,
                                reasoning=f"Direct automation for {quick_intent} - no AI generation needed"
                            )
                            
                            logger.info(f"✅ Direct automation completed: {quick_intent} in {automation_result['execution_time']:.2f}s")
                            return intent_data, response_text, routing_decision
                        else:
                            # Automation failed, provide error response
                            response_text = automation_result["message"]
                            intent_data = quick_intent_data
                            intent_data.update({
                                "automation_success": False,
                                "automation_error": automation_result["message"]
                            })
                            
                            routing_decision = RoutingDecision(
                                primary_model=ModelChoice.GROQ,
                                confidence=0.8,
                                reasoning=f"Direct automation failed for {quick_intent} - returning error message"
                            )
                            
                            logger.warning(f"❌ Direct automation failed: {quick_intent} - {automation_result['message']}")
                            return intent_data, response_text, routing_decision
                            
                    except Exception as automation_error:
                        logger.error(f"Direct automation handler error: {automation_error}")
                        # Continue with normal AI processing as fallback
                        
            except Exception as quick_intent_error:
                logger.warning(f"Quick intent detection failed: {quick_intent_error}")
                # Continue with normal processing
            
            # Step 3: Advanced task classification with context (for non-direct automation intents)
            classification = await self.analyze_task_classification(user_input, session_id)
            
            # Step 4: Calculate routing decision
            
            # Step 4: Calculate routing decision
            routing_decision = self._calculate_routing_decision(classification, session_id)
            
            # Step 5: Update conversation history
            self._update_conversation_history(session_id, user_input, classification)
            
            logger.info(f"🧠 Classification: {classification.primary_intent} | Routing: {routing_decision.primary_model.value} | Confidence: {routing_decision.confidence:.2f}")
            logger.info(f"💡 Reasoning: {routing_decision.reasoning}")
            
            # Step 6: Execute routing decision with FULL conversation context
            try:
                # All routing now goes to Groq - simplified logic
                intent_data = await self._groq_intent_detection(user_input)
                
                if intent_data.get("intent") == "general_chat":
                    # For general chat, use Groq with enhanced conversational prompt
                    enhanced_prompt = user_input
                    if full_conversation_context:
                        enhanced_prompt = f"{full_conversation_context}\n\nCurrent request: {user_input}"
                    
                    # Create a conversational system message for Groq
                    conversational_system = """You are Elva AI, a warm, friendly, and helpful assistant. 

Respond naturally and conversationally. Be human-like, engaging, and show personality. 
Avoid robotic responses. If someone greets you or asks how you are, respond warmly.
Keep responses concise but friendly. Use emojis occasionally to be more expressive.
Always maintain context from previous conversation."""
                    
                    response_text = await self._get_groq_response(enhanced_prompt, conversational_system)
                else:
                    # For other intents, use standard Groq processing but make it friendly
                    response_text = await self._get_groq_response(
                        f"Please respond to this request in a helpful and friendly way: {user_input}",
                        "You are Elva AI, a helpful and friendly assistant. Respond naturally and conversationally."
                    )
                
                # Step 7: Store conversation context in MCP
                try:
                    mcp_service = get_mcp_service()
                    context_data = mcp_service.prepare_context_data(
                        user_input, response_text, intent_data, 
                        routing_info={
                            "model_used": routing_decision.primary_model.value,
                            "confidence": routing_decision.confidence,
                            "reasoning": routing_decision.reasoning
                        }
                    )
                    await mcp_service.write_context(
                        session_id=session_id,
                        intent=intent_data.get("intent", "general_chat"),
                        data=context_data
                    )
                    logger.info(f"💾 Stored conversation context in MCP for session: {session_id}")
                except Exception as e:
                    logger.warning(f"Could not store conversation context in MCP: {e}")
                
                return intent_data, response_text, routing_decision
                
            except Exception as e:
                logger.error(f"Processing error: {e}")
                # Fallback to Groq with friendly response
                try:
                    intent_data = await self._groq_intent_detection(user_input) 
                    response_text = await self._get_groq_response(
                        user_input,
                        "You are Elva AI, a helpful and friendly assistant. Respond naturally and conversationally."
                    )
                    
                    # Store fallback conversation in MCP
                    try:
                        mcp_service = get_mcp_service()
                        context_data = mcp_service.prepare_context_data(user_input, response_text, intent_data)
                        await mcp_service.write_context(
                            session_id=session_id,
                            intent=intent_data.get("intent", "general_chat"),
                            data=context_data
                        )
                    except Exception as mem_e:
                        logger.warning(f"Could not store fallback conversation in MCP: {mem_e}")
                    
                    return intent_data, response_text, routing_decision
                except Exception as fallback_error:
                    logger.error(f"Fallback error: {fallback_error}")
                
                # Ultimate fallback
                return (
                    {"intent": "general_chat", "message": user_input, "error": str(e)},
                    "I apologize, but I encountered an error processing your request. Please try again.",
                    RoutingDecision(ModelChoice.CLAUDE, 0.5, "Error fallback")
                )
                
        except Exception as e:
            logger.error(f"Critical processing error: {e}")
            return (
                {"intent": "general_chat", "message": user_input, "error": str(e)},
                "I apologize, but I encountered a critical error. Please try again.",
                RoutingDecision(ModelChoice.CLAUDE, 0.5, "Critical error fallback")
            )

    def get_routing_stats(self, session_id: str) -> dict:
        """Get routing statistics for this session"""
        if session_id not in self.conversation_history:
            return {"total_messages": 0, "routing_decisions": []}
            
        history = self.conversation_history[session_id]
        return {
            "total_messages": len(history),
            "recent_classifications": [
                {
                    "intent": h["classification"].primary_intent,
                    "emotional_complexity": h["classification"].emotional_complexity,
                    "professional_tone": h["classification"].professional_tone_required
                } for h in history[-5:]  # Last 5 messages
            ]
        }

# Global instance
advanced_hybrid_ai = AdvancedHybridAI()

# Compatibility functions for existing API
async def detect_intent(user_input: str) -> dict:
    """Enhanced intent detection with sophisticated routing"""
    session_id = "legacy_session"  # For backward compatibility
    intent_data, _, routing_decision = await advanced_hybrid_ai.process_message(user_input, session_id)
    
    # Add routing metadata
    intent_data["_routing_info"] = {
        "model_used": routing_decision.primary_model.value,
        "confidence": routing_decision.confidence,
        "reasoning": routing_decision.reasoning
    }
    
    return intent_data

async def generate_friendly_draft(intent_data: dict) -> str:
    """Enhanced draft generation with contextual awareness"""
    session_id = "legacy_session"
    
    # Create a mock user input from intent data
    user_input = f"Generate a friendly response for: {intent_data.get('intent', 'general task')}"
    
    # Use the advanced system
    _, response_text, _ = await advanced_hybrid_ai.process_message(user_input, session_id)
    return response_text

async def handle_general_chat(user_input: str) -> str:
    """Enhanced general chat with emotional intelligence"""
    session_id = "legacy_session"
    _, response_text, _ = await advanced_hybrid_ai.process_message(user_input, session_id)
    return response_text

def format_intent_for_webhook(intent_data: dict, user_id: str, session_id: str) -> dict:
    """Format intent data for webhook"""
    from datetime import datetime
    return {
        "user_id": user_id,
        "session_id": session_id,
        "intent": intent_data.get("intent"),
        "data": intent_data,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "routing_info": intent_data.get("_routing_info", {})
    }