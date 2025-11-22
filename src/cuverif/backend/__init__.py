from .base import Backend, LogicBuffers
from .cpu_backend import CpuBackend

def select_default_backend() -> Backend:
    try:
        import numba.cuda as cuda
        if cuda.is_available():
            from .cuda_backend import CudaBackend
            return CudaBackend()
    except Exception:
        pass
    return CpuBackend()

DEFAULT_BACKEND: Backend = select_default_backend()
