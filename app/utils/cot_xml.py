import os
import uuid
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import logging
from .military import format_mgrs_grid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the WinTAK import directory - this should be configurable in production
DEFAULT_WINTAK_IMPORT_DIR = os.path.expanduser("~/TAK/import")

def get_wintak_import_dir():
    """
    Get the WinTAK import directory, creating it if it doesn't exist.
    This should be made configurable in a production system.
    """
    # Check environment variable first (for easy configuration)
    wintak_dir = os.environ.get('WINTAK_IMPORT_DIR', DEFAULT_WINTAK_IMPORT_DIR)
    
    # Create directory if it doesn't exist
    if not os.path.exists(wintak_dir):
        try:
            os.makedirs(wintak_dir)
            logger.info(f"Created WinTAK import directory: {wintak_dir}")
        except Exception as e:
            logger.error(f"Failed to create WinTAK import directory: {e}")
    
    return wintak_dir

def mgrs_to_decimal_degrees(mgrs_string):
    """
    Convert MGRS coordinates to decimal degrees.
    
    In a production system, this would use a proper coordinate conversion library.
    For this prototype, we'll return placeholder values and log that this needs
    to be implemented properly.
    """
    # TODO: Implement proper MGRS to decimal degrees conversion
    # This is a placeholder - in production use pyproj, mgrs, or another library
    logger.warning("MGRS conversion not implemented - using placeholder values")
    return {
        "lat": 34.0,  # Placeholder latitude
        "lon": -118.0,  # Placeholder longitude
        "hae": 0.0,  # Height above ellipsoid (placeholder)
    }

def generate_cot_xml(report_type, report_data, reporting_unit=None):
    """
    Generate a Cursor-on-Target (CoT) XML message based on report data.
    
    Args:
        report_type (str): The type of report (e.g., "SITREP", "CONTACTREP")
        report_data (dict): Dictionary containing the report field values
        reporting_unit (str, optional): The unit submitting the report
        
    Returns:
        tuple: (xml_string, file_path) - The generated XML string and saved file path
    """
    # Get templates to access CoT type mapping
    from .reports import load_report_templates
    templates = load_report_templates()
    
    if report_type not in templates:
        logger.error(f"Unknown report type: {report_type}")
        return None, None
    
    template = templates[report_type]
    
    # Generate a unique ID for this message
    uid = str(uuid.uuid4())
    
    # Current time in ISO format
    now = datetime.utcnow()
    time_str = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    
    # Stale time (when the message expires) - default to 1 hour from now
    stale_time = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    
    # Get CoT type from template
    cot_type = template.get("cot_type", "a-f-G-U-C")  # Default to friendly unit
    
    # XML element name from template
    xml_element = template.get("xml_element", report_type.lower())
    
    # Create root element
    root = ET.Element("event")
    root.set("version", "2.0")
    root.set("uid", uid)
    root.set("type", cot_type)
    root.set("time", time_str)
    root.set("start", time_str)
    root.set("stale", stale_time)
    root.set("how", "h-g-i-g-o")  # Human input, GPS, COT
    
    # Extract location data - look for fields with location information
    location_field = None
    for field_name in ["location_desc", "pickup_location", "location"]:
        if field_name in report_data and report_data[field_name]:
            location_field = field_name
            break
    
    # Parse coordinates if available
    coords = {"lat": 0.0, "lon": 0.0, "hae": 0.0}
    if location_field and report_data[location_field]:
        location_text = report_data[location_field]
        
        # Try to extract MGRS coordinates
        if "MGRS" in location_text or any(char.isdigit() for char in location_text):
            # Basic attempt to extract what looks like MGRS coords
            coords = mgrs_to_decimal_degrees(location_text)
    
    # Create point element
    point = ET.SubElement(root, "point")
    point.set("lat", str(coords["lat"]))
    point.set("lon", str(coords["lon"]))
    point.set("hae", str(coords["hae"]))
    point.set("ce", "9999999.0")  # Circular error (set large for low confidence)
    point.set("le", "9999999.0")  # Linear error (set large for low confidence)
    
    # Create detail element
    detail = ET.SubElement(root, "detail")
    
    # Add contact information if available
    contact = ET.SubElement(detail, "contact")
    if reporting_unit:
        contact.set("callsign", reporting_unit)
    elif "reporting_unit" in report_data:
        contact.set("callsign", report_data["reporting_unit"])
    elif "unit" in report_data:
        contact.set("callsign", report_data["unit"])
    else:
        contact.set("callsign", "UNKNOWN")
    
    # Add group information
    group = ET.SubElement(detail, "__group")
    group.set("name", "Yellow")  # Default color
    group.set("role", "Team Member")  # Default role
    
    # Add remarks if available
    remarks_text = f"{template['title']} - Generated by RepGen"
    if "situation" in report_data:
        remarks_text += f": {report_data['situation']}"
    remarks = ET.SubElement(detail, "remarks")
    remarks.text = remarks_text
    
    # Create report-specific element
    report_element = ET.SubElement(detail, xml_element)
    
    # Add all fields from the report data to the report element
    for field_id, value in report_data.items():
        if value:  # Only add non-empty fields
            field_element = ET.SubElement(report_element, field_id)
            field_element.text = value
    
    # Convert to string
    xml_string = ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')
    
    # Get WinTAK import directory
    wintak_dir = get_wintak_import_dir()
    
    # Save to file
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"{report_type}_{timestamp}.xml"
    file_path = os.path.join(wintak_dir, filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(xml_string)
        logger.info(f"CoT XML file saved to: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save CoT XML file: {e}")
        file_path = None
    
    return xml_string, file_path

def generate_cot_from_report(report_type, report_data):
    """
    Wrapper function to generate and save a CoT XML file from a report.
    Returns the path to the saved file.
    """
    _, file_path = generate_cot_xml(report_type, report_data)
    return file_path