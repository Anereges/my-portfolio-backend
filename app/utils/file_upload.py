import aiofiles
from fastapi import UploadFile
from PIL import Image
import secrets
from pathlib import Path

# Base directory - CORRECTED to match main.py exactly
# file_upload.py location: aman_portfolio/backend/app/utils/file_upload.py
# We want BASE_DIR to point to: aman_portfolio/backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Points to backend/

async def save_upload_file(upload_file: UploadFile, subfolder: str = "general") -> str:
    """
    Save uploaded file into backend/blog_images/ and return its URL path
    """
    try:
        # Create upload directory - EXACTLY matches main.py
        upload_path = BASE_DIR / "blog_images"  # Same as main.py: aman_portfolio/backend/blog_images
        upload_path.mkdir(parents=True, exist_ok=True)

        # Generate a secure random filename
        file_extension = upload_file.filename.split('.')[-1] if '.' in upload_file.filename else 'jpg'
        random_hex = secrets.token_hex(8)
        filename = f"{random_hex}.{file_extension}"
        file_path = upload_path / filename

        # Read and save the uploaded file
        contents = await upload_file.read()
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(contents)

        # Optimize if it's an image
        if upload_file.content_type and upload_file.content_type.startswith('image/'):
            await optimize_image(file_path)

        # Return URL path that FastAPI will serve
        return f"/uploads/{filename}"

    except Exception as e:
        print(f"Error saving file: {e}")
        return None

async def optimize_image(file_path: Path, max_size: tuple = (1200, 800)):
    """
    Optimize image size and quality
    """
    try:
        with Image.open(file_path) as img:
            # Convert to RGB if image uses unsupported mode
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Resize image if larger than max size
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Save optimized image
            img.save(
                file_path,
                "JPEG" if file_path.suffix.lower() in ['.jpg', '.jpeg'] else "PNG",
                optimize=True,
                quality=85
            )
    except Exception as e:
        print(f"Image optimization failed: {e}")

async def delete_file(file_path: str):
    """
    Delete file from filesystem if exists
    """
    try:
        if file_path and file_path.startswith('/uploads/'):
            # Convert URL path to actual filesystem path - EXACTLY matches main.py
            filename = file_path.lstrip('/uploads/')
            actual_path = BASE_DIR / "blog_images" / filename  # Same as main.py
            if actual_path.exists():
                actual_path.unlink()
                return True
        return False
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
        return False

# Debugging function to verify paths match
def debug_paths():
    """Verify that file_upload.py uses the same paths as main.py"""
    upload_path = BASE_DIR / "blog_images"
    print("=" * 60)
    print("🔍 FILE_UPLOAD.PY PATH DEBUGGING")
    print("=" * 60)
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"Upload path: {upload_path}")
    print(f"Path exists: {upload_path.exists()}")
    
    if upload_path.exists():
        print(f"Files in directory:")
        for file_path in upload_path.iterdir():
            print(f"  - {file_path.name}")
    print("=" * 60)

# Run debug when module is loaded
debug_paths()