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
    status: str = "draft"  # draft, active, paused, completed
    message_variants: List[MessageVariant] = []
    target_persona: Optional[str] = None
    user_id: str
    team_id: Optional[str] = None
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
    target_persona: Optional[str] = None

class UpdateCampaignRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    target_persona: Optional[str] = None

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
    if not session or session["expires_at"] < datetime.now(timezone.utc):
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

# ============ CAMPAIGN ROUTES ============

@api_router.post("/campaigns", response_model=Campaign)
async def create_campaign(campaign_data: CreateCampaignRequest, current_user: User = Depends(get_current_user)):
    campaign = Campaign(
        name=campaign_data.name,
        target_persona=campaign_data.target_persona,
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
    Research LinkedIn profile using Perplexity and generate persona
    """
    lead = await db.leads.find_one({"id": request.lead_id, "user_id": current_user.id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    if not perplexity_api_key:
        return {"message": "Perplexity API key not configured. Using mock persona.", "persona": "Professional with 5+ years of experience. Goal-oriented and data-driven decision maker. Values efficiency and ROI. Key interests: growth, automation, scalability."}
    
    # Use Perplexity API for research
    try:
        async with httpx.AsyncClient() as client:
            research_query = f"Research the LinkedIn profile: {request.linkedin_url}. Provide a professional persona including: job title, company, key responsibilities, professional interests, communication style, likely goals and pain points."
            
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {perplexity_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar-pro",
                    "messages": [{"role": "user", "content": research_query}],
                    "return_images": False
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                persona = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Update lead with persona
                await db.leads.update_one(
                    {"id": request.lead_id},
                    {"$set": {"persona": persona, "date_contacted": datetime.now(timezone.utc)}}
                )
                
                return {"lead_id": request.lead_id, "persona": persona}
            else:
                return {"message": "Research service temporarily unavailable", "persona": "Professional profile - research pending"}
    except Exception as e:
        logging.error(f"Perplexity API error: {str(e)}")
        return {"message": f"Research error: {str(e)}", "persona": "Professional profile - research pending"}

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

# ============ MOCK OUTREACH (Email/LinkedIn) ============

@api_router.post("/outreach/send")
async def send_outreach(campaign_id: str, lead_ids: List[str], variant_id: str, current_user: User = Depends(get_current_user)):
    """
    Mock send outreach messages
    """
    campaign = await db.campaigns.find_one({"id": campaign_id, "user_id": current_user.id})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Find variant
    variant = None
    for v in campaign.get("message_variants", []):
        if v["id"] == variant_id:
            variant = v
            break
    
    if not variant:
        raise HTTPException(status_code=404, detail="Message variant not found")
    
    # Update metrics (mock)
    sent_count = len(lead_ids)
    
    # Update variant metrics
    await db.campaigns.update_one(
        {"id": campaign_id, "message_variants.id": variant_id},
        {"$inc": {"message_variants.$.metrics.sent": sent_count}}
    )
    
    # Update leads
    for lead_id in lead_ids:
        await db.leads.update_one(
            {"id": lead_id},
            {"$set": {"date_contacted": datetime.now(timezone.utc), "campaign_id": campaign_id}}
        )
    
    return {"message": f"Sent {sent_count} messages via {variant['channel']}", "sent_count": sent_count}

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
