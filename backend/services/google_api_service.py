"""
Encapsulates all interactions with Google Workspace APIs (Gmail, Calendar, Drive).
Handles authentication and provides methods for API calls.
"""

import os
import base64
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
import io
from functools import wraps
import time

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaIoBaseUpload
from google.auth.exceptions import RefreshError
from httplib2 import ServerNotFoundError

import config
from utils.logger import get_logger
from utils.email_parser import parse_email_content

logger = get_logger(__name__)


def retry_on_connection_error(max_retries=3, delay=2):
    """A decorator to retry a function on connection-related errors."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except (ConnectionAbortedError, ServerNotFoundError) as e:
                    attempts += 1
                    logger.warning(
                        f"Connection error in {func.__name__} (Attempt {attempts}/{max_retries}): {e}. Retrying in {delay}s..."
                    )
                    time.sleep(delay * attempts)
            logger.error(
                f"Failed to execute {func.__name__} after {max_retries} attempts."
            )
            raise ConnectionAbortedError(f"Failed after {max_retries} retries.")

        return wrapper

    return decorator


class GoogleApiService:
    """A service class for all Google Workspace API operations."""

    def __init__(self):
        """Initializes the service and authenticates, creating API clients."""
        self.creds = self._get_credentials()
        self.gmail_service = self._build_service("gmail", "v1")
        self.calendar_service = self._build_service("calendar", "v3")
        self.drive_service = self._build_service("drive", "v3")
        self._label_cache: Dict[str, str] = {}

    def _get_credentials(self):
        """
        Handles user authentication for Google APIs.
        Uses stored tokens or initiates a new OAuth2 flow.
        """
        creds = None
        token_path = "token.json"

        # --- Handle corrupted token file ---
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(
                    token_path, config.GOOGLE_SCOPES
                )
            except Exception as e:
                logger.warning(
                    f"Could not load token from {token_path}. File may be corrupted. Error: {e}"
                )
                os.remove(token_path)  # Delete corrupted token
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired credentials...")
                    creds.refresh(Request())
                except RefreshError as e:
                    logger.error(
                        f"Failed to refresh token. User may have revoked access. Error: {e}"
                    )
                    os.remove(token_path)  # Delete invalid token
                    creds = None  # Force re-authentication

            # If there are no valid credentials, start the OAuth flow
            if not creds:
                logger.info("No valid credentials found. Starting new OAuth2 flow.")
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GOOGLE_CREDENTIALS_PATH, config.GOOGLE_SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the new or refreshed credentials for the next run
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        return creds

    def _build_service(self, service_name: str, version: str) -> Optional[Resource]:
        """A generic helper to build a Google API service client."""
        try:
            return build(service_name, version, credentials=self.creds)
        except Exception as e:
            logger.error(f"Failed to build Google API service '{service_name}': {e}")
            return None

    # --- Gmail Methods ---
    def get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        if not self.gmail_service:
            return None
        try:
            return (
                self.gmail_service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        except Exception as e:
            logger.error(f"Error getting email details for msg {message_id}: {e}")
            return None

    @retry_on_connection_error()
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
    ) -> Optional[Dict]:
        """Sends an email directly."""
        if not self.gmail_service:
            return None

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
            message["References"] = in_reply_to

        create_message = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}
        if thread_id:
            create_message["threadId"] = thread_id

        sent_message = (
            self.gmail_service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )
        logger.info(f"Email sent successfully with ID: {sent_message['id']}")
        return sent_message

    @retry_on_connection_error()
    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
    ) -> Optional[str]:
        """Creates a draft email and returns its ID."""
        if not self.gmail_service:
            return None

        message = MIMEText(body, "html")
        message["to"] = to
        message["subject"] = subject
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
            message["References"] = in_reply_to

        draft_body = {
            "message": {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}
        }
        if thread_id:
            draft_body["message"]["threadId"] = thread_id

        draft = (
            self.gmail_service.users()
            .drafts()
            .create(userId="me", body=draft_body)
            .execute()
        )
        logger.info(f"Draft created successfully with ID: {draft['id']}")
        return draft.get("id")

    @retry_on_connection_error()
    def send_draft(self, draft_id: str) -> Optional[Dict]:
        """Sends an existing draft email."""
        if not self.gmail_service:
            return None
        sent_message = (
            self.gmail_service.users()
            .drafts()
            .send(userId="me", body={"id": draft_id})
            .execute()
        )
        logger.info(
            f"Draft {draft_id} sent successfully. New message ID: {sent_message.get('id')}"
        )
        return sent_message

    @retry_on_connection_error()
    def trash_draft(self, draft_id: str) -> None:
        """Deletes a draft email by moving it to the trash."""
        if not self.gmail_service:
            return
        (self.gmail_service.users().drafts().delete(userId="me", id=draft_id).execute())
        logger.info(f"Draft {draft_id} trashed successfully.")

    @retry_on_connection_error()
    def trash_email(self, message_id: str) -> None:
        """Moves a specific email to the trash."""
        if not self.gmail_service:
            return
        (
            self.gmail_service.users()
            .messages()
            .trash(userId="me", id=message_id)
            .execute()
        )
        logger.info(f"Email {message_id} moved to trash.")

    def toggle_star_email(self, message_id: str) -> str:
        """Adds or removes the 'STARRED' label from an email."""
        if not self.gmail_service:
            return "Gmail service not available."
        try:
            message = self.get_email_details(message_id)
            if not message:
                return f"Could not find email with ID {message_id}."

            label_ids = message.get("labelIds", [])
            if "STARRED" in label_ids:
                self.modify_email_labels(message_id, [], ["STARRED"])
                return f"Removed star from email {message_id}."
            else:
                self.modify_email_labels(message_id, ["STARRED"], [])
                return f"Added star to email {message_id}."
        except Exception as e:
            logger.error(
                f"Error toggling star for email {message_id}: {e}", exc_info=True
            )
            return "An error occurred while changing the star status."

    def search_emails_by_query(
        self, query: str, max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Searches for emails using a specific query string."""
        if not self.gmail_service:
            return []
        try:
            response = (
                self.gmail_service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
            return response.get("messages", [])
        except Exception as e:
            logger.error(
                f"Error searching emails with query '{query}': {e}", exc_info=True
            )
            return []

    def get_or_create_label_id(self, label_name: str) -> Optional[str]:
        """Gets a label ID from cache or creates it if it doesn't exist."""
        if not self.gmail_service:
            return None
        if label_name in self._label_cache:
            return self._label_cache[label_name]

        try:
            results = self.gmail_service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])
            for label in labels:
                self._label_cache[label["name"]] = label["id"]

            if label_name in self._label_cache:
                return self._label_cache[label_name]

            logger.info(f"Label '{label_name}' not found, creating it.")
            label_body = {
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            created_label = (
                self.gmail_service.users()
                .labels()
                .create(userId="me", body=label_body)
                .execute()
            )
            self._label_cache[label_name] = created_label["id"]
            return created_label["id"]
        except Exception as e:
            logger.error(f"Error getting/creating label '{label_name}': {e}")
            return None

    def search_unread_emails(self) -> List[Dict[str, Any]]:
        if not self.gmail_service:
            return []
        processed_label_name = config.GMAIL_PROCESSED_LABEL
        query = f"is:unread in:inbox -label:{processed_label_name}"
        try:
            response = (
                self.gmail_service.users()
                .messages()
                .list(userId="me", q=query, maxResults=100)
                .execute()
            )
            return response.get("messages", [])
        except Exception as e:
            logger.error(f"An error occurred while searching unread emails: {e}")
            return []

    def search_starred_emails(self) -> List[Dict[str, Any]]:
        """Fetches starred emails and returns them in a structured format."""
        if not self.gmail_service:
            return []
        try:
            response = (
                self.gmail_service.users()
                .messages()
                .list(userId="me", q="is:starred", maxResults=50)
                .execute()
            )
            messages = response.get("messages", [])

            starred_list = []
            for msg in messages:
                details = self.get_email_details(msg["id"])
                if details:
                    parsed = parse_email_content(details)
                    starred_list.append(
                        {
                            "id": msg["id"],
                            "threadId": details.get("threadId"),
                            "from": parsed.get("from"),
                            "subject": parsed.get("subject"),
                            "snippet": details.get("snippet"),
                            "timestamp": int(details.get("internalDate")) / 1000,
                        }
                    )
            return starred_list
        except Exception as e:
            logger.error(f"An error occurred while searching starred emails: {e}")
            return []

    def get_all_labels(self) -> List[Dict[str, Any]]:
        """Fetches all user-created labels from Gmail."""
        if not self.gmail_service:
            return []
        try:
            results = self.gmail_service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])
            user_labels = [l for l in labels if l.get("type") == "user"]
            return user_labels
        except Exception as e:
            logger.error(f"An error occurred while fetching labels: {e}")
            return []

    def search_emails_by_label(
        self,
        label_id: str,
        query: str = "",
        page_token: Optional[str] = None,
        max_results: int = 25,
    ) -> Dict[str, Any]:
        """Fetches a paginated list of emails for a given label, with an optional search query."""
        if not self.gmail_service:
            return {"emails": [], "nextPageToken": None, "total": 0}
        try:
            request = (
                self.gmail_service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    labelIds=[label_id],
                    maxResults=max_results,
                    pageToken=page_token,
                )
            )
            response = request.execute()

            messages = response.get("messages", [])
            email_list = []
            for msg in messages:
                details = self.get_email_details(msg["id"])
                if details:
                    parsed = parse_email_content(details)
                    is_starred = "STARRED" in details.get("labelIds", [])
                    email_list.append(
                        {
                            "id": msg["id"],
                            "threadId": details.get("threadId"),
                            "from": parsed.get("from"),
                            "subject": parsed.get("subject"),
                            "snippet": details.get("snippet"),
                            "timestamp": int(details.get("internalDate")) / 1000,
                            "is_starred": is_starred,
                        }
                    )

            return {
                "emails": email_list,
                "nextPageToken": response.get("nextPageToken"),
                "total": response.get("resultSizeEstimate", 0),
            }
        except Exception as e:
            logger.error(
                f"An error occurred while searching emails for label {label_id}: {e}"
            )
            return {"emails": [], "nextPageToken": None, "total": 0}

    def modify_email_labels(
        self, message_id: str, labels_to_add: List[str], labels_to_remove: List[str]
    ) -> None:
        if not self.gmail_service:
            return
        add_label_ids = [
            self.get_or_create_label_id(name) for name in labels_to_add if name
        ]
        remove_label_ids = [
            self.get_or_create_label_id(name) for name in labels_to_remove if name
        ]
        add_label_ids = [id for id in add_label_ids if id]
        remove_label_ids = [id for id in remove_label_ids if id]

        if not add_label_ids and not remove_label_ids:
            return
        modify_request = {
            "addLabelIds": add_label_ids,
            "removeLabelIds": remove_label_ids,
        }
        try:
            self.gmail_service.users().messages().modify(
                userId="me", id=message_id, body=modify_request
            ).execute()
        except Exception as e:
            logger.error(
                f"An error occurred modifying labels for email {message_id}: {e}"
            )

    # --- Calendar Methods ---
    def create_calendar_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        attendees: List[dict[str, str]] = None,
    ) -> Optional[Dict]:
        """Creates a new event on the user's primary calendar."""
        if not self.calendar_service:
            return None
        event = {
            "summary": summary,
            "start": {"dateTime": start_time, "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": end_time, "timeZone": "Asia/Kolkata"},
        }
        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]
        try:
            created_event = (
                self.calendar_service.events()
                .insert(calendarId="primary", body=event)
                .execute()
            )
            logger.info(f"Event created: {created_event.get('htmlLink')}")
            return created_event
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}", exc_info=True)
            return None

    # --- Drive Methods ---
    def get_or_create_folder_id(self, folder_name: str) -> Optional[str]:
        """Searches for a folder in Drive by name and creates it if not found."""
        if not self.drive_service:
            return None
        try:
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
            response = (
                self.drive_service.files()
                .list(q=query, spaces="drive", fields="files(id, name)")
                .execute()
            )
            if response.get("files"):
                logger.info(f"Found existing Drive folder '{folder_name}'.")
                return response.get("files")[0].get("id")

            logger.info(f"Drive folder '{folder_name}' not found, creating it.")
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            file = (
                self.drive_service.files()
                .create(body=file_metadata, fields="id")
                .execute()
            )
            return file.get("id")
        except Exception as e:
            logger.error(
                f"Failed to get or create Drive folder '{folder_name}': {e}",
                exc_info=True,
            )
            return None

    def get_attachment(self, message_id: str, attachment_id: str) -> Optional[str]:
        """Retrieves the base64-encoded data for a specific email attachment."""
        if not self.gmail_service:
            return None
        try:
            attachment = (
                self.gmail_service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
            return attachment.get("data")
        except Exception as e:
            logger.error(
                f"Failed to get attachment {attachment_id} from message {message_id}: {e}",
                exc_info=True,
            )
            return None

    def upload_file_to_drive(
        self, folder_id: str, filename: str, file_data_b64: str, mimetype: str
    ):
        """Uploads a file (from base64 data) to a specified Google Drive folder."""
        if not self.drive_service:
            return None
        try:
            file_data = base64.urlsafe_b64decode(file_data_b64.encode("UTF-8"))
            media = MediaIoBaseUpload(io.BytesIO(file_data), mimetype=mimetype)
            file_metadata = {"name": filename, "parents": [folder_id]}
            file = (
                self.drive_service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
            logger.info(
                f"Successfully uploaded file '{filename}' to Drive with ID: {file.get('id')}"
            )
            return file
        except Exception as e:
            logger.error(
                f"Failed to upload file '{filename}' to Drive: {e}", exc_info=True
            )
            return None

    def search_drive_files(self, query: str, max_results: int = 10) -> List[Dict]:
        """Searches for files in the user's Google Drive."""
        if not self.drive_service:
            return []
        try:
            keywords = [keyword.replace("'", "\\'") for keyword in query.split()]

            name_query_parts = [f"name contains '{keyword}'" for keyword in keywords]
            text_query_parts = [
                f"fullText contains '{keyword}'" for keyword in keywords
            ]

            name_query = " and ".join(name_query_parts)
            text_query = " and ".join(text_query_parts)

            formatted_query = f"({name_query}) or ({text_query})"

            logger.info(f"Searching Drive with formatted query: {formatted_query}")

            results = (
                self.drive_service.files()
                .list(
                    q=formatted_query,
                    pageSize=max_results,
                    fields="nextPageToken, files(id, name, webViewLink)",
                )
                .execute()
            )
            return results.get("files", [])
        except Exception as e:
            logger.error(f"Failed to search Drive: {e}", exc_info=True)
            return []
