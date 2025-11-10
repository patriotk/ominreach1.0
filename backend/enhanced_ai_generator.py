import os
import json
import logging
from typing import Dict, Any, List, Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)

class EnhancedAIMessageGenerator:
    """Advanced AI message generator with agent profiles and comprehensive scoring"""
    
    def __init__(self, llm_key: str):
        self.llm_key = llm_key
    
    async def generate_message_with_scoring(
        self,
        lead_data: Dict[str, Any],
        product_info: Dict[str, Any],
        step_config: Dict[str, Any],
        agent_profile: Dict[str, Any],
        campaign_type: str
    ) -> Dict[str, Any]:
        """
        Generate message with comprehensive AI scoring
        
        Returns:
            {
                "subject": str,
                "body": str,
                "reasoning": str,
                "clarity_score": float,
                "personalization_score": float,
                "relevance_score": float,
                "total_score": float
            }
        """
        
        prompt = self._build_comprehensive_prompt(
            lead_data,
            product_info,
            step_config,
            agent_profile,
            campaign_type
        )
        
        # Use agent's model configuration
        provider = agent_profile.get("model_provider", "openai")
        model = agent_profile.get("model_name", "gpt-5")
        temperature = agent_profile.get("temperature", 0.7)
        
        chat = LlmChat(
            api_key=self.llm_key,
            session_id=f"enhanced-msg-{lead_data.get('id', 'unknown')}",
            system_message="You are an expert B2B outreach specialist. Generate personalized, scored messages in valid JSON format."
        ).with_model(provider, model)
        
        message_obj = UserMessage(text=prompt)
        response = await chat.send_message(message_obj)
        
        # Parse JSON response
        try:
            result = json.loads(response)
            
            # Calculate total score
            clarity = float(result.get("clarity_score", 5.0))
            personalization = float(result.get("personalization_score", 5.0))
            relevance = float(result.get("relevance_score", 5.0))
            total = round((clarity + personalization + relevance) / 3, 2)
            
            result["total_score"] = total
            
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from AI: {response[:200]}")
            # Return fallback
            return {
                "subject": "Personalized outreach" if campaign_type == "email" else None,
                "body": response,
                "reasoning": "AI response could not be parsed as JSON",
                "clarity_score": 5.0,
                "personalization_score": 5.0,
                "relevance_score": 5.0,
                "total_score": 5.0
            }
    
    def _build_comprehensive_prompt(
        self,
        lead_data: Dict[str, Any],
        product_info: Dict[str, Any],
        step_config: Dict[str, Any],
        agent_profile: Dict[str, Any],
        campaign_type: str
    ) -> str:
        """
        Build comprehensive generation prompt with all context
        """
        
        # Extract lead info
        lead_name = lead_data.get("leadName", lead_data.get("name", ""))
        lead_persona = lead_data.get("leadPersona", lead_data.get("persona", ""))
        company = lead_data.get("company", "")
        job_title = lead_data.get("job_title", lead_data.get("title", ""))
        
        # Extract product info
        product_name = product_info.get("name", "")
        product_summary = product_info.get("summary", "")
        differentiators = product_info.get("differentiators", "")
        parsed_content = product_info.get("parsed_content", "")
        
        # Extract step config
        step_number = step_config.get("step_number", 1)
        step_name = step_config.get("step_name", f"Step {step_number}")
        purpose = step_config.get("purpose", "")
        best_practices = step_config.get("best_practices", "")
        
        # Extract agent profile
        tone = agent_profile.get("tone", "professional")
        style = agent_profile.get("style", "medium")
        focus = agent_profile.get("focus", "value_driven")
        avoid_words = agent_profile.get("avoid_words", [])
        brand_personality = agent_profile.get("brand_personality", "")
        
        # Length guidelines
        length_map = {
            "short": "50-100 words, 2-3 sentences",
            "medium": "100-150 words, 3-4 sentences",
            "long": "150-200 words, 4-5 sentences"
        }
        length_guide = length_map.get(style, "100-150 words")
        
        prompt = f"""Generate a personalized {campaign_type} outreach message for {step_name}.

=== LEAD INFORMATION ===
Name: {lead_name}
Persona: {lead_persona}
Company: {company}
Title: {job_title}

=== PRODUCT INFORMATION ===
Product: {product_name}
Summary: {product_summary}
Key Differentiators: {differentiators}
{f'Additional Context: {parsed_content[:500]}' if parsed_content else ''}

=== STEP CONFIGURATION ===
Step {step_number}: {step_name}
Purpose: {purpose}
Best Practices: {best_practices}

=== AI AGENT PROFILE ===
Agent Tone: {tone}
Message Style: {style} ({length_guide})
Focus: {focus}
Brand Personality: {brand_personality}
{'Avoid these words: ' + ', '.join(avoid_words) if avoid_words else ''}

=== GENERATION INSTRUCTIONS ===
1. Analyze the lead's persona to understand their communication preferences
2. Highlight product benefits most relevant to their role and challenges
3. Match the {tone} tone throughout the message
4. Keep message length to {length_guide}
5. Focus on {focus}
6. Follow the step's best practices exactly
7. Use personalization tokens: {{{{first_name}}}}, {{{{company}}}}, {{{{job_title}}}}
8. {'Create a compelling subject line' if campaign_type == 'email' else 'Focus on message body only'}
9. Be specific and avoid generic phrases
10. Make it feel natural and conversational

=== SCORING CRITERIA ===
After generating the message, score it on:
- Clarity (0-10): How clear and easy to understand is the message?
- Personalization (0-10): How well is it tailored to this specific lead's persona and role?
- Relevance (0-10): How relevant is the product/value proposition to their needs?

=== OUTPUT FORMAT (STRICT JSON) ===
{{
  "subject": "compelling subject line" (email only, null for LinkedIn),
  "body": "personalized message with {{{{tokens}}}}",
  "reasoning": "brief explanation of approach and why it works for this persona",
  "clarity_score": 0.0-10.0,
  "personalization_score": 0.0-10.0,
  "relevance_score": 0.0-10.0
}}

Generate the message now. Return ONLY valid JSON, no other text."""
        
        return prompt
    
    async def generate_variants(
        self,
        lead_data: Dict[str, Any],
        product_info: Dict[str, Any],
        step_config: Dict[str, Any],
        agent_profile: Dict[str, Any],
        campaign_type: str,
        num_variants: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple message variants for A/B testing
        """
        variants = []
        
        for i in range(num_variants):
            # Adjust temperature slightly for variety
            agent_copy = agent_profile.copy()
            agent_copy["temperature"] = min(0.9, agent_profile.get("temperature", 0.7) + (i * 0.1))
            
            variant = await self.generate_message_with_scoring(
                lead_data,
                product_info,
                step_config,
                agent_copy,
                campaign_type
            )
            
            variant["variant_name"] = f"Variant {chr(65 + i)}"  # A, B, C
            variants.append(variant)
        
        return variants
    
    async def rescore_message(self, message: str, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Re-score an existing message for quality audit
        """
        
        scoring_prompt = f"""Evaluate this outreach message for quality:

Message: \"{message}\"

Context:
- Lead Persona: {context.get('persona', 'N/A')}
- Product: {context.get('product_name', 'N/A')}
- Step Purpose: {context.get('purpose', 'N/A')}

Score the message on:
1. Clarity (0-10): Is it clear and easy to understand?
2. Personalization (0-10): How well tailored to the lead?
3. Relevance (0-10): How relevant is the value proposition?

Return JSON:
{{
  "clarity_score": 0.0-10.0,
  "personalization_score": 0.0-10.0,
  "relevance_score": 0.0-10.0,
  "feedback": "brief improvement suggestions"
}}"""
        
        chat = LlmChat(
            api_key=self.llm_key,
            session_id="message-rescoring",
            system_message="You are a message quality auditor. Provide objective scores."
        ).with_model("openai", "gpt-5")
        
        response = await chat.send_message(UserMessage(text=scoring_prompt))
        
        try:
            scores = json.loads(response)
            total = (scores.get("clarity_score", 0) + 
                    scores.get("personalization_score", 0) + 
                    scores.get("relevance_score", 0)) / 3
            scores["total_score"] = round(total, 2)
            return scores
        except:
            return {
                "clarity_score": 5.0,
                "personalization_score": 5.0,
                "relevance_score": 5.0,
                "total_score": 5.0,
                "feedback": "Could not parse scores"
            }
