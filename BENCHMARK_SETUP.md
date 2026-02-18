# Multi-LLM Benchmarking Setup

## Overview

This system supports benchmarking different reasoning models while keeping vision fixed to OpenAI GPT-4o.

## Architecture

- **Vision Model**: Always OpenAI GPT-4o (for analyzing screenshots)
- **Reasoning Model**: Configurable (OpenAI or Ollama via API)

## Running Benchmarks

### For Ollama Models (e.g., nemotron-3-nano:30b-cloud)

1. **Start Ollama locally** (if not already running):
   ```bash
   ollama serve
   ```

2. **Pull the model** (if not already pulled):
   ```bash
   ollama pull nemotron-3-nano:30b-cloud
   ```

3. **Run benchmark** (5 trials):
   ```bash
   python run_benchmark_model.py --reasoning-model nemotron-3-nano:30b-cloud --trials 5
   ```

### For OpenAI Models

```bash
python run_benchmark_model.py --reasoning-model gpt-4o --trials 5
```

## Configuration

The system automatically detects:
- **Ollama models**: Models with ":" in name (e.g., `nemotron-3-nano:30b-cloud`)
- **OpenAI models**: Models starting with `gpt-`, `o1-`, or `o3-`

## Environment Variables

- `REASONING_MODEL`: The reasoning model to use (default: `gpt-4o`)
- `OLLAMA_BASE_URL`: Ollama API base URL (default: `http://localhost:11434`)
- `OPENAI_API_KEY`: OpenAI API key (required for vision)

## Database Storage

All results are stored in `benchmark.db` with:
- `reasoning_llm_model`: The reasoning model used
- `vision_llm_model`: Always `gpt-4o`
- `model`: The reasoning model (for grouping in metrics)

## Viewing Results

```bash
# View metrics for specific experiment
python view_metrics.py --experiment-id bench_nemotron_3_nano_30b_cloud_2026_01_07

# View all metrics
python view_metrics.py
```

## Notes

- Vision calls (with screenshots) always use OpenAI GPT-4o
- Reasoning model is logged but currently all planning uses vision API
- Token counts for Ollama are estimated (Ollama doesn't provide exact counts)
- Cost calculation uses OpenAI pricing for vision calls


