# Copyright (c) Microsoft. All rights reserved.

"""
Legal Workflow - Orchestrates agents using Microsoft Agent Framework WorkflowBuilder.
"""

import os
from typing import List, Dict, Any
from agent_framework import (
    WorkflowBuilder,
    WorkflowContext,
    Executor,
    ChatMessage,
    Case,
    Default,
    handler,
    AgentExecutorRequest,
    AgentExecutorResponse,
    AgentExecutor
)
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import logging

from agents.router import RouterAgent, is_classification_query, is_section_query
from agents.legal_classifier import create_legal_classifier
from agents.section_expert import create_section_expert
from models.schemas import QueryDecision
from typing_extensions import Never

load_dotenv()
logger = logging.getLogger(__name__)


class QueryPreprocessor(Executor):
    """Executor that preprocesses user queries and enriches with context."""
    
    def __init__(self, search_context_func=None):
        """
        Initialize the query preprocessor.
        
        Args:
            search_context_func: Function to retrieve context from vector search
        """
        super().__init__(id="query_preprocessor")
        self.search_context_func = search_context_func
    
    @handler
    async def process(
        self, 
        request: Dict[str, Any], 
        ctx: WorkflowContext[Dict[str, Any]]
    ) -> None:
        """
        Process the incoming query and enrich with context.
        
        Args:
            request: Dict containing query, language, chat_history
            ctx: Workflow context for sending messages
        """
        try:
            query = request.get("query", "")
            language = request.get("language", "English")
            chat_history = request.get("chat_history", "")
            
            # Get context from vector search if function is provided
            context = ""
            if self.search_context_func:
                try:
                    context = await self.search_context_func(query)
                except Exception as e:
                    logger.warning(f"Failed to retrieve search context: {e}")
            
            # Enrich the request with context
            enriched_request = {
                "query": query,
                "language": language,
                "chat_history": chat_history,
                "context": context
            }
            
            await ctx.send_message(enriched_request)
            
        except Exception as e:
            logger.error(f"Error in query preprocessing: {e}")
            raise


class RouterExecutor(Executor):
    """Executor that routes queries to appropriate agents."""
    
    def __init__(self, router_agent: RouterAgent):
        """
        Initialize the router executor.
        
        Args:
            router_agent: RouterAgent instance for query classification
        """
        super().__init__(id="router_executor")
        self.router = router_agent
    
    @handler
    async def route(
        self, 
        request: Dict[str, Any], 
        ctx: WorkflowContext[QueryDecision]
    ) -> None:
        """
        Route the query to appropriate agent.
        
        Args:
            request: Enriched request with query and context
            ctx: Workflow context for sending routing decision
        """
        try:
            query = request.get("query", "")
            
            # Get routing decision from router agent
            decision = await self.router.route_query(query)
            
            logger.info(f"Routing decision: {decision.query_type} (confidence: {decision.confidence})")
            
            # Attach the original request to the decision for downstream use
            decision_with_context = {
                "decision": decision,
                "request": request
            }
            
            await ctx.send_message(decision_with_context)
            
        except Exception as e:
            logger.error(f"Error in routing: {e}")
            raise


class LegalClassifierExecutor(Executor):
    """Executor for legal classification agent."""
    
    def __init__(self, chat_client: AzureOpenAIChatClient):
        """
        Initialize the legal classifier executor.
        
        Args:
            chat_client: Azure OpenAI chat client
        """
        super().__init__(id="legal_classifier")
        self.agent = create_legal_classifier(chat_client)
    
    @handler
    async def classify(
        self, 
        decision_context: Dict[str, Any], 
        ctx: WorkflowContext[Never, str]
    ) -> None:
        """
        Classify legal query and provide analysis.
        
        Args:
            decision_context: Dictionary with decision and request
            ctx: Workflow context for yielding output
        """
        try:
            request = decision_context["request"]
            query = request.get("query", "")
            language = request.get("language", "English")
            context = request.get("context", "")
            chat_history_text = request.get("chat_history", "")
            
            # Build prompt with context
            prompt = f"""
Analyze the following criminal situation and provide detailed legal insights.

Previous conversation context:
{chat_history_text if chat_history_text else "No previous context"}

Context from legal database:
{context if context else "No additional context"}

Current query:
{query}

Provide a comprehensive analysis including:
1. Classification of the offense
2. Applicable sections under Indian Penal Code and other relevant acts
3. Severity level (cognizable/non-cognizable, bailable/non-bailable)
4. Legal procedures that apply
5. Rights of the parties involved
6. Possible defenses or mitigating factors

Respond in {language}.

If this situation is not related to a legal problem or criminal situation, reply with:
"I am an AI-powered legal assistant specialized in Indian criminal law. I provide information and assistance related to criminal offenses, legal sections, and legal procedures under Indian law."
"""
            
            messages = [ChatMessage(role="user", text=prompt)]
            response = await self.agent.run(messages)
            
            # Extract response text
            response_text = self._extract_text(response)
            
            await ctx.yield_output(response_text)
            
        except Exception as e:
            logger.error(f"Error in legal classification: {e}")
            await ctx.yield_output(f"Error processing legal classification: {str(e)}")
    
    def _extract_text(self, response: AgentExecutorResponse) -> str:
        """Extract text from agent response."""
        if hasattr(response, 'text'):
            return response.text
        if hasattr(response, 'messages') and response.messages:
            last_msg = response.messages[-1]
            if hasattr(last_msg, 'text'):
                return last_msg.text
            if hasattr(last_msg, 'contents'):
                for content in last_msg.contents:
                    if hasattr(content, 'text'):
                        return content.text
        return str(response)


class SectionExpertExecutor(Executor):
    """Executor for section expert agent."""
    
    def __init__(self, chat_client: AzureOpenAIChatClient):
        """
        Initialize the section expert executor.
        
        Args:
            chat_client: Azure OpenAI chat client
        """
        super().__init__(id="section_expert")
        self.agent = create_section_expert(chat_client)
    
    @handler
    async def explain(
        self, 
        decision_context: Dict[str, Any], 
        ctx: WorkflowContext[Never, str]
    ) -> None:
        """
        Explain legal section in detail.
        
        Args:
            decision_context: Dictionary with decision and request
            ctx: Workflow context for yielding output
        """
        try:
            request = decision_context["request"]
            query = request.get("query", "")
            language = request.get("language", "English")
            context = request.get("context", "")
            chat_history_text = request.get("chat_history", "")
            
            # Build prompt with context
            prompt = f"""
Provide detailed information about the legal section or act mentioned in the query.

Context from legal database:
{context if context else "No additional context available"}

Previous conversation:
{chat_history_text if chat_history_text else "No previous conversation"}

Query:
{query}

Provide a comprehensive response including:
1. Section number and act name (IPC/BNS, CrPC/BNSS, etc.)
2. Clear summary of what the section covers
3. Prescribed punishment (if applicable)
4. Key elements that constitute the offense/provision
5. Relevant case laws or precedents
6. Related sections
7. Recent amendments if any

Respond in {language}.
"""
            
            messages = [ChatMessage(role="user", text=prompt)]
            response = await self.agent.run(messages)
            
            # Extract response text
            response_text = self._extract_text(response)
            
            await ctx.yield_output(response_text)
            
        except Exception as e:
            logger.error(f"Error in section explanation: {e}")
            await ctx.yield_output(f"Error processing section explanation: {str(e)}")
    
    def _extract_text(self, response: AgentExecutorResponse) -> str:
        """Extract text from agent response."""
        if hasattr(response, 'text'):
            return response.text
        if hasattr(response, 'messages') and response.messages:
            last_msg = response.messages[-1]
            if hasattr(last_msg, 'text'):
                return last_msg.text
            if hasattr(last_msg, 'contents'):
                for content in last_msg.contents:
                    if hasattr(content, 'text'):
                        return content.text
        return str(response)


class LegalWorkflow:
    """Main workflow orchestrator for legal queries."""
    
    def __init__(self, search_context_func=None):
        """
        Initialize the legal workflow.
        
        Args:
            search_context_func: Optional function to retrieve vector search context
        """
        self.chat_client = AzureOpenAIChatClient(
            credential=DefaultAzureCredential(),
            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
            api_version=os.getenv("OPENAI_API_VERSION"),
            model_deployment_name=os.getenv("AZURE_CHAT_DEPLOYMENT")
        )
        
        # Initialize router
        self.router_agent = RouterAgent(self.chat_client)
        
        # Create executors
        self.query_preprocessor = QueryPreprocessor(search_context_func)
        self.router_executor = RouterExecutor(self.router_agent)
        self.legal_classifier = LegalClassifierExecutor(self.chat_client)
        self.section_expert = SectionExpertExecutor(self.chat_client)
        
        # Build workflow with switch-case routing
        self.workflow = self._build_workflow()
        
        logger.info("Legal Workflow initialized with switch-case routing")
    
    def _build_workflow(self):
        """
        Build the workflow with conditional routing.
        
        Returns:
            Configured Workflow instance
        """
        
        def route_condition(decision_context: Dict[str, Any]) -> bool:
            """Helper to extract decision from context."""
            if isinstance(decision_context, dict):
                decision = decision_context.get("decision")
                if isinstance(decision, QueryDecision):
                    return decision
            return None
        
        # Build workflow with switch-case edge group
        workflow = (
            WorkflowBuilder(name="LegalAssistantWorkflow")
            .set_start_executor(self.query_preprocessor)
            .add_edge(self.query_preprocessor, self.router_executor)
            .add_switch_case_edge_group(
                self.router_executor,
                [
                    Case(
                        condition=lambda dc: route_condition(dc) and route_condition(dc).query_type == "law",
                        target=self.legal_classifier
                    ),
                    Case(
                        condition=lambda dc: route_condition(dc) and route_condition(dc).query_type == "section",
                        target=self.section_expert
                    ),
                    Default(target=self.legal_classifier)  # Default to legal classifier
                ]
            )
            .build()
        )
        
        return workflow
    
    async def process_query(
        self, 
        query: str, 
        language: str = "English",
        chat_history: str = ""
    ) -> str:
        """
        Process a legal query through the workflow.
        
        Args:
            query: User's legal query
            language: Response language
            chat_history: Previous conversation context
            
        Returns:
            AI assistant's response
        """
        try:
            # Prepare request
            request = {
                "query": query,
                "language": language,
                "chat_history": chat_history
            }
            
            # Run workflow
            events = await self.workflow.run(request)
            
            # Get outputs
            outputs = events.get_outputs()
            
            if outputs:
                return outputs[0]
            else:
                return "I apologize, but I couldn't process your query. Please try again."
                
        except Exception as e:
            logger.error(f"Error in workflow processing: {e}")
            return f"An error occurred while processing your query: {str(e)}"
