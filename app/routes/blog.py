from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from typing import List, Optional
from bson import ObjectId
from slugify import slugify
from datetime import datetime

from app.models.blog import BlogPostCreate, BlogPostUpdate, BlogPostResponse, BlogStatus, BlogCategory
from app.database.mongodb import get_collection
from app.utils.file_upload import save_upload_file
from app.schemas.response import StandardResponse, PaginatedResponse
from app.services.cloudinary_service import cloudinary_service  # ADD THIS IMPORT

router = APIRouter()

@router.get("/blog/posts", response_model=PaginatedResponse)
async def get_blog_posts(
    page: int = Query(1, ge=1),
    size: int = Query(9, ge=1, le=50),
    category: Optional[BlogCategory] = None,
    status: Optional[BlogStatus] = None,
    featured: Optional[bool] = None,
    search: Optional[str] = None
):
    collection = get_collection("blog_posts")
    
    # Build filter - default to published for public access
    filter_query = {"status": BlogStatus.PUBLISHED}
    if category:
        filter_query["category"] = category
    if status:
        filter_query["status"] = status
    if featured is not None:
        filter_query["featured"] = featured
    if search:
        filter_query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"excerpt": {"$regex": search, "$options": "i"}},
            {"content": {"$regex": search, "$options": "i"}},
            {"tags": {"$in": [search]}}
        ]
    
    # Get total count
    total = await collection.count_documents(filter_query)
    
    # Calculate pagination
    skip = (page - 1) * size
    pages = (total + size - 1) // size
    
    # Get posts
    posts = await collection.find(filter_query).sort("created_at", -1).skip(skip).limit(size).to_list(size)
    
    # Convert ObjectId to string
    for post in posts:
        post["_id"] = str(post["_id"])
    
    return PaginatedResponse(
        items=posts,
        total=total,
        page=page,
        size=size,
        pages=pages
    )

@router.get("/blog/posts/featured", response_model=List[BlogPostResponse])
async def get_featured_posts(limit: int = Query(3, ge=1, le=10)):
    collection = get_collection("blog_posts")
    
    posts = await collection.find({
        "status": BlogStatus.PUBLISHED,
        "featured": True
    }).sort("created_at", -1).limit(limit).to_list(limit)
    
    for post in posts:
        post["_id"] = str(post["_id"])
    
    return posts

@router.get("/blog/posts/{identifier}", response_model=BlogPostResponse)
async def get_blog_post(identifier: str):
    collection = get_collection("blog_posts")
    
    # Try to find by ID first
    if ObjectId.is_valid(identifier):
        post = await collection.find_one({"_id": ObjectId(identifier)})
    else:
        # Then try by slug
        post = await collection.find_one({"slug": identifier})
    
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    
    # Only show published posts to public
    if post.get("status") != BlogStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Blog post not found")
    
    # Increment views
    await collection.update_one(
        {"_id": post["_id"]},
        {"$inc": {"views": 1}}
    )
    
    post["_id"] = str(post["_id"])
    return post

@router.get("/blog/posts/id/{post_id}", response_model=BlogPostResponse)
async def get_blog_post_by_id(post_id: str):
    collection = get_collection("blog_posts")
    
    if not ObjectId.is_valid(post_id):
        raise HTTPException(400, "Invalid post ID")
    
    post = await collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    
    # Only show published posts to public
    if post.get("status") != BlogStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Blog post not found")
    
    # Increment views
    await collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$inc": {"views": 1}}
    )
    
    post["_id"] = str(post["_id"])
    return post

@router.post("/blog/posts", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def create_blog_post(
    title: str = Form(...),
    excerpt: str = Form(...),
    content: str = Form(...),
    category: BlogCategory = Form(...),
    tags: str = Form(""),
    featured: bool = Form(False),
    read_time: int = Form(5),
    featured_image: Optional[UploadFile] = File(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None)
):
    collection = get_collection("blog_posts")
    
    # Generate slug from title
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    
    # Check if slug already exists and make unique
    while True:
        existing_post = await collection.find_one({"slug": slug})
        if not existing_post:
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    # Handle featured image upload - UPDATED TO USE CLOUDINARY
    image_url = None
    if featured_image and featured_image.filename:
        try:
            print(f"📸 Uploading blog image to Cloudinary: {featured_image.filename}")
            image_url = await cloudinary_service.upload_blog_image(featured_image)
            print(f"✅ Blog image uploaded to Cloudinary: {image_url}")
        except Exception as e:
            print(f"❌ Cloudinary upload failed: {str(e)}")
            # Fallback to local storage if Cloudinary fails
            try:
                image_url = await save_upload_file(featured_image, "blog_images")
                print(f"📁 Using local storage fallback: {image_url}")
            except Exception as fallback_error:
                print(f"❌ Local storage also failed: {str(fallback_error)}")
                raise HTTPException(status_code=500, detail="Image upload failed")
    
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
        "status": BlogStatus.PUBLISHED,
        "author": "Admin",
        "views": 0,
        "likes": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "published_at": datetime.utcnow()
    }
    
    result = await collection.insert_one(post_data)
    
    return StandardResponse(
        success=True,
        message="Blog post created successfully",
        data={"post_id": str(result.inserted_id), "slug": slug}
    )

@router.put("/blog/posts/{post_id}", response_model=StandardResponse)
async def update_blog_post(
    post_id: str,
    title: Optional[str] = Form(None),
    excerpt: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    category: Optional[BlogCategory] = Form(None),
    tags: Optional[str] = Form(None),
    featured: Optional[bool] = Form(None),
    read_time: Optional[int] = Form(None),
    featured_image: Optional[UploadFile] = File(None),
    status: Optional[BlogStatus] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None)
):
    collection = get_collection("blog_posts")
    
    if not ObjectId.is_valid(post_id):
        raise HTTPException(400, "Invalid post ID")
    
    # Build update data
    update_data = {}
    if title is not None:
        update_data["title"] = title
        # Regenerate slug if title changes
        base_slug = slugify(title)
        slug = base_slug
        counter = 1
        
        # Ensure new slug is unique
        while True:
            existing_post = await collection.find_one({"slug": slug, "_id": {"$ne": ObjectId(post_id)}})
            if not existing_post:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        update_data["slug"] = slug
        
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
            update_data["published_at"] = datetime.utcnow()
    if meta_title is not None:
        update_data["meta_title"] = meta_title
    if meta_description is not None:
        update_data["meta_description"] = meta_description
    
    # Handle featured image upload - UPDATED TO USE CLOUDINARY
    if featured_image and featured_image.filename:
        try:
            print(f"📸 Uploading updated blog image to Cloudinary: {featured_image.filename}")
            image_url = await cloudinary_service.upload_blog_image(featured_image)
            print(f"✅ Updated blog image uploaded to Cloudinary: {image_url}")
            update_data["featured_image"] = image_url
        except Exception as e:
            print(f"❌ Cloudinary upload failed: {str(e)}")
            # Fallback to local storage
            try:
                image_url = await save_upload_file(featured_image, "blog_images")
                update_data["featured_image"] = image_url
                print(f"📁 Using local storage fallback: {image_url}")
            except Exception as fallback_error:
                print(f"❌ Local storage also failed: {str(fallback_error)}")
                raise HTTPException(status_code=500, detail="Image upload failed")
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(404, "Blog post not found")
    
    return StandardResponse(
        success=True,
        message="Blog post updated successfully"
    )

@router.delete("/blog/posts/{post_id}", response_model=StandardResponse)
async def delete_blog_post(post_id: str):
    collection = get_collection("blog_posts")
    
    if not ObjectId.is_valid(post_id):
        raise HTTPException(400, "Invalid post ID")
    
    # Optional: Delete image from Cloudinary when post is deleted
    # You can implement this later if needed
    
    result = await collection.delete_one({"_id": ObjectId(post_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(404, "Blog post not found")
    
    return StandardResponse(
        success=True,
        message="Blog post deleted successfully"
    )

@router.get("/blog/categories", response_model=List[str])
async def get_blog_categories():
    return [category.value for category in BlogCategory]

@router.get("/blog/stats", response_model=dict)
async def get_blog_stats():
    collection = get_collection("blog_posts")
    
    total_posts = await collection.count_documents({"status": BlogStatus.PUBLISHED})
    
    # Total views
    total_views_result = await collection.aggregate([
        {"$match": {"status": BlogStatus.PUBLISHED}},
        {"$group": {"_id": None, "total": {"$sum": "$views"}}}
    ]).to_list(1)
    total_views = total_views_result[0]["total"] if total_views_result else 0
    
    # Total likes
    total_likes_result = await collection.aggregate([
        {"$match": {"status": BlogStatus.PUBLISHED}},
        {"$group": {"_id": None, "total": {"$sum": "$likes"}}}
    ]).to_list(1)
    total_likes = total_likes_result[0]["total"] if total_likes_result else 0
    
    return {
        "total_posts": total_posts,
        "total_views": total_views,
        "total_likes": total_likes
    }

# Cloudinary test endpoint
@router.post("/blog/test-upload")
async def test_blog_image_upload(featured_image: UploadFile = File(...)):
    """Test Cloudinary upload for blog images"""
    try:
        if not featured_image.filename:
            return {"success": False, "error": "No file provided"}
        
        image_url = await cloudinary_service.upload_blog_image(featured_image)
        
        return {
            "success": True,
            "message": "✅ Blog image upload successful!",
            "data": {
                "image_url": image_url,
                "filename": featured_image.filename
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Debug endpoint to see all posts (remove in production)
@router.get("/blog/debug/posts")
async def debug_all_posts():
    collection = get_collection("blog_posts")
    posts = await collection.find().sort("created_at", -1).to_list(100)
    
    for post in posts:
        post["_id"] = str(post["_id"])
    
    return {
        "total": len(posts),
        "posts": posts
    }