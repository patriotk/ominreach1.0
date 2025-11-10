from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, time
import uuid
from enum import Enum

class CampaignType(str, Enum):
    LINKEDIN = "linkedin"
    EMAIL = "email"

class AgentTone(str, Enum):
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    ENERGETIC = "energetic"
    PERSUASIVE = "persuasive"

class AgentStyle(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"

class AgentFocus(str, Enum):
    RELATIONSHIP = "relationship_building"
    VALUE = "value_driven"
    INSIGHTFUL = "insightful"

class CampaignStep(BaseModel):
    model_config = ConfigDict(extra="ignore")
    step_number: int
    step_name: str
    purpose: str
    delay_days: int = 0
    send_window_start: int = 9  # Hour (0-23)
    send_window_end: int = 17  # Hour (0-23)
    best_practices: str = ""
    variants: List[Dict[str, Any]] = []

class ProductInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    summary: str
    differentiators: str
    file_urls: List[str] = []  # Uploaded document URLs
    key_features: List[str] = []

class AIAgentProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    tone: AgentTone = AgentTone.PROFESSIONAL
    style: AgentStyle = AgentStyle.MEDIUM
    focus: AgentFocus = AgentFocus.VALUE
    avoid_words: List[str] = []
    brand_personality: str = ""
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EnhancedCampaign(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    campaign_type: CampaignType
    status: str = "draft"
    steps: List[CampaignStep] = []
    product_info: Optional[ProductInfo] = None
    agent_profile_id: Optional[str] = None
    daily_send_cap: int = 50
    lead_ids: List[str] = []
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GeneratedMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    lead_id: str
    step_number: int
    variant_index: int = 0
    subject: Optional[str] = None
    body: str
    reasoning: str = ""
    ai_score_clarity: float = 0.0
    ai_score_personalization: float = 0.0
    ai_score_relevance: float = 0.0
    ai_score_total: float = 0.0
    status: str = "draft"  # draft, scheduled, sent, failed
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SendJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    lead_id: str
    step_number: int
    message_id: str
    scheduled_for: datetime
    sent_at: Optional[datetime] = None
    status: str = "scheduled"  # scheduled, sent, failed, skipped
    error: Optional[str] = None
    channel: str  # linkedin or email
