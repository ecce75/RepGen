import re
import json
import logging
from typing import Dict, List, Tuple, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Military communication examples for few-shot learning
MILITARY_EXTRACTION_EXAMPLES = {
    "MEDEVAC": {
        "examples": [
            {
                "transmission": "DUSTOFF this is RAZOR 3-1, break, 9-line MEDEVAC follows, over. Line 1, grid 18T WL niner-four-three-four-five six-seven-eight-niner-zero, break. Line 2, freq four-seven-point-five-five, call sign RAZOR 3-1, break. Line 3, two urgent surgical, one priority, break. Line 4, alpha, no special equipment, wait correction, need ventilator for urgent surgical, break. Line 5, two litter, one ambulatory, break. Line 6, november, no enemy in area, break. Line 7, smoke purple, break. Line 8, alpha, US military, break. Line 9, none, how copy, over.",
                "extraction_process": """
                Let me extract each field step by step:

                Line 1 (Location): "grid 18T WL niner-four-three-four-five six-seven-eight-niner-zero"
                - Converting phonetic: niner = 9, so grid is "18TWL9434567890"
                - Extract: "18TWL9434567890"

                Line 2 (Frequency/Callsign): "freq four-seven-point-five-five, call sign RAZOR 3-1"
                - Frequency: "47.55"
                - Callsign: "RAZOR 3-1"

                Line 3 (Number patients by precedence): "two urgent surgical, one priority"
                - Total patients: 3
                - Breaking down: 2 urgent surgical, 1 priority
                - Extract: "2 urgent surgical, 1 priority"

                Line 4 (Special equipment): "alpha, no special equipment, wait correction, need ventilator"
                - Initial: "None" (alpha = A = None)
                - Correction: "need ventilator"
                - Final extract: "Ventilator" (take the correction)

                Line 5 (Patient type): "two litter, one ambulatory"
                - Litter: "2"
                - Ambulatory: "1"

                Line 6 (Security): "november, no enemy in area"
                - November = N = No enemy
                - Extract: "N"

                Line 7 (Marking method): "smoke purple"
                - Extract: "Smoke - Purple"

                Line 8 (Nationality): "alpha, US military"
                - Alpha = A = US Military
                - Extract: "A"

                Line 9 (NBC Contamination): "none"
                - Extract: "None"

                Reporting unit from initial call: "RAZOR 3-1"
                """,
                "final_output": {
                    "location": "18TWL9434567890",
                    "frequency": "47.55",
                    "reporting_unit": "RAZOR 3-1",
                    "number_patients": "3",
                    "patient_precedence": "2 urgent surgical, 1 priority",
                    "special_equipment": "Ventilator",
                    "number_litter": "2",
                    "number_ambulatory": "1",
                    "security_at_pickup": "N",
                    "method_of_marking": "Smoke - Purple",
                    "patient_nationality": "A",
                    "nbc_contamination": "None"
                }
            },
            {
                "transmission": "Any station this net, this is VIPER 2, emergency MEDEVAC. We got three casualties from IED strike. Uh, two are pretty bad, gonna need immediate evac. Third guy is walking wounded but needs treatment. We're at... shit, standby... okay, grid one-eight tango whiskey lima eight-seven-six-five four-three-two-one. Need a bird with trauma team, these guys are bleeding bad.",
                "extraction_process": """
                    This is informal/emergency communication. Let me extract the 9-line elements present:

                    Callsign identification: "this is VIPER 2" 
                    - Reporting unit: "VIPER 2"

                    Location: "grid one-eight tango whiskey lima eight-seven-six-five four-three-two-one"
                    - Converting spoken to MGRS: "18TWL8765 4321" (assuming 10-digit)
                    - Note: Under stress, incomplete grid given

                    Casualties mentioned: "three casualties" with "two are pretty bad" and "third guy is walking wounded"
                    - Total patients: 3
                    - By precedence: 2 immediate (pretty bad), 1 priority (walking wounded)
                    - Patient type: 2 litter (pretty bad), 1 ambulatory (walking wounded)

                    Equipment: "Need a bird with trauma team"
                    - "Trauma team" implies need for advanced medical support
                    - No specific equipment mentioned, but urgency suggests possible need

                    Nature of injuries: "IED strike" and "bleeding bad"
                    - Mechanism: IED (for remarks/context)
                    - Urgent surgical likely due to traumatic bleeding

                    Security: Not mentioned (default to unknown)
                    Marking: Not mentioned
                    Frequency: Not mentioned (using current net)
                    """,
                "final_output": {
                    "location": "18TWL87654321",
                    "frequency": "Current net",
                    "reporting_unit": "VIPER 2",
                    "number_patients": "3",
                    "patient_precedence": "2 immediate, 1 priority",
                    "special_equipment": "None specified",
                    "number_litter": "2",
                    "number_ambulatory": "1",
                    "security_at_pickup": "Unknown",
                    "method_of_marking": "TBD",
                    "patient_nationality": "A",
                    "nbc_contamination": "None",
                    "injury_type": "IED blast, traumatic bleeding"
                }
            }
        ],
        "negative_examples": [
            {
                "common_error": "Including conversational padding in equipment field",
                "wrong": {"special_equipment": "Well, initially I thought we didn't need anything special but now thinking about it, probably should have a ventilator ready just in case"},
                "correct": {"special_equipment": "Ventilator"},
                "explanation": "Extract only the actual equipment needed, not the thought process"
            },
            {
                "common_error": "Not converting phonetic numbers",
                "wrong": {"location": "18TWL niner-four-three-four"},
                "correct": {"location": "18TWL9434"},
                "explanation": "Convert phonetic numbers (niner=9, fife=5) to digits"
            }
        ],
        "field_patterns": {
            "precedence_mapping": {
                "urgent": ["urgent", "immediate", "flash", "emergency", "critical", "bad shape"],
                "priority": ["priority", "urgent surgical", "needs surgery"],
                "routine": ["routine", "walking wounded", "ambulatory", "stable"],
                "convenience": ["convenience", "return to duty", "minor"]
            },
            "security_codes": {
                "N": ["november", "no enemy", "secure", "cold LZ"],
                "P": ["papa", "possible enemy", "unknown", "unclear"],
                "E": ["echo", "enemy in area", "hot LZ", "troops in contact"],
                "X": ["x-ray", "armed escort required", "heavy contact"]
            }
        }
    },
    "CONTACTREP": {
        "examples": [
            {
                "transmission": "THUNDER 6 this is THUNDER 3, CONTACT REPORT, over. Time 1435 local, grid 18S UH eight-four-two-one three-six-five-four. Observing approximately platoon-sized element, that's three-zero personnel, moving north along MSR TAMPA. Mix of technical vehicles and dismounts. Weapons observed include small arms and possible RPGs. Enemy is approximately 800 meters east of our position. We are not engaged at this time, continuing to observe, how copy?",
                "extraction_process": """
                    Parsing military contact report:

                    Reporting unit: "THUNDER 3" (from "this is THUNDER 3")
                    Higher HQ: "THUNDER 6" (battalion commander)

                    Time: "1435 local"
                    - Extract: "1435L"

                    Location: "grid 18S UH eight-four-two-one three-six-five-four"
                    - Converting: "18SUH84213654"

                    Enemy size: "platoon-sized element, that's three-zero personnel"
                    - Phonetic "three-zero" = 30
                    - Size: "Platoon (30 personnel)"

                    Activity: "moving north along MSR TAMPA"
                    - Extract: "Moving north on MSR TAMPA"

                    Equipment: "Mix of technical vehicles and dismounts. Weapons observed include small arms and possible RPGs"
                    - Extract: "Technical vehicles, small arms, possible RPGs"

                    Distance: "800 meters east"
                    - Extract: "800m east"

                    Current status: "not engaged at this time, continuing to observe"
                    - Extract: "Observing, not engaged"
                    """,
                "final_output": {
                    "reporting_unit": "THUNDER 3",
                    "time_of_contact": "1435L",
                    "location": "18SUH84213654",
                    "enemy_size": "Platoon (30 personnel)",
                    "enemy_activity": "Moving north on MSR TAMPA",
                    "enemy_equipment": "Technical vehicles, small arms, possible RPGs",
                    "distance_direction": "800m east",
                    "friendly_status": "Observing, not engaged",
                    "unit_location": "Undisclosed"
                }
            }
        ],
        "field_patterns": {
            "size_indicators": {
                "team": [2, 4],
                "squad": [8, 13],
                "platoon": [16, 44],
                "company": [60, 200],
                "battalion": [300, 1000]
            },
            "activity_keywords": ["moving", "stationary", "digging in", "attacking", "withdrawing", "patrolling", "establishing", "occupying"]
        }
    },
    "SITREP": {
        "examples": [
            {
                "transmission": "APACHE 6, this is APACHE 3, SITREP follows. Current location grid 18T WK two-three-four-five six-seven-eight-niner. All personnel accounted for, no casualties. Ammunition green, fuel amber at 40 percent, expected to go black in four hours without resupply. Currently established in blocking position vicinity checkpoint 7. No enemy contact last 24 hours. Request fuel resupply NLT 1800 hours, over.",
                "extraction_process": """
                    Extracting SITREP elements:

                    Unit identification: "APACHE 3" reporting to "APACHE 6"

                    Location: "grid 18T WK two-three-four-five six-seven-eight-niner"
                    - Converting: "18TWK23456789"

                    Personnel status: "All personnel accounted for, no casualties"
                    - Status: "100% strength, no casualties"

                    Supply status using color codes:
                    - Ammunition: "green" = 80-100% (full supply)
                    - Fuel: "amber at 40 percent" = 40% remaining
                    - Note: "expected to go black in four hours" (black = 0-20%)

                    Current activity: "established in blocking position vicinity checkpoint 7"

                    Enemy situation: "No enemy contact last 24 hours"

                    Request: "fuel resupply NLT 1800 hours"
                    - NLT = No Later Than
                    """,
                "final_output": {
                    "reporting_unit": "APACHE 3",
                    "location": "18TWK23456789",
                    "personnel_status": "100% strength, no casualties",
                    "ammunition_status": "Green (80-100%)",
                    "fuel_status": "Amber (40%), black in 4 hours",
                    "current_activity": "Blocking position at checkpoint 7",
                    "enemy_activity": "No contact last 24 hours",
                    "requests": "Fuel resupply NLT 1800"
                }
            }
        ],
        "field_patterns": {
            "supply_color_codes": {
                "green": "80-100% (full supply)",
                "amber": "40-79% (adequate)",
                "red": "20-39% (critical)",
                "black": "0-19% (emergency)"
            }
        }
    }
}

# Brevity codes and military terminology
MILITARY_BREVITY_CODES = {
    "affirmative": "yes",
    "negative": "no",
    "roger": "understood",
    "wilco": "will comply",
    "standby": "wait",
    "say again": "repeat",
    "correction": "disregard previous, correct info follows",
    "break": "separation between parts",
    "over": "end transmission, expect response",
    "out": "end transmission, no response expected",
    "actual": "commander/leader",
    "vic": "vicinity of",
    "pos": "position",
    "freq": "frequency",
    "NLT": "no later than",
    "ASAP": "as soon as possible"
}

# Report type detection patterns
REPORT_TYPE_INDICATORS = {
    "CONTACTREP": {
        "keywords": ["enemy contact", "troops in contact", "TIC", "engaged", "receiving fire", 
                    "contact report", "hostile", "enemy activity", "under fire", "engagement"],
        "priority_indicators": ["immediate", "troops in contact", "casualty", "under fire"],
        "weight": 1.5
    },
    "MEDEVAC": {
        "keywords": ["casualty", "wounded", "injured", "medevac", "medical evacuation", 
                    "nine line", "9 line", "patient", "urgent surgical", "priority patient",
                    "litter", "ambulatory", "ventilator", "bleeding"],
        "priority_indicators": ["urgent", "flash", "immediate", "critical"],
        "weight": 2.0
    },
    "SITREP": {
        "keywords": ["situation report", "sitrep", "status update", "current situation",
                    "nothing to report", "all quiet", "routine", "normal operations"],
        "priority_indicators": ["routine", "no change"],
        "weight": 0.5
    },
    "SPOTREP": {
        "keywords": ["spot report", "spotrep", "observed", "sighting", "surveillance",
                    "enemy movement", "vehicle spotted", "personnel observed"],
        "priority_indicators": ["immediate", "priority"],
        "weight": 1.0
    },
    "SALUTE": {
        "keywords": ["size", "activity", "location", "unit", "time", "equipment",
                    "salute report", "enemy observation"],
        "priority_indicators": ["priority", "immediate"],
        "weight": 1.2
    }
}

# Field extraction patterns
FIELD_EXTRACTION_PATTERNS = {
    "grid_coordinates": r"(?:grid\s*)?([0-9]{2}[A-Z]{1,2}\s*[0-9]{4,10})",
    "mgrs": r"([0-9]{1,2}[A-Z]{1,3}\s*[A-Z]{2}\s*[0-9]{5}\s*[0-9]{5})",
    "callsign": r"(?:this is|callsign)\s+([A-Z][A-Z0-9\-]+(?:\s+[0-9]+)?)",
    "unit_identifier": r"(?:unit|element|team|squad|platoon|company)\s+([A-Z0-9\-]+)",
    "time_group": r"([0-9]{2}[0-9]{2}(?:Z|L)?(?:\s+[A-Z]{3}\s+[0-9]{2})?)",
    "precedence": r"(?:precedence|priority)[\s:]+?(routine|priority|immediate|flash)",
    "equipment_needed": r"(?:need|require|request)\s+(?:a\s+)?(\w+(?:\s+\w+)?)"
}

# Phonetic conversion maps
PHONETIC_NUMBERS = {
    "zero": "0", "one": "1", "two": "2", "tree": "3", "three": "3",
    "fower": "4", "four": "4", "fife": "5", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "niner": "9", "nine": "9"
}

PHONETIC_ALPHABET = {
    "alpha": "A", "bravo": "B", "charlie": "C", "delta": "D", "echo": "E",
    "foxtrot": "F", "golf": "G", "hotel": "H", "india": "I", "juliet": "J",
    "kilo": "K", "lima": "L", "mike": "M", "november": "N", "oscar": "O",
    "papa": "P", "quebec": "Q", "romeo": "R", "sierra": "S", "tango": "T",
    "uniform": "U", "victor": "V", "whiskey": "W", "x-ray": "X", "xray": "X",
    "yankee": "Y", "zulu": "Z"
}

def convert_phonetic_to_standard(text: str) -> str:
    """Convert military phonetic alphabet and numbers to standard format."""
    result = text
    
    # Convert phonetic numbers
    for phonetic, digit in PHONETIC_NUMBERS.items():
        result = re.sub(r'\b' + phonetic + r'\b', digit, result, flags=re.IGNORECASE)
    
    # Convert phonetic alphabet for single letter references
    for phonetic, letter in PHONETIC_ALPHABET.items():
        # Only convert when it appears to be used as a letter code
        result = re.sub(r'\b' + phonetic + r'\b(?=\s*[,\-\s]|$)', letter, result, flags=re.IGNORECASE)
    
    return result

def extract_callsign_from_transcript(transcript: str) -> Optional[str]:
    """Extract military callsign from radio transcript."""
    callsign_patterns = [
        r"this is ([A-Z][A-Z0-9\-\s]+?)(?:,|\.|$)",
        r"([A-Z][A-Z0-9\-\s]+?) calling",
        r"from ([A-Z][A-Z0-9\-\s]+?)(?:,|\.|$)",
        r"callsign ([A-Z][A-Z0-9\-\s]+?)(?:,|\.|$)",
        r"^([A-Z][A-Z0-9\-\s]+?) to",
    ]
    
    transcript_upper = transcript.upper()
    for pattern in callsign_patterns:
        match = re.search(pattern, transcript_upper, re.IGNORECASE)
        if match:
            callsign = match.group(1).strip()
            if len(callsign) > 2 and not callsign.isdigit():
                return callsign
    
    return None

def clean_field_value(field_type: str, raw_value: str) -> str:
    """Clean and extract specific information from raw field values."""
    # Remove filler words
    filler_patterns = [
        r"(?:I think|maybe|actually|wait|um|uh|like|you know)",
        r"(?:might need|probably need|gonna need)",
        r"No special gear needed[,.]?\s*"
    ]
    
    cleaned = raw_value
    for pattern in filler_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    
    # Field-specific extraction
    if field_type in ["special_equipment", "equipment_needed"]:
        equipment_keywords = ["ventilator", "hoist", "extraction equipment", 
                            "litter", "stretcher", "oxygen", "IV", "splint"]
        found_equipment = []
        for equipment in equipment_keywords:
            if equipment.lower() in cleaned.lower():
                found_equipment.append(equipment)
        
        if found_equipment:
            return ", ".join(found_equipment)
        elif "none" in cleaned.lower() or "nothing" in cleaned.lower():
            return "None"
    
    elif field_type in ["location", "pickup_location", "grid"]:
        # Try to extract grid coordinates
        grid_match = re.search(FIELD_EXTRACTION_PATTERNS["grid_coordinates"], cleaned)
        if grid_match:
            return grid_match.group(1)
        
        # Extract landmark references
        location_match = re.search(r"(?:at|near|by)\s+(\w+(?:\s+\w+){0,3})", cleaned, re.IGNORECASE)
        if location_match:
            return location_match.group(1)
    
    elif field_type == "number_patients":
        # Extract numbers
        number_words = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
                       "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
        
        digit_match = re.search(r"(\d+)", cleaned)
        if digit_match:
            return digit_match.group(1)
        
        for word, digit in number_words.items():
            if word in cleaned.lower():
                return digit
    
    # Default: return first sentence or 50 chars
    first_sentence = cleaned.split('.')[0].strip()
    if len(first_sentence) > 50:
        return first_sentence[:50] + "..."
    return first_sentence

def determine_report_type_enhanced(transcript: str, report_templates: dict) -> Tuple[str, float]:
    """Enhanced report type determination using weighted keyword matching."""
    transcript_lower = transcript.lower()
    scores = {}
    
    for report_type, indicators in REPORT_TYPE_INDICATORS.items():
        if report_type not in report_templates:
            continue
            
        score = 0
        keyword_matches = 0
        
        for keyword in indicators["keywords"]:
            if keyword in transcript_lower:
                keyword_matches += 1
                score += indicators["weight"]
        
        for priority_word in indicators["priority_indicators"]:
            if priority_word in transcript_lower:
                score += 0.5
        
        if keyword_matches > 0:
            scores[report_type] = score / len(indicators["keywords"])
        else:
            scores[report_type] = 0
    
    if scores:
        best_match = max(scores.items(), key=lambda x: x[1])
        confidence = min(best_match[1] / 2.0, 1.0)
        
        if confidence < 0.3:
            for report_type in report_templates:
                if report_type.lower() in transcript_lower:
                    return report_type, 0.8
        
        return best_match[0], confidence
    
    return "SITREP", 0.3

# Fixed prompt engineering functions for military_nlp.py
# Replace the create_military_conditioned_prompt function with this improved version

def process_grid_sequence(text: str) -> str:
    """Convert spelled-out grid coordinates to proper format."""
    # Split by commas or spaces
    parts = re.split(r'[,\s]+', text)
    result = []
    
    for part in parts:
        part = part.strip().upper()
        if not part:
            continue
            
        # Check if it's a phonetic letter
        phonetic_found = False
        for phonetic, letter in PHONETIC_ALPHABET.items():
            if part == phonetic.upper():
                result.append(letter)
                phonetic_found = True
                break
        
        # If not phonetic, check if it's a number
        if not phonetic_found:
            # Check phonetic numbers
            for phonetic, digit in PHONETIC_NUMBERS.items():
                if part == phonetic.upper():
                    result.append(digit)
                    phonetic_found = True
                    break
            
            # If still not found, keep as is (likely a digit)
            if not phonetic_found and part.isdigit():
                result.append(part)
    
    return ''.join(result)

def preprocess_military_transcript(transcript: str) -> str:
    """
    Preprocess transcript to handle military-specific speech patterns.
    Handles comma-separated digit sequences and phonetic spelling.
    """
    # First, handle comma-separated numbers that represent single values
    # Pattern for frequency-like sequences (e.g., "1, 2, 4, 0.5" -> "124.05")
    def merge_frequency(match):
        parts = match.group(0).split(',')
        # If last part has decimal, keep it
        if '.' in parts[-1].strip():
            integer_part = ''.join(p.strip() for p in parts[:-1])
            decimal_part = parts[-1].strip()
            return f"{integer_part}.{decimal_part.split('.')[-1]}"
        else:
            return ''.join(p.strip() for p in parts)
    
    # Match sequences of comma-separated single digits possibly ending with decimal
    freq_pattern = r'\b\d\s*,\s*\d(?:\s*,\s*\d)*(?:\s*,\s*\d+\.\d+)?\b'
    transcript = re.sub(freq_pattern, merge_frequency, transcript)
    
    # Handle grid coordinates with mixed phonetic and numbers
    # "3, 5, Victor, November, Foxtrot, 6, 1, 1, 0, 5, 1, 9, 7" should become "35VNF611051197"
    
    # Look for grid patterns - sequence starting with digits followed by phonetic letters
    grid_pattern = r'(?:grid\s+)?((?:\d+\s*,\s*)+(?:[A-Z][a-z]+\s*,\s*)+(?:\d+\s*,?\s*)+)'
    
    def replace_grid(match):
        grid_text = match.group(1)
        processed = process_grid_sequence(grid_text)
        return f"grid {processed}"
    
    transcript = re.sub(grid_pattern, replace_grid, transcript, flags=re.IGNORECASE)
    
    # Convert standalone phonetic words
    transcript = convert_phonetic_to_standard(transcript)
    
    return transcript

def create_military_conditioned_prompt(report_type: str, transcript: str, template: dict) -> list:
    """
    Create a military-conditioned prompt that prevents example data leakage.
    """
    # Preprocess the transcript first
    processed_transcript = preprocess_military_transcript(transcript)
    
    report_examples = MILITARY_EXTRACTION_EXAMPLES.get(report_type, {})
    
    # Build learning examples but with clear separation
    examples_text = ""
    if "examples" in report_examples:
        examples_text = "\n**LEARNING EXAMPLES - DO NOT COPY THESE VALUES:**\n"
        examples_text += "These examples show HOW to extract, not WHAT to extract:\n\n"
        
        for i, example in enumerate(report_examples["examples"], 1):
            examples_text += f"**Learning Example {i} - Pattern Only:**\n"
            first_line = example['extraction_process'].split('\n')[0]
            examples_text += f"Example shows: {first_line}\n"
            examples_text += "Key lesson: Identify the pattern, extract from YOUR transcript\n\n"
    
    # Build field instructions with anti-copying warnings
    field_instructions = []
    for field in template.get("fields", []):
        field_id = field["id"]
        field_label = field["label"]
        
        if field_id == "reporting_unit" or field_id == "callsign":
            instruction = f"- {field_id}: Extract callsign from the CURRENT transcript only. Common patterns: 'this is [CALLSIGN]' or unit names like 'Warhawk 2-1'. DO NOT use RAZOR, THUNDER, or any callsign from examples."
        elif "location" in field_id or "grid" in field_id:
            instruction = f"- {field_id}: Extract the grid from THIS transcript. Look for sequences of numbers and phonetic letters after 'grid'. Convert phonetic to letters but use ONLY coordinates from this message."
        elif field_id == "method_of_marking":
            instruction = f"- {field_id}: Extract ONLY the marking method mentioned in THIS transcript (smoke color, panels, etc). DO NOT default to purple smoke or example values."
        elif field_id == "frequency":
            instruction = f"- {field_id}: Extract the radio frequency from THIS transcript. May be spoken as separate digits that need combining (e.g., '1 2 4 0.5' = '124.05')."
        else:
            instruction = f"- {field_id}: {field_label} - Extract from current transcript only."
        
        field_instructions.append(instruction)
    
    # Build the prompt with strong anti-copying instructions
    system_prompt = f"""You are a military radio operator extracting information from tactical transmissions.

    CRITICAL RULES:
    1. **NEVER copy values from examples** - Examples show patterns, not data to reuse
    2. **ONLY extract from the current transcript** - Every value must come from the message below
    3. **Convert phonetic alphabet and numbers** but keep the actual values from this message
    4. **If information is not in THIS transcript, leave the field empty** - Do not use defaults

    Key conversions:
    - Phonetic letters: Alpha=A, Bravo=B, Charlie=C... Victor=V, November=N, Foxtrot=F
    - Phonetic numbers: One=1, Two=2... Niner=9
    - Comma-separated digits may form single numbers (1,2,4,0.5 = 124.05)

    DO NOT USE THESE EXAMPLE VALUES: RAZOR, THUNDER, 18TWL, purple smoke, 47.55 - these are learning examples only!"""

    user_prompt = f"""Extract information from THIS {template.get('title', report_type)} transmission ONLY.

    **CURRENT TRANSCRIPT TO PROCESS:**
    Original: "{transcript}"
    Preprocessed: "{processed_transcript}"

    **Required fields - extract ONLY from above transcript:**
    {chr(10).join(field_instructions)}

    Remember:
    - Warhawk 2-1 is NOT RAZOR 3-1
    - The grid in THIS message is NOT 18TWL9434567890
    - The smoke color mentioned HERE is what to extract, not purple
    - Every value must come from THIS transcript

    Provide ONLY a JSON object with values found in THIS message. Leave fields empty if not mentioned."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def validate_military_extraction(report_type: str, extracted_fields: dict) -> dict:
    """Validate and correct extracted fields using military logic rules."""
    validated = extracted_fields.copy()
    
    if report_type == "MEDEVAC":
        # Adjust precedence based on equipment
        if validated.get("special_equipment", "").lower() in ["ventilator", "trauma team"]:
            if validated.get("patient_precedence", "").lower() == "priority":
                validated["patient_precedence"] = "Urgent surgical"
        
        # Ensure patient counts add up
        try:
            total = int(validated.get("number_patients", 0))
            litter = int(validated.get("number_litter", 0))
            ambulatory = int(validated.get("number_ambulatory", 0))
            
            if litter + ambulatory != total and total > 0:
                if litter > 0 and ambulatory == 0:
                    ambulatory = total - litter
                elif ambulatory > 0 and litter == 0:
                    litter = total - ambulatory
                else:
                    litter = max(1, total // 2)
                    ambulatory = total - litter
                
                validated["number_litter"] = str(litter)
                validated["number_ambulatory"] = str(ambulatory)
        except (ValueError, TypeError):
            pass
    
    elif report_type == "CONTACTREP":
        # Ensure enemy size has count
        size_field = validated.get("enemy_size", "")
        if size_field and not any(char.isdigit() for char in size_field):
            size_map = {"team": "4", "squad": "9", "platoon": "30", "company": "120"}
            for unit, count in size_map.items():
                if unit in size_field.lower():
                    validated["enemy_size"] = f"{size_field} (~{count} personnel)"
                    break
    
    # Universal validations
    if "reporting_unit" in validated and validated["reporting_unit"]:
        validated["reporting_unit"] = validated["reporting_unit"].upper()
    
    # Validate grid coordinates
    for field in ["location", "grid", "pickup_location"]:
        if field in validated and validated[field]:
            grid = validated[field].upper().replace(" ", "")
            if re.match(r"^[0-9]{1,2}[A-Z]{1,3}[A-Z]{2}[0-9]+$", grid):
                validated[field] = grid
    
    return validated

def post_process_extracted_fields(report_type: str, fields: dict, transcript: str) -> dict:
    """Post-process extracted fields to ensure military reporting standards."""
    processed_fields = {}
    
    # Try to extract callsign if missing
    if "reporting_unit" not in fields or not fields.get("reporting_unit"):
        callsign = extract_callsign_from_transcript(transcript)
        if callsign:
            fields["reporting_unit"] = callsign
    
    # Process each field
    for field_id, value in fields.items():
        if value and isinstance(value, str):
            cleaned_value = clean_field_value(field_id, value)
            processed_fields[field_id] = cleaned_value
        else:
            processed_fields[field_id] = value or ""
    
    # Add report-specific defaults
    if report_type == "MEDEVAC":
        medevac_defaults = {
            "location": "Grid TBD",
            "frequency": "Primary",
            "number_patients": "1",
            "special_equipment": "None",
            "security_at_pickup": "N",
            "method_of_marking": "Smoke",
            "patient_nationality": "US Military",
            "nbc_contamination": "None"
        }
        for field, default in medevac_defaults.items():
            if field not in processed_fields or not processed_fields[field]:
                processed_fields[field] = default
    
    return processed_fields

# Additional fallback extraction logic to add to military_nlp.py
# This provides regex-based extraction when AI fails

def extract_fields_with_fallback(transcript: str, report_type: str) -> dict:
    """
    Fallback field extraction using regex patterns when AI extraction fails.
    This ensures critical fields are captured even if the model hallucinates.
    """
    fields = {}
    
    # Preprocess transcript
    processed = preprocess_military_transcript(transcript)
    
    # Extract callsign with multiple patterns
    callsign_patterns = [
        r'(?:this is|I\'m|we\'re)\s+([A-Z][a-z]+[\s,]+\d+[\s,]+\d+)',  # "Warhawk, 2, 1"
        r'(?:callsign|call sign)\s+([A-Z][a-z]+[\s\-]+\d+[\s\-]+\d+)',
        r'^([A-Z][a-z]+[\s,]+\d+[\s,]+\d+)',  # At start of transmission
    ]
    
    for pattern in callsign_patterns:
        match = re.search(pattern, transcript, re.IGNORECASE)
        if match:
            # Clean up the callsign
            callsign = match.group(1).strip()
            # Replace commas and multiple spaces with single space or dash
            callsign = re.sub(r'[,\s]+', ' ', callsign).strip()
            fields['reporting_unit'] = callsign.upper()
            break
    
    # Extract grid coordinates
    grid_patterns = [
        r'grid\s+([\d\s,]+[A-Za-z\s,]+[\d\s,]+)',  # Mixed format
        r'grid\s+([0-9A-Z]+)',  # Already processed format
        r'(?:location|position|at)\s+grid\s+([\d\sA-Za-z,]+)',
    ]
    
    for pattern in grid_patterns:
        match = re.search(pattern, transcript, re.IGNORECASE)
        if match:
            grid_text = match.group(1)
            # Process the grid text
            if ',' in grid_text or re.search(r'[A-Za-z]{2,}', grid_text):
                # Contains phonetic spelling
                fields['location'] = process_grid_sequence(grid_text)
            else:
                fields['location'] = grid_text.upper().replace(' ', '')
            break
    
    # Extract frequency
    freq_patterns = [
        r'(?:freq|frequency)\s+([\d\s,\.]+)',
        r'(?:radio|channel)\s+([\d\s,\.]+)',
        r'(?:on)\s+([\d\s,\.]+)\s+(?:MHz|megahertz)',
    ]
    
    for pattern in freq_patterns:
        match = re.search(pattern, transcript, re.IGNORECASE)
        if match:
            freq_text = match.group(1)
            # Clean up frequency
            if ',' in freq_text:
                # Handle comma-separated format
                parts = freq_text.split(',')
                if '.' in parts[-1]:
                    # Last part has decimal
                    integer = ''.join(p.strip() for p in parts[:-1])
                    decimal = parts[-1].strip()
                    fields['frequency'] = f"{integer}.{decimal.split('.')[-1]}"
                else:
                    fields['frequency'] = ''.join(p.strip() for p in parts)
            else:
                fields['frequency'] = freq_text.strip()
            break
    
    # Extract number of patients
    patient_patterns = [
        r'(\d+)\s+(?:casualties|casualty|patients?|wounded)',
        r'(?:have|got)\s+(\d+)\s+(?:down|injured|hurt)',
        r'(\d+)\s+urgent\s+surgical',
    ]
    
    for pattern in patient_patterns:
        match = re.search(pattern, transcript, re.IGNORECASE)
        if match:
            fields['number_patients'] = match.group(1)
            break
    
    # Extract precedence
    if 'urgent surgical' in transcript.lower():
        urgent_match = re.search(r'(\d+)\s+urgent\s+surgical', transcript, re.IGNORECASE)
        if urgent_match:
            fields['patient_precedence'] = f"{urgent_match.group(1)} urgent surgical"
    
    # Extract litter/ambulatory
    litter_match = re.search(r'(\d+)\s+(?:can walk|walking|ambulatory)', transcript, re.IGNORECASE)
    if litter_match:
        fields['number_ambulatory'] = litter_match.group(1)
        # Calculate litter if we have total
        if 'number_patients' in fields:
            total = int(fields['number_patients'])
            ambulatory = int(litter_match.group(1))
            fields['number_litter'] = str(total - ambulatory)
    
    # Extract equipment
    equipment_keywords = {
        'ventilator': ['ventilator', 'vent', 'breathing support'],
        'hoist': ['hoist', 'winch', 'cable'],
        'extraction': ['extraction equipment', 'extraction'],
    }
    
    equipment_found = []
    for equip, keywords in equipment_keywords.items():
        if any(kw in transcript.lower() for kw in keywords):
            equipment_found.append(equip.capitalize())
    
    if equipment_found:
        fields['special_equipment'] = ', '.join(equipment_found)
    
    # Extract marking method
    marking_patterns = [
        r'(?:mark|marking|marked with)\s+(\w+)\s+smoke',
        r'(\w+)\s+smoke\s+(?:when|on)',
        r'(?:pop|throw|use)\s+(\w+)\s+smoke',
    ]
    
    for pattern in marking_patterns:
        match = re.search(pattern, transcript, re.IGNORECASE)
        if match:
            color = match.group(1).capitalize()
            fields['method_of_marking'] = f"{color} smoke"
            break
    
    # Extract security status
    security_keywords = {
        'N': ['no enemy', 'cold', 'secure', 'clear'],
        'P': ['possible enemy', 'unknown', 'not sure'],
        'E': ['enemy', 'hot', 'troops', 'contact'],
        'X': ['heavy', 'need escort', 'under fire'],
    }
    
    for code, keywords in security_keywords.items():
        if any(kw in transcript.lower() for kw in keywords):
            fields['security_at_pickup'] = code
            break
    
    return fields

def merge_extraction_results(ai_fields: dict, fallback_fields: dict, transcript: str) -> dict:
    """
    Intelligently merge AI extraction with fallback extraction.
    Prefer AI results unless they contain example data.
    """
    merged = {}
    example_contamination = ["RAZOR", "THUNDER", "18TWL", "purple smoke", "47.55"]
    
    for field_id, ai_value in ai_fields.items():
        # Check if AI value is contaminated with example data
        if ai_value and any(example in str(ai_value) for example in example_contamination):
            # Use fallback if available
            if field_id in fallback_fields and fallback_fields[field_id]:
                merged[field_id] = fallback_fields[field_id]
                logger.info(f"Using fallback for {field_id}: {merged[field_id]} (AI had: {ai_value})")
            else:
                # AI value is contaminated but no fallback available
                merged[field_id] = ""
        else:
            # AI value looks clean, use it
            merged[field_id] = ai_value
    
    # Add any fields from fallback that AI missed
    for field_id, fallback_value in fallback_fields.items():
        if field_id not in merged or not merged[field_id]:
            merged[field_id] = fallback_value
            logger.info(f"Added missing field {field_id} from fallback: {fallback_value}")
    
    return merged

