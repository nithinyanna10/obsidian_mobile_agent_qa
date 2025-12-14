"""
QA Test Cases for Obsidian Mobile App Testing
Each test case includes:
- id: Unique test identifier
- should_pass: Expected result (True = should pass, False = should fail)
- text: Natural language description of the test
"""

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

