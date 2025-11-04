from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

class MessageStep(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int
    channel: str  # email or linkedin
    delay_days: int = 0  # Days after previous step
    variants: List[Dict[str, Any]] = []  # List of variant objects

class MessageVariant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # "Variant A", "Variant B"
    subject: Optional[str] = None  # For emails
    content: str
    metrics: Dict[str, int] = Field(default_factory=lambda: {"sent": 0, "opened": 0, "replied": 0, "clicked": 0, "converted": 0})
    ai_score: Optional[float] = None
    is_winner: bool = False

class CampaignSchedule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    start_date: datetime
    timezone: str = "UTC"
    sending_days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    sending_hours: List[int] = [9, 10, 11, 14, 15, 16]  # Hours to send
    max_daily_linkedin: int = 50
    max_daily_email: int = 100
    randomize_timing: bool = True

class CampaignMetrics(BaseModel):
    model_config = ConfigDict(extra="ignore")
    messages_sent: int = 0
    messages_opened: int = 0
    messages_replied: int = 0
    messages_clicked: int = 0
    connections_accepted: int = 0
    calls_offered: int = 0
    calls_booked: int = 0
    avg_response_time_hours: Optional[float] = None
    avg_interest_to_close_days: Optional[float] = None
    open_rate: float = 0.0
    reply_rate: float = 0.0
    conversion_rate: float = 0.0
    ai_score: Optional[float] = None
    verdict: Optional[str] = None  # Success / Moderate / Poor

class Campaign(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    goal_type: str  # email, linkedin, hybrid
    status: str = "draft"  # draft, validating, active, paused, completed, archived
    target_persona: Optional[str] = None
    message_steps: List[MessageStep] = []
    schedule: Optional[CampaignSchedule] = None
    metrics: CampaignMetrics = Field(default_factory=CampaignMetrics)
    lead_ids: List[str] = []  # Associated lead IDs
    user_id: str
    team_id: Optional[str] = None
    validation_errors: List[str] = []
    last_sent_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CampaignExecution(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    lead_id: str
    step_number: int
    variant_id: str
    channel: str
    status: str  # pending, sent, opened, replied, failed
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    error: Optional[str] = None
