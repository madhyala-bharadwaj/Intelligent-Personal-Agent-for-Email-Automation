"""
Manages the persistent state of high-priority emails in the Firestore database.
"""

from utils.logger import get_logger
from .firestore_service import get_db

logger = get_logger(__name__)


class PriorityService:
    """Handles creating, retrieving, and deleting high-priority item records in Firestore."""

    def __init__(self):
        """Initializes the service with a connection to the Firestore database."""
        self.db = get_db()
        self.collection = self.db.collection("high_priority_queue")

    def create_item(self, item_data: dict):
        """Saves a new high-priority item to Firestore, using the message_id as the document ID."""
        try:
            message_id = item_data["id"]
            item_data["seen"] = False
            self.collection.document(message_id).set(item_data)
            logger.info(
                f"Successfully saved high-priority item {message_id} to Firestore."
            )
        except Exception as e:
            logger.error(
                f"Could not save high-priority item {item_data.get('id')} to Firestore: {e}"
            )

    def get_pending_items(self) -> list:
        """Retrieves all pending high-priority items from Firestore."""
        try:
            items = self.collection.stream()
            return [item.to_dict() for item in items]
        except Exception as e:
            logger.error(
                f"Could not retrieve pending high-priority items from Firestore: {e}"
            )
            return []

    def mark_as_seen(self, message_id: str):
        """Updates a high-priority item to mark it as seen."""
        try:
            self.collection.document(message_id).update({"seen": True})
            logger.info(f"Marked high-priority item {message_id} as seen.")
        except Exception as e:
            logger.error(f"Could not mark item {message_id} as seen: {e}")

    def remove_item(self, message_id: str):
        """Deletes a high-priority item's record from Firestore."""
        try:
            self.collection.document(message_id).delete()
            logger.info(
                f"Successfully removed high-priority item {message_id} from Firestore."
            )
        except Exception as e:
            logger.error(
                f"Could not remove high-priority item {message_id} from Firestore: {e}"
            )
