# VCS Golden Harness - Test Summary

## Methodology

**Goal**: Establish equivalence between CuVerif and VCS simulation on a reference design.

**Design Under Test**: `dummy.v` (simple AND gate: `q = clk & rst`)

**Stimulus**: 200 cycles of deterministic pseudo-random inputs (seed=42)

**Signals Compared**: `clk`, `rst`, `q`

**Backend Used**: CPU (golden reference implementation)

## Results

### Mock VCS Mode (CPU vs CPU)

**Date**: 2025-11-21

**Status**: ✅ **0 mismatches** across 200 cycles

**Interpretation**: 
- CuVerif CPU backend produces self-consistent results
- Stimulus generation, trace extraction, and comparison scripts working correctly
- Mock mode validates the test harness infrastructure

### Real VCS Mode

**Status**: ⏸️ Pending VCS access

**Next Steps**:
1. Compile `dummy.v` with VCS: `vcs -sverilog tests/tb_dummy.sv dummy.v`
2. Run simulation: `./simv`
3. Parse VCD: `python tools/parse_vcd.py tools/dummy_vcs.vcd tools/trace_vcs.json`
4. Compare: `python tools/compare_traces.py tools/trace_cuverif.json tools/trace_vcs.json`
5. Document results (expected: 0 mismatches if logic correct)

## Limitations

- **Single design**: Only tested on `dummy.v` (trivial AND gate)
- **No CUDA validation yet**: CUDA backend not tested against VCS
- **No complex circuits**: Missing DFF, scan chains, multi-gate netlists
- **Mock mode caveat**: CPU-vs-CPU comparison doesn't validate CUDA correctness

## Future Work

1. Test against real VCS on `dummy.v`
2. Add `simple_cpu.v` (has DFF + combinational logic)
3. Run CUDA backend trace and compare
4. Expand to larger blocks (>100 gates)
5. Add fault injection scenarios

---
*Last Updated: 2025-11-21*
