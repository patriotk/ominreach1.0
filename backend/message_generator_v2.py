"""
AI Message Generator V2
Generates personalized messages per lead, per step
Uses multi-source context
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv()
logger = logging.getLogger(__name__)


class MessageGeneratorV2:
    """Generate personalized messages using GPT-5"""
    
    def __init__(self):
        self.api_key = os.getenv("EMERGENT_LLM_KEY")
        if not self.api_key:
            raise ValueError("EMERGENT_LLM_KEY not found")
    
    async def generate_message(
        self,
        lead: Dict[str, Any],
        campaign_type: str,
        step_number: int,
        product_info: Dict[str, Any],
        step_agent_settings: Dict[str, Any],
        step_best_practices: Optional[str],
        previous_message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a single message for a lead at a specific step
        
        Args:
            lead: Lead data (name, title, company, persona)
            campaign_type: "email" or "linkedin"
            step_number: 1, 2, or 3
            product_info: Product context
            step_agent_settings: Tone, style, focus, etc.
            step_best_practices: Step-specific guidelines
            previous_message: Content from previous step (for steps 2 & 3)
        
        Returns:
            Dict with subject, content, ai_score, reasoning
        """
        try:
            # Build context prompt
            prompt = self._build_prompt(
                lead=lead,
                campaign_type=campaign_type,
                step_number=step_number,
                product_info=product_info,
                agent_settings=step_agent_settings,
                best_practices=step_best_practices,
                previous_message=previous_message
            )
            
            # Initialize LLM chat
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"msg-gen-{lead.get('id', 'unknown')}-step{step_number}",
                system_message="You are an expert outreach message writer."
            ).with_model("openai", "gpt-5")
            
            # Generate
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            # Parse JSON response
            result = self._parse_response(response)
            
            if result:
                logger.info(f"Generated message for lead {lead.get('name')} - Step {step_number}")
                return result
            else:
                logger.error("Failed to parse AI response")
                return None
                
        except Exception as e:
            logger.error(f"Message generation error: {str(e)}")
            return None
    
    def _build_prompt(
        self,
        lead: Dict[str, Any],
        campaign_type: str,
        step_number: int,
        product_info: Dict[str, Any],
        agent_settings: Dict[str, Any],
        best_practices: Optional[str],
        previous_message: Optional[str]
    ) -> str:
        """Build the GPT-5 prompt with all context"""
        
        # Format product info
        product_context = f"""Product: {product_info.get('product_name', 'N/A')}
Summary: {product_info.get('summary', 'N/A')}
Features: {', '.join(product_info.get('features', []))}
Differentiators: {', '.join(product_info.get('differentiators', []))}
CTA: {product_info.get('call_to_action', 'N/A')}"""
        
        # Format best practices
        practices = best_practices if best_practices else "Use best judgment for professional outreach."
        
        # Format previous message
        prev_msg = previous_message if previous_message else "N/A (This is the first message)"
        
        prompt = f"""You are an AI outreach assistant that writes highly personalized, step-specific campaign messages.

---

### PRODUCT INFORMATION
{product_context}

### STEP BEST PRACTICES
{practices}

### AGENT PROFILE
Tone: {agent_settings.get('tone', 'professional')}
Style: {agent_settings.get('style', 'concise')}
Focus: {agent_settings.get('focus', 'value-driven')}
Avoid Words: {', '.join(agent_settings.get('avoid_words', []))}
Brand Personality: {agent_settings.get('brand_personality', 'N/A')}

### LEAD PERSONA
Name: {lead.get('name', 'Unknown')}
Title: {lead.get('title', 'N/A')}
Company: {lead.get('company', 'N/A')}
Persona Summary: {lead.get('persona', 'Professional contact')}

### PREVIOUS MESSAGE
{prev_msg}

---

### OBJECTIVE
Write a {campaign_type} message for **Step {step_number}** that:
- Aligns with the product value and persona's needs
- Follows the provided best practices for this step
- Reflects the tone, style, and brand personality
- Feels natural and tailored, not templated
- Ends with a clear, low-friction call to action

{"- For Step " + str(step_number) + ": " + self._get_step_guidance(step_number) if step_number > 1 else ""}

Return valid JSON only:

{{
  "subject": "(only if email, otherwise empty string)",
  "body": "(final personalized message with {{{{first_name}}}}, {{{{company}}}}, {{{{job_title}}}} tokens)",
  "tone_used": "",
  "ai_score": {{
    "clarity": 0-10,
    "personalization": 0-10,
    "relevance": 0-10,
    "total": "average of above"
  }},
  "reasoning": "2-3 sentences explaining why this message fits the persona and step"
}}"""

        return prompt
    
    def _get_step_guidance(self, step_number: int) -> str:
        """Step-specific guidance"""
        guidance = {
            1: "This is the first contact. Focus on introducing value and building curiosity.",
            2: "This is a follow-up. Reference the previous message, add new insight, and re-engage.",
            3: "This is the final attempt. Be direct, acknowledge previous messages, and provide a clear next step or graceful exit."
        }
        return guidance.get(step_number, "")
    
    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from AI"""
        try:
            # Clean response
            response_text = response.strip()
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
            
            # Parse JSON
            data = json.loads(response_text)
            
            # Validate required fields
            required = ["body", "ai_score"]
            for field in required:
                if field not in data:
                    logger.warning(f"Missing field: {field}")
                    return None
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Raw response: {response}")
            return None
