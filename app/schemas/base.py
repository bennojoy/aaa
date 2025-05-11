from pydantic import BaseModel
from typing import Optional, Any, Dict

class BaseResponse(BaseModel):
    trace_id: str

class ErrorResponse(BaseResponse):
    error: str
    message: str

class SuccessResponse(BaseResponse):
    data: Optional[Any] = None
    message: Optional[str] = None

class PaginatedResponse(BaseResponse):
    items: list
    total: int
    page: int
    size: int
    pages: int 