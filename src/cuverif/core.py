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
        batch_size: int | None = None,
        *,
        backend: Backend | None = None,
        v_data: Any | None = None,
        s_data: Any | None = None,
    ):
        self.backend = backend or DEFAULT_BACKEND
        
        # Case 1: Wrap existing device buffers (Internal/Advanced)
        if v_data is not None and s_data is not None:
            self.v_data = v_data
            self.s_data = s_data
            if batch_size is None:
                # Try to infer, but prefer explicit
                if hasattr(v_data, "size"):
                    self.batch_size = v_data.size
                else:
                    raise ValueError("batch_size must be provided when using raw device buffers")
            else:
                self.batch_size = int(batch_size)
                
        # Case 2: Allocate new buffers
        elif batch_size is not None:
            self.batch_size = int(batch_size)
            self.v_data, self.s_data = self.backend.alloc_logic(self.batch_size)
            
        else:
            raise ValueError("Must provide batch_size or (v_data, s_data)")

        # Invariants
        if self.v_data is None or self.s_data is None:
            raise RuntimeError("LogicTensor constructed without device buffers")
        if self.batch_size <= 0:
            raise RuntimeError(f"Invalid batch_size={self.batch_size}")

    @classmethod
    def from_host(cls, data_v, data_s, backend: Backend | None = None) -> "LogicTensor":
        """Creates a LogicTensor from host numpy arrays."""
        backend = backend or DEFAULT_BACKEND
        data_v = np.asarray(data_v, dtype=np.uint32)
        data_s = np.asarray(data_s, dtype=np.uint32)
        
        if data_v.shape != data_s.shape:
            raise ValueError("data_v and data_s must have the same shape")
            
        batch_size = int(data_v.size)
        
        # Allocate device buffers
        t = cls(batch_size=batch_size, backend=backend)
        
        # Copy host data to device via backend
        backend.copy_from_host(t._buffers(), data_v, data_s)
            
        return t

    @classmethod
    def from_device(cls, v_data, s_data, batch_size: int, backend: Backend | None = None) -> "LogicTensor":
        """Wraps existing device buffers into a LogicTensor."""
        return cls(batch_size=batch_size, backend=backend, v_data=v_data, s_data=s_data)

    # ---- helpers ----

    def _buffers(self) -> LogicBuffers:
        return LogicBuffers(self.v_data, self.s_data)

    def _ensure_compatible(self, other: "LogicTensor"):
        """
        Verify that two tensors can participate in the same operation.
        
        Backends are treated as singleton identity objects - we use `is` to check
        that both tensors use the same backend instance. This enforces that all
        operations use a consistent compute context.
        """
        if self.backend is not other.backend:
            raise ValueError(f"Backend mismatch: {self.backend} vs {other.backend}")
        if self.batch_size != other.batch_size:
            raise ValueError(f"Batch size mismatch: {self.batch_size} vs {other.batch_size}")

    # Ergonomic property aliases
    @property
    def val(self): return self.v_data
    @property
    def strength(self): return self.s_data
    @property
    def size(self): return self.batch_size

    # ---- constructors ----

    @classmethod
    def zeros(cls, batch_size, backend: Backend | None = None) -> "LogicTensor":
        # 0: V=0, S=1
        host_v = np.zeros(batch_size, dtype=np.uint32)
        host_s = np.ones(batch_size, dtype=np.uint32)
        return cls.from_host(host_v, host_s, backend=backend)

    @classmethod
    def ones(cls, batch_size, backend: Backend | None = None) -> "LogicTensor":
        # 1: V=1, S=1
        host_v = np.ones(batch_size, dtype=np.uint32)
        host_s = np.ones(batch_size, dtype=np.uint32)
        return cls.from_host(host_v, host_s, backend=backend)
        
    @classmethod
    def randint(cls, low, high, size, backend: Backend | None = None) -> "LogicTensor":
        host_v = np.random.randint(low, high, size, dtype=np.uint32)
        host_s = np.ones(size, dtype=np.uint32)
        return cls.from_host(host_v, host_s, backend=backend)
        
    @classmethod
    def unknown(cls, size, backend: Backend | None = None) -> "LogicTensor":
        # X: V=0, S=0
        host_v = np.zeros(size, dtype=np.uint32)
        host_s = np.zeros(size, dtype=np.uint32)
        return cls.from_host(host_v, host_s, backend=backend)
        
    @classmethod
    def hiz(cls, size, backend: Backend | None = None) -> "LogicTensor":
        # Z: V=1, S=0 (High Impedance)
        host_v = np.ones(size, dtype=np.uint32)
        host_s = np.zeros(size, dtype=np.uint32)
        return cls.from_host(host_v, host_s, backend=backend)

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
