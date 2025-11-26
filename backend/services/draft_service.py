"""
Manages the persistent state of draft emails in the Firestore database.
This ensures that pending drafts are not lost if the server restarts.
"""

from google.cloud import firestore
from utils.logger import get_logger
from .firestore_service import get_db

logger = get_logger(__name__)


class DraftService:
    """Handles creating, retrieving, and deleting draft records in Firestore."""

    def __init__(self):
        """Initializes the service with a connection to the Firestore database."""
        self.db = get_db()
        self.collection = self.db.collection("drafts_queue")

    def create_draft(self, draft_data: dict):
        """Saves a new draft's details to Firestore, using the message_id as the document ID."""
        try:
            # --- Data validation ---
            if "id" not in draft_data:
                logger.error("Draft data is missing required 'id' field.")
                return

            message_id = draft_data["id"]

            # --- Server-side timestamp for reliable sorting ---
            draft_data["timestamp"] = firestore.SERVER_TIMESTAMP

            self.collection.document(message_id).set(draft_data)
            logger.info(f"Successfully saved draft {message_id} to Firestore.")
        except Exception as e:
            logger.error(
                f"Could not save draft {draft_data.get('id')} to Firestore: {e}"
            )

    def get_draft(self, message_id: str) -> dict:
        """Retrieves a single draft by its message ID."""
        try:
            doc = self.collection.document(message_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Could not retrieve draft {message_id} from Firestore: {e}")
            return None

    def get_pending_drafts(self) -> list:
        """Retrieves all pending drafts from Firestore, sorted by most recent."""
        try:
            # --- Sort drafts by timestamp in descending order ---
            drafts_query = self.collection.order_by(
                "timestamp", direction=firestore.Query.DESCENDING
            )
            drafts = drafts_query.stream()

            drafts_list = []
            for draft in drafts:
                draft_dict = draft.to_dict()
                # Ensure timestamp is JSON serializable for the API
                if "timestamp" in draft_dict and hasattr(
                    draft_dict["timestamp"], "isoformat"
                ):
                    draft_dict["timestamp"] = draft_dict["timestamp"].isoformat()
                drafts_list.append(draft_dict)

            return drafts_list
        except Exception as e:
            logger.error(f"Could not retrieve pending drafts from Firestore: {e}")
            return []

    def remove_draft(self, message_id: str):
        """Deletes a draft's record from Firestore after it has been actioned."""
        try:
            self.collection.document(message_id).delete()
            logger.info(f"Successfully removed draft {message_id} from Firestore.")
        except Exception as e:
            logger.error(f"Could not remove draft {message_id} from Firestore: {e}")
