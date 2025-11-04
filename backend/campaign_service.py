from datetime import datetime, timezone, timedelta
import re
from typing import List, Dict, Any, Optional
import random

class CampaignService:
    def __init__(self, db):
        self.db = db
    
    def validate_campaign(self, campaign: Dict) -> List[str]:
        """Validate campaign before activation"""
        errors = []
        
        # Check message steps
        if not campaign.get("message_steps"):
            errors.append("Campaign must have at least one message step")
        
        # Check each step has variants
        for step in campaign.get("message_steps", []):
            if len(step.get("variants", [])) < 2:
                errors.append(f"Step {step['step_number']} must have at least 2 variants for A/B testing")
        
        # Check schedule
        if not campaign.get("schedule"):
            errors.append("Campaign must have a schedule configured")
        
        # Check leads
        if not campaign.get("lead_ids"):
            errors.append("Campaign must have at least one lead assigned")
        
        return errors
    
    def apply_personalization(self, template: str, lead: Dict) -> str:
        """Apply personalization tokens to message template"""
        # Support tokens: {{first_name}}, {{last_name}}, {{company}}, {{job_title}}
        result = template
        
        # Extract first name from full name
        full_name = lead.get("name", "")
        first_name = full_name.split()[0] if full_name else "there"
        last_name = " ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else ""
        
        replacements = {
            "{{first_name}}": first_name,
            "{{last_name}}": last_name,
            "{{company}}": lead.get("company", "your company"),
            "{{job_title}}": lead.get("title", "your role"),
            "{{name}}": full_name
        }
        
        for token, value in replacements.items():
            result = result.replace(token, value)
        
        return result
    
    def select_variant_for_lead(self, variants: List[Dict], lead_id: str) -> Dict:
        """Select variant using consistent hashing for A/B split"""
        # Use lead_id hash to consistently assign variant
        hash_val = hash(lead_id)
        index = hash_val % len(variants)
        return variants[index]
    
    def calculate_metrics(self, campaign_id: str, executions: List[Dict]) -> Dict:
        """Calculate campaign metrics from executions"""
        total_sent = len([e for e in executions if e["status"] in ["sent", "opened", "replied"]])
        total_opened = len([e for e in executions if e["status"] in ["opened", "replied"]])
        total_replied = len([e for e in executions if e["status"] == "replied"])
        
        open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
        reply_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0
        
        # Calculate response time
        response_times = []
        for exec in executions:
            if exec.get("replied_at") and exec.get("sent_at"):
                sent = exec["sent_at"] if isinstance(exec["sent_at"], datetime) else datetime.fromisoformat(exec["sent_at"])
                replied = exec["replied_at"] if isinstance(exec["replied_at"], datetime) else datetime.fromisoformat(exec["replied_at"])
                hours = (replied - sent).total_seconds() / 3600
                response_times.append(hours)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        return {
            "messages_sent": total_sent,
            "messages_opened": total_opened,
            "messages_replied": total_replied,
            "open_rate": round(open_rate, 2),
            "reply_rate": round(reply_rate, 2),
            "avg_response_time_hours": round(avg_response_time, 2) if avg_response_time else None
        }
    
    def calculate_ai_score(self, metrics: Dict) -> float:
        """Calculate AI performance score /10"""
        # Weighted scoring
        reply_weight = 0.5
        open_weight = 0.3
        conversion_weight = 0.2
        
        reply_score = min(metrics.get("reply_rate", 0) / 10, 10)  # 10% reply = 1 point
        open_score = min(metrics.get("open_rate", 0) / 10, 10)  # 10% open = 1 point
        conversion_score = metrics.get("conversion_rate", 0) * 10  # 10% conversion = 1 point
        
        total_score = (
            reply_score * reply_weight +
            open_score * open_weight +
            conversion_score * conversion_weight
        )
        
        return min(round(total_score, 1), 10.0)
    
    def determine_verdict(self, ai_score: float) -> str:
        """Determine campaign verdict based on AI score"""
        if ai_score >= 7.0:
            return "Success"
        elif ai_score >= 4.0:
            return "Moderate"
        else:
            return "Poor"
    
    def determine_winning_variant(self, variants: List[Dict]) -> Optional[str]:
        """Determine winning variant based on metrics"""
        if not variants:
            return None
        
        # Need minimum sends threshold
        min_sends = 50
        valid_variants = [v for v in variants if v.get("metrics", {}).get("sent", 0) >= min_sends]
        
        if not valid_variants:
            return None
        
        # Score based on reply rate and conversion
        def variant_score(v):
            metrics = v.get("metrics", {})
            sent = metrics.get("sent", 1)
            replies = metrics.get("replied", 0)
            conversions = metrics.get("converted", 0)
            reply_rate = replies / sent if sent > 0 else 0
            conversion_rate = conversions / sent if sent > 0 else 0
            return (reply_rate * 0.6) + (conversion_rate * 0.4)
        
        winner = max(valid_variants, key=variant_score)
        return winner.get("id")
    
    async def sync_to_google_sheets(self, campaign_id: str, user_id: str):
        """Sync campaign results to Google Sheets"""
        # Get sheet integration
        integration = await self.db.integrations.find_one({
            "user_id": user_id,
            "type": "google_sheets"
        })
        
        if not integration:
            return {"error": "Google Sheets not connected"}
        
        # Get campaign and executions
        campaign = await self.db.campaigns.find_one({"id": campaign_id})
        executions = await self.db.campaign_executions.find({"campaign_id": campaign_id}).to_list(1000)
        
        # Get leads
        lead_ids = campaign.get("lead_ids", [])
        leads = await self.db.leads.find({"id": {"$in": lead_ids}}).to_list(1000)
        
        # Prepare sheet data
        rows = []
        for lead in leads:
            # Find executions for this lead
            lead_execs = [e for e in executions if e["lead_id"] == lead["id"]]
            
            contacted_date = lead_execs[0]["sent_at"] if lead_execs else None
            persona = lead.get("persona", "")
            call_offered = lead.get("call_offered", False)
            call_booked = lead.get("call_booked", False)
            verdict = lead.get("verdict") or campaign.get("metrics", {}).get("verdict", "")
            score = lead.get("score") or campaign.get("metrics", {}).get("ai_score", 0)
            
            rows.append({
                "Name": lead.get("name"),
                "Date Contacted": contacted_date.strftime("%Y-%m-%d") if contacted_date else "",
                "Persona": persona[:100] if persona else "",
                "Call Offered": "Yes" if call_offered else "No",
                "Call Booked": "Yes" if call_booked else "No",
                "Verdict": verdict,
                "Date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "Score": f"{score}/10" if score else ""
            })
        
        # In production, this would use Google Sheets API
        return {
            "message": "Sheet sync prepared",
            "rows": len(rows),
            "note": "Add Google Sheets API credentials for live sync"
        }
