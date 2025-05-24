#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Platform-specific setup script for RepGen.
This script detects your platform and installs the appropriate dependencies.
"""

import platform
import subprocess
import sys
import os


def main():
    print("RepGen Platform-Specific Setup")
    print("===============================")

    # Detect platform
    system = platform.system()
    machine = platform.machine()
    print(f"Detected system: {system} on {machine}")

    # Install base requirements
    print("\nInstalling base requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    # Platform-specific installations
    if system == "Linux" or system == "Windows":
        try:
            subprocess.check_call(["nvidia-smi"])
            print("\nNVIDIA GPU detected. Installing bitsandbytes for quantization...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "bitsandbytes"])
            print("bitsandbytes installed successfully!")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("\nNo NVIDIA GPU detected. Skipping bitsandbytes installation.")

    elif system == "Darwin" and machine == "arm64":
        print("\nApple Silicon detected. Setting up MPS acceleration...")
        # No additional packages needed, PyTorch's MPS backend works with standard installation
        print("Your system will use Metal Performance Shaders (MPS) for acceleration.")
        print("Note: For optimal performance, we recommend using smaller models (0.6B or 1.7B).")

    # Create appropriate .env file
    create_env_file(system, machine)

    print("\nSetup completed successfully!")
    print("To run the application, use: streamlit run app/main.py")


def create_env_file(system, machine):
    """Create a suitable .env file based on the platform"""
    print("\nCreating .env configuration file...")

    # Determine optimal settings
    if system == "Darwin" and machine == "arm64":
        # Apple Silicon settings
        whisper_size = "small"  # Good balance for M1/M2
        qwen_size = "1.7B"  # Reasonable size for Apple Silicon
        device = "mps"
        use_gpu = "True"
        use_quantization = "False"  # No quantization on MPS
    elif system == "Linux" or system == "Windows":
        # Check for NVIDIA GPU
        try:
            subprocess.check_call(["nvidia-smi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # CUDA system settings
            whisper_size = "small"
            qwen_size = "4B"
            device = "cuda"
            use_gpu = "True"
            use_quantization = "True"
        except (subprocess.CalledProcessError, FileNotFoundError):
            # CPU-only settings
            whisper_size = "small"
            qwen_size = "1.7B"
            device = "cpu"
            use_gpu = "False"
            use_quantization = "False"
    else:
        # Default/fallback settings
        whisper_size = "small"
        qwen_size = "1.7B"
        device = "cpu"
        use_gpu = "False"
        use_quantization = "False"

    # Create the .env file
    with open(".env", "w") as f:
        f.write("# RepGen Configuration\n\n")
        f.write(f"WHISPER_MODEL_SIZE='{whisper_size}'\n")
        f.write(f"QWEN_MODEL_SIZE='{qwen_size}'\n")
        f.write(f"USE_GPU='{use_gpu}'\n")
        f.write(f"DEVICE='{device}'\n")
        cache_dir = os.path.expanduser("~/.cache/repgen/models")
        f.write(f"WHISPER_MODEL_PATH='{cache_dir}/whisper-{whisper_size}'\n")
        f.write(f"QWEN_MODEL_PATH='{cache_dir}/qwen3-{qwen_size}'\n")
        f.write(f"MOCK_WHISPER='False'\n")
        f.write(f"MOCK_QWEN='False'\n")
        f.write(f"USE_QUANTIZATION='{use_quantization}'\n")

    print(f"Created .env file with appropriate settings for your {system} {machine} system")


if __name__ == "__main__":
    main()