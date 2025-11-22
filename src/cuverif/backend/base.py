from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Tuple
import numpy as np

class LogicBuffers:
    """Small helper to keep v/s together cleanly."""
    __slots__ = ("v", "s")

    def __init__(self, v, s):
        self.v = v
        self.s = s

class Backend(ABC):
    """
    Abstract interface for compute backends (CPU, CUDA, etc.)
    All LogicTensor operations delegate to a backend for actual computation.
    
    Backends are treated as singleton identity objects - operations between
    tensors from different backend instances are not supported.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the backend name (e.g., 'cpu', 'cuda')."""
        ...

    @abstractmethod
    def alloc_logic(self, batch_size: int, dtype=np.uint32) -> Tuple[Any, Any]:
        """Allocate (v_data, s_data) buffers on this backend."""

    @abstractmethod
    def copy_from_host(self, buffers: LogicBuffers, host_v, host_s) -> None:
        """
        Copy host numpy arrays into backend device buffers.
        
        Args:
            buffers: Device buffers to write to (v, s)
            host_v: Host numpy array (uint32) for value bits
            host_s: Host numpy array (uint32) for strength bits
        """
        ...

    @abstractmethod
    def to_host(self, v_data: Any, s_data: Any) -> Tuple[np.ndarray, np.ndarray]:
        """Copy value/strength arrays from device to host numpy."""
        
    @abstractmethod
    def get_device_array(self, host_data: np.ndarray) -> Any:
        """Transfer host array to device."""

    # ---- logic operations ----
    @abstractmethod
    def logic_and(self, out: LogicBuffers, a: LogicBuffers, b: LogicBuffers, n: int) -> None: ...
    @abstractmethod
    def logic_or(self, out: LogicBuffers, a: LogicBuffers, b: LogicBuffers, n: int) -> None: ...
    @abstractmethod
    def logic_xor(self, out: LogicBuffers, a: LogicBuffers, b: LogicBuffers, n: int) -> None: ...
    @abstractmethod
    def logic_not(self, out: LogicBuffers, a: LogicBuffers, n: int) -> None: ...

    # ---- sequential / DFF ----
    @abstractmethod
    def dff_update(self, q_next: LogicBuffers, d: LogicBuffers, rst: LogicBuffers, n: int) -> None: ...

    # ---- faults ----
    @abstractmethod
    def inject_fault(self, target: LogicBuffers, en_mask: LogicBuffers, val_mask: LogicBuffers, n: int) -> None: ...
