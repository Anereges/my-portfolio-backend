from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum

class ContactStatus(str, Enum):
    NEW = "new"
    READ = "read"
    REPLIED = "replied"
    ARCHIVED = "archived"

class ContactBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=10, max_length=2000)
    company: Optional[str] = None
    phone: Optional[str] = None

class ContactCreate(ContactBase):
    pass

class ContactInDB(ContactBase):
    id: str = Field(..., alias="_id")
    status: ContactStatus = ContactStatus.NEW
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class ContactResponse(ContactInDB):
    class Config:
        from_attributes = True
