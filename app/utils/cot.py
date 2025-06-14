import os
import logging
from ..models.qwen import load_model
import torch
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_chain_of_thought(report_type, report_data):
    """
    Generate a chain-of-thought analysis from report data using Qwen.
    
    This function takes structured report data and generates a narrative analysis
    that explains the implications, recommendations, and potential actions based on
    the report content.
    
    Args:
        report_type (str): The type of report (e.g., "SITREP", "CONTACTREP")
        report_data (dict): Dictionary containing the report field values
        
    Returns:
        str: A markdown-formatted chain-of-thought analysis
    """
    # Load the model
    tokenizer, model = load_model()
    
    # Convert report data to a readable string
    report_content = f"Report Type: {report_type}\n"
    for field_id, value in report_data.items():
        if value:
            report_content += f"{field_id}: {value}\n"
    
    # Create a prompt for the model - use Qwen3 chat format
    prompt = [
        {"role": "system",
         "content": "You are an experienced military intelligence analyst. Analyze reports and provide insightful chain-of-thought analysis, identifying important details, implications, and recommended actions. Your analysis should be clear, concise, and structured."},
        {"role": "user", "content": f"""
        Please analyze the following {report_type} report and provide a chain-of-thought analysis. 
        Include context, implications, and recommended actions based on the report content.
        
        Report details:
        {report_content}
        
        Format your response in markdown with these sections:
        1. Summary
        2. Critical Details
        3. Implications
        4. Recommended Actions
        
        Make sure your analysis is professional, focused on operational relevance, and demonstrates military understanding.
        """}
            ]

    try:
        # Apply chat template with thinking mode enabled for CoT
        text = tokenizer.apply_chat_template(
            prompt,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=True  # Enable thinking mode for CoT
        )

        # Tokenize the prompt and move to the appropriate device
        input_tokens = tokenizer(text, return_tensors="pt")
        
        # Handle device placement based on model type
        if hasattr(model, 'device'):
            # If model has a single device
            device = model.device
            input_features = input_tokens.to(device)
        else:
            # For models with device_map (usually quantized models)
            input_features = input_tokens

        # Generate response with sampling
        with torch.no_grad():
            generation_args = {
                "max_new_tokens": 1500,  # Allow longer responses
                "temperature": 0.7,       # More creative
                "top_p": 0.95,
                "do_sample": True
            }

            generated_ids = model.generate(
                input_features.input_ids,
                attention_mask=input_features.attention_mask,
                **generation_args
            )

            response = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
        
        # Extract the assistant's response
        if "<answer>" in response:
            # Extract content between <answer> tags (for thinking mode)
            response = response.split("<answer>")[1].split("</answer>")[0].strip()
        else:
            # Extract the last part that would be the assistant's reply
            parts = response.split("assistant:")
            if len(parts) > 1:
                response = parts[-1].strip()
        
        return response

    except Exception as e:
        logger.error(f"Error generating chain of thought: {str(e)}")
        return f"Error generating analysis: {str(e)}"

def save_chain_of_thought_to_file(report_type, report_data, cot_analysis):
    """
    Save the chain-of-thought analysis to a file that WinTAK can monitor.
    
    Args:
        report_type (str): The type of report
        report_data (dict): The report data
        cot_analysis (str): The chain-of-thought analysis text
    
    Returns:
        str: Path to the saved file
    """
    # Define the directory for COT outputs
    cot_dir = os.environ.get('COT_OUTPUT_DIR', os.path.expanduser("~/TAK/cot"))
    
    # Create directory if it doesn't exist
    if not os.path.exists(cot_dir):
        try:
            os.makedirs(cot_dir)
            logger.info(f"Created COT output directory: {cot_dir}")
        except Exception as e:
            logger.error(f"Failed to create COT output directory: {e}")
            return None
    
    # Create a filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_title = report_type.lower()
    filename = f"cot_{report_title}_{timestamp}.md"
    file_path = os.path.join(cot_dir, filename)
    
    # Add report metadata as YAML frontmatter
    frontmatter = "---\n"
    frontmatter += f"title: Chain of Thought - {report_type}\n"
    frontmatter += f"date: {datetime.now().isoformat()}\n"
    frontmatter += f"report_type: {report_type}\n"
    frontmatter += "---\n\n"
    
    # Add a header with report details
    header = f"# Chain of Thought Analysis: {report_type}\n\n"
    header += "## Report Details\n\n"
    
    for field_id, value in report_data.items():
        if value:
            header += f"- **{field_id}**: {value}\n"
    
    header += "\n## Analysis\n\n"
    
    # Combine all content
    full_content = frontmatter + header + cot_analysis
    
    # Save to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        logger.info(f"Chain of thought analysis saved to: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to save chain of thought analysis: {e}")
        return None