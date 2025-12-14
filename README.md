# Obsidian Mobile QA Agent

An automated QA testing system for the Obsidian mobile app using a Supervisor-Planner-Executor architecture with Gemini AI and ADB.

## 🏗️ Project Structure

```
obsidian_mobile_qa_agent/
├── agents/
│   ├── planner.py      # Breaks down test cases into execution steps
│   ├── executor.py     # Executes actions on Android device via ADB
│   └── supervisor.py   # Verifies test results using vision AI
├── tools/
│   ├── adb_tools.py    # ADB command wrappers
│   └── screenshot.py   # Screenshot capture utilities
├── tests/
│   └── qa_tests.py     # Test case definitions
├── screenshots/        # Generated screenshots (created at runtime)
├── main.py             # Main orchestrator
├── config.py           # Configuration (API keys, settings)
├── config.example.py   # Example config file
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## 🚀 Setup

### Prerequisites

1. **Android Device/Emulator** with Obsidian app installed
2. **ADB (Android Debug Bridge)** installed and configured
3. **Python 3.8+**
4. **Gemini API Key** (free from Google AI Studio)

### Installation

1. **Clone/Create the project:**
   ```bash
   cd /Users/nithinyanna/Downloads/obsidian_mobile_qa_agent
   ```

2. **Install/Update dependencies (MANDATORY):**
   ```bash
   # First, upgrade google-generativeai to 0.5.x or newer (REQUIRED)
   pip install --upgrade google-generativeai
   
   # Verify version (must be 0.5.x or newer)
   pip show google-generativeai
   
   # Install other dependencies
   pip install -r requirements.txt
   ```
   
   ⚠️ **IMPORTANT**: If `google-generativeai` is still 0.3.x or 0.4.x, the model WILL NOT WORK.

3. **Restart your Python process:**
   ```bash
   # If using venv, deactivate and reactivate
   deactivate
   source venv/bin/activate
   
   # Or restart your terminal/Cursor kernel
   ```

4. **Test Gemini API access (VERIFY BEFORE RUNNING AGENTS):**
   ```bash
   python3 test_gemini.py
   ```
   
   ✅ **Expected output**: "Hello! 👋" or similar
   
   If this works → your entire agent system will work.

5. **Set up Gemini API Key:**
   
   The API key is already configured in `config.py`. If you need to change it:
   
   - **Option 1**: Edit `config.py` and update `GEMINI_API_KEY`
   - **Option 2**: Set environment variable:
     ```bash
     export GEMINI_API_KEY='your-api-key-here'
     ```
   
   Get your API key from: https://aistudio.google.com/app/apikey

6. **Verify ADB connection:**
   ```bash
   adb devices
   ```
   
   You should see your device listed. If not:
   - Enable USB debugging on your Android device
   - Or start an Android emulator

7. **Verify Obsidian is installed:**
   ```bash
   adb shell pm list packages | grep obsidian
   ```
   
   Should show: `package:md.obsidian`

## 🧪 Test Cases

The system includes 4 test cases with a mix of passing and failing tests:

1. **Test 1 (Should PASS)**: Create a new vault named 'InternVault'
2. **Test 2 (Should PASS)**: Create a new note titled 'Meeting Notes'
3. **Test 3 (Should FAIL)**: Verify 'Appearance' tab icon is Red (should detect mismatch)
4. **Test 4 (Should FAIL)**: Find 'Print to PDF' button (should detect missing element)

## 🏃 Running Tests

```bash
python main.py
```

The system will:
1. **Plan** each test case into executable steps
2. **Execute** each step on the Android device
3. **Verify** results using screenshot analysis
4. **Report** pass/fail status

## 🤖 Agent Architecture

### Planner Agent
- Takes natural language test descriptions
- Uses Gemini LLM to break down into ordered UI actions
- Generates JSON plan with coordinates and actions

### Executor Agent
- Executes planned actions via ADB commands
- Handles taps, typing, key events, swipes
- Captures screenshots after each step

### Supervisor Agent
- Analyzes final screenshots using Gemini Vision
- Determines PASS/FAIL based on test requirements
- Compares actual vs expected results

## 📝 Configuration

### Obsidian Package Name
Default: `md.obsidian`

If your Obsidian installation uses a different package name, update it in:
- `agents/planner.py` (in the prompt)
- `agents/executor.py` (if needed)

### Screen Coordinates
The planner generates approximate coordinates. For better accuracy:
- Use `uiautomator` to find exact element coordinates
- Or refine plans based on screenshots (feature in planner)

## 🔧 Troubleshooting

### ADB not found
```bash
# Install ADB (macOS)
brew install android-platform-tools

# Or download from Android SDK
```

### Device not connected
```bash
# Check connection
adb devices

# Restart ADB server
adb kill-server
adb start-server
```

### API Key issues
- Verify key is set: `echo $GEMINI_API_KEY`
- Check key is valid at Google AI Studio
- Ensure billing/quota is enabled (free tier available)

### Model 404 Error (models/gemini-1.5-flash not found)
If you see "404 models/gemini-1.5-flash is not found", follow these steps **IN ORDER**:

1. **Upgrade the Gemini SDK (MANDATORY):**
   ```bash
   pip install --upgrade google-generativeai
   pip show google-generativeai  # Should show 0.5.x or newer
   ```
   ⚠️ If it's still 0.3.x or 0.4.x, the model WILL NOT WORK.

2. **Restart your Python process:**
   ```bash
   # Deactivate and reactivate venv
   deactivate
   source venv/bin/activate
   # Or restart terminal/Cursor kernel
   ```

3. **Verify model name format:**
   - Must use: `"models/gemini-1.5-flash"` (with "models/" prefix)
   - NOT: `"gemini-1.5-flash"` (without prefix)
   - Check `config.py` has: `GEMINI_MODEL = "models/gemini-1.5-flash"`

4. **Test with minimal script:**
   ```bash
   python3 test_gemini.py
   ```
   ✅ Should output: "Hello! 👋" or similar

5. **If still not working:**
   - Verify API key at https://aistudio.google.com/app/apikey
   - Check package version: `pip show google-generativeai`
   - The system will automatically fall back to `models/gemini-pro` if initialization fails

### Screenshot issues
- Ensure `screenshots/` directory is writable
- Check ADB permissions on device

## 📊 Output

The system generates:
- Console logs with execution progress
- Screenshots in `screenshots/` directory
- Final test summary with pass/fail counts

## 🎯 Extending the System

### Adding New Test Cases
Edit `tests/qa_tests.py`:
```python
{
    "id": 5,
    "should_pass": True,
    "text": "Your test description here"
}
```

### Custom Actions
Add new action types in:
- `agents/planner.py` (update prompt)
- `agents/executor.py` (add handler)
- `tools/adb_tools.py` (add ADB command)

## 📄 License

This project is for educational/demonstration purposes.

## 🤝 Contributing

Feel free to extend and improve the system!

