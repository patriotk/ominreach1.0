import os
import json
import logging
from typing import Dict, Any, List
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)

class AIMessageGenerator:
    """Advanced AI message generator with agent profiles and scoring"""
    
    def __init__(self, llm_key: str):
        self.llm_key = llm_key
    
    async def generate_message_with_scoring(
        self,
        lead_data: Dict,
        product_info: Dict,
        step_config: Dict,
        agent_profile: Dict,
        campaign_type: str
    ) -> Dict[str, Any]:
        """
        Generate message with AI scoring
        """
        
        # Build comprehensive prompt
        prompt = self._build_generation_prompt(
            lead_data,
            product_info,
            step_config,
            agent_profile,
            campaign_type
        )
        
        # Use configured model
        provider = agent_profile.get("model_provider", "openai")
        model = agent_profile.get("model_name", "gpt-5")
        temperature = agent_profile.get("temperature", 0.7)
        
        chat = LlmChat(
            api_key=self.llm_key,
            session_id=f"msg-gen-{lead_data['id']}",
            system_message="You are an expert B2B outreach specialist. Generate personalized, effective messages with detailed scoring."
        ).with_model(provider, model)
        
        message_obj = UserMessage(text=prompt)
        response = await chat.send_message(message_obj)
        
        # Parse JSON response
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            # Fallback if not valid JSON
            logger.error(f"Invalid JSON from AI: {response[:200]}")
            return {
                "subject": "Outreach message",
                "body": response,
                "reasoning": "Could not parse AI response",
                "clarity_score": 5.0,
                "personalization_score": 5.0,
                "relevance_score": 5.0
            }
    
    def _build_generation_prompt(
        self,
        lead_data: Dict,
        product_info: Dict,
        step_config: Dict,
        agent_profile: Dict,
        campaign_type: str
    ) -> str:
        """
        Build comprehensive generation prompt
        """
        
        lead_name = lead_data.get("leadName", "")
        lead_persona = lead_data.get("leadPersona", "")
        company = lead_data.get("company", "")
        job_title = lead_data.get("job_title", "")
        
        product_name = product_info.get("name", "")
        product_summary = product_info.get("summary", "")
        differentiators = product_info.get("differentiators", "")
        
        step_number = step_config.get("step_number", 1)
        step_purpose = step_config.get("purpose", "")
        best_practices = step_config.get("best_practices", "")
        
        tone = agent_profile.get("tone", "professional")
        style = agent_profile.get("style", "medium")
        focus = agent_profile.get("focus", "value_driven")
        avoid_words = agent_profile.get("avoid_words", [])
        brand_personality = agent_profile.get("brand_personality", "")
        
        length_guide = {
            "short": "50-100 words",
            "medium": "100-150 words",
            "long": "150-200 words"
        }
        
        prompt = f"""Generate a personalized {campaign_type} outreach message for Step {step_number}.

=== LEAD INFORMATION ===
Name: {lead_name}
Persona: {lead_persona}
Company: {company}
Title: {job_title}

=== PRODUCT INFORMATION ===
Product: {product_name}
Summary: {product_summary}
Key Differentiators: {differentiators}

=== STEP CONFIGURATION ===
Step {step_number} Purpose: {step_purpose}
Best Practices: {best_practices}

=== AI AGENT PROFILE ===
Tone: {tone}
Style: {style} ({length_guide.get(style, '100-150 words')})
Focus: {focus}
Brand Personality: {brand_personality}
{'Avoid these words: ' + ', '.join(avoid_words) if avoid_words else ''}

=== INSTRUCTIONS ===
1. Use the lead's persona to tailor message tone and content
2. Highlight product benefits most relevant to their role
3. Match the {tone} tone and {style} style
4. Focus on {focus}
5. Follow the step's best practices
6. Use personalization tokens: {{{{first_name}}}}, {{{{company}}}}, {{{{job_title}}}}
7. {'For email: Include compelling subject line' if campaign_type == 'email' else 'LinkedIn message only'}

=== OUTPUT FORMAT (JSON ONLY) ===
{{
  "subject": "compelling subject line" (email only),
  "body": "personalized message body with tokens",
  "reasoning": "why this approach works for this persona",
  "clarity_score": 0-10 (how clear and easy to understand),
  "personalization_score": 0-10 (how well tailored to the lead),
  "relevance_score": 0-10 (how relevant product is to their needs)
}}

Generate the message now:"""
        
        return prompt
