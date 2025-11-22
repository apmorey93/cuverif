from . import core
import numpy as np

class DFlipFlop:
    """
    A D-type flip-flop module.
    
    **Contract (Tier 1):**
    - **Clocking:** Implicit positive-edge triggered by `step()`.
    - **Reset:** 
        - Active High (1 = Reset, 0 = Run).
        - Synchronous priority (evaluated at clock edge).
        - If Reset is 1, Q becomes 0 (Strong).
    - **X-Propagation Rules:**
        - If Reset is X (Unknown): Q becomes X (Strong 0, Value 0).
        - If Reset is 0 (Inactive):
            - If Data is X: Q becomes X.
            - If Data is 0/1: Q becomes Data.
    - **Input/Output:**
        - Inputs `d` and `reset` must be `LogicTensor` of same batch size.
        - Output `q` is updated in-place and returned.
    """
    def __init__(self, batch_size):
        self.batch_size = batch_size
        # Initialize Q output to 0 state (V=0, S=1)
        self.q = core.zeros(batch_size) 

    def step(self, d, reset=None):
        """
        Performs a clock step update with 4-state logic.
        See class docstring for precise semantics.
        """
        if reset is None: 
            # Default reset is Logic 0 (V=0, S=1) - inactive
            reset = core.zeros(self.batch_size)
            
        # Use backend for update
        self.q.backend.dff_update(
            self.q._buffers(),
            d._buffers(),
            reset._buffers(),
            self.batch_size
        )
        
        return self.q

class ScanChain:
    """
    Manages a chain of flip-flops for Zero-Time Scan Loading.
    Allows "teleporting" ATPG patterns directly into registers, bypassing
    the slow serial shift process.
    """
    def __init__(self, registers):
        """
        registers: A list of DFlipFlop instances in the order they are chained.
        (Scan_In -> Reg[0] -> Reg[1] -> ... -> Reg[N] -> Scan_Out)
        """
        self.chain = registers
        self.length = len(registers)

    def scan_load(self, pattern_val, pattern_x=None):
        """
        Zero-Time Load. Teleports data into the FFs.
        pattern_val: Numpy array of shape [Batch_Size, Chain_Length]
        pattern_x:   Optional Numpy array for X states (0=X, 1=Valid)
        """
        # 1. Check shapes
        if pattern_val.shape[1] != self.length:
            raise ValueError(f"Pattern length {pattern_val.shape[1]} != Chain length {self.length}")

        # 2. Iterate and Force
        # This is a bit inefficient (Python loop), but O(Chain_Length) is better than O(Chain_Length * Batch)
        # Ideally we'd have a backend.scan_load_batch kernel, but for now we iterate registers.
        
        # We need to ensure we are using the correct backend. 
        # Assuming all registers share the same backend (invariant).
        backend = self.chain[0].q.backend
        
        for i, reg in enumerate(self.chain):
            # Extract column 'i' from the pattern [Batch, Length]
            col_val = pattern_val[:, i].astype(np.uint32)
            
            if pattern_x is not None:
                col_x = pattern_x[:, i].astype(np.uint32)
            else:
                col_x = np.ones(reg.batch_size, dtype=np.uint32)

            # We need to transfer this column to the device to copy it into the register
            # We can use the backend's get_device_array or alloc+copy
            
            # Create temp buffers on device
            # Note: This creates new allocations every time. 
            # Optimization: Pre-allocate a single scratchpad buffer if this is hot path.
            
            # For now, we use LogicTensor to handle the transfer, then copy buffer-to-buffer
            # This is slightly wasteful (allocating temp tensor) but clean.
            
            # Actually, we can just overwrite the register's data directly if the backend supports host-to-device copy
            # But our backend interface only has get_device_array (alloc+copy) or to_host.
            # Let's assume we create a temp tensor and then copy.
            
            # Wait, we can just assign! 
            # reg.q.v_data = backend.get_device_array(col_val)
            # But that changes the pointer, breaking anyone holding a reference to the old buffer?
            # LogicTensor holds the buffer. If DFlipFlop holds LogicTensor, and we replace the buffer inside LogicTensor...
            # LogicTensor doesn't expose a "set_data" method.
            # And we want to support "teleporting" which implies modifying the state in place.
            
            # Let's use a backend method for this? 
            # Or just expose a "copy_from_host" on LogicTensor?
            # Or use the backend's copy capability if we knew it.
            
            # For this refactor, let's do:
            # 1. Create temp LogicTensor with new data
            # 2. Use backend to copy temp -> reg.q (we need a copy kernel or memcpy)
            # Our backend interface doesn't have a generic "copy" or "assign".
            # But we can use logic operations! 
            # reg.q = temp (This replaces the reference in the python object, but DFF holds the object)
            # So: reg.q.v_data = ... is dangerous if shared.
            
            # The cleanest way for now without adding new backend API:
            # reg.q.v_data = backend.get_device_array(col_val)
            # This assumes reg.q is the OWNER of the buffer and no one else is holding a ref to the buffer directly.
            # In our architecture, LogicTensor owns the buffer.
            
            reg.q.v_data = backend.get_device_array(col_val)
            reg.q.s_data = backend.get_device_array(col_x)
            
            # NOTE: If we wanted to be strictly "in-place" memory safe, we'd need a backend.copy(src, dst)
            # But replacing the handle is fine for this Python-level object model.

class FuseBank:
    """
    One-Time Programmable (OTP) eFuse Memory.
    Simulates the physical burning process where bits can only transition 0->1.
    """
    def __init__(self, num_bits, batch_size):
        self.num_bits = num_bits
        self.batch_size = batch_size
        
        # STORAGE: A list of LogicTensors (One per bit)
        self.fuses = [core.zeros(batch_size) for _ in range(num_bits)]
        
        # OUTPUT: Buffered output (Sense Amplifiers)
        self.q = [core.zeros(batch_size) for _ in range(num_bits)]

    def step(self, read_en, prog_en, addr, wdata):
        """
        Cycle-Accurate Fuse Logic.
        """
        # 1. PROGRAMMING LOGIC (The "Sticky" Bit)
        # Equation: Fuse_Next = Fuse_Old | (Prog_En & Write_Data)
        
        if addr < self.num_bits:
            current_val = self.fuses[addr]
            
            # Burn Logic: Only burn if prog_en is 1
            burn_mask = prog_en & wdata
            
            # Update State (Sticky OR operation)
            # LogicTensor operations create new tensors, so we update the reference
            self.fuses[addr] = current_val | burn_mask
            
        # 2. SENSE AMP LOGIC (Reading)
        # Logic: q_next = read_en ? fuse_val : q_old
        
        not_read = ~read_en
        
        for i in range(self.num_bits):
            val_term = read_en & self.fuses[i]
            hold_term = not_read & self.q[i]
            self.q[i] = val_term | hold_term

    def backdoor_burn(self, bit_index, mask):
        """
        Factory Mode: Instantly sets fuse bits for specific instances.
        """
        if bit_index >= self.num_bits:
            raise ValueError(f"Fuse index {bit_index} out of range (max={self.num_bits-1})")
            
        # Sticky Update
        self.fuses[bit_index] = self.fuses[bit_index] | mask
        
    def backdoor_read(self):
        """Debug helper to dump fuse state to CPU"""
        return [f.cpu() for f in self.fuses]

