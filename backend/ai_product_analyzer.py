"""
AI Product Analyzer Service
Extracts structured product information from document text using GPT-5
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv()
logger = logging.getLogger(__name__)

PRODUCT_ANALYSIS_PROMPT = """You are a product marketing assistant that analyzes product or service documents
to extract concise, structured marketing data.

From the document text below, extract and summarize the following fields:

1. product_name — Name of the product or service.
2. product_summary — 1–2 sentence overview describing what it does and its value.
3. key_differentiators — Three concise bullet points that describe what makes it unique.
4. call_to_action — A single, natural sentence inviting the reader to take the next step.
5. main_features — Up to five short bullets of core capabilities (if identifiable).

Return **only valid JSON** in this exact format:

{
  "product_name": "",
  "product_summary": "",
  "key_differentiators": ["", "", ""],
  "call_to_action": "",
  "main_features": ["", "", "", "", ""]
}

Document text:
{{extracted_text}}"""


class AIProductAnalyzer:
    """Analyze product documents and extract structured information using AI"""
    
    def __init__(self):
        self.api_key = os.getenv("EMERGENT_LLM_KEY")
        if not self.api_key:
            raise ValueError("EMERGENT_LLM_KEY not found in environment")
    
    async def analyze_product_document(self, extracted_text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze product document text and return structured product information
        
        Args:
            extracted_text: Raw text extracted from PDF/DOCX (first 10k chars)
        
        Returns:
            Dict with product_name, product_summary, key_differentiators, 
            call_to_action, main_features
        """
        try:
            # Limit text to 10k characters
            text_to_analyze = extracted_text[:10000]
            
            # Build prompt with extracted text
            prompt = PRODUCT_ANALYSIS_PROMPT.replace("{{extracted_text}}", text_to_analyze)
            
            # Initialize LLM chat
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"product-analysis-{hash(text_to_analyze[:100])}",
                system_message="You are a product marketing assistant that extracts structured data from documents."
            ).with_model("openai", "gpt-5")
            
            # Create user message
            user_message = UserMessage(text=prompt)
            
            # Get AI response
            response = await chat.send_message(user_message)
            
            # Parse JSON response
            try:
                # The response might be wrapped in markdown code blocks
                response_text = response.strip()
                if response_text.startswith("```json"):
                    response_text = response_text.replace("```json", "").replace("```", "").strip()
                elif response_text.startswith("```"):
                    response_text = response_text.replace("```", "").strip()
                
                product_data = json.loads(response_text)
                
                # Validate required fields
                required_fields = ["product_name", "product_summary", "key_differentiators", 
                                 "call_to_action", "main_features"]
                for field in required_fields:
                    if field not in product_data:
                        logger.warning(f"Missing field in AI response: {field}")
                        product_data[field] = "" if field != "key_differentiators" and field != "main_features" else []
                
                logger.info(f"Successfully analyzed product document: {product_data.get('product_name', 'Unknown')}")
                return product_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(f"Raw response: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing product document: {str(e)}")
            return None
    
    async def generate_enhanced_message(
        self,
        product_info: str,
        step_best_practices: str,
        agent_profile: Dict[str, Any],
        lead: Dict[str, Any],
        previous_message: str,
        campaign_type: str,
        step_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Generate personalized message using multi-source context
        
        Returns:
            Dict with subject, body, tone_used, ai_score, reasoning
        """
        try:
            # Build context prompt
            prompt = f"""You are an AI outreach assistant that writes highly personalized, 
step-specific campaign messages using the materials provided below.

---

### PRODUCT INFORMATION
{product_info}

### STEP BEST PRACTICES
{step_best_practices}

### AGENT PROFILE
Tone: {agent_profile.get('tone', 'professional')}
Style: {agent_profile.get('style', 'concise')}
Focus: {agent_profile.get('focus', 'value-driven')}
Avoid Words: {', '.join(agent_profile.get('avoid_words', []))}
Brand Personality: {agent_profile.get('brand_personality', 'N/A')}

### LEAD PERSONA
Name: {lead.get('name', 'Unknown')}
Title: {lead.get('title', 'N/A')}
Company: {lead.get('company', 'N/A')}
Persona Summary: {lead.get('persona_summary', 'N/A')}

### PREVIOUS MESSAGE
{previous_message if previous_message else 'N/A (First message in sequence)'}

---

### OBJECTIVE
Write a {campaign_type} message for **Step {step_number}** that:
- Aligns with the product value and persona's needs.
- Follows the provided best practices for this step.
- Reflects the tone, style, and brand personality.
- Feels natural and tailored, not templated.
- Ends with a clear, low-friction call to action.

Return valid JSON only:

{{
  "subject": "(optional if email)",
  "body": "(final personalized message)",
  "tone_used": "",
  "ai_score": {{
    "clarity": 0-10,
    "personalization": 0-10,
    "relevance": 0-10,
    "total": "average of above"
  }},
  "reasoning": "2–3 sentences explaining why this message fits the persona and step"
}}"""

            # Initialize LLM chat
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"message-gen-{lead.get('id', 'unknown')}-step{step_number}",
                system_message="You are an expert outreach message writer."
            ).with_model("openai", "gpt-5")
            
            # Create user message
            user_message = UserMessage(text=prompt)
            
            # Get AI response
            response = await chat.send_message(user_message)
            
            # Parse JSON response
            try:
                response_text = response.strip()
                if response_text.startswith("```json"):
                    response_text = response_text.replace("```json", "").replace("```", "").strip()
                elif response_text.startswith("```"):
                    response_text = response_text.replace("```", "").strip()
                
                message_data = json.loads(response_text)
                
                logger.info(f"Generated message for lead {lead.get('name', 'Unknown')} - Step {step_number}")
                return message_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse message generation response as JSON: {e}")
                logger.error(f"Raw response: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating enhanced message: {str(e)}")
            return None
