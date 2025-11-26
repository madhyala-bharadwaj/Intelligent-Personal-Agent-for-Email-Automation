"""
REVISED: Deterministic email parsing utility.
Uses Python's standard `email` library to reliably extract headers, content,
and attachment metadata from the raw email data provided by the Gmail API.
"""

import base64
import email
from email.header import decode_header
from typing import Dict, Any, List, Tuple


def parse_email_content(full_email_message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses a full email message object from the Gmail API into a structured dictionary.

    Args:
        full_email_message: The complete message resource from a messages.get() call.

    Returns:
        A dictionary containing parsed details like 'from', 'to', 'subject', 'body',
        and a list of attachments.
    """
    # We must first extract the
    # 'raw' field from the API response, decode it from base64, and then
    # pass the resulting bytes to the email parser.
    raw_email_data = full_email_message.get("raw", "")
    if not raw_email_data:
        payload = full_email_message.get("payload", {})
        return _parse_from_payload(payload)

    email_bytes = base64.urlsafe_b64decode(raw_email_data)
    msg = email.message_from_bytes(email_bytes)

    from_ = _decode_header_field(msg.get("From", ""))
    to = _decode_header_field(msg.get("To", ""))
    subject = _decode_header_field(msg.get("Subject", ""))
    message_id_header = msg.get("Message-ID", "")
    sender_email = email.utils.parseaddr(from_)[1]

    body, attachments = _parse_parts_from_message(msg, full_email_message)

    return {
        "from": from_,
        "sender_email": sender_email,
        "to": to,
        "subject": subject,
        "message_id": message_id_header,
        "body": body.strip(),
        "attachments": attachments,
    }


def _parse_parts_from_message(
    msg: email.message.Message, full_email_message: Dict[str, Any]
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Walks through the parts of a parsed email Message object, prioritizing HTML content.
    """
    html_body = ""
    plain_body = ""
    attachments = []

    attachment_id_map = {}
    if "payload" in full_email_message and "parts" in full_email_message["payload"]:
        for part in full_email_message["payload"].get("parts", []):
            if part.get("filename"):
                attachment_id_map[part["filename"]] = part.get("body", {}).get(
                    "attachmentId"
                )

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            is_attachment = "attachment" in content_disposition

            if not is_attachment:
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"

                    if content_type == "text/html":
                        html_body = payload.decode(charset, errors="replace")
                    elif content_type == "text/plain":
                        plain_body = payload.decode(charset, errors="replace")
                except Exception:
                    continue
            else:
                filename = part.get_filename()
                if filename:
                    attachments.append(
                        {
                            "id": attachment_id_map.get(filename),
                            "filename": filename,
                            "mimeType": part.get_content_type(),
                        }
                    )
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            if msg.get_content_type() == "text/html":
                html_body = payload.decode(charset, errors="replace")
            else:
                plain_body = payload.decode(charset, errors="replace")
        except Exception:
            plain_body = ""

    return html_body, attachments if html_body else plain_body, attachments


def _decode_header_field(header_field: str) -> str:
    """Decodes an email header field to a readable string, handling various encodings."""
    if not header_field:
        return ""
    decoded_parts: List[str] = []
    for part, charset in decode_header(header_field):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(charset or "utf-8", errors="ignore"))
        else:
            decoded_parts.append(str(part))
    return "".join(decoded_parts)


def _parse_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """A fallback parser that works directly with the payload structure if 'raw' is missing."""
    headers = payload.get("headers", [])
    parsed_headers = {h["name"].lower(): h["value"] for h in headers}

    from_ = parsed_headers.get("from", "")
    to = parsed_headers.get("to", "")
    subject = parsed_headers.get("subject", "")
    message_id_header = parsed_headers.get("message-id", "")
    sender_email = email.utils.parseaddr(from_)[1]

    body, attachments = _recursive_payload_parser(payload)

    return {
        "from": from_,
        "sender_email": sender_email,
        "to": to,
        "subject": subject,
        "message_id": message_id_header,
        "body": body.strip(),
        "attachments": attachments,
    }


def _recursive_payload_parser(
    payload: Dict[str, Any],
) -> Tuple[str, List[Dict[str, Any]]]:
    """Recursively parses the payload to find the body and attachments as a fallback."""
    html_body = ""
    plain_body = ""
    attachments = []
    parts = payload.get("parts", [])

    if not parts:
        mime_type = payload.get("mimeType")
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            decoded_data = base64.urlsafe_b64decode(body_data).decode(
                "utf-8", errors="replace"
            )
            if mime_type == "text/html":
                html_body = decoded_data
            elif mime_type == "text/plain":
                plain_body = decoded_data
        return html_body if html_body else plain_body, attachments

    for part in parts:
        filename = part.get("filename")
        mime_type = part.get("mimeType")
        body_data = part.get("body", {})

        if filename:
            attachment_id = body_data.get("attachmentId")
            if attachment_id:
                attachments.append(
                    {"id": attachment_id, "filename": filename, "mimeType": mime_type}
                )
        elif mime_type == "text/html":
            data = body_data.get("data", "")
            if data:
                html_body = base64.urlsafe_b64decode(data).decode(
                    "utf-8", errors="replace"
                )
        elif mime_type == "text/plain":
            data = body_data.get("data", "")
            if data:
                plain_body = base64.urlsafe_b64decode(data).decode(
                    "utf-8", errors="replace"
                )
        elif part.get("parts"):
            nested_body, nested_attachments = _recursive_payload_parser(part)
            if nested_body and not (
                html_body or plain_body
            ):  # Prioritize top-level bodies
                if "<html>" in nested_body:
                    html_body = nested_body
                else:
                    plain_body = nested_body
            attachments.extend(nested_attachments)

    return html_body if html_body else plain_body, attachments
