"""
Initializes and runs the multi-tool conversational agent, now integrated
with the dynamic ToolRegistry for a comprehensive and extensible toolset.
"""

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from prompts.prompt_library import PromptLibrary
from tools.tool_registry import ToolRegistry
from utils.logger import get_logger
from services.google_api_service import GoogleApiService


logger = get_logger(__name__)


class ChatAgentService:
    """
    A service to create and manage the chat agent. It uses the ToolRegistry
    to dynamically equip the agent with all available tools.
    """

    def __init__(
        self, tool_registry: ToolRegistry, google_api_service: GoogleApiService, llm
    ):
        """
        Initializes the ChatAgentService.

        Args:
            tool_registry (ToolRegistry): An instance of ToolRegistry that provides
                                          the necessary tools for the agent.
            google_api_service (GoogleApiService): Instance for Google API interactions.
            llm: The language model instance.
        """
        logger.info("Initializing ChatAgentService with ToolRegistry...")
        self.tool_registry = tool_registry
        self.google_api_service = google_api_service
        self.llm = llm
        self.agent_executor = self._create_chat_agent()
        logger.info("ChatAgentService initialized successfully.")

    def _create_chat_agent(self) -> AgentExecutor:
        """
        Creates the chat agent by assembling the prompt, LLM, and the
        comprehensive toolset from the ToolRegistry.
        """
        logger.info("Creating the chat agent with a dynamic toolset.")

        system_prompt = PromptLibrary.get_agent_prompt()
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        # Get the complete list of tools directly from the registry
        tools = self.tool_registry.get_all_tools()

        logger.info(f"Agent will be created with {len(tools)} tools.")

        agent = create_tool_calling_agent(self.llm, tools, prompt)

        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
        )

        return agent_executor

    def get_agent_executor(self) -> AgentExecutor:
        """
        Returns the created agent executor instance.
        """
        return self.agent_executor

    async def invoke(self, user_input: str, chat_history: list) -> str:
        """Invokes the agent with the user's input and chat history."""
        try:
            formatted_history = []
            for msg in chat_history:
                if msg.get("role") == "user":
                    formatted_history.append(HumanMessage(content=msg.get("content")))
                elif msg.get("role") == "agent":
                    formatted_history.append(AIMessage(content=msg.get("content")))

            response = await self.agent_executor.ainvoke(
                {"input": user_input, "chat_history": formatted_history}
            )

            if response.get("output"):
                return response["output"]

            if response.get("intermediate_steps"):
                last_action, last_observation = response["intermediate_steps"][-1]
                return last_observation

            return "I'm sorry, I encountered an issue processing your request."

        except Exception as e:
            logger.error(f"Error during agent invocation: {e}", exc_info=True)
            return "An error occurred while talking to the agent."

    async def generate_smart_replies(self, websocket, email_id: str):
        """
        Generates smart reply suggestions for a given email and sends them to the client.
        """
        try:
            logger.info(f"Generating smart replies for email_id: {email_id}")
            # 1. Fetch email content
            full_email = self.google_api_service.get_email_details(email_id)
            if not full_email or not full_email.get("snippet"):
                logger.warning(
                    f"Could not fetch details for smart reply on email {email_id}"
                )
                return

            email_content = full_email["snippet"]

            # 2. Format the prompt
            prompt = PromptLibrary.SMART_REPLY_PROMPT.format(
                email_content=email_content
            )

            # 3. Invoke the LLM
            response = await self.llm.ainvoke(prompt)

            # 4. Parse the response
            suggestions = [
                line.strip()
                for line in response.content.split("\n")
                if line.strip() and not line.strip().startswith("-")
            ]

            # 5. Send suggestions back to the client
            await websocket.send_json(
                {
                    "type": "smart_reply_suggestions",
                    "payload": {
                        "suggestions": suggestions[:3]  # Ensure max 3
                    },
                }
            )
            logger.info(f"Sent smart replies for {email_id}: {suggestions[:3]}")

        except Exception as e:
            logger.error(
                f"Error generating smart replies for {email_id}: {e}", exc_info=True
            )
