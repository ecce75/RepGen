from transformers import MarianMTModel, MarianTokenizer
import torch
import streamlit as st
import logging

logger = logging.getLogger(__name__)

# Global variables for translation model
translation_model = None
translation_tokenizer = None

def load_translation_model():
    """Load the Estonian to English translation model."""
    global translation_model, translation_tokenizer
    
    if translation_model is None or translation_tokenizer is None:
        try:
            # Using Helsinki-NLP's Estonian-English model
            model_name = "Helsinki-NLP/opus-mt-et-en"
            st.info("Loading Estonian-English translation model...")
            
            translation_tokenizer = MarianTokenizer.from_pretrained(model_name)
            translation_model = MarianMTModel.from_pretrained(model_name)
            
            # Move to appropriate device
            if torch.cuda.is_available():
                translation_model = translation_model.to("cuda")
            elif torch.backends.mps.is_available():
                translation_model = translation_model.to("mps")
            
            st.success("Translation model loaded!")
            
        except Exception as e:
            logger.error(f"Error loading translation model: {str(e)}")
            raise e
    
    return translation_tokenizer, translation_model

def translate_text(text: str, source_lang="et", target_lang="en") -> str:
    """
    Translate text from Estonian to English.
    
    Args:
        text (str): Text to translate
        source_lang (str): Source language code
        target_lang (str): Target language code
        
    Returns:
        str: Translated text
    """
    if source_lang != "et" or target_lang != "en":
        logger.warning(f"This model only supports et->en translation")
        return text
    
    tokenizer, model = load_translation_model()
    
    try:
        # Prepare text for translation
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        
        # Move to same device as model
        if model.device.type != "cpu":
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        # Generate translation
        with torch.no_grad():
            translated = model.generate(**inputs, max_length=512, num_beams=4, early_stopping=True)
        
        # Decode the translation
        translation = tokenizer.decode(translated[0], skip_special_tokens=True)
        return translation
        
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return text  # Return original text if translation fails