"""
MobileRL Client - MAI-UI-2B Integration
Unified vision-language model for mobile GUI agents

MAI-UI supports vision and is designed to be used via vLLM as OpenAI-compatible API.
This client supports both:
1. vLLM API (recommended) - Set MOBILERL_VLLM_URL environment variable
2. Transformers pipeline (fallback) - Direct model loading
"""
import os
import base64
import torch
from PIL import Image
import json
import re
from typing import Optional, Dict, Any, List
import time
import requests

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️  transformers not installed. Install with: pip install transformers torch")

try:
    from openai import OpenAI as OpenAIClient
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  openai not installed. Install with: pip install openai")


class MobileRLClient:
    """Client for MAI-UI-2B model via vLLM API (recommended) or HuggingFace pipeline (fallback)"""
    
    def __init__(self, model_name: str = "Tongyi-MAI/MAI-UI-2B", device: str = None, vllm_url: str = None, vllm_model_name: str = None):
        """
        Initialize MobileRL client
        
        Args:
            model_name: HuggingFace model identifier (for direct loading if vLLM not used)
                       Default: "Tongyi-MAI/MAI-UI-2B" (2B model - smaller and faster)
            device: Device to use ("cuda", "cpu", or None for auto) - only for direct loading
            vllm_url: vLLM server URL (e.g., "http://localhost:8000/v1") - recommended approach
            vllm_model_name: Model name as served by vLLM (e.g., "MAI-UI-2B")
        """
        self.model_name = model_name
        self.vllm_url = vllm_url or os.getenv("MOBILERL_VLLM_URL", None)
        self.vllm_model_name = vllm_model_name or os.getenv("MOBILERL_VLLM_MODEL_NAME", "MAI-UI-2B")
        
        # Determine mode: vLLM API (preferred) or direct transformers
        if self.vllm_url:
            # Use vLLM API (OpenAI-compatible)
            if not OPENAI_AVAILABLE:
                raise ImportError("openai library required for vLLM API. Install with: pip install openai")
            self.mode = "vllm"
            self.client = OpenAIClient(base_url=self.vllm_url, api_key="dummy")  # vLLM doesn't need real API key
            print(f"📦 MobileRL Client initialized for {model_name}")
            print(f"   Mode: vLLM API ({self.vllm_url})")
            print(f"   Model: {self.vllm_model_name}")
        else:
            # Use direct transformers pipeline (fallback)
            if not TRANSFORMERS_AVAILABLE:
                raise ImportError("transformers library not installed. Install with: pip install transformers torch")
            self.mode = "direct"
            # Auto-detect best device: CUDA > CPU (skip MPS due to unsupported operations)
            if device:
                self.device = device
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"  # Default to CPU (MPS has compatibility issues)
            self.pipe = None
            self._loaded = False
            print(f"📦 MobileRL Client initialized for {model_name}")
            print(f"   Mode: Direct transformers pipeline")
            device_desc = "CUDA GPU" if self.device == "cuda" else "CPU"
            print(f"   Device: {self.device} ({device_desc})")
            print(f"   ⚠️  Note: vLLM API is recommended. Set MOBILERL_VLLM_URL to use vLLM.")
    
    def load_model(self):
        """Lazy load the model (only when first used)"""
        if self._loaded:
            return
        
        model_size = "~4GB" if "2B" in self.model_name else "~8GB" if "8B" in self.model_name else "~20GB"
        print(f"🔄 Loading {self.model_name} model ({model_size})...")
        if self.device == "cuda":
            print(f"   GPU: Should load in ~10-30 seconds")
        else:
            print(f"   CPU: May take 30-90 seconds (Mac M4 Pro: ~30-60 seconds)")
        print(f"   Model will be cached after first load for faster subsequent runs")
        start_time = time.time()
        
        try:
            # Use pipeline as a high-level helper
            # Pipeline automatically handles model caching
            # Map device for pipeline (CPU only - MPS has compatibility issues)
            if self.device == "cuda":
                device_map = 0
                dtype = torch.float16
            else:
                device_map = -1  # CPU
                dtype = torch.float32
            
            # Load model (CPU mode for compatibility)
            self.pipe = pipeline(
                "image-text-to-text",
                model=self.model_name,
                device=device_map,
                model_kwargs={"dtype": dtype}  # Use 'dtype' instead of deprecated 'torch_dtype'
            )
            
            self._loaded = True
            
            load_time = time.time() - start_time
            minutes = int(load_time // 60)
            seconds = int(load_time % 60)
            if minutes > 0:
                print(f"✓ Model loaded in {minutes}m {seconds}s")
            else:
                print(f"✓ Model loaded in {seconds}s")
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    
    def call_unified(self, screenshot_path: str, prompt: str, logger=None, **kwargs) -> Dict[str, Any]:
        """
        Unified vision+reasoning call - analyzes screenshot and returns action
        
        Args:
            screenshot_path: Path to screenshot image
            prompt: Text prompt describing the task
            logger: Optional BenchmarkLogger for tracking
            **kwargs: Additional arguments (temperature, max_tokens, etc.)
        
        Returns:
            Dictionary with action in format: {"action": "tap", "x": 100, "y": 200, "description": "..."}
        """
        if self.mode == "vllm":
            return self._call_vllm(screenshot_path, prompt, logger, **kwargs)
        else:
            return self._call_direct(screenshot_path, prompt, logger, **kwargs)
    
    def _call_vllm(self, screenshot_path: str, prompt: str, logger=None, **kwargs) -> Dict[str, Any]:
        """Call MAI-UI via vLLM API (OpenAI-compatible)"""
        # Load and encode image
        try:
            with open(screenshot_path, "rb") as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode("utf-8")
        except Exception as e:
            raise ValueError(f"Failed to load screenshot: {e}")
        
        # Prepare messages in OpenAI format with vision
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
        
        # Call vLLM API
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.vllm_model_name,
                messages=messages,
                **kwargs
            )
            
            generated_text = response.choices[0].message.content
            inference_time = time.time() - start_time
            
        except Exception as e:
            raise RuntimeError(f"vLLM API call failed: {e}")
        
        # Parse response to extract action
        action = self._parse_response(generated_text, prompt)
        
        # Log if logger provided
        if logger:
            tokens_in = 0
            tokens_out = 0
            if hasattr(response, 'usage') and response.usage:
                tokens_in = getattr(response.usage, 'prompt_tokens', 0) or 0
                tokens_out = getattr(response.usage, 'completion_tokens', 0) or 0
            
            logger.log_api_call(
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                model=f"mobilerl-vllm-{self.vllm_model_name}"
            )
        
        return action
    
    def _call_direct(self, screenshot_path: str, prompt: str, logger=None, **kwargs) -> Dict[str, Any]:
        """Call MAI-UI via direct transformers pipeline (fallback)"""
        if not self._loaded:
            self.load_model()
        
        # Load and prepare image
        try:
            image = Image.open(screenshot_path).convert("RGB")
        except Exception as e:
            raise ValueError(f"Failed to load screenshot: {e}")
        
        # Prepare messages for pipeline format
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},  # PIL Image object
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        # Generate response using pipeline
        start_time = time.time()
        
        try:
            # Pipeline expects messages format
            result = self.pipe(text=messages)
            
            # Extract generated text from pipeline result
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict):
                    generated_text = result[0].get("generated_text", result[0].get("text", str(result[0])))
                else:
                    generated_text = str(result[0])
            elif isinstance(result, dict):
                generated_text = result.get("generated_text", result.get("text", str(result)))
            else:
                generated_text = str(result)
            
            inference_time = time.time() - start_time
            
        except Exception as e:
            raise RuntimeError(f"Model generation failed: {e}")
        
        # Parse response to extract action
        action = self._parse_response(generated_text, prompt)
        
        # Log if logger provided
        if logger:
            # Estimate tokens (rough approximation: 1 token ≈ 4 chars)
            input_tokens = len(prompt) // 4
            output_tokens = len(generated_text) // 4
            
            logger.log_api_call(
                tokens_in=input_tokens,
                tokens_out=output_tokens,
                model=f"mobilerl-{self.model_name}"
            )
        
        return action
    
    def _parse_response(self, response_text: str, original_prompt: str) -> Dict[str, Any]:
        """
        Parse model response to extract action in our format
        
        Expected format: {"action": "tap", "x": 100, "y": 200, "description": "..."}
        """
        # Try to extract JSON from response
        # Look for JSON block in the response
        json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response_text, re.DOTALL)
        
        if json_match:
            try:
                action_json = json.loads(json_match.group(0))
                # Validate and normalize
                if "action" in action_json:
                    return {
                        "action": action_json.get("action", "tap"),
                        "x": action_json.get("x", 0),
                        "y": action_json.get("y", 0),
                        "description": action_json.get("description", "Action from MAI-UI-2B")
                    }
            except json.JSONDecodeError:
                pass
        
        # Fallback: Try to extract coordinates from text
        coord_match = re.search(r'\((\d+),\s*(\d+)\)', response_text)
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            return {
                "action": "tap",
                "x": x,
                "y": y,
                "description": f"Tap at ({x}, {y}) - parsed from MAI-UI response"
            }
        
        # Last resort: Return a wait action
        print(f"⚠️  Could not parse MAI-UI response, using fallback")
        print(f"   Response: {response_text[:200]}...")
        return {
            "action": "wait",
            "seconds": 1,
            "description": "Waiting - MAI-UI response parsing failed"
        }


# Global instance (lazy loaded)
_mobilerl_client = None

def get_mobilerl_client(model_name: str = None, device: str = None, vllm_url: str = None, vllm_model_name: str = None) -> MobileRLClient:
    """Get or create global MobileRL client instance"""
    global _mobilerl_client
    
    if _mobilerl_client is None:
        model = model_name or os.getenv("MOBILERL_MODEL", "Tongyi-MAI/MAI-UI-2B")
        dev = device or os.getenv("MOBILERL_DEVICE", None)
        vllm = vllm_url or os.getenv("MOBILERL_VLLM_URL", None)
        vllm_name = vllm_model_name or os.getenv("MOBILERL_VLLM_MODEL_NAME", "MAI-UI-2B")
        _mobilerl_client = MobileRLClient(model_name=model, device=dev, vllm_url=vllm, vllm_model_name=vllm_name)
    
    return _mobilerl_client
