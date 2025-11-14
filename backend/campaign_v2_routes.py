"""
Campaign V2 API Routes
Clean, new endpoints for rebuilt campaign system
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional
import logging
from datetime import datetime, timezone

from campaign_v2_models import (
    CreateCampaignRequest, UpdateCampaignRequest, UpdateStepRequest,
    GenerateMessageRequest, GenerateTestMessagesRequest,
    BulkGenerateMessagesRequest, UpdateMessageRequest,
    ActivateCampaignRequest, Campaign, Message
)
from campaign_v2_service import CampaignServiceV2
from document_parser import DocumentParser
from ai_product_analyzer import AIProductAnalyzer

logger = logging.getLogger(__name__)

# Router
campaign_v2_router = APIRouter(prefix="/api/v2/campaigns", tags=["Campaigns V2"])


# Dependency injection helpers (will be set by main server.py)
campaign_service: Optional[CampaignServiceV2] = None
ai_analyzer: Optional[AIProductAnalyzer] = None


def get_campaign_service() -> CampaignServiceV2:
    """Get campaign service instance"""
    if campaign_service is None:
        raise HTTPException(status_code=500, detail="Campaign service not initialized")
    return campaign_service


def get_ai_analyzer() -> AIProductAnalyzer:
    """Get AI analyzer instance"""
    if ai_analyzer is None:
        raise HTTPException(status_code=500, detail="AI analyzer not initialized")
    return ai_analyzer


# ============ CAMPAIGN CRUD ============

@campaign_v2_router.post("/")
async def create_campaign(
    request: CreateCampaignRequest,
    user_id: str = "user-patriot-1762275399425",  # TODO: Get from auth
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Create new campaign with 3 default steps"""
    try:
        campaign = await service.create_campaign(
            user_id=user_id,
            name=request.name,
            campaign_type=request.type,
            lead_limit=request.lead_limit
        )
        return campaign.model_dump()
    except Exception as e:
        logger.error(f"Create campaign error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@campaign_v2_router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Get campaign by ID"""
    campaign = await service.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@campaign_v2_router.get("/")
async def list_campaigns(
    user_id: str = "user-patriot-1762275399425",  # TODO: Get from auth
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """List all campaigns for user"""
    campaigns = await service.db.campaigns_v2.find({"user_id": user_id}).to_list(None)
    return campaigns


@campaign_v2_router.patch("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    request: UpdateCampaignRequest,
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Update campaign"""
    updates = {}
    if request.name:
        updates["name"] = request.name
    if request.selected_lead_ids is not None:
        updates["selected_lead_ids"] = request.selected_lead_ids
    if request.lead_limit is not None:
        updates["lead_limit"] = request.lead_limit
    if request.schedule:
        updates["schedule"] = request.schedule.model_dump()
    
    success = await service.update_campaign(campaign_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {"success": True}


@campaign_v2_router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Delete campaign"""
    result = await service.db.campaigns_v2.delete_one({"id": campaign_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Also delete messages
    await service.db.messages_v2.delete_many({"campaign_id": campaign_id})
    
    return {"success": True}


# ============ PRODUCT INFO ============

@campaign_v2_router.post("/{campaign_id}/product-info/upload")
async def upload_product_doc(
    campaign_id: str,
    file: UploadFile = File(...),
    service: CampaignServiceV2 = Depends(get_campaign_service),
    analyzer: AIProductAnalyzer = Depends(get_ai_analyzer)
):
    """Upload and analyze product document"""
    
    # Validate file
    if not file.filename.endswith(('.pdf', '.docx', '.txt')):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, TXT supported")
    
    # Parse document
    content = await file.read()
    parsed_text = DocumentParser.parse_file(file.filename, content)
    
    if not parsed_text:
        raise HTTPException(status_code=400, detail="Could not extract text")
    
    # AI Analysis
    product_data = await analyzer.analyze_product_document(parsed_text)
    
    if not product_data:
        raise HTTPException(status_code=500, detail="AI analysis failed")
    
    # Update campaign
    product_info = {
        "product_name": product_data.get("product_name", ""),
        "summary": product_data.get("product_summary", ""),
        "features": product_data.get("main_features", []),
        "differentiators": product_data.get("key_differentiators", []),
        "call_to_action": product_data.get("call_to_action", ""),
        "raw_content": parsed_text[:2000]
    }
    
    await service.update_campaign(campaign_id, {"product_info": product_info})
    
    return {
        "success": True,
        "product_info": product_info,
        "preview": parsed_text[:300]
    }


# ============ STEP CONFIGURATION ============

@campaign_v2_router.patch("/{campaign_id}/steps/{step_number}")
async def update_step(
    campaign_id: str,
    step_number: int,
    request: UpdateStepRequest,
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Update step configuration"""
    
    if step_number not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Step number must be 1, 2, or 3")
    
    updates = {}
    if request.delay_days is not None:
        updates["delay_days"] = request.delay_days
    if request.delay_hours is not None:
        updates["delay_hours"] = request.delay_hours
    if request.window_start_hour is not None:
        updates["window_start_hour"] = request.window_start_hour
    if request.window_end_hour is not None:
        updates["window_end_hour"] = request.window_end_hour
    if request.agent_settings:
        updates["agent_settings"] = request.agent_settings.model_dump()
    
    success = await service.update_step(campaign_id, step_number, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Campaign or step not found")
    
    return {"success": True}


@campaign_v2_router.post("/{campaign_id}/steps/{step_number}/best-practices")
async def upload_best_practices(
    campaign_id: str,
    step_number: int,
    file: UploadFile = File(...),
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Upload best practices document for a step"""
    
    if step_number not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Step number must be 1, 2, or 3")
    
    # Validate file
    if not file.filename.endswith(('.pdf', '.docx', '.txt')):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, TXT supported")
    
    # Parse document
    content = await file.read()
    parsed_text = DocumentParser.parse_file(file.filename, content)
    
    if not parsed_text:
        raise HTTPException(status_code=400, detail="Could not extract text")
    
    # Update step
    updates = {
        "best_practices_text": parsed_text[:5000],  # First 5000 chars
        "best_practices_file_url": file.filename
    }
    
    success = await service.update_step(campaign_id, step_number, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Campaign or step not found")
    
    return {
        "success": True,
        "filename": file.filename,
        "preview": parsed_text[:300]
    }


# ============ MESSAGE GENERATION ============

@campaign_v2_router.post("/generate-test-messages")
async def generate_test_messages(
    request: GenerateTestMessagesRequest,
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Generate messages for first 3 leads (test phase)"""
    
    result = await service.generate_test_messages(request.campaign_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Generation failed"))
    
    return result


@campaign_v2_router.post("/generate-bulk-messages")
async def generate_bulk_messages(
    request: BulkGenerateMessagesRequest,
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Generate messages for all leads (after test approval)"""
    
    result = await service.generate_bulk_messages(request.campaign_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Generation failed"))
    
    return result


@campaign_v2_router.post("/regenerate-message/{message_id}")
async def regenerate_message(
    message_id: str,
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Regenerate a specific message"""
    
    new_message = await service.regenerate_message(message_id)
    
    if not new_message:
        raise HTTPException(status_code=404, detail="Message not found or regeneration failed")
    
    return new_message


# ============ MESSAGE REVIEW ============

@campaign_v2_router.get("/{campaign_id}/messages")
async def get_campaign_messages(
    campaign_id: str,
    lead_ids: Optional[str] = None,  # Comma-separated
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Get all messages for campaign"""
    
    lead_id_list = None
    if lead_ids:
        lead_id_list = lead_ids.split(",")
    
    messages = await service.get_campaign_messages(campaign_id, lead_id_list)
    return messages


@campaign_v2_router.patch("/messages/{message_id}")
async def update_message(
    message_id: str,
    request: UpdateMessageRequest,
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Update/edit a message"""
    
    updates = {}
    if request.subject is not None:
        updates["subject"] = request.subject
    if request.content is not None:
        updates["content"] = request.content
    
    success = await service.update_message(message_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"success": True}


# ============ CAMPAIGN APPROVAL & ACTIVATION ============

@campaign_v2_router.post("/{campaign_id}/approve-test")
async def approve_test_phase(
    campaign_id: str,
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Approve test phase and allow bulk generation"""
    
    success = await service.update_campaign(campaign_id, {
        "test_approved": True
    })
    
    if not success:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {"success": True, "message": "Test phase approved. Ready for bulk generation."}


@campaign_v2_router.post("/{campaign_id}/activate")
async def activate_campaign(
    campaign_id: str,
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Activate campaign (start sending)"""
    
    campaign = await service.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Validation
    if not campaign.get("test_approved"):
        raise HTTPException(status_code=400, detail="Test phase not approved")
    
    if not campaign.get("schedule"):
        raise HTTPException(status_code=400, detail="Schedule not configured")
    
    # Check messages exist
    messages = await service.get_campaign_messages(campaign_id)
    if len(messages) == 0:
        raise HTTPException(status_code=400, detail="No messages generated")
    
    # Activate
    success = await service.update_campaign(campaign_id, {
        "status": "active"
    })
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to activate")
    
    return {"success": True, "message": "Campaign activated"}


# ============ ANALYTICS ============

@campaign_v2_router.get("/{campaign_id}/analytics")
async def get_campaign_analytics(
    campaign_id: str,
    service: CampaignServiceV2 = Depends(get_campaign_service)
):
    """Get campaign analytics"""
    
    analytics = await service.get_campaign_analytics(campaign_id)
    return analytics
