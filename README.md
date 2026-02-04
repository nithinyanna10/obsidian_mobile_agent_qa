# Obsidian Mobile QA Agent

An automated QA testing system for the Obsidian mobile app using a **Supervisor–Planner–Executor** architecture: **OpenAI (GPT-4o)** for vision and reasoning, and **ADB** for Android control. The planner uses screenshot + Android state to choose the next action; the executor runs it on device; the supervisor verifies results.

## 🏗️ Project Structure

```
obsidian_mobile_qa_agent/
├── agents/
│   ├── planner.py      # Vision + reasoning → next action (JSON)
│   ├── executor.py     # Runs actions on Android via ADB
│   └── supervisor.py   # Verifies test results (vision + expected)
├── tools/
│   ├── adb_tools.py    # ADB wrappers, UI dump, screen detection
│   ├── screenshot.py  # Screenshot capture
│   ├── llm_client.py   # OpenAI / Ollama / vision + reasoning
│   └── benchmark_*.py  # Benchmark DB and logging
├── tests/
│   └── qa_tests.py     # Test case definitions
├── prompts/
│   └── few_shot_examples.txt
├── main.py             # Orchestrator: run test suite
├── config.py           # OPENAI_API_KEY, OPENAI_MODEL, etc.
├── config.example.py   # Example config (copy to config.py)
├── requirements.txt    # Python dependencies
└── README.md
```

## 🚀 Setup

### Prerequisites

1. **Android device or emulator** with Obsidian installed  
2. **ADB** installed and connected (`adb devices`)  
3. **Python 3.8+**  
4. **OpenAI API key** (for GPT-4o vision and reasoning)

### Installation

1. **Clone or open the project**
   ```bash
   cd obsidian_mobile_qa_agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API key**
   - Copy `config.example.py` to `config.py` and set your key, or  
   - Set the environment variable:
     ```bash
     export OPENAI_API_KEY='your-openai-api-key'
     ```
   Get a key at: https://platform.openai.com/api-keys  

4. **Verify ADB**
   ```bash
   adb devices
   ```
   Device or emulator should be listed.

5. **Verify Obsidian is installed**
   ```bash
   adb shell pm list packages | grep obsidian
   ```
   Should show: `package:md.obsidian`

## 🧪 Test Cases

Four tests (mix of expected pass/fail):

1. **Test 1 (PASS)** – Create a new vault named `InternVault`  
2. **Test 2 (PASS)** – Create a note titled `Meeting Notes` with body `Daily Standup`  
3. **Test 3 (FAIL)** – Verify Appearance tab icon is Red (intended mismatch)  
4. **Test 4 (FAIL)** – Find “Print to PDF” button (missing element)

## 🏃 Running Tests

```bash
python main.py
```

The run will:

1. **Plan** – For each step: vision describes the screenshot, then the reasoning model returns one JSON action.  
2. **Execute** – Executor runs the action on the device (tap, type, key, swipe, etc.).  
3. **Verify** – Supervisor checks outcome vs expected (PASS/FAIL).  
4. **Report** – Console summary and optional benchmark DB (see `view_latest_run.py`).

## 🤖 Agent Architecture

- **Planner** – Two-step: (1) OpenAI Vision describes the screenshot, (2) reasoning model (default same as vision, e.g. GPT-4o) returns a single JSON action using screenshot description + Android state (current_screen, input fields, buttons). Uses few-shot examples and optional RL/subgoal hints.  
- **Executor** – Runs actions via ADB (tap, type, focus, key, swipe, wait, open_app). Can use UIAutomator to resolve (0,0) taps to elements. Captures screenshots and optional UI dumps.  
- **Supervisor** – Compares final state (screenshot + UI) to test expectation and marks PASS/FAIL.

## 📝 Prompts

- **Vision prompt** – Asks the model to describe the mobile app screenshot (screen/UI, buttons, text fields, on-screen text). Used in `agents/planner.py` for the first step of each planning cycle.
- **Reasoning prompt** – Includes Android state (current_screen, input fields, buttons), test goal, action history, and few-shot examples; asks for a single JSON action. Used in `agents/planner.py` for the second step.
- **Few-shot examples** – Stored in `prompts/few_shot_examples.txt`; loaded and appended to the reasoning prompt. Edit this file to add or change example action sequences (e.g. create vault, create note, open Settings).
- To change planner behavior, edit the prompts in `agents/planner.py` and/or `prompts/few_shot_examples.txt`.

## 📝 Configuration

In `config.py` (or env):

- **OPENAI_API_KEY** – Required for vision and default reasoning.  
- **OPENAI_MODEL** – Vision model (default `gpt-4o`).  
- **REASONING_MODEL** – Defaults to `OPENAI_MODEL`; can set to an Ollama model name for local reasoning.  
- **OBSIDIAN_PACKAGE** – `md.obsidian`.  
- **USE_FUNCTION_CALLING**, **ENABLE_SUBGOAL_DETECTION**, **USE_REWARD_SELECTION**, **DISABLE_RL_FOR_BENCHMARKING** – Optional behavior flags.

See `config.example.py` for a minimal template.

## 🔧 Troubleshooting

**ADB not found**
```bash
# macOS
brew install android-platform-tools
```

**Device not connected**
```bash
adb devices
adb kill-server && adb start-server
```

**OpenAI API**
- Ensure `OPENAI_API_KEY` is set: `echo $OPENAI_API_KEY`  
- Check usage/billing at https://platform.openai.com  

**Screenshots / permissions**
- Ensure `screenshots/` is writable.  
- Check ADB can capture screen on the device/emulator.

## 📊 Output

- Console: step-by-step logs and final pass/fail summary.  
- Screenshots in `screenshots/`.  
- Optional: benchmark DB and run viewer (`view_latest_run.py`, `view_latest_suite.py`).

## 🎯 Extending

- **New tests** – Add entries in `tests/qa_tests.py` (id, should_pass, text).  
- **New actions** – Implement in `agents/executor.py`, expose in planner prompt / schema.  
- **Other apps** – Change `OBSIDIAN_PACKAGE` and adjust test goals; planner prompts are app-agnostic.

## 📄 License

For educational and demonstration use.
