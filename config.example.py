"""
Configuration file for API keys and settings
Copy this file to config.py and fill in your API key
"""
import os

# OpenAI API Key
# You can set it here or via environment variable OPENAI_API_KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_API_KEY_HERE")

# Obsidian package name
OBSIDIAN_PACKAGE = "md.obsidian"

# Screenshot directory
SCREENSHOTS_DIR = "screenshots"

# OpenAI model name
# Options: "gpt-4o" (better quality, more expensive), "gpt-4o-mini" (faster, cheaper)
# Both support vision (screenshot analysis)
OPENAI_MODEL = "gpt-4o-mini"

