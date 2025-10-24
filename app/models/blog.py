from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from bson import ObjectId

class BlogStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class BlogCategory(str, Enum):
    TECHNOLOGY = "technology"
    SECURITY = "security"
    WEB_DEV = "web_development"
    CYBER_SECURITY = "cyber_security"
    PROGRAMMING = "programming"
    TUTORIAL = "tutorial"
    NEWS = "news"

class BlogPostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=200)
    excerpt: str = Field(..., min_length=10, max_length=300)
    content: str = Field(..., min_length=10)
    featured_image: Optional[str] = None
    category: BlogCategory
    tags: List[str] = Field(default_factory=list)
    status: BlogStatus = BlogStatus.DRAFT
    featured: bool = False
    read_time: int = Field(default=5, ge=1)  # in minutes
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None

class BlogPostCreate(BlogPostBase):
    pass

class BlogPostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=200)
    excerpt: Optional[str] = Field(None, min_length=10, max_length=300)
    content: Optional[str] = Field(None, min_length=10)
    featured_image: Optional[str] = None
    category: Optional[BlogCategory] = None
    tags: Optional[List[str]] = None
    status: Optional[BlogStatus] = None
    featured: Optional[bool] = None
    read_time: Optional[int] = Field(None, ge=1)
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None

class BlogPostInDB(BlogPostBase):
    id: str = Field(..., alias="_id")
    author: str = Field(default="Admin")
    views: int = Field(default=0)
    likes: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True

class BlogPostResponse(BlogPostInDB):
    class Config:
        from_attributes = True