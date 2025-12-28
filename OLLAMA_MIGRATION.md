# Migration from OpenAI to Ollama

## ✅ Changes Completed

### 1. Configuration (`config.py`)
- Removed `OPENAI_API_KEY` and `OPENAI_MODEL`
- Added `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
- Added `OLLAMA_VISION_MODEL` = `"qwen3-vl:8b"` (for screenshot analysis)
- Added `OLLAMA_TEXT_MODEL` = `"gpt-oss:120b-cloud"` (for text-only tasks, if needed)

### 2. New Ollama Client (`tools/ollama_client.py`)
- Created `call_ollama_vision()` - Calls qwen3-vl:8b with images
- Created `call_ollama_chat()` - Calls gpt-oss:120b-cloud for text tasks
- Created `check_ollama_connection()` - Verifies Ollama is running
- Uses `/api/chat` endpoint with `images` array for vision models

### 3. Planner Agent (`agents/planner.py`)
- Removed OpenAI imports and client initialization
- Replaced all `call_openai_with_retry()` calls with `call_ollama_vision()`
- Updated response parsing (Ollama returns text directly, not response objects)
- All 4 vision API calls now use Ollama

### 4. Supervisor Agent (`agents/supervisor.py`)
- Removed OpenAI imports and client initialization
- Replaced `call_openai_with_retry()` with `call_ollama_vision()`
- Updated response parsing

### 5. Main Orchestrator (`main.py`)
- Removed OpenAI API key checks
- Added Ollama connection check
- Updated imports

### 6. Dependencies (`requirements.txt`)
- Removed `openai>=1.0.0`
- Added `ollama>=0.1.0` (optional, we use direct HTTP requests)
- Added `requests` (for HTTP calls to Ollama API)

## 🚀 Setup Instructions

### 1. Install Ollama
```bash
# macOS
brew install ollama

# Or download from https://ollama.ai
```

### 2. Start Ollama Service
```bash
ollama serve
```

### 3. Pull Required Models
```bash
# Pull vision model (for screenshot analysis)
ollama pull qwen3-vl:8b

# Pull text model (optional, for future use)
ollama pull gpt-oss:120b-cloud
```

### 4. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 5. Verify Ollama is Running
```bash
# Check if Ollama is accessible
curl http://localhost:11434/api/tags

# Or test with Python
python -c "from tools.ollama_client import check_ollama_connection; print('Ollama OK' if check_ollama_connection() else 'Ollama not running')"
```

## 📝 Usage

The system now uses Ollama instead of OpenAI:

- **Zero cost** - All models run locally
- **Privacy** - No data sent to external APIs
- **Same functionality** - Vision models analyze screenshots just like before

### Running Tests
```bash
python main.py
```

The system will:
1. Check if Ollama is running
2. Use `qwen3-vl:8b` for all screenshot analysis
3. Work exactly as before, but with local models

## 🔧 Configuration

Edit `config.py` to customize:

```python
# Change Ollama server URL (if not running on localhost)
OLLAMA_BASE_URL = "http://localhost:11434"

# Change vision model
OLLAMA_VISION_MODEL = "qwen3-vl:8b"

# Change text model (if needed)
OLLAMA_TEXT_MODEL = "gpt-oss:120b-cloud"
```

## ⚠️ Notes

1. **Model Availability**: Ensure `qwen3-vl:8b` is pulled and available
2. **Performance**: Local models may be slower than cloud APIs, but no cost
3. **Memory**: Vision models require significant RAM (8GB+ recommended)
4. **API Format**: qwen3-vl uses `/api/chat` with `images` array in messages

## 🐛 Troubleshooting

### Ollama not found
```bash
# Install Ollama
brew install ollama  # macOS
# Or download from https://ollama.ai
```

### Model not found
```bash
# Pull the model
ollama pull qwen3-vl:8b
```

### Connection refused
```bash
# Start Ollama service
ollama serve
```

### Model too slow
- Consider using a smaller/faster vision model
- Or use GPU acceleration if available

## ✅ Benefits

- ✅ **Zero cost** - No API charges
- ✅ **Privacy** - All processing local
- ✅ **No rate limits** - Run as many tests as needed
- ✅ **Offline capable** - Works without internet

