"""
Memory management for agentic AI system.

Tracks conversation history, extracted data, verification results, and reasoning chains.
"""

from typing import Dict, List, Optional, Any
import time
import logging

logger = logging.getLogger(__name__)


class AgentMemory:
    """
    Manages memory for agentic AI system.
    
    Tracks:
    - Conversation history (list of agent actions/decisions)
    - Extracted data state (current candidate/job info)
    - Verification results
    - Reasoning chain (step-by-step decisions)
    - Confidence scores per decision
    """
    
    def __init__(self):
        """Initialize empty memory"""
        self.conversation_history: List[Dict] = []
        self.extracted_data: Dict[str, Any] = {}
        self.verification_results: Dict[str, Any] = {}
        self.reasoning_chain: List[Dict] = []
        self.confidence_scores: Dict[str, float] = {}
        self.timestamps: Dict[str, float] = {}
    
    def add_conversation(self, role: str, content: str, metadata: Optional[Dict] = None):
        """
        Add message to conversation history.
        
        Args:
            role: Message role (system, user, assistant, tool)
            content: Message content
            metadata: Optional metadata
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        self.conversation_history.append(message)
        logger.debug(f"Added conversation: {role}")
    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history.
        
        Args:
            limit: Optional limit on number of messages
        
        Returns:
            List of conversation messages
        """
        if limit:
            return self.conversation_history[-limit:]
        return self.conversation_history.copy()
    
    def store_extracted_data(self, key: str, data: Any, confidence: float = 1.0):
        """
        Store extracted data.
        
        Args:
            key: Data key (e.g., "cv_data", "linkedin_data", "github_data")
            data: Extracted data
            confidence: Confidence score (0.0 to 1.0)
        """
        self.extracted_data[key] = data
        self.confidence_scores[key] = confidence
        self.timestamps[key] = time.time()
        logger.debug(f"Stored extracted data: {key} (confidence: {confidence})")
    
    def get_extracted_data(self, key: str) -> Optional[Any]:
        """
        Get extracted data.
        
        Args:
            key: Data key
        
        Returns:
            Extracted data or None
        """
        return self.extracted_data.get(key)
    
    def get_all_extracted_data(self) -> Dict[str, Any]:
        """Get all extracted data"""
        return self.extracted_data.copy()
    
    def store_verification_result(self, key: str, result: Any, verified: bool):
        """
        Store verification result.
        
        Args:
            key: Verification key (e.g., "github_handle", "skill_evidence")
            result: Verification result
            verified: Whether verification passed
        """
        self.verification_results[key] = {
            "result": result,
            "verified": verified,
            "timestamp": time.time()
        }
        logger.debug(f"Stored verification: {key} (verified: {verified})")
    
    def get_verification_result(self, key: str) -> Optional[Dict]:
        """
        Get verification result.
        
        Args:
            key: Verification key
        
        Returns:
            Verification result or None
        """
        return self.verification_results.get(key)
    
    def add_reasoning_step(self, step: str, reasoning: str, confidence: float = 1.0):
        """
        Add reasoning step to chain.
        
        Args:
            step: Step description
            reasoning: Reasoning explanation
            confidence: Confidence in this reasoning
        """
        reasoning_entry = {
            "step": step,
            "reasoning": reasoning,
            "confidence": confidence,
            "timestamp": time.time()
        }
        self.reasoning_chain.append(reasoning_entry)
        logger.debug(f"Added reasoning step: {step}")
    
    def get_reasoning_chain(self) -> List[Dict]:
        """Get reasoning chain"""
        return self.reasoning_chain.copy()
    
    def set_confidence(self, key: str, confidence: float):
        """
        Set confidence score for a key.
        
        Args:
            key: Key identifier
            confidence: Confidence score (0.0 to 1.0)
        """
        self.confidence_scores[key] = confidence
    
    def get_confidence(self, key: str) -> float:
        """
        Get confidence score for a key.
        
        Args:
            key: Key identifier
        
        Returns:
            Confidence score or 0.0 if not found
        """
        return self.confidence_scores.get(key, 0.0)
    
    def get_all_confidences(self) -> Dict[str, float]:
        """Get all confidence scores"""
        return self.confidence_scores.copy()
    
    def clear(self):
        """Clear all memory"""
        self.conversation_history = []
        self.extracted_data = {}
        self.verification_results = {}
        self.reasoning_chain = []
        self.confidence_scores = {}
        self.timestamps = {}
        logger.info("Memory cleared")
    
    def get_summary(self) -> Dict:
        """
        Get memory summary.
        
        Returns:
            Dictionary with memory statistics
        """
        return {
            "conversation_messages": len(self.conversation_history),
            "extracted_data_keys": list(self.extracted_data.keys()),
            "verification_keys": list(self.verification_results.keys()),
            "reasoning_steps": len(self.reasoning_chain),
            "confidence_scores": self.confidence_scores.copy()
        }

