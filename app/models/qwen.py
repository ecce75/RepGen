import torch
import streamlit as st
import json
import logging
import platform
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
import re
from app.utils.military_nlp import (
    create_military_conditioned_prompt,
    validate_military_extraction,
    post_process_extracted_fields,
    determine_report_type_enhanced,
    convert_phonetic_to_standard,
    preprocess_military_transcript,
    extract_fields_with_fallback,
    merge_extraction_results
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables to store the model and tokenizer
model = None
tokenizer = None


def load_model(model_size="4B"):
    """
    Load the Qwen model and tokenizer with hardware-specific optimizations.

    This is a hybrid implementation that:
    1. Uses bitsandbytes quantization on CUDA GPUs
    2. Uses MPS acceleration on Apple Silicon
    3. Falls back to CPU with appropriate optimizations elsewhere

    Args:
        model_size (str): Size of the Qwen model to use
                          - For CUDA GPUs: '4B', '8B' recommended
                          - For Apple Silicon: '0.6B', '1.7B' recommended
                          - For CPU-only: '0.6B', '1.7B' recommended

    Returns:
        tuple: (tokenizer, model) - The loaded Qwen tokenizer and model
    """
    global model, tokenizer

    # Only load if not already loaded
    if tokenizer is None or model is None:
        try:
            st.info(f"Loading Qwen3-{model_size} model. This may take a moment...")

            # Use correct Qwen3 model name format
            model_name = f"Qwen/Qwen3-{model_size}"

            # Load the tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

            # After loading tokenizer, add:
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.unk_token
            if tokenizer.pad_token == tokenizer.eos_token:
                tokenizer.pad_token = tokenizer.unk_token

            # Determine the hardware platform and best device
            is_apple_silicon = (platform.system() == "Darwin" and
                                platform.machine() == "arm64" and
                                torch.backends.mps.is_available())

            has_cuda = torch.cuda.is_available()

            model_kwargs = {}

            # OPTION 1: CUDA GPUs with bitsandbytes quantization
            if has_cuda:
                device = "cuda"
                st.success("Using NVIDIA GPU acceleration with bitsandbytes quantization")

                try:
                    # Try to import and use bitsandbytes
                    from transformers import BitsAndBytesConfig

                    # 4-bit quantization for efficiency
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )

                    model_kwargs['quantization_config'] = quantization_config
                    st.info("Using 4-bit quantization for better memory efficiency")

                except ImportError:
                    st.warning("bitsandbytes not available, using standard GPU loading")

                # Load the model with CUDA optimizations
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                    device_map="auto",
                    **model_kwargs
                )

            # OPTION 2: Apple Silicon with MPS backend
            elif is_apple_silicon:
                device = "mps"
                st.success("Using Apple Silicon GPU acceleration via Metal Performance Shaders")

                # Recommend smaller model size if using a large model on MPS
                if model_size not in ["0.6B", "1.7B"] and model_size.endswith("B"):
                    st.warning(f"Model size {model_size} may be too large for optimal performance on Apple Silicon. " +
                               "Consider using 0.6B or 1.7B for better speed.")

                # Load model specifically for MPS
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                    torch_dtype=torch.float16  # Use float16 for better performance
                ).to("mps")

            # OPTION 3: CPU fallback
            else:
                device = "cpu"
                st.warning("No GPU acceleration available. Using CPU only (slower performance)")

                # If using a large model on CPU, warn about potential issues
                if model_size not in ["0.6B", "1.7B"] and model_size.endswith("B"):
                    st.warning(f"Model size {model_size} is quite large for CPU-only inference. " +
                               "This may be very slow. Consider using 0.6B or 1.7B for better speed.")

                # Load the model for CPU
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                    device_map="auto",
                    **model_kwargs
                )

            st.success(f"Qwen3 model loaded successfully on {device}!")
            return tokenizer, model

        except Exception as e:
            error_msg = f"Error loading Qwen model: {str(e)}"
            logger.error(error_msg)
            st.error(error_msg)
            raise e

    return tokenizer, model


def extract_fields_from_text(report_type: str, transcript: str, report_templates: dict) -> dict:
    """
    Enhanced extraction that orchestrates the full pipeline using military utilities.
    """
    global model, tokenizer
    
    if model is None or tokenizer is None:
        tokenizer, model = load_model()
    
    template = report_templates.get(report_type, {})
    
    # Log the preprocessed transcript for debugging
    preprocessed = preprocess_military_transcript(transcript)
    logger.info(f"Original transcript: {transcript}")
    logger.info(f"Preprocessed transcript: {preprocessed}")
    
    # Create prompt with anti-copying measures
    prompt = create_military_conditioned_prompt(report_type, transcript, template)
    
    try:
        # Apply chat template
        text = tokenizer.apply_chat_template(
            prompt,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )
        
        # Generate with very low temperature for extraction consistency
        input_tokens = tokenizer(text, return_tensors="pt")
        
        if hasattr(model, 'device'):
            device = model.device
            input_features = input_tokens.to(device)
        else:
            input_features = input_tokens
        
        with torch.no_grad():
            generation_args = {
                "max_new_tokens": 500,
                "temperature": 0.05,  # Very low for consistent extraction
                "top_p": 0.9,
                "do_sample": True,
                "repetition_penalty": 1.2
            }
            
            generated_ids = model.generate(
                input_features.input_ids,
                attention_mask=input_features.attention_mask,
                **generation_args
            )
            
            response = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
        
        # Extract JSON
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_start = response.rfind('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
            else:
                raise ValueError("No JSON found in response")
        
        extracted_fields = json.loads(json_str)
        
        # Double-check for example data leakage
        example_values = ["RAZOR 3-1", "THUNDER", "18TWL9434567890", "47.55", "purple"]
        for field, value in extracted_fields.items():
            if value and any(example in str(value) for example in example_values):
                logger.warning(f"Example data leaked into field {field}: {value}")
                # Try to extract from preprocessed transcript
                if field == "location" and "grid" in preprocessed.lower():
                    grid_match = re.search(r'grid\s+([A-Z0-9]+)', preprocessed, re.IGNORECASE)
                    if grid_match:
                        extracted_fields[field] = grid_match.group(1)
        
        # Validate and clean using military utilities
        validated_fields = validate_military_extraction(report_type, extracted_fields)
        final_fields = post_process_extracted_fields(report_type, validated_fields, transcript)
        
        # Ensure all fields exist
        for field in template.get("fields", []):
            if field["id"] not in final_fields:
                final_fields[field["id"]] = ""
        
        return final_fields
        
    except Exception as e:
        logger.error(f"Error in military field extraction: {str(e)}")
        return {field["id"]: "" for field in template.get("fields", [])}


def extract_fields_from_text_with_safety(report_type: str, transcript: str, report_templates: dict) -> dict:
    """
    Extract fields using AI with fallback safety net.
    """
    # First try AI extraction
    ai_fields = extract_fields_from_text(report_type, transcript, report_templates)
    
    # Always run fallback extraction for safety
    fallback_fields = extract_fields_with_fallback(transcript, report_type)
    
    # Merge results intelligently
    final_fields = merge_extraction_results(ai_fields, fallback_fields, transcript)
    
    # Ensure all required fields exist
    template = report_templates.get(report_type, {})
    for field in template.get("fields", []):
        if field["id"] not in final_fields:
            final_fields[field["id"]] = ""
    
    return final_fields


def analyze_priority(report_type, fields):
    """
    Analyze the report content and suggest a priority level.

    Args:
        report_type (str): The type of report
        fields (dict): Extracted fields from the report

    Returns:
        str: Suggested priority level
    """
    global model, tokenizer

    # Load the model if not already loaded
    if model is None or tokenizer is None:
        tokenizer, model = load_model()

    # Create a prompt for priority analysis
    fields_str = "\n".join([f"{k}: {v}" for k, v in fields.items()])

    prompt = [
        {"role": "system",
         "content": "You are a military report analyst. Analyze report content and suggest appropriate priority levels."},
        {"role": "user", "content": f"""
Analyze the following {report_type} report content and suggest an appropriate priority level.
The levels from lowest to highest urgency are: Routine, Priority, Immediate, Flash.

Report fields:
{fields_str}

Only return the single word priority level (Routine, Priority, Immediate, or Flash). No explanation.
"""}
    ]

    try:
        # Apply chat template
        text = tokenizer.apply_chat_template(
            prompt,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )

        # Tokenize the prompt and move to the appropriate device
        input_tokens = tokenizer(text, return_tensors="pt")

        # Handle device placement based on model type
        if hasattr(model, 'device'):
            # If model has a single device
            device = model.device
            # FIX: Keep the tokens as an object, not a dictionary
            input_features = input_tokens.to(device)
        else:
            # For models with device_map (usually quantized models)
            input_features = input_tokens

        # Generate response
        with torch.no_grad():
            generation_args = {
                "max_new_tokens": 20,
                "temperature": 0.1,
                "top_p": 0.95,
                "do_sample": True
            }

            generated_ids = model.generate(
                input_features.input_ids,
                attention_mask=input_features.attention_mask,
                **generation_args
            )

            response = tokenizer.decode(generated_ids[0], skip_special_tokens=True).strip()

        # Extract just the priority level
        priority_levels = ["Routine", "Priority", "Immediate", "Flash"]
        for level in priority_levels:
            if level.lower() in response.lower():
                return level

        # Default fallback based on report type
        default_priorities = {
            "CONTACTREP": "Immediate",
            "SITREP": "Routine",
            "MEDEVAC": "Flash",
            "RECCEREP": "Priority"
        }
        return default_priorities.get(report_type, "Routine")

    except Exception as e:
        logger.error(f"Error analyzing priority: {str(e)}")

        # Fallback to default priorities
        default_priorities = {
            "CONTACTREP": "Immediate",
            "SITREP": "Routine",
            "MEDEVAC": "Flash",
            "RECCEREP": "Priority"
        }
        return default_priorities.get(report_type, "Routine")


def suggest_recipients(report_type, fields):
    """
    Suggest recipients based on report content.

    Args:
        report_type (str): The type of report
        fields (dict): Extracted fields from the report

    Returns:
        list: List of suggested recipients
    """
    global model, tokenizer

    # Load the model if not already loaded
    if model is None or tokenizer is None:
        tokenizer, model = load_model()

    # Create a prompt for recipient suggestion
    fields_str = "\n".join([f"{k}: {v}" for k, v in fields.items()])

    prompt = [
        {"role": "system",
         "content": "You are a military communications specialist. Suggest appropriate recipients for military reports."},
        {"role": "user", "content": f"""
This is a {report_type} report with the following content:

{fields_str}

Based on this content, suggest appropriate recipients for this report. 
Return ONLY a comma-separated list of recipient roles (e.g., "Battalion TOC, Company CP, Medical Officer").
No explanation or other text.
"""}
    ]

    try:
        # Apply chat template
        text = tokenizer.apply_chat_template(
            prompt,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )

        # Tokenize the prompt and move to the appropriate device
        input_tokens = tokenizer(text, return_tensors="pt")

        # Handle device placement based on model type
        if hasattr(model, 'device'):
            # If model has a single device
            device = model.device
            # FIX: Keep the tokens as an object, not a dictionary
            input_features = input_tokens.to(device)
        else:
            # For models with device_map (usually quantized models)
            input_features = input_tokens

        # Generate response
        with torch.no_grad():
            generation_args = {
                "max_new_tokens": 100,
                "temperature": 0.2,
                "top_p": 0.95,
                "do_sample": True
            }

            generated_ids = model.generate(
                input_features.input_ids,
                attention_mask=input_features.attention_mask,
                **generation_args
            )

            response = tokenizer.decode(generated_ids[0], skip_special_tokens=True).strip()

        # Process the response into a list of recipients
        if ',' in response:
            recipients = [r.strip() for r in response.split(',')]
        else:
            recipients = [response.strip()]

        # Filter out any empty strings
        recipients = [r for r in recipients if r]

        # Return recipients if we got them
        if recipients:
            return recipients

        # Fallback to default recipients if needed
        base_recipients = {
            "CONTACTREP": ["Battalion TOC", "Company CP", "Adjacent Units"],
            "SITREP": ["Battalion S3", "Company Commander"],
            "MEDEVAC": ["Battalion Aid Station", "MEDEVAC Dispatch", "Company CP"],
            "RECCEREP": ["Battalion S2", "Company CP"]
        }
        return base_recipients.get(report_type, ["Chain of Command"])

    except Exception as e:
        logger.error(f"Error suggesting recipients: {str(e)}")

        # Fallback to default recipients
        base_recipients = {
            "CONTACTREP": ["Battalion TOC", "Company CP", "Adjacent Units"],
            "SITREP": ["Battalion S3", "Company Commander"],
            "MEDEVAC": ["Battalion Aid Station", "MEDEVAC Dispatch", "Company CP"],
            "RECCEREP": ["Battalion S2", "Company CP"]
        }
        return base_recipients.get(report_type, ["Chain of Command"])


def determine_report_type(transcript: str, report_templates: dict) -> tuple:
    """
    Determine report type using enhanced military pattern matching.
    """
    # First convert any phonetic words to standard format
    standardized_transcript = convert_phonetic_to_standard(transcript)
    
    # Use the enhanced determination from military_nlp module
    return determine_report_type_enhanced(standardized_transcript, report_templates)