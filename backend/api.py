"""
This script creates a FastAPI web server to expose the email agent's functionality.
It provides API endpoints for the React frontend to interact with the agent and
a WebSocket for real-time communication and logging.
"""

import asyncio
import sys
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_google_genai import ChatGoogleGenerativeAI
import config
from graph.orchestrator import GraphOrchestrator
from graph.state import AgentState, EmailDetails, SearchRequest
from services.google_api_service import GoogleApiService
from services.knowledge_base import KnowledgeBase
from services.memory_service import MemoryService
from services.state_manager import StateManager
from services.learning_service import LearningService
from services.draft_service import DraftService
from services.priority_service import PriorityService
from services.chat_agent_service import ChatAgentService
from services.settings_service import SettingsService
from knowledge_manager import process_learning_approvals
from utils.email_parser import parse_email_content
from utils.logger import get_logger
from tools.tool_registry import ToolRegistry


# --- FastAPI App Initialization ---
app = FastAPI(
    title="Gmail Assistant API",
    description="API for controlling and monitoring the AI Email Automation System.",
)

logger = get_logger(__name__)

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"New client connected. Total clients: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(
            f"Client disconnected. Total clients: {len(self.active_connections)}"
        )

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()

# --- Global Services & State Initialization ---
stop_event = asyncio.Event()
app_state = {}
llm = None
graph_orchestrator = None
chat_agent_service = None
tool_registry = None
settings_service = None
knowledge_base = None
google_api_service = None
current_settings = {}

# --- prevent race conditions on the background task ---
background_task_lock = asyncio.Lock()


def initialize_dynamic_services():
    """Initializes or re-initializes services that depend on settings."""
    global llm, graph_orchestrator, chat_agent_service, tool_registry, current_settings

    current_settings = settings_service.get_settings()
    llm = ChatGoogleGenerativeAI(
        model=current_settings.get("llm_model_name", config.LLM_MODEL_NAME),
        temperature=current_settings.get("llm_temperature", config.LLM_TEMPERATURE),
    )
    logger.info(
        f"LLM Initialized with Model: {llm.model}, Temperature: {llm.temperature}"
    )

    tool_registry = ToolRegistry(
        google_api_service=google_api_service, knowledge_base=knowledge_base, llm=llm
    )
    graph_orchestrator = GraphOrchestrator(
        llm, knowledge_base, google_api_service, tool_registry
    )
    chat_agent_service = ChatAgentService(
        tool_registry=tool_registry, google_api_service=google_api_service, llm=llm
    )
    logger.info("Dynamic services re-initialized with latest settings.")


try:
    logger.info("--- Initializing AI Email Automation System Services ---")

    google_api_service = GoogleApiService()
    state_manager = StateManager()
    memory_service = MemoryService()
    knowledge_base = KnowledgeBase()
    settings_service = SettingsService(knowledge_base=knowledge_base)

    learning_service = LearningService()
    draft_service = DraftService()
    priority_service = PriorityService()

    initialize_dynamic_services()

    logger.info(
        f"LLM Initialized with Model: {llm.model}, Temperature: {llm.temperature}"
    )

    logger.info("Loading persistent state from Firestore...")
    app_state = {
        "agent_status": "Stopped",
        "last_checked": None,
        "activity_feed": [],
        "drafts_queue": draft_service.get_pending_drafts(),
        "learning_queue": learning_service.get_pending_proposals(),
        "priority_queue": priority_service.get_pending_items(),
        "starred_queue": google_api_service.search_starred_emails(),
        "chat_history": [],
    }
    logger.info(
        f"Loaded {len(app_state['drafts_queue'])} drafts, {len(app_state['learning_queue'])} learning proposals, and {len(app_state['priority_queue'])} high-priority items."
    )

except Exception as e:
    logger.error(f"FATAL ERROR during initialization: {e}", exc_info=True)
    app_state = {
        "agent_status": "Error",
        "last_checked": None,
        "activity_feed": [
            {
                "time": time.strftime("%I:%M:%S %p"),
                "message": f"Fatal Error during startup: {e}",
                "type": "error",
            }
        ],
        "drafts_queue": [],
        "learning_queue": [],
        "priority_queue": [],
        "starred_queue": [],
        "chat_history": [],
    }

# --- Background Task Control ---
background_task: Optional[asyncio.Task] = None
stop_event = asyncio.Event()


async def log_and_broadcast(
    message: str,
    type: str = "log",
    exc_info=False,
    notification_type: Optional[str] = None,
):
    """Logs a message and broadcasts it over WebSocket, respecting notification settings."""
    if exc_info:
        logger.error(message, exc_info=True)
    else:
        logger.info(message)

    timestamp = time.strftime("%I:%M:%S %p")
    log_entry = {"time": timestamp, "message": message, "type": type}

    app_state["activity_feed"].insert(0, log_entry)
    if len(app_state["activity_feed"]) > 100:
        app_state["activity_feed"].pop()

    broadcast_message = {"type": "log", "payload": log_entry}

    if notification_type:
        triggers = current_settings.get("notification_triggers", {})
        should_notify = triggers.get(notification_type, True)
        if should_notify:
            broadcast_message["notification_type"] = notification_type

    await manager.broadcast(broadcast_message)


# --- Core Agent Logic ---
async def process_emails():
    """The core logic for fetching, processing, and acting on emails."""
    global app_state
    if app_state["agent_status"] == "Processing":
        await log_and_broadcast("Agent is already processing. Skipping new run.")
        return

    app_state["agent_status"] = "Processing"
    app_state["last_checked"] = time.ctime()
    await manager.broadcast(
        {
            "type": "status_update",
            "payload": {"agent_status": app_state["agent_status"]},
        }
    )
    await log_and_broadcast("Agent status changed to Processing.")

    try:
        unread_messages = google_api_service.search_unread_emails()

        if not unread_messages:
            await log_and_broadcast("No new unread emails found.")
        else:
            await log_and_broadcast(f"Found {len(unread_messages)} new email(s).")
            for msg_summary in unread_messages:
                if stop_event.is_set():
                    await log_and_broadcast(
                        "Stop signal received, halting email processing."
                    )
                    break

                message_id = msg_summary["id"]

                if state_manager.is_processed(message_id):
                    google_api_service.modify_email_labels(message_id, [], ["UNREAD"])
                    continue

                await log_and_broadcast(f"Processing new email with ID: {message_id}")
                full_email_data = google_api_service.get_email_details(message_id)
                if not full_email_data:
                    await log_and_broadcast(
                        f"Could not fetch details for email {message_id}. Skipping.",
                        "error",
                    )
                    continue

                parsed_email = parse_email_content(full_email_data)
                thread_id = full_email_data.get("threadId")
                received_timestamp = (
                    int(full_email_data.get("internalDate", "0")) / 1000
                )

                if not thread_id:
                    await log_and_broadcast(
                        f"Email {message_id} is missing threadId. Skipping.", "error"
                    )
                    google_api_service.modify_email_labels(
                        message_id, [config.GMAIL_PROCESSED_LABEL], ["UNREAD"]
                    )
                    continue

                conversation_history = memory_service.get_history(thread_id)

                initial_state: AgentState = {
                    "email_details": EmailDetails(
                        message_id=message_id,
                        thread_id=thread_id,
                        sender_email=parsed_email["sender_email"],
                        subject=parsed_email["subject"],
                        full_content=f"From: {parsed_email['from']}\nSubject: {parsed_email['subject']}\n\n{parsed_email['body']}",
                        original_message_id_header=parsed_email["message_id"],
                    ),
                    "conversation_history": conversation_history,
                    "revision_count": 0,
                }

                final_state = await asyncio.to_thread(
                    graph_orchestrator.invoke, initial_state
                )

                if final_state.get("error_message"):
                    await log_and_broadcast(
                        f"Workflow failed for email {message_id}. It will be retried on the next cycle. Error: {final_state['error_message']}",
                        "error",
                    )
                    continue

                triage_result = final_state.get("triage_result")

                extracted_data_obj = final_state.get("extracted_data")
                summary = (
                    extracted_data_obj.summary
                    if extracted_data_obj
                    else "No summary available."
                )

                labels_to_add = [config.GMAIL_PROCESSED_LABEL]
                labels_to_remove = ["UNREAD"]

                if triage_result and triage_result.priority == "high":
                    is_starred = "STARRED" in full_email_data.get("labelIds", [])
                    priority_item = {
                        "id": message_id,
                        "threadId": thread_id,
                        "from": parsed_email["sender_email"],
                        "subject": parsed_email["subject"],
                        "summary": summary,
                        "timestamp": received_timestamp,
                        "is_starred": is_starred,
                    }
                    priority_service.create_item(priority_item)
                    labels_to_add.append(config.GMAIL_HIGH_PRIORITY_LABEL)
                    app_state["priority_queue"] = priority_service.get_pending_items()
                    await manager.broadcast(
                        {
                            "type": "priority_update",
                            "payload": app_state["priority_queue"],
                            "notification_type": "priority_item",
                        }
                    )

                    await log_and_broadcast(
                        f"High-priority item added: {summary}",
                        notification_type="priority_item",
                    )

                if final_state.get("learnable_fact"):
                    learning_service.create_proposal(
                        message_id,
                        final_state["learnable_fact"],
                        parsed_email["sender_email"],
                        timestamp=received_timestamp,
                    )
                    labels_to_add.append(config.GMAIL_LEARNING_PROPOSAL_LABEL)
                    app_state["learning_queue"] = (
                        learning_service.get_pending_proposals()
                    )
                    await manager.broadcast(
                        {
                            "type": "learning_update",
                            "payload": app_state["learning_queue"],
                            "notification_type": "new_learning",
                        }
                    )

                    await log_and_broadcast(
                        "New learning proposal created.",
                        notification_type="new_learning",
                    )

                if final_state.get("draft_reply") and final_state.get(
                    "requires_review"
                ):
                    draft_body = final_state["draft_reply"]
                    draft_subject = f"Re: {parsed_email['subject']}"
                    gmail_draft_id = google_api_service.create_draft(
                        to=parsed_email["sender_email"],
                        subject=draft_subject,
                        body=draft_body,
                        thread_id=thread_id,
                        in_reply_to=parsed_email["message_id"],
                    )
                    if gmail_draft_id:
                        draft_data = {
                            "id": message_id,
                            "gmailDraftId": gmail_draft_id,
                            "threadId": thread_id,
                            "from": parsed_email["sender_email"],
                            "subject": draft_subject,
                            "body": draft_body,
                            "category": triage_result.category
                            if triage_result
                            else "other",
                            "summary": summary,
                            "timestamp": received_timestamp,
                        }
                        draft_service.create_draft(draft_data)
                        labels_to_add.append(config.GMAIL_NEEDS_REVIEW_LABEL)
                        memory_service.add_to_history(thread_id, summary, draft_body)
                        app_state["drafts_queue"] = draft_service.get_pending_drafts()
                        await manager.broadcast(
                            {
                                "type": "drafts_update",
                                "payload": app_state["drafts_queue"],
                                "notification_type": "new_draft",
                            }
                        )

                        await log_and_broadcast(
                            "New draft created for review.",
                            notification_type="new_draft",
                        )

                google_api_service.modify_email_labels(
                    message_id, list(set(labels_to_add)), labels_to_remove
                )
                state_manager.add_processed_id(message_id)
                await log_and_broadcast(f"Finished processing email ID: {message_id}")

    except Exception as e:
        await log_and_broadcast(
            f"A critical error occurred in the processing loop: {e}",
            "error",
            exc_info=True,
        )
    finally:
        if not stop_event.is_set():
            app_state["agent_status"] = "Idle"
            await manager.broadcast(
                {
                    "type": "status_update",
                    "payload": {"agent_status": app_state["agent_status"]},
                }
            )
            await log_and_broadcast("Agent status changed to Idle.")


async def main_loop():
    """The main continuous loop for the agent. Runs until stop_event is set."""
    while not stop_event.is_set():
        try:
            await process_emails()
            if stop_event.is_set():
                break
            process_learning_approvals(
                google_api_service, learning_service, knowledge_base
            )
            if stop_event.is_set():
                break
        except Exception as e:
            await log_and_broadcast(f"Error in main loop: {e}", "error", exc_info=True)

        try:
            interval = current_settings.get(
                "check_interval_seconds", config.CHECK_INTERVAL_SECONDS
            )
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass

    logger.info("Main loop has been stopped.")


# --- API Endpoints ---
@app.on_event("startup")
async def on_startup():
    """Check settings on startup to see if we should start the agent."""
    if settings_service:
        startup_settings = settings_service.get_settings()
        if startup_settings.get("start_on_launch", False):
            logger.info("Start on Launch is enabled. Starting agent automatically.")
            # run this in the background
            asyncio.create_task(start_email_check())
    else:
        logger.error(
            "Settings service not initialized at startup, cannot check 'start_on_launch'."
        )


@app.get("/api/state")
async def get_full_state():
    return app_state


@app.get("/api/labels")
async def get_labels():
    """Endpoint to retrieve all user-defined Gmail labels."""
    if not google_api_service:
        raise HTTPException(status_code=503, detail="Google API service not available.")
    return google_api_service.get_all_labels()


@app.get("/api/emails-by-label/{label_id}")
async def get_emails_by_label(
    label_id: str, query: str = "", page_token: Optional[str] = None
):
    """Endpoint to retrieve emails for a specific label, with pagination and search."""
    if not google_api_service:
        raise HTTPException(status_code=503, detail="Google API service not available.")
    return google_api_service.search_emails_by_label(label_id, query, page_token)


@app.post("/api/trigger-check")
async def start_email_check():
    """Starts the background email processing task."""
    global background_task
    async with background_task_lock:
        if background_task and not background_task.done():
            return {"message": "Processing task is already running."}

        stop_event.clear()
        background_task = asyncio.create_task(main_loop())
        app_state["agent_status"] = "Idle"
    await manager.broadcast(
        {"type": "status_update", "payload": {"agent_status": "Idle"}}
    )
    await log_and_broadcast("Manual email processing started.")
    return {"message": "Email processing started."}


@app.post("/api/stop-check")
async def stop_email_check():
    """Stops the background email processing task."""
    global background_task
    async with background_task_lock:
        if not background_task or background_task.done():
            return {"message": "Processing task is not running."}

        stop_event.set()
        await log_and_broadcast("Stop signal sent to processing loop.")

        try:
            await asyncio.wait_for(background_task, timeout=10)
        except asyncio.TimeoutError:
            await log_and_broadcast(
                "Task did not stop in time, may need to be cancelled.", "error"
            )

        background_task = None
        app_state["agent_status"] = "Stopped"
    await manager.broadcast(
        {"type": "status_update", "payload": {"agent_status": "Stopped"}}
    )
    await log_and_broadcast("Email processing stopped.")
    return {"message": "Email processing stopped."}


@app.post("/api/search")
async def global_search(request: SearchRequest):
    """
    New endpoint for the global search bar. Performs a federated search
    across emails, Drive files, and the knowledge base.
    """
    query = request.query
    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
    try:
        email_results = google_api_service.search_emails_by_query(query, max_results=5)
        drive_results = google_api_service.search_drive_files(query, max_results=5)

        detailed_emails = []
        for msg in email_results:
            details = google_api_service.get_email_details(msg["id"])
            if details:
                parsed = parse_email_content(details)
                detailed_emails.append(
                    {
                        "id": msg["id"],
                        "threadId": details.get("threadId"),
                        "from": parsed.get("from"),
                        "subject": parsed.get("subject"),
                    }
                )

        retriever = knowledge_base.get_retriever()
        kb_docs = retriever.get_relevant_documents(query)
        kb_results = [{"fact": doc.page_content} for doc in kb_docs]

        return {
            "emails": detailed_emails,
            "drive_files": drive_results,
            "knowledge_base": kb_results,
        }
    except Exception as e:
        logger.error(f"Error in /api/search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to perform search.")


@app.post("/api/chat")
async def chat_with_agent(message_body: Dict[str, str] = Body(...)):
    global app_state
    user_message = message_body.get("message")
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    try:
        user_chat_entry = {"role": "user", "content": user_message}
        app_state["chat_history"].append(user_chat_entry)
        await manager.broadcast({"type": "chat_update", "payload": user_chat_entry})

        agent_response = await chat_agent_service.invoke(
            user_message, app_state["chat_history"]
        )

        agent_chat_entry = {"role": "agent", "content": agent_response}
        app_state["chat_history"].append(agent_chat_entry)
        await manager.broadcast({"type": "chat_update", "payload": agent_chat_entry})
        return {"status": "success"}
    except Exception as e:
        await log_and_broadcast(f"Error in chat endpoint: {e}", "error")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chat/clear")
async def clear_chat_history():
    """Endpoint to clear the entire chat history."""
    global app_state
    app_state["chat_history"] = []
    await manager.broadcast({"type": "chat_history_cleared"})
    await log_and_broadcast("Chat history has been cleared by the user.")
    return {"status": "success", "message": "Chat history cleared."}


# Action Queue Endpoints
@app.post("/api/actions/send-draft/{message_id}")
async def send_draft_action(message_id: str):
    draft = draft_service.get_draft(message_id)
    if not draft or not draft.get("gmailDraftId"):
        raise HTTPException(status_code=404, detail="Draft not found.")
    try:
        google_api_service.send_draft(draft["gmailDraftId"])
        draft_service.remove_draft(message_id)
        app_state["drafts_queue"] = draft_service.get_pending_drafts()
        await manager.broadcast(
            {"type": "drafts_update", "payload": app_state["drafts_queue"]}
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(
            f"Failed to send draft for message {message_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to send draft. The network connection may have been interrupted.",
        )


@app.delete("/api/actions/discard-draft/{message_id}")
async def discard_draft_action(message_id: str):
    draft = draft_service.get_draft(message_id)
    try:
        if draft and draft.get("gmailDraftId"):
            google_api_service.trash_draft(draft["gmailDraftId"])
        draft_service.remove_draft(message_id)
        app_state["drafts_queue"] = draft_service.get_pending_drafts()
        await manager.broadcast(
            {"type": "drafts_update", "payload": app_state["drafts_queue"]}
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(
            f"Failed to discard draft for message {message_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to discard draft. The network connection may have been interrupted.",
        )


@app.post("/api/actions/approve-learning/{message_id}")
async def approve_learning_action(message_id: str):
    proposal = learning_service.get_proposal(message_id)
    if not proposal or not proposal.exists:
        raise HTTPException(status_code=404, detail="Learning proposal not found")

    fact = proposal.to_dict().get("fact")
    if not fact:
        raise HTTPException(status_code=400, detail="Proposal is missing a fact.")

    try:
        new_fact = knowledge_base.add_fact(fact)
        if not new_fact:
            raise HTTPException(
                status_code=500, detail="Failed to save fact to knowledge base."
            )

        await manager.broadcast({"type": "new_fact_added", "payload": new_fact})

        google_api_service.modify_email_labels(
            message_id, [config.GMAIL_APPROVE_LEARNING_LABEL], []
        )
        learning_service.mark_proposal_learned(message_id)
        app_state["learning_queue"] = [
            p for p in app_state["learning_queue"] if p.get("id") != message_id
        ]
        await manager.broadcast(
            {"type": "remove_learning", "payload": {"id": message_id}}
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(
            f"Error during learning approval for {message_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


@app.post("/api/actions/reject-learning/{message_id}")
async def reject_learning_action(message_id: str):
    try:
        learning_service.reject_proposal(message_id)
        google_api_service.modify_email_labels(
            message_id, [], [config.GMAIL_LEARNING_PROPOSAL_LABEL]
        )
        app_state["learning_queue"] = [
            p for p in app_state["learning_queue"] if p.get("id") != message_id
        ]
        await manager.broadcast(
            {"type": "learning_update", "payload": app_state["learning_queue"]}
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error rejecting learning for {message_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


@app.post("/api/actions/keep-priority/{message_id}")
async def keep_priority_action(message_id: str):
    try:
        priority_service.mark_as_seen(message_id)

        for item in app_state["priority_queue"]:
            if item["id"] == message_id:
                item["seen"] = True
                break

        await log_and_broadcast(
            f"User acknowledged and kept high-priority item {message_id} for later review.",
            "info",
        )
        await manager.broadcast(
            {
                "type": "update_priority_item",
                "payload": {"id": message_id, "seen": True},
            }
        )
        return {"status": "success"}
    except Exception as e:
        await log_and_broadcast(
            f"Error keeping priority item {message_id}: {e}", "error"
        )
        return {"status": "error", "message": str(e)}


@app.post("/api/actions/dismiss-priority/{message_id}")
async def dismiss_priority_action(message_id: str):
    try:
        google_api_service.modify_email_labels(
            message_id, [], [config.GMAIL_HIGH_PRIORITY_LABEL]
        )
        priority_service.remove_item(message_id)
        app_state["priority_queue"] = priority_service.get_pending_items()
        await manager.broadcast(
            {"type": "priority_update", "payload": app_state["priority_queue"]}
        )
        await log_and_broadcast(f"High-priority item {message_id} dismissed.")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error dismissing priority item {message_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


@app.post("/api/actions/star-email/{message_id}")
async def star_email_action(message_id: str):
    """Adds the 'STARRED' label to an email and refreshes relevant queues."""
    try:
        google_api_service.modify_email_labels(message_id, ["STARRED"], [])

        for item in app_state["priority_queue"]:
            if item["id"] == message_id:
                item["is_starred"] = True
                break
        await manager.broadcast(
            {"type": "priority_update", "payload": app_state["priority_queue"]}
        )

        app_state["starred_queue"] = google_api_service.search_starred_emails()
        await manager.broadcast(
            {"type": "starred_update", "payload": app_state["starred_queue"]}
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error starring email {message_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/unstar-email/{message_id}")
async def unstar_email_action(message_id: str):
    """Removes the 'STARRED' label from an email and refreshes the starred list."""
    try:
        google_api_service.modify_email_labels(message_id, [], ["STARRED"])
        app_state["starred_queue"] = [
            item for item in app_state["starred_queue"] if item["id"] != message_id
        ]
        manager.broadcast(
            {"type": "starred_update", "payload": app_state["starred_queue"]}
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error unstarring email {message_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/delete-email/{message_id}")
async def delete_email_action(message_id: str):
    """Moves a specific email to the trash."""
    try:
        google_api_service.trash_email(message_id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error deleting email {message_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/bulk-unstar")
async def bulk_unstar_action(message_ids: List[str] = Body(...)):
    """Removes the 'STARRED' label from multiple emails."""
    try:
        for message_id in message_ids:
            google_api_service.modify_email_labels(message_id, [], ["STARRED"])

        app_state["starred_queue"] = google_api_service.search_starred_emails()
        await manager.broadcast(
            {"type": "starred_update", "payload": app_state["starred_queue"]}
        )
        return {"status": "success", "message": f"Unstarred {len(message_ids)} emails."}
    except Exception as e:
        logger.error(f"Error during bulk unstar: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An error occurred during bulk unstar."
        )


@app.get("/api/actions/get-email-content/{message_id}")
async def get_email_content(message_id: str):
    """Retrieves the full, parsed content of a specific email."""
    try:
        email_details = google_api_service.get_email_details(message_id)
        if not email_details:
            raise HTTPException(status_code=404, detail="Email not found.")

        parsed_content = parse_email_content(email_details)
        return {"content": parsed_content.get("body", "Could not parse email body.")}
    except Exception as e:
        logger.error(
            f"Error fetching email content for {message_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to fetch email content.")


@app.get("/api/settings")
async def get_settings():
    """Endpoint to retrieve the current effective settings."""
    if not settings_service:
        return {"error": "Settings service not initialized"}, 500
    return settings_service.get_settings()


@app.post("/api/settings")
async def save_settings(payload: Dict[str, Any] = Body(...)):
    """Endpoint to save updated settings."""

    try:
        result = settings_service.save_settings(payload)
        initialize_dynamic_services()
        await log_and_broadcast("Settings updated and services re-initialized.", "log")
        return result
    except Exception as e:
        logger.error(f"Error saving settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings/reset")
async def reset_settings():
    """Endpoint to reset settings to their default values."""
    if not settings_service:
        raise HTTPException(status_code=500, detail="Settings service not initialized")
    try:
        default_settings = settings_service.reset_to_defaults()
        initialize_dynamic_services()
        await log_and_broadcast("Settings reset and services re-initialized.", "log")
        return default_settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/knowledge-base/all")
async def clear_all_knowledge_base_facts():
    """Endpoint to clear the entire knowledge base."""
    if not settings_service:
        return {"error": "Settings service not initialized"}, 500
    try:
        result = settings_service.clear_knowledge_base()
        return result
    except Exception as e:
        return {"error": str(e)}, 500


@app.get("/api/knowledge-base")
async def get_knowledge_base_facts():
    """Endpoint to retrieve all facts from the knowledge base."""
    if not knowledge_base:
        return {"error": "Knowledge base not initialized"}, 500
    facts = knowledge_base.get_all_facts()
    return facts


@app.post("/api/knowledge-base")
async def add_knowledge_base_fact(payload: Dict[str, str] = Body(...)):
    """Endpoint to add a new fact to the knowledge base."""
    fact = payload.get("fact")
    if not fact:
        return {"error": "Fact content cannot be empty"}, 400
    if not knowledge_base:
        return {"error": "Knowledge base not initialized"}, 500

    try:
        new_fact = knowledge_base.add_fact(fact)
        return new_fact
    except Exception as e:
        return {"error": str(e)}, 500


@app.delete("/api/knowledge-base/{fact_id}")
async def delete_knowledge_base_fact(fact_id: str):
    """Endpoint to delete a fact from the knowledge base."""
    if not knowledge_base:
        return {"error": "Knowledge base not initialized"}, 500

    try:
        result = knowledge_base.delete_fact(fact_id)
        if result.get("status") == "not_found":
            return {"error": "Fact not found"}, 404
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}, 500


# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "initial_state", "payload": app_state})
        while True:
            data = await websocket.receive_json()
            if data["type"] == "get_smart_replies":
                email_id = data["payload"]["emailId"]
                # Use a background task to avoid blocking the WebSocket
                asyncio.create_task(
                    chat_agent_service.generate_smart_replies(websocket, email_id)
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# --- Uvicorn Server Entry Point ---
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Uvicorn server for Gmail Assistant API...")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
