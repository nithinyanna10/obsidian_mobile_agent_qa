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
        "text": "Go to Settings and verify that the 'Appearance' tab icon is the color Red."
    },
    {
        "id": 4,
        "should_pass": False,
        "text": "Find and click the 'Print to PDF' button in the main file menu."
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

# Android Settings app tests (mix of pass/fail; no sign-in required)
SETTINGS_TESTS = [
    {
        "id": 1,
        "should_pass": True,
        "text": "Open Android Settings and verify that you are on the main Settings screen (e.g. text like 'Network', 'Connected devices', 'Apps', 'Notifications', or 'Display' is visible)."
    },
    {
        "id": 2,
        "should_pass": True,
        "text": "In Android Settings, tap on 'Notifications' or 'Apps' (or 'Apps & notifications') and verify that the sub-screen opens and shows a list or options."
    },
    {
        "id": 3,
        "should_pass": False,
        "text": "In Android Settings, find and tap the 'Export all settings to PDF' button. (This option does not exist; the agent should report that the element was not found.)"
    },
    {
        "id": 4,
        "should_pass": False,
        "text": "Go to Settings > Display (or Display & brightness) and verify that the brightness control is labeled exactly 'Brightness' in purple text. (We expect a mismatch: the label or color may differ, so the test should fail and report the mismatch.)"
    }
]

# Calendar app tests (mix of pass/fail; includes opening Settings and scrolling in Settings)
CALENDAR_TESTS = [
    {
        "id": 1,
        "should_pass": True,
        "text": "Open the calendar app. Once you see the main calendar view—month view with dates and a search bar or gear icon at the top—immediately return assert (do not open Settings or tap anything else; the goal is only to confirm the main view is visible)."
    },
    {
        "id": 2,
        "should_pass": True,
        "text": "Tap the Settings (gear) icon to open the calendar's Settings screen. Do NOT tap section headers like 'Look & feel' or 'General'—they are not buttons. Scroll down slowly (use swipe up repeatedly) until you reach the very end of the Settings list. At the end, verify that the last visible option is 'Import settings' and report that name. The goal is to scroll to the bottom and retrieve/confirm the last button name: 'Import settings'."
    },
    {
        "id": 3,
        "should_pass": False,
        "text": "From the calendar main screen, open the three-dot or 'More options' menu and find the 'Print to PDF' button. Tap it and verify a print dialog appears. (This option does not exist in the standard calendar app; the agent should report that the element was not found.)"
    },
    {
        "id": 4,
        "should_pass": False,
        "text": "In the calendar app Settings, find the 'Use 24-hour time format' option and verify that its toggle is labeled exactly '24-hour' in green text. (We expect a mismatch: the label or color may differ, so the test should fail and report the mismatch.)"
    }
]

# Map app name -> test list (for main.py --app)
APP_TESTS = {
    "obsidian": QA_TESTS,
    "duckduckgo": DUCKDUCKGO_TESTS,
    "settings": SETTINGS_TESTS,
    "calendar": CALENDAR_TESTS,
}