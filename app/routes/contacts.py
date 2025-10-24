from fastapi import APIRouter, Request, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
from bson import ObjectId

from app.database.mongodb import get_collection
from app.models.contact import ContactCreate, ContactResponse, ContactStatus
from app.schemas.response import StandardResponse, PaginatedResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

router = APIRouter()

# Email configuration with validation
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "amanuelsisay687@gmail.com")

def validate_email_config():
    """Validate that email configuration is present"""
    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        logger.warning("Email configuration missing. Email notifications will be disabled.")
        return False
    return True

async def send_email_notification(contact_data: dict):
    """Send email notification when someone contacts you"""
    # Check if email is configured
    if not validate_email_config():
        logger.info("Email notifications disabled - no configuration")
        return
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USERNAME
        msg['To'] = ADMIN_EMAIL
        msg['Subject'] = f"🔥 New Portfolio Contact: {contact_data.get('subject', 'General Inquiry')}"
        
        # Enhanced email body with better formatting
        body = f"""
        🚀 NEW CONTACT FORM SUBMISSION

        📋 Contact Details:
        • Name: {contact_data.get('name', 'Not provided')}
        • Email: {contact_data.get('email', 'Not provided')}
        • Subject: {contact_data.get('subject', 'General Inquiry')}
        • Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        💬 Message:
        {contact_data.get('message', 'No message provided')}

        🌐 Technical Details:
        • IP Address: {contact_data.get('ip_address', 'Not available')}
        • User Agent: {contact_data.get('user_agent', 'Not available')}
        • Submission ID: {contact_data.get('_id', 'Pending')}

        ---
        🔒 This message was sent from your portfolio contact form
        """

        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        logger.info(f"Attempting to send email via {SMTP_SERVER}:{SMTP_PORT}")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        
        # Login with credentials
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        
        # Send the email
        server.send_message(msg)
        server.quit()
        
        logger.info("✅ Email notification sent successfully to admin")
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ SMTP Authentication failed: {str(e)}")
        logger.error("Please check your EMAIL_USERNAME and EMAIL_PASSWORD")
    except smtplib.SMTPException as e:
        logger.error(f"❌ SMTP error occurred: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Failed to send email: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")

@router.post("/contacts", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(contact: ContactCreate, request: Request, background_tasks: BackgroundTasks):
    try:
        collection = get_collection("contacts")
        
        contact_dict = contact.dict()
        
        # Add metadata
        contact_dict["ip_address"] = request.client.host if request.client else None
        contact_dict["user_agent"] = request.headers.get("user-agent")
        contact_dict["status"] = "unread"
        contact_dict["created_at"] = datetime.utcnow()
        
        # Insert into database
        result = await collection.insert_one(contact_dict)
        contact_dict["_id"] = str(result.inserted_id)
        
        logger.info(f"✅ Contact saved to database: {contact_dict['name']} ({contact_dict['email']})")
        
        # Send email notification in background (won't block the response)
        background_tasks.add_task(send_email_notification, contact_dict)
        
        return StandardResponse(
            success=True,
            message="Thank you for your message! I'll get back to you soon.",
            data={
                "contact_id": str(result.inserted_id),
                "email_sent": validate_email_config()  # Indicate if email will be attempted
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error creating contact: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process your message. Please try again."
        )

@router.get("/contacts", response_model=PaginatedResponse)
async def get_contacts(
    page: int = 1,
    size: int = 20,
    status: ContactStatus = None
):
    collection = get_collection("contacts")
    
    filter_query = {}
    if status:
        filter_query["status"] = status
    
    total = await collection.count_documents(filter_query)
    skip = (page - 1) * size
    pages = (total + size - 1) // size
    
    contacts = await collection.find(filter_query).sort("created_at", -1).skip(skip).limit(size).to_list(size)
    
    for contact in contacts:
        contact["_id"] = str(contact["_id"])
    
    return PaginatedResponse(
        items=contacts,
        total=total,
        page=page,
        size=size,
        pages=pages
    )

@router.delete("/contacts/{contact_id}", response_model=StandardResponse)
async def delete_contact(contact_id: str):
    """
    Delete a contact message
    """
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(contact_id):
            raise HTTPException(status_code=400, detail="Invalid contact ID format")
            
        collection = get_collection("contacts")
        result = await collection.delete_one({"_id": ObjectId(contact_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        logger.info(f"✅ Contact deleted: {contact_id}")
        
        return StandardResponse(
            success=True,
            message="Contact deleted successfully",
            data={"deleted_count": result.deleted_count}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting contact: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid contact ID")

# Add health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for your frontend"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "email_configured": validate_email_config()
    }