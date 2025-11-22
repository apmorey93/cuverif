"""
CuVerif P4 Manager - Perforce Integration
=========================================
Automates source control operations for design files.
"""

try:
    from P4 import P4, P4Exception
    P4_AVAILABLE = True
except ImportError:
    P4_AVAILABLE = False
    print("Warning: P4Python not installed. Perforce integration disabled.")
    print("Install with: pip install p4python")

import glob
import os

class SourceControl:
    """
    Perforce (P4) integration for automatic netlist synchronization.
    """
    def __init__(self):
        if not P4_AVAILABLE:
            raise ImportError("P4Python library not installed")
        self.p4 = P4()
        self.connected = False
        
    def connect(self, port, user, client):
        """
        Connect to P4 server.
        
        port: P4PORT (e.g., "perforce:1666")
        user: P4USER (e.g., "jsmith")
        client: P4CLIENT (e.g., "jsmith-ws")
        """
        self.p4.port = port
        self.p4.user = user
        self.p4.client = client
        try:
            self.p4.connect()
            self.connected = True
            return True
        except P4Exception as e:
            self.connected = False
            print(f"P4 Connection Error: {e}")
            return False

    def sync_path(self, depot_path):
        """
        Sync files from Perforce depot.
        
        depot_path: Depot path (e.g., "//depot/project/rtl/...")
        Returns: Status message
        """
        if not self.connected:
            return "Error: Not connected to P4"
            
        try:
            result = self.p4.run_sync(depot_path)
            num_files = len(result)
            return f"Synced {num_files} file(s)"
        except P4Exception as e:
            return f"Sync Error: {e}"
            
    def get_verilog_files(self, local_path):
        """
        Find all Verilog files in a local directory.
        
        local_path: Local filesystem path
        Returns: List of .v file paths
        """
        return glob.glob(f"{local_path}/**/*.v", recursive=True)
        
    def get_latest_changelist(self):
        """Get latest changelist number"""
        if not self.connected:
            return None
        try:
            changes = self.p4.run_changes("-m1")
            return changes[0]['change'] if changes else None
        except P4Exception:
            return None
            
    def disconnect(self):
        """Disconnect from P4 server"""
        if self.connected:
            self.p4.disconnect()
            self.connected = False
