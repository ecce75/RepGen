import json
import os
from datetime import datetime
import socket
import streamlit as st
import re

# Import the TAK CoT XML generation module
from app.utils.pytak_cot import create_cot_event
from typing import Tuple, Optional


def load_report_templates():
    """
    Load report templates from a file or return default templates.
    Templates are now aligned with NATO standards as defined in reports.txt
    """
    # Return dictionary of standardized NATO-format templates
    return {
        "MEDEVAC": {
            "title": "9-Line MEDEVAC Request",
            "cot_type": "a-f-G-U-C-I-M-E",  
            "xml_element": "medevac",        
            "fields": [
                {"id": "location", "label": "Location (Grid)", "required": True},
                {"id": "frequency", "label": "Radio Frequency", "required": False},
                {"id": "reporting_unit", "label": "Callsign", "required": True},
                {"id": "number_patients", "label": "Number of Patients", "required": True},
                {"id": "patient_precedence", "label": "Precedence", "required": True},
                {"id": "special_equipment", "label": "Special Equipment", "required": False},
                {"id": "number_litter", "label": "Litter Patients", "required": True},
                {"id": "number_ambulatory", "label": "Ambulatory Patients", "required": True},
                {"id": "security_at_pickup", "label": "Security (N/P/E/X)", "required": True},
                {"id": "method_of_marking", "label": "Marking Method", "required": True},
                {"id": "patient_nationality", "label": "Nationality", "required": True},
                {"id": "nbc_contamination", "label": "NBC Contamination", "required": False}
            ]
        },
        "CONTACTREP": {
            "title": "Contact Report",
            "cot_type": "a-h-G",           
            "xml_element": "contactrep",    
            "fields": [
                {"id": "reporting_unit", "label": "Reporting Unit", "required": True},
                {"id": "time_of_contact", "label": "Time of Contact", "required": True},
                {"id": "location", "label": "Location (Grid)", "required": True},
                {"id": "enemy_size", "label": "Enemy Size", "required": True},
                {"id": "enemy_activity", "label": "Enemy Activity", "required": True},
                {"id": "enemy_equipment", "label": "Enemy Equipment", "required": False},
                {"id": "distance_direction", "label": "Distance/Direction", "required": True},
                {"id": "friendly_status", "label": "Friendly Status", "required": True}
            ]
        },
        "SITREP": {
            "title": "Situation Report",
            "cot_type": "a-f-G-U-C",       
            "xml_element": "sitrep",        
            "fields": [
                {"id": "reporting_unit", "label": "Reporting Unit", "required": True},
                {"id": "location", "label": "Current Location", "required": True},
                {"id": "personnel_status", "label": "Personnel Status", "required": True},
                {"id": "ammunition_status", "label": "Ammunition Status", "required": True},
                {"id": "fuel_status", "label": "Fuel Status", "required": True},
                {"id": "current_activity", "label": "Current Activity", "required": True},
                {"id": "enemy_activity", "label": "Enemy Activity", "required": False},
                {"id": "requests", "label": "Requests/Requirements", "required": False}
            ]
        },
        "SPOTREP": {
            "title": "Spot Report",
            "description": "Report time-sensitive observations",
            "cot_type": "a-f-G-E",
            "xml_element": "spot_report",
            "fields": [
                {"id": "size", "label": "Size", "required": True, "type": "text",
                 "placeholder": "Squad sized, platoon, etc."},
                {"id": "activity", "label": "Activity", "required": True, "type": "text",
                 "placeholder": "What was observed"},
                {"id": "location_desc", "label": "Location", "required": True, "type": "text",
                 "placeholder": "MGRS: 34TFM12345678"},
                {"id": "unit", "label": "Unit", "required": True, "type": "text",
                 "placeholder": "Unknown infantry, armor, etc."},
                {"id": "time_observed", "label": "Time Observed", "required": True, "type": "text",
                 "placeholder": "DDMMMYY HHMMZ"},
                {"id": "equipment", "label": "Equipment", "required": True, "type": "text",
                 "placeholder": "Weapons, vehicles observed"}
            ]
        },
        "SALUTE": {
            "title": "SALUTE Report",
            "description": "Size, Activity, Location, Unit, Time, Equipment report",
            "cot_type": "a-h-G-U-C-I",
            "xml_element": "salute",
            "fields": [
                {"id": "size", "label": "Size", "required": True, "type": "text",
                 "placeholder": "Number of personnel, vehicles, etc."},
                {"id": "activity", "label": "Activity", "required": True, "type": "text",
                 "placeholder": "What they are doing"},
                {"id": "location_desc", "label": "Location", "required": True, "type": "text",
                 "placeholder": "MGRS: 34TFM12345678"},
                {"id": "unit", "label": "Unit", "required": True, "type": "text",
                 "placeholder": "Unit identification if known"},
                {"id": "time", "label": "Time", "required": True, "type": "text",
                 "placeholder": "Time of observation"},
                {"id": "equipment", "label": "Equipment", "required": True, "type": "text",
                 "placeholder": "Equipment observed"}
            ]
        },
        "PATROLREP": {
            "title": "Patrol Report",
            "description": "Report on patrol activities and observations",
            "cot_type": "a-f-G-P",
            "xml_element": "patrol_report",
            "fields": [
                {"id": "patrol_number", "label": "Patrol Number", "required": True, "type": "text",
                 "placeholder": "Patrol identifier"},
                {"id": "task_purpose", "label": "Task and Purpose", "required": True, "type": "text",
                 "placeholder": "Mission objective"},
                {"id": "time_departed", "label": "Time Departed", "required": True, "type": "text",
                 "placeholder": "DDMMMYY HHMMZ"},
                {"id": "time_returned", "label": "Time Returned", "required": True, "type": "text",
                 "placeholder": "DDMMMYY HHMMZ"},
                {"id": "route", "label": "Route Used", "required": True, "type": "text",
                 "placeholder": "Description or checkpoints"},
                {"id": "terrain", "label": "Terrain", "required": False, "type": "text",
                 "placeholder": "Terrain description"},
                {"id": "weather", "label": "Weather", "required": False, "type": "text",
                 "placeholder": "Weather conditions"},
                {"id": "enemy_contact", "label": "Enemy Contact", "required": True, "type": "text",
                 "placeholder": "Any enemy contact made"},
                {"id": "obstacles", "label": "Obstacles Encountered", "required": False, "type": "text",
                 "placeholder": "Obstacles or impediments"},
                {"id": "conclusion", "label": "Conclusion", "required": True, "type": "text",
                 "placeholder": "Summary and recommendations"}
                    ]
                }
            }


def extract_report_data(report_type, transcript):
    """
    Extract structured data from transcript using Qwen.

    Parameters:
    report_type - Type of report (CONTACTREP, SITREP, etc.)
    transcript - Text transcript of the audio

    Returns:
    report_data - Dictionary with extracted field values
    """
    # Get the templates
    templates = load_report_templates()

    # Use Qwen integration to extract the data
    from app.utils.ai import extract_entities_from_text
    return extract_entities_from_text(report_type, transcript)


def validate_report_data(report_type, report_data):
    """
    Validate report data against the template.
    Returns a list of missing required fields.
    """
    templates = load_report_templates()
    if report_type not in templates:
        return ["Invalid report type"]

    template = templates[report_type]
    missing_fields = []

    for field in template["fields"]:
        if field["required"] and (field["id"] not in report_data or not report_data[field["id"]]):
            missing_fields.append(field["label"])

    return missing_fields


def format_report_for_transmission(report_type: str, report_data: dict) -> str:
    """
    Format report for display only.
    CoT XML generation happens in pytak_cot module.
    """
    # Load templates at module level or pass as parameter
    report_templates = load_report_templates()
    template = report_templates.get(report_type, {})
    
    formatted_lines = [f"=== {template['title']} ==="]
    for field in template["fields"]:
        value = report_data.get(field["id"], "")
        if value:
            formatted_lines.append(f"{field['label']}: {value}")
    
    return "\n".join(formatted_lines)

def format_report_for_display(report_type: str, report_data: dict) -> str:
    """Alias for backward compatibility."""
    return format_report_for_transmission(report_type, report_data)

def send_cot_tcp(ip, port, xml_file_path):
    """
    Send CoT XML data to a WinTAK server.
    """
    # This would send the XML data to the specified IP and port via TCP

    # Check if xml_file_path is valid
    if not xml_file_path or not os.path.exists(xml_file_path):
        print(f"Invalid or missing XML file: {xml_file_path}")
        return False

    # get xml file in string format
    xml_data = xml_to_string(xml_file_path)

    # log the action
    print(f"Sending CoT XML to {ip}:{port}:::\n{xml_data}")

    # try to connect and send the data to the TAK server/multicast address
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))    
        sock.sendall(xml_data.encode('utf-8'))
        sock.close()
    except Exception as e:
        print(f"Failed to send CoT XML: {e}")
        return False

    return True  # Simulate successful transmission

def send_cot_udp(ip, port, xml_file_path):
    """
    Send CoT XML data to a WinTAK server via UDP.
    """
    # This would send the XML data to the specified IP and port via UDP

    # Check if xml_file_path is valid
    if not xml_file_path or not os.path.exists(xml_file_path):
        print(f"Invalid or missing XML file: {xml_file_path}")
        return False

    # get xml file in string format
    xml_data = xml_to_string(xml_file_path)

    # log the action
    print(f"Sending CoT XML to {ip}:{port}:::\n{xml_data}")

    # try to connect and send the data to the TAK server/multicast address
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(xml_data.encode('utf-8'), (ip, port))
        sock.close()
    except Exception as e:
        print(f"Failed to send CoT XML: {e}")
        return False

    return True  # Simulate successful transmission

# Generate pretty XML string    
def xml_to_string(xml_path):
    # open the xml file, read it and convert to string
    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"XML file not found: {xml_path}")
    
    with open(xml_path, 'r', encoding='utf-8') as file:
        xml_str = file.read()
    
    return xml_str 

def determine_recipients(report_type):
    """
    Determine appropriate recipients based on report type using Qwen-based analysis.
    """
    # This now uses our Qwen model but with mock data for now
    # We'll keep the function signature simple since we don't have the report data at this point
    recipients = {
        "CONTACTREP": ["Battalion TOC", "Company CP", "Adjacent Units"],
        "SITREP": ["Battalion S3", "Company Commander"],
        "MEDEVAC": ["Battalion Aid Station", "MEDEVAC Dispatch", "Company CP"],
        "RECCEREP": ["Battalion S2", "Company CP"]
    }
    return recipients.get(report_type, ["Chain of Command"])


def save_report_to_history(report_type, report_data, recipients, status="Sent"):
    """
    Save a report to the history.
    In a real implementation, this would save to a database.
    """
    if 'report_history' not in st.session_state:
        st.session_state.report_history = []

    templates = load_report_templates()
    if report_type not in templates:
        return False

    template = templates[report_type]

    report = {
        "type": report_type,
        "title": template["title"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data": report_data.copy(),
        "recipients": recipients,
        "status": status
    }

    st.session_state.report_history.insert(0, report)  # Add to the beginning of the list
    return True
