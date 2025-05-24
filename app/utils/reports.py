import json
import os
from datetime import datetime
import streamlit as st
import re


def load_report_templates():
    """
    Load report templates from a file or return default templates.
    For the MVP, we'll use hardcoded templates, but in a real implementation,
    these would be loaded from JSON files or a database.
    """
    # In a production app, we would load these from files
    # For the MVP, we'll return a hardcoded dictionary
    return {
        "CONTACTREP": {
            "title": "Contact Report",
            "description": "Report enemy contact or engagement",
            "fields": [
                {"id": "datetime", "label": "Date/Time", "required": True, "type": "text",
                 "placeholder": "DDMMMYY HHMMZ"},
                {"id": "unit", "label": "Unit/Callsign", "required": True, "type": "text", "placeholder": "Alpha 2-1"},
                {"id": "location", "label": "Location", "required": True, "type": "text",
                 "placeholder": "MGRS: 34TFM12345678"},
                {"id": "enemy_activity", "label": "Enemy Activity", "required": True, "type": "text",
                 "placeholder": "Small arms fire from tree line"},
                {"id": "enemy_strength", "label": "Enemy Strength", "required": True, "type": "text",
                 "placeholder": "4-6 personnel"},
                {"id": "enemy_disposition", "label": "Enemy Disposition", "required": False, "type": "text",
                 "placeholder": "Dug in at tree line"},
                {"id": "actions_taken", "label": "Actions Taken", "required": True, "type": "text",
                 "placeholder": "Returned fire, established security"},
                {"id": "casualties", "label": "Casualties", "required": True, "type": "text", "placeholder": "None"},
                {"id": "equipment_status", "label": "Equipment Status", "required": False, "type": "text",
                 "placeholder": "All operational"},
                {"id": "ammo_status", "label": "Ammunition Status", "required": False, "type": "text",
                 "placeholder": "Green"},
                {"id": "assistance_required", "label": "Assistance Required", "required": False, "type": "text",
                 "placeholder": "None"}
            ]
        },
        "SITREP": {
            "title": "Situation Report",
            "description": "Regular update on unit status and situation",
            "fields": [
                {"id": "datetime", "label": "Date/Time", "required": True, "type": "text",
                 "placeholder": "DDMMMYY HHMMZ"},
                {"id": "unit", "label": "Unit/Callsign", "required": True, "type": "text", "placeholder": "Alpha 2-1"},
                {"id": "location", "label": "Location", "required": True, "type": "text",
                 "placeholder": "MGRS: 34TFM12345678"},
                {"id": "activity", "label": "Current Activity", "required": True, "type": "text",
                 "placeholder": "Establishing patrol base"},
                {"id": "situation", "label": "Situation Summary", "required": True, "type": "text",
                 "placeholder": "All quiet, no enemy contact"},
                {"id": "personnel_status", "label": "Personnel Status", "required": True, "type": "text",
                 "placeholder": "Full strength, no casualties"},
                {"id": "equipment_status", "label": "Equipment Status", "required": True, "type": "text",
                 "placeholder": "All operational"},
                {"id": "supply_status", "label": "Supply Status", "required": True, "type": "text",
                 "placeholder": "Green on all classes"},
                {"id": "next_actions", "label": "Next Actions", "required": False, "type": "text",
                 "placeholder": "Continue mission as planned"}
            ]
        },
        "MEDEVAC": {
            "title": "Medical Evacuation Request",
            "description": "Request for medical evacuation",
            "fields": [
                {"id": "datetime", "label": "Date/Time", "required": True, "type": "text",
                 "placeholder": "DDMMMYY HHMMZ"},
                {"id": "unit", "label": "Unit/Callsign", "required": True, "type": "text", "placeholder": "Alpha 2-1"},
                {"id": "pickup_location", "label": "Pickup Location", "required": True, "type": "text",
                 "placeholder": "MGRS: 34TFM12345678"},
                {"id": "radio_frequency", "label": "Radio Frequency", "required": True, "type": "text",
                 "placeholder": "38.50 MHz"},
                {"id": "patients", "label": "Number of Patients", "required": True, "type": "text",
                 "placeholder": "2 urgent, 1 priority"},
                {"id": "special_equipment", "label": "Special Equipment", "required": False, "type": "text",
                 "placeholder": "None"},
                {"id": "patient_status", "label": "Patient Status", "required": True, "type": "text",
                 "placeholder": "2 litter, 1 ambulatory"},
                {"id": "security", "label": "Security at Pickup", "required": True, "type": "text",
                 "placeholder": "No enemy, secured LZ"},
                {"id": "marking_method", "label": "Marking Method", "required": True, "type": "text",
                 "placeholder": "VS-17 panel"}
            ]
        },
        "RECCEREP": {
            "title": "Reconnaissance Report",
            "description": "Report reconnaissance findings",
            "fields": [
                {"id": "datetime", "label": "Date/Time", "required": True, "type": "text",
                 "placeholder": "DDMMMYY HHMMZ"},
                {"id": "unit", "label": "Unit/Callsign", "required": True, "type": "text", "placeholder": "Recon 1"},
                {"id": "location", "label": "Location", "required": True, "type": "text",
                 "placeholder": "MGRS: 34TFM12345678"},
                {"id": "observation_time", "label": "Time of Observation", "required": True, "type": "text",
                 "placeholder": "0730Z"},
                {"id": "activity_observed", "label": "Activity Observed", "required": True, "type": "text",
                 "placeholder": "Vehicle movement, digging positions"},
                {"id": "unit_size", "label": "Unit Size/Composition", "required": True, "type": "text",
                 "placeholder": "Squad-sized, infantry with 1 technical"},
                {"id": "direction", "label": "Direction of Movement", "required": False, "type": "text",
                 "placeholder": "Moving SE along MSR"},
                {"id": "equipment_observed", "label": "Equipment Observed", "required": False, "type": "text",
                 "placeholder": "Small arms, 1 HMG"},
                {"id": "assessed_intent", "label": "Assessed Intent", "required": False, "type": "text",
                 "placeholder": "Establishing checkpoint"},
                {"id": "actions_taken", "label": "Actions Taken", "required": True, "type": "text",
                 "placeholder": "Continuing observation"}
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
    In a real implementation, this would format the data according to
    the specific format required by the receiving system.
    """
    templates = load_report_templates()
    if report_type not in templates:
        return "ERROR: Invalid report type"

    template = templates[report_type]

    # Format the report in a standardized way
    formatted_lines = [f"--- {template['title'].upper()} ---"]

    for field in template["fields"]:
        field_id = field["id"]
        field_label = field["label"]

        if field_id in report_data and report_data[field_id]:
            formatted_lines.append(f"{field_label.upper()}: {report_data[field_id]}")

    return "\n".join(formatted_lines)


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
