import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import pytak
import xml.etree.ElementTree as ET
import logging
import re

logger = logging.getLogger(__name__)

# Report type to CoT type mappings using PyTAK constants
COT_TYPE_MAPPINGS = {
    "MEDEVAC": {
        "default": "a-f-G-U-C-I-M-E",  # friendly medical evacuation
        "priority_based": {
            "flash": "a-f-G-E-V-A-M",     # emergency medevac
            "immediate": "a-f-G-U-C-I-M-E",
            "priority": "a-f-G-U-C-I-M",
            "routine": "a-f-G-U-C-I"
        }
    },
    "CONTACTREP": {
        "default": "a-h-G",  # hostile ground element
        "priority_based": {
            "immediate": "a-h-G-E-V-A",  # hostile attacking
            "priority": "a-h-G",
            "routine": "a-h-G"
        }
    },
    "SITREP": {
        "default": "a-f-G-U-C",      # friendly unit combat
        "all_clear": "a-f-G-U-C-F"   # friendly full strength
    }
}

def extract_priority_from_data(report_data: dict) -> str:
    """Extract priority level from report data."""
    priority_fields = ["priority", "precedence", "urgency", "patient_precedence"]
    
    for field in priority_fields:
        if field in report_data and report_data[field]:
            value = report_data[field].lower()
            if "flash" in value:
                return "flash"
            elif "immediate" in value or "urgent" in value:
                return "immediate"
            elif "priority" in value:
                return "priority"
    
    return "routine"

def determine_cot_type(report_type: str, report_data: dict) -> str:
    """Determine appropriate CoT type based on report content."""
    if report_type not in COT_TYPE_MAPPINGS:
        return "a-f-G-U-C"  # default friendly
    
    type_config = COT_TYPE_MAPPINGS[report_type]
    priority = extract_priority_from_data(report_data)
    
    if "priority_based" in type_config and priority in type_config["priority_based"]:
        return type_config["priority_based"][priority]
    
    return type_config["default"]

def extract_coordinates_from_location(location_text: str) -> Dict[str, float]:
    """Extract coordinates from location text."""
    # This is a placeholder - integrate with your MGRS conversion
    # For now, return default coordinates
    coords = {
        "lat": 0.0,
        "lon": 0.0,
        "hae": 0.0,
        "ce": 9999999.0,
        "le": 9999999.0
    }
    
    # If you have valid MGRS data, convert it here
    # PyTAK can work with decimal degrees directly
    if location_text and "grid" in location_text.lower():
        # Your MGRS conversion logic here
        coords["ce"] = 10.0  # Better accuracy for valid grid
        coords["le"] = 10.0
    
    return coords

def create_cot_event(report_type: str, report_data: dict, reporting_unit: Optional[str] = None) -> bytes:
    """
    Create a CoT Event XML string from report data.
    PyTAK uses ElementTree XML, not Event objects.
    """
    # Generate unique ID
    uid = f"{report_type}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # Time calculations  
    priority = extract_priority_from_data(report_data)
    stale_hours = {
        "flash": 0.5,
        "immediate": 1,
        "priority": 2,
        "routine": 4
    }
    stale_seconds = int(stale_hours.get(priority, 1) * 3600)
    
    # Determine CoT type
    cot_type = determine_cot_type(report_type, report_data)
    
    # Extract location
    location_field = None
    for field in ["location", "grid", "pickup_location", "enemy_location"]:
        if field in report_data and report_data[field]:
            location_field = report_data[field]
            break
    
    coords = extract_coordinates_from_location(location_field or "")
    
    # Extract callsign
    callsign = reporting_unit or report_data.get("reporting_unit", "UNKNOWN")
    if callsign == "UNKNOWN":
        for field in ["callsign", "unit", "from_unit"]:
            if field in report_data and report_data[field]:
                callsign = report_data[field].upper()
                break
    
    # Create the Event XML using ElementTree
    root = ET.Element("event")
    root.set("version", "2.0")
    root.set("type", cot_type)
    root.set("uid", uid)
    root.set("how", "h-g-i-g-o")  # human, GPS, integrated, observed
    root.set("time", pytak.cot_time())
    root.set("start", pytak.cot_time())
    root.set("stale", pytak.cot_time(stale_seconds))
    
    # Add point element
    point = ET.SubElement(root, "point")
    point.set("lat", str(coords["lat"]))
    point.set("lon", str(coords["lon"]))
    point.set("hae", str(coords["hae"]))
    point.set("ce", str(coords["ce"]))
    point.set("le", str(coords["le"]))
    
    # Create detail element
    detail = ET.Element("detail")
    
    # Add contact
    contact = ET.SubElement(detail, "contact")
    contact.set("callsign", callsign)
    
    # Add group
    group = ET.SubElement(detail, "__group")
    group_colors = {
        "MEDEVAC": "White",
        "CONTACTREP": "Red", 
        "SITREP": "Blue",
        "SPOTREP": "Yellow"
    }
    group.set("name", group_colors.get(report_type, "Blue"))
    group.set("role", "Team Member")
    
    # Add remarks
    remarks_text = f"{report_type} from {callsign}"
    if priority in ["flash", "immediate"]:
        remarks_text = f"**{priority.upper()}** {remarks_text}"
    
    remarks = ET.SubElement(detail, "remarks")
    remarks.text = remarks_text
    
    # Add report-specific details
    if report_type == "MEDEVAC":
        medevac = ET.SubElement(detail, "_medevac")
        
        # Map fields to 9-line
        field_mappings = {
            "location": "line1",
            "frequency": "line2", 
            "number_patients": "line3_patients",
            "patient_precedence": "line3_precedence",
            "special_equipment": "line4",
            "number_litter": "line5_litter",
            "number_ambulatory": "line5_ambulatory",
            "security_at_pickup": "line6",
            "method_of_marking": "line7",
            "patient_nationality": "line8",
            "nbc_contamination": "line9"
        }
        
        for data_field, xml_field in field_mappings.items():
            if data_field in report_data and report_data[data_field]:
                elem = ET.SubElement(medevac, xml_field)
                elem.text = str(report_data[data_field])
    
    elif report_type == "CONTACTREP":
        contact_elem = ET.SubElement(detail, "_contact")
        for field in ["enemy_size", "enemy_activity", "enemy_equipment", "friendly_status"]:
            if field in report_data and report_data[field]:
                elem = ET.SubElement(contact_elem, field)
                elem.text = str(report_data[field])
    
    # Set the detail on the event
    root.append(detail)
    
    return ET.tostring(root)