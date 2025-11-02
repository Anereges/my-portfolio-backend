from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
import os
from datetime import datetime, timedelta

from app.database.mongodb import connect_to_mongo, close_mongo_connection
from app.routes import projects, skills, contacts, admin, blog
from app.utils.logger import setup_logger

# 🧠 Setup logger
logger = setup_logger()

# 📁 Define base directory (root of your backend) - CORRECTED
BASE_DIR = Path(__file__).resolve().parent  # This points to backend/ folder

# 🔔 INITIALIZE SAMPLE NOTIFICATIONS
async def initialize_sample_notifications():
    """
    Create sample notifications if the collection is empty
    """
    from app.database.mongodb import get_collection
    
    try:
        notifications_collection = get_collection("notifications")
        
        # Check if we already have notifications
        existing_count = await notifications_collection.count_documents({})
        if existing_count > 0:
            logger.info("🔔 Notifications already exist in database")
            return
        
        sample_notifications = [
            {
                "message": "🚀 Welcome to your admin dashboard! System is running smoothly.",
                "type": "success",
                "read": False,
                "priority": "medium",
                "created_by": "system",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "message": "📊 Dashboard analytics are now available. Check your portfolio stats.",
                "type": "info",
                "read": False,
                "priority": "low",
                "created_by": "system",
                "created_at": datetime.utcnow() - timedelta(hours=2),
                "updated_at": datetime.utcnow() - timedelta(hours=2)
            },
            {
                "message": "🔒 Security system activated. All admin routes are protected.",
                "type": "security",
                "read": True,
                "priority": "high",
                "created_by": "system",
                "created_at": datetime.utcnow() - timedelta(hours=4),
                "updated_at": datetime.utcnow() - timedelta(hours=4)
            },
            {
                "message": "💼 New contact message received from portfolio visitor.",
                "type": "info",
                "read": False,
                "priority": "medium",
                "created_by": "system",
                "created_at": datetime.utcnow() - timedelta(hours=1),
                "updated_at": datetime.utcnow() - timedelta(hours=1)
            },
            {
                "message": "⚠️ System maintenance scheduled for tomorrow at 2:00 AM.",
                "type": "warning",
                "read": False,
                "priority": "medium",
                "created_by": "system",
                "created_at": datetime.utcnow() - timedelta(minutes=30),
                "updated_at": datetime.utcnow() - timedelta(minutes=30)
            }
        ]
        
        # Insert sample notifications
        await notifications_collection.insert_many(sample_notifications)
        logger.info("✅ Sample notifications initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize notifications: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    
    # Initialize sample notifications
    await initialize_sample_notifications()
    
    logger.info("🚀 Application started successfully")
    yield
    # Shutdown
    await close_mongo_connection()
    logger.info("🛑 Application shutdown")

# ⚙️ Initialize FastAPI app
app = FastAPI(
    title="Portfolio API",
    description="Professional Portfolio Backend API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# 🌍 CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev
        "http://127.0.0.1:5173",  # Vue + Vite dev
        "https://my-portfolio-frontend.onrender.com",  # Prod frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🖼️ Static files setup (for blog images) - CORRECTED PATH
blog_image_dir = BASE_DIR / "blog_images"
blog_image_dir.mkdir(parents=True, exist_ok=True)

# Mount for serving blog images
app.mount("/uploads", StaticFiles(directory=str(blog_image_dir)), name="uploads")

# Test endpoint
@app.get("/test-image")
async def test_image():
    file_path = blog_image_dir / "c66a24078117eeb6.jpg"
    if file_path.exists():
        return FileResponse(file_path, media_type="image/jpeg")
    else:
        return {"error": f"File not found at {file_path}"}

# 🧩 Include Routers
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(skills.router, prefix="/api/v1", tags=["skills"])
app.include_router(contacts.router, prefix="/api/v1", tags=["contacts"])
app.include_router(blog.router, prefix="/api/v1", tags=["blog"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

# 💓 Health Check Endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Portfolio API is running smoothly",
        "version": "1.0.0"
    }

# 🚨 Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

# 🏁 Run App - UPDATED FOR RENDER
if __name__ == "__main__":
    import uvicorn
    import os
    # Get port from Render environment variable or default to 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Set to False for production
        log_level="info"
    )