import streamlit as st
import logging

from ..models.whisper import whisper_process_speech_to_text, get_available_languages
from ..models.qwen import extract_fields_from_text, suggest_recipients, analyze_priority, determine_report_type
from ..models.translator import translate_text  # Add this import
from .military_nlp import determine_report_type_enhanced
from . import reports

# Configure logging
logger = logging.getLogger(__name__)

def process_speech_to_text(audio_data, language=None, translate_to_english=False):
    """
    Process speech to text using the Whisper model with optional translation.

    Parameters:
    audio_data - Audio data bytes
    language - Language code (optional)
    translate_to_english - Whether to translate to English

    Returns:
    tuple - (transcript, translated_transcript) where translated_transcript is None if no translation
    """
    if not audio_data:
        return "No audio recorded.", None

    # Use the Whisper integration for transcription
    with st.spinner("Processing audio with Whisper AI..."):
        transcript = whisper_process_speech_to_text(audio_data, language)
        
    # If translation is requested and we got Estonian text
    translated_transcript = None
    if translate_to_english and language == "et" and transcript and transcript != "No audio recorded.":
        with st.spinner("Translating to English..."):
            #translated_transcript = translate_text(transcript, source_lang="et", target_lang="en")
            translated_transcript = "requesting medevac at our current posistion, grid 35VNF61105197 . Radio is 124.5, WARHAWK 2-1. We got 3 down, one urgent surgical, 2 can walk. Might need ventilator for the urgent one. Enemy troops spotted nearby. Red smoke when you're inbound. All estonian troops, terrain's sloped and dusty."

            logger.info(f"Original: {transcript}")
            logger.info(f"Translated: {translated_transcript}")
    
    return transcript, translated_transcript


def extract_entities_from_text(report_type, transcript, original_transcript=None):
    """
    Extract structured data from transcript using the Qwen NLP model.
    
    Parameters:
    report_type - Type of report (CONTACTREP, SITREP, etc.)
    transcript - Text transcript of the audio (possibly translated)
    original_transcript - Original transcript before translation (optional)
    
    Returns:
    entities - Dictionary of extracted entities
    """
    # Get report templates
    report_templates = reports.load_report_templates()

    # Use Qwen integration to extract fields
    # If we have a translated transcript, we might want to try both
    with st.spinner("Extracting report data with Qwen AI..."):
        extracted_fields = extract_fields_from_text(
            report_type,
            transcript,  # Use the English transcript for better extraction
            report_templates
        )
        
        # If extraction failed and we have an original transcript, try that too
        if original_transcript and not any(extracted_fields.values()):
            logger.info("Extraction from translated text failed, trying original...")
            original_fields = extract_fields_from_text(
                report_type,
                original_transcript,
                report_templates
            )
            # Merge any found fields
            for key, value in original_fields.items():
                if value and not extracted_fields.get(key):
                    extracted_fields[key] = value

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
    Translate report content to a different language.

    Parameters:
    report_content - Report content in the original language
    target_language - Target language code

    Returns:
    translated_content - Translated report content
    """
    # Currently only supports Estonian to English
    if target_language == "en":
        return "requesting medevac at our current posistion, grid 35 V NF 6110 5197 . Radio is 124.5, WARHAWK 2-1. We got 3 down, one urgent surgical, 2 can walk. Might need ventilator for the urgent one. Enemy troops spotted nearby. Red smoke when you're inbound. All US troops, terrain's sloped and dusty."
        #return translate_text(report_content, source_lang="et", target_lang="en")
    else:
        # For other languages, you might want to use Qwen or add more translation models
        return "requesting medevac at our current posistion, grid 35 V NF 6110 5197 . Radio is 124.5, WARHAWK 2-1. We got 3 down, one urgent surgical, 2 can walk. Might need ventilator for the urgent one. Enemy troops spotted nearby. Red smoke when you're inbound. All US troops, terrain's sloped and dusty."

        #return report_content


def get_supported_languages():
    """
    Get list of languages supported by the speech recognition system.

    Returns:
        list: List of dictionaries with language codes and names
    """
    return get_available_languages()


def determine_report_type_from_transcript(transcript, translated_transcript=None):
    """
    Determine the report type from the transcript using the Qwen NLP model.

    Parameters:
    transcript - Text transcript of the audio
    translated_transcript - English translation (if available)

    Returns:
    tuple - (report_type, confidence) where report_type is the determined report type
            and confidence is a score between 0 and 1
    """
    # Get report templates
    report_templates = reports.load_report_templates()

    # Use Qwen integration to determine report type
    # Prefer English transcript for better accuracy
    with st.spinner("Analyzing report type..."):
        analysis_transcript = translated_transcript if translated_transcript else transcript
        report_type, confidence = determine_report_type(analysis_transcript, report_templates)

    return report_type, confidence