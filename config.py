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
# Default: same as vision model (use OpenAI for both). Set REASONING_MODEL to override (e.g. Ollama).
REASONING_MODEL = os.getenv("REASONING_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# App package names
OBSIDIAN_PACKAGE = "md.obsidian"
DUCKDUCKGO_PACKAGE = "com.duckduckgo.mobile.android"
SETTINGS_PACKAGE = "com.android.settings"
# Calendar app (Fossify Calendar, Google Calendar, etc. - set to your installed app's package)
CALENDAR_PACKAGE = os.getenv("CALENDAR_PACKAGE", "org.fossify.calendar")

# Target app for this run (set by main.py when using --app)
# Read at runtime so main can set os.environ before first use
def get_target_package():
    return os.getenv("TARGET_PACKAGE", OBSIDIAN_PACKAGE)

# Screenshot directory
SCREENSHOTS_DIR = "screenshots"

# Function calling support (for structured output)
USE_FUNCTION_CALLING = os.getenv("USE_FUNCTION_CALLING", "false").lower() == "true"

# Subgoal detection
ENABLE_SUBGOAL_DETECTION = os.getenv("ENABLE_SUBGOAL_DETECTION", "true").lower() == "true"

# Reward-based action selection
USE_REWARD_SELECTION = os.getenv("USE_REWARD_SELECTION", "true").lower() == "true"

# Disable RL pattern matching for benchmarking (set to "true" for fair model comparison)
DISABLE_RL_FOR_BENCHMARKING = os.getenv("DISABLE_RL_FOR_BENCHMARKING", "false").lower() == "true"

# Phase 1/2: Use XML element list at every step; LLM returns tap/type by element text, executor resolves from XML
USE_XML_ELEMENT_ACTIONS = os.getenv("USE_XML_ELEMENT_ACTIONS", "true").lower() == "true"
