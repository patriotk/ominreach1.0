from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, status, Cookie
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import httpx
from emergentintegrations.llm.chat import LlmChat, UserMessage
from campaign_models import Campaign, MessageStep, MessageVariant, CampaignSchedule, CampaignMetrics, CampaignExecution
from campaign_service import CampaignService
import resend

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ============ MODELS ============

class User(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "agent"  # admin, manager, agent
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    persona: Optional[str] = None
    date_contacted: Optional[datetime] = None
    call_offered: bool = False
    call_booked: bool = False
    verdict: Optional[str] = None
    score: Optional[float] = None
    campaign_id: Optional[str] = None
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MessageVariant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    subject: Optional[str] = None
    content: str
    channel: str  # email or linkedin
    metrics: Dict[str, int] = Field(default_factory=lambda: {"sent": 0, "opened": 0, "replied": 0, "converted": 0})

class Campaign(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    goal_type: str = "hybrid"  # email, linkedin, hybrid
    status: str = "draft"  # draft, active, paused, completed
    message_variants: List[MessageVariant] = []
    message_steps: List[Dict[str, Any]] = []  # Sequence of steps
    schedule: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    target_persona: Optional[str] = None
    product_info: Dict[str, Any] = Field(default_factory=dict)  # Product information
    lead_ids: List[str] = []
    user_id: str
    team_id: Optional[str] = None
    validation_errors: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AnalyticsMetrics(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    date: datetime
    messages_sent: int = 0
    messages_opened: int = 0
    messages_replied: int = 0
    calls_offered: int = 0
    calls_booked: int = 0
    conversions: int = 0
    avg_response_time: Optional[float] = None

class AIInsight(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: Optional[str] = None
    insight_type: str  # performance, optimization, trend
    title: str
    description: str
    data: Dict[str, Any] = {}
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ INPUT SCHEMAS ============

class SessionDataRequest(BaseModel):
    session_id: str

class CreateLeadRequest(BaseModel):
    name: str
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    campaign_id: Optional[str] = None

class UpdateLeadRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    persona: Optional[str] = None
    call_offered: Optional[bool] = None
    call_booked: Optional[bool] = None
    verdict: Optional[str] = None
    score: Optional[float] = None

class CreateCampaignRequest(BaseModel):
    name: str
    goal_type: str = "hybrid"  # email, linkedin, hybrid
    target_persona: Optional[str] = None
    lead_ids: List[str] = []
    product_info: Optional[Dict[str, Any]] = None

class UpdateCampaignRequest(BaseModel):
    name: Optional[str] = None
    goal_type: Optional[str] = None
    status: Optional[str] = None
    target_persona: Optional[str] = None
    lead_ids: Optional[List[str]] = None
    product_info: Optional[Dict[str, Any]] = None

class AddMessageStepRequest(BaseModel):
    step_number: int
    channel: str  # email or linkedin
    delay_days: int = 0
    variants: List[Dict[str, Any]]  # List of {name, subject, content}

class SetCampaignScheduleRequest(BaseModel):
    start_date: str  # ISO format
    timezone: str = "UTC"
    sending_days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    sending_hours: List[int] = [9, 10, 11, 14, 15, 16]
    max_daily_linkedin: int = 50
    max_daily_email: int = 100
    randomize_timing: bool = True

class GenerateMessageRequest(BaseModel):
    campaign_id: str
    step_number: int
    lead_id: str  # To use persona
    variant_name: str  # "Variant A" or "Variant B"

class BulkGenerateMessagesRequest(BaseModel):
    campaign_id: str
    step_number: int
    variant_name: str
    lead_ids: List[str]  # Generate for multiple leads

class AIAgentConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    campaign_id: Optional[str] = None
    step_1_system_prompt: str = "You are an expert B2B sales copywriter for initial outreach. Create personalized, engaging first contact messages."
    step_1_instructions: str = "Keep under 100 words. Establish relevance. End with soft question."
    step_2_system_prompt: str = "You are an expert B2B follow-up specialist. Create helpful, value-focused messages."
    step_2_instructions: str = "Reference first message. Share specific benefit. Include social proof or metric."
    step_3_system_prompt: str = "You are an expert B2B closer. Create direct, respectful final touchpoints."
    step_3_instructions: str = "Acknowledge silence. Provide clear CTA. Create appropriate urgency."
    model_provider: str = "openai"  # openai or gemini
    model_name: str = "gpt-5"
    temperature: float = 0.7
    max_tokens: int = 500

class AIUsageLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    campaign_id: str
    operation: str  # "generate_message", "generate_persona", "generate_insights"
    provider: str  # openai, gemini, perplexity
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AddMessageVariantRequest(BaseModel):
    name: str
    subject: Optional[str] = None
    content: str
    channel: str

class ResearchPersonaRequest(BaseModel):
    lead_id: str
    linkedin_url: str

class GenerateInsightsRequest(BaseModel):
    campaign_id: Optional[str] = None
    time_period: str = "week"  # day, week, month, all

class BulkImportLeadsRequest(BaseModel):
    leads: List[Dict[str, Any]]
    campaign_id: Optional[str] = None

class GoogleSheetsConnectRequest(BaseModel):
    spreadsheet_url: str
    
class APIKeysUpdate(BaseModel):
    perplexity_key: Optional[str] = None
    openai_key: Optional[str] = None
    gemini_key: Optional[str] = None
    resend_key: Optional[str] = None

# ============ AUTH HELPERS ============

async def get_current_user(request: Request, session_token: Optional[str] = Cookie(None)) -> User:
    """
    Get current user from session token (cookie or header)
    """
    token = session_token
    
    # Fallback to Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check session
    session = await db.user_sessions.find_one({"session_token": token})
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Handle both naive and aware datetimes
    expires_at = session["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Get user
    user_doc = await db.users.find_one({"id": session["user_id"]})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    return User(**user_doc)

# ============ AUTH ROUTES ============

@api_router.post("/auth/session")
async def create_session(response: Response):
    """
    Process session ID from Emergent Auth and create session
    Called by frontend after OAuth redirect
    """
    # This endpoint receives X-Session-ID header from frontend
    return {"message": "This endpoint should be called by frontend with X-Session-ID header"}

@api_router.post("/auth/session-data")
async def get_session_data(request: Request, response: Response):
    """
    Exchange session_id for user data and session_token
    """
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header required")
    
    # Call Emergent Auth service
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id},
                timeout=10.0
            )
            auth_response.raise_for_status()
            user_data = auth_response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Auth service error: {str(e)}")
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data["email"]})
    
    if not existing_user:
        # Create new user
        user = User(
            email=user_data["email"],
            name=user_data["name"],
            picture=user_data.get("picture")
        )
        await db.users.insert_one(user.model_dump())
    else:
        user = User(**existing_user)
    
    # Create session
    session_token = user_data["session_token"]
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    session = UserSession(
        user_id=user.id,
        session_token=session_token,
        expires_at=expires_at
    )
    
    await db.user_sessions.insert_one(session.model_dump())
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7*24*60*60,
        path="/"
    )
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "role": user.role,
        "session_token": session_token
    }

@api_router.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.post("/auth/logout")
async def logout(response: Response, current_user: User = Depends(get_current_user), session_token: Optional[str] = Cookie(None)):
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out successfully"}

# ============ LEAD ROUTES ============

@api_router.post("/leads", response_model=Lead)
async def create_lead(lead_data: CreateLeadRequest, current_user: User = Depends(get_current_user)):
    lead = Lead(
        name=lead_data.name,
        email=lead_data.email,
        linkedin_url=lead_data.linkedin_url,
        company=lead_data.company,
        title=lead_data.title,
        campaign_id=lead_data.campaign_id,
        user_id=current_user.id
    )
    await db.leads.insert_one(lead.model_dump())
    return lead

@api_router.get("/leads", response_model=List[Lead])
async def get_leads(campaign_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {"user_id": current_user.id}
    if campaign_id:
        query["campaign_id"] = campaign_id
    
    leads = await db.leads.find(query).to_list(1000)
    return [Lead(**lead) for lead in leads]

@api_router.get("/leads/{lead_id}", response_model=Lead)
async def get_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id, "user_id": current_user.id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return Lead(**lead)

@api_router.patch("/leads/{lead_id}", response_model=Lead)
async def update_lead(lead_id: str, update_data: UpdateLeadRequest, current_user: User = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id, "user_id": current_user.id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if update_dict:
        await db.leads.update_one({"id": lead_id}, {"$set": update_dict})
        lead.update(update_dict)
    
    return Lead(**lead)

@api_router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    result = await db.leads.delete_one({"id": lead_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead deleted successfully"}

@api_router.post("/leads/import")
async def bulk_import_leads(import_data: BulkImportLeadsRequest, current_user: User = Depends(get_current_user)):
    """
    Bulk import leads from CSV or other sources
    """
    imported_count = 0
    leads_to_insert = []
    
    for lead_data in import_data.leads:
        lead = Lead(
            name=lead_data.get("name", ""),
            email=lead_data.get("email"),
            linkedin_url=lead_data.get("linkedin_url"),
            company=lead_data.get("company"),
            title=lead_data.get("title"),
            campaign_id=import_data.campaign_id,
            user_id=current_user.id
        )
        leads_to_insert.append(lead.model_dump())
        imported_count += 1
    
    if leads_to_insert:
        await db.leads.insert_many(leads_to_insert)
    
    return {"message": f"Successfully imported {imported_count} leads", "count": imported_count}

# ============ CAMPAIGN ROUTES ============

@api_router.post("/campaigns", response_model=Campaign)
async def create_campaign(campaign_data: CreateCampaignRequest, current_user: User = Depends(get_current_user)):
    campaign = Campaign(
        name=campaign_data.name,
        goal_type=campaign_data.goal_type,
        target_persona=campaign_data.target_persona,
        lead_ids=campaign_data.lead_ids,
        user_id=current_user.id
    )
    await db.campaigns.insert_one(campaign.model_dump())
    return campaign

@api_router.get("/campaigns", response_model=List[Campaign])
async def get_campaigns(current_user: User = Depends(get_current_user)):
    campaigns = await db.campaigns.find({"user_id": current_user.id}).to_list(1000)
    return [Campaign(**c) for c in campaigns]

@api_router.get("/campaigns/{campaign_id}", response_model=Campaign)
async def get_campaign(campaign_id: str, current_user: User = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return Campaign(**campaign)

@api_router.patch("/campaigns/{campaign_id}", response_model=Campaign)
async def update_campaign(campaign_id: str, update_data: UpdateCampaignRequest, current_user: User = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if update_dict:
        update_dict["updated_at"] = datetime.now(timezone.utc)
        await db.campaigns.update_one({"id": campaign_id}, {"$set": update_dict})
        campaign.update(update_dict)
    
    return Campaign(**campaign)

@api_router.post("/campaigns/{campaign_id}/steps")
async def add_campaign_step(campaign_id: str, step_data: AddMessageStepRequest, current_user: User = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    step = {
        "id": str(uuid.uuid4()),
        "step_number": step_data.step_number,
        "channel": step_data.channel,
        "delay_days": step_data.delay_days,
        "variants": step_data.variants
    }
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$push": {"message_steps": step}}
    )
    
    return {"message": "Step added successfully", "step": step}

@api_router.post("/campaigns/{campaign_id}/schedule")
async def set_campaign_schedule(campaign_id: str, schedule_data: SetCampaignScheduleRequest, current_user: User = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    schedule = schedule_data.model_dump()
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"schedule": schedule}}
    )
    
    return {"message": "Schedule set successfully", "schedule": schedule}

@api_router.post("/campaigns/{campaign_id}/validate")
async def validate_campaign(campaign_id: str, current_user: User = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign_service = CampaignService(db)
    errors = campaign_service.validate_campaign(campaign)
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"validation_errors": errors}}
    )
    
    return {"valid": len(errors) == 0, "errors": errors}

@api_router.post("/campaigns/{campaign_id}/activate")
async def activate_campaign(campaign_id: str, current_user: User = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Validate first
    campaign_service = CampaignService(db)
    errors = campaign_service.validate_campaign(campaign)
    
    if errors:
        return {"success": False, "errors": errors}
    
    # Set status to validating then active
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"status": "active", "validation_errors": []}}
    )
    
    return {"success": True, "message": "Campaign activated successfully"}

@api_router.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(campaign_id: str, current_user: User = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get executions
    executions = await db.campaign_executions.find({"campaign_id": campaign_id}).to_list(1000)
    
    # Calculate metrics
    campaign_service = CampaignService(db)
    metrics = campaign_service.calculate_metrics(campaign_id, executions)
    
    # Calculate AI score
    ai_score = campaign_service.calculate_ai_score(metrics)
    verdict = campaign_service.determine_verdict(ai_score)
    
    metrics["ai_score"] = ai_score
    metrics["verdict"] = verdict
    
    # Update campaign metrics
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"metrics": metrics}}
    )
    
    # Get variant performance
    variant_performance = []
    for step in campaign.get("message_steps", []):
        for variant in step.get("variants", []):
            variant_execs = [e for e in executions if e.get("variant_id") == variant.get("id")]
            variant_metrics = campaign_service.calculate_metrics(campaign_id, variant_execs)
            variant_performance.append({
                "step": step["step_number"],
                "variant": variant["name"],
                "variant_id": variant["id"],
                "metrics": variant_metrics
            })
    
    return {
        "campaign": campaign,
        "overall_metrics": metrics,
        "variant_performance": variant_performance,
        "total_executions": len(executions)
    }

@api_router.post("/campaigns/{campaign_id}/sync-sheets")
async def sync_campaign_to_sheets(campaign_id: str, current_user: User = Depends(get_current_user)):
    campaign_service = CampaignService(db)
    result = await campaign_service.sync_to_google_sheets(campaign_id, current_user.id)
    return result

@api_router.post("/campaigns/generate-message")
async def generate_ai_message(request: GenerateMessageRequest, current_user: User = Depends(get_current_user)):
    """
    Generate AI-powered message for campaign step based on persona and product info
    """
    # Get campaign
    campaign = await db.campaigns.find_one({"id": request.campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get lead for persona
    lead = await db.leads.find_one({"id": request.lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get product info
    product_info = campaign.get("product_info", {})
    product_name = product_info.get("name", "our product")
    product_description = product_info.get("description", "")
    product_benefits = product_info.get("benefits", "")
    product_cta = product_info.get("cta", "learn more")
    
    # Get persona
    persona = lead.get("persona", "Professional contact")
    lead_name = lead.get("name", "")
    lead_title = lead.get("title", "")
    lead_company = lead.get("company", "")
    
    # Determine step context
    step_contexts = {
        1: {
            "goal": "Initial introduction and value proposition",
            "tone": "Friendly, professional, brief",
            "focus": "Establish relevance and pique interest",
            "best_practices": "Personalize with their role, keep under 100 words, end with soft question"
        },
        2: {
            "goal": "Follow-up with specific value and social proof",
            "tone": "Helpful, consultative",
            "focus": "Address potential pain points, provide proof/credibility",
            "best_practices": "Reference first message, share specific benefit, include case study or metric"
        },
        3: {
            "goal": "Final touchpoint with clear call-to-action",
            "tone": "Direct but respectful",
            "focus": "Create urgency, offer easy next step",
            "best_practices": "Acknowledge silence, provide clear CTA, give timeline/scarcity"
        }
    }
    
    step_context = step_contexts.get(request.step_number, step_contexts[1])
    channel = campaign.get("goal_type", "email")
    
    # Generate message using GPT-5
    try:
        llm_key = os.getenv("EMERGENT_LLM_KEY")
        chat = LlmChat(
            api_key=llm_key,
            session_id=f"msg-gen-{current_user.id}",
            system_message="You are an expert B2B sales copywriter specializing in personalized outreach. Create compelling, natural-sounding messages that feel authentic and personalized."
        ).with_model("openai", "gpt-5")
        
        generation_prompt = f"""Create a {channel} outreach message for Step {request.step_number} ({request.variant_name}).

LEAD INFORMATION:
- Name: {lead_name}
- Title: {lead_title}
- Company: {lead_company}
- Persona: {persona}

PRODUCT INFORMATION:
- Product: {product_name}
- Description: {product_description}
- Key Benefits: {product_benefits}
- Call-to-Action: {product_cta}

STEP {request.step_number} CONTEXT:
- Goal: {step_context['goal']}
- Tone: {step_context['tone']}
- Focus: {step_context['focus']}
- Best Practices: {step_context['best_practices']}

REQUIREMENTS:
1. Personalize using lead's name, title, and company
2. Reference their persona/role naturally
3. Highlight product benefit most relevant to their role
4. Match the tone and goal for Step {request.step_number}
5. {"Include subject line and body" if channel == "email" else "LinkedIn message only (no subject)"}
6. Keep concise ({"under 150 words" if request.step_number == 1 else "under 200 words"})
7. Use personalization tokens: {{{{first_name}}}}, {{{{company}}}}, {{{{job_title}}}}

{"Format as JSON: {subject: string, body: string}" if channel == "email" else "Return just the message body text"}
"""
        
        message_obj = UserMessage(text=generation_prompt)
        ai_response = await chat.send_message(message_obj)
        
        # Parse response
        if channel == "email":
            import json
            try:
                result = json.loads(ai_response)
                return {
                    "subject": result.get("subject", ""),
                    "content": result.get("body", ai_response),
                    "variant": request.variant_name
                }
            except:
                # Fallback if not JSON
                lines = ai_response.split('\n', 1)
                return {
                    "subject": lines[0].replace("Subject:", "").strip() if len(lines) > 0 else "Outreach",
                    "content": lines[1].strip() if len(lines) > 1 else ai_response,
                    "variant": request.variant_name
                }
        else:
            return {
                "content": ai_response,
                "variant": request.variant_name
            }
    
    except Exception as e:
        logging.error(f"AI message generation error: {str(e)}")
        # Return fallback template
        return {
            "subject": f"Quick question, {{{{first_name}}}}",
            "content": f"Hi {{{{first_name}}}},\n\nI noticed your work as {{{{job_title}}}} at {{{{company}}}}.\n\nI thought {product_name} might be relevant for your team.\n\nWould you be open to a quick chat?",
            "variant": request.variant_name,
            "note": "AI generation unavailable - using template"
        }

@api_router.patch("/campaigns/{campaign_id}", response_model=Campaign)
async def update_campaign_old(campaign_id: str, update_data: UpdateCampaignRequest, current_user: User = Depends(get_current_user)):
    # Keeping old endpoint for compatibility
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if update_dict:
        await db.campaigns.update_one({"id": campaign_id}, {"$set": update_dict})
        campaign.update(update_dict)
    
    return Campaign(**campaign)

@api_router.post("/campaigns/{campaign_id}/variants", response_model=Campaign)
async def add_message_variant(campaign_id: str, variant_data: AddMessageVariantRequest, current_user: User = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    variant = MessageVariant(
        name=variant_data.name,
        subject=variant_data.subject,
        content=variant_data.content,
        channel=variant_data.channel
    )
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$push": {"message_variants": variant.model_dump()}}
    )
    
    campaign = await db.campaigns.find_one({"id": campaign_id})
    return Campaign(**campaign)

@api_router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str, current_user: User = Depends(get_current_user)):
    result = await db.campaigns.delete_one({"id": campaign_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"message": "Campaign deleted successfully"}

# ============ PERSONA RESEARCH ROUTES ============

@api_router.post("/research/persona")
async def research_persona(request: ResearchPersonaRequest, current_user: User = Depends(get_current_user)):
    """
    Research person using Perplexity and generate persona
    """
    lead = await db.leads.find_one({"id": request.lead_id, "user_id": current_user.id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get user's API key or use environment key
    user_keys = await db.integrations.find_one({"user_id": current_user.id, "type": "api_keys"})
    perplexity_api_key = user_keys.get("perplexity_key") if user_keys else None
    
    if not perplexity_api_key:
        perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    
    if not perplexity_api_key:
        return {
            "message": "Perplexity API key not configured. Add your key in Settings.",
            "persona": "Professional with experience in their field. Configure Perplexity API to get detailed persona."
        }
    
    # Extract person info from lead
    person_name = lead.get("name", "")
    company = lead.get("company", "")
    title = lead.get("title", "")
    
    # Use Perplexity API for research - search by name and company, not LinkedIn URL
    try:
        async with httpx.AsyncClient() as client:
            # Search for the person using their name and company
            research_query = f"""Search for information about {person_name}, {title} at {company}.

Find and analyze:
- Their professional background and career history
- Current role and responsibilities at {company}
- Areas of expertise and specialization
- Public speaking, articles, or thought leadership
- Professional interests and goals
- Company information and recent news about {company}
- Industry trends they're likely focused on

Based on this research, create a CONCISE professional persona in ONE PARAGRAPH (4-5 sentences max) that includes:
- Their role and experience level
- Communication style (formal/casual, technical/business-focused)
- Top 2-3 professional priorities or goals
- Main pain point or challenge
- Best outreach approach

Keep it brief, actionable, and focused. Do not write multiple paragraphs or sections."""
            
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {perplexity_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar-pro",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert B2B sales researcher. Create concise, single-paragraph professional personas. Never use multiple paragraphs or bullet points - keep it to 4-5 sentences maximum in ONE paragraph."
                        },
                        {
                            "role": "user",
                            "content": research_query
                        }
                    ],
                    "return_images": False,
                    "return_related_questions": False,
                    "search_recency_filter": "month",
                    "temperature": 0.7
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                persona = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Also get citations for transparency
                citations = result.get("citations", [])
                persona_with_sources = persona
                if citations:
                    persona_with_sources += f"\n\nSources: {', '.join(citations[:3])}"
                
                # Calculate a basic score
                score = 7.5  # Default score, could be enhanced with sentiment analysis
                
                # Update lead with persona and score
                await db.leads.update_one(
                    {"id": request.lead_id},
                    {"$set": {
                        "persona": persona_with_sources,
                        "score": score,
                        "date_contacted": datetime.now(timezone.utc)
                    }}
                )
                
                return {
                    "lead_id": request.lead_id,
                    "persona": persona_with_sources,
                    "score": score,
                    "citations": citations[:5]
                }
            else:
                error_detail = f"API returned status {response.status_code}"
                logging.error(f"Perplexity API error: {error_detail}")
                return {
                    "message": f"Research service error: {error_detail}",
                    "persona": "Unable to complete research. Please verify your API key is valid."
                }
    except httpx.TimeoutException:
        logging.error("Perplexity API timeout")
        return {
            "message": "Research timed out. Please try again.",
            "persona": "Research in progress - please retry in a moment."
        }
    except Exception as e:
        logging.error(f"Perplexity API error: {str(e)}")
        return {
            "message": f"Research error: {str(e)}",
            "persona": "Unable to complete research. Please check your API key and try again."
        }

# ============ ANALYTICS & AI INSIGHTS ============

@api_router.get("/analytics/overview")
async def get_analytics_overview(current_user: User = Depends(get_current_user)):
    # Get all user campaigns
    campaigns = await db.campaigns.find({"user_id": current_user.id}).to_list(1000)
    leads = await db.leads.find({"user_id": current_user.id}).to_list(1000)
    
    total_campaigns = len(campaigns)
    total_leads = len(leads)
    contacted_leads = len([l for l in leads if l.get("date_contacted")])
    calls_booked = len([l for l in leads if l.get("call_booked")])
    
    # Calculate metrics from message variants
    total_sent = 0
    total_opened = 0
    total_replied = 0
    
    for campaign in campaigns:
        for variant in campaign.get("message_variants", []):
            metrics = variant.get("metrics", {})
            total_sent += metrics.get("sent", 0)
            total_opened += metrics.get("opened", 0)
            total_replied += metrics.get("replied", 0)
    
    open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
    reply_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0
    conversion_rate = (calls_booked / contacted_leads * 100) if contacted_leads > 0 else 0
    
    return {
        "total_campaigns": total_campaigns,
        "total_leads": total_leads,
        "contacted_leads": contacted_leads,
        "calls_booked": calls_booked,
        "total_sent": total_sent,
        "total_opened": total_opened,
        "total_replied": total_replied,
        "open_rate": round(open_rate, 2),
        "reply_rate": round(reply_rate, 2),
        "conversion_rate": round(conversion_rate, 2)
    }

@api_router.post("/analytics/insights")
async def generate_insights(request: GenerateInsightsRequest, current_user: User = Depends(get_current_user)):
    """
    Generate AI insights using GPT-5
    """
    # Get campaign data
    query = {"user_id": current_user.id}
    if request.campaign_id:
        query["id"] = request.campaign_id
    
    campaigns = await db.campaigns.find(query).to_list(1000)
    leads = await db.leads.find({"user_id": current_user.id}).to_list(1000)
    
    # Prepare data summary for AI
    data_summary = {
        "campaigns": len(campaigns),
        "leads": len(leads),
        "variants": sum(len(c.get("message_variants", [])) for c in campaigns),
        "contacted": len([l for l in leads if l.get("date_contacted")]),
        "calls_booked": len([l for l in leads if l.get("call_booked")])
    }
    
    # Use GPT-5 for analysis
    try:
        llm_key = os.getenv("EMERGENT_LLM_KEY")
        chat = LlmChat(
            api_key=llm_key,
            session_id=f"insights-{current_user.id}",
            system_message="You are an expert marketing analyst specializing in outreach campaigns and A/B testing. Provide actionable insights based on campaign data."
        ).with_model("openai", "gpt-5")
        
        analysis_prompt = f"""Analyze this outreach campaign data and provide 3-5 key insights:

Campaign Overview:
- Total campaigns: {data_summary['campaigns']}
- Message variants tested: {data_summary['variants']}
- Leads contacted: {data_summary['contacted']}
- Calls booked: {data_summary['calls_booked']}
- Conversion rate: {(data_summary['calls_booked'] / data_summary['contacted'] * 100) if data_summary['contacted'] > 0 else 0:.1f}%

Provide insights on:
1. Overall performance assessment
2. A/B testing recommendations
3. Best performing patterns (if visible)
4. Optimization suggestions

Format as JSON with: {{"insights": [{{"title": "...", "description": "...", "type": "performance|optimization|trend"}}]}}
"""
        
        message = UserMessage(text=analysis_prompt)
        response = await chat.send_message(message)
        
        # Parse response
        import json
        try:
            insights_data = json.loads(response)
            insights = insights_data.get("insights", [])
        except:
            # Fallback if not JSON
            insights = [{
                "title": "Campaign Analysis",
                "description": response[:500],
                "type": "performance"
            }]
        
        # Store insights
        for insight_data in insights:
            insight = AIInsight(
                campaign_id=request.campaign_id,
                insight_type=insight_data.get("type", "performance"),
                title=insight_data.get("title", "Insight"),
                description=insight_data.get("description", ""),
                data=data_summary
            )
            await db.ai_insights.insert_one(insight.model_dump())
        
        return {"insights": insights}
    
    except Exception as e:
        logging.error(f"AI insight generation error: {str(e)}")
        # Return default insights
        return {
            "insights": [
                {
                    "title": "Campaign Performance",
                    "description": f"You have {data_summary['campaigns']} active campaigns with {data_summary['contacted']} leads contacted and {data_summary['calls_booked']} calls booked.",
                    "type": "performance"
                },
                {
                    "title": "Optimization Opportunity",
                    "description": "Consider testing more message variants to improve conversion rates. A/B testing different approaches can help identify what resonates best with your audience.",
                    "type": "optimization"
                }
            ]
        }

@api_router.get("/analytics/insights")
async def get_insights(campaign_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {}
    if campaign_id:
        query["campaign_id"] = campaign_id
    
    insights = await db.ai_insights.find(query).sort("generated_at", -1).limit(10).to_list(10)
    return [AIInsight(**i) for i in insights]

# ============ GOOGLE SHEETS INTEGRATION ============

@api_router.post("/integrations/google-sheets/connect")
async def connect_google_sheets(request: GoogleSheetsConnectRequest, current_user: User = Depends(get_current_user)):
    """
    Connect Google Sheets for CRM sync
    """
    # Extract sheet ID from URL
    import re
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', request.spreadsheet_url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid Google Sheets URL")
    
    sheet_id = match.group(1)
    
    # Store sheet connection
    await db.integrations.update_one(
        {"user_id": current_user.id, "type": "google_sheets"},
        {"$set": {
            "user_id": current_user.id,
            "type": "google_sheets",
            "sheet_id": sheet_id,
            "sheet_url": request.spreadsheet_url,
            "connected_at": datetime.now(timezone.utc),
            "status": "connected"
        }},
        upsert=True
    )
    
    return {"message": "Google Sheets connected successfully", "sheet_id": sheet_id}

@api_router.get("/integrations/google-sheets/status")
async def get_google_sheets_status(current_user: User = Depends(get_current_user)):
    """
    Get Google Sheets connection status
    """
    integration = await db.integrations.find_one({
        "user_id": current_user.id,
        "type": "google_sheets"
    })
    
    if integration:
        return {
            "connected": True,
            "sheet_url": integration.get("sheet_url"),
            "connected_at": integration.get("connected_at")
        }
    
    return {"connected": False}

@api_router.post("/integrations/google-sheets/sync")
async def sync_google_sheets(current_user: User = Depends(get_current_user)):
    """
    Sync leads to Google Sheets
    """
    # Get sheet connection
    integration = await db.integrations.find_one({
        "user_id": current_user.id,
        "type": "google_sheets"
    })
    
    if not integration:
        raise HTTPException(status_code=404, detail="Google Sheets not connected")
    
    # Get all leads
    leads = await db.leads.find({"user_id": current_user.id}).to_list(1000)
    
    # In a real implementation, this would use Google Sheets API
    # For now, we'll return a mock response
    return {
        "message": "Sync complete",
        "synced_leads": len(leads),
        "note": "Add Google Sheets API credentials to enable live sync"
    }

# ============ SETTINGS & API KEYS ============

@api_router.get("/settings/integrations")
async def get_integration_settings(current_user: User = Depends(get_current_user)):
    """
    Get integration status and settings
    """
    # Check which API keys are configured
    perplexity_configured = bool(os.getenv("PERPLEXITY_API_KEY"))
    emergent_llm_configured = bool(os.getenv("EMERGENT_LLM_KEY"))
    
    # Check Google Sheets
    sheets_integration = await db.integrations.find_one({
        "user_id": current_user.id,
        "type": "google_sheets"
    })
    
    # Check LinkedIn (mock for now)
    linkedin_integration = await db.integrations.find_one({
        "user_id": current_user.id,
        "type": "linkedin"
    })
    
    return {
        "ai_models": {
            "gpt5": {"enabled": emergent_llm_configured, "provider": "openai", "status": "ready" if emergent_llm_configured else "not_configured"},
            "gemini": {"enabled": emergent_llm_configured, "provider": "google", "status": "ready" if emergent_llm_configured else "not_configured"},
            "perplexity": {"enabled": perplexity_configured, "status": "ready" if perplexity_configured else "not_configured"}
        },
        "integrations": {
            "google_sheets": {
                "connected": bool(sheets_integration),
                "status": sheets_integration.get("status") if sheets_integration else "not_connected"
            },
            "linkedin": {
                "connected": bool(linkedin_integration),
                "status": "mock_mode"
            },
            "email": {
                "connected": False,
                "status": "not_configured",
                "note": "Email service pending configuration"
            }
        }
    }

@api_router.post("/settings/api-keys")
async def update_api_keys(keys: APIKeysUpdate, current_user: User = Depends(get_current_user)):
    """
    Update API keys
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Store API keys in user's integration settings
    updates = {}
    if keys.perplexity_key:
        updates["perplexity_key"] = keys.perplexity_key
    if keys.openai_key:
        updates["openai_key"] = keys.openai_key
    if keys.gemini_key:
        updates["gemini_key"] = keys.gemini_key
    if keys.resend_key:
        updates["resend_key"] = keys.resend_key
    
    if updates:
        await db.integrations.update_one(
            {"user_id": current_user.id, "type": "api_keys"},
            {"$set": updates},
            upsert=True
        )
    
    return {"message": "API keys updated successfully", "keys_updated": list(updates.keys())}

@api_router.get("/settings/api-keys")
async def get_api_keys(current_user: User = Depends(get_current_user)):
    """
    Get configured API keys (masked)
    """
    integration = await db.integrations.find_one({
        "user_id": current_user.id,
        "type": "api_keys"
    })
    
    if not integration:
        return {
            "perplexity_configured": False,
            "openai_configured": False,
            "gemini_configured": False,
            "resend_configured": False
        }
    
    return {
        "perplexity_configured": bool(integration.get("perplexity_key")),
        "openai_configured": bool(integration.get("openai_key")),
        "gemini_configured": bool(integration.get("gemini_key")),
        "resend_configured": bool(integration.get("resend_key")),
        "perplexity_key_preview": integration.get("perplexity_key", "")[:8] + "..." if integration.get("perplexity_key") else None,
        "openai_key_preview": integration.get("openai_key", "")[:8] + "..." if integration.get("openai_key") else None,
        "gemini_key_preview": integration.get("gemini_key", "")[:8] + "..." if integration.get("gemini_key") else None,
        "resend_key_preview": integration.get("resend_key", "")[:8] + "..." if integration.get("resend_key") else None
    }

# ============ MESSAGES / INBOX ============

class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    lead_id: str
    step_number: int
    variant_id: str
    channel: str
    direction: str  # outgoing or incoming
    subject: Optional[str] = None
    content: str
    status: str  # sent, delivered, opened, replied, failed
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    user_id: str

class SendReplyRequest(BaseModel):
    message_id: str  # Original message to reply to
    content: str

@api_router.get("/messages")
async def get_messages(
    campaign_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    direction: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get messages (inbox)
    """
    query = {"user_id": current_user.id}
    if campaign_id:
        query["campaign_id"] = campaign_id
    if lead_id:
        query["lead_id"] = lead_id
    if direction:
        query["direction"] = direction
    
    messages = await db.messages.find(query, {"_id": 0}).sort("sent_at", -1).limit(100).to_list(100)
    
    # Enrich with lead info
    for msg in messages:
        lead = await db.leads.find_one({"id": msg["lead_id"]}, {"_id": 0})
        if lead:
            msg["lead_name"] = lead.get("name")
            msg["lead_email"] = lead.get("email")
            msg["lead_company"] = lead.get("company")
    
    return messages

@api_router.post("/messages/reply")
async def send_reply(reply_data: SendReplyRequest, current_user: User = Depends(get_current_user)):
    """
    Send reply to an incoming message
    """
    # Get original message
    original = await db.messages.find_one({"id": reply_data.message_id})
    if not original:
        raise HTTPException(status_code=404, detail="Original message not found")
    
    # Create reply message
    reply = Message(
        campaign_id=original["campaign_id"],
        lead_id=original["lead_id"],
        step_number=original["step_number"],
        variant_id=original["variant_id"],
        channel=original["channel"],
        direction="outgoing",
        content=reply_data.content,
        status="sent",
        sent_at=datetime.now(timezone.utc),
        user_id=current_user.id
    )
    
    await db.messages.insert_one(reply.model_dump())
    
    return {"message": "Reply sent successfully", "reply_id": reply.id}

# Mock endpoint to simulate incoming messages
@api_router.post("/messages/simulate-incoming")
async def simulate_incoming_message(campaign_id: str, lead_id: str, content: str, current_user: User = Depends(get_current_user)):
    """
    Simulate an incoming reply (for testing)
    """
    msg = Message(
        campaign_id=campaign_id,
        lead_id=lead_id,
        step_number=1,
        variant_id="test",
        channel="email",
        direction="incoming",
        content=content,
        status="replied",
        sent_at=datetime.now(timezone.utc),
        replied_at=datetime.now(timezone.utc),
        user_id=current_user.id
    )
    
    await db.messages.insert_one(msg.model_dump())
    
    # Update lead status
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {"date_contacted": datetime.now(timezone.utc)}}
    )
    
    return {"message": "Incoming message simulated", "message_id": msg.id}

# ============ MOCK OUTREACH (Email/LinkedIn) ============

@api_router.post("/outreach/send")
async def send_outreach(campaign_id: str, lead_ids: List[str], variant_id: str, current_user: User = Depends(get_current_user)):
    """
    Send outreach messages via Email or LinkedIn
    """
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Find the message step and variant
    variant = None
    step_info = None
    for step in campaign.get("message_steps", []):
        for v in step.get("variants", []):
            if v["id"] == variant_id:
                variant = v
                step_info = step
                break
        if variant:
            break
    
    if not variant:
        raise HTTPException(status_code=404, detail="Message variant not found")
    
    sent_count = 0
    failed_count = 0
    channel = step_info.get("channel", "email")
    
    # Get leads
    leads = await db.leads.find({"id": {"$in": lead_ids}}).to_list(len(lead_ids))
    
    # Get Resend API key if email campaign
    resend_api_key = None
    if channel == "email":
        user_keys = await db.integrations.find_one({"user_id": current_user.id, "type": "api_keys"})
        resend_api_key = user_keys.get("resend_key") if user_keys else None
        
        if not resend_api_key:
            resend_api_key = os.getenv("RESEND_API_KEY")
    
    for lead in leads:
        # Apply personalization
        campaign_service = CampaignService(db)
        personalized_content = campaign_service.apply_personalization(variant["content"], lead)
        personalized_subject = campaign_service.apply_personalization(variant.get("subject", ""), lead) if variant.get("subject") else None
        
        if channel == "email" and resend_api_key:
            # Send via Resend
            try:
                resend.api_key = resend_api_key
                
                params = {
                    "from": "outreach@omnireach.ai",
                    "to": [lead.get("email")],
                    "subject": personalized_subject or "Outreach Message",
                    "html": f"<p>{personalized_content.replace(chr(10), '<br>')}</p>",
                    "tags": [
                        {"name": "campaign_id", "value": campaign_id},
                        {"name": "variant_id", "value": variant_id},
                        {"name": "lead_id", "value": lead.get("id")}
                    ]
                }
                
                email_response = resend.Emails.send(params)
                
                # Store message
                message = Message(
                    campaign_id=campaign_id,
                    lead_id=lead.get("id"),
                    step_number=step_info.get("step_number", 1),
                    variant_id=variant_id,
                    channel=channel,
                    direction="outgoing",
                    subject=personalized_subject,
                    content=personalized_content,
                    status="sent",
                    sent_at=datetime.now(timezone.utc),
                    user_id=current_user.id
                )
                await db.messages.insert_one(message.model_dump())
                
                sent_count += 1
            except Exception as e:
                logging.error(f"Email send error: {str(e)}")
                failed_count += 1
        else:
            # Mock send (LinkedIn or no API key)
            message = Message(
                campaign_id=campaign_id,
                lead_id=lead.get("id"),
                step_number=step_info.get("step_number", 1),
                variant_id=variant_id,
                channel=channel,
                direction="outgoing",
                subject=personalized_subject,
                content=personalized_content,
                status="sent",
                sent_at=datetime.now(timezone.utc),
                user_id=current_user.id
            )
            await db.messages.insert_one(message.model_dump())
            sent_count += 1
        
        # Update lead
        await db.leads.update_one(
            {"id": lead.get("id")},
            {"$set": {"date_contacted": datetime.now(timezone.utc), "campaign_id": campaign_id}}
        )
    
    # Update variant metrics
    for step in campaign.get("message_steps", []):
        for idx, v in enumerate(step.get("variants", [])):
            if v["id"] == variant_id:
                await db.campaigns.update_one(
                    {"id": campaign_id},
                    {"$inc": {f"message_steps.{campaign.get('message_steps', []).index(step)}.variants.{idx}.metrics.sent": sent_count}}
                )
                break
    
    return {
        "message": f"Sent {sent_count} messages via {channel}" + (f" ({failed_count} failed)" if failed_count > 0 else ""),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "channel": channel,
        "using_real_email": bool(channel == "email" and resend_api_key)
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
