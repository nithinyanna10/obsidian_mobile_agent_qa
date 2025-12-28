"""
Configuration file for API keys and settings
"""
import os

# Ollama Configuration
# Ollama runs locally, no API key needed
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Vision model for screenshot analysis (has image reading capabilities)
OLLAMA_VISION_MODEL = "qwen3-vl:8b"

# Text model for non-vision tasks (if needed)
OLLAMA_TEXT_MODEL = "gpt-oss:120b-cloud"

# LLM Approach: "single" (vision model does everything) or "two-model" (vision describes, text plans)
# "two-model" is recommended for better JSON output
OLLAMA_APPROACH = "two-model"  # Options: "single" or "two-model"

# Obsidian package name
OBSIDIAN_PACKAGE = "md.obsidian"

# Screenshot directory
SCREENSHOTS_DIR = "screenshots"
