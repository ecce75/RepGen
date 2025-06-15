import torch
import numpy as np
import streamlit as st
import tempfile
import os
import io
import logging
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import librosa
from pydub import AudioSegment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables to store models
processor = None
model = None


def load_model(model_size="small", custom_model=None):
    """
    Load the Whisper model and processor.

    Args:
        model_size (str): Size of the Whisper model to use ('tiny', 'base', 'small', 'medium', 'large')
                          Ignored if custom_model is provided
        custom_model (str): Custom model name from HuggingFace (e.g., 'TalTechNLP/whisper-large-v3-et-subs')

    Returns:
        tuple: (processor, model) - The loaded Whisper processor and model
    """
    global processor, model

    # Only load if not already loaded
    if processor is None or model is None:
        try:
            # Use custom model if provided, otherwise use default OpenAI models
            if custom_model:
                model_name = custom_model
                st.info(f"Loading custom Whisper model: {model_name}")
            else:
                model_name = f"openai/whisper-{model_size}"
                st.info(f"Loading Whisper {model_size} model. This may take a moment...")

            processor = WhisperProcessor.from_pretrained(model_name)
            model = WhisperForConditionalGeneration.from_pretrained(model_name)

            # Device selection remains the same
            if torch.backends.mps.is_available():
                device = "mps"
                st.success("Using Apple Silicon GPU acceleration via Metal Performance Shaders")
            elif torch.cuda.is_available():
                device = "cuda"
                st.success("Using NVIDIA GPU acceleration via CUDA")
            else:
                device = "cpu"
                st.warning("Using CPU for Whisper (slower). No GPU acceleration available.")

            model = model.to(device)

            st.success(f"Whisper model loaded successfully on {device}!")
            return processor, model

        except Exception as e:
            st.error(f"Error loading Whisper model: {str(e)}")
            logger.error(f"Error loading Whisper model: {str(e)}")
            raise e

    return processor, model


def preprocess_audio_bytes(audio_bytes):
    """
    Preprocess audio bytes to format expected by Whisper.

    Args:
        audio_bytes (bytes): Audio data in bytes format from Streamlit recorder

    Returns:
        numpy.ndarray: Audio data as a numpy array with correct sampling rate
    """
    logger.info(f"PREPROCESS_AUDIO_BYTES received type: {type(audio_bytes)}")

    try:
        # Save to a temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name

        # Process the audio file
        try:
            # First try using pydub which handles various formats well
            audio = AudioSegment.from_file(temp_audio_path)
            audio = audio.set_channels(1)  # Convert to mono
            audio = audio.set_frame_rate(16000)  # Convert to 16kHz

            # Export to a new temporary file
            mono_path = temp_audio_path + '_mono.wav'
            audio.export(mono_path, format="wav")

            # Load with librosa (which gives us the numpy array we need)
            audio_array, _ = librosa.load(mono_path, sr=16000)

            # Clean up temporary files
            os.remove(mono_path)

        except Exception as pydub_error:
            logger.warning(f"Pydub processing failed, trying librosa directly: {str(pydub_error)}")
            # Fallback to direct librosa loading
            audio_array, _ = librosa.load(temp_audio_path, sr=16000)

        finally:
            # Clean up the original temporary file
            os.remove(temp_audio_path)

        return audio_array

    except Exception as e:
        logger.error(f"Error preprocessing audio: {str(e)}")
        st.error(f"Error preprocessing audio: {str(e)}")
        raise e


def transcribe_audio(audio_array, language=None, task="transcribe", use_custom_model=False):
    """
    Transcribe audio using the Whisper model.

    Args:
        audio_array (numpy.ndarray): Preprocessed audio array
        language (str, optional): Language code for transcription (e.g. 'en', 'fr', 'et')
        task (str): Either 'transcribe' or 'translate' (to English)
        use_custom_model (bool): Whether to use the Estonian-optimized model

    Returns:
        str: Transcribed text
    """
    global processor, model

    if audio_array is None:
        return "Error: No audio data to transcribe."

    # Load appropriate model
    if use_custom_model:
        processor, model = load_model(custom_model="TalTechNLP/whisper-large-v3-turbo-et-subs")
    else:
        processor, model = load_model()

    try:
        # Get the device the model is on
        device = next(model.parameters()).device

        # Process audio with the model
        input_features = processor(audio_array, sampling_rate=16000, return_tensors="pt").input_features
        input_features = input_features.to(device)

        # Generate token ids with specific language and task
        forced_decoder_ids = None

        # Set the language if specified
        if language:
            forced_decoder_ids = processor.get_decoder_prompt_ids(language=language, task=task)

        # Generate transcription
        with torch.no_grad():
            predicted_ids = model.generate(
                input_features,
                forced_decoder_ids=forced_decoder_ids,
                max_length=448,  # Maximum length for generated tokens
                num_beams=5,  # Beam search for better quality
            )

        # Decode token ids to text
        transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]

        return transcription.strip()

    except Exception as e:
        error_msg = f"Error transcribing audio: {str(e)}"
        logger.error(error_msg)
        raise e


def whisper_process_speech_to_text(audio_bytes, language=None, use_estonian_model=False):
    """
    Process audio bytes to text using Whisper.
    This is the main function to call from the Streamlit app.

    Args:
        audio_bytes (bytes): Audio data from Streamlit's audio recorder
        language (str, optional): Language code for transcription
        use_estonian_model (bool): Use the Estonian-optimized model

    Returns:
        str: Transcribed text
    """
    if not audio_bytes:
        return "No audio recorded."

    try:
        logger.info(f"Processing audio of type: {type(audio_bytes)} and size: {len(audio_bytes)} bytes")

        # Preprocess the audio
        audio_array = preprocess_audio_bytes(audio_bytes)

        # Transcribe with appropriate model
        if audio_array is not None:
            # Force Estonian language if using Estonian model
            if use_estonian_model:
                language = "et"
            
            transcript = transcribe_audio(
                audio_array, 
                language, 
                use_custom_model=use_estonian_model
            )
            return transcript
        else:
            return "Failed to process audio."

    except Exception as e:
        logger.error(f"Error in whisper_process_speech_to_text: {str(e)}")
        st.error(f"Error processing speech: {str(e)}")
        return f"Error processing audio: {str(e)}"


def get_available_languages():
    """
    Get list of languages supported by Whisper.

    Returns:
        list: List of language codes and names
    """
    return [
        {"code": "en", "name": "English"},
        {"code": "et", "name": "Estonian"},
        {"code": "zh", "name": "Chinese"},
        {"code": "de", "name": "German"},
        {"code": "es", "name": "Spanish"},
        {"code": "ru", "name": "Russian"},
        {"code": "fr", "name": "French"},
        {"code": "ja", "name": "Japanese"},
        {"code": "pt", "name": "Portuguese"},
        {"code": "ar", "name": "Arabic"},
        {"code": "hi", "name": "Hindi"},
        {"code": "it", "name": "Italian"},
        {"code": "nl", "name": "Dutch"},
        {"code": "tr", "name": "Turkish"},
        {"code": "pl", "name": "Polish"},
        {"code": "ko", "name": "Korean"},
        {"code": "he", "name": "Hebrew"},
        {"code": "sv", "name": "Swedish"},
        {"code": "cs", "name": "Czech"},
        {"code": "uk", "name": "Ukrainian"},
        {"code": "ro", "name": "Romanian"},
    ]