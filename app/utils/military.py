import re
from datetime import datetime


# This file contains utilities specific to military terminology and standards

def format_mgrs_grid(grid_input):
    """
    Format a Military Grid Reference System (MGRS) coordinate string.
    Standardizes different input formats to the standard format.

    Parameters:
    grid_input - User input grid reference

    Returns:
    formatted_grid - Standardized grid reference
    """
    if not grid_input:
        return ""

    # Remove any spaces and convert to uppercase
    grid_clean = grid_input.replace(" ", "").upper()

    # Try to match the grid pattern
    # Example MGRS: 34TFM12345678
    mgrs_pattern = r'^(\d{1,2}[A-Z]{1})([A-Z]{2})(\d{2,})$'
    match = re.match(mgrs_pattern, grid_clean)

    if match:
        grid_zone = match.group(1)
        square_id = match.group(2)
        coords = match.group(3)

        # Ensure even number of digits in coordinates
        if len(coords) % 2 != 0:
            coords = coords + "0"

        # Split coordinates into easting and northing
        half_len = len(coords) // 2
        easting = coords[:half_len]
        northing = coords[half_len:]

        # Format as standard MGRS
        formatted_grid = f"{grid_zone} {square_id} {easting} {northing}"
        return formatted_grid

    return grid_input  # Return original if not matching pattern


def format_military_datetime(datetime_input):
    """
    Format a datetime string to the military standard format.

    Parameters:
    datetime_input - User input datetime string

    Returns:
    formatted_datetime - Standardized datetime string
    """
    if not datetime_input:
        # Return current date-time in military format
        return datetime.now().strftime("%d%b%y %H%MZ").upper()

    # Try to parse various formats (simplified for MVP)
    # In a real implementation, this would be more robust
    try:
        # If it's already in the right format, return it
        if re.match(r'^\d{2}[A-Za-z]{3}\d{2} \d{4}Z$', datetime_input.upper()):
            return datetime_input.upper()

        # Try to parse as ISO format
        dt = datetime.fromisoformat(datetime_input.replace('Z', '+00:00'))
        return dt.strftime("%d%b%y %H%MZ").upper()
    except ValueError:
        # Try other common formats
        try:
            for fmt in ["%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M"]:
                try:
                    dt = datetime.strptime(datetime_input, fmt)
                    return dt.strftime("%d%b%y %H%MZ").upper()
                except ValueError:
                    continue
        except:
            pass

    # If all parsing fails, return original
    return datetime_input


def validate_callsign(callsign):
    """
    Validate and format a military callsign.

    Parameters:
    callsign - User input callsign

    Returns:
    (valid, formatted_callsign) - Tuple with validation result and formatted callsign
    """
    if not callsign:
        return (False, "")

    # Remove excess whitespace and convert to uppercase
    formatted = callsign.strip().upper()

    # In a real implementation, this would check against
    # a list of valid callsigns or patterns
    valid = len(formatted) > 0

    return (valid, formatted)


def format_frequencies(frequency_input):
    """
    Format radio frequencies to standard military format.

    Parameters:
    frequency_input - User input frequency

    Returns:
    formatted_frequency - Standardized frequency
    """
    if not frequency_input:
        return ""

    # Remove spaces
    freq_clean = frequency_input.replace(" ", "")

    # Try to match frequency patterns
    # VHF/UHF: 30.00 MHz, 150.00 MHz
    vhf_uhf_pattern = r'(\d+\.?\d*)(?:MHz|mhz|MHZ)?'
    match = re.match(vhf_uhf_pattern, freq_clean)

    if match:
        freq_value = float(match.group(1))
        return f"{freq_value:.2f} MHz"

    # HF: 5.123 kHz
    hf_pattern = r'(\d+\.?\d*)(?:kHz|khz|KHZ)?'
    match = re.match(hf_pattern, freq_clean)

    if match:
        freq_value = float(match.group(1))
        return f"{freq_value:.3f} kHz"

    return frequency_input  # Return original if not matching


def get_nato_phonetic(text):
    """
    Convert text to NATO phonetic alphabet.

    Parameters:
    text - Input text

    Returns:
    phonetic - Text with NATO phonetic substitutions
    """
    nato_phonetic = {
        'A': 'Alpha',
        'B': 'Bravo',
        'C': 'Charlie',
        'D': 'Delta',
        'E': 'Echo',
        'F': 'Foxtrot',
        'G': 'Golf',
        'H': 'Hotel',
        'I': 'India',
        'J': 'Juliet',
        'K': 'Kilo',
        'L': 'Lima',
        'M': 'Mike',
        'N': 'November',
        'O': 'Oscar',
        'P': 'Papa',
        'Q': 'Quebec',
        'R': 'Romeo',
        'S': 'Sierra',
        'T': 'Tango',
        'U': 'Uniform',
        'V': 'Victor',
        'W': 'Whiskey',
        'X': 'X-ray',
        'Y': 'Yankee',
        'Z': 'Zulu',
        '0': 'Zero',
        '1': 'One',
        '2': 'Two',
        '3': 'Three',
        '4': 'Four',
        '5': 'Five',
        '6': 'Six',
        '7': 'Seven',
        '8': 'Eight',
        '9': 'Nine'
    }

    result = []
    for char in text.upper():
        if char in nato_phonetic:
            result.append(nato_phonetic[char])
        else:
            result.append(char)

    return ' '.join(result)


def format_for_radio_transmission(text):
    """
    Format text for radio transmission, adding appropriate terminologies.

    Parameters:
    text - Input text

    Returns:
    formatted_text - Text formatted for radio transmission
    """
    # Add line breaks and formatting
    lines = text.split('\n')
    formatted_lines = []

    for i, line in enumerate(lines):
        # First line gets "THIS IS" prefix
        if i == 0:
            formatted_lines.append(f"THIS IS {line}, OVER")
        # Last line gets "OUT" suffix
        elif i == len(lines) - 1:
            formatted_lines.append(f"{line}, OUT")
        # Other lines get "I SAY AGAIN" for emphasis on key points
        elif ":" in line and any(keyword in line.upper() for keyword in ["EMERGENCY", "URGENT", "CRITICAL"]):
            parts = line.split(":", 1)
            formatted_lines.append(f"{parts[0]}, I SAY AGAIN, {parts[0]}: {parts[1]}")
        # Regular lines just get "OVER" suffix
        else:
            formatted_lines.append(f"{line}, OVER")

    return '\n'.join(formatted_lines)


def get_report_precedence(report_type, content=None):
    """
    Determine the appropriate precedence level for a report.

    Parameters:
    report_type - Type of report
    content - Report content (optional)

    Returns:
    precedence - Recommended precedence level
    """
    # Default precedence by report type
    default_precedence = {
        "CONTACTREP": "Immediate",
        "SITREP": "Routine",
        "MEDEVAC": "Flash",
        "RECCEREP": "Priority"
    }

    # In a real implementation, this would analyze the content
    # to determine if the precedence should be escalated

    # For the MVP, just return the default precedence
    return default_precedence.get(report_type, "Routine")