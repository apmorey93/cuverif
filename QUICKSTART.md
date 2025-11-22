# CuVerif Quick Start Guide

## Installation

```bash
# Clone repository
git clone https://github.com/apmorey93/cuverif.git
cd cuverif

# Install dependencies
pip install -r requirements.txt

# Optional: Install in development mode
pip install -e .
```

## Basic Usage

### 1. Run Smoke Test (Verify Installation)

```bash
python smoke_test.py
```

Expected output: All basic components working.

### 2. Simple Simulation Example

```python
import cuverif.core as cv
from cuverif.modules import DFlipFlop

# Create a D flip-flop (10 parallel instances)
dff = DFlipFlop(batch_size=10)

# Create input: all 1s
d_input = cv.ones(10)
reset = cv.zeros(10)

# Simulate one clock cycle
dff.step(d_input, reset)

# Check output
print(f"Q output: {dff.q.cpu()}")
# Should show (v=[1,1,1...], s=[1,1,1...])
```

### 3. Fault Injection Example

```python
from cuverif.faults import FaultCampaign
import cuverif.core as cv

# Create campaign with 1000 parallel fault simulations
campaign = FaultCampaign(batch_size=1000)

# Index 0 is always the gold (fault-free) model
gold_idx = 0

# Add stuck-at-0 fault on wire A
sa0_idx = campaign.add_fault("wire_A_SA0", stuck_value=0)

# Add stuck-at-1 fault on wire A  
sa1_idx = campaign.add_fault("wire_A_SA1", stuck_value=1)

# Simulate circuit
wire_a = cv.ones(1000)  # All instances start with wire_a = 1

# Apply fault masks
en_mask, val_mask = campaign.get_masks("wire_A_SA0")
wire_a.force(en_mask, val_mask)

# Check results
v, s = wire_a.cpu()
print(f"Gold model wire_a: {v[gold_idx]}")  # Should be 1
print(f"SA0 fault wire_a: {v[sa0_idx]}")    # Should be 0 (fault applied)
```

### 4. Compile Verilog Netlist

```python
from cuverif.compiler import VerilogCompiler

# Read your netlist
with open("my_design.v", "r") as f:
    verilog_code = f.read()

# Compile to Python model
compiler = VerilogCompiler()
chip = compiler.compile(verilog_code, batch_size=1000)

# Simulate
inputs = {
    'clk': cv.zeros(1000),
    'rst': cv.ones(1000),
    'data_in': cv.randint(0, 2, 1000)
}

# Set inputs
for sig_name, tensor in inputs.items():
    chip.set_input(sig_name, tensor)

# Run one cycle
chip.step()

# Read outputs
result = chip.get_output('data_out')
```

## Running Tests

### CPU Backend Tests (Always Available)

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_logic_truth_tables.py -v

# Run with coverage
pytest tests/ --cov=cuverif --cov-report=html
```

### GPU Backend Tests (Requires CUDA)

```bash
# Check CUDA availability
python -c "from numba import cuda; print(f'CUDA: {cuda.is_available()}')"

# Run parametric tests (both CPU and CUDA)
pytest tests/test_logic_truth_tables.py -v
# Should see both [cpu] and [cuda] variants
```

## VCS Golden Harness

### Mock Mode (No VCS Required)

```bash
# 1. Generate stimulus
python tools/generate_stimulus.py

# 2. Run CuVerif trace
python tools/trace_cuverif.py

# 3. Generate mock "VCS" output
python tools/mock_vcs.py

# 4. Compare traces
python tools/compare_traces.py tools/trace_cuverif.json tools/trace_vcs_mock.json
```

Expected: `[SUCCESS] 0 mismatches found`

### Real VCS Mode (Requires Commercial License)

```bash
# 1. Generate stimulus
python tools/generate_stimulus.py

# 2. Run CuVerif
python tools/trace_cuverif.py

# 3. Compile with VCS
vcs -sverilog tests/tb_dummy.sv dummy.v -o sim_dummy

# 4. Run VCS simulation
./sim_dummy

# 5. Parse VCD
python tools/parse_vcd.py tools/dummy_vcs.vcd tools/trace_vcs.json

# 6. Compare
python tools/compare_traces.py tools/trace_cuverif.json tools/trace_vcs.json
```

## Command-Line Interface (Experimental)

```bash
# Fault grading
python -m cuverif.cli fault-grade --netlist my_design.v --patterns patterns.npy

# VCD simulation
python -m cuverif.cli sim-vcd --netlist my_design.v --cycles 1000 --output sim.vcd
```

Note: CLI is currently in development. See `src/cuverif/cli.py`.

## Troubleshooting

### Import Errors

```python
# If you get "ModuleNotFoundError: No module named 'cuverif'"
import sys
sys.path.insert(0, '/path/to/cuverif/src')
import cuverif.core as cv
```

### CUDA Not Available

If CUDA tests are skipped:
- Check: `nvidia-smi` (GPU visible?)
- Check: `nvcc --version` (CUDA toolkit installed?)
- Check: `pip show numba` (numba version >= 0.56?)

### Memory Errors

If you get OOM (out of memory):
- Reduce `batch_size` (e.g., 100,000 instead of 1,000,000)
- Check available GPU memory: `nvidia-smi`

### Performance Issues

- Start with CPU backend for debugging, switch to CUDA for production
- Use smaller batch sizes for development
- Profile with: `python -m cProfile -o profile.stats your_script.py`

## Next Steps

- Read `TEST_STATUS.md` for validation status
- Read `CUDA_PERF_NOTES.md` for performance characteristics
- See examples in `tests/` directory
- For GPU validation: see `GPU_VALIDATION_CHECKLIST.md`

## Getting Help

- Check existing tests in `tests/` for usage patterns
- Review `PROJECT_SUMMARY.md` for architecture overview
- File issues on GitHub with reproduction steps
