"""
Configuration file for API keys and settings
"""
import os

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Obsidian package name
OBSIDIAN_PACKAGE = "md.obsidian"

# Screenshot directory
SCREENSHOTS_DIR = "screenshots"
