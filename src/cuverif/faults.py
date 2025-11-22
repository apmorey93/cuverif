import numpy as np
from . import core

class FaultCampaign:
    """
    Manages parallel fault injection campaigns.
    Maps specific faults (e.g., "wire_A stuck-at-0") to specific GPU threads.
    """
    def __init__(self, batch_size):
        self.batch_size = batch_size
        self.fault_list = [] # List of (description, thread_index)
        
        # Index 0 is always GOLD (No Faults)
        self.next_free_index = 1 

    def add_fault(self, name, fault_type):
        """
        Registers a fault and assigns it a GPU thread index.
        name: Name of the signal to fault
        fault_type: 0 (SA0) or 1 (SA1)
        Returns: The assigned thread index
        """
        if self.next_free_index >= self.batch_size:
            raise ValueError("Batch size too small for fault list!")
            
        idx = self.next_free_index
        self.fault_list.append({
            "name": name,
            "type": fault_type, # 0 or 1
            "index": idx
        })
        self.next_free_index += 1
        return idx

    def get_masks(self, current_signal_name):
        """
        Generates the GPU tensors (Enable, Value) for a specific signal.
        This tells the GPU: "Which threads have a fault on THIS wire?"
        """
        # Start with all zeros (No faults)
        en_host = np.zeros(self.batch_size, dtype=np.uint32)
        val_host = np.zeros(self.batch_size, dtype=np.uint32)
        
        # Fill in the specific threads that target this signal
        for fault in self.fault_list:
            if fault["name"] == current_signal_name:
                t_idx = fault["index"]
                en_host[t_idx] = 1
                val_host[t_idx] = fault["type"]
        
import numpy as np
from . import core

class FaultCampaign:
    """
    Manages parallel fault injection campaigns.
    Maps specific faults (e.g., "wire_A stuck-at-0") to specific GPU threads.
    """
    def __init__(self, batch_size):
        self.batch_size = batch_size
        self.fault_list = [] # List of (description, thread_index)
        
        # Index 0 is always GOLD (No Faults)
        self.next_free_index = 1 

    def add_fault(self, name, fault_type):
        """
        Registers a fault and assigns it a GPU thread index.
        name: Name of the signal to fault
        fault_type: 0 (SA0) or 1 (SA1)
        Returns: The assigned thread index
        """
        if self.next_free_index >= self.batch_size:
            raise ValueError("Batch size too small for fault list!")
            
        idx = self.next_free_index
        self.fault_list.append({
            "name": name,
            "type": fault_type, # 0 or 1
            "index": idx
        })
        self.next_free_index += 1
        return idx

    def get_masks(self, current_signal_name):
        """
        Generates the GPU tensors (Enable, Value) for a specific signal.
        This tells the GPU: "Which threads have a fault on THIS wire?"
        """
        # Start with all zeros (No faults)
        en_host = np.zeros(self.batch_size, dtype=np.uint32)
        val_host = np.zeros(self.batch_size, dtype=np.uint32)
        
        # Fill in the specific threads that target this signal
        for fault in self.fault_list:
            if fault["name"] == current_signal_name:
                t_idx = fault["index"]
                en_host[t_idx] = 1
                val_host[t_idx] = fault["type"]
        
        # Create LogicTensors (using explicit V/S init to avoid ambiguity)
        # Enable mask: V=en_host, S=1 (always valid control signal)
        en_tensor = core.LogicTensor(data_v=en_host, data_s=np.ones(self.batch_size, dtype=np.uint32))
        
        # Value mask: V=val_host, S=1
        val_tensor = core.LogicTensor(data_v=val_host, data_s=np.ones(self.batch_size, dtype=np.uint32))
                
        return en_tensor, val_tensor
