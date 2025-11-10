from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class CampaignScheduler:
    """Handles campaign scheduling and send job creation"""
    
    def __init__(self, db):
        self.db = db
    
    async def schedule_campaign_messages(
        self,
        campaign_id: str,
        lead_ids: List[str]
    ) -> Dict[str, int]:
        """
        Create send jobs for all steps and leads in a campaign
        """
        campaign = await self.db.campaigns.find_one({"id": campaign_id})
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        steps = campaign.get("steps", [])
        daily_cap = campaign.get("daily_send_cap", 50)
        
        jobs_created = 0
        current_date = datetime.now(timezone.utc)
        
        for lead_id in lead_ids:
            schedule_date = current_date
            
            for step in steps:
                step_number = step.get("step_number")
                delay_days = step.get("delay_days", 0)
                send_start_hour = step.get("send_window_start", 9)
                
                # Calculate scheduled time
                if step_number > 1:
                    schedule_date = schedule_date + timedelta(days=delay_days)
                
                # Set to send window start hour
                schedule_datetime = schedule_date.replace(
                    hour=send_start_hour,
                    minute=0,
                    second=0
                )
                
                # Create send job
                job = {
                    "id": str(uuid.uuid4()),
                    "campaign_id": campaign_id,
                    "lead_id": lead_id,
                    "step_number": step_number,
                    "scheduled_for": schedule_datetime,
                    "status": "scheduled",
                    "channel": campaign.get("campaign_type"),
                    "created_at": datetime.now(timezone.utc)
                }
                
                await self.db.send_jobs.insert_one(job)
                jobs_created += 1
        
        return {
            "jobs_created": jobs_created,
            "leads_scheduled": len(lead_ids),
            "steps_per_lead": len(steps)
        }
    
    async def get_pending_jobs(
        self,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get jobs ready to send (scheduled_for <= now, status = scheduled)
        """
        now = datetime.now(timezone.utc)
        
        jobs = await self.db.send_jobs.find({
            "status": "scheduled",
            "scheduled_for": {"$lte": now}
        }).limit(limit).to_list(limit)
        
        return jobs
    
    async def mark_job_sent(
        self,
        job_id: str,
        success: bool = True,
        error: str = None
    ):
        """
        Mark a send job as completed
        """
        update = {
            "status": "sent" if success else "failed",
            "sent_at": datetime.now(timezone.utc)
        }
        
        if error:
            update["error"] = error
        
        await self.db.send_jobs.update_one(
            {"id": job_id},
            {"$set": update}
        )

import uuid
