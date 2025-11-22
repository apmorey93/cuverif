from . import core, backend as K
from numba import cuda

class DFlipFlop:
    """
    A D-type flip-flop module. 
    Currently uses the legacy 1-state update kernel, pending 4-state update.
    """
    def __init__(self, batch_size):
        self.batch_size = batch_size
        # Initialize Q output to 0 state (V=0, S=1)
        self.q = core.zeros(batch_size) 

    def step(self, d, reset=None):
        """
        Performs a clock step update with 4-state logic.
        
        Propagates X states from both data and reset inputs:
        - If reset is X, output becomes X
        - If reset is 1, output becomes 0
        - If reset is 0, output samples data (including X)
        """
        if reset is None: 
            # Default reset is Logic 0 (V=0, S=1) - inactive
            reset = core.zeros(self.batch_size)
            
        # Launch 4-State DFF Update Kernel
        blocks = K.get_grid_size(self.batch_size)
        
        K.k_dff_update_4state[blocks, K.THREADS_PER_BLOCK](
            d.v_data, d.s_data,           # D input (Value, Strength)
            self.q.v_data, self.q.s_data, # Q state (updated in-place)
            reset.v_data, reset.s_data,   # Reset input (Value, Strength)
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
                     Column 0 goes to Reg[0], Column 1 to Reg[1]...
        pattern_x:   Optional Numpy array for X states (0=X, 1=Valid)
        """
        # 1. Check shapes
        if pattern_val.shape[1] != self.length:
            raise ValueError(f"Pattern length {pattern_val.shape[1]} != Chain length {self.length}")

        # 2. Iterate and Force
        for i, reg in enumerate(self.chain):
            # Extract column 'i' from the pattern [Batch, Length]
            col_val = pattern_val[:, i].astype(np.uint32)
            
            # Create temporary tensors for this column
            # Note: We create new LogicTensors to handle the transfer to GPU
            t_val = core.LogicTensor(data_v=col_val, data_s=np.ones(reg.batch_size, dtype=np.uint32))
            
            if pattern_x is not None:
                col_x = pattern_x[:, i].astype(np.uint32)
                # If X mask provided, use it for strength
                t_x = core.LogicTensor(data_v=col_val, data_s=col_x)
            else:
                # Default: All valid
                t_x = core.LogicTensor(data_v=col_val, data_s=np.ones(reg.batch_size, dtype=np.uint32))

            # FORCE THE STATE
            # We overwrite the Q state of the register directly.
            # We skip the D input entirely.
            # NOTE: We must copy the GPU data from our temp tensor to the register's tensor
            # Since LogicTensor.v_data is a GPU array, we can use copy_to_device if needed,
            # but here we just replace the reference or copy content.
            # For MVP, we'll use CUDA copy_to_device if available, or just replace the tensor data reference
            # if the shapes match (which they do).
            
            # Efficient way: Copy data from temp tensor to register tensor
            # This assumes both are on GPU.
            cuda.driver.device_to_device(
                t_val.v_data, reg.q.v_data, t_val.v_data.nbytes
            )
            cuda.driver.device_to_device(
                t_x.s_data, reg.q.s_data, t_x.s_data.nbytes
            )

class FuseBank:
    """
    One-Time Programmable (OTP) eFuse Memory.
    Simulates the physical burning process where bits can only transition 0->1.
    """
    def __init__(self, num_bits, batch_size):
        self.num_bits = num_bits
        self.batch_size = batch_size
        
        # STORAGE: A list of LogicTensors (One per bit)
        # Initialize to 0 (Unprogrammed state)
        self.fuses = [core.zeros(batch_size) for _ in range(num_bits)]
        
        # OUTPUT: Buffered output (Sense Amplifiers)
        self.q = [core.zeros(batch_size) for _ in range(num_bits)]

    def step(self, read_en, prog_en, addr, wdata):
        """
        Cycle-Accurate Fuse Logic.
        read_en: If 1, updates self.q with current fuse values.
        prog_en: If 1, ATTEMPTS to burn the fuse at 'addr'.
        wdata:   The data to burn (LogicTensor).
        addr:    Integer index of the fuse to burn.
        """
        # 1. PROGRAMMING LOGIC (The "Sticky" Bit)
        # Equation: Fuse_Next = Fuse_Old | (Prog_En & Write_Data)
        # This ensures 0->1 is possible, but 1->0 is impossible.
        
        if addr < self.num_bits:
            current_val = self.fuses[addr]
            
            # Burn Logic: Only burn if prog_en is 1
            burn_mask = prog_en & wdata
            
            # Update State (Sticky OR operation)
            self.fuses[addr] = current_val | burn_mask
            
        # 2. SENSE AMP LOGIC (Reading)
        # If read_en is high, latch the fuse values to Q
        # Logic: q_next = read_en ? fuse_val : q_old
        
        not_read = ~read_en
        
        for i in range(self.num_bits):
            val_term = read_en & self.fuses[i]
            hold_term = not_read & self.q[i]
            self.q[i] = val_term | hold_term

    def backdoor_burn(self, bit_index, mask):
        """
        Factory Mode: Instantly sets fuse bits for specific instances.
        mask: LogicTensor (1 = Burn this instance, 0 = Skip).
        """
        if bit_index >= self.num_bits:
            raise ValueError(f"Fuse index {bit_index} out of range (max={self.num_bits-1})")
            
        # Sticky Update
        self.fuses[bit_index] = self.fuses[bit_index] | mask
        
    def backdoor_read(self):
        """Debug helper to dump fuse state to CPU"""
        return [f.cpu() for f in self.fuses]

