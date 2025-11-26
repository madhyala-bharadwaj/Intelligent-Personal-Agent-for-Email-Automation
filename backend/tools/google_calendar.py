"""
REFACTORED: Tool for interacting with Google Calendar.
This version has been re-engineered to be more robust. Instead of relying on
brittle string parsing, it now uses an LLM to understand the user's natural
language query and extract a structured start and end time. This makes it far
more flexible and reliable.
"""

from langchain.tools import tool
from dateutil.parser import parse
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Optional, List
import datetime

from utils.logger import get_logger
from services.google_api_service import GoogleApiService
import config

logger = get_logger(__name__)


class CalendarQuery(BaseModel):
    """Structured output for calendar queries."""

    start_time: str = Field(
        description="The start of the time range in ISO 8601 format."
    )
    end_time: str = Field(description="The end of the time range in ISO 8601 format.")
    summary: Optional[str] = Field(
        default=None, description="A summary or title for a new event."
    )
    attendees: Optional[List[str]] = Field(
        default=None, description="A list of email addresses for attendees."
    )


def _create_parser_chain():
    """Creates the LLM chain for parsing natural language date/time queries."""
    parser_llm = ChatGoogleGenerativeAI(model=config.LLM_MODEL_NAME, temperature=0)
    current_time_info = (
        datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    )

    parser_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""You are an expert at parsing date, time, and event details from natural language.
                The user is in Hyderabad, Telangana, India.
                The current time is {current_time_info}.
                Convert the user's request into a precise start time, end time, a summary for the event, and a list of attendee emails.
                - All times must be in ISO 8601 format (e.g., YYYY-MM-DDTHH:MM:SS+05:30).
                - If no end time is specified, assume the event is 1 hour long.
                - For "next week", assume it starts on the upcoming Monday.
                - Extract any email addresses mentioned as attendees.
                """,
            ),
            ("human", "User's request: '{query}'"),
        ]
    )
    return parser_prompt | parser_llm.with_structured_output(CalendarQuery)


def _parse_query(query: str) -> Optional[CalendarQuery]:
    """Invokes the parser chain and handles errors."""
    parser_chain = _create_parser_chain()
    try:
        return parser_chain.invoke({"query": query})
    except Exception as e:
        logger.error(f"LLM failed to parse calendar query: {e}", exc_info=True)
        return None


@tool
def check_availability(query: str) -> str:
    """
    Checks for available time slots on the user's Google Calendar based on a natural language query.
    Use this to answer questions about scheduling, availability, or events on the calendar.
    For example: 'Am I free tomorrow afternoon?' or 'What's on my calendar for next Tuesday?'.
    """
    logger.info(f"Checking calendar availability for query: '{query}'...")
    parsed_query = _parse_query(query)
    if not parsed_query:
        return "Error: I could not understand the date or time in your request. Please be more specific."

    time_min = parsed_query.start_time
    time_max = parsed_query.end_time
    range_str = (
        f"between {parse(time_min).strftime('%c')} and {parse(time_max).strftime('%c')}"
    )

    try:
        google_api_service = GoogleApiService()
        if not google_api_service.calendar_service:
            return "Error: Could not connect to Google Calendar."

        events_result = (
            google_api_service.calendar_service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        busy_slots = events_result.get("items", [])
        if not busy_slots:
            return f"Your calendar is completely free {range_str}."

        busy_times = [
            f"'{event['summary']}' from {parse(event['start'].get('dateTime')).strftime('%I:%M %p')} to {parse(event['end'].get('dateTime')).strftime('%I:%M %p')}"
            for event in busy_slots
        ]
        return f"You have commitments at the following times {range_str}: {'; '.join(busy_times)}."
    except Exception as e:
        logger.error(f"Error accessing Google Calendar: {e}", exc_info=True)
        return f"Error accessing Google Calendar: {e}"


@tool
def create_calendar_event(query: str) -> str:
    """
    Creates a new event on the user's Google Calendar based on a natural language query.
    Use this to schedule meetings or block out time.
    For example: 'Schedule a meeting with jane.doe@example.com tomorrow at 2pm to discuss the project'.
    """
    logger.info(f"Attempting to create calendar event from query: '{query}'...")
    parsed_query = _parse_query(query)
    if not parsed_query or not parsed_query.summary:
        return "Error: I could not understand the event details. Please provide a title, date, and time."

    try:
        google_api_service = GoogleApiService()
        created_event = google_api_service.create_calendar_event(
            summary=parsed_query.summary,
            start_time=parsed_query.start_time,
            end_time=parsed_query.end_time,
            attendees=parsed_query.attendees,
        )
        if created_event and created_event.get("htmlLink"):
            return f"Successfully created event: '{parsed_query.summary}'. View it here: {created_event['htmlLink']}"
        else:
            return "Error: Failed to create the event in Google Calendar."
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}", exc_info=True)
        return f"Error creating calendar event: {e}"
