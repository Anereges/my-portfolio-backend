from pydantic import BaseModel
from typing import Any, Optional, List, Dict

class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

class PaginatedResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int
    pages: int

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Any] = None