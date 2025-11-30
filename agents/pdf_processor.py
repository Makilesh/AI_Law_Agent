# Copyright (c) Microsoft. All rights reserved.

"""
PDF Processor Agent - Handles PDF uploads and conversational retrieval.
"""

import os
from typing import Dict, List
import logging
from agent_framework import ChatAgent, ChatMessage, Role
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain.document_loaders import PyPDFLoader
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore

from utils.prompts import PDF_PROCESSOR_INSTRUCTIONS

load_dotenv()
logger = logging.getLogger(__name__)


class PDFProcessorAgent:
    """Agent for processing PDF documents and answering questions about them."""
    
    def __init__(
        self,
        pinecone_api_key: str = None,
        pinecone_index_name: str = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """
        Initialize the PDF Processor Agent.
        
        Args:
            pinecone_api_key: Pinecone API key
            pinecone_index_name: Name of Pinecone index
            chunk_size: Size of text chunks for splitting
            chunk_overlap: Overlap between chunks
        """
        # Load environment variables
        self.pinecone_api_key = pinecone_api_key or os.getenv("PINECONE_API_KEY")
        self.pinecone_index_name = pinecone_index_name or os.getenv("PINECONE_INDEX_NAME", "pdf-chat-index")
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        logger.info("Pinecone client initialized")
        
        # Initialize embeddings
        try:
            self.embeddings = AzureOpenAIEmbeddings(
                azure_deployment=os.getenv("AZURE_EMBEDDINGS_DEPLOYMENT"),
                openai_api_version=os.getenv("OPENAI_API_VERSION"),
                azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            )
            # Test embeddings
            test_embedding = self.embeddings.embed_query("test")
            logger.info(f"Embeddings initialized. Vector dimension: {len(test_embedding)}")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {str(e)}")
            raise
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        
        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        # Initialize chain (will be set up after PDF processing)
        self.vector_store = None
        self.chain = None
        
        self._initialize_index()
        logger.info("PDF Processor Agent initialized")
    
    def _initialize_index(self):
        """Initialize or connect to Pinecone index."""
        try:
            # Check if index exists
            if self.pinecone_index_name not in self.pc.list_indexes().names():
                logger.info(f"Creating new Pinecone index: {self.pinecone_index_name}")
                self.pc.create_index(
                    name=self.pinecone_index_name,
                    dimension=3072,  # text-embedding-3-large dimension
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
            
            # Get index and clear if needed
            index = self.pc.Index(self.pinecone_index_name)
            stats = index.describe_index_stats()
            total_vector_count = stats.total_vector_count
            
            if total_vector_count != 0:
                index.delete(delete_all=True)
                logger.info("Cleared existing vectors from index")
            
            # Initialize vector store
            self.vector_store = PineconeVectorStore(
                index=index,
                embedding=self.embeddings,
                text_key="text"
            )
            logger.info("Vector store initialized")
            
        except Exception as e:
            logger.error(f"Error initializing index: {str(e)}")
            raise
    
    def _initialize_chain(self):
        """Initialize the conversational retrieval chain."""
        try:
            # Initialize chat model
            chat_model = AzureChatOpenAI(
                openai_api_version=os.getenv("OPENAI_API_VERSION"),
                azure_deployment=os.getenv("AZURE_CHAT_DEPLOYMENT"),
                azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                streaming=False,
                temperature=0.7,
                max_tokens=2000,
            )
            
            # Test chat model
            test_response = chat_model.invoke("Test message")
            logger.info("Chat model initialized and tested")
            
            # Initialize chain
            self.chain = ConversationalRetrievalChain.from_llm(
                llm=chat_model,
                retriever=self.vector_store.as_retriever(search_kwargs={"k": 10}),
                memory=self.memory,
                return_source_documents=True,
                verbose=True,
                output_key="answer"
            )
            logger.info("Conversational retrieval chain initialized")
            
        except Exception as e:
            logger.error(f"Chain initialization failed: {str(e)}")
            raise
    
    async def process_pdf(self, pdf_path: str) -> Dict:
        """
        Process a PDF file and store in vector database.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dict with processing statistics
        """
        try:
            logger.info(f"Starting to process PDF: {pdf_path}")
            
            # Verify file exists
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            # Load PDF
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()
            total_pages = len(pages)
            logger.info(f"Loaded PDF with {total_pages} pages")
            
            # Split into chunks
            texts = self.text_splitter.split_documents(pages)
            total_chunks = len(texts)
            logger.info(f"Created {total_chunks} text chunks")
            
            # Check index capacity (free tier limit: 10,000 vectors)
            index = self.pc.Index(self.pinecone_index_name)
            stats = index.describe_index_stats()
            current_vectors = stats.get("total_vector_count", 0)
            logger.info(f"Current vectors in index: {current_vectors}")
            
            if current_vectors + total_chunks > 10000:
                raise Exception("This upload would exceed the free tier limit of 10,000 vectors")
            
            # Process chunks and upload
            logger.info("Starting embeddings generation and upload")
            self.vector_store = PineconeVectorStore.from_documents(
                documents=texts,
                embedding=self.embeddings,
                index_name=self.pinecone_index_name,
            )
            logger.info("Successfully uploaded embeddings to Pinecone")
            
            # Initialize the chain
            self._initialize_chain()
            
            return {
                "total_pages": total_pages,
                "total_chunks": total_chunks,
                "vectors_before": current_vectors,
                "vectors_after": current_vectors + total_chunks,
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise
    
    async def query_pdf(
        self, 
        question: str, 
        language: str = "English",
        chat_history: str = ""
    ) -> str:
        """
        Query the processed PDF with a question.
        
        Args:
            question: User's question
            language: Response language
            chat_history: Previous conversation context
            
        Returns:
            Answer from the PDF content
        """
        try:
            if self.chain is None:
                return "Please upload a PDF document first before asking questions."
            
            # Enhance question with language instruction
            enhanced_question = f"""
{question}

Please provide your answer in {language}. Base your response on the content of the uploaded legal document.
"""
            
            # Query the chain
            result = self.chain({"question": enhanced_question})
            
            answer = result.get("answer", "I couldn't find an answer in the document.")
            source_documents = result.get("source_documents", [])
            
            # Add source information if available
            if source_documents:
                sources = set()
                for doc in source_documents[:3]:  # Top 3 sources
                    page = doc.metadata.get("page", "unknown")
                    sources.add(f"Page {page}")
                
                if sources:
                    answer += f"\n\nSources: {', '.join(sorted(sources))}"
            
            return answer
            
        except Exception as e:
            logger.error(f"Error querying PDF: {str(e)}")
            return f"Error processing your question: {str(e)}"
    
    def clear_memory(self):
        """Clear conversation memory."""
        self.memory.clear()
        logger.info("Conversation memory cleared")
    
    def get_index_stats(self) -> Dict:
        """
        Get statistics about the Pinecone index.
        
        Returns:
            Dict with index statistics
        """
        try:
            index = self.pc.Index(self.pinecone_index_name)
            stats = index.describe_index_stats()
            logger.info(f"Retrieved index stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error getting index stats: {str(e)}")
            raise
