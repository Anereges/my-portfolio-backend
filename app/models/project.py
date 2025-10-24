from pydantic import BaseModel, Field, HttpUrl, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from bson import ObjectId

class ProjectStatus(str, Enum):
    PLANNING = "planning"
    DEVELOPMENT = "development"  # Changed from IN_PROGRESS
    TESTING = "testing"         # Added
    DEPLOYED = "deployed"       # Changed from COMPLETED
    MAINTENANCE = "maintenance"

class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=10, max_length=1000)
    short_description: Optional[str] = Field(None, min_length=10, max_length=200)  # Made optional
    technologies: List[str] = Field(..., min_items=1)
    category: str = Field(..., min_length=1, max_length=50)
    status: ProjectStatus = ProjectStatus.PLANNING  # Default to planning
    featured: bool = False
    github_url: Optional[str] = None  # Changed from HttpUrl to string for flexibility
    live_url: Optional[str] = None    # Changed from HttpUrl to string for flexibility
    demo_url: Optional[str] = None    # Changed from HttpUrl to string
    image_url: Optional[str] = None
    gallery: List[str] = Field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    client: Optional[str] = None
    challenges: List[str] = Field(default_factory=list)
    solutions: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    # Auto-generate short_description from description if not provided
    @validator('short_description', pre=True, always=True)
    def set_short_description(cls, v, values):
        if v is None and 'description' in values:
            # Take first 150 chars of description
            desc = values['description']
            if len(desc) > 150:
                return desc[:147] + '...'
            return desc
        return v

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=10, max_length=1000)
    short_description: Optional[str] = Field(None, min_length=10, max_length=200)
    technologies: Optional[List[str]] = None
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    status: Optional[ProjectStatus] = None
    featured: Optional[bool] = None
    github_url: Optional[str] = None  # Changed from HttpUrl
    live_url: Optional[str] = None    # Changed from HttpUrl
    demo_url: Optional[str] = None    # Changed from HttpUrl
    image_url: Optional[str] = None

    class Config:
        extra = 'ignore'  # Ignore extra fields

class ProjectInDB(ProjectBase):
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    views: int = Field(default=0)
    likes: int = Field(default=0)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True

class ProjectResponse(ProjectInDB):
    class Config:
        from_attributes = True