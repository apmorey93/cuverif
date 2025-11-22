# CuVerif Setup Guide

## Prerequisites

### Hardware Requirements
- **NVIDIA GPU** (CUDA Compute Capability 5.0+)
- Tested on: GTX 1060+, RTX 20/30/40 series, Tesla/Quadro/A-series

### Software Requirements
1. **Python 3.7+** (Recommended: 3.9+)
2. **CUDA Toolkit** (11.0+ recommended)
   - Download from: https://developer.nvidia.com/cuda-downloads
3. **NVIDIA GPU Drivers** (Latest version)

---

## Installation

### Step 1: Install CUDA Toolkit
```bash
# Windows: Download and run installer from NVIDIA
# Verify installation:
nvcc --version
```

### Step 2: Install Python Dependencies
```bash
# Navigate to project directory
cd cuverif

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Verify Numba CUDA Support
```python
# Run this in Python to check CUDA availability
from numba import cuda
print(cuda.gpus)
```

If this shows your GPU, you're ready! If not, see **Troubleshooting** below.

---

## For Google Colab Users

Colab has CUDA pre-installed! Just install the Python packages:

```python
# In a Colab cell:
!pip install numba matplotlib

# Verify GPU is available
from numba import cuda
if cuda.is_available():
    print(f"✓ GPU Detected: {cuda.gpus[0].name}")
else:
    print("✗ No GPU found - check Runtime > Change runtime type > GPU")
```

---

## Quick Start

### 1. Run Smoke Test
```bash
python smoke_test.py
```

Expected output:
```
✓ Successfully imported cuverif.core
✓ XOR verified: [0 1 1 0]
✓ AND verified: [1 0 0 0]
...
SUCCESS: All smoke tests passed!
```

### 2. Run X-Propagation Test (Phase 2)
```bash
python tests/test_x_propagation.py
```

Expected output:
```
======================================================================
X-PROPAGATION VERIFICATION TEST
======================================================================
✓ Reset X-Propagation: Q becomes X when Reset is X
✓ Reset Recovery: Q recovers to 1 when Reset=0, Data=1
...
✓ SUCCESS: All X-propagation scenarios verified!
```

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'numba'`
**Solution:**
```bash
pip install numba
```

### Issue: `CudaSupportError: Error at driver init`
**Possible causes:**
1. **No NVIDIA GPU** - CuVerif requires CUDA hardware
2. **Outdated drivers** - Update to latest NVIDIA drivers
3. **CUDA toolkit not installed** - Install from NVIDIA website

**Debug:**
```python
from numba import cuda
print(cuda.detect())  # Shows detailed CUDA info
```

### Issue: Numba installs but `cuda.is_available()` returns False
**Solution:**
```bash
# Reinstall CUDA-enabled Numba
pip uninstall numba
pip install --upgrade numba
```

### Issue: "CUDA driver version is insufficient"
**Solution:** Update GPU drivers to match your CUDA toolkit version

---

## Development Setup

### Running Tests
```bash
# All tests
python smoke_test.py
python tests/test_x_propagation.py

# With pytest (optional)
pip install pytest
pytest tests/
```

### Interactive Development (Jupyter/Colab)
```python
import sys
import os
sys.path.append(os.path.abspath('src'))

import cuverif.core as cv
import cuverif.modules as modules
import numpy as np

# Create a simple circuit
a = cv.randint(0, 2, 1000)  # 1000 parallel instances
b = cv.randint(0, 2, 1000)
c = a ^ b  # XOR on GPU

# Get results
v, s = c.cpu()
print(f"Computed {len(v)} XOR operations on GPU!")
```

---

## Environment Variables (Optional)

```bash
# Force specific GPU (if multiple GPUs)
set CUDA_VISIBLE_DEVICES=0

# Numba debugging
set NUMBA_ENABLE_CUDASIM=1  # CPU simulation mode (slow, no GPU needed)
```

---

## Next Steps

1. ✓ Verify installation with `smoke_test.py`
2. ✓ Run X-propagation tests
3. □ Read `4state_implementation_plan.md` for architecture details
4. □ Check `README.md` for usage examples
5. □ Start building your own circuits!

---

## Getting Help

- **CUDA Installation**: https://docs.nvidia.com/cuda/cuda-installation-guide-windows/
- **Numba CUDA Docs**: https://numba.readthedocs.io/en/stable/cuda/
- **CuVerif Issues**: Check the GitHub repository (when published)

---

## Minimum Tested Configuration

- **OS**: Windows 10/11, Linux (Ubuntu 20.04+)
- **Python**: 3.9.13
- **CUDA**: 11.7
- **Numba**: 0.56.4
- **NumPy**: 1.23.5
- **GPU**: GTX 1660 (tested on Colab T4)
