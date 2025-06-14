import json
import os
from datetime import datetime
import socket
import streamlit as st
import re

# Import the TAK CoT XML generation module
from app.utils.cot_xml import generate_cot_from_report


def load_report_templates():
    """
    Load report templates from a file or return default templates.
    Templates are now aligned with NATO standards as defined in reports.txt
    """
    # Return dictionary of standardized NATO-format templates
    return {
        "CONTACTREP": {
            "title": "Contact Report",
            "description": "Report enemy contact or engagement",
            "cot_type": "a-h-G",
            "xml_element": "contact_report",
            "fields": [
                {"id": "size", "label": "Size of Enemy Unit", "required": True, "type": "text",
                 "placeholder": "Squad sized, 4-6 personnel"},
                {"id": "activity", "label": "Activity of Enemy", "required": True, "type": "text",
                 "placeholder": "Small arms fire, movement"},
                {"id": "location_desc", "label": "Location of Enemy", "required": True, "type": "text",
                 "placeholder": "MGRS: 34TFM12345678"},
                {"id": "unit_id", "label": "Unit Identification", "required": True, "type": "text",
                 "placeholder": "Unknown infantry"},
                {"id": "time_observed", "label": "Time of Observation", "required": True, "type": "text",
                 "placeholder": "DDMMMYY HHMMZ"},
                {"id": "equipment", "label": "Equipment Observed", "required": True, "type": "text",
                 "placeholder": "Small arms, technical vehicles"}
            ]
        },
        "SITREP": {
            "title": "Situation Report",
            "description": "Regular update on unit status and situation",
            "cot_type": "a-f-G-U-C",
            "xml_element": "sitrep",
            "fields": [
                {"id": "dtg", "label": "Date-Time Group (DTG)", "required": True, "type": "text",
                 "placeholder": "DDMMMYY HHMMZ"},
                {"id": "reporting_unit", "label": "Reporting Unit", "required": True, "type": "text", 
                 "placeholder": "Unit designation"},
                {"id": "location_desc", "label": "Location", "required": True, "type": "text",
                 "placeholder": "MGRS: 34TFM12345678"},
                {"id": "situation", "label": "Situation Summary", "required": True, "type": "text",
                 "placeholder": "Brief description of current situation"},
                {"id": "personnel", "label": "Personnel Status", "required": True, "type": "text",
                 "placeholder": "Personnel strength and status"},
                {"id": "equipment_status", "label": "Equipment Status", "required": True, "type": "text",
                 "placeholder": "Status of key equipment"},
                {"id": "supplies_status", "label": "Supplies Status", "required": True, "type": "text",
                 "placeholder": "Status of supplies"},
                {"id": "mission_status", "label": "Mission Status", "required": True, "type": "text",
                 "placeholder": "Progress towards mission objectives"},
                {"id": "comms_status", "label": "Communications Status", "required": False, "type": "text",
                 "placeholder": "Status of communications systems"},
                {"id": "next_report", "label": "Next Report Time", "required": False, "type": "text",
                 "placeholder": "When next report will be sent"}
            ]
        },
        "MEDEVAC": {
            "title": "Medical Evacuation Request",
            "description": "Request for medical evacuation",
            "cot_type": "b-r-f-h-c",
            "xml_element": "medevac",
            "fields": [
                {"id": "pickup_location", "label": "Location of Pickup Site", "required": True, "type": "text",
                 "placeholder": "MGRS: 34TFM12345678"},
                {"id": "radio_freq", "label": "Radio Frequency & Callsign", "required": True, "type": "text",
                 "placeholder": "38.50 MHz, Alpha 2-1"},
                {"id": "patients_precedence", "label": "Number of Patients by Precedence", "required": True, "type": "text",
                 "placeholder": "2 urgent, 1 priority"},
                {"id": "special_equipment", "label": "Special Equipment Required", "required": False, "type": "text",
                 "placeholder": "None"},
                {"id": "patients_type", "label": "Number of Patients by Type", "required": True, "type": "text",
                 "placeholder": "2 litter, 1 ambulatory"},
                {"id": "security", "label": "Security at Pickup Site", "required": True, "type": "text",
                 "placeholder": "No enemy, secured LZ"},
                {"id": "marking_method", "label": "Method of Marking Pickup Site", "required": True, "type": "text",
                 "placeholder": "VS-17 panel"},
                {"id": "patient_status", "label": "Patient Nationality & Status", "required": False, "type": "text",
                 "placeholder": "US military"},
                {"id": "nbc_contamination", "label": "NBC Contamination", "required": False, "type": "text",
                 "placeholder": "None"}
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


def format_report_for_transmission(report_type, report_data):
    """
    Format report data for transmission according to NATO standards.
    This function also generates the CoT XML file for WinTAK.
    
    Returns a tuple with (formatted_text, xml_file_path)
    """
    templates = load_report_templates()
    if report_type not in templates:
        return "ERROR: Invalid report type", None

    template = templates[report_type]

    # Format the report in a standardized way for display
    formatted_lines = [f"--- {template['title'].upper()} ---"]

    for field in template["fields"]:
        field_id = field["id"]
        field_label = field["label"]

        if field_id in report_data and report_data[field_id]:
            formatted_lines.append(f"{field_label.upper()}: {report_data[field_id]}")
    
    # Generate the CoT XML file for WinTAK
    try:
        xml_file_path = generate_cot_from_report(report_type, report_data)
        # Add a note about the XML file
        if xml_file_path:
            formatted_lines.append(f"\nWinTAK XML file created at: {xml_file_path}")
    except Exception as e:
        import logging
        logging.error(f"Failed to generate CoT XML: {e}")
        formatted_lines.append(f"\nError creating WinTAK XML file: {str(e)}")
        xml_file_path = None

    return "\n".join(formatted_lines), xml_file_path

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
