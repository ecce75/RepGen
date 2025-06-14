import streamlit as st
import logging

from ..models.whisper import whisper_process_speech_to_text, get_available_languages
from ..models.qwen import extract_fields_from_text, suggest_recipients, analyze_priority, determine_report_type
from .military_nlp import determine_report_type_enhanced
from . import reports

# Configure logging
logger = logging.getLogger(__name__)

def process_speech_to_text(audio_data, language=None):
    """
    Process speech to text using the Whisper model.

    Parameters:
    audio_data - Audio data bytes
    language - Language code (optional)

    Returns:
    transcript - Text transcript of the audio
    """
    if not audio_data:
        return "No audio recorded."

    # Use the Whisper integration
    with st.spinner("Processing audio with Whisper AI..."):
        transcript = whisper_process_speech_to_text(audio_data, language)
        return transcript


def extract_entities_from_text(report_type, transcript):
    """
    Extract structured data from transcript using the Qwen NLP model.

    Parameters:
    report_type - Type of report (CONTACTREP, SITREP, etc.)
    transcript - Text transcript of the audio

    Returns:
    entities - Dictionary of extracted entities
    """
    # Get report templates
    report_templates = reports.load_report_templates()

    # Use Qwen integration to extract fields
    with st.spinner("Extracting report data with Qwen AI..."):
        extracted_fields = extract_fields_from_text(
            report_type,
            transcript,
            report_templates
        )

    return extracted_fields


def analyze_report_priority(report_type, entities):
    """
    Analyze the report and suggest a priority level using Qwen.

    Parameters:
    report_type - Type of report (CONTACTREP, SITREP, etc.)
    entities - Dictionary of extracted entities

    Returns:
    priority - Suggested priority level
    """
    with st.spinner("Analyzing report priority..."):
        return analyze_priority(report_type, entities)


def suggest_additional_recipients(report_type, entities):
    """
    Suggest additional recipients based on report content using Qwen.

    Parameters:
    report_type - Type of report (CONTACTREP, SITREP, etc.)
    entities - Dictionary of extracted entities

    Returns:
    additional_recipients - List of suggested additional recipients
    """
    with st.spinner("Suggesting appropriate recipients..."):
        return suggest_recipients(report_type, entities)


def translate_report(report_content, target_language):
    """
    Translate report content to a different language using Qwen.

    Parameters:
    report_content - Report content in the original language
    target_language - Target language code

    Returns:
    translated_content - Translated report content
    """
    # This would be implemented with a translation model or Qwen prompt
    # For now, just return the original content until implemented
    return report_content


def get_supported_languages():
    """
    Get list of languages supported by the speech recognition system.

    Returns:
        list: List of dictionaries with language codes and names
    """
    return get_available_languages()


def determine_report_type_from_transcript(transcript):
    """
    Determine the report type from the transcript using the Qwen NLP model.

    Parameters:
    transcript - Text transcript of the audio

    Returns:
    tuple - (report_type, confidence) where report_type is the determined report type
            and confidence is a score between 0 and 1
    """
    # Get report templates
    report_templates = reports.load_report_templates()

    # Use Qwen integration to determine report type
    with st.spinner("Analyzing report type..."):
        report_type, confidence = determine_report_type(transcript, report_templates)

    return report_type, confidence