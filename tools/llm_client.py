"""
Unified LLM Client - Supports OpenAI and Ollama APIs
Separates vision (OpenAI) from reasoning (configurable)
"""
import os
import requests
import json
from typing import Optional, Dict, Any, List
from openai import OpenAI as OpenAIClient


class LLMClient:
    """Unified client for calling different LLM providers"""
    
    def __init__(self, vision_model: str = "gpt-4o", reasoning_model: str = None, vision_api_key: str = None, reasoning_api_key: str = None, reasoning_base_url: str = None):
        """
        Initialize LLM client
        
        Args:
            vision_model: Model for vision tasks (default: gpt-4o)
            reasoning_model: Model for reasoning/planning (default: same as vision)
            vision_api_key: API key for vision provider
            reasoning_api_key: API key for reasoning provider (if different)
            reasoning_base_url: Base URL for reasoning provider (e.g., Ollama)
        """
        self.vision_model = vision_model
        self.reasoning_model = reasoning_model or vision_model
        
        # Initialize OpenAI client for vision (always OpenAI)
        self.vision_client = OpenAIClient(api_key=vision_api_key or os.getenv("OPENAI_API_KEY", ""))
        
        # Initialize reasoning client based on model
        # Detect Ollama models: contains ":" (e.g., "nemotron-3-nano:30b-cloud", "gemini-3-flash-preview:cloud") or "ollama" in name
        if reasoning_base_url or ":" in self.reasoning_model or "ollama" in self.reasoning_model.lower():
            # Ollama model (includes cloud models accessed via Ollama like nemotron, gemini, etc.)
            self.reasoning_base_url = reasoning_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            self.reasoning_provider = "ollama"
        elif self.reasoning_model.startswith("gpt-") or self.reasoning_model.startswith("o1-") or self.reasoning_model.startswith("o3-"):
            # OpenAI model
            self.reasoning_client = OpenAIClient(api_key=reasoning_api_key or os.getenv("OPENAI_API_KEY", ""))
            self.reasoning_provider = "openai"
        elif "gemini" in self.reasoning_model.lower():
            # Google Gemini model (if accessed directly via Google API, not Ollama)
            # For now, if it has ":" it's already handled as Ollama above
            # If no ":", we'll default to OpenAI format (may need Google API client later)
            self.reasoning_client = OpenAIClient(api_key=reasoning_api_key or os.getenv("OPENAI_API_KEY", ""))
            self.reasoning_provider = "openai"  # Fallback, but should be Ollama if has ":"
        else:
            # Default to OpenAI
            self.reasoning_client = OpenAIClient(api_key=reasoning_api_key or os.getenv("OPENAI_API_KEY", ""))
            self.reasoning_provider = "openai"
    
    def call_vision(self, messages: List[Dict], logger=None, **kwargs):
        """
        Call vision API (always OpenAI GPT-4o)
        
        Args:
            messages: Messages with image_url content
            logger: Optional BenchmarkLogger
            **kwargs: Additional arguments
        
        Returns:
            API response
        """
        response = self.vision_client.chat.completions.create(
            model=self.vision_model,
            messages=messages,
            **kwargs
        )
        
        # Log API call
        if logger:
            tokens_in = 0
            tokens_out = 0
            if hasattr(response, 'usage') and response.usage:
                tokens_in = getattr(response.usage, 'prompt_tokens', 0) or getattr(response.usage, 'input_tokens', 0) or 0
                tokens_out = getattr(response.usage, 'completion_tokens', 0) or getattr(response.usage, 'output_tokens', 0) or 0
            
            logger.log_api_call(
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                model=self.vision_model
            )
        
        return response
    
    def call_reasoning(self, messages: List[Dict], logger=None, **kwargs):
        """
        Call reasoning API (configurable: OpenAI or Ollama)
        
        Args:
            messages: Messages (text only, no images)
            logger: Optional BenchmarkLogger
            **kwargs: Additional arguments
        
        Returns:
            API response
        """
        if self.reasoning_provider == "ollama":
            return self._call_ollama(messages, logger, **kwargs)
        else:
            return self._call_openai_reasoning(messages, logger, **kwargs)
    
    def _call_openai_reasoning(self, messages: List[Dict], logger=None, **kwargs):
        """Call OpenAI for reasoning"""
        response = self.reasoning_client.chat.completions.create(
            model=self.reasoning_model,
            messages=messages,
            **kwargs
        )
        
        # Log API call
        if logger:
            tokens_in = 0
            tokens_out = 0
            if hasattr(response, 'usage') and response.usage:
                tokens_in = getattr(response.usage, 'prompt_tokens', 0) or getattr(response.usage, 'input_tokens', 0) or 0
                tokens_out = getattr(response.usage, 'completion_tokens', 0) or getattr(response.usage, 'output_tokens', 0) or 0
            
            logger.log_api_call(
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                model=self.reasoning_model
            )
        
        return response
    
    def _call_ollama(self, messages: List[Dict], logger=None, **kwargs):
        """Call Ollama API"""
        # Extract model name (remove "ollama" prefix if present)
        model_name = self.reasoning_model.replace("ollama:", "").replace("ollama-", "")
        
        # Convert messages to Ollama format
        # Ollama expects: {"model": "...", "messages": [...], "stream": False}
        ollama_payload = {
            "model": model_name,
            "messages": messages,
            "stream": False
        }
        
        # Add kwargs
        if "temperature" in kwargs:
            ollama_payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            ollama_payload["num_predict"] = kwargs["max_tokens"]
        
        # Call Ollama API
        url = f"{self.reasoning_base_url}/api/chat"
        response = requests.post(url, json=ollama_payload, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        
        # Convert to OpenAI-like response format
        class OllamaResponse:
            def __init__(self, ollama_result):
                self.choices = [type('obj', (object,), {
                    'message': type('obj', (object,), {
                        'content': ollama_result.get('message', {}).get('content', '')
                    })()
                })()]
                
                # Ollama provides token counts in response.eval_count and response.prompt_eval_count
                # But these might not be in the response, so estimate if not available
                if 'prompt_eval_count' in ollama_result and 'eval_count' in ollama_result:
                    estimated_tokens_in = ollama_result.get('prompt_eval_count', 0)
                    estimated_tokens_out = ollama_result.get('eval_count', 0)
                else:
                    # Fallback: estimate from message length
                    prompt_text = " ".join([msg.get("content", "") if isinstance(msg.get("content"), str) else str(msg.get("content", "")) for msg in messages])
                    completion_text = ollama_result.get('message', {}).get('content', '')
                    # Rough estimate: 1 token ≈ 4 characters for English text
                    estimated_tokens_in = len(prompt_text) // 4
                    estimated_tokens_out = len(completion_text) // 4
                
                class Usage:
                    def __init__(self, prompt_tokens, completion_tokens):
                        self.prompt_tokens = prompt_tokens
                        self.completion_tokens = completion_tokens
                        self.input_tokens = prompt_tokens
                        self.output_tokens = completion_tokens
                
                self.usage = Usage(estimated_tokens_in, estimated_tokens_out)
        
        response_obj = OllamaResponse(result)
        
        # Log API call
        if logger:
            logger.log_api_call(
                tokens_in=response_obj.usage.prompt_tokens,
                tokens_out=response_obj.usage.completion_tokens,
                model=self.reasoning_model
            )
        
        return response_obj

