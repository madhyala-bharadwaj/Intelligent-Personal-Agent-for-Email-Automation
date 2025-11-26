"""
Contains the functions that define the nodes in our LangGraph workflow.
Each node is a self-contained unit of work. Using structured outputs (Pydantic models)
from the LLM calls makes the data flow between nodes reliable and type-safe.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

from graph.state import AgentState, TriageResult, ExtractedData, Intent, Critique
from tools.tool_registry import ToolRegistry
from tools.knowledge_updater import extract_learnable_info
from utils.logger import get_logger
from services.google_api_service import GoogleApiService
from services.settings_service import SettingsService
from prompts.prompt_library import PromptLibrary

logger = get_logger(__name__)


# --- Node 1: Triage ---
def triage_email(state: AgentState, llm: ChatGoogleGenerativeAI) -> dict:
    """Classifies the email, assigns priority, and decides if a response is needed."""
    logger.info("---NODE: TRIAGING EMAIL---")
    email_details = state.get("email_details")
    if not email_details:
        return {"error_message": "Triage failed: Missing email_details in state."}

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PromptLibrary.TRIAGE_PROMPT),
            (
                "human",
                "Conversation History:\n{history}\n\nLatest Email:\n\n{email_content}",
            ),
        ]
    )
    chain = prompt | llm.with_structured_output(TriageResult)
    try:
        result = chain.invoke(
            {
                "history": state.get("conversation_history") or "N/A",
                "email_content": email_details.full_content,
            }
        )
        if not result:
            logger.error("Triage LLM call returned None. API might be timing out.")
            return {"error_message": "Triage failed: LLM API returned no result."}

        logger.info(f"Triage Result: {result.model_dump_json(indent=2)}")
        return {"triage_result": result}
    except Exception as e:
        logger.error(f"Triage failed: {e}", exc_info=True)
        return {"error_message": f"Triage failed: {e}"}


# --- Node 2: Extract Data ---
def extract_data(state: AgentState, llm: ChatGoogleGenerativeAI) -> dict:
    """Extracts a summary and checks for attachments."""
    logger.info("---NODE: EXTRACTING DATA---")
    email_details = state.get("email_details")
    if not email_details:
        return {
            "error_message": "Data extraction failed: Missing email_details in state."
        }

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PromptLibrary.EXTRACT_DATA_PROMPT),
            (
                "human",
                "Email has attachments: {has_attachments_bool}\n\nLatest Email:\n\n{email_content}",
            ),
        ]
    )
    chain = prompt | llm.with_structured_output(ExtractedData)
    try:
        has_attachments = bool(email_details.attachments)
        result = chain.invoke(
            {
                "email_content": email_details.full_content,
                "has_attachments_bool": has_attachments,
            }
        )
        if not result:
            logger.error(
                "Data extraction LLM call returned None. API might be timing out."
            )
            return {
                "error_message": "Data extraction failed: LLM API returned no result."
            }

        logger.info(f"Extracted Data: {result.model_dump_json(indent=2)}")
        return {"extracted_data": result}
    except Exception as e:
        logger.error(f"Data extraction failed: {e}", exc_info=True)
        return {"error_message": f"Data extraction failed: {e}"}


# --- Node 3: Find Learning Opportunities ---
def find_learning_opportunities(state: AgentState, llm: ChatGoogleGenerativeAI) -> dict:
    """Scans the email for new facts and saves them to the state."""
    logger.info("---NODE: FINDING LEARNING OPPORTUNITIES---")
    email_details = state.get("email_details")
    if not email_details:
        return {}

    learnable_info = extract_learnable_info(llm, email_details.full_content)

    if learnable_info and learnable_info.is_significant and learnable_info.fact:
        return {"learnable_fact": learnable_info.fact}

    return {}


# --- Node 4: Intent & Tool Selection ---
def select_intent_and_tool(
    state: AgentState, llm: ChatGoogleGenerativeAI, tool_registry: ToolRegistry
) -> dict:
    """Determines the user's intent and selects a tool."""
    logger.info("---NODE: SELECTING INTENT AND TOOL---")
    email_details = state.get("email_details")
    extracted_data = state.get("extracted_data")
    if not email_details or not extracted_data:
        return {
            "error_message": "Intent selection failed: Missing email_details or extracted_data."
        }

    available_tools = ", ".join([tool.name for tool in tool_registry.get_all_tools()])
    system_prompt = PromptLibrary.get_select_intent_prompt(
        available_tools, extracted_data.summary, extracted_data.has_attachments
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                "Conversation History:\n{history}\n\nLatest Email:\n\n{full_content}",
            ),
        ]
    )
    chain = prompt | llm.with_structured_output(Intent)
    try:
        result = chain.invoke(
            {
                "history": state.get("conversation_history") or "N/A",
                "full_content": email_details.full_content,
            }
        )
        if not result:
            logger.error(
                "Intent selection LLM call returned None. API might be timing out."
            )
            return {
                "error_message": "Intent selection failed: LLM API returned no result."
            }

        logger.info(
            f"Intent Selected: Tool='{result.tool_name}', Query='{result.tool_query}'"
        )
        return {"intent": result}
    except Exception as e:
        logger.error(f"Intent selection failed: {e}", exc_info=True)
        return {"error_message": f"Intent selection failed: {e}"}


# --- Node 5: RAG ---
def retrieve_from_knowledge_base(
    state: AgentState, llm: ChatGoogleGenerativeAI, retriever
) -> dict:
    """Retrieves relevant information from the personal knowledge base."""
    logger.info("---NODE: RETRIEVING FROM KNOWLEDGE BASE---")
    extracted_data = state.get("extracted_data")
    if not extracted_data:
        return {"rag_context": "Skipping RAG: Missing extracted_data."}

    system_prompt = "You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that. Keep the answer concise.\n\n{context}"
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", "{input}")]
    )
    rag_chain = create_retrieval_chain(
        retriever, create_stuff_documents_chain(llm, prompt)
    )
    try:
        result = rag_chain.invoke({"input": extracted_data.summary})
        logger.info(f"RAG Context Found: {result['answer']}")
        return {"rag_context": result["answer"]}
    except Exception as e:
        logger.warning(f"RAG failed: {e}", exc_info=True)
        return {"rag_context": "Failed to retrieve context from knowledge base."}


# --- Node 6: Tool Execution ---
def execute_tool(
    state: AgentState,
    llm: ChatGoogleGenerativeAI,
    google_api_service: GoogleApiService,
    tool_registry: ToolRegistry,
) -> dict:
    """Executes the selected tool with the appropriate arguments."""
    logger.info("---NODE: EXECUTING TOOL---")
    intent = state.get("intent")
    email_details = state.get("email_details")
    if not intent or not email_details:
        return {
            "error_message": "Tool execution failed: Missing intent or email_details."
        }

    tool_name = intent.tool_name
    tool_query = intent.tool_query
    tool_function = getattr(tool_registry, tool_name, None)
    if not tool_function:
        return {"error_message": f"Tool '{tool_name}' not found in registry."}

    try:
        settings_service = SettingsService(
            knowledge_base=None
        )
        settings = settings_service.get_settings()

        if tool_name == "analyze_and_save_attachments":
            tool_input = {
                "message_id": email_details.message_id,
                "email_context": email_details.full_content,
                "attachments": email_details.attachments,
                "drive_folder_name": settings.get("drive_folder_name"),
            }
        else:
            tool_input = tool_query

        logger.info(f"Invoking tool '{tool_name}' with input: {tool_input}")
        output = tool_function.invoke(tool_input)
        logger.info(f"Tool Output: {output}")
        return {"tool_output": output}
    except Exception as e:
        logger.error(f"Tool execution for '{tool_name}' failed: {e}", exc_info=True)
        return {"error_message": f"Tool execution for '{tool_name}' failed: {e}"}


# --- Node 7: Generate Response ---
def generate_response(state: AgentState, llm: ChatGoogleGenerativeAI) -> dict:
    """Generates the final email draft."""
    logger.info(
        f"---NODE: GENERATING DRAFT RESPONSE (Revision #{state.get('revision_count', 0)})---"
    )
    if not state.get("extracted_data"):
        return {"error_message": "Response generation failed: Missing extracted_data."}

    settings_service = SettingsService(knowledge_base=None)
    settings = settings_service.get_settings()
    signature = settings.get("default_email_signature", "Sincerely,\nM Bharadwaj")

    system_prompt = PromptLibrary.get_generate_response_prompt(signature)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                "Primary Goal: {summary}\nConversation History: {history}\nTool Output: {tool_output}\nPrevious Feedback: {critique_feedback}\n\nPlease generate the email draft now.",
            ),
        ]
    )
    chain = prompt | llm
    try:
        response = chain.invoke(
            {
                "summary": state["extracted_data"].summary,
                "history": state.get("conversation_history") or "N/A",
                "tool_output": state.get("tool_output") or "No tool was used.",
                "critique_feedback": state.get("critique_feedback") or "N/A",
            }
        )
        if not response:
            return {
                "error_message": "Response generation failed: LLM API returned no result."
            }
        logger.info(f"Generated Draft:\n{response.content}")
        return {
            "draft_reply": response.content,
            "revision_count": state.get("revision_count", 0) + 1,
        }
    except Exception as e:
        logger.error(f"Response generation failed: {e}", exc_info=True)
        return {"error_message": f"Response generation failed: {e}"}


# --- Node 8: Critique and Refine ---
def critique_and_refine(state: AgentState, llm: ChatGoogleGenerativeAI) -> dict:
    """Critiques the generated draft."""
    logger.info("---NODE: CRITIQUING DRAFT---")
    extracted_data = state.get("extracted_data")
    draft_reply = state.get("draft_reply")
    if not extracted_data or not draft_reply:
        return {"requires_review": True}

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PromptLibrary.CRITIQUE_PROMPT),
            (
                "human",
                "Original Goal: {summary}\nTool Output: {tool_output}\n\n**DRAFT TO REVIEW**:\n---\n{draft}\n---\n\nIs this draft an acceptable response?",
            ),
        ]
    )
    chain = prompt | llm.with_structured_output(Critique)
    try:
        critique = chain.invoke(
            {
                "summary": extracted_data.summary,
                "tool_output": state.get("tool_output") or "No tool was used.",
                "draft": draft_reply,
            }
        )
        if not critique:
            logger.error("Critique LLM call returned None. Approving draft to be safe.")
            return {"requires_review": True}

        if critique.is_acceptable:
            logger.info("Critique: Draft is acceptable.")
            return {"critique_feedback": "None", "requires_review": True}
        else:
            logger.warning(
                f"Critique: Draft is NOT acceptable. Feedback: {critique.feedback}"
            )
            return {"critique_feedback": critique.feedback, "requires_review": False}
    except Exception as e:
        logger.error(
            f"Critique failed, approving draft by default to prevent loop. Error: {e}",
            exc_info=True,
        )
        return {"requires_review": True}
