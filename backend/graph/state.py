"""
Defines the state object for the LangGraph workflow.
Using Pydantic and TypedDict provides runtime data validation and clarity,
ensuring that data passed between nodes is structured correctly, which makes
the graph more robust and easier to debug.
"""

from pydantic import BaseModel, Field
from typing import Optional, TypedDict, List


class TriageResult(BaseModel):
    category: str = Field(
        description="The category of the email (e.g., 'job_application', 'spam', 'billing')."
    )
    priority: str = Field(
        description="The priority of the email ('low', 'medium', 'high')."
    )
    should_respond: bool = Field(
        description="Whether a response is required for this email."
    )
    reasoning: str = Field(
        description="A brief, one-sentence explanation for the classification and decision."
    )


class ExtractedData(BaseModel):
    summary: str = Field(
        description="A concise, one-sentence summary of the user's primary request."
    )
    has_attachments: bool = Field(
        description="Whether the email contains one or more file attachments."
    )


class AttachmentDetails(BaseModel):
    id: str
    filename: str
    mimeType: str


class EmailDetails(BaseModel):
    message_id: str
    thread_id: str
    sender_email: str
    subject: str
    full_content: str
    original_message_id_header: str
    attachments: List[AttachmentDetails] = []


class Intent(BaseModel):
    tool_name: str = Field(
        description="The name of the tool to use. Must be one of the available tool names or 'respond'."
    )
    tool_query: Optional[str] = Field(
        default=None, description="The specific query or argument to pass to the tool."
    )


class Critique(BaseModel):
    is_acceptable: bool = Field(
        description="Whether the draft is acceptable to send or needs revision."
    )
    feedback: str = Field(
        description="Constructive feedback for improving the draft if it is not acceptable."
    )


class AgentState(TypedDict, total=False):
    """The state passed between nodes in the graph."""

    email_details: EmailDetails
    conversation_history: str
    triage_result: TriageResult
    extracted_data: ExtractedData
    intent: Intent
    rag_context: str
    tool_output: str
    draft_reply: str
    learnable_fact: str
    # --- Self-Correction Loop Fields ---
    critique_feedback: str
    revision_count: int
    # --- Control Flow & Error Fields ---
    requires_review: bool
    error_message: str


class SearchRequest(BaseModel):
    query: str
