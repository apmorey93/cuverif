"""
CuVerif Silicon Bridge - Physical Hardware Interface
====================================================
Provides JTAG connectivity to real silicon via Olimex/FTDI dongles.
Allows the same debug operations on physical hardware as in simulation.
"""

import time

try:
    from pyftdi.jtag import JtagEngine
    from pyftdi.ftdi import Ftdi
    FTDI_AVAILABLE = True
except ImportError:
    FTDI_AVAILABLE = False
    print("Warning: pyftdi not installed. Silicon Bridge will not function.")
    print("Install with: pip install pyftdi")

class SiliconBridge:
    """
    Driver for Olimex/FTDI JTAG Dongles.
    Allows Python to communicate with real silicon via JTAG.
    """
    def __init__(self, url='ftdi://ftdi:2232:1/1'):
        """
        Initialize bridge with FTDI device URL.
        Default URL works for Olimex ARM-USB-TINY-H.
        """
        self.url = url
        self.jtag = None
        self.connected = False
        
        if not FTDI_AVAILABLE:
            raise ImportError("pyftdi library not installed")

    def connect(self):
        """
        Establish connection to JTAG dongle.
        Returns: Status message string
        """
        try:
            # Connect to Olimex ARM-USB-TINY-H or similar
            # frequency=100000 = 100 kHz TCK (safe for most chips)
            self.jtag = JtagEngine(trst=True, frequency=100000)
            self.jtag.configure(self.url)
            self.jtag.reset()
            self.connected = True
            return "Connected to Olimex JTAG"
        except Exception as e:
            self.connected = False
            return f"Connection Failed: {e}"

    def write_register(self, addr, data):
        """
        Backdoor register write via JTAG (e.g., APB over JTAG).
        This mimics the 'DebugPort' we built for simulation.
        
        addr: Register address (int)
        data: Data to write (int)
        """
        if not self.connected:
            raise RuntimeError("Not connected to hardware")
        
        # 1. Shift Instruction (WRITE_APB or similar)
        # IR Length depends on chip - common values: 4, 5, 6
        # This is a simplified example - real implementation needs chip-specific protocol
        self.jtag.write_ir(0x2, 4)  # Instruction: WRITE
        
        # 2. Shift Data (Addr + Data)
        # Protocol: 32-bit Addr + 32-bit Data = 64 bits total
        payload = (int(addr) << 32) | int(data)
        self.jtag.write_dr(payload, 64)
        
    def read_register(self, addr):
        """
        Backdoor register read via JTAG.
        Returns: Register value (int)
        """
        if not self.connected:
            raise RuntimeError("Not connected to hardware")
        
        # 1. Shift Instruction (READ_APB)
        self.jtag.write_ir(0x3, 4)  # Instruction: READ
        
        # 2. Shift Address
        self.jtag.write_dr(int(addr), 32)
        
        # 3. Read Data (Shift out 32 bits)
        data = self.jtag.read_dr(32)
        return int(data)

    def disconnect(self):
        """Close JTAG connection"""
        if self.jtag:
            self.jtag.close()
        self.connected = False
        
    def enumerate_devices(self):
        """
        List all connected FTDI devices.
        Useful for finding the correct URL.
        """
        if not FTDI_AVAILABLE:
            return []
        
        try:
            ftdi = Ftdi()
            devices = ftdi.list_devices()
            return [f"ftdi://{d[0]}/{d[1]}/{d[2]}" for d in devices]
        except Exception as e:
            return [f"Error enumerating: {e}"]
