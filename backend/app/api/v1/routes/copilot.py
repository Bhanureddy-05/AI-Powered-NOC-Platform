"""
app/api/v1/routes/copilot.py
============================
AI Copilot Chat & Session API Router
Exposes endpoints to create sessions, list history, and stream agent actions via SSE.
"""

import json
import asyncio
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db, async_session
from app.models.user import User
from app.models.copilot_session import CopilotSession
from app.models.copilot_message import CopilotMessage
from app.api.v1.routes.auth import get_current_user, check_role
from app.schemas.copilot import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageResponse,
    ChatQueryRequest
)
from app.services.copilot import copilot_model, vector_store

router = APIRouter(prefix="/copilot", tags=["AI Copilot Assistant"])

from sqlalchemy.orm import selectinload

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Lists all persistent AI Copilot chat sessions for the logged-in user.
    """
    stmt = select(CopilotSession).where(CopilotSession.user_id == current_user.id).options(selectinload(CopilotSession.messages)).order_by(CopilotSession.updated_at.desc())
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return sessions

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_in: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Creates a new chat session for the authenticated user.
    """
    title = session_in.title or f"Chat Session - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
    session = CopilotSession(
        user_id=current_user.id,
        title=title,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(session)
    await db.commit()
    
    # Reload with messages relationship loaded
    stmt = select(CopilotSession).where(CopilotSession.id == session.id).options(selectinload(CopilotSession.messages))
    res = await db.execute(stmt)
    return res.scalars().first()

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Deletes an existing chat session and its corresponding message history.
    """
    stmt = select(CopilotSession).where(CopilotSession.id == session_id, CopilotSession.user_id == current_user.id)
    result = await db.execute(stmt)
    session = result.scalars().first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied."
        )
        
    await db.delete(session)
    await db.commit()
    return

@router.get("/sessions/{session_id}/history", response_model=List[ChatMessageResponse])
async def get_session_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Loads all previous message threads for a specific chat session.
    """
    # Verify session ownership first
    sess_stmt = select(CopilotSession).where(CopilotSession.id == session_id, CopilotSession.user_id == current_user.id)
    sess_res = await db.execute(sess_stmt)
    session = sess_res.scalars().first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied."
        )

    stmt = select(CopilotMessage).where(CopilotMessage.session_id == session_id).order_by(CopilotMessage.timestamp.asc())
    result = await db.execute(stmt)
    messages = result.scalars().all()
    return messages

async def save_assistant_message(session_id: str, content: str, citations: list):
    async with async_session() as write_session:
        assistant_msg = CopilotMessage(
            session_id=session_id,
            role="assistant",
            content=content,
            citations=json.dumps(citations) if citations else None,
            timestamp=datetime.utcnow()
        )
        write_session.add(assistant_msg)
        
        # Fetch session again to update update time
        sess_fetch = await write_session.execute(
            select(CopilotSession).where(CopilotSession.id == session_id)
        )
        session_obj = sess_fetch.scalars().first()
        if session_obj:
            session_obj.updated_at = datetime.utcnow()
            
        await write_session.commit()

@router.post("/sessions/{session_id}/chat")
async def chat_with_agent(
    session_id: str,
    query_in: ChatQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["admin", "operator", "viewer"]))
):
    """
    Handles user queries. Streams agent tokens via Server-Sent Events (SSE),
    executes background operations tools, and saves full history.
    """
    # Verify session ownership
    sess_stmt = select(CopilotSession).where(CopilotSession.id == session_id, CopilotSession.user_id == current_user.id)
    sess_res = await db.execute(sess_stmt)
    session = sess_res.scalars().first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied."
        )

    query = query_in.query

    # Save User message
    user_msg = CopilotMessage(
        session_id=session_id,
        role="user",
        content=query,
        timestamp=datetime.utcnow()
    )
    db.add(user_msg)
    
    # Update session updated_at
    session.updated_at = datetime.utcnow()
    await db.commit()

    # Load session history context
    history_stmt = select(CopilotMessage).where(CopilotMessage.session_id == session_id).order_by(CopilotMessage.timestamp.asc())
    history_res = await db.execute(history_stmt)
    history_records = history_res.scalars().all()
    
    history_context = [{"role": m.role, "content": m.content} for m in history_records]

    async def sse_event_generator():
        accumulated_text = ""
        try:
            # Yield response chunks as Server-Sent Events (SSE)
            async for chunk in copilot_model.stream_response(query, history_context):
                accumulated_text += chunk
                payload = {"content": chunk, "session_id": session_id}
                yield f"data: {json.dumps(payload)}\n\n"
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"SSE stream error: {type(e).__name__}: {e}\n{tb}")
            # Yield error event with diagnostic detail
            err_payload = {"error": f"{type(e).__name__}: {e}", "content": f"\n\n⚠️ *AI Agent encountered a processing failure: {type(e).__name__}: {e}*"}
            yield f"data: {json.dumps(err_payload)}\n\n"
        finally:
            if accumulated_text:
                citations = []
                if "source_runbook" in accumulated_text.lower():
                    citations.append("source_runbook")
                # Fire-and-forget: do not hold stream open waiting for DB write
                asyncio.ensure_future(save_assistant_message(session_id, accumulated_text, citations))

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")
