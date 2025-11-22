from numba import cuda
import numpy as np
from . import backend as K

# --- 4-State Logic Constants ---
V_0, S_0 = 0, 1  # State 0
V_1, S_1 = 1, 1  # State 1
V_X, S_X = 0, 0  # State X (Unknown)
V_Z, S_Z = 1, 0  # State Z (High Impedance)

class LogicTensor:
    """
    Represents a tensor of logic signals residing on the GPU.
    Refactored to hold two arrays: v_data (Value) and s_data (Strong)
    to support 4-state logic (0, 1, X, Z).
    """
    def __init__(self, data_v=None, data_s=None, shape=None, gpu_ref_v=None, gpu_ref_s=None):
        
        if gpu_ref_v is not None and gpu_ref_s is not None:
            # Constructor 1: Reference to existing GPU arrays
            self.v_data = gpu_ref_v
            self.s_data = gpu_ref_s
            self.size = gpu_ref_v.size
        else:
            # Constructor 2: Initialize from CPU data or shape
            if shape is not None:
                # Initialize to '0' state (V=0, S=1)
                data_v = np.zeros(shape, dtype=np.uint32)
                data_s = np.ones(shape, dtype=np.uint32)
            elif data_v is not None and data_s is not None:
                # Initialize from provided V and S CPU arrays
                data_v = np.array(data_v, dtype=np.uint32)
                data_s = np.array(data_s, dtype=np.uint32)
            else:
                # Fallback: Create a single '0' element
                data_v = np.array([V_0], dtype=np.uint32)
                data_s = np.array([S_0], dtype=np.uint32)
            
            # Transfer to device
            self.v_data = cuda.to_device(data_v)
            self.s_data = cuda.to_device(data_s)
            self.size = data_v.size

    # Ergonomic property aliases for cleaner API
    @property
    def val(self):
        """Alias for v_data (Value bits)"""
        return self.v_data
    
    @property
    def x(self):
        """Alias for s_data (Strength bits) - x represents 'eXistence/strength'"""
        return self.s_data

    def __and__(self, other):
        out_v = cuda.device_array_like(self.v_data)
        out_s = cuda.device_array_like(self.s_data)
        K.k_and_4state[K.get_grid_size(self.size), K.THREADS_PER_BLOCK](
            self.v_data, self.s_data, other.v_data, other.s_data, out_v, out_s, self.size
        )
        return LogicTensor(gpu_ref_v=out_v, gpu_ref_s=out_s)

    def __or__(self, other):
        out_v = cuda.device_array_like(self.v_data)
        out_s = cuda.device_array_like(self.s_data)
        K.k_or_4state[K.get_grid_size(self.size), K.THREADS_PER_BLOCK](
            self.v_data, self.s_data, other.v_data, other.s_data, out_v, out_s, self.size
        )
        return LogicTensor(gpu_ref_v=out_v, gpu_ref_s=out_s)

    def __xor__(self, other):
        # 4-State XOR with proper X/Z propagation
        out_v = cuda.device_array_like(self.v_data)
        out_s = cuda.device_array_like(self.s_data)

        K.k_xor_4state[K.get_grid_size(self.size), K.THREADS_PER_BLOCK](
            self.v_data, self.s_data, other.v_data, other.s_data, out_v, out_s, self.size
        )
        return LogicTensor(gpu_ref_v=out_v, gpu_ref_s=out_s)
    
    def __invert__(self):
        out_v = cuda.device_array_like(self.v_data)
        out_s = cuda.device_array_like(self.s_data)
        K.k_not_4state[K.get_grid_size(self.size), K.THREADS_PER_BLOCK](
            self.v_data, self.s_data, out_v, out_s, self.size
        )
        return LogicTensor(gpu_ref_v=out_v, gpu_ref_s=out_s)

    def force(self, enable_mask, value_mask):
        """
        Injects stuck-at faults into this specific wire.
        enable_mask: LogicTensor (1 where fault exists)
        value_mask:  LogicTensor (0 for SA0, 1 for SA1)
        """
        # Ensure masks are on GPU
        if not isinstance(enable_mask, LogicTensor):
            raise ValueError("Masks must be LogicTensors")
            
        # Launch Kernel
        blocks = K.get_grid_size(self.size)
        K.k_inject_fault[blocks, K.THREADS_PER_BLOCK](
            self.v_data, self.s_data,  # Target Signal (Modified in-place)
            enable_mask.v_data,        # Enable Bit
            value_mask.v_data,         # Value Bit
            self.size
        )
        # We return self to allow chaining, though modification is in-place
        return self

    def cpu(self):
        """Copies V and S data to host and returns them as a tuple."""
        v_host = self.v_data.copy_to_host()
        s_host = self.s_data.copy_to_host()
        return v_host, s_host

# --- Utility Constructors ---

def randint(low, high, size):
    """Creates a LogicTensor with random 0/1 states (V=random, S=1)."""
    v_data = np.random.randint(low, high, size, dtype=np.uint32)
    s_data = np.ones(size, dtype=np.uint32)
    return LogicTensor(data_v=v_data, data_s=s_data)

def zeros(size):
    """Creates a LogicTensor initialized to the '0' state (V=0, S=1)."""
    v_data = np.zeros(size, dtype=np.uint32)
    s_data = np.ones(size, dtype=np.uint32)
    return LogicTensor(data_v=v_data, data_s=s_data)

def unknown(size):
    """Creates a LogicTensor initialized to the 'X' state (V=0, S=0)."""
    v_data = np.zeros(size, dtype=np.uint32)
    s_data = np.zeros(size, dtype=np.uint32)
    return LogicTensor(data_v=v_data, data_s=s_data)
