from __future__ import annotations
from typing import Tuple, Any
import numpy as np

from .base import Backend, LogicBuffers

class CpuBackend(Backend):
    """CPU-based backend using NumPy for all operations."""

    @property
    def name(self) -> str:
        return "cpu"

    def alloc_logic(self, batch_size: int, dtype=np.uint32) -> Tuple[Any, Any]:
        v = np.zeros(batch_size, dtype=dtype)
        s = np.zeros(batch_size, dtype=dtype)
        return v, s

    def copy_from_host(self, buffers: LogicBuffers, host_v, host_s) -> None:
        buffers.v[:] = host_v
        buffers.s[:] = host_s

    def to_host(self, v_data, s_data):
        return v_data.copy(), s_data.copy()
        
    def get_device_array(self, host_data: np.ndarray) -> Any:
        return host_data.copy()

    # 4-state encodings: 
    # 0: V=0,S=1; 1: V=1,S=1; X: V=0,S=0; Z: V=1,S=0

    def logic_and(self, out: LogicBuffers, a: LogicBuffers, b: LogicBuffers, n: int) -> None:
        # 4-State AND: 
        # If either is 0 (V=0, S=1), result is 0 (V=0, S=1).
        # Else if both are 1 (V=1, S=1), result is 1 (V=1, S=1).
        # Else result is X (V=0, S=0).
        
        # Mask for "Strong 0"
        a_zero = (a.s == 1) & (a.v == 0)
        b_zero = (b.s == 1) & (b.v == 0)
        any_zero = a_zero | b_zero
        
        # Mask for "Strong 1"
        a_one = (a.s == 1) & (a.v == 1)
        b_one = (b.s == 1) & (b.v == 1)
        both_one = a_one & b_one
        
        # Result V: 1 if both_one, else 0
        out.v[:] = np.where(both_one, 1, 0)
        # Result S: 1 if (any_zero or both_one), else 0
        out.s[:] = np.where(any_zero | both_one, 1, 0)

    def logic_or(self, out: LogicBuffers, a: LogicBuffers, b: LogicBuffers, n: int) -> None:
        # 4-State OR:
        # If either is 1, result is 1.
        # Else if both are 0, result is 0.
        # Else X.
        
        a_one = (a.s == 1) & (a.v == 1)
        b_one = (b.s == 1) & (b.v == 1)
        any_one = a_one | b_one
        
        a_zero = (a.s == 1) & (a.v == 0)
        b_zero = (b.s == 1) & (b.v == 0)
        both_zero = a_zero & b_zero
        
        out.v[:] = np.where(any_one, 1, 0)
        out.s[:] = np.where(any_one | both_zero, 1, 0)

    def logic_xor(self, out: LogicBuffers, a: LogicBuffers, b: LogicBuffers, n: int) -> None:
        # 4-State XOR:
        # If both valid, XOR values. Else X.
        valid_mask = (a.s == 1) & (b.s == 1)
        out.v[:] = np.where(valid_mask, a.v ^ b.v, 0)
        out.s[:] = np.where(valid_mask, 1, 0)

    def logic_not(self, out: LogicBuffers, a: LogicBuffers, n: int) -> None:
        # 4-State NOT:
        # If valid, invert value. Else X.
        valid = (a.s == 1)
        out.v[:] = np.where(valid, a.v ^ 1, 0)
        out.s[:] = np.where(valid, 1, 0)

    def dff_update(self, q_next: LogicBuffers, d: LogicBuffers, rst: LogicBuffers, n: int) -> None:
        # 1. Check Reset Strength
        rst_invalid = (rst.s == 0)
        
        # 2. Check Reset Value (Active High)
        rst_active = (rst.v == 1)
        
        # Logic:
        # If rst invalid -> X
        # Elif rst active -> 0 (Valid)
        # Else -> D
        
        # Default to D
        new_v = d.v.copy()
        new_s = d.s.copy()
        
        # Apply Reset Active (Force 0)
        mask_rst = rst_active & (~rst_invalid)
        new_v[mask_rst] = 0
        new_s[mask_rst] = 1
        
        # Apply Reset Invalid (Force X)
        new_v[rst_invalid] = 0
        new_s[rst_invalid] = 0
        
        q_next.v[:] = new_v
        q_next.s[:] = new_s

    def inject_fault(self, target: LogicBuffers, en_mask: LogicBuffers, val_mask: LogicBuffers, n: int) -> None:
        mask = en_mask.v.astype(bool)
        target.v[mask] = val_mask.v[mask]
        target.s[mask] = 1
