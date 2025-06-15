from asyncio.log import logger
import re
import mgrs

def validate_ip_address(ip):
    """Validate IP address format"""
    # Simple regex for IPv4 validation
    pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    if pattern.match(ip):
        # Check if each octet is valid (0-255)
        octets = ip.split('.')
        for octet in octets:
            if int(octet) > 255:
                return False
        return True
    return False

def validate_port(port):
    """Validate port number"""
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except:
        return False

def mgrs_to_decimal_degrees(mgrs_string):
    """
    Convert MGRS coordinates to decimal degrees.
    Handles various MGRS formats.
    """
    try:
        m = mgrs.MGRS()
        
        # Clean and standardize MGRS string
        # Remove common separators and extra spaces
        mgrs_clean = mgrs_string.upper()
        mgrs_clean = re.sub(r'[^\w\d]', '', mgrs_clean)  # Remove non-alphanumeric
        
        # Try to extract MGRS pattern
        # Example: 35VNF61105197 or 35V NF 6110 5197
        mgrs_pattern = r'(\d{1,2}[A-Z])([A-Z]{2})(\d+)'
        match = re.match(mgrs_pattern, mgrs_clean)
        
        if match:
            # Reconstruct MGRS in standard format
            grid_zone = match.group(1)
            square = match.group(2)
            coords = match.group(3)
            
            # Ensure even number of digits for coordinates
            if len(coords) % 2 != 0:
                coords = coords + "0"
            
            mgrs_formatted = f"{grid_zone}{square}{coords}"
            
            # Convert to lat/lon
            lat, lon = m.toLatLon(mgrs_formatted)
            
            return {
                "lat": lat,
                "lon": lon,
                "hae": 0.0,
                "ce": 10.0  # MGRS conversion is accurate
            }
    except Exception as e:
        logger.warning(f"MGRS conversion failed for '{mgrs_string}': {e}")
    
    # Fallback - try to parse as lat/lon if not MGRS
    try:
        # Look for decimal coordinates
        coord_pattern = r'([-]?\d+\.?\d*)[,\s]+([-]?\d+\.?\d*)'
        match = re.search(coord_pattern, mgrs_string)
        if match:
            return {
                "lat": float(match.group(1)),
                "lon": float(match.group(2)),
                "hae": 0.0,
                "ce": 100.0  # Less accurate
            }
    except:
        pass
    
    # Return zeros if all parsing fails
    logger.error(f"Could not parse location: {mgrs_string}")
    return {"lat": 0.0, "lon": 0.0, "hae": 0.0, "ce": 9999999.0}