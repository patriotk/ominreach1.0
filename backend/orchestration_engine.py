"""
Orchestration Engine - The "Brain"
Handles scheduling and execution of sequence steps
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
import httpx

logger = logging.getLogger(__name__)


class OrchestrationEngine:
    """Core engine for executing sequences"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.phantombuster_api_key = os.getenv("PHANTOMBUSTER_API_KEY")
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "https://reach-master-2.preview.emergentagent.com")
    
    async def run_scheduler(self):
        """
        Main scheduler - runs every minute
        Finds prospects with due steps and executes them
        """
        logger.info("🔄 Running orchestration scheduler...")
        
        # Find ACTIVE prospects with due steps
        now = datetime.now(timezone.utc)
        due_prospects = await self.db.prospects.find({
            "status": "ACTIVE",
            "next_step_due_at": {"$lte": now}
        }).to_list(100)
        
        logger.info(f"Found {len(due_prospects)} prospects with due steps")
        
        for prospect in due_prospects:
            try:
                await self.execute_prospect_step(prospect)
            except Exception as e:
                logger.error(f"Error executing step for prospect {prospect['id']}: {str(e)}")
    
    async def execute_prospect_step(self, prospect: Dict[str, Any]):
        """Execute the current step for a prospect"""
        
        # Get current step
        step = await self.db.campaign_steps.find_one({"id": prospect["current_step_id"]})
        if not step:
            logger.error(f"Step {prospect['current_step_id']} not found")
            return
        
        # Get persona (for credentials)
        persona = await self.db.personas.find_one({"id": prospect["assigned_persona_id"]})
        if not persona:
            logger.error(f"Persona {prospect['assigned_persona_id']} not found")
            return
        
        # Execute based on channel
        if step["channel"] == "EMAIL":
            await self.execute_email_step(prospect, step, persona)
        elif step["channel"] == "LINKEDIN":
            await self.execute_linkedin_step(prospect, step, persona)
    
    async def execute_email_step(
        self,
        prospect: Dict[str, Any],
        step: Dict[str, Any],
        persona: Dict[str, Any]
    ):
        """Execute an email step"""
        logger.info(f"Executing EMAIL step for prospect {prospect['id']}")
        
        try:
            # Get template
            template = await self.db.templates.find_one({"id": step.get("template_id")})
            if not template:
                raise Exception("Template not found")
            
            # Replace merge tags
            subject = self._replace_merge_tags(template.get("email_subject", ""), prospect)
            body = self._replace_merge_tags(template["body_text"], prospect)
            
            # Send email via SendGrid
            success = await self._send_email_sendgrid(
                to_email=prospect["email"],
                from_email=persona["credentials"]["email"],
                subject=subject,
                body=body,
                api_key=persona["credentials"].get("sendgrid_api_key", self.sendgrid_api_key)
            )
            
            if success:
                # Log activity
                await self._log_activity(
                    prospect_id=prospect["id"],
                    persona_id=persona["id"],
                    campaign_id=prospect["current_campaign_id"],
                    step_id=step["id"],
                    channel="EMAIL",
                    action="Email Sent",
                    status="COMPLETED",
                    details=f"Subject: {subject}"
                )
                
                # Advance to next step
                await self.advance_to_next_step(prospect["id"])
            else:
                raise Exception("Email send failed")
                
        except Exception as e:
            logger.error(f"Email step failed: {str(e)}")
            await self._handle_step_failure(prospect["id"], str(e))
    
    async def execute_linkedin_step(
        self,
        prospect: Dict[str, Any],
        step: Dict[str, Any],
        persona: Dict[str, Any]
    ):
        """Execute a LinkedIn step via Phantombuster"""
        logger.info(f"Executing LINKEDIN step for prospect {prospect['id']}")
        
        try:
            # Determine which phantom to use
            phantom_id = None
            if step["action"] == "VIEW_PROFILE":
                phantom_id = persona["credentials"].get("phantom_view_id")
            elif step["action"] == "SEND_CONNECT":
                phantom_id = persona["credentials"].get("phantom_connect_id")
            elif step["action"] == "SEND_MESSAGE":
                phantom_id = persona["credentials"].get("phantom_message_id")
            
            if not phantom_id:
                raise Exception(f"Phantom ID not configured for action {step['action']}")
            
            # Get message content if needed
            message_content = None
            if step["action"] in ["SEND_CONNECT", "SEND_MESSAGE"] and step.get("template_id"):
                template = await self.db.templates.find_one({"id": step["template_id"]})
                if template:
                    message_content = self._replace_merge_tags(template["body_text"], prospect)
            
            # Generate webhook URL
            webhook_url = f"{self.webhook_base_url}/api/webhooks/phantombuster/{prospect['id']}"
            
            # Launch Phantombuster job
            container_id = await self._launch_phantombuster_job(
                phantom_id=phantom_id,
                api_key=persona["credentials"]["phantombuster_api_key"],
                linkedin_url=prospect.get("linkedin_url", ""),
                message=message_content,
                webhook_url=webhook_url
            )
            
            # Update prospect to awaiting webhook
            await self.db.prospects.update_one(
                {"id": prospect["id"]},
                {
                    "$set": {
                        "status": "PAUSED_AWAITING_WEBHOOK",
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # Log activity as PENDING
            await self._log_activity(
                prospect_id=prospect["id"],
                persona_id=persona["id"],
                campaign_id=prospect["current_campaign_id"],
                step_id=step["id"],
                channel="LINKEDIN",
                action=f"LinkedIn {step['action']}",
                status="PENDING",
                details="Waiting for Phantombuster webhook",
                external_id=container_id
            )
            
        except Exception as e:
            logger.error(f"LinkedIn step failed: {str(e)}")
            await self._handle_step_failure(prospect["id"], str(e))
    
    async def advance_to_next_step(self, prospect_id: str):
        """Move prospect to the next step in their sequence"""
        
        prospect = await self.db.prospects.find_one({"id": prospect_id})
        if not prospect:
            return
        
        # Get current step
        current_step = await self.db.campaign_steps.find_one({"id": prospect["current_step_id"]})
        if not current_step:
            return
        
        # Find next step
        next_step = await self.db.campaign_steps.find_one({
            "campaign_id": prospect["current_campaign_id"],
            "step_number": current_step["step_number"] + 1
        })
        
        if next_step:
            # Calculate next due date
            next_due = datetime.now(timezone.utc) + timedelta(days=next_step["delay_in_days"])
            
            # Update prospect
            await self.db.prospects.update_one(
                {"id": prospect_id},
                {
                    "$set": {
                        "status": "ACTIVE",
                        "current_step_id": next_step["id"],
                        "next_step_due_at": next_due,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            logger.info(f"✅ Advanced prospect {prospect_id} to step {next_step['step_number']}")
        else:
            # Sequence completed
            await self.db.prospects.update_one(
                {"id": prospect_id},
                {
                    "$set": {
                        "status": "COMPLETED",
                        "current_step_id": None,
                        "next_step_due_at": None,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            logger.info(f"🎉 Prospect {prospect_id} completed sequence")
    
    async def handle_phantombuster_webhook(
        self,
        prospect_id: str,
        container_id: str,
        status: str,
        error: Optional[str] = None
    ):
        """Handle webhook callback from Phantombuster"""
        
        prospect = await self.db.prospects.find_one({"id": prospect_id})
        if not prospect:
            logger.error(f"Prospect {prospect_id} not found for webhook")
            return
        
        if status == "success":
            # Update activity log
            await self.db.activity_log.update_one(
                {"external_id": container_id},
                {"$set": {"status": "COMPLETED"}}
            )
            
            # Advance to next step
            await self.advance_to_next_step(prospect_id)
            
        else:
            # Failed - log and pause for manual review
            await self._log_activity(
                prospect_id=prospect_id,
                persona_id=prospect["assigned_persona_id"],
                campaign_id=prospect["current_campaign_id"],
                step_id=prospect["current_step_id"],
                channel="LINKEDIN",
                action="LinkedIn Step Failed",
                status="FAILED",
                details=f"Phantombuster error: {error}",
                external_id=container_id
            )
            
            await self.db.prospects.update_one(
                {"id": prospect_id},
                {
                    "$set": {
                        "status": "PAUSED_MANUAL_REVIEW",
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
    
    async def handle_email_reply(self, prospect_email: str):
        """Handle email reply detection - auto-pause sequence"""
        
        prospect = await self.db.prospects.find_one({"email": prospect_email})
        if not prospect:
            return
        
        # Only pause if they're active in a sequence
        if prospect["status"] == "ACTIVE":
            await self.db.prospects.update_one(
                {"id": prospect["id"]},
                {
                    "$set": {
                        "status": "REPLIED",
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # Log reply
            await self._log_activity(
                prospect_id=prospect["id"],
                persona_id=prospect["assigned_persona_id"],
                campaign_id=prospect["current_campaign_id"],
                step_id=prospect.get("current_step_id"),
                channel="EMAIL",
                action="Reply Received",
                status="COMPLETED",
                details="Prospect replied - sequence auto-paused"
            )
            
            logger.info(f"📧 Prospect {prospect['id']} replied - sequence paused")
    
    # ============ HELPER METHODS ============
    
    def _replace_merge_tags(self, text: str, prospect: Dict[str, Any]) -> str:
        """Replace merge tags in template with prospect data"""
        replacements = {
            "{{first_name}}": prospect.get("first_name", ""),
            "{{last_name}}": prospect.get("last_name", ""),
            "{{company}}": prospect.get("company", ""),
            "{{title}}": prospect.get("title", ""),
            "{{email}}": prospect.get("email", "")
        }
        
        for tag, value in replacements.items():
            text = text.replace(tag, value)
        
        return text
    
    async def _send_email_sendgrid(
        self,
        to_email: str,
        from_email: str,
        subject: str,
        body: str,
        api_key: str
    ) -> bool:
        """Send email via SendGrid API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "personalizations": [{"to": [{"email": to_email}]}],
                        "from": {"email": from_email},
                        "subject": subject,
                        "content": [{"type": "text/plain", "value": body}]
                    }
                )
                return response.status_code == 202
        except Exception as e:
            logger.error(f"SendGrid error: {str(e)}")
            return False
    
    async def _launch_phantombuster_job(
        self,
        phantom_id: str,
        api_key: str,
        linkedin_url: str,
        message: Optional[str],
        webhook_url: str
    ) -> str:
        """Launch Phantombuster job and return container ID"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.phantombuster.com/api/v2/agents/launch",
                    headers={
                        "X-Phantombuster-Key": api_key
                    },
                    json={
                        "id": phantom_id,
                        "argument": {
                            "profileUrl": linkedin_url,
                            "message": message,
                            "webhookUrl": webhook_url
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("containerId", "")
                else:
                    raise Exception(f"Phantombuster API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Phantombuster launch error: {str(e)}")
            raise
    
    async def _log_activity(
        self,
        prospect_id: str,
        persona_id: str,
        campaign_id: Optional[str],
        step_id: Optional[str],
        channel: str,
        action: str,
        status: str,
        details: Optional[str] = None,
        external_id: Optional[str] = None
    ):
        """Log activity to unified timeline"""
        
        activity = {
            "id": str(uuid.uuid4()),
            "prospect_id": prospect_id,
            "persona_id": persona_id,
            "campaign_id": campaign_id,
            "step_id": step_id,
            "timestamp": datetime.now(timezone.utc),
            "channel": channel,
            "action": action,
            "status": status,
            "details": details,
            "external_id": external_id
        }
        
        await self.db.activity_log.insert_one(activity)
    
    async def _handle_step_failure(self, prospect_id: str, error_message: str):
        """Handle step failure - pause for manual review"""
        
        await self.db.prospects.update_one(
            {"id": prospect_id},
            {
                "$set": {
                    "status": "PAUSED_MANUAL_REVIEW",
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        logger.error(f"❌ Step failed for prospect {prospect_id}: {error_message}")


import uuid
