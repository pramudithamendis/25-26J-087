"""
Unit tests for BaseAgent.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.agents.base_agent import BaseAgent


class TestAgent(BaseAgent):
    """Test agent implementation"""
    
    def execute(self, state):
        return {"result": "test"}


class TestBaseAgent:
    """Test cases for BaseAgent"""
    
    def test_agent_initialization(self):
        """Test agent initialization"""
        agent = TestAgent(
            name="TestAgent",
            system_prompt="Test prompt",
            temperature=0.3
        )
        assert agent.name == "TestAgent"
        assert agent.system_prompt == "Test prompt"
        assert agent.temperature == 0.3
        assert agent.conversation_history == []
    
    def test_add_to_memory(self):
        """Test adding to memory"""
        agent = TestAgent("TestAgent", "Test prompt")
        agent.add_to_memory("user", "Hello")
        assert len(agent.conversation_history) == 1
        assert agent.conversation_history[0]["role"] == "user"
        assert agent.conversation_history[0]["content"] == "Hello"
    
    def test_clear_memory(self):
        """Test clearing memory"""
        agent = TestAgent("TestAgent", "Test prompt")
        agent.add_to_memory("user", "Hello")
        agent.clear_memory()
        assert len(agent.conversation_history) == 0
    
    def test_register_tool(self):
        """Test tool registration"""
        agent = TestAgent("TestAgent", "Test prompt")
        
        def test_tool(param: str):
            return {"result": param}
        
        schema = {
            "name": "test_tool",
            "description": "Test tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "param": {"type": "string"}
                }
            }
        }
        
        agent.register_tool("test_tool", test_tool, schema)
        assert "test_tool" in agent.tool_registry
        assert len(agent.tools) == 1
    
    @patch('app.services.agents.base_agent.get_openai_client')
    def test_call_llm(self, mock_get_client):
        """Test LLM call"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.tool_calls = None
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        agent = TestAgent("TestAgent", "Test prompt")
        agent.client = mock_client
        
        result = agent.call_llm("Test prompt")
        assert result["content"] == "Test response"
        assert result["role"] == "assistant"
    
    def test_execute_tool_call(self):
        """Test tool execution"""
        agent = TestAgent("TestAgent", "Test prompt")
        
        def test_tool(param: str):
            return {"result": param}
        
        agent.register_tool("test_tool", test_tool, {
            "name": "test_tool",
            "description": "Test"
        })
        
        tool_call = {
            "id": "call_123",
            "name": "test_tool",
            "arguments": {"param": "test_value"}
        }
        
        result = agent.execute_tool_call(tool_call)
        assert result["result"] == "test_value"
    
    def test_get_reasoning_chain(self):
        """Test getting reasoning chain"""
        agent = TestAgent("TestAgent", "Test prompt")
        agent.add_to_memory("user", "Question")
        agent.add_to_memory("assistant", "Answer")
        
        chain = agent.get_reasoning_chain()
        assert len(chain) == 2
        assert chain[0]["role"] == "user"
        assert chain[1]["role"] == "assistant"

