"""
REFACTORED: Manages persistent conversational memory using Google Firestore.
This service replaces the local JSON file, providing a robust, scalable, and
portable way to store and retrieve conversation history for each email thread.
"""

from google.cloud import firestore
from utils.logger import get_logger
from .firestore_service import get_db

logger = get_logger(__name__)


class MemoryService:
    """Handles loading and saving of conversation history to Firestore."""

    def __init__(self):
        """Initializes the service with a connection to the Firestore database."""
        self.db = get_db()
        self.collection = self.db.collection("conversations")

    def get_history(self, thread_id: str) -> str:
        """Retrieves the formatted conversation history for a given thread ID from Firestore."""
        try:
            doc_ref = self.collection.document(thread_id)
            doc = doc_ref.get()
            if doc.exists:
                history_list = doc.to_dict().get("history", [])
                logger.info(
                    f"Loaded {len(history_list)} messages from history for thread {thread_id}."
                )
                return "\n".join(history_list)
            else:
                logger.info(f"No history found for thread {thread_id}. Starting fresh.")
                return ""
        except Exception as e:
            logger.error(
                f"Error loading history for thread {thread_id} from Firestore: {e}"
            )
            return ""  # Return empty history on error to prevent breaking the flow

    def add_to_history(self, thread_id: str, user_query: str, agent_response: str):
        """Adds a new turn to the conversation history for a thread and saves it to Firestore."""
        try:
            doc_ref = self.collection.document(thread_id)
            new_entries = [f"User said: {user_query}", f"You replied: {agent_response}"]

            # Use a transaction to safely update the history array
            @firestore.transactional
            def update_in_transaction(transaction, doc_ref, entries):
                doc = doc_ref.get(transaction=transaction)
                if doc.exists:
                    current_history = doc.to_dict().get("history", [])
                    new_history = current_history + entries
                    transaction.update(doc_ref, {"history": new_history})
                else:
                    transaction.set(doc_ref, {"history": entries})

            transaction = self.db.transaction()
            update_in_transaction(transaction, doc_ref, new_entries)
            logger.info(f"Successfully added to history for thread {thread_id}.")
        except Exception as e:
            logger.error(
                f"Could not save history to Firestore for thread {thread_id}. Error: {e}"
            )
