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

## TAK Integration Configuration

### Setting up WinTAK Import Directory

By default, RepGen saves TAK CoT XML files to `~/TAK/import`. To configure a custom directory:

```bash
# Set environment variable (Linux/Mac)
export WINTAK_IMPORT_DIR="/path/to/your/wintak/import"

# Or on Windows
set WINTAK_IMPORT_DIR="C:\path\to\your\wintak\import"
```

### CoT XML File Format

RepGen generates NATO-standard Cursor-on-Target XML files that include:
- Unique message identifiers
- Proper CoT types for different report formats
- Geographic coordinates (when available)
- Report field data structured for TAK consumption
- Expiration timestamps

## System Requirements

| Platform | RAM | Storage | Performance |
|----------|-----|---------|-------------|
| NVIDIA GPU (8GB+ VRAM) | 8GB | 5GB | Excellent |
| Apple Silicon (M1/M2/M3) | 8GB | 3GB | Very Good |
| CPU only | 4GB | 2GB | Good |

## Troubleshooting

### Common Issues

- **Out of memory errors**: The application will automatically use smaller models if memory is limited
- **Slow performance**: Performance will vary based on hardware; consider upgrading for better experience
- **Model loading issues**: Check your internet connection and ensure you have sufficient disk space
- **Audio recording not working**: 
  - Ensure your browser has microphone permissions
  - Check that `streamlit-audio-recorder` is properly installed
  - Try refreshing the browser page

### TAK Integration Issues

- **CoT XML files not appearing in WinTAK**: 
  - Verify the `WINTAK_IMPORT_DIR` path is correct
  - Check that WinTAK is monitoring the import directory
  - Ensure the generated XML files have proper permissions

### Performance Optimization

- **For better speech recognition**: Use a quiet environment and speak clearly
- **For faster processing**: Close other applications to free up system resources
- **For improved accuracy**: Pause between different report sections when speaking

## Environment Variables

Optional environment variables for advanced configuration:

```bash
# TAK integration
WINTAK_IMPORT_DIR="/path/to/tak/import"  # Custom TAK import directory

# Model configuration (advanced users)
WHISPER_MODEL_SIZE="small"              # Whisper model size
QWEN_MODEL_SIZE="1.8b"                  # Qwen model size
```