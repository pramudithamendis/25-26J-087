"""
Base agent class for all agentic AI agents.

Provides LLM integration, tool calling, memory management, and error handling.
"""

from typing import Dict, List, Optional, Callable, Any
from abc import ABC, abstractmethod
from openai import OpenAI
from app.config import settings
import logging
import json
import time
from functools import wraps

logger = logging.getLogger(__name__)

# Global OpenAI client
_openai_client = None


def get_openai_client() -> Optional[OpenAI]:
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None and settings.OPENAI_API_KEY:
        try:
            _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized for agents")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    return _openai_client


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying agent operations on failure"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_exception
        return wrapper
    return decorator


class BaseAgent(ABC):
    """
    Base class for all agentic AI agents.
    
    Provides:
    - LLM client initialization
    - Tool calling capability (OpenAI function calling)
    - Memory management (conversation history)
    - Error handling and retry logic
    - State tracking
    """
    
    def __init__(
        self,
        name: str,
        system_prompt: str,
        temperature: float = None,
        max_tokens: int = 2000,
        tools: Optional[List[Dict]] = None
    ):
        """
        Initialize base agent.
        
        Args:
            name: Agent name for logging
            system_prompt: System prompt for the agent
            temperature: LLM temperature (defaults to settings.AGENT_TEMPERATURE)
            max_tokens: Maximum tokens for responses
            tools: List of tool definitions for function calling
        """
        self.name = name
        self.system_prompt = system_prompt
        self.temperature = temperature or getattr(settings, 'AGENT_TEMPERATURE', 0.3)
        self.max_tokens = max_tokens
        self.tools = tools or []
        self.client = get_openai_client()
        self.conversation_history: List[Dict] = []
        self.tool_registry: Dict[str, Callable] = {}
        
        # Register tools if provided
        if self.tools:
            self._register_tools()
    
    def _register_tools(self):
        """Register tools for function calling"""
        for tool in self.tools:
            tool_name = tool.get("function", {}).get("name")
            if tool_name:
                # Tools are called by name, actual implementation in subclasses
                logger.debug(f"Registered tool: {tool_name}")
    
    def register_tool(self, name: str, func: Callable, schema: Dict):
        """
        Register a tool function.
        
        Args:
            name: Tool name
            func: Tool function to call
            schema: OpenAI function schema
        """
        self.tool_registry[name] = func
        # Add to tools list if not already present
        tool_exists = any(
            t.get("function", {}).get("name") == name 
            for t in self.tools
        )
        if not tool_exists:
            self.tools.append({
                "type": "function",
                "function": schema
            })
        logger.info(f"Registered tool: {name}")
    
    def add_to_memory(self, role: str, content: str, metadata: Optional[Dict] = None):
        """
        Add message to conversation memory.
        
        Args:
            role: Message role (system, user, assistant, tool)
            content: Message content
            metadata: Optional metadata
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time()
        }
        if metadata:
            message["metadata"] = metadata
        self.conversation_history.append(message)
        logger.debug(f"[{self.name}] Added to memory: {role}")
    
    def get_memory(self) -> List[Dict]:
        """Get conversation history"""
        return self.conversation_history.copy()
    
    def clear_memory(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.debug(f"[{self.name}] Memory cleared")
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def call_llm(
        self,
        user_prompt: str,
        tools: Optional[List[Dict]] = None,
        response_format: Optional[Dict] = None
    ) -> Dict:
        """
        Call LLM with prompt and optional tools.
        
        Args:
            user_prompt: User prompt
            tools: Optional tools for function calling
            response_format: Optional response format (e.g., {"type": "json_object"})
        
        Returns:
            LLM response dictionary
        """
        if not self.client:
            raise RuntimeError("OpenAI client not available")
        
        # Build messages
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history (last 10 messages to avoid token limits)
        recent_history = self.conversation_history[-10:]
        messages.extend(recent_history)
        
        # Add current user prompt
        messages.append({"role": "user", "content": user_prompt})
        
        # Prepare request
        request_params = {
            "model": settings.OPENAI_MODEL,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"
        
        if response_format:
            request_params["response_format"] = response_format
        
        # Add to memory
        self.add_to_memory("user", user_prompt)
        
        try:
            logger.info(f"[{self.name}] Calling LLM...")
            response = self.client.chat.completions.create(**request_params)
            
            message = response.choices[0].message
            result = {
                "content": message.content,
                "role": message.role,
                "tool_calls": []
            }
            
            # Handle tool calls
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments)
                    }
                    for tc in message.tool_calls
                ]
            
            # Add to memory
            self.add_to_memory("assistant", message.content or "", {
                "tool_calls": result.get("tool_calls", [])
            })
            
            return result
            
        except Exception as e:
            logger.error(f"[{self.name}] LLM call failed: {str(e)}")
            raise
    
    def execute_tool_call(self, tool_call: Dict) -> Any:
        """
        Execute a tool call.
        
        Args:
            tool_call: Tool call dictionary with name and arguments
        
        Returns:
            Tool execution result
        """
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("arguments", {})
        
        if tool_name not in self.tool_registry:
            raise ValueError(f"Tool {tool_name} not registered")
        
        logger.info(f"[{self.name}] Executing tool: {tool_name}")
        try:
            func = self.tool_registry[tool_name]
            result = func(**tool_args)
            
            # Add tool result to memory
            self.add_to_memory("tool", json.dumps(result), {
                "tool_name": tool_name,
                "tool_call_id": tool_call.get("id")
            })
            
            return result
        except Exception as e:
            logger.error(f"[{self.name}] Tool execution failed: {str(e)}")
            raise
    
    def call_with_tools(
        self,
        user_prompt: str,
        max_iterations: int = 5
    ) -> Dict:
        """
        Call LLM with tool support, handling tool calls iteratively.
        
        Args:
            user_prompt: User prompt
            max_iterations: Maximum tool call iterations
        
        Returns:
            Final response after tool calls
        """
        tools_to_use = self.tools if self.tools else None
        
        for iteration in range(max_iterations):
            response = self.call_llm(user_prompt, tools=tools_to_use)
            
            # If no tool calls, return response
            if not response.get("tool_calls"):
                return response
            
            # Execute tool calls
            tool_results = []
            for tool_call in response["tool_calls"]:
                try:
                    result = self.execute_tool_call(tool_call)
                    tool_results.append({
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "name": tool_call["name"],
                        "content": json.dumps(result)
                    })
                except Exception as e:
                    logger.error(f"Tool call failed: {str(e)}")
                    tool_results.append({
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "name": tool_call["name"],
                        "content": json.dumps({"error": str(e)})
                    })
            
            # Add tool results to conversation
            for tool_result in tool_results:
                self.conversation_history.append(tool_result)
            
            # Continue conversation with tool results
            user_prompt = "Tool execution completed. Continue with the task."
        
        # Max iterations reached
        logger.warning(f"[{self.name}] Max iterations reached")
        return response
    
    @abstractmethod
    def execute(self, state: Dict) -> Dict:
        """
        Execute agent's main task.
        
        Args:
            state: Current evaluation state
        
        Returns:
            Agent output
        """
        pass
    
    def get_reasoning_chain(self) -> List[Dict]:
        """
        Get reasoning chain from conversation history.
        
        Returns:
            List of reasoning steps
        """
        reasoning = []
        for msg in self.conversation_history:
            if msg["role"] in ["user", "assistant"]:
                reasoning.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg.get("timestamp")
                })
        return reasoning

