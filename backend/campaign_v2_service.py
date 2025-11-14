"""
Campaign Service V2
Handles campaign business logic
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from campaign_v2_models import (
    Campaign, Message, LeadCampaignState, CampaignStep,
    StepAgentSettings, ProductInfo, CampaignSchedule
)
from message_generator_v2 import MessageGeneratorV2

logger = logging.getLogger(__name__)


class CampaignServiceV2:
    """Campaign operations and logic"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.message_generator = MessageGeneratorV2()
    
    async def create_campaign(
        self,
        user_id: str,
        name: str,
        campaign_type: str,
        lead_limit: int = 100
    ) -> Campaign:
        """Create new campaign with 3 default steps"""
        
        # Create 3 default steps
        steps = []
        for i in range(1, 4):
            delay_days = 0 if i == 1 else (3 if i == 2 else 5)
            step = CampaignStep(
                step_number=i,
                delay_days=delay_days,
                delay_hours=0,
                window_start_hour=9,
                window_end_hour=17,
                agent_settings=StepAgentSettings()
            )
            steps.append(step)
        
        # Create campaign
        campaign = Campaign(
            user_id=user_id,
            name=name,
            type=campaign_type,
            lead_limit=lead_limit,
            steps=steps
        )
        
        # Save to DB
        await self.db.campaigns_v2.insert_one(campaign.model_dump())
        logger.info(f"Created campaign: {campaign.id}")
        
        return campaign
    
    async def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign by ID"""
        campaign = await self.db.campaigns_v2.find_one({"id": campaign_id})
        return campaign
    
    async def update_campaign(
        self,
        campaign_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update campaign fields"""
        updates["updated_at"] = datetime.now(timezone.utc)
        
        result = await self.db.campaigns_v2.update_one(
            {"id": campaign_id},
            {"$set": updates}
        )
        
        return result.modified_count > 0
    
    async def update_step(
        self,
        campaign_id: str,
        step_number: int,
        updates: Dict[str, Any]
    ) -> bool:
        """Update a specific step"""
        campaign = await self.get_campaign(campaign_id)
        if not campaign:
            return False
        
        steps = campaign.get("steps", [])
        for step in steps:
            if step["step_number"] == step_number:
                # Update step fields
                for key, value in updates.items():
                    if key == "agent_settings" and isinstance(value, dict):
                        step["agent_settings"].update(value)
                    else:
                        step[key] = value
                break
        
        # Save updated steps
        await self.db.campaigns_v2.update_one(
            {"id": campaign_id},
            {"$set": {"steps": steps, "updated_at": datetime.now(timezone.utc)}}
        )
        
        return True
    
    async def generate_test_messages(self, campaign_id: str) -> Dict[str, Any]:
        """
        Generate messages for first 3 leads (test phase)
        Returns: {success: bool, messages_generated: int, test_lead_ids: []}
        """
        campaign = await self.get_campaign(campaign_id)
        if not campaign:
            return {"success": False, "error": "Campaign not found"}
        
        # Get first 3 leads
        selected_leads = campaign.get("selected_lead_ids", [])
        if len(selected_leads) < 3:
            return {"success": False, "error": "Need at least 3 leads selected"}
        
        test_lead_ids = selected_leads[:3]
        
        # Get lead data
        leads = await self.db.leads.find({"id": {"$in": test_lead_ids}}).to_list(3)
        
        if len(leads) < 3:
            return {"success": False, "error": "Could not find lead data"}
        
        # Generate messages for all 3 steps for these 3 leads
        messages_generated = 0
        
        for lead in leads:
            for step_number in [1, 2, 3]:
                result = await self._generate_message_for_lead(
                    campaign=campaign,
                    lead=lead,
                    step_number=step_number
                )
                
                if result:
                    messages_generated += 1
        
        # Update campaign status
        await self.update_campaign(campaign_id, {
            "status": "test_phase",
            "test_lead_ids": test_lead_ids,
            "test_approved": False
        })
        
        return {
            "success": True,
            "messages_generated": messages_generated,
            "test_lead_ids": test_lead_ids
        }
    
    async def generate_bulk_messages(self, campaign_id: str) -> Dict[str, Any]:
        """
        Generate messages for ALL leads up to lead_limit
        Returns: {success: bool, messages_generated: int}
        """
        campaign = await self.get_campaign(campaign_id)
        if not campaign:
            return {"success": False, "error": "Campaign not found"}
        
        if not campaign.get("test_approved"):
            return {"success": False, "error": "Test phase not approved"}
        
        # Get leads up to limit
        selected_leads = campaign.get("selected_lead_ids", [])
        lead_limit = campaign.get("lead_limit", 100)
        leads_to_process = selected_leads[:lead_limit]
        
        # Get lead data
        leads = await self.db.leads.find({"id": {"$in": leads_to_process}}).to_list(lead_limit)
        
        messages_generated = 0
        
        for lead in leads:
            for step_number in [1, 2, 3]:
                result = await self._generate_message_for_lead(
                    campaign=campaign,
                    lead=lead,
                    step_number=step_number
                )
                
                if result:
                    messages_generated += 1
        
        # Update campaign status
        await self.update_campaign(campaign_id, {
            "status": "approved"
        })
        
        return {
            "success": True,
            "messages_generated": messages_generated,
            "total_leads": len(leads)
        }
    
    async def _generate_message_for_lead(
        self,
        campaign: Dict[str, Any],
        lead: Dict[str, Any],
        step_number: int
    ) -> Optional[str]:
        """Generate a single message for a lead at a step"""
        
        # Get step config
        steps = campaign.get("steps", [])
        step_config = None
        for step in steps:
            if step["step_number"] == step_number:
                step_config = step
                break
        
        if not step_config:
            logger.error(f"Step {step_number} not found in campaign")
            return None
        
        # Get previous message (for steps 2 & 3)
        previous_message = None
        if step_number > 1:
            prev_msg = await self.db.messages_v2.find_one({
                "campaign_id": campaign["id"],
                "lead_id": lead["id"],
                "step_number": step_number - 1
            })
            if prev_msg:
                previous_message = prev_msg.get("content")
        
        # Generate message using AI
        result = await self.message_generator.generate_message(
            lead=lead,
            campaign_type=campaign["type"],
            step_number=step_number,
            product_info=campaign.get("product_info", {}),
            step_agent_settings=step_config.get("agent_settings", {}),
            step_best_practices=step_config.get("best_practices_text"),
            previous_message=previous_message
        )
        
        if not result:
            logger.error(f"Failed to generate message for lead {lead['id']} step {step_number}")
            return None
        
        # Create message document
        message = Message(
            campaign_id=campaign["id"],
            lead_id=lead["id"],
            step_number=step_number,
            channel=campaign["type"],
            subject=result.get("subject", ""),
            content=result.get("body", ""),
            status="draft",
            ai_score=result.get("ai_score"),
            generation_context={
                "tone_used": result.get("tone_used"),
                "reasoning": result.get("reasoning")
            }
        )
        
        # Save message
        await self.db.messages_v2.insert_one(message.model_dump())
        logger.info(f"Generated message for lead {lead.get('name')} - Step {step_number}")
        
        return message.id
    
    async def regenerate_message(
        self,
        message_id: str
    ) -> Optional[Dict[str, Any]]:
        """Regenerate a specific message"""
        
        # Get existing message
        message = await self.db.messages_v2.find_one({"id": message_id})
        if not message:
            return None
        
        # Get campaign and lead
        campaign = await self.get_campaign(message["campaign_id"])
        lead = await self.db.leads.find_one({"id": message["lead_id"]})
        
        if not campaign or not lead:
            return None
        
        # Delete old message
        await self.db.messages_v2.delete_one({"id": message_id})
        
        # Generate new message
        new_message_id = await self._generate_message_for_lead(
            campaign=campaign,
            lead=lead,
            step_number=message["step_number"]
        )
        
        if new_message_id:
            # Return new message
            new_message = await self.db.messages_v2.find_one({"id": new_message_id})
            return new_message
        
        return None
    
    async def get_campaign_messages(
        self,
        campaign_id: str,
        lead_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get all messages for a campaign (optionally filtered by leads)"""
        
        query = {"campaign_id": campaign_id}
        if lead_ids:
            query["lead_id"] = {"$in": lead_ids}
        
        messages = await self.db.messages_v2.find(query).to_list(None)
        return messages
    
    async def update_message(
        self,
        message_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update message content (manual edit)"""
        
        updates["updated_at"] = datetime.now(timezone.utc)
        
        result = await self.db.messages_v2.update_one(
            {"id": message_id},
            {"$set": updates}
        )
        
        return result.modified_count > 0
    
    async def get_campaign_analytics(self, campaign_id: str) -> Dict[str, Any]:
        """Get campaign analytics"""
        
        # Get all messages for campaign
        messages = await self.db.messages_v2.find({"campaign_id": campaign_id}).to_list(None)
        
        # Count by status
        total_sent = len([m for m in messages if m["status"] == "sent"])
        total_opened = len([m for m in messages if m["status"] == "opened"])
        total_clicked = len([m for m in messages if m["status"] == "clicked"])
        total_replied = len([m for m in messages if m["status"] == "replied"])
        
        # Count by step
        step1_sent = len([m for m in messages if m["step_number"] == 1 and m["status"] == "sent"])
        step2_sent = len([m for m in messages if m["step_number"] == 2 and m["status"] == "sent"])
        step3_sent = len([m for m in messages if m["step_number"] == 3 and m["status"] == "sent"])
        
        # Calculate rates
        open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
        click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0
        reply_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0
        
        # Get lead states
        lead_states = await self.db.lead_campaign_states.find({"campaign_id": campaign_id}).to_list(None)
        
        states_count = {}
        for state in lead_states:
            state_name = state["state"]
            states_count[state_name] = states_count.get(state_name, 0) + 1
        
        return {
            "campaign_id": campaign_id,
            "total_leads": len(lead_states),
            "messages_sent": total_sent,
            "messages_opened": total_opened,
            "messages_clicked": total_clicked,
            "messages_replied": total_replied,
            "step1_sent": step1_sent,
            "step2_sent": step2_sent,
            "step3_sent": step3_sent,
            "open_rate": round(open_rate, 2),
            "click_rate": round(click_rate, 2),
            "reply_rate": round(reply_rate, 2),
            "leads_not_contacted": states_count.get("not_contacted", 0),
            "leads_in_progress": states_count.get("step1_sent", 0) + states_count.get("step2_sent", 0),
            "leads_replied": states_count.get("replied", 0),
            "leads_completed": states_count.get("completed", 0),
            "leads_failed": states_count.get("failed", 0)
        }
