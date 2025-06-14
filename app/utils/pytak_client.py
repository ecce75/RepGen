import asyncio
import pytak
import xml.etree.ElementTree as ET
from configparser import ConfigParser
import logging

logger = logging.getLogger(__name__)

class VoxFieldPyTAKClient:
    def __init__(self, server_ip, server_port, connection_type="UDP", tls_config=None):
        self.server_ip = server_ip
        self.server_port = server_port
        self.connection_type = connection_type
        self.tls_config = tls_config or {}
        self.clitool = None
        self.sender = None
        
    async def setup(self):
        """Initialize PyTAK client"""
        config = ConfigParser()
        
        # Build COT URL based on connection type
        if self.connection_type == "UDP":
            cot_url = f"udp://{self.server_ip}:{self.server_port}"
        elif self.connection_type == "TCP":
            cot_url = f"tcp://{self.server_ip}:{self.server_port}"
        elif self.connection_type == "TLS":
            cot_url = f"tls://{self.server_ip}:{self.server_port}"
        
        config["repgen"] = {
            "COT_URL": cot_url,
            "FTS_COMPAT": "1",  # FreeTAKServer compatibility
        }
        
        # Add TLS configuration if needed
        if self.connection_type == "TLS" and self.tls_config:
            config["repgen"].update(self.tls_config)
        
        self.clitool = pytak.CLITool(config["repgen"])
        await self.clitool.setup()
        
        # Create sender
        self.sender = VoxFieldCoTSender(self.clitool.tx_queue, config["repgen"])
        self.clitool.add_tasks({self.sender})
        
        return True
    
    async def send_cot(self, xml_data):
        """Send CoT XML data"""
        if not self.sender:
            raise Exception("Client not initialized")
        
        await self.sender.put_queue(xml_data.encode())
        return True
    
    async def test_connection(self):
        """Test connection to TAK server"""
        try:
            # Send a simple ping CoT
            test_cot = self._create_test_cot()
            await self.send_cot(test_cot)
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)
    
    def _create_test_cot(self):
        """Create a test CoT for connection testing"""
        root = ET.Element("event")
        root.set("version", "2.0")
        root.set("type", "t-x-d-d")  # takPong type
        root.set("uid", "repgen-test")
        root.set("how", "m-g")
        root.set("time", pytak.cot_time())
        root.set("start", pytak.cot_time())
        root.set("stale", pytak.cot_time(60))
        
        point = ET.SubElement(root, "point")
        point.set("lat", "0.0")
        point.set("lon", "0.0")
        point.set("hae", "0.0")
        point.set("ce", "999999")
        point.set("le", "999999")
        
        return ET.tostring(root, encoding='unicode')

class VoxFieldCoTSender(pytak.QueueWorker):
    """Handles sending RepGen reports as CoT events"""
    
    async def handle_data(self, data):
        """Process data from queue"""
        await self.put_queue(data)
    
    async def run(self):
        """Main run loop"""
        while True:
            data = await self.queue.get()
            await self.handle_data(data)