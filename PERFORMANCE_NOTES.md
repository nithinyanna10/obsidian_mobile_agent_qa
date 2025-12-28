# Performance Notes - Ollama Vision Models

## ⚠️ Current Issue: Slow Response Times

The `qwen3-vl:8b` model is taking **5-10 minutes per screenshot analysis** on CPU. This is causing:
- Timeouts (even with 600s timeout)
- Multiple retries
- Very slow test execution

## 🔍 Root Cause

Vision models are computationally expensive:
- **qwen3-vl:8b** is an 8 billion parameter model
- Processing images requires significant computation
- Running on CPU (no GPU) makes it much slower
- Each screenshot analysis can take 5-10 minutes

## ✅ Fixes Applied

1. **Increased timeout** from 300s to 600s (10 minutes)
2. **Improved response parsing** to avoid unnecessary retries
3. **Better error handling** for timeouts with helpful messages
4. **Smarter retry logic** that doesn't retry on valid responses

## 🚀 Solutions to Speed Up

### Option 1: Use a Faster/Smaller Model (Recommended)
```bash
# Try smaller vision models
ollama pull llava:7b          # Smaller, faster
ollama pull llava:13b         # Medium size
ollama pull bakllava:7b       # Alternative
```

Then update `config.py`:
```python
OLLAMA_VISION_MODEL = "llava:7b"  # Much faster than qwen3-vl:8b
```

### Option 2: Use GPU Acceleration
If you have an NVIDIA GPU:
```bash
# Install CUDA-enabled Ollama
# Or use GPU-accelerated Docker image
```

### Option 3: Reduce Image Size
Modify screenshot capture to resize images before sending to model:
- Current: Full resolution screenshots
- Optimized: Resize to 512x512 or 768x768 before analysis

### Option 4: Use Streaming (Future Enhancement)
Ollama supports streaming responses, which can show progress and reduce perceived wait time.

## 📊 Expected Performance

| Model | CPU Time | GPU Time | Quality |
|-------|----------|----------|---------|
| qwen3-vl:8b | 5-10 min | 30-60s | High |
| llava:13b | 2-5 min | 15-30s | High |
| llava:7b | 1-3 min | 10-20s | Medium |
| bakllava:7b | 1-3 min | 10-20s | Medium |

## 💡 Recommendation

For faster testing, use **llava:7b** or **llava:13b**:
1. They're faster while still providing good vision capabilities
2. Quality is sufficient for screenshot analysis
3. Much better user experience

To switch:
```bash
# Pull the model
ollama pull llava:7b

# Update config.py
OLLAMA_VISION_MODEL = "llava:7b"
```

## 🔧 Current Status

- ✅ Response parsing fixed
- ✅ Timeout increased to 600s
- ✅ Better error messages
- ⚠️ Still slow due to model size (expected)

The system will work, but be patient - each screenshot analysis takes 5-10 minutes with qwen3-vl:8b on CPU.

