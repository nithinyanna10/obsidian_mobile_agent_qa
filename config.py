"""
Configuration file for API keys and settings
"""
import os

# OpenAI Configuration (for vision)
# Set OPENAI_API_KEY as environment variable for security
# export OPENAI_API_KEY="your-api-key-here"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")  # Vision model (always OpenAI)

# Reasoning Model Configuration
# Can be OpenAI model or Ollama model
REASONING_MODEL = os.getenv("REASONING_MODEL", "gpt-4o")  # Default to OpenAI
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Obsidian package name
OBSIDIAN_PACKAGE = "md.obsidian"

# Screenshot directory
SCREENSHOTS_DIR = "screenshots"
