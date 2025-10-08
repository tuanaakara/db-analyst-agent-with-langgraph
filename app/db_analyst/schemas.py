"""
Data schemas for the AI Analyst agent.

This module defines all data structures for the project, including:
1.  Internal State Management: The AnalystState class for the LangGraph workflow.
2.  API Contracts: Pydantic models for API request and response bodies.
"""
from typing import Dict, Any, List, Optional, TypedDict, Annotated
import operator
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


# --- 1. Internal State Management Schema ---

class AnalystState(TypedDict):
    """
    Represents the internal state of the agent's LangGraph workflow.
    This is the agent's "memory" as it moves from one step to another.
    """
    messages: Annotated[list[BaseMessage], operator.add]
    plan: Optional[List[str]]
    executed_steps: Optional[Dict[str, Any]]
    user_query: str
    db_schema: str
    context: Optional[Dict[str, Any]]
    current_step_index: Optional[int]
    accumulated_data: Optional[Dict[str, Any]]
    log_messages: Optional[List[Dict[str, Any]]]


# --- 2. API Contract Schemas (Request/Response) ---

class AnalyzeRequest(BaseModel):
    """
    Schema for the request body sent to the analysis API endpoint.
    This defines the data contract for what the frontend must send.
    """
    user_query: str = Field(..., min_length=1, description="The user's question in natural language.")
    # ileride chat_id gibi başka alanlar da eklenebilir
    # chat_id: Optional[str] = None


class StreamUpdate(BaseModel):
    """
    Schema for a single update chunk sent in the streaming API response.
    This defines the data contract for what the backend will send back.
    """
    type: str = Field(..., description="The type of the update (e.g., 'plan', 'sql_query', 'final_result').")
    content: Any = Field(..., description="The content of the update, which can be a list, string, or dict.")
    step: Optional[int] = None # Hangi adıma ait olduğu bilgisi