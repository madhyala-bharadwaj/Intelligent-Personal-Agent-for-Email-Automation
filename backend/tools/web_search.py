"""
Tool for performing web searches using the Tavily Search API.
This allows the agent to find information beyond its internal knowledge.
"""

from langchain.tools import tool
from tavily import TavilyClient
import config
from utils.logger import get_logger

logger = get_logger(__name__)


@tool
def search_the_web(query: str) -> str:
    """
    Performs a web search for the given query using the Tavily Search API.
    Use this for questions about current events, general knowledge, or information not found in the personal knowledge base.
    """
    logger.info(f"Performing web search for '{query}' using Tavily...")
    try:
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        response = client.search(query=query, search_depth="basic", max_results=3)
        results = "\n".join(
            [f"- {obj['content']}" for obj in response.get("results", [])]
        )
        return results if results else "No results found."
    except Exception as e:
        logger.error(f"Error performing web search: {e}")
        return f"Error performing web search: {e}"
