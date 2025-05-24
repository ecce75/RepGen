# RepGen Installation Guide

This guide will help you set up RepGen on different platforms, including Apple Silicon Macs, CUDA-enabled systems, and CPU-only environments.

## Quick Setup (All Platforms)

The easiest way to get started is to use our platform-specific setup script:

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/your-username/RepGen.git
cd RepGen

# Run the platform setup script
python setup_platform.py

# Start the application
streamlit run app/main.py
```

The setup script will:
1. Detect your platform (MacOS, Windows, Linux)
2. Install appropriate dependencies
3. Configure optimal model settings for your hardware
4. Create an appropriate .env file

## Manual Setup for Specific Platforms

### Apple Silicon (M1/M2/M3) Macs

Apple Silicon requires a specific setup since bitsandbytes is not supported:

```bash
# Install dependencies
pip install -r requirements.txt

# Create appropriate .env file
cat > .env << EOL
WHISPER_MODEL_SIZE='small'
QWEN_MODEL_SIZE='1.7B'
USE_GPU='True'
DEVICE='mps'
WHISPER_MODEL_PATH='~/.cache/repgen/models/whisper-small'
QWEN_MODEL_PATH='~/.cache/repgen/models/qwen3-1.7B'
MOCK_WHISPER='False'
MOCK_QWEN='False'
USE_QUANTIZATION='False'
EOL

# Download models
python scripts/setup_models.py --whisper small --qwen 1.7B

# Start the application
streamlit run app/main.py
```

### CUDA-enabled Systems

If you have an NVIDIA GPU, you can use bitsandbytes for 4-bit quantization:

```bash
# Install dependencies with bitsandbytes
pip install -r requirements.txt
pip install bitsandbytes

# Create appropriate .env file
cat > .env << EOL
WHISPER_MODEL_SIZE='small'
QWEN_MODEL_SIZE='4B'
USE_GPU='True'
DEVICE='cuda'
WHISPER_MODEL_PATH='~/.cache/repgen/models/whisper-small'
QWEN_MODEL_PATH='~/.cache/repgen/models/qwen3-4B'
MOCK_WHISPER='False'
MOCK_QWEN='False'
USE_QUANTIZATION='True'
EOL

# Download models
python scripts/setup_models.py --whisper small --qwen 4B

# Start the application
streamlit run app/main.py
```

### CPU-only Systems

For systems without GPU acceleration:

```bash
# Install dependencies
pip install -r requirements.txt

# Create appropriate .env file
cat > .env << EOL
WHISPER_MODEL_SIZE='small'
QWEN_MODEL_SIZE='1.7B'
USE_GPU='False'
DEVICE='cpu'
WHISPER_MODEL_PATH='~/.cache/repgen/models/whisper-small'
QWEN_MODEL_PATH='~/.cache/repgen/models/qwen3-1.7B'
MOCK_WHISPER='False'
MOCK_QWEN='False'
USE_QUANTIZATION='False'
EOL

# Download models (using smaller models for better CPU performance)
python scripts/setup_models.py --whisper small --qwen 1.7B

# Start the application
streamlit run app/main.py
```

## Recommended Model Sizes by Platform

| Platform | Whisper | Qwen | Notes |
|----------|---------|------|-------|
| NVIDIA GPU (16GB+ VRAM) | medium | 8B | Best quality, requires more VRAM |
| NVIDIA GPU (8GB VRAM) | small | 4B | Good balance of quality and speed |
| NVIDIA GPU (<8GB VRAM) | small | 1.7B | More memory efficient |
| Apple Silicon | small | 1.7B | Good performance on M1/M2/M3 |
| CPU only | small | 0.6B | Fastest option for CPU |

## Troubleshooting

- **Out of memory errors**: Try a smaller model size or disable quantization
- **Slow performance**: On CPU systems, use the smallest model sizes
- **Model loading issues**: Check your internet connection and disk space
- **Audio recording not working**: Ensure you have installed audio-recorder-streamlit