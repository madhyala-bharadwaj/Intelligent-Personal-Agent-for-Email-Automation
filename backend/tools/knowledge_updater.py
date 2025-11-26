"""
NEW TOOL: Enables the agent to learn from conversations by identifying
new, important facts within an email.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Optional

from utils.logger import get_logger
from prompts.prompt_library import PromptLibrary

logger = get_logger(__name__)


class LearnableInfo(BaseModel):
    """Structured output for identifying learnable facts."""

    is_significant: bool = Field(
        description="Whether a new, significant, and concrete fact was found."
    )
    fact: Optional[str] = Field(
        default=None,
        description="The specific, concise fact that could be learned (e.g., 'Jane Doe's new phone number is 555-1234').",
    )


def extract_learnable_info(
    llm: ChatGoogleGenerativeAI, email_content: str
) -> Optional[LearnableInfo]:
    """
    Scans an email for new, concrete information that would be valuable to add
    to a long-term knowledge base.
    """
    logger.info("Scanning email for learnable information...")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PromptLibrary.LEARNING_PROMPT),
            ("human", "Analyze the following email content:\n\n{content}"),
        ]
    )

    chain = prompt | llm.with_structured_output(LearnableInfo)

    try:
        result = chain.invoke({"content": email_content})

        if not result:
            logger.error(
                "Learnable info LLM call returned None. API might be timing out."
            )
            return None

        if result.is_significant:
            logger.info(f"Found significant new fact: {result.fact}")
        else:
            logger.info("No significant new facts found in the email.")
        return result
    except Exception as e:
        logger.error(f"Failed to extract learnable info: {e}", exc_info=True)
        return None
