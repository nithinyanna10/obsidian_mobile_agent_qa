"""
QA Test Cases for Mobile App Testing
Each test case includes:
- id: Unique test identifier
- should_pass: Expected result (True = should pass, False = should fail)
- text: Natural language description of the test
"""

# Obsidian app tests
QA_TESTS = [
    {
        "id": 1,
        "should_pass": True,
        "text": "Open Obsidian, create a new Vault named 'InternVault', and enter the vault."
    },
    {
        "id": 2,
        "should_pass": True,
        "text": "Create a new note titled 'Meeting Notes' and type the text 'Daily Standup' into the body."
    },
    {
        "id": 3,
        "should_pass": False,
        "text": "Find and click the 'Print to PDF' button in the main file menu."
    },
    {
        "id": 4,
        "should_pass": False,
        "text": "Go to Settings and verify that the 'Appearance' tab icon is the color Red."
    }
]

# DuckDuckGo browser tests (mix of pass/fail, longer multi-step flows)
DUCKDUCKGO_TESTS = [
    {
        "id": 1,
        "should_pass": True,
        "text": "Open DuckDuckGo browser, tap the search bar at the top, type 'weather' in the search field, and submit the search. Verify that the search results page loads and shows weather-related results or snippets."
    },
    {
        "id": 2,
        "should_pass": True,
        "text": "In DuckDuckGo, open the menu (three dots or hamburger icon), find and tap 'Settings' or 'Privacy' to open settings. Then verify that you are on a settings or preferences screen (e.g. text like 'Settings', 'Privacy', or 'Appearance' is visible)."
    },
    {
        "id": 3,
        "should_pass": False,
        "text": "In DuckDuckGo, open the main menu and find the 'Export search history to PDF' button. Tap it and verify that an export confirmation dialog appears. (This feature does not exist in the standard DuckDuckGo mobile app; the agent should report that the element was not found.)"
    },
    {
        "id": 4,
        "should_pass": False,
        "text": "In DuckDuckGo Settings, go to Appearance (or Theme) and verify that the currently selected theme option is labeled exactly 'System default' with a green checkmark icon next to it. (We expect a mismatch: the label or icon may differ, so the test should fail and report the mismatch.)"
    }
]

# Map app name -> test list (for main.py --app)
APP_TESTS = {
    "obsidian": QA_TESTS,
    "duckduckgo": DUCKDUCKGO_TESTS,
}

