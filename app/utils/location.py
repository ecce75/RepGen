import streamlit as st
from streamlit_javascript import st_javascript
import requests
import json
import logging

logger = logging.getLogger(__name__)

def get_browser_location():
    """
    Get location from browser using JavaScript geolocation API
    Returns: (latitude, longitude, accuracy) or (None, None, None) if failed
    """
    # JavaScript to get location
    js_code = """
    await (async () => {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                resolve({error: 'Geolocation not supported'});
            }
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        altitude: position.coords.altitude || 0
                    });
                },
                (error) => {
                    resolve({error: error.message});
                },
                {
                    enableHighAccuracy: true,
                    timeout: 5000,
                    maximumAge: 0
                }
            );
        });
    })();
    """
    
    try:
        result = st_javascript(js_code)
        if result and 'error' not in result:
            return (
                result.get('latitude'),
                result.get('longitude'),
                result.get('accuracy', 9999999),
                result.get('altitude', 0)
            )
    except Exception as e:
        logger.error(f"Failed to get browser location: {e}")
    
    return None, None, None, None

def get_ip_location():
    """
    Fallback: Get approximate location from IP address
    Returns: (latitude, longitude, accuracy) or (None, None, None) if failed
    """
    try:
        # Using ipapi.co free service
        response = requests.get('https://ipapi.co/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return (
                float(data.get('latitude', 0)),
                float(data.get('longitude', 0)),
                50000,  # IP geolocation is very inaccurate, ~50km
                0  # No altitude from IP
            )
    except Exception as e:
        logger.error(f"Failed to get IP location: {e}")
    
    return None, None, None, None

def get_location_with_fallback():
    """
    Try to get location using multiple methods
    Returns: dict with lat, lon, hae, ce (circular error)
    """
    # Try browser location first
    lat, lon, accuracy, alt = get_browser_location()
    
    if lat is None or lon is None:
        # Fallback to IP location
        lat, lon, accuracy, alt = get_ip_location()
    
    if lat is None or lon is None:
        # Final fallback - use stored location or zeros
        lat = st.session_state.get('manual_lat', 0.0)
        lon = st.session_state.get('manual_lon', 0.0)
        alt = st.session_state.get('manual_alt', 0.0)
        accuracy = 9999999
    
    return {
        "lat": lat,
        "lon": lon,
        "hae": alt,  # Height above ellipsoid
        "ce": accuracy  # Circular error
    }