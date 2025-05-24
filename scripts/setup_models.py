#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup script for downloading and configuring AI models for the Military Report Automation system.
This script handles downloading Whisper and Qwen models and setting up the configuration.

Usage:
    python setup_models.py                         # Default setup with recommended models
    python setup_models.py --whisper small --qwen 4B  # Custom model selection
"""

import os
import argparse
import shutil
import subprocess
import sys
import torch
from pathlib import Path
from huggingface_hub import snapshot_download
import logging
from tqdm import tqdm
import json
from dotenv import load_dotenv, set_key

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('model_setup')

# Default paths
MODEL_DIR = os.path.expanduser("~/.cache/repgen/models")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")


def check_prerequisites():
    """
    Check if all prerequisites are met for model setup.
    """
    logger.info("Checking prerequisites...")

    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        logger.error("Python 3.8 or higher is required. Found Python %s.%s",
                     python_version.major, python_version.minor)
        return False

    # Check pip installation
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        logger.error("Pip is not installed or not working properly")
        return False

    # Check CUDA availability (optional)
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        logger.info("CUDA is available. Will use GPU acceleration.")
    else:
        logger.warning("CUDA is not available. Models will run on CPU (slower).")

    # Check FFmpeg installation (needed for audio processing)
    try:
        subprocess.check_call(["ffmpeg", "-version"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("FFmpeg is not installed. Audio processing may not work correctly.")
        logger.warning("Please install FFmpeg before running the application.")

    # Check disk space (approximately)
    try:
        # Get free space in bytes for the model directory
        if not os.path.exists(MODEL_DIR):
            os.makedirs(MODEL_DIR, exist_ok=True)

        if sys.platform == "win32":
            free_space = shutil.disk_usage(MODEL_DIR).free
        else:
            stat = os.statvfs(MODEL_DIR)
            free_space = stat.f_frsize * stat.f_bavail

        # Convert to GB
        free_space_gb = free_space / (1024 ** 3)

        if free_space_gb < 5:
            logger.warning("Less than 5GB of free disk space available (%0.1fGB). "
                           "This may not be enough for the models.", free_space_gb)
        else:
            logger.info("%0.1fGB of free disk space available. This should be sufficient.",
                        free_space_gb)

    except Exception as e:
        logger.warning("Could not check available disk space: %s", str(e))

    return True


def download_whisper_model(model_size="small"):
    """
    Download Whisper model from Hugging Face.

    Args:
        model_size (str): Size of Whisper model to download (tiny, base, small, medium, large)

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Downloading Whisper-{model_size} model...")
    model_name = f"openai/whisper-{model_size}"
    model_path = os.path.join(MODEL_DIR, f"whisper-{model_size}")

    try:
        # Download model using HuggingFace snapshot_download
        snapshot_download(
            repo_id=model_name,
            local_dir=model_path,
            local_dir_use_symlinks=False
        )
        logger.info(f"Successfully downloaded Whisper-{model_size} model to {model_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading Whisper model: {str(e)}")
        return False


def download_qwen_model(model_size="4B"):
    """
    Download Qwen3 model from Hugging Face.

    Args:
        model_size (str): Size of Qwen model to download ('0.6B', '1.7B', '4B', '8B', '14B', '32B', etc.)

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Downloading Qwen3-{model_size} model...")

    # Correct model name format for Qwen3 (no -Chat suffix)
    model_name = f"Qwen/Qwen3-{model_size}"
    model_path = os.path.join(MODEL_DIR, f"qwen3-{model_size}")

    try:
        # Download model using HuggingFace snapshot_download
        snapshot_download(
            repo_id=model_name,
            local_dir=model_path,
            local_dir_use_symlinks=False
        )
        logger.info(f"Successfully downloaded Qwen3-{model_size} model to {model_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading Qwen model: {str(e)}")
        return False


def setup_configuration(whisper_size, qwen_size, use_gpu, quantize=True):
    """
    Set up configuration for the models.

    Args:
        whisper_size (str): Size of Whisper model
        qwen_size (str): Size of Qwen model
        use_gpu (bool): Whether to use GPU acceleration
        quantize (bool): Whether to use quantization for Qwen model

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Setting up configuration...")

    try:
        # Create .env file if it doesn't exist
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                f.write("# Military Report Automation Configuration\n\n")

        # Load existing configuration
        load_dotenv(CONFIG_FILE)

        # Set configuration values
        config = {
            "WHISPER_MODEL_SIZE": whisper_size,
            "QWEN_MODEL_SIZE": qwen_size,
            "USE_GPU": str(use_gpu),
            "DEVICE": "cuda" if use_gpu and torch.cuda.is_available() else "cpu",
            "WHISPER_MODEL_PATH": os.path.join(MODEL_DIR, f"whisper-{whisper_size}"),
            "QWEN_MODEL_PATH": os.path.join(MODEL_DIR, f"qwen3-{qwen_size}"),
            "MOCK_WHISPER": "False",
            "MOCK_QWEN": "False",
            "USE_QUANTIZATION": str(quantize)
        }

        # Write configuration to .env file
        for key, value in config.items():
            set_key(CONFIG_FILE, key, value)

        logger.info(f"Configuration saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error setting up configuration: {str(e)}")
        return False


def main():
    """
    Main entry point for the script.
    """
    parser = argparse.ArgumentParser(description="Setup AI models for Military Report Automation")
    parser.add_argument("--whisper", type=str, choices=["tiny", "base", "small", "medium", "large"],
                        default="small", help="Whisper model size")
    parser.add_argument("--qwen", type=str, choices=["0.6B", "1.7B", "4B", "8B", "14B", "32B", "30B-A3B", "235B-A22B"],
                        default="4B", help="Qwen3 model size")
    parser.add_argument("--cpu-only", action="store_true", help="Force CPU usage even if GPU is available")
    parser.add_argument("--no-quantize", action="store_true", help="Disable model quantization (uses more memory)")

    args = parser.parse_args()

    # Determine whether to use quantization
    use_quantize = not args.no_quantize

    # Check prerequisites
    if not check_prerequisites():
        logger.error("Prerequisites check failed. Please fix the issues and try again.")
        return 1

    # Create model directory if it doesn't exist
    os.makedirs(MODEL_DIR, exist_ok=True)

    # Create app/models directory if it doesn't exist
    app_models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "models")
    if not os.path.exists(app_models_dir):
        os.makedirs(app_models_dir, exist_ok=True)
        # Create __init__.py if it doesn't exist
        init_file = os.path.join(app_models_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write("# Make the models directory a proper Python package\n")

    success = True

    # Download models
    whisper_success = download_whisper_model(args.whisper)
    qwen_success = download_qwen_model(args.qwen)

    # Set up configuration
    if whisper_success and qwen_success:
        config_success = setup_configuration(args.whisper, args.qwen, not args.cpu_only, use_quantize)
        success = config_success
    else:
        success = False

    if success:
        logger.info("Model setup completed successfully!")
        logger.info("\nTo run the application:")
        logger.info("  streamlit run app/main.py")
        return 0
    else:
        logger.error("Model setup failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())