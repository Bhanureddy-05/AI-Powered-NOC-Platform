"""
tests/test_copilot.py
=====================
Pytest suite verifying AI Copilot and RAG features.
Tests dynamic runbook indexing, database session CRUD, and agent tool responses.
"""

import os
import pytest
from datetime import datetime
from sqlalchemy.future import select

from app.models.copilot_session import CopilotSession
from app.models.copilot_message import CopilotMessage
from app.services.copilot import (
    vector_store,
    execute_db_query,
    execute_log_search,
    execute_metrics_retrieval,
    copilot_model
)

@pytest.mark.asyncio
async def test_vector_store_fallback():
    """Verifies that the RAG vector store indexes markdown documentation and searches correctly."""
    # Initialize indexer
    vector_store.initialize_store()
    
    # Run similarity search
    results = vector_store.similarity_search("CPU usage mitigation", k=1)
    
    assert len(results) > 0
    assert "content" in results[0]
    assert "source" in results[0]
    assert "cpu_spike" in results[0]["source"].lower() or "runbook" in results[0]["source"].lower()

@pytest.mark.asyncio
async def test_log_search_tool():
    """Verifies simulated syslog query generator."""
    logs_all = await execute_log_search("core-router-01")
    logs_ssh = await execute_log_search("core-router-01", "SSH")
    
    assert "Simulated Syslog" in logs_all
    assert "SSH" in logs_ssh or "AAA_FAIL" in logs_ssh

@pytest.mark.asyncio
async def test_metrics_retrieval_tool(db_session):
    """Verifies telemetry metrics fetcher."""
    # Test query with a non-existent device
    res = await execute_metrics_retrieval("unknown-device-name")
    assert "not found" in res.lower()

@pytest.mark.asyncio
async def test_resilient_chat_model_fallback():
    """Verifies that the chatbot streams responses successfully using the fallback model."""
    chunks = []
    async for chunk in copilot_model.stream_response("How to mitigate high CPU on switch?"):
      chunks.append(chunk)
      
    full_response = "".join(chunks)
    assert len(full_response) > 0
    assert "Thought" in full_response or "NOC" in full_response
