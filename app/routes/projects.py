from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from app.database.mongodb import get_collection
from app.models.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectStatus
from app.schemas.response import StandardResponse, PaginatedResponse

router = APIRouter()

@router.get("/projects", response_model=PaginatedResponse)
async def get_projects(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    technology: Optional[str] = None,
    status: Optional[ProjectStatus] = None
):
    collection = get_collection("projects")
    
    # Build filter
    filter_query = {}
    if category:
        filter_query["category"] = category
    if featured is not None:
        filter_query["featured"] = featured
    if technology:
        filter_query["technologies"] = technology
    if status:
        filter_query["status"] = status
    
    # Get total count
    total = await collection.count_documents(filter_query)
    
    # Calculate pagination
    skip = (page - 1) * size
    pages = (total + size - 1) // size
    
    # Get projects
    projects = await collection.find(filter_query).sort("created_at", -1).skip(skip).limit(size).to_list(size)
    
    # Convert ObjectId to string
    for project in projects:
        project["_id"] = str(project["_id"])
    
    return PaginatedResponse(
        items=projects,
        total=total,
        page=page,
        size=size,
        pages=pages
    )

@router.get("/projects/featured", response_model=List[ProjectResponse])
async def get_featured_projects(limit: int = Query(6, ge=1, le=12)):
    collection = get_collection("projects")
    
    projects = await collection.find(
        {"featured": True}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    for project in projects:
        project["_id"] = str(project["_id"])
    
    return projects

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    collection = get_collection("projects")
    
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project ID")
    
    project = await collection.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(404, "Project not found")
    
    # Increment views
    await collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$inc": {"views": 1}}
    )
    
    project["_id"] = str(project["_id"])
    return project

@router.post("/projects", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def create_project(project: ProjectCreate):
    collection = get_collection("projects")
    
    project_dict = project.dict()
    result = await collection.insert_one(project_dict)
    
    return StandardResponse(
        success=True,
        message="Project created successfully",
        data={"project_id": str(result.inserted_id)}
    )

@router.put("/projects/{project_id}", response_model=StandardResponse)
async def update_project(project_id: str, project_update: ProjectUpdate):
    collection = get_collection("projects")
    
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project ID")
    
    update_data = {k: v for k, v in project_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(404, "Project not found")
    
    return StandardResponse(
        success=True,
        message="Project updated successfully"
    )

@router.delete("/projects/{project_id}", response_model=StandardResponse)
async def delete_project(project_id: str):
    collection = get_collection("projects")
    
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project ID")
    
    result = await collection.delete_one({"_id": ObjectId(project_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(404, "Project not found")
    
    return StandardResponse(
        success=True,
        message="Project deleted successfully"
    )