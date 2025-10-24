from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class SkillCategory(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    DEVOPS = "devops"
    TOOLS = "tools"
    SOFT_SKILLS = "soft_skills"

class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class SkillBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    category: SkillCategory
    level: SkillLevel
    proficiency: int = Field(..., ge=0, le=100)
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    years_of_experience: float = Field(default=0, ge=0)
    featured: bool = False
    order: int = Field(default=0, ge=0)

class SkillCreate(SkillBase):
    pass

class SkillUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    category: Optional[SkillCategory] = None
    level: Optional[SkillLevel] = None
    proficiency: Optional[int] = Field(None, ge=0, le=100)
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    years_of_experience: Optional[float] = Field(None, ge=0)
    featured: Optional[bool] = None
    order: Optional[int] = Field(None, ge=0)

class SkillInDB(SkillBase):
    id: str = Field(..., alias="_id")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class SkillResponse(SkillInDB):
    class Config:
        from_attributes = True