"""
Campaign System V2 - Clean Models
Complete rewrite based on new requirements
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone
import uuid


# ============ CAMPAIGN MODELS ============

class StepAgentSettings(BaseModel):
    """AI Agent configuration per step"""
    tone: str = "professional"
    style: str = "concise"
    focus: str = "value-driven"
    avoid_words: List[str] = []
    brand_personality: str = ""


class CampaignStep(BaseModel):
    """Single step in 3-step sequence"""
    step_number: int  # 1, 2, or 3
    delay_days: int = 0
    delay_hours: int = 0
    window_start_hour: int = 9  # 24hr format
    window_end_hour: int = 17  # 24hr format
    agent_settings: StepAgentSettings = Field(default_factory=StepAgentSettings)
    best_practices_text: Optional[str] = None  # Parsed content from uploaded doc
    best_practices_file_url: Optional[str] = None  # Filename


class ProductInfo(BaseModel):
    """Structured product information from AI extraction"""
    product_name: str = ""
    summary: str = ""
    features: List[str] = []
    differentiators: List[str] = []
    call_to_action: str = ""
    raw_content: Optional[str] = None  # First 2000 chars from doc


class CampaignSchedule(BaseModel):
    """Campaign scheduling configuration"""
    start_date: str  # ISO date string YYYY-MM-DD
    start_time: str = "09:00"  # HH:MM format
    timezone: str = "America/New_York"
    daily_cap: int = 50


class Campaign(BaseModel):
    """Main Campaign Model V2"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    type: Literal["email", "linkedin"]
    
    # Product context
    product_info: ProductInfo = Field(default_factory=ProductInfo)
    
    # Always 3 steps
    steps: List[CampaignStep] = Field(default_factory=list)
    
    # Lead selection
    selected_lead_ids: List[str] = []
    lead_limit: int = 100
    
    # Scheduling
    schedule: Optional[CampaignSchedule] = None
    
    # Status
    status: Literal["draft", "test_phase", "approved", "active", "paused", "completed"] = "draft"
    
    # Test phase tracking
    test_lead_ids: List[str] = []  # First 3 leads for testing
    test_approved: bool = False
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============ MESSAGE MODELS ============

class Message(BaseModel):
    """Individual message for a lead at a specific step"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    lead_id: str
    step_number: int  # 1, 2, or 3
    channel: Literal["email", "linkedin"]
    
    # Content
    subject: Optional[str] = None  # Email only
    content: str
    
    # Status tracking
    status: Literal[
        "draft",       # Generated but not scheduled
        "pending",     # Scheduled, waiting to send
        "sent",        # Successfully sent
        "opened",      # Email opened (email only)
        "clicked",     # Link clicked (email only)
        "replied",     # Lead replied
        "failed"       # Send failed
    ] = "draft"
    
    # Scheduling
    send_window_start: Optional[datetime] = None
    send_window_end: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    
    # Execution tracking
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    
    # Integration tracking
    phantom_run_id: Optional[str] = None  # PhantomBuster execution ID
    resend_message_id: Optional[str] = None  # Resend message ID
    
    # AI metadata
    ai_score: Optional[Dict[str, Any]] = None
    generation_context: Optional[Dict[str, Any]] = None  # What was used to generate
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LeadCampaignState(BaseModel):
    """Track lead's state within a campaign"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    lead_id: str
    
    # State machine
    state: Literal[
        "not_contacted",   # Initial state
        "step1_sent",      # Step 1 sent
        "step2_sent",      # Step 2 sent
        "step3_sent",      # Step 3 sent (final)
        "replied",         # Lead replied (STOP)
        "completed",       # Sequence completed (no reply)
        "failed"           # Failed to send
    ] = "not_contacted"
    
    # Tracking
    last_message_sent_at: Optional[datetime] = None
    reply_received_at: Optional[datetime] = None
    sequence_stopped: bool = False  # True if replied (stops future sends)
    
    # Step message IDs
    step1_message_id: Optional[str] = None
    step2_message_id: Optional[str] = None
    step3_message_id: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============ REQUEST/RESPONSE MODELS ============

class CreateCampaignRequest(BaseModel):
    """Request to create new campaign"""
    name: str
    type: Literal["email", "linkedin"]
    lead_limit: int = 100


class UpdateCampaignRequest(BaseModel):
    """Request to update campaign"""
    name: Optional[str] = None
    selected_lead_ids: Optional[List[str]] = None
    lead_limit: Optional[int] = None
    schedule: Optional[CampaignSchedule] = None


class UpdateStepRequest(BaseModel):
    """Request to update a step"""
    delay_days: Optional[int] = None
    delay_hours: Optional[int] = None
    window_start_hour: Optional[int] = None
    window_end_hour: Optional[int] = None
    agent_settings: Optional[StepAgentSettings] = None


class GenerateMessageRequest(BaseModel):
    """Request to generate AI message for a lead at a step"""
    campaign_id: str
    lead_id: str
    step_number: int


class GenerateTestMessagesRequest(BaseModel):
    """Request to generate messages for 3-lead test phase"""
    campaign_id: str


class BulkGenerateMessagesRequest(BaseModel):
    """Request to generate messages for all leads"""
    campaign_id: str


class UpdateMessageRequest(BaseModel):
    """Request to update/edit a message"""
    subject: Optional[str] = None
    content: Optional[str] = None


class ActivateCampaignRequest(BaseModel):
    """Request to activate campaign (start sending)"""
    campaign_id: str


class CampaignAnalytics(BaseModel):
    """Campaign analytics summary"""
    campaign_id: str
    total_leads: int
    
    # Overall stats
    messages_sent: int = 0
    messages_opened: int = 0  # Email only
    messages_clicked: int = 0  # Email only
    messages_replied: int = 0
    
    # Step breakdown
    step1_sent: int = 0
    step2_sent: int = 0
    step3_sent: int = 0
    
    # Rates
    open_rate: float = 0.0  # Email only
    click_rate: float = 0.0  # Email only
    reply_rate: float = 0.0
    
    # Lead states
    leads_not_contacted: int = 0
    leads_in_progress: int = 0
    leads_replied: int = 0
    leads_completed: int = 0
    leads_failed: int = 0
