# GPU Validation Checklist

## Critical Gap: No GPU Testing Yet

**Current State**: CUDA kernel fixes are implemented and look correct, but have NOT been validated on actual hardware. All CUDA tests are being skipped in CI.

## Priority 1: Run CUDA Tests on Real Hardware

### Prerequisites
- Access to H100, A100, or similar NVIDIA GPU
- CUDA toolkit installed
- numba with CUDA support

### Validation Steps

```bash
# 1. Clone repository on GPU machine
git clone https://github.com/apmorey93/cuverif.git
cd cuverif

# 2. Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov

# 3. Verify CUDA is available
python -c "from numba import cuda; print(f'CUDA Available: {cuda.is_available()}')"

# 4. Run parametric tests (CPU + CUDA)
pytest tests/test_logic_truth_tables.py -v

# Expected output if fix is correct:
# test_and_truth_table[cpu] PASSED
# test_and_truth_table[cuda] PASSED  ← Must see this
# test_or_truth_table[cpu] PASSED
# test_or_truth_table[cuda] PASSED   ← Must see this
# ... all 8 tests passing

# 5. Run with coverage
pytest tests/test_logic_truth_tables.py --cov=cuverif.backend.cuda_backend -v

# 6. Run DFF tests
pytest tests/test_dff_semantics.py -v
```

### Success Criteria

✅ **All CUDA tests must PASS**
- No skipped tests
- test_and_truth_table[cuda] validates `0 & X = 0` fix
- test_or_truth_table[cuda] validates `1 | X = 1` fix
- test_not_truth_table[cuda] validates XOR inversion

❌ **If any CUDA test FAILS**
- Indicates kernel bug still exists
- Must debug with CUDA-GDB or print statements
- Compare exact (v, s) outputs vs CPU backend

### Known Risks

1. **Numba JIT bugs**: Numba's CUDA compiler might miscompile the branching logic
2. **Integer overflow**: uint32 operations might behave differently on GPU
3. **Race conditions**: Memory ordering issues (unlikely but possible)

## Priority 2: Real VCS Validation

Once CUDA tests pass on GPU:

```bash
# 1. Get VCS access (Synopsys commercial license)
vcs -sverilog tests/tb_dummy.sv dummy.v -o sim_dummy

# 2. Run simulation
./sim_dummy

# 3. Parse VCD output
python tools/parse_vcd.py tools/dummy_vcs.vcd tools/trace_vcs.json

# 4. Compare against CuVerif (CPU backend first)
python tools/compare_traces.py tools/trace_cuverif.json tools/trace_vcs.json

# Expected: 0 mismatches

# 5. Compare CUDA backend vs VCS
python tools/trace_cuverif.py --backend cuda
python tools/compare_traces.py tools/trace_cuverif_cuda.json tools/trace_vcs.json
```

## Priority 3: Performance Profiling

With Nsight Compute:

```bash
# Profile specific kernels
ncu --set full --target-processes all python -c "
from cuverif.backend.cuda_backend import CudaBackend
# ... run workload
"

# Look for:
# - Warp divergence percentage
# - Memory throughput vs peak bandwidth
# - Occupancy (should be >50%)
# - Branch efficiency
```

## Priority 4: Optimization Experiments

Only after correctness is validated:
- Try interleaved V/S memory layout
- Experiment with packed 2-bit encoding
- Profile different thread block sizes (128, 256, 512)

---

## Documentation Requirements

After GPU validation, update:
1. `TEST_STATUS.md`: Change "CUDA: Skipped" → "CUDA: Passing on H100"
2. `CUDA_PERF_NOTES.md`: Add actual profiling data
3. `README.md`: Can claim "Validated on GPU" instead of "CPU-only testing"

---

## Failure Recovery

If CUDA tests fail on hardware:
1. Capture exact failure case (which test, which input)
2. Add debug prints to kernel to see actual (v, s) values
3. Compare kernel output vs CPU backend on same input
4. File issue with exact reproduction steps
5. DO NOT merge or claim correctness until fixed

**Bottom line**: Until someone runs this on real GPU hardware and shows me green checkmarks for all CUDA tests, the correctness fix is unverified.
