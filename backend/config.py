"""
Centralized configuration for the email automation application.
All settings, paths, model names, and labels are defined here to allow for
easy modification without changing the core application logic.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

# --- Logging Configuration ---
LOG_LEVEL = logging.INFO

# --- API Key Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("FATAL: GOOGLE_API_KEY not found in .env file.")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("FATAL: TAVILY_API_KEY not found in .env file.")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if not PINECONE_API_KEY:
    raise ValueError("FATAL: PINECONE_API_KEY not found in .env file.")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("FATAL: GROQ_API_KEY not found in .env file.")


# --- Google Cloud Project Configuration ---
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
if not GOOGLE_CLOUD_PROJECT:
    raise ValueError(
        "FATAL: GOOGLE_CLOUD_PROJECT not found in .env file. Please set it."
    )


# --- LLM Configuration ---
LLM_MODEL_NAME = "gemini-2.5-flash"
VISION_MODEL_NAME = "meta-llama/llama-4-maverick-17b-128e-instruct"
LLM_TEMPERATURE = 0.2


# --- Knowledge Base and RAG Configuration ---
KNOWLEDGE_BASE_DIR = "knowledge_base/"
EMBEDDING_MODEL_NAME = "models/embedding-001"
PINECONE_INDEX_NAME = "email-agent-knowledge-base"


# --- Google Service Configuration ---
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
]
GOOGLE_CREDENTIALS_PATH = "credentials.json"
DRIVE_FOLDER_NAME = "Email Agent Attachments"


# --- Gmail Label Configuration ---
GMAIL_PROCESSED_LABEL = "AI-Processed"
GMAIL_NEEDS_REVIEW_LABEL = "AI-Needs-Review"
GMAIL_HIGH_PRIORITY_LABEL = "AI-High-Priority"
GMAIL_INVOICE_LABEL = "AI-Invoice"
GMAIL_JOB_RELATED_LABEL = "AI-Job-Related"
GMAIL_NO_ACTION_LABEL = "AI-No-Action-Required"
GMAIL_LEARNING_PROPOSAL_LABEL = "AI-Learning-Proposal"
GMAIL_APPROVE_LEARNING_LABEL = "AI-Approve-Learning"


# --- Main Application Loop Configuration ---

START_ON_LAUNCH = False
CHECK_INTERVAL_SECONDS = 30
DEFAULT_EMAIL_SIGNATURE = "Sincerely,\nM Bharadwaj"
CONVERSATION_MEMORY_RETENTION_DAYS = 90
ERROR_RETRY_SECONDS = 60
MAX_REVISIONS = 2
