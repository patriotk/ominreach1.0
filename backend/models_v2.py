from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
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

class MessageVariant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    subject: Optional[str] = None
    body: str
    reasoning: str = ""
    clarity_score: float = 0.0
    personalization_score: float = 0.0
    relevance_score: float = 0.0
    total_score: float = 0.0
    percentage: int = 50
    metrics: Dict[str, int] = Field(default_factory=lambda: {"sent": 0, "opened": 0, "replied": 0, "clicked": 0})

class CampaignStep(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int
    step_name: str
    purpose: str
    delay_days: int = 0
    send_window_start_hour: int = 9
    send_window_end_hour: int = 17
    best_practices: str = ""
    variants: List[MessageVariant] = []

class ProductInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = ""
    summary: str = ""
    differentiators: str = ""
    file_urls: List[str] = []
    key_features: List[str] = []
    parsed_content: str = ""  # Content from uploaded files

class AIAgentProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    tone: str = "professional"
    style: str = "medium"
    focus: str = "value_driven"
    avoid_words: List[str] = []
    brand_personality: str = ""
    model_provider: str = "openai"
    model_name: str = "gpt-5"
    temperature: float = 0.7
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EnhancedCampaign(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    campaign_type: str  # linkedin or email
    status: str = "draft"
    steps: List[CampaignStep] = []
    product_info: ProductInfo = Field(default_factory=ProductInfo)
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
    status: str = "draft"
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
    status: str = "scheduled"
    error: Optional[str] = None
    channel: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
