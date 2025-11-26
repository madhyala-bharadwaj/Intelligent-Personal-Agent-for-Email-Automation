"""
REVISED SERVICE: Manages the state of learning proposals in Firestore.
This allows the agent to track facts it has proposed to learn, keyed by message ID.
"""

from google.cloud.firestore_v1.base_query import FieldFilter
from utils.logger import get_logger
from .firestore_service import get_db

logger = get_logger(__name__)


class LearningService:
    """Handles the creation and retrieval of learning proposals."""

    def __init__(self):
        """Initializes the service with a connection to the Firestore database."""
        self.db = get_db()
        self.collection = self.db.collection("learning_proposals")

    def create_proposal(
        self, message_id: str, fact: str, from_email: str, timestamp: float
    ):
        """Creates a new learning proposal document in Firestore, keyed by message ID."""
        try:
            doc_ref = self.collection.document(message_id)
            doc_ref.set(
                {
                    "id": message_id,
                    "fact": fact,
                    "fromEmail": from_email,
                    "proposed_at": timestamp,
                    "status": "proposed",
                }
            )
            logger.info(f"Created learning proposal for message {message_id}.")
        except Exception as e:
            logger.error(
                f"Could not create learning proposal for message {message_id}: {e}"
            )

    def get_proposal(self, message_id: str):
        """Retrieves a specific proposal by its message ID."""
        try:
            doc_ref = self.collection.document(message_id)
            return doc_ref.get()
        except Exception as e:
            logger.error(f"Could not retrieve proposal for message {message_id}: {e}")
            return None

    def get_pending_proposals(self) -> list:
        """Retrieves all proposals with 'proposed' status and ensures data is JSON serializable."""
        try:
            proposals_stream = self.collection.where(
                filter=FieldFilter("status", "==", "proposed")
            ).stream()
            proposals_list = []
            for p in proposals_stream:
                proposal_dict = p.to_dict()
                if "proposed_at" in proposal_dict and hasattr(
                    proposal_dict["proposed_at"], "isoformat"
                ):
                    proposal_dict["proposed_at"] = proposal_dict[
                        "proposed_at"
                    ].isoformat()
                proposals_list.append(proposal_dict)
            return proposals_list
        except Exception as e:
            logger.error(f"Could not retrieve pending proposals: {e}")
            return []

    def mark_proposal_learned(self, message_id: str):
        """Marks a proposal as learned after user approval."""
        try:
            doc_ref = self.collection.document(message_id)
            doc_ref.update({"status": "learned"})
            logger.info(
                f"Marked learning proposal for message {message_id} as learned."
            )
        except Exception as e:
            logger.error(
                f"Could not update proposal status for message {message_id}: {e}"
            )

    def reject_proposal(self, message_id: str):
        """Marks a proposal as rejected."""
        try:
            doc_ref = self.collection.document(message_id)
            doc_ref.update({"status": "rejected"})
            logger.info(f"Marked proposal for {message_id} as rejected.")
        except Exception as e:
            logger.error(f"Could not reject proposal for {message_id}: {e}")
