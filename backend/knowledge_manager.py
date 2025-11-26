"""
Checks for user approval on learning proposals via Gmail labels
and updates the agent's knowledge base accordingly.
"""

import config
from utils.logger import get_logger
from services.google_api_service import GoogleApiService
from services.learning_service import LearningService
from services.knowledge_base import KnowledgeBase

logger = get_logger(__name__)


def process_learning_approvals(
    google_api_service: GoogleApiService,
    learning_service: LearningService,
    knowledge_base: KnowledgeBase,
):
    """
    Finds emails with the 'AI-Approve-Learning' label, confirms they have a
    pending proposal, adds the fact to the knowledge base, and cleans up labels.
    """
    logger.info("[Knowledge Manager] Checking for learning approvals...")

    try:
        # 1. Find all messages with the approval label
        approval_label_id = google_api_service.get_or_create_label_id(
            config.GMAIL_APPROVE_LEARNING_LABEL
        )
        proposal_label_id = google_api_service.get_or_create_label_id(
            config.GMAIL_LEARNING_PROPOSAL_LABEL
        )

        approved_messages = (
            google_api_service.gmail_service.users()
            .messages()
            .list(userId="me", labelIds=[approval_label_id])
            .execute()
            .get("messages", [])
        )

        if not approved_messages:
            logger.info("[Knowledge Manager] No new approvals found.")
            return

        for msg_summary in approved_messages:
            message_id = msg_summary["id"]
            logger.info(f"[Knowledge Manager] Found approved message: {message_id}")

            # 2. Get the proposal from Firestore to find the fact
            proposal = learning_service.get_proposal(message_id)
            if not proposal or not proposal.exists:
                logger.warning(
                    f"[Knowledge Manager] Found approval label on message {message_id}, but no matching proposal in Firestore. Cleaning up label."
                )
                google_api_service.modify_email_labels(
                    message_id, [], [approval_label_id]
                )
                continue

            proposal_data = proposal.to_dict()

            if proposal_data.get("status") == "learned":
                logger.info(
                    f"[Knowledge Manager] Proposal for {message_id} was already learned. Cleaning up orphaned labels."
                )
                # Attempt to clean up labels again in case the previous attempt failed
                google_api_service.modify_email_labels(
                    message_id, [], [approval_label_id, proposal_label_id]
                )
                continue

            fact_to_learn = proposal.to_dict().get("fact")
            if not fact_to_learn:
                logger.warning(
                    f"[Knowledge Manager] Proposal for {message_id} is missing the fact. Discarding."
                )
                learning_service.mark_proposal_learned(message_id)
                google_api_service.modify_email_labels(
                    message_id, [], [approval_label_id, proposal_label_id]
                )
                continue

            # 3. Add the fact to the knowledge base
            logger.info(
                f"[Knowledge Manager] Learning new fact from message {message_id}: '{fact_to_learn}'"
            )
            knowledge_base.add_fact(fact_to_learn)

            # 4. Mark proposal as learned in Firestore
            learning_service.mark_proposal_learned(message_id)

            # 5. Clean up by removing both labels from the email
            logger.info(
                f"[Knowledge Manager] Cleaning up labels for message {message_id}."
            )
            google_api_service.modify_email_labels(
                message_id, [], [approval_label_id, proposal_label_id]
            )

    except Exception as e:
        logger.error(
            f"[Knowledge Manager] An error occurred while processing approvals: {e}",
            exc_info=True,
        )
