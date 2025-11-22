from numba import cuda
import numpy as np

# --- Configuration Constants ---
THREADS_PER_BLOCK = 256

def get_grid_size(n):
    """Calculates the number of blocks needed for N elements."""
    return (n + (THREADS_PER_BLOCK - 1)) // THREADS_PER_BLOCK

# --- 1-State (Legacy) Bitwise Kernels ---

@cuda.jit
def k_and(a, b, out, n):
    idx = cuda.grid(1)
    if idx < n: out[idx] = a[idx] & b[idx]

@cuda.jit
def k_or(a, b, out, n):
    idx = cuda.grid(1)
    if idx < n: out[idx] = a[idx] | b[idx]

@cuda.jit
def k_xor(a, b, out, n):
    idx = cuda.grid(1)
    if idx < n: out[idx] = a[idx] ^ b[idx]

@cuda.jit
def k_not(a, out, n):
    idx = cuda.grid(1)
    if idx < n: out[idx] = ~a[idx]

# --- 4-State (V/S) Bitwise Kernels ---

@cuda.jit
def k_and_4state(a_v, a_s, b_v, b_s, out_v, out_s, n):
    """
    4-State AND with correct controlling value semantics.
    
    Truth Table:
    - 0 & X = 0 (0 is controlling value)
    - 1 & 1 = 1
    - Any & X = X (if no controlling value)
    
    NOTE: Contains branches which cause warp divergence.
    Correctness over performance for now.
    """
    idx = cuda.grid(1)
    if idx < n:
        # Check for controlling 0: (v=0, s=1)
        a_is_zero = (a_v[idx] == 0) and (a_s[idx] == 1)
        b_is_zero = (b_v[idx] == 0) and (b_s[idx] == 1)
        
        if a_is_zero or b_is_zero:
            # 0 dominates - output is 0
            out_v[idx] = 0
            out_s[idx] = 1
        elif (a_s[idx] == 1) and (b_s[idx] == 1):
            # Both valid (not X/Z) - normal AND
            out_v[idx] = a_v[idx] & b_v[idx]
            out_s[idx] = 1
        else:
            # At least one is X/Z - output is X
            out_v[idx] = 0
            out_s[idx] = 0


@cuda.jit
def k_or_4state(a_v, a_s, b_v, b_s, out_v, out_s, n):
    """
    4-State OR with correct controlling value semantics.
    
    Truth Table:
    - 1 | X = 1 (1 is controlling value)
    - 0 | 0 = 0
    - Any | X = X (if no controlling value)
    
    NOTE: Contains branches which cause warp divergence.
    Correctness over performance for now.
    """
    idx = cuda.grid(1)
    if idx < n:
        # Check for controlling 1: (v=1, s=1)
        a_is_one = (a_v[idx] == 1) and (a_s[idx] == 1)
        b_is_one = (b_v[idx] == 1) and (b_s[idx] == 1)
        
        if a_is_one or b_is_one:
            # 1 dominates - output is 1
            out_v[idx] = 1
            out_s[idx] = 1
        elif (a_s[idx] == 1) and (b_s[idx] == 1):
            # Both valid (not X/Z) - normal OR
            out_v[idx] = a_v[idx] | b_v[idx]
            out_s[idx] = 1
        else:
            # At least one is X/Z - output is X
            out_v[idx] = 0
            out_s[idx] = 0


@cuda.jit
def k_not_4state(a_v, a_s, out_v, out_s, n):
    """
    4-State NOT with X-propagation.
    
    Truth Table:
    - ~0 = 1
    - ~1 = 0
    - ~X = X
    - ~Z = X
    
    NOTE: Uses XOR for inversion, not bitwise complement.
    """
    idx = cuda.grid(1)
    if idx < n:
        # If input is valid (s=1), invert value bit
        # Otherwise output is X
        if a_s[idx] == 1:
            out_v[idx] = a_v[idx] ^ 1  # XOR to flip 0<->1
            out_s[idx] = 1
        else:
            out_v[idx] = 0
            out_s[idx] = 0


@cuda.jit
def k_xor_4state(a_v, a_s, b_v, b_s, out_v, out_s, n):
    """
    4-State XOR Kernel with proper X/Z propagation.
    
    Truth Table:
    - 0 ^ 0 = 0
    - 0 ^ 1 = 1
    - 1 ^ 0 = 1
    - 1 ^ 1 = 0
    - Any ^ X = X
    - Any ^ Z = X
    """
    idx = cuda.grid(1)
    if idx < n:
        # Check if inputs are valid (S=1 means valid, S=0 means X/Z)
        valid_a = a_s[idx]
        valid_b = b_s[idx]
        
        # If either input is invalid (X or Z), output is X
        if (valid_a == 0) or (valid_b == 0):
            out_v[idx] = 0  # X state value
            out_s[idx] = 0  # Invalid strength
        else:
            # Both inputs are valid (0 or 1), perform standard XOR
            out_v[idx] = a_v[idx] ^ b_v[idx]
            out_s[idx] = 1  # Valid strength

# --- Sequential Logic Kernels ---

@cuda.jit
def k_dff_update(d, q, reset, n):
    """Legacy 1-state DFF update kernel."""
    idx = cuda.grid(1)
    if idx < n:
        if reset[idx] != 0:
            q[idx] = 0
        else:
            q[idx] = d[idx]

@cuda.jit
def k_dff_update_4state(d_v, d_s, q_v, q_s, rst_v, rst_s, n):
    """
    4-State D Flip-Flop Update Kernel with X-Propagation.
    
    Critical for catching reset-recovery bugs:
    - If Reset is X, output becomes X (corrupted state)
    - If Reset is 1 (active), output becomes 0
    - If Reset is 0 (inactive), output samples D (including X states)
    """
    idx = cuda.grid(1)
    if idx < n:
        # 1. Check Reset Strength First
        # If Reset is X or Z (invalid), the whole state gets corrupted
        if rst_s[idx] == 0:
            q_v[idx] = 0  # X state value
            q_s[idx] = 0  # State becomes X
            
        # 2. If Reset is 1 (Active High), force state to 0
        elif rst_v[idx] == 1:
            q_v[idx] = 0  # Value 0
            q_s[idx] = 1  # Valid state
            
        # 3. If Reset is 0 (Inactive), sample Data input
        else:
            # Pass D straight through to Q (sampled at clock edge)
            # If D was X, Q becomes X - this is X-propagation
            q_v[idx] = d_v[idx]
            q_s[idx] = d_s[idx]

# --- FAULT INJECTION KERNELS ---

@cuda.jit
def k_inject_fault(val, strength, fault_en, fault_val, n):
    """
    Overwrites signal state if fault_en is high.
    val/strength: The target signal's data (IN/OUT modified in-place)
    fault_en: 1 = Inject Fault, 0 = Leave Signal Alone
    fault_val: The value to force (0 or 1)
    """
    idx = cuda.grid(1)
    if idx < n:
        # If this specific thread (chip instance) has a fault enabled:
        if fault_en[idx] == 1:
            val[idx] = fault_val[idx]
            strength[idx] = 1  # Faults are "Strong" drivers (Valid)
            # Note: We overwrite whatever logic calculated previously
