"""
Configuration file for API keys and settings
"""
import os

# OpenAI Configuration
# Set OPENAI_API_KEY as environment variable for security
# export OPENAI_API_KEY="your-api-key-here"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Obsidian package name
OBSIDIAN_PACKAGE = "md.obsidian"

# Screenshot directory
SCREENSHOTS_DIR = "screenshots"
