"""
Defines the advanced toolkit for the conversational chat agent.
These tools allow the agent to query databases, search Gmail/Drive,
and take actions on behalf of the user.
"""

from langchain.tools import tool
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
import config

from services.google_api_service import GoogleApiService
from services.draft_service import DraftService
from services.priority_service import PriorityService
from utils.logger import get_logger
from utils.email_parser import parse_email_content
from services.knowledge_base import KnowledgeBase
from .attachment_handler import analyze_and_save_attachments


logger = get_logger(__name__)


class DraftReplyArgs(BaseModel):
    """Structured arguments for drafting a reply."""

    subject: Optional[str] = Field(
        default=None,
        description="The subject of the email to reply to. Can be partial.",
    )
    sender: Optional[str] = Field(
        default=None,
        description="The email address of the person who sent the email to reply to.",
    )
    instructions: str = Field(
        description="The user's instructions for the reply content."
    )

    @field_validator("subject", "sender", "instructions")
    def check_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError("String fields cannot be empty.")
        return v

    @field_validator("instructions")
    def instructions_must_exist(cls, v):
        if not v:
            raise ValueError("Reply instructions must be provided.")
        return v


# --- Pydantic Models for Robust Tool Arguments ---
class EmailArgs(BaseModel):
    to: str = Field(description="The recipient's email address.")
    subject: str = Field(description="The subject of the email.")
    body: str = Field(description="The content of the email body.")


class SendEmailArgs(BaseModel):
    """Structured arguments for sending an email."""

    recipient: str = Field(description="The email address of the recipient.")
    subject: str = Field(description="The subject line of the email.")
    body: str = Field(description="The main content/body of the email.")
    confirm: bool = Field(
        default=False, description="Confirmation flag. Must be true to send."
    )


class ReplyArgs(BaseModel):
    query: str = Field(
        description="A Gmail search query to find the target email (e.g., 'from:jane@example.com subject:Update')."
    )


class MessageIdArgs(BaseModel):
    """A reusable model for tools that operate on a single email message ID."""

    message_id: str = Field(description="The unique ID of the email message.")


# --- Database Query Tools ---
@tool
def get_pending_drafts_summary() -> List[str]:
    """
    Returns a list of summaries for all draft emails currently awaiting user review.
    """
    draft_service = DraftService()
    drafts = draft_service.get_pending_drafts()
    if not drafts:
        return ["No drafts are currently pending review."]
    return [
        f"Draft to {d.get('from', 'N/A')} with subject: '{d.get('subject', 'N/A')}'"
        for d in drafts
    ]


@tool
def get_high_priority_summary() -> List[Dict[str, Any]]:
    """
    Returns a list of summaries for all emails currently in the high-priority queue.
    Each item includes the sender, subject, and the AI-generated summary of the email's content.
    Use this to answer questions about what needs urgent attention or to get a summary of a specific high-priority email.
    """
    priority_service = PriorityService()
    items = priority_service.get_pending_items()
    if not items:
        return [{"message": "The high-priority queue is empty."}]

    return [
        {
            "from": i.get("from", "N/A"),
            "subject": i.get("subject", "N/A"),
            "summary": i.get("summary", "No summary available."),
        }
        for i in items
    ]


# --- Action-Taking Tools ---
@tool(args_schema=MessageIdArgs)
def get_full_email_content(message_id: str) -> str:
    """
    Retrieves the full, plain-text body of a specific email by its message ID.
    Use this when a user asks to see the complete content of an email that has been summarized.
    """
    logger.info(f"Retrieving full content for email ID: {message_id}")
    google_api_service = GoogleApiService()
    try:
        email_details = google_api_service.get_email_details(message_id)
        if not email_details:
            return f"Error: No email found with the ID '{message_id}'."

        parsed_content = parse_email_content(email_details)
        return f"Full content of email from {parsed_content['from']} with subject '{parsed_content['subject']}':\n\n{parsed_content['body']}"

    except Exception as e:
        logger.error(
            f"Error retrieving full email content for {message_id}: {e}", exc_info=True
        )
        return f"An unexpected error occurred while fetching the email: {e}"


@tool(args_schema=MessageIdArgs)
def list_attachments(message_id: str) -> List[Dict[str, str]]:
    """
    Lists the filenames and types of all attachments found in a specific email.
    Use this when a user asks what files are attached to an email.
    """
    logger.info(f"Listing attachments for email ID: {message_id}")
    google_api_service = GoogleApiService()
    try:
        email_details = google_api_service.get_email_details(message_id)
        if not email_details:
            return [{"error": f"No email found with the ID '{message_id}'."}]

        parsed_content = parse_email_content(email_details)
        attachments = parsed_content.get("attachments", [])

        if not attachments:
            return [{"message": "No attachments found in this email."}]

        return [
            {"filename": att["filename"], "type": att["mimeType"]}
            for att in attachments
        ]

    except Exception as e:
        logger.error(f"Error listing attachments for {message_id}: {e}", exc_info=True)
        return [{"error": f"An unexpected error occurred: {e}"}]


@tool(args_schema=MessageIdArgs)
def star_email(message_id: str) -> str:
    """
    Adds or removes a star from a specific email. This action toggles the star status.
    Use this to highlight important emails or remove their highlight.
    """
    logger.info(f"Toggling star for email ID: {message_id}")
    google_api_service = GoogleApiService()
    try:
        result = google_api_service.toggle_star_email(message_id)
        return result
    except Exception as e:
        logger.error(f"Error toggling star for {message_id}: {e}", exc_info=True)
        return f"An unexpected error occurred while starring the email: {e}"


@tool(args_schema=MessageIdArgs)
def delete_email(message_id: str) -> str:
    """
    Moves a specific email to the trash. This is a soft delete, not permanent.
    Use this when the user wants to remove an email from their inbox.
    """
    logger.info(f"Moving email ID to trash: {message_id}")
    google_api_service = GoogleApiService()
    try:
        google_api_service.trash_email(message_id)
        return f"Successfully moved email with ID '{message_id}' to the trash."
    except Exception as e:
        logger.error(f"Error moving email {message_id} to trash: {e}", exc_info=True)
        return f"An unexpected error occurred while deleting the email: {e}"


@tool(args_schema=EmailArgs)
def send_email_directly(to: str, subject: str, body: str) -> str:
    """
    Sends an email immediately without a review step. Use for simple, direct commands.
    """
    logger.info(f"Attempting to send email directly to {to}")
    google_api_service = GoogleApiService()
    try:
        result = google_api_service.send_email(to=to, subject=subject, body=body)
        if result and result.get("id"):
            return f"Successfully sent an email to {to} with subject '{subject}'."
        else:
            return "Error: Failed to send the email via Gmail API."
    except Exception as e:
        logger.error(f"Error in send_email_directly tool: {e}", exc_info=True)
        return f"An unexpected error occurred: {e}"


@tool(args_schema=ReplyArgs)
def draft_a_reply(query: str) -> str:
    """
    Creates a draft reply to a specific email based on a single natural language instruction.
    The input 'query' should contain all necessary information, such as the subject and/or sender of the email to reply to, and the instructions for the reply.
    For example: 'draft a reply to the email from jane@example.com about "Screening Call" saying I am available tomorrow at 2 PM.'
    """
    logger.info(f"Attempting to draft a reply based on query: '{query}'")

    llm = ChatGoogleGenerativeAI(
        model=config.LLM_MODEL_NAME, temperature=config.LLM_TEMPERATURE
    )
    parser_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert at extracting structured data from a user's request. Extract the subject of the email they want to reply to, the sender's email address, and their instructions for the reply content. At least one of subject or sender must be present.",
            ),
            (
                "human",
                "Please extract the subject, sender, and instructions from this query:\n\n{query}",
            ),
        ]
    )
    parser_chain = parser_prompt | llm.with_structured_output(DraftReplyArgs)

    try:
        parsed_args = parser_chain.invoke({"query": query})
    except Exception as e:
        logger.error(f"Failed to parse draft reply query: {e}")
        return f"Error: I could not understand the request to draft a reply. Please be more specific. Error details: {e}"

    google_api_service = GoogleApiService()
    draft_service = DraftService()

    search_query_parts = []
    if parsed_args.subject:
        search_query_parts.append(f'subject:"{parsed_args.subject}"')
    if parsed_args.sender:
        search_query_parts.append(f'from:"{parsed_args.sender}"')
    search_query = " ".join(search_query_parts)

    messages = google_api_service.search_emails_by_query(search_query, max_results=1)
    if not messages:
        return f"Error: Could not find an email matching the criteria: {search_query}"

    message_id = messages[0]["id"]
    full_email_data_raw = google_api_service.get_email_details(message_id)
    if not full_email_data_raw:
        return "Error: Could not fetch details for the found email."

    parsed_email = parse_email_content(full_email_data_raw)

    reply_content = llm.invoke(
        f"Based on these instructions: '{parsed_args.instructions}', write a professional email body. Sign it 'Sincerely,\nM Bharadwaj'."
    ).content

    gmail_draft_id = google_api_service.create_draft(
        to=parsed_email["sender_email"],
        subject=f"Re: {parsed_email['subject']}",
        body=reply_content,
        thread_id=full_email_data_raw["threadId"],
        in_reply_to=parsed_email["message_id"],
    )

    if not gmail_draft_id:
        return "Error: Failed to create the draft in Gmail."

    draft_data = {
        "id": message_id,
        "gmailDraftId": gmail_draft_id,
        "threadId": full_email_data_raw["threadId"],
        "from": parsed_email["from"],
        "subject": f"Re: {parsed_email['subject']}",
        "body": reply_content,
        "category": "other",
        "chainOfThought": "Drafted via Chat Command",
    }
    draft_service.create_draft(draft_data)
    return f"Successfully created a draft reply to the email with subject '{parsed_email['subject']}'. It is now in the Action Queue for your review."


# --- Search Tools ---
@tool
def search_google_drive(query: str) -> List[Dict[str, str]]:
    """
    Performs a live search of your Google Drive for a specific query.
    """
    logger.info(f"Performing Google Drive search with query: {query}")
    google_api_service = GoogleApiService()
    files = google_api_service.search_drive_files(query, max_results=5)
    if not files:
        return [{"message": f"No files found in Google Drive matching '{query}'."}]
    return [{"name": f.get("name"), "url": f.get("webViewLink")} for f in files]


@tool
def search_gmail(query: str) -> List[str]:
    """
    Performs a live search of your Gmail inbox for a specific query and returns a list of matching email subjects.
    """
    logger.info(f"Performing Gmail search: {query}")
    google_api_service = GoogleApiService()
    messages = google_api_service.search_emails_by_query(query, max_results=5)
    if not messages:
        return [f"No emails found matching the query: '{query}'"]

    results = []
    for msg in messages:
        details = google_api_service.get_email_details(msg["id"])
        if details:
            parsed = parse_email_content(details)
            results.append(
                f"Email from {parsed['from']} with subject: '{parsed['subject']}'"
            )
    return results


@tool
def knowledge_tool(query: str) -> str:
    """
    Searches the user's personal knowledge base to answer questions about their contacts, projects, or other learned facts.
    Use this as the primary tool for questions about specific people, internal projects, or user preferences.
    For example: 'What is Jane Doe's phone number?' or 'What are the key points from the Project Phoenix kickoff meeting?'
    """
    logger.info(f"Querying knowledge base for: '{query}'")
    knowledge_base = KnowledgeBase()
    retriever = knowledge_base.get_retriever()
    try:
        results = retriever.get_relevant_documents(query)
        if not results:
            return "I couldn't find any information about that in your knowledge base."
        return "\n".join([doc.page_content for doc in results])
    except Exception as e:
        logger.error(f"Knowledge base query failed: {e}", exc_info=True)
        return f"An error occurred while searching the knowledge base: {e}"


@tool
def contact_lookup(name: str) -> str:
    """
    Looks up contact information for a specific person from Google Contacts.
    Use this when you need to find an email address or other contact details for someone by name.
    """
    logger.info(f"Looking up contact: {name}")
    google_api_service = GoogleApiService()
    try:
        query = f"from:{name} or to:{name}"
        messages = google_api_service.search_emails_by_query(query, max_results=1)
        if not messages:
            return f"No contact information found for '{name}' in recent emails."

        details = google_api_service.get_email_details(messages[0]["id"])
        from_header = next(
            (
                h["value"]
                for h in details["payload"]["headers"]
                if h["name"].lower() == "from"
            ),
            "",
        )
        return f"Found contact details in a recent email: {from_header}"
    except Exception as e:
        logger.error(f"Contact lookup failed: {e}", exc_info=True)
        return f"An error occurred during contact lookup: {e}"


@tool(args_schema=SendEmailArgs)
def send_email(recipient: str, subject: str, body: str, confirm: bool = False) -> str:
    """
    Sends an email. This is a powerful tool that requires confirmation.
    The agent must first call this tool with confirm=False. The tool will return a confirmation message.
    The agent must then ask the user for approval. If the user approves, the agent calls the tool again with confirm=True to actually send the email.
    """
    if not confirm:
        logger.info("Confirmation requested for sending email.")
        return f"CONFIRMATION_REQUIRED: Please ask the user to confirm sending an email to '{recipient}' with subject '{subject}'."

    logger.info(f"Sending email to {recipient} with subject: {subject}")
    google_api_service = GoogleApiService()
    try:
        google_api_service.send_email(to=recipient, subject=subject, body=body)
        return "Email sent successfully."
    except Exception as e:
        logger.error(f"Failed to send email: {e}", exc_info=True)
        return f"An error occurred while sending the email: {e}"


@tool
def process_attachment(message_id: str) -> str:
    """
    Analyzes and saves attachments from a specific email to Google Drive.
    Use this tool when an email has attachments that need to be processed, analyzed, or stored.
    The message_id of the email must be known.
    """
    logger.info(f"Processing attachments for message ID: {message_id}")

    google_api_service = GoogleApiService()
    llm = ChatGoogleGenerativeAI(model=config.LLM_MODEL_NAME)

    email_details_raw = google_api_service.get_email_details(message_id)
    if not email_details_raw:
        return f"Error: Could not find email with ID {message_id}."

    parsed_email = parse_email_content(email_details_raw)

    return analyze_and_save_attachments(
        google_api_service=google_api_service,
        llm=llm,
        message_id=message_id,
        email_context=parsed_email["body"],
        attachments=parsed_email["attachments"],
    )
