import streamlit as st
import io
import tempfile
import os
from datetime import datetime
import logging
import importlib.util

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_audio_from_microphone(key=None):
    """
    Get audio from the user's microphone using the best available method.
    Returns the audio data if successful, None otherwise.
    """
    # Initialize session state for recording flow
    if 'microphone_step' not in st.session_state:
        st.session_state.microphone_step = 'initial'
    if 'temp_audio_data' not in st.session_state:
        st.session_state.temp_audio_data = None

    # Generate a consistent key for the recorder
    recorder_key = key or "audio_recorder_component"

    # Display appropriate instructions based on microphone step
    if st.session_state.microphone_step == 'initial':
        st.markdown("### Recording Instructions")
        st.markdown("1. Click the microphone button below to start recording")
        st.markdown("2. If prompted, allow microphone access in your browser")
        st.markdown("3. After allowing access, the page may reload - this is normal")
        st.markdown("4. Once recording, speak clearly and click again to stop")

        # Display a notice about the reload behavior
        st.info(
            "Note: Your browser may request microphone permissions the first time. If the page reloads after granting permission, simply click the record button again.")

    # If we're in the recording step or subsequent steps
    if st.session_state.microphone_step in ['recording', 'completed']:
        st.success("✅ Microphone access granted. Click below to record/stop.")

    # Try using the audio_recorder_streamlit package
    try:
        # Check if audio_recorder_streamlit is installed
        if importlib.util.find_spec("audio_recorder_streamlit"):
            from audio_recorder_streamlit import audio_recorder

            # Use the audio_recorder component
            audio_bytes = audio_recorder(
                text="Click to record",
                recording_color="#e8b62c",
                neutral_color="#6aa36f",
                icon_name="microphone",
                key=recorder_key
            )

            # Handle state changes
            if audio_bytes:
                # Successfully recorded audio
                st.session_state.microphone_step = 'completed'
                st.session_state.temp_audio_data = audio_bytes
                logger.info(f"Successfully recorded audio: {len(audio_bytes)} bytes")
                return audio_bytes
            elif st.session_state.microphone_step == 'completed' and st.session_state.temp_audio_data:
                # Return stored audio if we've already completed recording but page reloaded
                logger.info("Returning previously recorded audio from session state")
                return st.session_state.temp_audio_data
            else:
                # If microphone was accessed but no recording completed yet
                if st.session_state.microphone_step == 'initial':
                    st.session_state.microphone_step = 'recording'

                return None

    except ImportError:
        st.error("""
        ## Audio Recording Component Not Installed

        Please install the audio-recorder-streamlit package:
        ```
        pip install audio-recorder-streamlit
        ```

        After installing, restart the application.
        """)
        return None

    except Exception as e:
        st.error(f"Error recording audio: {str(e)}")
        logger.error(f"Error recording audio: {str(e)}")
        return None


def save_audio_to_temp_file(audio_bytes):
    """
    Save audio bytes to a temporary file and return the file path.
    """
    if not audio_bytes:
        return None

    # Create a temporary file
    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_audio_path = os.path.join(temp_dir, f"audio_{timestamp}.wav")

    # Write audio bytes to the temporary file
    with open(temp_audio_path, 'wb') as f:
        f.write(audio_bytes)

    logger.info(f"Saved audio to temporary file: {temp_audio_path}")
    return temp_audio_path


def audio_to_text(audio_bytes, language=None):
    """
    Convert audio to text using the Whisper speech recognition model.

    Parameters:
    audio_bytes - Audio data in bytes
    language - Language code (optional)

    Returns:
    text - Transcribed text
    """
    from app.utils.ai import process_speech_to_text

    # Use the AI module's process_speech_to_text function
    return process_speech_to_text(audio_bytes, language)


def preprocess_audio(audio_bytes):
    """
    Preprocess audio data for the speech recognition model.

    Parameters:
    audio_bytes - Audio data in bytes

    Returns:
    audio_array - Preprocessed audio data ready for the speech recognition model
    """
    try:
        from ..models import whisper
        return whisper.preprocess_audio_bytes(audio_bytes)
    except ImportError:
        logger.error("Could not import whisper module. Make sure it's properly installed.")
        return None