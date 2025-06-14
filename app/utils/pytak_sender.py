import asyncio
import pytak
from typing import Optional
import logging
from configparser import ConfigParser
from .pytak_cot import create_cot_event

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
    async def _send():
        try:
            # Create configuration
            config = ConfigParser()
            config["repgen"] = {
                "COT_URL": tak_url
            }
            config = config["repgen"]
            
            # Create CLITool instance for connection management
            clitool = pytak.CLITool(config)
            await clitool.setup()
            
            # Create our serializer with the report data
            serializer = RepGenSerializer(
                clitool.tx_queue, 
                config, 
                report_type, 
                report_data
            )
            
            # Add the serializer to the task list
            clitool.add_tasks({serializer})
            
            # Run until the serializer completes
            # We need a timeout to prevent hanging
            try:
                await asyncio.wait_for(
                    serializer.run(), 
                    timeout=10.0
                )
                logger.info(f"Successfully queued {report_type} for transmission")
                
                # Give CLITool a moment to actually send
                await asyncio.sleep(1)
                
                return True
                
            except asyncio.TimeoutError:
                logger.error("Timeout sending CoT")
                return False
                
        except Exception as e:
            logger.error(f"PyTAK send error: {str(e)}")
            return False
    
    # Run the async function in a new event loop
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
    import socket
    import urllib.parse
    
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