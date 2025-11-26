"""
REFACTORED: Manages the connection to and retrieval from a managed vector database.
This implementation uses Pinecone to provide a scalable, cloud-based knowledge
base for the agent, making its knowledge portable and independent of the machine
it runs on.
"""

import os
from pinecone import Pinecone as PineconeClient, ServerlessSpec
from langchain_pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader
from utils.logger import get_logger
import config
import uuid
from google.cloud import firestore


logger = get_logger(__name__)


class KnowledgeBase:
    """Handles loading documents, creating embeddings, and retrieving from Pinecone."""

    def __init__(self):
        """Initializes the knowledge base, connecting to or creating the Pinecone index."""
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=config.EMBEDDING_MODEL_NAME
        )
        self.pc = PineconeClient(api_key=config.PINECONE_API_KEY)
        self.index_name = config.PINECONE_INDEX_NAME
        self.vector_store = self._initialize_vector_store()

        # Initialize Firestore client
        self.db = firestore.Client()
        self.collection_ref = self.db.collection("knowledge_base")

    def _initialize_vector_store(self):
        """
        Connects to an existing Pinecone index or creates a new one.
        If the index is new, it populates it with documents from the knowledge base directory.
        """
        if self.index_name not in self.pc.list_indexes().names():
            logger.info(
                f"Pinecone index '{self.index_name}' not found. Creating a new one..."
            )
            self._create_pinecone_index()
            vector_store = self._populate_new_index()
        else:
            logger.info(f"Connecting to existing Pinecone index '{self.index_name}'...")
            vector_store = Pinecone.from_existing_index(
                self.index_name, self.embeddings
            )

        return vector_store

    def _create_pinecone_index(self):
        """Creates a new serverless Pinecone index."""
        try:
            self.pc.create_index(
                name=self.index_name,
                dimension=768,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            logger.info(f"Successfully created Pinecone index '{self.index_name}'.")
        except Exception as e:
            logger.error(f"Failed to create Pinecone index: {e}")
            raise

    def _populate_new_index(self):
        """Loads documents from the local directory and upserts them into the new index."""
        logger.info(
            f"Loading documents from '{config.KNOWLEDGE_BASE_DIR}' to populate new index..."
        )
        if not os.path.exists(config.KNOWLEDGE_BASE_DIR) or not os.listdir(
            config.KNOWLEDGE_BASE_DIR
        ):
            logger.warning(
                "Knowledge base directory is empty or doesn't exist. RAG will have no context."
            )
            return Pinecone.from_existing_index(self.index_name, self.embeddings)

        loader = DirectoryLoader(config.KNOWLEDGE_BASE_DIR, glob="**/*.txt")
        documents = loader.load()

        if not documents:
            logger.warning(
                "No .txt documents found in the knowledge base directory. RAG will have no context."
            )
            return Pinecone.from_existing_index(self.index_name, self.embeddings)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=100
        )
        docs = text_splitter.split_documents(documents)
        logger.info(f"Creating vector store with {len(docs)} document chunks...")

        vector_store = Pinecone.from_documents(
            docs, self.embeddings, index_name=self.index_name
        )
        logger.info(f"Successfully populated Pinecone index '{self.index_name}'.")
        return vector_store

    def get_retriever(self):
        """Returns a retriever object for the vector store."""
        return self.vector_store.as_retriever()

    def add_fact(self, fact: str):
        """
        Adds a new fact (a single string) to the Pinecone knowledge base.
        """
        try:
            logger.info(f"Adding new fact to knowledge base: '{fact}'")
            vector_id = str(uuid.uuid4())
            self.vector_store.add_texts([fact], ids=[vector_id])
            doc_ref = self.collection_ref.document()
            doc_ref.set(
                {
                    "fact": fact,
                    "pinecone_id": vector_id,
                    "created_at": firestore.SERVER_TIMESTAMP,
                }
            )
            logger.info(
                f"Successfully added fact with ID {doc_ref.id} and vector ID {vector_id}."
            )
            return {"id": doc_ref.id, "fact": fact}
        except Exception as e:
            logger.error(f"Failed to add fact to knowledge base: {e}")

    def get_all_facts(self):
        """Retrieves all facts from the Firestore collection."""
        try:
            logger.info("Fetching all facts from knowledge base...")
            docs = self.collection_ref.order_by(
                "created_at", direction=firestore.Query.DESCENDING
            ).stream()
            facts = [{"id": doc.id, "fact": doc.to_dict()["fact"]} for doc in docs]
            logger.info(f"Successfully fetched {len(facts)} facts.")
            return facts
        except Exception as e:
            logger.error(f"Failed to get all facts: {e}")
            return []

    def delete_fact(self, fact_id: str):
        """Deletes a fact from both Firestore and Pinecone."""
        try:
            logger.info(f"Deleting fact with Firestore ID: {fact_id}")
            doc_ref = self.collection_ref.document(fact_id)
            doc = doc_ref.get()

            if not doc.exists:
                logger.warning(f"Fact with ID {fact_id} not found in Firestore.")
                return {"status": "not_found"}

            pinecone_id = doc.to_dict().get("pinecone_id")

            if pinecone_id:
                index = self.pc.Index(self.index_name)
                index.delete(ids=[pinecone_id])
                logger.info(f"Deleted vector with ID {pinecone_id} from Pinecone.")

            doc_ref.delete()
            logger.info(f"Deleted document with ID {fact_id} from Firestore.")

            return {"status": "success"}
        except Exception as e:
            logger.error(f"Failed to delete fact {fact_id}: {e}")
            raise

    def clear_all_facts(self):
        """
        Deletes all facts from both Firestore and Pinecone. This is a destructive operation.
        """
        try:
            logger.warning("--- DANGER ZONE: Clearing entire knowledge base ---")

            # 1. Delete all vectors from the Pinecone index
            try:
                index = self.pc.Index(self.index_name)
                index.delete(delete_all=True)
                logger.info("Successfully cleared all vectors from Pinecone index.")
            except Exception as pinecone_error:
                logger.error(
                    f"Could not clear Pinecone index, but proceeding with Firestore cleanup. Error: {pinecone_error}"
                )

            # 2. Delete all documents from the Firestore collection
            logger.info(
                "Deleting all documents from Firestore 'knowledge_base' collection..."
            )
            docs = self.collection_ref.stream()
            deleted_count = 0
            for doc in docs:
                doc.reference.delete()
                deleted_count += 1

            logger.info(
                f"Successfully deleted {deleted_count} documents from Firestore."
            )
            return {"status": "success", "deleted_count": deleted_count}
        except Exception as e:
            logger.error(f"Failed to clear knowledge base: {e}", exc_info=True)
            raise
