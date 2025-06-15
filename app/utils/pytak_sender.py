import asyncio
import pytak
import socket
import urllib.parse
from typing import Optional
import logging
from configparser import ConfigParser
from app.utils.pytak_cot import create_cot_event

logger = logging.getLogger(__name__)

class RepGenSerializer(pytak.QueueWorker):
    """
    QueueWorker that handles single report transmission.
    This replaces the incorrect TAKClient implementation.
    """
    
    def __init__(self, queue, config, report_type, report_data):
        super().__init__(queue, config)
        self.report_type = report_type
        self.report_data = report_data
        self.sent = False
    
    async def handle_data(self, data):
        """Put CoT Event onto the queue for transmission."""
        await self.put_queue(data)
        self.sent = True
    
    async def run(self):
        """Generate the CoT event and send it once."""
        if not self.sent:
            # Create the CoT event XML
            cot_xml = create_cot_event(self.report_type, self.report_data)
            self._logger.info(f"Sending {self.report_type} CoT")
            await self.handle_data(cot_xml)
            # Signal completion by setting sent flag
            self.sent = True
        # Exit after sending once
        return

def send_cot_pytak(tak_url: str, report_type: str, report_data: dict) -> bool:
    """
    Synchronous wrapper to send CoT via PyTAK using proper QueueWorker pattern.
    
    Args:
        tak_url: TAK server URL (e.g., "tcp://192.168.1.194:8087")
        report_type: Type of report
        report_data: Report field data
        
    Returns:
        bool: Success status
    """
    logger.info(f"send_cot_pytak called with URL: {tak_url}")
    
    async def _send():
        clitool = None
        try:
            # Add +wo for UDP to prevent binding issues
            modified_url = tak_url
            if tak_url.startswith("udp://"):
                modified_url = tak_url.replace("udp://", "udp+wo://")
            
            # Create configuration
            config = ConfigParser()
            config["repgen"] = {
                "COT_URL": modified_url  # Use the modified URL
            }
            config = config["repgen"]
            
            # Rest of the function remains the same...
            clitool = pytak.CLITool(config)
            await clitool.setup()
            
            serializer = RepGenSerializer(
                clitool.tx_queue, 
                config, 
                report_type, 
                report_data
            )
            
            clitool.add_tasks({serializer})
            
            await asyncio.wait_for(serializer.run(), timeout=5.0)
            await asyncio.sleep(0.5)
            
            return True
            
        except Exception as e:
            logger.error(f"PyTAK send error: {str(e)}")
            return False
        finally:
            if clitool:
                try:
                    await clitool.cleanup()
                except:
                    pass
    
    # Run in new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_send())
    finally:
        loop.close()

# Alternative implementation using raw socket for immediate sending
def send_cot_direct(tak_url: str, report_type: str, report_data: dict) -> bool:
    """
    Direct CoT transmission without PyTAK's queue system.
    Useful for one-shot transmissions in Streamlit.
    """
    logger.info(f"send_cot_direct called with URL: {tak_url}")
    
    try:
        # Parse the URL
        parsed = urllib.parse.urlparse(tak_url)
        host = parsed.hostname
        port = parsed.port
        
        # Create the CoT XML
        cot_xml = create_cot_event(report_type, report_data)
        
        if parsed.scheme == "tcp":
            # TCP transmission
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((host, port))
                sock.sendall(cot_xml)
                logger.info(f"Sent {report_type} CoT via TCP to {host}:{port}")
                return True
                
        elif parsed.scheme == "udp":
            # UDP transmission
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(cot_xml, (host, port))
                logger.info(f"Sent {report_type} CoT via UDP to {host}:{port}")
                return True
                
        else:
            logger.error(f"Unsupported scheme: {parsed.scheme}")
            return False
            
    except Exception as e:
        logger.error(f"Direct send error: {str(e)}")
        return False