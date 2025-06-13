import torch
import streamlit as st
import json
import logging
import platform
import os
from transformers import AutoModelForCausalLM, AutoTokenizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables to store the model and tokenizer
model = None
tokenizer = None


def load_model(model_size="0.6B"):
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


def extract_fields_from_text(report_type, transcript, report_templates):
    """
    Extract fields from transcript for a specific report type.

    Args:
        report_type (str): The type of report (e.g., "CONTACTREP")
        transcript (str): The transcript of the audio
        report_templates (dict): Dictionary containing report templates

    Returns:
        dict: Dictionary with extracted fields
    """
    global model, tokenizer

    # Load the model if not already loaded
    if model is None or tokenizer is None:
        tokenizer, model = load_model()

    # Get template for this report type
    template = report_templates.get(report_type, {})
    fields = [field for field in template.get("fields", [])]

    # Create a prompt for the model - use Qwen3 chat format
    field_descriptions = "\n".join([f"- {field['id']}: {field['label']}" for field in fields])

    prompt = [
        {"role": "system",
         "content": "You are a military information extraction assistant. Extract information from military reports accurately and format it as requested."},
        {"role": "user", "content": f"""
I need you to extract structured data from the following military report:

Report Type: {template.get("title", report_type)}
Transcript: {transcript}

Extract the following fields and format your answer ONLY as a JSON object (with no other text):
{field_descriptions}

NOTE: ONLY return the JSON object, nothing else. No explanations or other text.
"""}
    ]

    # Generate response
    try:
        # Apply chat template with thinking mode disabled to keep it focused on extraction
        text = tokenizer.apply_chat_template(
            prompt,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False  # Disable thinking mode for extraction tasks
        )

        # Tokenize the prompt and move to the appropriate device
        input_tokens = tokenizer(text, return_tensors="pt")

        # Handle device placement based on model type
        if hasattr(model, 'device'):
            # If model has a single device
            device = model.device

            # Here's the important fix:
            # Store the device-transferred tensors back into the original format, not as a dict
            input_features = input_tokens.to(device)
        else:
            # For models with device_map (usually quantized models)
            input_features = input_tokens

        # Generate response with sampling (not greedy decoding)
        with torch.no_grad():
            generation_args = {
                "max_new_tokens": 500,
                "temperature": 0.2,
                "top_p": 0.95,
                "do_sample": True
            }

            # Use the correctly formatted input_features
            generated_ids = model.generate(
                input_features.input_ids,
                attention_mask=input_features.attention_mask,
                **generation_args
            )

            response = tokenizer.decode(generated_ids[0], skip_special_tokens=True)

        # Extract the JSON part of the response
        try:
            # Sometimes the model might include "```json" and "```" around the response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].strip()
            else:
                # Find the JSON object in the text
                json_start = response.find('{')
                json_end = response.rfind('}') + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                else:
                    # Fall back to the full response
                    json_str = response

            extracted_fields = json.loads(json_str)

            # Ensure all field IDs are included
            field_ids = [field["id"] for field in fields]
            for field_id in field_ids:
                if field_id not in extracted_fields:
                    extracted_fields[field_id] = ""

            return extracted_fields
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from model response: {str(e)}")
            logger.debug(f"Response was: {response}")
            raise e

    except Exception as e:
        error_msg = f"Error in field extraction: {str(e)}"
        logger.error(error_msg)
        raise e


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


def determine_report_type(transcript, report_templates):
    """
    Determine the report type from the transcript.

    Args:
        transcript (str): The transcript of the audio
        report_templates (dict): Dictionary containing report templates

    Returns:
        str: The determined report type (e.g., "CONTACTREP", "SITREP", etc.)
        float: Confidence score (0-1)
    """
    global model, tokenizer

    # Load the model if not already loaded
    if model is None or tokenizer is None:
        tokenizer, model = load_model()

    # Create a prompt for the model - use Qwen3 chat format
    report_types_str = ", ".join([f"{key} ({template['title']})" for key, template in report_templates.items()])

    prompt = [
        {"role": "system",
         "content": "You are a military report classification assistant. Determine which type of military report is being described."},
        {"role": "user", "content": f"""
Analyze the following transcript and determine which type of military report it represents.

Transcript: {transcript}

Available report types:
{report_types_str}

Return ONLY the report type code (e.g., CONTACTREP, SITREP, MEDEVAC, RECCEREP) that best matches the transcript.
If you're unsure, choose the closest match.
"""}
    ]

    # Generate response
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

        # Generate response with sampling
        with torch.no_grad():
            generation_args = {
                "max_new_tokens": 50,
                "temperature": 0.2,
                "top_p": 0.95,
                "do_sample": True
            }

            generated_ids = model.generate(
                input_features.input_ids,
                attention_mask=input_features.attention_mask,
                **generation_args
            )

            response = tokenizer.decode(generated_ids[0], skip_special_tokens=True)

        # Extract the report type from the response
        # Clean up the response to get just the report type
        for report_type in report_templates.keys():
            if report_type in response:
                return report_type, 0.9  # High confidence if exact match

        # If no exact match, try to find the closest match
        response_clean = response.strip().upper()
        for report_type in report_templates.keys():
            if report_type in response_clean:
                return report_type, 0.8

        # If still no match, use simple keyword matching as fallback
        transcript_lower = transcript.lower()
        matches = {}

        report_keywords = {
            "CONTACTREP": ["contact report", "enemy contact", "engagement", "fire", "attack"],
            "SITREP": ["situation report", "sitrep", "status update", "current situation"],
            "MEDEVAC": ["medical evacuation", "medevac", "casualty", "wounded", "injured", "evacuation request"],
            "RECCEREP": ["reconnaissance report", "recon report", "observation", "surveillance"]
        }

        for report_type, keywords in report_keywords.items():
            matches[report_type] = sum(1 for keyword in keywords if keyword in transcript_lower)

        # Find the report type with the most matches
        best_match = max(matches.items(), key=lambda x: x[1])

        # If no matches, default to SITREP
        if best_match[1] == 0:
            return "SITREP", 0.5

        # Calculate a simple confidence score (0-1)
        total_matches = sum(matches.values())
        confidence = best_match[1] / total_matches if total_matches > 0 else 0.5

        return best_match[0], confidence

    except Exception as e:
        logger.error(f"Error in report type determination: {str(e)}")

        # Use simple keyword matching as fallback
        transcript_lower = transcript.lower()
        matches = {}

        report_keywords = {
            "CONTACTREP": ["contact report", "enemy contact", "engagement", "fire", "attack"],
            "SITREP": ["situation report", "sitrep", "status update", "current situation"],
            "MEDEVAC": ["medical evacuation", "medevac", "casualty", "wounded", "injured", "evacuation request"],
            "RECCEREP": ["reconnaissance report", "recon report", "observation", "surveillance"]
        }

        for report_type, keywords in report_keywords.items():
            matches[report_type] = sum(1 for keyword in keywords if keyword in transcript_lower)

        # Find the report type with the most matches
        best_match = max(matches.items(), key=lambda x: x[1])

        # If no matches, default to SITREP
        if best_match[1] == 0:
            return "SITREP", 0.5

        # Calculate a simple confidence score (0-1)
        total_matches = sum(matches.values())
        confidence = best_match[1] / total_matches if total_matches > 0 else 0.5

        return best_match[0], confidence