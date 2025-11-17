"""
LiquidOutreach - Complete Data Models
Persona-centric outreach orchestration system
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone
import uuid


# ============ PERSONA MODELS ============

class PersonaCredentials(BaseModel):
    """Email and Phantombuster credentials for a persona"""
    email: str
    email_oauth_token: Optional[str] = None  # OAuth token for email
    sendgrid_api_key: Optional[str] = None   # Or SendGrid if not using OAuth
    phantombuster_api_key: str
    phantom_connect_id: Optional[str] = None  # LinkedIn connect request phantom
    phantom_message_id: Optional[str] = None  # LinkedIn message phantom
    phantom_view_id: Optional[str] = None     # LinkedIn profile view phantom


class Persona(BaseModel):
    """A sales persona with dedicated email + LinkedIn accounts"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    credentials: PersonaCredentials
    assigned_user_id: Optional[str] = None  # Which salesperson owns this persona
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============ PROSPECT MODELS ============

class Prospect(BaseModel):
    """Master prospect record - single source of truth"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    first_name: str
    last_name: str
    email: str  # UNIQUE - used for duplicate checking
    linkedin_url: Optional[str] = None  # UNIQUE - used for duplicate checking
    company: Optional[str] = None
    title: Optional[str] = None
    
    # Status
    status: Literal[
        "NEW",                    # Just imported
        "ACTIVE",                 # In a sequence
        "PAUSED_AWAITING_WEBHOOK", # Waiting for Phantombuster
        "PAUSED_MANUAL_REVIEW",   # Failed step - needs attention
        "REPLIED",                # Prospect replied - paused
        "COMPLETED",              # Sequence finished
        "UNSUBSCRIBED"            # Opted out
    ] = "NEW"
    
    # Locking - CRITICAL for preventing cross-contamination
    assigned_persona_id: Optional[str] = None  # LOCKED to this persona
    locked_at: Optional[datetime] = None
    
    # Current sequence state
    current_campaign_id: Optional[str] = None
    current_step_id: Optional[str] = None
    next_step_due_at: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============ ACTIVITY LOG ============

class ActivityLog(BaseModel):
    """Unified timeline of all prospect interactions"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prospect_id: str
    persona_id: str  # Which persona performed this action
    campaign_id: Optional[str] = None
    step_id: Optional[str] = None
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    channel: Literal["EMAIL", "LINKEDIN", "MANUAL_CALL", "MANUAL_NOTE"]
    action: str  # e.g., "Email Sent", "Profile Viewed", "Connection Request Sent"
    status: Literal["COMPLETED", "FAILED", "PENDING"]
    
    details: Optional[str] = None  # Error messages, notes, etc.
    external_id: Optional[str] = None  # Phantombuster containerId or email message_id
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============ CAMPAIGN (SEQUENCE) MODELS ============

class Template(BaseModel):
    """Email or LinkedIn message template with merge tags"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    channel: Literal["EMAIL", "LINKEDIN"]
    action_type: Literal["EMAIL_SEND", "LINKEDIN_CONNECT", "LINKEDIN_MESSAGE"]
    
    email_subject: Optional[str] = None  # Only for emails
    body_text: str  # Supports merge tags: {{first_name}}, {{company}}, etc.
    
    created_by_user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CampaignStep(BaseModel):
    """Single step in a multi-channel sequence"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    step_number: int  # Order: 1, 2, 3, etc.
    
    channel: Literal["EMAIL", "LINKEDIN"]
    action: Literal["SEND_EMAIL", "VIEW_PROFILE", "SEND_CONNECT", "SEND_MESSAGE"]
    
    template_id: Optional[str] = None  # NULL for VIEW_PROFILE
    delay_in_days: int = 0  # Wait X days after previous step (0 for first step)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Campaign(BaseModel):
    """A multi-channel outreach sequence (the "playbook")"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: Literal["DRAFT", "ACTIVE", "ARCHIVED"] = "DRAFT"
    
    created_by_user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============ REQUEST/RESPONSE MODELS ============

class CreatePersonaRequest(BaseModel):
    """Request to create a new persona"""
    name: str
    email: str
    sendgrid_api_key: Optional[str] = None
    phantombuster_api_key: str
    phantom_connect_id: Optional[str] = None
    phantom_message_id: Optional[str] = None
    phantom_view_id: Optional[str] = None
    assigned_user_id: Optional[str] = None


class ImportProspectRequest(BaseModel):
    """Request to import a prospect"""
    first_name: str
    last_name: str
    email: str
    linkedin_url: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None


class EnrollProspectRequest(BaseModel):
    """Request to enroll prospect in a sequence with a persona"""
    prospect_id: str
    campaign_id: str
    persona_id: str


class CreateCampaignRequest(BaseModel):
    """Request to create a campaign"""
    name: str


class AddCampaignStepRequest(BaseModel):
    """Request to add a step to a campaign"""
    campaign_id: str
    channel: Literal["EMAIL", "LINKEDIN"]
    action: Literal["SEND_EMAIL", "VIEW_PROFILE", "SEND_CONNECT", "SEND_MESSAGE"]
    template_id: Optional[str] = None
    delay_in_days: int = 0


class CreateTemplateRequest(BaseModel):
    """Request to create a template"""
    name: str
    channel: Literal["EMAIL", "LINKEDIN"]
    action_type: Literal["EMAIL_SEND", "LINKEDIN_CONNECT", "LINKEDIN_MESSAGE"]
    email_subject: Optional[str] = None
    body_text: str


class ProspectControlRequest(BaseModel):
    """Request to manually control prospect status"""
    prospect_id: str
    action: Literal["PAUSE", "UNPAUSE", "RETRY_STEP"]


class PhantombusterWebhookPayload(BaseModel):
    """Webhook payload from Phantombuster"""
    containerId: str
    status: str  # "success" or "error"
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
