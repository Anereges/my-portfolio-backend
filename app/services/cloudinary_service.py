import cloudinary
import cloudinary.uploader
import cloudinary.api
from fastapi import HTTPException, UploadFile
import os
from typing import Optional

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

class CloudinaryService:
    @staticmethod
    async def upload_blog_image(image_file: UploadFile, folder: str = "blog_images") -> str:
        """
        Upload image to Cloudinary and return secure URL
        """
        try:
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']
            if image_file.content_type not in allowed_types:
                raise HTTPException(status_code=400, detail="Invalid image format")
            
            # Read file content
            file_content = await image_file.read()
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                file_content,
                folder=folder,
                transformation=[
                    {"width": 800, "height": 500, "crop": "fill"},
                    {"quality": "auto:good"},
                    {"format": "auto"}
                ]
            )
            
            print(f"✅ Image uploaded to Cloudinary: {result['secure_url']}")
            return result['secure_url']
            
        except Exception as e:
            print(f"❌ Cloudinary upload error: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Image upload failed: {str(e)}"
            )

# Create instance
cloudinary_service = CloudinaryService()