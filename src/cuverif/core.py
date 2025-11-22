from __future__ import annotations
from typing import Any
import numpy as np

from cuverif.backend import Backend, DEFAULT_BACKEND, LogicBuffers

# --- 4-State Logic Constants ---
V_0, S_0 = 0, 1  # State 0
V_1, S_1 = 1, 1  # State 1
V_X, S_X = 0, 0  # State X (Unknown)
V_Z, S_Z = 1, 0  # State Z (High Impedance)

class LogicTensor:
    """
    4-state logic vector on a chosen backend.

    Invariants:
    - v_data and s_data are backend-owned buffers of length batch_size.
    - All tensors participating in an op must share the same backend and batch_size.
    """

    __slots__ = ("backend", "batch_size", "v_data", "s_data")

    def __init__(
        self,
        batch_size: int = 0, # Default to 0 if not provided, though usually required
        backend: Backend | None = None,
        v_data: Any | None = None,
        s_data: Any | None = None,
        # Legacy/Helper args for backward compat or ease of use
        data_v=None, data_s=None, shape=None, gpu_ref_v=None, gpu_ref_s=None
    ):
        self.backend = backend or DEFAULT_BACKEND
        
        # Handle legacy/helper constructors
        if gpu_ref_v is not None:
            self.v_data = gpu_ref_v
            self.s_data = gpu_ref_s
            self.batch_size = gpu_ref_v.size # Assuming size attr exists
        elif shape is not None:
            self.batch_size = shape
            self.v_data, self.s_data = self.backend.alloc_logic(shape)
            # Init to 0
            # Note: alloc_logic might return uninitialized memory depending on backend
            # For safety in this constructor we should init, but for perf we might not want to.
            # The original code did zeros/ones init.
            # Let's assume alloc gives us usable memory, but we need to set values.
            # CPU backend gives zeros. CUDA gives uninitialized.
            # We'll manually set to 0 state (V=0, S=1)
            # This is inefficient if we overwrite immediately, but safe.
            # TODO: Optimize init
            # For now, let's trust the factory methods (zeros/ones) are preferred.
            pass 
        elif data_v is not None and data_s is not None:
            data_v = np.array(data_v, dtype=np.uint32)
            data_s = np.array(data_s, dtype=np.uint32)
            self.batch_size = data_v.size
            self.v_data = self.backend.get_device_array(data_v)
            self.s_data = self.backend.get_device_array(data_s)
        else:
            # Direct init (preferred internal path)
            self.batch_size = batch_size
            if v_data is None or s_data is None:
                 if batch_size > 0:
                    v_data, s_data = self.backend.alloc_logic(batch_size)
            self.v_data = v_data
            self.s_data = s_data

    # ---- helpers ----

    def _buffers(self) -> LogicBuffers:
        return LogicBuffers(self.v_data, self.s_data)

    def _ensure_compatible(self, other: "LogicTensor"):
        if self.backend is not other.backend:
            raise ValueError(f"Backend mismatch: {self.backend} vs {other.backend}")
        if self.batch_size != other.batch_size:
            raise ValueError(f"Batch size mismatch: {self.batch_size} vs {other.batch_size}")

    # Ergonomic property aliases
    @property
    def val(self): return self.v_data
    @property
    def x(self): return self.s_data
    @property
    def size(self): return self.batch_size

    # ---- constructors ----

    @classmethod
    def zeros(cls, batch_size, backend: Backend | None = None) -> "LogicTensor":
        t = cls(batch_size, backend=backend)
        # 0: V=0, S=1. Need backend-specific fill or copy.
        # For now, we'll use a slow but safe host-to-device copy for initialization
        # to avoid adding fill() to backend interface yet.
        # TODO: Add fill() to backend
        v = np.zeros(batch_size, dtype=np.uint32)
        s = np.ones(batch_size, dtype=np.uint32)
        t.v_data = t.backend.get_device_array(v)
        t.s_data = t.backend.get_device_array(s)
        return t

    @classmethod
    def ones(cls, batch_size, backend: Backend | None = None) -> "LogicTensor":
        t = cls(batch_size, backend=backend)
        v = np.ones(batch_size, dtype=np.uint32)
        s = np.ones(batch_size, dtype=np.uint32)
        t.v_data = t.backend.get_device_array(v)
        t.s_data = t.backend.get_device_array(s)
        return t
        
    @classmethod
    def randint(cls, low, high, size, backend: Backend | None = None) -> "LogicTensor":
        t = cls(size, backend=backend)
        v = np.random.randint(low, high, size, dtype=np.uint32)
        s = np.ones(size, dtype=np.uint32)
        t.v_data = t.backend.get_device_array(v)
        t.s_data = t.backend.get_device_array(s)
        return t
        
    @classmethod
    def unknown(cls, size, backend: Backend | None = None) -> "LogicTensor":
        t = cls(size, backend=backend)
        v = np.zeros(size, dtype=np.uint32)
        s = np.zeros(size, dtype=np.uint32)
        t.v_data = t.backend.get_device_array(v)
        t.s_data = t.backend.get_device_array(s)
        return t

    # ---- logic ops ----

    def __and__(self, other: "LogicTensor") -> "LogicTensor":
        self._ensure_compatible(other)
        out = LogicTensor(self.batch_size, backend=self.backend)
        self.backend.logic_and(out._buffers(), self._buffers(), other._buffers(), self.batch_size)
        return out

    def __or__(self, other: "LogicTensor") -> "LogicTensor":
        self._ensure_compatible(other)
        out = LogicTensor(self.batch_size, backend=self.backend)
        self.backend.logic_or(out._buffers(), self._buffers(), other._buffers(), self.batch_size)
        return out

    def __xor__(self, other: "LogicTensor") -> "LogicTensor":
        self._ensure_compatible(other)
        out = LogicTensor(self.batch_size, backend=self.backend)
        self.backend.logic_xor(out._buffers(), self._buffers(), other._buffers(), self.batch_size)
        return out

    def __invert__(self) -> "LogicTensor":
        out = LogicTensor(self.batch_size, backend=self.backend)
        self.backend.logic_not(out._buffers(), self._buffers(), self.batch_size)
        return out

    def force(self, enable_mask, value_mask):
        """Injects stuck-at faults."""
        self._ensure_compatible(enable_mask)
        self._ensure_compatible(value_mask)
        self.backend.inject_fault(self._buffers(), enable_mask._buffers(), value_mask._buffers(), self.batch_size)
        return self

    # ---- host access ----

    def cpu(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (values, strengths) as numpy arrays."""
        return self.backend.to_host(self.v_data, self.s_data)

    def __repr__(self) -> str:
        v, s = self.cpu()
        # Show first few elements
        limit = 8
        v_str = str(v[:limit]) + ("..." if self.batch_size > limit else "")
        s_str = str(s[:limit]) + ("..." if self.batch_size > limit else "")
        return f"LogicTensor(batch={self.batch_size}, backend={self.backend.name}, v={v_str}, s={s_str})"

# --- Utility Constructors (Global Wrappers) ---

def randint(low, high, size):
    return LogicTensor.randint(low, high, size)

def zeros(size):
    return LogicTensor.zeros(size)

def ones(size):
    return LogicTensor.ones(size)

def unknown(size):
    return LogicTensor.unknown(size)
