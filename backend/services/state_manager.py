"""
Manages persistent state for a single user using Google Firestore.
This service tracks processed email IDs to prevent reprocessing. It loads all
IDs into a local set on startup for efficient in-memory checks.
"""

from utils.logger import get_logger
from .firestore_service import get_db

logger = get_logger(__name__)


class StateManager:
    """Handles loading and saving of processed email IDs to Firestore."""

    def __init__(self):
        """Initializes the service with a connection to the Firestore database."""
        self.db = get_db()
        self.collection = self.db.collection("processed_emails")
        self.processed_ids = self._load_processed_ids()
        logger.info(
            f"Loaded {len(self.processed_ids)} processed email IDs into memory."
        )

    def _load_processed_ids(self) -> set:
        """Loads all processed IDs from Firestore into a local set for fast lookups."""
        try:
            docs = self.collection.stream()
            return {doc.id for doc in docs}
        except Exception as e:
            logger.error(
                f"Could not load processed IDs from Firestore: {e}", exc_info=True
            )
            return set()

    def add_processed_id(self, message_id: str):
        """Adds a message ID to the processed set in memory and saves it to Firestore."""
        if message_id not in self.processed_ids:
            self.processed_ids.add(message_id)
            try:
                self.collection.document(message_id).set({})
            except Exception as e:
                logger.error(
                    f"Could not save processed ID {message_id} to Firestore: {e}"
                )

    def is_processed(self, message_id: str) -> bool:
        """
        Checks if a message ID has already been processed by checking the local set.
        This is much faster than querying Firestore for every check.
        """
        return message_id in self.processed_ids
