"""
Manages loading and saving user-configurable settings.
It loads default values from config.py and allows them to be
overridden by user preferences stored in Firestore.
"""

from google.cloud import firestore
from utils.logger import get_logger
from services.knowledge_base import KnowledgeBase
import config

logger = get_logger(__name__)


class SettingsService:
    def __init__(self, knowledge_base: KnowledgeBase):
        """Initializes the service and connects to Firestore."""
        self.db = firestore.Client()
        self.knowledge_base = knowledge_base
        self.collection_ref = self.db.collection("settings")
        self.document_id = "user_preferences"
        self.default_settings = self._load_defaults_from_config()

    def _load_defaults_from_config(self):
        """Loads the relevant settings from the main config.py file."""
        return {
            "llm_model_name": config.LLM_MODEL_NAME,
            "llm_temperature": config.LLM_TEMPERATURE,
            "max_revisions": config.MAX_REVISIONS,
            "start_on_launch": config.START_ON_LAUNCH,
            "check_interval_seconds": config.CHECK_INTERVAL_SECONDS,
            "notification_triggers": {
                "new_draft": True,
                "priority_item": True,
                "new_learning": False,
            },
            "conversation_memory_retention_days": config.CONVERSATION_MEMORY_RETENTION_DAYS,
            "default_email_signature": config.DEFAULT_EMAIL_SIGNATURE,
            "drive_folder_name": config.DRIVE_FOLDER_NAME,
        }

    def get_settings(self):
        """
        Retrieves settings by loading defaults and merging any user-saved
        preferences from Firestore on top.
        """
        try:
            logger.info("Fetching settings...")
            user_settings_doc = self.collection_ref.document(self.document_id).get()

            effective_settings = self.default_settings.copy()

            if user_settings_doc.exists:
                logger.info(
                    "Found user preferences in Firestore. Merging with defaults."
                )
                user_settings = user_settings_doc.to_dict()

                if "notification_triggers" in user_settings:
                    effective_settings["notification_triggers"].update(
                        user_settings["notification_triggers"]
                    )
                    del user_settings["notification_triggers"]

                effective_settings.update(user_settings)
            else:
                logger.info("No user preferences found. Using default settings.")

            return effective_settings
        except Exception as e:
            logger.error(f"Failed to get settings: {e}", exc_info=True)
            return self.default_settings

    def save_settings(self, new_settings: dict):
        """
        Saves a dictionary of settings to the user's preferences document in Firestore.
        """
        try:
            settings_to_save = {
                key: new_settings[key]
                for key in self.default_settings
                if key in new_settings
            }
            logger.info(f"Saving new settings to Firestore: {settings_to_save}")
            self.collection_ref.document(self.document_id).set(
                settings_to_save, merge=True
            )
            logger.info("Successfully saved settings.")
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Failed to save settings: {e}", exc_info=True)
            raise

    def reset_to_defaults(self):
        """
        Resets user settings by deleting their preferences document from Firestore.
        The application will fall back to the hardcoded defaults from config.py.
        """
        try:
            logger.warning("Resetting user settings to default.")
            doc_ref = self.collection_ref.document(self.document_id)
            if doc_ref.get().exists:
                doc_ref.delete()
                logger.info("Successfully deleted user preferences document.")
            else:
                logger.info("No user preferences to delete. Already using defaults.")
            return self.default_settings
        except Exception as e:
            logger.error(f"Failed to reset settings: {e}", exc_info=True)
            raise

    def clear_knowledge_base(self):
        """
        Triggers the knowledge base service to clear all facts.
        """
        return self.knowledge_base.clear_all_facts()
