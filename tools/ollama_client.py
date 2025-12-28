"""
Ollama API Client for Vision and Text Models
Handles communication with local Ollama instance
"""
import requests
import json
import base64
import time
from PIL import Image
import io
import os
import sys

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OLLAMA_BASE_URL, OLLAMA_VISION_MODEL, OLLAMA_TEXT_MODEL


def call_ollama_vision(prompt, image_path=None, image_base64=None, model=None, max_retries=3, temperature=0.1):
    """
    Call Ollama vision model (qwen3-vl:8b) with image
    
    Args:
        prompt: Text prompt
        image_path: Path to image file (optional, if image_base64 not provided)
        image_base64: Base64 encoded image (optional, if image_path not provided)
        model: Model name (defaults to OLLAMA_VISION_MODEL)
        max_retries: Maximum retry attempts
        temperature: Temperature for generation
    
    Returns:
        Response text from model
    """
    model = model or OLLAMA_VISION_MODEL
    
    # Prepare image data
    if image_base64:
        image_data = image_base64
    elif image_path:
        # Read and encode image
        img = Image.open(image_path)
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        image_data = base64.b64encode(img_buffer.read()).decode('utf-8')
    else:
        raise ValueError("Either image_path or image_base64 must be provided")
    
    # For Ollama vision models, we use the /api/chat endpoint with images
    # qwen3-vl supports images in the messages format
    import time as time_module
    start_time = time_module.time()
    
    for attempt in range(max_retries):
        try:
            # Ollama chat API endpoint (supports vision models)
            url = f"{OLLAMA_BASE_URL}/api/chat"
            
            # Build messages with image - Ollama expects images as base64 strings in an array
            messages = [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_data]  # Base64 image data (without data:image/png;base64, prefix)
                }
            ]
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            
            # Timeout for vision models - qwen3-vl:8b can be slow on CPU
            # qwen3-vl:8b typically takes 5-10 minutes on CPU, 30-60s on GPU
            print(f"  ⏱️  Starting screenshot analysis (this may take 5-10 minutes with {model} on CPU)...")
            response = requests.post(url, json=payload, timeout=600)  # 10 minutes for qwen3-vl:8b
            response.raise_for_status()
            
            elapsed_time = time_module.time() - start_time
            print(f"  ⏱️  Screenshot analysis completed in {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
            
            result = response.json()
            
            # Debug: Print result structure if empty
            if not result:
                print(f"  ⚠️  Ollama returned empty result")
                if attempt < max_retries - 1:
                    print(f"  ⚠️  Retrying... ({attempt + 1}/{max_retries})")
                    time.sleep(2.0 * (attempt + 1))
                    continue
                return ""
            
            # Extract response from message content - Ollama chat API format
            # Response structure: {"message": {"content": "...", "role": "assistant"}, "done": true, ...}
            if "message" in result:
                message = result["message"]
                if isinstance(message, dict):
                    content = message.get("content")
                    # Check if content exists
                    if content is not None:
                        content_str = str(content).strip()
                        if content_str:  # Only return if non-empty
                            return content_str
                    # If content is None or empty, check if done
                    if result.get("done", False):
                        # Model finished but no content - might be an error or empty response
                        if content is None or content == "":
                            if attempt < max_retries - 1:
                                print(f"  ⚠️  Model returned empty content (done=True), retrying... ({attempt + 1}/{max_retries})")
                                time.sleep(2.0 * (attempt + 1))
                                continue
                            # Debug: print what we got
                            print(f"  ⚠️  Response structure: {list(result.keys())}")
                            print(f"  ⚠️  Message keys: {list(message.keys()) if isinstance(message, dict) else 'N/A'}")
                            return ""
                elif isinstance(message, str):
                    return message.strip()
            
            # Fallback: check for "response" field (for /api/generate endpoint)
            if "response" in result:
                response_text = result["response"]
                if response_text:
                    return str(response_text).strip()
            
            # Check if there's an error
            if "error" in result:
                error_msg = result["error"]
                raise Exception(f"Ollama API error: {error_msg}")
            
            # If done is True but no content, model finished with no output
            if result.get("done", False):
                print(f"  ⚠️  Model finished but no content found")
                return ""
            
            # Last resort: print debug info
            print(f"  ⚠️  Could not extract content. Response keys: {list(result.keys())}")
            if attempt < max_retries - 1:
                print(f"  ⚠️  Retrying... ({attempt + 1}/{max_retries})")
                time.sleep(2.0 * (attempt + 1))
                continue
            return ""
            
        except requests.exceptions.Timeout as e:
            # Timeout is common with vision models - they're slow
            error_str = str(e)
            if attempt < max_retries - 1:
                wait_time = 5.0 * (attempt + 1)  # Longer wait for timeouts
                print(f"  ⚠️  Ollama timeout (model is slow). Waiting {wait_time:.2f}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
                continue
            else:
                print(f"  ❌ Ollama API timed out after {max_retries} attempts")
                print(f"  💡 Vision models can be slow. Try:")
                print(f"     - Using a faster/smaller model")
                print(f"     - Reducing image size")
                print(f"     - Using GPU acceleration if available")
                raise Exception(f"Ollama API timeout after {max_retries} attempts: {error_str}")
        except requests.exceptions.RequestException as e:
            error_str = str(e)
            if attempt < max_retries - 1:
                wait_time = 2.0 * (attempt + 1)  # Exponential backoff
                print(f"  ⚠️  Ollama API error: {error_str}")
                print(f"  ⚠️  Waiting {wait_time:.2f}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
                continue
            else:
                print(f"  ❌ Ollama API call failed after {max_retries} attempts: {error_str}")
                raise Exception(f"Ollama API call failed after {max_retries} attempts: {error_str}")
        except Exception as e:
            error_str = str(e)
            if attempt < max_retries - 1:
                wait_time = 2.0 * (attempt + 1)
                print(f"  ⚠️  Unexpected error: {error_str}")
                print(f"  ⚠️  Waiting {wait_time:.2f}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
                continue
            else:
                print(f"  ❌ Unexpected error after {max_retries} attempts: {error_str}")
                raise
    
    return ""


def call_ollama_chat(messages, model=None, max_retries=3, temperature=0.1):
    """
    Call Ollama chat API (for text-only tasks)
    
    Args:
        messages: List of message dicts with "role" and "content"
        model: Model name (defaults to OLLAMA_TEXT_MODEL)
        max_retries: Maximum retry attempts
        temperature: Temperature for generation
    
    Returns:
        Response text from model
    """
    model = model or OLLAMA_TEXT_MODEL
    
    for attempt in range(max_retries):
        try:
            # Ollama chat API endpoint
            url = f"{OLLAMA_BASE_URL}/api/chat"
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            return result.get("message", {}).get("content", "").strip()
            
        except requests.exceptions.RequestException as e:
            error_str = str(e)
            if attempt < max_retries - 1:
                wait_time = 2.0 * (attempt + 1)  # Exponential backoff
                print(f"  ⚠️  Ollama API error, waiting {wait_time:.2f}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
                continue
            else:
                raise Exception(f"Ollama API call failed after {max_retries} attempts: {error_str}")
    
    return ""


def check_ollama_connection():
    """
    Check if Ollama is running and accessible
    
    Returns:
        True if Ollama is accessible, False otherwise
    """
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

