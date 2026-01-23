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

# Function calling support (for structured output)
USE_FUNCTION_CALLING = os.getenv("USE_FUNCTION_CALLING", "false").lower() == "true"

# Subgoal detection
ENABLE_SUBGOAL_DETECTION = os.getenv("ENABLE_SUBGOAL_DETECTION", "true").lower() == "true"

# Reward-based action selection
USE_REWARD_SELECTION = os.getenv("USE_REWARD_SELECTION", "true").lower() == "true"

# Disable RL pattern matching for benchmarking (ensures fair model comparison)
DISABLE_RL_FOR_BENCHMARKING = os.getenv("DISABLE_RL_FOR_BENCHMARKING", "true").lower() == "true"
