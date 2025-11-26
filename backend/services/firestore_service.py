"""
Initializes and provides a singleton instance of the Google Firestore client.
This service is used by other services (StateManager, MemoryService) to interact
with the database without needing to handle the connection details themselves.
"""

from google.cloud import firestore
from utils.logger import get_logger
import config

logger = get_logger(__name__)

try:
    # The Firestore client automatically uses the credentials from the
    # GOOGLE_APPLICATION_CREDENTIALS environment variable, but it needs to know
    # which project to connect to. We provide it explicitly from our config.
    db = firestore.Client(project=config.GOOGLE_CLOUD_PROJECT)
    logger.info(
        f"Firestore client initialized successfully for project '{config.GOOGLE_CLOUD_PROJECT}'."
    )
except Exception as e:
    logger.error(f"FATAL: Could not initialize Firestore client. Error: {e}")
    logger.error(
        "Please ensure you have authenticated with Google Cloud CLI ('gcloud auth application-default login') and have set the GOOGLE_CLOUD_PROJECT in your .env file."
    )
    db = None


def get_db():
    """Returns the initialized Firestore database client instance."""
    if db is None:
        raise ConnectionError(
            "Firestore client is not available. Check initialization logs for errors."
        )
    return db
