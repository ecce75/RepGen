import re

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