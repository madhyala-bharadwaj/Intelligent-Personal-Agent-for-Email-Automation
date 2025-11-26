"""
Defines the LangGraph workflow, connecting the nodes and conditional edges.
The GraphOrchestrator class builds and compiles the StateGraph, defining the
agent's core decision-making process.
"""

from functools import partial
from langgraph.graph import END, StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI

import config
from graph.nodes import (
    critique_and_refine,
    execute_tool,
    extract_data,
    find_learning_opportunities,
    generate_response,
    retrieve_from_knowledge_base,
    select_intent_and_tool,
    triage_email,
)
from graph.state import AgentState
from services.google_api_service import GoogleApiService
from services.knowledge_base import KnowledgeBase
from tools.tool_registry import (
    ToolRegistry,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class GraphOrchestrator:
    def __init__(
        self,
        llm: ChatGoogleGenerativeAI,
        knowledge_base: KnowledgeBase,
        google_api_service: GoogleApiService,
        tool_registry: ToolRegistry,
    ):
        self.llm = llm
        self.knowledge_base = knowledge_base
        self.google_api_service = google_api_service
        self.tool_registry = tool_registry
        self.app = self._build_graph()

    def _build_graph(self):
        """Constructs the LangGraph StateGraph."""
        workflow = StateGraph(AgentState)

        triage_node = partial(triage_email, llm=self.llm)
        extract_node = partial(extract_data, llm=self.llm)
        learning_node = partial(find_learning_opportunities, llm=self.llm)
        intent_node = partial(
            select_intent_and_tool, llm=self.llm, tool_registry=self.tool_registry
        )
        rag_node = partial(
            retrieve_from_knowledge_base,
            llm=self.llm,
            retriever=self.knowledge_base.get_retriever(),
        )
        tool_node = partial(
            execute_tool,
            llm=self.llm,
            google_api_service=self.google_api_service,
            tool_registry=self.tool_registry,
        )
        response_node = partial(generate_response, llm=self.llm)
        critique_node = partial(critique_and_refine, llm=self.llm)

        # Add nodes to the graph
        workflow.add_node("triage", triage_node)
        workflow.add_node("extract_data", extract_node)
        workflow.add_node("find_learning_opportunities", learning_node)
        workflow.add_node("select_intent", intent_node)
        workflow.add_node("rag", rag_node)
        workflow.add_node("execute_tool", tool_node)
        workflow.add_node("generate_response", response_node)
        workflow.add_node("critique_and_refine", critique_node)

        # Define the graph's control flow
        workflow.set_entry_point("triage")
        workflow.add_conditional_edges(
            "triage", self._route_after_triage, {"continue": "extract_data", "end": END}
        )

        workflow.add_conditional_edges(
            "extract_data",
            self._route_after_extraction,
            {"learn": "find_learning_opportunities", "end": END},
        )
        workflow.add_edge("find_learning_opportunities", "select_intent")

        workflow.add_conditional_edges(
            "select_intent",
            self._route_action,
            {
                "rag_and_respond": "rag",
                "tool_and_respond": "execute_tool",
                "respond": "generate_response",
                "end": END,
            },
        )
        workflow.add_edge("rag", "generate_response")
        workflow.add_edge("execute_tool", "generate_response")
        workflow.add_edge("generate_response", "critique_and_refine")
        workflow.add_conditional_edges(
            "critique_and_refine",
            self._route_for_revision,
            {"revise": "generate_response", "end": END},
        )

        return workflow.compile()

    # --- Conditional Routing Functions ---
    def _route_after_triage(self, state: AgentState) -> str:
        logger.info("---ROUTER: After Triage---")
        triage_result = state.get("triage_result")

        if state.get("error_message") or not triage_result:
            logger.info("Decision: Ending workflow (error or no triage result).")
            return "end"

        if triage_result.priority == "high":
            logger.info(
                "Decision: High priority detected. Continuing to data extraction."
            )
            return "continue"

        if not triage_result.should_respond:
            logger.info(
                "Decision: Not high priority and no response needed. Ending workflow."
            )
            return "end"

        logger.info("Decision: Response needed. Continuing to data extraction.")
        return "continue"

    def _route_after_extraction(self, state: AgentState) -> str:
        logger.info("---ROUTER: After Data Extraction---")
        triage_result = state.get("triage_result")

        if (
            triage_result
            and triage_result.priority == "high"
            and not triage_result.should_respond
        ):
            logger.info(
                "Decision: High-priority summary extracted. Ending response workflow."
            )
            return "end"

        logger.info("Decision: Continuing to learning opportunities.")
        return "learn"

    def _route_action(self, state: AgentState) -> str:
        logger.info("---ROUTER: Main Action Router---")
        intent = state.get("intent")
        triage_result = state.get("triage_result")

        if state.get("error_message") or not intent or not triage_result:
            logger.info(
                "Decision: Ending workflow (error or missing intent/triage data)."
            )
            return "end"

        if hasattr(self.tool_registry, intent.tool_name):
            logger.info(f"Decision: Routing to tool '{intent.tool_name}'.")
            return "tool_and_respond"

        if triage_result.category in ["job_application", "customer_support"]:
            logger.info("Decision: Routing to RAG for internal knowledge.")
            return "rag_and_respond"

        logger.info("Decision: Routing directly to response generation.")
        return "respond"

    def _route_for_revision(self, state: AgentState) -> str:
        logger.info("---ROUTER: Revision Check---")
        revision_count = state.get("revision_count", 0)
        requires_review = state.get("requires_review", False)

        if requires_review or revision_count >= config.MAX_REVISIONS:
            if revision_count >= config.MAX_REVISIONS:
                logger.warning(
                    f"Max revisions ({config.MAX_REVISIONS}) reached. Finalizing."
                )
            logger.info(
                f"Decision: Ending workflow. Requires Review: {requires_review}, Revisions: {revision_count}"
            )
            return "end"

        logger.info(f"Decision: Revising draft. Revision count: {revision_count}")
        return "revise"

    def invoke(self, initial_state: dict):
        """Runs the graph with the provided initial state."""
        return self.app.invoke(initial_state)
