"""
REVISED TOOL: Handles email attachments by analyzing their content, intelligently
renaming them, saving them to Google Drive, and returning the analysis to the agent.
"""

from typing import List, Any, Tuple
from groq import Groq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

import config
from utils.logger import get_logger
from services.google_api_service import GoogleApiService

logger = get_logger(__name__)


class FileName(BaseModel):
    """Structured output for generating a file name."""

    intelligent_name: str = Field(
        description="A descriptive, SEO-friendly file name based on the content, ending with the correct file extension (e.g., .pdf, .jpg)."
    )


def _analyze_and_name_image(
    llm: ChatGoogleGenerativeAI, image_b64: str, email_context: str
) -> Tuple[str, str]:
    """
    Uses a vision model to get an analysis of an image and then uses an LLM
    to generate a filename from that analysis.
    Returns a tuple of (filename, analysis).
    """
    logger.info("Analyzing image with vision model...")
    client = Groq(api_key=config.GROQ_API_KEY)

    try:
        # Step 1: Get a rich, descriptive analysis from the vision model.
        standard_b64 = image_b64.replace("-", "+").replace("_", "/")
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Analyze this image in detail. Describe what you see, what the purpose of the interface or image is, and any text visible. The original email context is: {email_context}",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{standard_b64}"
                            },
                        },
                    ],
                }
            ],
            model=config.VISION_MODEL_NAME,
        )
        image_analysis = chat_completion.choices[0].message.content
        logger.info(f"Image Analysis Received: {image_analysis}")

        # Step 2: Use the analysis to generate a concise filename.
        parser_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert at creating a concise, descriptive filename from a text description. The filename must end with a correct image extension (like .jpg or .png).",
                ),
                (
                    "human",
                    "Based on this analysis, what is the best filename?\n\nAnalysis: {analysis}",
                ),
            ]
        )

        parser_chain = parser_prompt | llm.with_structured_output(FileName)
        result = parser_chain.invoke({"analysis": image_analysis})

        logger.info(f"Generated intelligent filename: {result.intelligent_name}")
        return result.intelligent_name, image_analysis

    except Exception as e:
        logger.error(f"Image analysis or naming failed: {e}", exc_info=True)
        return "image_analysis_failed.jpg", "Could not analyze the image."


def _get_intelligent_name_for_doc(
    llm: ChatGoogleGenerativeAI, email_context: str, original_filename: str
) -> str:
    """Uses a standard LLM to generate a name for a non-image document."""
    logger.info(
        f"Analyzing document context for '{original_filename}' to generate file name..."
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert at creating concise, descriptive file names. Based on the email context, create an intelligent file name for the attached document. Preserve the original file extension.",
            ),
            (
                "human",
                "Email Context:\n{context}\n\nOriginal Filename: {filename}\n\nNew Filename:",
            ),
        ]
    )
    chain = prompt | llm.with_structured_output(FileName)
    try:
        result = chain.invoke({"context": email_context, "filename": original_filename})
        return result.intelligent_name
    except Exception as e:
        logger.error(f"Document name generation failed: {e}")
        return original_filename


def analyze_and_save_attachments(
    google_api_service: GoogleApiService,
    llm: ChatGoogleGenerativeAI,
    message_id: str,
    email_context: str,
    attachments: List[Any],
) -> str:
    """
    Processes attachments: saves them to Drive and returns an analysis of their content.
    """
    if not attachments:
        return "No attachments found to process."

    logger.info(
        f"Analyzing and saving {len(attachments)} attachments for message {message_id}..."
    )

    folder_id = google_api_service.get_or_create_folder_id(config.DRIVE_FOLDER_NAME)
    if not folder_id:
        error_msg = "Error: Could not access or create the Google Drive folder. Check permissions."
        logger.error(error_msg)
        return error_msg

    analysis_results = []
    for attachment in attachments:
        try:
            original_filename = attachment["filename"]
            mimetype = attachment["mimeType"]
            attachment_id = attachment["id"]

            if not all([original_filename, mimetype, attachment_id]):
                logger.warning("Skipping attachment with missing details.")
                continue

            attachment_data_b64 = google_api_service.get_attachment(
                message_id, attachment_id
            )
            if not attachment_data_b64:
                logger.warning(
                    f"Could not retrieve data for attachment {original_filename}"
                )
                continue

            analysis_text = f"Attachment '{original_filename}' was a non-visual file."
            if mimetype.startswith("image/"):
                new_filename, analysis_text = _analyze_and_name_image(
                    llm, attachment_data_b64, email_context
                )
            else:
                new_filename = _get_intelligent_name_for_doc(
                    llm, email_context, original_filename
                )

            google_api_service.upload_file_to_drive(
                folder_id, new_filename, attachment_data_b64, mimetype
            )
            analysis_results.append(
                f"Successfully saved '{new_filename}'. My analysis is: {analysis_text}"
            )

        except Exception as e:
            filename_for_log = attachment.get("filename", "N/A")
            logger.error(
                f"Failed to process attachment {filename_for_log}: {e}", exc_info=True
            )
            continue

    if not analysis_results:
        return "Could not save or analyze any attachments."

    return "\n".join(analysis_results)
