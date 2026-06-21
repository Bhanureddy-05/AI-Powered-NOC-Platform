"""
app/schemas/copilot.py
======================
Pydantic Schemas for Copilot Session & Chat Message Validation & Serialization
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class ChatMessageCreate(BaseModel):
    content: str = Field(..., description="Message text content")

class ChatMessageResponse(BaseModel):
    id: int
    session_id: str
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    citations: Optional[str] = Field(default=None, description="Serialized JSON citations/sources")
    timestamp: datetime

    class Config:
        from_attributes = True

class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field(default="New AI Copilot Session", description="Optional title of the chat session")

class ChatSessionResponse(BaseModel):
    id: str
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = []

    class Config:
        from_attributes = True

class ChatQueryRequest(BaseModel):
    query: str = Field(..., description="User's query to the AI Agent")
