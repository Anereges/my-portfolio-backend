from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query, Form, UploadFile, File
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import List, Optional
from bson import ObjectId
import slugify
from datetime import datetime, timedelta
from app.core.config import settings
from app.schemas.response import StandardResponse
from app.models.blog import BlogCategory, BlogStatus
from app.utils.file_upload import save_upload_file
import secrets
import hashlib
import time
import jwt
import os
from pydantic import BaseModel

router = APIRouter()
security = HTTPBasic()

# 🔐 Enhanced Security Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "cyber-portfolio-super-secure-jwt-key-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 3600  # 1 hour in seconds

# 🛡️ Security Storage (In production, use Redis)
login_attempts = {}
active_sessions = {}
token_blacklist = set()

# 🧠 Enhanced Security Models
class LoginRequest(BaseModel):
    username: str
    password: str
    remember: bool = False

class LoginResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[dict] = None
    expires_in: Optional[int] = None
    security_level: str = "MAXIMUM"

class TokenData(BaseModel):
    username: str
    session_id: str
    ip_address: str
    user_agent: str

# 🔒 Advanced Security Functions
def generate_session_id():
    return secrets.token_urlsafe(32)

def hash_password(password: str) -> str:
    """Hash password with salt"""
    salt = secrets.token_hex(16)
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT token with enhanced security"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(16),  # Unique token ID
        "iss": "cyber-portfolio-admin",    # Issuer
        "aud": "cyber-portfolio-frontend"  # Audience
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """Verify JWT token with enhanced security checks"""
    try:
        # Check if token is blacklisted
        if token in token_blacklist:
            raise HTTPException(status_code=401, detail="Token revoked")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience="cyber-portfolio-frontend")
        
        # Additional security checks
        if payload.get("iss") != "cyber-portfolio-admin":
            raise HTTPException(status_code=401, detail="Invalid token issuer")
            
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

def check_rate_limit(client_ip: str):
    """Enhanced rate limiting with IP tracking"""
    if client_ip in login_attempts:
        attempts, first_attempt, last_attempt = login_attempts[client_ip]
        
        # Check if still in lockout period
        if attempts >= MAX_LOGIN_ATTEMPTS and time.time() - first_attempt < LOCKOUT_DURATION:
            remaining_time = LOCKOUT_DURATION - (time.time() - first_attempt)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts. Account locked for {int(remaining_time/60)} minutes."
            )
        elif time.time() - first_attempt >= LOCKOUT_DURATION:
            # Reset attempts after lockout period
            del login_attempts[client_ip]

def track_failed_attempt(client_ip: str):
    """Track failed login attempts"""
    current_time = time.time()
    if client_ip not in login_attempts:
        login_attempts[client_ip] = [1, current_time, current_time]
    else:
        attempts, first_attempt, _ = login_attempts[client_ip]
        login_attempts[client_ip] = [attempts + 1, first_attempt, current_time]

def clear_attempts(client_ip: str):
    """Clear login attempts on successful login"""
    if client_ip in login_attempts:
        del login_attempts[client_ip]

def get_client_info(request: Request):
    """Get comprehensive client information for security"""
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    forwarded_for = request.headers.get("x-forwarded-for")
    real_ip = request.headers.get("x-real-ip")
    
    return {
        "ip": client_ip,
        "user_agent": user_agent,
        "forwarded_for": forwarded_for,
        "real_ip": real_ip,
        "timestamp": datetime.utcnow().isoformat()
    }

# 🔐 Enhanced Authentication Dependencies
async def authenticate_admin_enhanced(
    credentials: HTTPBasicCredentials = Depends(security),
    request: Request = None
):
    """Enhanced admin authentication with security features"""
    client_info = get_client_info(request)
    client_ip = client_info["ip"]
    
    # Check rate limiting
    check_rate_limit(client_ip)
    
    # Secure credential comparison
    correct_username = secrets.compare_digest(credentials.username, settings.ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.ADMIN_PASSWORD)
    
    if not (correct_username and correct_password):
        track_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    clear_attempts(client_ip)
    return credentials.username

async def verify_admin_token(request: Request):
    """Enhanced token verification with session management"""
    token = None
    
    # Multiple token extraction methods
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif "admin_token" in request.cookies:
        token = request.cookies.get("admin_token")
    elif "x-auth-token" in request.headers:
        token = request.headers.get("x-auth-token")
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify token
    payload = verify_token(token)
    
    # Additional session validation
    session_id = payload.get("session_id")
    if session_id and session_id not in active_sessions:
        raise HTTPException(status_code=401, detail="Session expired")
    
    return payload

# 🚀 Enhanced Admin Routes
@router.post("/login", response_model=LoginResponse)
async def admin_login(
    login_data: LoginRequest,
    response: Response,
    request: Request
):
    """
    🔐 Enhanced admin login with JWT tokens, session management, and security features
    """
    client_info = get_client_info(request)
    client_ip = client_info["ip"]
    
    # Enhanced rate limiting
    check_rate_limit(client_ip)
    
    # Verify credentials with timing attack protection
    start_time = time.time()
    correct_username = secrets.compare_digest(login_data.username, settings.ADMIN_USERNAME)
    correct_password = secrets.compare_digest(login_data.password, settings.ADMIN_PASSWORD)
    
    # Add artificial delay to prevent timing attacks
    processing_time = time.time() - start_time
    if processing_time < 0.5:  # Minimum processing time
        time.sleep(0.5 - processing_time)
    
    if not (correct_username and correct_password):
        track_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Clear attempts on success
    clear_attempts(client_ip)
    
    # Generate session
    session_id = generate_session_id()
    active_sessions[session_id] = {
        "username": login_data.username,
        "ip_address": client_ip,
        "login_time": datetime.utcnow(),
        "user_agent": client_info["user_agent"]
    }
    
    # Create JWT token
    access_token_expires = timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES if not login_data.remember else 60 * 24 * 7  # 7 days if remember me
    )
    
    token_data = {
        "sub": login_data.username,
        "type": "access",
        "session_id": session_id,
        "ip": client_ip,
        "security_level": "maximum"
    }
    
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
    
    # Set secure HTTP-only cookies
    response.set_cookie(
        key="admin_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production (HTTPS)
        samesite="lax",
        max_age=int(access_token_expires.total_seconds())
    )
    
    response.set_cookie(
        key="admin_session",
        value=session_id,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=int(access_token_expires.total_seconds())
    )
    
    # Log successful login
    print(f"🔐 ADMIN LOGIN: {login_data.username} from {client_ip} at {datetime.utcnow().isoformat()}")
    
    return LoginResponse(
        success=True,
        message="Authentication successful. Access granted.",
        token=access_token,
        user={
            "username": login_data.username,
            "role": "Administrator",
            "login_time": datetime.utcnow().isoformat(),
            "security_level": "MAXIMUM",
            "session_id": session_id
        },
        expires_in=int(access_token_expires.total_seconds()),
        security_level="MAXIMUM"
    )

@router.post("/logout", response_model=StandardResponse)
async def admin_logout(
    response: Response, 
    request: Request
):
    """
    🔐 Enhanced admin logout with graceful token handling
    """
    token = None
    username = "Unknown"
    session_id = None
    
    # Extract token from multiple sources
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif "admin_token" in request.cookies:
        token = request.cookies.get("admin_token")
    
    # Try to verify token and get user info
    if token:
        try:
            token_data = verify_token(token)
            username = token_data.get("sub", "Unknown")
            session_id = token_data.get("session_id")
            
            # Add token to blacklist
            token_blacklist.add(token)
            
            # Remove session
            if session_id in active_sessions:
                del active_sessions[session_id]
                
        except HTTPException:
            # Token is invalid/expired, but we still proceed with logout
            pass
    
    # Clear cookies regardless of token validity
    response.delete_cookie(key="admin_token")
    response.delete_cookie(key="admin_session")
    
    # Log logout
    print(f"🔐 ADMIN LOGOUT: {username} at {datetime.utcnow().isoformat()}")
    
    return StandardResponse(
        success=True,
        message="Successfully logged out. All sessions terminated.",
        data={
            "username": username, 
            "logout_time": datetime.utcnow().isoformat(),
            "session_cleared": session_id is not None
        }
    )

@router.get("/security-status", response_model=StandardResponse)
async def security_status(token_data: dict = Depends(verify_admin_token)):
    """
    🔒 Get current security status and active sessions
    """
    username = token_data.get("sub")
    
    user_sessions = {
        session_id: data for session_id, data in active_sessions.items()
        if data["username"] == username
    }
    
    return StandardResponse(
        success=True,
        message="Security status retrieved",
        data={
            "username": username,
            "security_level": "MAXIMUM",
            "active_sessions": len(user_sessions),
            "failed_attempts": len(login_attempts),
            "session_details": user_sessions,
            "token_issued": token_data.get("iat"),
            "token_expires": token_data.get("exp")
        }
    )

@router.post("/terminate-session/{session_id}", response_model=StandardResponse)
async def terminate_session(
    session_id: str,
    token_data: dict = Depends(verify_admin_token)
):
    """
    🔒 Terminate specific admin session
    """
    username = token_data.get("sub")
    
    if session_id in active_sessions:
        if active_sessions[session_id]["username"] == username:
            del active_sessions[session_id]
            
    return StandardResponse(
        success=True,
        message="Session terminated successfully",
        data={"terminated_session": session_id}
    )

# 🛡️ Enhanced Protected Routes (using token authentication)
@router.get("/dashboard", response_model=StandardResponse)
async def admin_dashboard(token_data: dict = Depends(verify_admin_token)):
    """
    📊 Admin dashboard with enhanced security
    """
    from app.database.mongodb import get_collection
    
    username = token_data.get("sub")
    
    projects_collection = get_collection("projects")
    skills_collection = get_collection("skills")
    contacts_collection = get_collection("contacts")
    blog_collection = get_collection("blog_posts")
    
    total_projects = await projects_collection.count_documents({})
    total_skills = await skills_collection.count_documents({})
    new_contacts = await contacts_collection.count_documents({"status": "new"})
    total_blog_posts = await blog_collection.count_documents({})
    published_blog_posts = await blog_collection.count_documents({"status": BlogStatus.PUBLISHED})
    
    # Enhanced dashboard data with security context
    recent_projects = await projects_collection.find().sort("created_at", -1).limit(5).to_list(5)
    recent_contacts = await contacts_collection.find().sort("created_at", -1).limit(5).to_list(5)
    recent_blog_posts = await blog_collection.find().sort("created_at", -1).limit(5).to_list(5)
    
    return StandardResponse(
        success=True,
        message="Admin dashboard data retrieved securely",
        data={
            "stats": [
                {
                    "title": "TOTAL_PROJECTS",
                    "value": str(total_projects),
                    "change": "+0",
                    "trend": "up",
                    "icon": "Folder",
                    "color": "text-cyber-primary",
                    "bgColor": "bg-cyber-primary/10",
                    "borderColor": "border-cyber-primary/30",
                    "route": "/admin/projects"
                },
                {
                    "title": "TECH_SKILLS",
                    "value": str(total_skills),
                    "change": "+0",
                    "trend": "up",
                    "icon": "Code2",
                    "color": "text-cyber-accent",
                    "bgColor": "bg-cyber-accent/10",
                    "borderColor": "border-cyber-accent/30",
                    "route": "/admin/skills"
                },
                {
                    "title": "NEW_MESSAGES",
                    "value": str(new_contacts),
                    "change": "+0",
                    "trend": "up",
                    "icon": "Mail",
                    "color": "text-cyber-secondary",
                    "bgColor": "bg-cyber-secondary/10",
                    "borderColor": "border-cyber-secondary/30",
                    "route": "/admin/contacts"
                },
                {
                    "title": "BLOG_POSTS",
                    "value": f"{published_blog_posts}/{total_blog_posts}",
                    "change": "+0",
                    "trend": "up",
                    "icon": "FileText",
                    "color": "text-purple-400",
                    "bgColor": "bg-purple-400/10",
                    "borderColor": "border-purple-400/30",
                    "route": "/admin/blog"
                }
            ],
            "security_context": {
                "username": username,
                "login_time": token_data.get("iat"),
                "session_id": token_data.get("session_id"),
                "security_level": token_data.get("security_level", "MAXIMUM"),
                "ip_address": token_data.get("ip")
            },
            "recentActivities": [
                {
                    "id": 1,
                    "message": f"TOTAL_PROJECTS_IN_PORTFOLIO: {total_projects}",
                    "time": "RECENTLY",
                    "type": "PROJECT",
                    "icon": "Folder",
                    "bgColor": "bg-cyber-primary/10",
                    "borderColor": "border-cyber-primary/30"
                },
                {
                    "id": 2,
                    "message": f"NEW_CONTACT_MESSAGES: {new_contacts}",
                    "time": "RECENTLY",
                    "type": "MESSAGE",
                    "icon": "MessageSquare",
                    "bgColor": "bg-cyber-accent/10",
                    "borderColor": "border-cyber-accent/30"
                },
                {
                    "id": 3,
                    "message": f"TECH_SKILLS_AVAILABLE: {total_skills}",
                    "time": "RECENTLY",
                    "type": "SKILL",
                    "icon": "Code2",
                    "bgColor": "bg-cyber-secondary/10",
                    "borderColor": "border-cyber-secondary/30"
                },
                {
                    "id": 4,
                    "message": f"BLOG_POSTS_PUBLISHED: {published_blog_posts}",
                    "time": "RECENTLY",
                    "type": "BLOG",
                    "icon": "FileText",
                    "bgColor": "bg-purple-400/10",
                    "borderColor": "border-purple-400/30"
                }
            ]
        }
    )

# 🛡️ Update all existing routes to use token authentication
@router.get("/projects", response_model=StandardResponse)
async def get_projects(
    token_data: dict = Depends(verify_admin_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """Get all projects with pagination (Token protected)"""
    from app.database.mongodb import get_collection
    
    projects_collection = get_collection("projects")
    
    total = await projects_collection.count_documents({})
    projects = await projects_collection.find().skip(skip).limit(limit).to_list(limit)
    
    for project in projects:
        project["_id"] = str(project["_id"])
    
    return StandardResponse(
        success=True,
        message="Projects retrieved successfully",
        data={
            "projects": projects,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": (skip + limit) < total
            },
            "accessed_by": token_data.get("sub")
        }
    )

@router.get("/projects/{project_id}", response_model=StandardResponse)
async def get_project(project_id: str, token_data: dict = Depends(verify_admin_token)):
    """Get specific project (Token protected)"""
    from app.database.mongodb import get_collection
    
    projects_collection = get_collection("projects")
    
    try:
        project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project["_id"] = str(project["_id"])
        return StandardResponse(
            success=True,
            message="Project retrieved successfully",
            data={"project": project}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid project ID")

@router.post("/projects", response_model=StandardResponse)
async def create_project(project_data: dict, token_data: dict = Depends(verify_admin_token)):
    """Create new project (Token protected)"""
    from app.database.mongodb import get_collection
    
    projects_collection = get_collection("projects")
    
    project_data["created_at"] = datetime.utcnow()
    project_data["updated_at"] = datetime.utcnow()
    project_data["created_by"] = token_data.get("sub")
    
    result = await projects_collection.insert_one(project_data)
    
    return StandardResponse(
        success=True,
        message="Project created successfully",
        data={"project_id": str(result.inserted_id)}
    )

@router.put("/projects/{project_id}", response_model=StandardResponse)
async def update_project(project_id: str, project_data: dict, token_data: dict = Depends(verify_admin_token)):
    """Update project (Token protected)"""
    from app.database.mongodb import get_collection
    
    projects_collection = get_collection("projects")
    
    project_data["updated_at"] = datetime.utcnow()
    project_data["updated_by"] = token_data.get("sub")
    
    try:
        result = await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": project_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return StandardResponse(
            success=True,
            message="Project updated successfully",
            data={"modified_count": result.modified_count}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid project ID")

@router.delete("/projects/{project_id}", response_model=StandardResponse)
async def delete_project(project_id: str, token_data: dict = Depends(verify_admin_token)):
    """Delete project (Token protected)"""
    from app.database.mongodb import get_collection
    
    projects_collection = get_collection("projects")
    
    try:
        result = await projects_collection.delete_one({"_id": ObjectId(project_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return StandardResponse(
            success=True,
            message="Project deleted successfully",
            data={"deleted_count": result.deleted_count}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid project ID")

# 🛡️ Continue with skills, contacts, blog routes using token authentication...
@router.get("/skills", response_model=StandardResponse)
async def get_skills(
    token_data: dict = Depends(verify_admin_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """Get all skills (Token protected)"""
    from app.database.mongodb import get_collection
    
    skills_collection = get_collection("skills")
    
    total = await skills_collection.count_documents({})
    skills = await skills_collection.find().skip(skip).limit(limit).to_list(limit)
    
    for skill in skills:
        skill["_id"] = str(skill["_id"])
    
    return StandardResponse(
        success=True,
        message="Skills retrieved successfully",
        data={
            "skills": skills,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": (skip + limit) < total
            }
        }
    )

@router.post("/skills", response_model=StandardResponse)
async def create_skill(skill_data: dict, token_data: dict = Depends(verify_admin_token)):
    """Create new skill (Token protected)"""
    from app.database.mongodb import get_collection
    
    skills_collection = get_collection("skills")
    
    skill_data["created_at"] = datetime.utcnow()
    skill_data["updated_at"] = datetime.utcnow()
    skill_data["created_by"] = token_data.get("sub")
    
    result = await skills_collection.insert_one(skill_data)
    
    return StandardResponse(
        success=True,
        message="Skill created successfully",
        data={"skill_id": str(result.inserted_id)}
    )

@router.put("/skills/{skill_id}", response_model=StandardResponse)
async def update_skill(skill_id: str, skill_data: dict, token_data: dict = Depends(verify_admin_token)):
    """Update skill (Token protected)"""
    from app.database.mongodb import get_collection
    
    skills_collection = get_collection("skills")
    
    skill_data["updated_at"] = datetime.utcnow()
    skill_data["updated_by"] = token_data.get("sub")
    
    try:
        result = await skills_collection.update_one(
            {"_id": ObjectId(skill_id)},
            {"$set": skill_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        return StandardResponse(
            success=True,
            message="Skill updated successfully",
            data={"modified_count": result.modified_count}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid skill ID")

@router.delete("/skills/{skill_id}", response_model=StandardResponse)
async def delete_skill(skill_id: str, token_data: dict = Depends(verify_admin_token)):
    """Delete skill (Token protected)"""
    from app.database.mongodb import get_collection
    
    skills_collection = get_collection("skills")
    
    try:
        result = await skills_collection.delete_one({"_id": ObjectId(skill_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        return StandardResponse(
            success=True,
            message="Skill deleted successfully",
            data={"deleted_count": result.deleted_count}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid skill ID")

@router.get("/contacts", response_model=StandardResponse)
async def get_contacts(
    token_data: dict = Depends(verify_admin_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None)
):
    """Get all contacts (Token protected)"""
    from app.database.mongodb import get_collection
    
    contacts_collection = get_collection("contacts")
    
    # Build filter query
    filter_query = {}
    if status_filter:
        filter_query["status"] = status_filter
    
    total = await contacts_collection.count_documents(filter_query)
    contacts = await contacts_collection.find(filter_query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    for contact in contacts:
        contact["_id"] = str(contact["_id"])
    
    return StandardResponse(
        success=True,
        message="Contacts retrieved successfully",
        data={
            "contacts": contacts,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": (skip + limit) < total
            }
        }
    )

@router.get("/contacts/{contact_id}", response_model=StandardResponse)
async def get_contact(contact_id: str, token_data: dict = Depends(verify_admin_token)):
    """Get specific contact (Token protected)"""
    from app.database.mongodb import get_collection
    
    contacts_collection = get_collection("contacts")
    
    try:
        contact = await contacts_collection.find_one({"_id": ObjectId(contact_id)})
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        contact["_id"] = str(contact["_id"])
        return StandardResponse(
            success=True,
            message="Contact retrieved successfully",
            data={"contact": contact}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid contact ID")

@router.put("/contacts/{contact_id}/status", response_model=StandardResponse)
async def update_contact_status(contact_id: str, status_data: dict, token_data: dict = Depends(verify_admin_token)):
    """Update contact status (Token protected)"""
    from app.database.mongodb import get_collection
    
    contacts_collection = get_collection("contacts")
    
    try:
        result = await contacts_collection.update_one(
            {"_id": ObjectId(contact_id)},
            {"$set": {"status": status_data.get("status"), "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        return StandardResponse(
            success=True,
            message="Contact status updated successfully",
            data={"modified_count": result.modified_count}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid contact ID")

@router.delete("/contacts/{contact_id}", response_model=StandardResponse)
async def delete_contact(contact_id: str, token_data: dict = Depends(verify_admin_token)):
    """Delete contact (Token protected)"""
    from app.database.mongodb import get_collection
    
    contacts_collection = get_collection("contacts")
    
    try:
        result = await contacts_collection.delete_one({"_id": ObjectId(contact_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        return StandardResponse(
            success=True,
            message="Contact deleted successfully",
            data={"deleted_count": result.deleted_count}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid contact ID")

@router.get("/blog", response_model=StandardResponse)
async def get_blog_posts(
    token_data: dict = Depends(verify_admin_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[BlogStatus] = Query(None)
):
    """Get all blog posts (Token protected)"""
    from app.database.mongodb import get_collection
    
    blog_collection = get_collection("blog_posts")
    
    # Build filter query
    filter_query = {}
    if status is not None:
        filter_query["status"] = status
    
    total = await blog_collection.count_documents(filter_query)
    posts = await blog_collection.find(filter_query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    for post in posts:
        post["_id"] = str(post["_id"])
    
    return StandardResponse(
        success=True,
        message="Blog posts retrieved successfully",
        data={
            "posts": posts,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": (skip + limit) < total
            }
        }
    )

@router.post("/blog", response_model=StandardResponse)
async def create_blog_post(
    title: str = Form(...),
    excerpt: str = Form(...),
    content: str = Form(...),
    category: BlogCategory = Form(...),
    tags: str = Form(""),
    featured: bool = Form(False),
    read_time: int = Form(5),
    status: BlogStatus = Form(BlogStatus.DRAFT),
    featured_image: Optional[UploadFile] = File(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    token_data: dict = Depends(verify_admin_token)
):
    """Create new blog post (Token protected)"""
    from app.database.mongodb import get_collection
    
    blog_collection = get_collection("blog_posts")
    
    # Generate slug from title
    slug = slugify.slugify(title)
    
    # Check if slug already exists
    existing_post = await blog_collection.find_one({"slug": slug})
    if existing_post:
        raise HTTPException(status_code=400, detail="A post with this title already exists")
    
    # Handle featured image upload
    image_url = None
    if featured_image:
        image_url = await save_upload_file(featured_image, "blog_images")
    
    # Process tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    post_data = {
        "title": title,
        "slug": slug,
        "excerpt": excerpt,
        "content": content,
        "category": category,
        "tags": tag_list,
        "featured": featured,
        "read_time": read_time,
        "featured_image": image_url,
        "meta_title": meta_title or title,
        "meta_description": meta_description or excerpt,
        "status": status,
        "author": token_data.get("sub"),
        "views": 0,
        "likes": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    # Set published_at if status is PUBLISHED
    if status == BlogStatus.PUBLISHED:
        post_data["published_at"] = datetime.utcnow()
    
    result = await blog_collection.insert_one(post_data)
    
    return StandardResponse(
        success=True,
        message="Blog post created successfully",
        data={"post_id": str(result.inserted_id), "slug": slug}
    )

@router.put("/blog/{post_id}", response_model=StandardResponse)
async def update_blog_post(
    post_id: str,
    title: Optional[str] = Form(None),
    excerpt: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    category: Optional[BlogCategory] = Form(None),
    tags: Optional[str] = Form(None),
    featured: Optional[bool] = Form(None),
    read_time: Optional[int] = Form(None),
    status: Optional[BlogStatus] = Form(None),
    featured_image: Optional[UploadFile] = File(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    token_data: dict = Depends(verify_admin_token)
):
    """Update blog post (Token protected)"""
    from app.database.mongodb import get_collection
    
    blog_collection = get_collection("blog_posts")
    
    if not ObjectId.is_valid(post_id):
        raise HTTPException(status_code=400, detail="Invalid post ID")
    
    # Build update data
    update_data = {"updated_at": datetime.utcnow()}
    
    if title is not None:
        update_data["title"] = title
        # Regenerate slug if title changes
        update_data["slug"] = slugify.slugify(title)
    if excerpt is not None:
        update_data["excerpt"] = excerpt
    if content is not None:
        update_data["content"] = content
    if category is not None:
        update_data["category"] = category
    if tags is not None:
        update_data["tags"] = [tag.strip() for tag in tags.split(",") if tag.strip()]
    if featured is not None:
        update_data["featured"] = featured
    if read_time is not None:
        update_data["read_time"] = read_time
    if status is not None:
        update_data["status"] = status
        if status == BlogStatus.PUBLISHED:
            # Set published_at when publishing
            update_data["published_at"] = datetime.utcnow()
    if meta_title is not None:
        update_data["meta_title"] = meta_title
    if meta_description is not None:
        update_data["meta_description"] = meta_description
    
    # Handle featured image upload
    if featured_image:
        image_url = await save_upload_file(featured_image, "blog_images")
        update_data["featured_image"] = image_url
    
    try:
        result = await blog_collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Blog post not found")
        
        return StandardResponse(
            success=True,
            message="Blog post updated successfully",
            data={"modified_count": result.modified_count}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid blog post ID")

@router.delete("/blog/{post_id}", response_model=StandardResponse)
async def delete_blog_post(post_id: str, token_data: dict = Depends(verify_admin_token)):
    """Delete blog post (Token protected)"""
    from app.database.mongodb import get_collection
    
    blog_collection = get_collection("blog_posts")
    
    try:
        result = await blog_collection.delete_one({"_id": ObjectId(post_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Blog post not found")
        
        return StandardResponse(
            success=True,
            message="Blog post deleted successfully",
            data={"deleted_count": result.deleted_count}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid blog post ID")

@router.get("/profile", response_model=StandardResponse)
async def admin_profile(token_data: dict = Depends(verify_admin_token)):
    """
    👤 Get admin profile with security context
    """
    return StandardResponse(
        success=True,
        message="Admin profile data",
        data={
            "username": token_data.get("sub"),
            "role": "Administrator",
            "security_level": token_data.get("security_level", "MAXIMUM"),
            "login_time": token_data.get("iat"),
            "session_id": token_data.get("session_id"),
            "ip_address": token_data.get("ip"),
            "permissions": ["read", "write", "delete", "admin"]
        }
    )

@router.get("/security-logs", response_model=StandardResponse)
async def security_logs(token_data: dict = Depends(verify_admin_token)):
    """
    📊 Get security logs and activity
    """
    return StandardResponse(
        success=True,
        message="Security logs retrieved",
        data={
            "failed_attempts": login_attempts,
            "active_sessions": active_sessions,
            "total_sessions": len(active_sessions),
            "blacklisted_tokens": len(token_blacklist),
            "current_user": token_data.get("sub")
        }
    )
# 🔔 NOTIFICATION ENDPOINTS
class NotificationCreate(BaseModel):
    message: str
    type: str = "info"  # success, warning, error, info, security, system
    action_url: Optional[str] = None
    priority: str = "medium"  # low, medium, high, critical

class NotificationResponse(BaseModel):
    id: str
    message: str
    type: str
    read: bool
    created_at: datetime
    action_url: Optional[str] = None
    priority: str

@router.get("/notifications", response_model=StandardResponse)
async def get_notifications(
    token_data: dict = Depends(verify_admin_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    unread_only: bool = Query(False)
):
    """
    🔔 Get admin notifications
    """
    from app.database.mongodb import get_collection
    
    notifications_collection = get_collection("notifications")
    
    # Build filter query
    filter_query = {}
    if unread_only:
        filter_query["read"] = False
    
    # Get notifications, most recent first
    total = await notifications_collection.count_documents(filter_query)
    notifications = await notifications_collection.find(filter_query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Convert ObjectId to string and format response
    formatted_notifications = []
    for notification in notifications:
        formatted_notifications.append({
            "id": str(notification["_id"]),
            "message": notification["message"],
            "type": notification.get("type", "info"),
            "read": notification.get("read", False),
            "created_at": notification["created_at"],
            "action_url": notification.get("action_url"),
            "priority": notification.get("priority", "medium")
        })
    
    return StandardResponse(
        success=True,
        message="Notifications retrieved successfully",
        data={
            "notifications": formatted_notifications,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": (skip + limit) < total
            },
            "unread_count": await notifications_collection.count_documents({"read": False})
        }
    )

@router.post("/notifications", response_model=StandardResponse)
async def create_notification(
    notification_data: NotificationCreate,
    token_data: dict = Depends(verify_admin_token)
):
    """
    🔔 Create a new notification
    """
    from app.database.mongodb import get_collection
    
    notifications_collection = get_collection("notifications")
    
    notification_doc = {
        "message": notification_data.message,
        "type": notification_data.type,
        "read": False,
        "action_url": notification_data.action_url,
        "priority": notification_data.priority,
        "created_by": token_data.get("sub"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await notifications_collection.insert_one(notification_doc)
    
    return StandardResponse(
        success=True,
        message="Notification created successfully",
        data={"notification_id": str(result.inserted_id)}
    )

@router.post("/notifications/{notification_id}/read", response_model=StandardResponse)
async def mark_notification_as_read(
    notification_id: str,
    token_data: dict = Depends(verify_admin_token)
):
    """
    🔔 Mark a notification as read
    """
    from app.database.mongodb import get_collection
    
    notifications_collection = get_collection("notifications")
    
    try:
        result = await notifications_collection.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"read": True, "updated_at": datetime.utcnow(), "read_by": token_data.get("sub")}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return StandardResponse(
            success=True,
            message="Notification marked as read",
            data={"modified_count": result.modified_count}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid notification ID")

@router.post("/notifications/read-all", response_model=StandardResponse)
async def mark_all_notifications_read(
    token_data: dict = Depends(verify_admin_token)
):
    """
    🔔 Mark all notifications as read
    """
    from app.database.mongodb import get_collection
    
    notifications_collection = get_collection("notifications")
    
    result = await notifications_collection.update_many(
        {"read": False},
        {"$set": {"read": True, "updated_at": datetime.utcnow(), "read_by": token_data.get("sub")}}
    )
    
    return StandardResponse(
        success=True,
        message=f"All notifications marked as read",
        data={"modified_count": result.modified_count}
    )

@router.delete("/notifications/{notification_id}", response_model=StandardResponse)
async def delete_notification(
    notification_id: str,
    token_data: dict = Depends(verify_admin_token)
):
    """
    🔔 Delete a notification
    """
    from app.database.mongodb import get_collection
    
    notifications_collection = get_collection("notifications")
    
    try:
        result = await notifications_collection.delete_one({"_id": ObjectId(notification_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return StandardResponse(
            success=True,
            message="Notification deleted successfully",
            data={"deleted_count": result.deleted_count}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid notification ID")

@router.get("/notifications/stats", response_model=StandardResponse)
async def get_notification_stats(
    token_data: dict = Depends(verify_admin_token)
):
    """
    🔔 Get notification statistics
    """
    from app.database.mongodb import get_collection
    
    notifications_collection = get_collection("notifications")
    
    total = await notifications_collection.count_documents({})
    unread = await notifications_collection.count_documents({"read": False})
    
    # Count by type
    type_counts = {}
    for ntype in ["success", "warning", "error", "info", "security", "system"]:
        type_counts[ntype] = await notifications_collection.count_documents({"type": ntype})
    
    # Count by priority
    priority_counts = {}
    for priority in ["low", "medium", "high", "critical"]:
        priority_counts[priority] = await notifications_collection.count_documents({"priority": priority})
    
    return StandardResponse(
        success=True,
        message="Notification statistics retrieved",
        data={
            "total": total,
            "unread": unread,
            "read": total - unread,
            "by_type": type_counts,
            "by_priority": priority_counts
        }
    )

# 🔔 AUTO-GENERATE NOTIFICATIONS FOR IMPORTANT EVENTS
async def create_system_notification(message: str, notification_type: str = "info", priority: str = "medium"):
    """
    Utility function to create system notifications automatically
    """
    from app.database.mongodb import get_collection
    
    notifications_collection = get_collection("notifications")
    
    notification_doc = {
        "message": message,
        "type": notification_type,
        "read": False,
        "priority": priority,
        "created_by": "system",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    await notifications_collection.insert_one(notification_doc)
 # 🚨 Emergency endpoints
@router.post("/emergency-lockdown", response_model=StandardResponse)
async def emergency_lockdown(token_data: dict = Depends(verify_admin_token)):
    """
    🚨 Emergency lockdown - terminate all sessions
    """
    username = token_data.get("sub")
    
    # Terminate all sessions except current one
    current_session = token_data.get("session_id")
    sessions_to_remove = []
    
    for session_id, session_data in active_sessions.items():
        if session_id != current_session and session_data["username"] == username:
            sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        del active_sessions[session_id]
    
    return StandardResponse(
        success=True,
        message=f"Emergency lockdown activated. {len(sessions_to_remove)} sessions terminated.",
        data={"terminated_sessions": sessions_to_remove, "remaining_sessions": 1}
    )

@router.post("/reset-security", response_model=StandardResponse)
async def reset_security(token_data: dict = Depends(verify_admin_token)):
    """
    🔄 Reset security counters and clear failed attempts
    """
    global login_attempts, token_blacklist
    
    login_attempts.clear()
    token_blacklist.clear()
    
    return StandardResponse(
        success=True,
        message="Security system reset successfully",
        data={
            "cleared_attempts": True,
            "cleared_blacklist": True,
            "reset_by": token_data.get("sub")
        }
    )