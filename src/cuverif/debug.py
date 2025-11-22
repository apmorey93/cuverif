"""
CuVerif Debug Port - Register Abstraction Layer (RAL)
=====================================================
Provides backdoor access to internal signals for debugging,
mimicking JTAG or APB debug interfaces.
"""

import numpy as np
import cuverif.core as cv
import cuverif.core as cv

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
            # Use the tensor's backend to ensure compatibility
            val_tensor = cv.LogicTensor.zeros(batch_size, backend=tensor.backend)
            # TODO: Efficient fill. For now, we rely on zeros() and then force if needed.
            # But wait, we can just create it from host arrays if we want specific values
            v_host = np.full(batch_size, value, dtype=np.uint32)
            s_host = np.ones(batch_size, dtype=np.uint32)
            val_tensor = cv.LogicTensor.from_host(data_v=v_host, data_s=s_host, backend=tensor.backend)
        else:
            val_tensor = value

        # 2. Standardize Mask
        if mask is None:
            # All ones (write to all instances)
            mask_host = np.ones(batch_size, dtype=np.uint32)
            mask_t = cv.LogicTensor.from_host(data_v=mask_host, data_s=mask_host, backend=tensor.backend)
        else:
            mask_t = mask

        # 3. Perform the Overwrite
        # Algorithm: New_State = (Mask & Write_Val) | (~Mask & Old_State)
        
        # We can't easily do "old_state = tensor" because tensor IS the reference we want to update.
        # And LogicTensor ops return NEW tensors.
        # So we calculate the new state as a new tensor...
        
        term_new = mask_t & val_tensor
        term_old = (~mask_t) & tensor
        final_state = term_new | term_old
        
        # 4. In-Place Update
        # We need to copy final_state's buffers into tensor's buffers.
        # LogicTensor doesn't expose a "copy_from" method, but we can access buffers.
        # We need a backend method to copy device-to-device.
        # Our backend interface currently lacks a generic "copy" method exposed publicly 
        # (it has get_device_array which allocates).
        # However, we can cheat slightly for now by swapping the buffers if we are sure 
        # no one else holds the specific buffer references (LogicTensor usually owns them).
        # BUT DFlipFlop.q is held by the DFF instance.
        
        # Safer: Use a backend-specific copy if available, or add `assign` to LogicTensor.
        # For this refactor, let's assume we can swap the buffer references in the LogicTensor object.
        # This is Python, so we can just update the attributes.
        # WARNING: If `tensor.v_data` was aliased elsewhere, this breaks that alias.
        # But in our design, LogicTensor owns the buffers.
        
        tensor.v_data = final_state.v_data
        tensor.s_data = final_state.s_data

    def read(self, target):
        """
        PEEK: Reads register state back to CPU.
        Returns: Tuple of (values, strengths) as numpy arrays
        """
        if target not in self.reg_map:
            raise KeyError(f"Register '{target}' not found.")
            
        tensor = self.reg_map[target]["ref"]
        
        # Return tuple (Values, Strengths) using the backend-agnostic .cpu() method
        return tensor.cpu()
