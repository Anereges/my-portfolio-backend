from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.database.mongodb import get_collection
from app.models.skill import SkillCreate, SkillUpdate, SkillResponse, SkillCategory, SkillLevel
from app.schemas.response import StandardResponse

router = APIRouter()

@router.get("/skills", response_model=List[SkillResponse])
async def get_skills(
    category: Optional[SkillCategory] = None, 
    featured: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    collection = get_collection("skills")
    
    filter_query = {}
    if category:
        filter_query["category"] = category
    if featured is not None:
        filter_query["featured"] = featured
    
    skills = await collection.find(filter_query).sort("order", 1).limit(limit).to_list(limit)
    
    for skill in skills:
        skill["_id"] = str(skill["_id"])
    
    return skills

@router.get("/skills/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: str):
    collection = get_collection("skills")
    
    from bson import ObjectId
    if not ObjectId.is_valid(skill_id):
        raise HTTPException(status_code=400, detail="Invalid skill ID")
    
    skill = await collection.find_one({"_id": ObjectId(skill_id)})
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    skill["_id"] = str(skill["_id"])
    return skill

@router.post("/skills", response_model=StandardResponse)
async def create_skill(skill: SkillCreate):
    collection = get_collection("skills")
    
    # Set default order if not provided
    skill_dict = skill.dict()
    if skill_dict.get("order") is None:
        # Get the highest order and add 1
        highest_order_skill = await collection.find_one(sort=[("order", -1)])
        skill_dict["order"] = (highest_order_skill["order"] + 1) if highest_order_skill else 1
    
    result = await collection.insert_one(skill_dict)
    
    return StandardResponse(
        success=True,
        message="Skill created successfully",
        data={"skill_id": str(result.inserted_id)}
    )

@router.put("/skills/{skill_id}", response_model=StandardResponse)
async def update_skill(skill_id: str, skill_update: SkillUpdate):
    collection = get_collection("skills")
    
    from bson import ObjectId
    if not ObjectId.is_valid(skill_id):
        raise HTTPException(status_code=400, detail="Invalid skill ID")
    
    update_data = {k: v for k, v in skill_update.dict().items() if v is not None}
    
    result = await collection.update_one(
        {"_id": ObjectId(skill_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return StandardResponse(
        success=True,
        message="Skill updated successfully"
    )

@router.delete("/skills/{skill_id}", response_model=StandardResponse)
async def delete_skill(skill_id: str):
    collection = get_collection("skills")
    
    from bson import ObjectId
    if not ObjectId.is_valid(skill_id):
        raise HTTPException(status_code=400, detail="Invalid skill ID")
    
    result = await collection.delete_one({"_id": ObjectId(skill_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return StandardResponse(
        success=True,
        message="Skill deleted successfully"
    )

@router.get("/skills/test")
async def test_skills():
    """Test endpoint to verify skills API is working"""
    return {
        "success": True,
        "message": "Skills API is working",
        "data": [
            {
                "_id": "test_1",
                "name": "Vue.js",
                "category": "frontend",
                "level": "expert",
                "proficiency": 95,
                "years_of_experience": 3,
                "featured": True,
                "order": 1
            },
            {
                "_id": "test_2", 
                "name": "Python",
                "category": "backend",
                "level": "advanced",
                "proficiency": 85,
                "years_of_experience": 4,
                "featured": True,
                "order": 2
            }
        ]
    }

@router.get("/skills/categories", response_model=List[str])
async def get_skill_categories():
    return [category.value for category in SkillCategory]