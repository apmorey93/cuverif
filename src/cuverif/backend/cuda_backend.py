from __future__ import annotations
from typing import Tuple, Any
import numpy as np
from numba import cuda

from .base import Backend, LogicBuffers

# Import kernels from the cuda_kernels module
from .. import cuda_kernels as K

_THREADS_PER_BLOCK = 256

class CudaBackend(Backend):
    name = "cuda"

    def __init__(self, device_id: int = 0):
        try:
            self.device = cuda.select_device(device_id)
        except Exception:
            # Fallback or error handling
            pass

    def alloc_logic(self, batch_size: int, dtype=np.uint32) -> Tuple[Any, Any]:
        v = cuda.device_array(batch_size, dtype=dtype)
        s = cuda.device_array(batch_size, dtype=dtype)
        return v, s

    def to_host(self, v_data, s_data):
        return v_data.copy_to_host(), s_data.copy_to_host()
        
    def get_device_array(self, host_data: np.ndarray) -> Any:
        return cuda.to_device(host_data)

    def _launch_1d(self, kernel, n: int, *args):
        blocks = (n + _THREADS_PER_BLOCK - 1) // _THREADS_PER_BLOCK
        kernel[blocks, _THREADS_PER_BLOCK](*args, n)

    def logic_and(self, out: LogicBuffers, a: LogicBuffers, b: LogicBuffers, n: int) -> None:
        self._launch_1d(K.k_and_4state, n, a.v, a.s, b.v, b.s, out.v, out.s)

    def logic_or(self, out: LogicBuffers, a: LogicBuffers, b: LogicBuffers, n: int) -> None:
        self._launch_1d(K.k_or_4state, n, a.v, a.s, b.v, b.s, out.v, out.s)

    def logic_xor(self, out: LogicBuffers, a: LogicBuffers, b: LogicBuffers, n: int) -> None:
        self._launch_1d(K.k_xor_4state, n, a.v, a.s, b.v, b.s, out.v, out.s)

    def logic_not(self, out: LogicBuffers, a: LogicBuffers, n: int) -> None:
        self._launch_1d(K.k_not_4state, n, a.v, a.s, out.v, out.s)

    def dff_update(self, q_next: LogicBuffers, d: LogicBuffers, rst: LogicBuffers, n: int) -> None:
        self._launch_1d(K.k_dff_update_4state, n, d.v, d.s, q_next.v, q_next.s, rst.v, rst.s)

    def inject_fault(self, target: LogicBuffers, en_mask: LogicBuffers, val_mask: LogicBuffers, n: int) -> None:
        self._launch_1d(K.k_inject_fault, n, target.v, target.s, en_mask.v, val_mask.v)
