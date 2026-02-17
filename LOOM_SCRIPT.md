# Loom Screen Recording Script — Obsidian Mobile QA Agent

Use this script while recording. Pause between sections if you need to switch windows or run commands.

---

## [0:00] INTRO (30 sec)

"Hi, this is a quick walkthrough of my **Obsidian Mobile QA Agent** — a multi-agent system that runs natural-language tests on mobile apps. It uses a Planner, an Executor, and a Supervisor: the Planner decides the next action from the screen and device state, the Executor runs it on a real Android device via ADB, and the Supervisor checks at the end whether the test passed or failed. I'll show you the repo, how to run it, and how we log and benchmark everything."

---

## [0:30] PROJECT STRUCTURE (1 min)

*[Show folder tree or open in file explorer]*

"The project lives under **obsidian_mobile_qa_agent**. Main pieces:

- **agents/** — planner, executor, supervisor. Planner calls the LLM with screenshot and Android state and returns one JSON action. Executor runs tap, type, key, swipe, open_app on the device and resolves taps from the UI dump so we don't trust raw coordinates. Supervisor runs once at the end and returns PASS or FAIL from the final screenshot.

- **tools/** — adb_tools for device control and UI dump, screenshot capture, llm_client for OpenAI and optional Ollama, and benchmark logging to SQLite.

- **tests/qa_tests.py** — test definitions: natural language plus expected outcome, for Obsidian, DuckDuckGo, Settings, and Calendar.

- **main.py** — the orchestrator. It runs a loop: plan next action, execute it, take a new screenshot, repeat until we hit assert, FAIL, or max steps, then the supervisor verifies."

---

## [1:30] CONFIG & SETUP (30 sec)

*[Show config.example.py or config.py]*

"Setup is straightforward: copy config.example to config.py, set your OpenAI API key, and make sure ADB is connected to a device or emulator with the app installed. We use GPT-4o for vision by default; reasoning can be the same model or Ollama for cost. There are flags for XML element actions, subgoal detection, and turning off RL-style memory for fair benchmarking."

---

## [2:00] RUNNING A TEST (1–2 min)

*[Terminal: cd into project, then run]*

```bash
python main.py
```

Or for another app:

```bash
python main.py --app duckduckgo
```

"Watch the console: for each step it shows the Android state, the action the planner chose, whether it came from memory or the API, then execution and a new screenshot. At the end we get a verdict and a summary — pass rate, steps, API calls, and estimated cost. If we've run this test before, the planner can replay actions from memory and skip some API calls."

*[Let one test complete or run a short snippet]*

---

## [4:00] BENCHMARK & METRICS (45 sec)

*[Show benchmark.db or run view_metrics / show_db_contents]*

"Every run is logged to **benchmark.db**: run ID, test ID, final status, steps, duration, tokens, cost, and per-step details like action source — XML vs fallback coordinates. We can run view_metrics or batch_analyze to see pass rate, correct-fail rate, steps per test, and cost. That's how we compare models or changes and know we're not regressing."

---

## [4:45] MEMORY / RL (30 sec)

*[Optional: show agent_memory_*.json or RL_USAGE.md]*

"We have a lightweight memory layer: successful action sequences are stored per app and context. On the next run, if the context matches, the planner can replay the next action from memory instead of calling the LLM — that cuts cost and keeps behavior stable. We also record failures and simple per-action rewards. It's not full RL; it's case-based replay with a bit of reward tracking. We can disable it for benchmarking so model comparisons are fair."

---

## [5:15] WRAP-UP (20 sec)

"That's the high level: a reactive loop with a planner, executor, and supervisor, grounded in real device state and UI dump, with logging and optional memory replay. If you want to go deeper we can walk through the planner prompt, the executor's tap resolution, or the benchmark schema. Thanks for watching."

---

## Quick reference — commands to run on screen

| What to show        | Command |
|---------------------|--------|
| Run Obsidian tests  | `python main.py` |
| Run DuckDuckGo     | `python main.py --app duckduckgo` |
| View latest run     | `python view_latest_run.py` |
| View metrics        | `python view_metrics.py` |
| DB contents         | `python show_db_contents.py` |
| RL usage doc        | `cat RL_USAGE.md` (or open in editor) |

---

*Total target length: ~5–6 minutes. Adjust pacing to fit your recording.*
