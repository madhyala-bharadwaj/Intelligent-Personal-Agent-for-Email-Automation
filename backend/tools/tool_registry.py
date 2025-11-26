"""
REVISED: A dynamic, class-based registry for all tools available to the agent.
This implementation automatically discovers tools from various modules,
making the system more modular and easier to extend. It acts as the single
source of truth for the agent's capabilities.
"""

from langchain.tools import BaseTool
from typing import List

from utils.logger import get_logger
from .web_search import search_the_web
from .google_calendar import check_availability, create_calendar_event
from .chat_tools import (
    get_pending_drafts_summary,
    get_high_priority_summary,
    search_gmail,
    search_google_drive,
    draft_a_reply,
    knowledge_tool,
    send_email,
    contact_lookup,
    process_attachment,
    get_full_email_content,
    list_attachments,
    star_email,
    delete_email,
)

logger = get_logger(__name__)


class ToolRegistry:
    """
    A central, dynamic registry for all tools available to the agent.
    It discovers tools from different modules and provides them to the agent executor.
    """

    def __init__(self, google_api_service, knowledge_base=None, llm=None):
        """
        Initializes the ToolRegistry and discovers all available tools.

        Args:
            google_api_service: An instance of the GoogleAPIService.
            knowledge_base: An instance of the KnowledgeBase service.
            llm: The language model instance for tools that need it.
        """
        logger.info("Initializing ToolRegistry...")
        self.google_api_service = google_api_service
        self.knowledge_base = knowledge_base
        self.llm = llm
        self._tools = self._discover_tools()

        # tools accessible via attributes for easy access
        for tool in self._tools:
            setattr(self, tool.name, tool)

        logger.info(f"ToolRegistry initialized with {len(self._tools)} tools.")

    def _discover_tools(self) -> List[BaseTool]:
        """
        Gathers all tool functions from the various tool modules.
        This is where we define the complete toolkit for our advanced agent.
        """
        discovered_tools = [
            # Web Search
            search_the_web,
            # Google Calendar Tools
            check_availability,
            create_calendar_event,
            # Email & Draft Management
            get_pending_drafts_summary,
            get_high_priority_summary,
            get_full_email_content,
            list_attachments,
            star_email,
            delete_email,
            search_gmail,
            search_google_drive,
            draft_a_reply,
            send_email,
            # Knowledge & Information
            knowledge_tool,
            contact_lookup,
            # Attachment & File Handling
            process_attachment,
        ]
        return discovered_tools

    def get_all_tools(self) -> List[BaseTool]:
        """
        Returns the list of all discovered tool instances.
        This is the primary method used by the ChatAgentService.
        """
        return self._tools
