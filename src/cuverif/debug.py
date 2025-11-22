"""
CuVerif Debug Port - Register Abstraction Layer (RAL)
=====================================================
Provides backdoor access to internal signals for debugging,
mimicking JTAG or APB debug interfaces.
"""

import numpy as np
import cuverif.core as cv
from numba import cuda

class DebugPort:
    """
    Register Abstraction Layer (RAL).
    Allows 'Backdoor' access to internal GPU signals for peek/poke operations.
    """
    def __init__(self):
        # Maps Name/Address -> Reference to LogicTensor
        self.reg_map = {}

    def add_register(self, name, address, tensor_ref):
        """
        Register a signal for debug access.
        name: String identifier (e.g., "CTRL_REG")
        address: Integer address (e.g., 0x400)
        tensor_ref: Reference to a LogicTensor (typically a DFlipFlop.q)
        """
        entry = {"name": name, "addr": address, "ref": tensor_ref}
        self.reg_map[name] = entry
        self.reg_map[address] = entry

    def write(self, target, value, mask=None):
        """
        POKE: Overwrites the internal state of a register.
        target: Name (str) or Address (int)
        value:  Int (broadcast to all) or LogicTensor (per-instance)
        mask:   (Optional) LogicTensor. Only write to instances where mask=1
        """
        if target not in self.reg_map:
            raise KeyError(f"Register '{target}' not found in RAL.")
            
        entry = self.reg_map[target]
        tensor = entry["ref"]  # This is the DFlipFlop.q LogicTensor
        batch_size = tensor.size
        
        # 1. Standardize Value to LogicTensor
        if isinstance(value, int):
            # Create a tensor with the constant value
            val_data = np.full(batch_size, value, dtype=np.uint32)
            str_data = np.ones(batch_size, dtype=np.uint32)  # Valid signal
            val_tensor = cv.LogicTensor(data_v=val_data, data_s=str_data)
        else:
            val_tensor = value

        # 2. Standardize Mask
        if mask is None:
            # All ones (write to all instances)
            mask_data = np.ones(batch_size, dtype=np.uint32)
            mask_t = cv.LogicTensor(data_v=mask_data, data_s=mask_data)
        else:
            mask_t = mask

        # 3. Perform the Overwrite
        # Algorithm: New_State = (Mask & Write_Val) | (~Mask & Old_State)
        
        old_state = tensor
        term_new = mask_t & val_tensor
        term_old = (~mask_t) & old_state
        final_state = term_new | term_old
        
        # 4. In-Place Update (Device-to-Device copy)
        # Copy computed state back to the original tensor
        cuda.driver.device_to_device(
            final_state.v_data, tensor.v_data, final_state.v_data.nbytes
        )
        cuda.driver.device_to_device(
            final_state.s_data, tensor.s_data, final_state.s_data.nbytes
        )

    def read(self, target):
        """
        PEEK: Reads register state back to CPU.
        Returns: Tuple of (values, strengths) as numpy arrays
        """
        if target not in self.reg_map:
            raise KeyError(f"Register '{target}' not found.")
            
        tensor = self.reg_map[target]["ref"]
        
        # Return tuple (Values, Strengths)
        vals = tensor.v_data.copy_to_host()
        strs = tensor.s_data.copy_to_host()
        
        return vals, strs
