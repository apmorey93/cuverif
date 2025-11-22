# CuVerif Validation Summary

## 4-state logic + DFF

- **Designs:** 
  - DFT Block A (Synthetic, ~40k gates)
  - DFT Block B (Synthetic, ~90k gates)
- **Flow:** Gate-level Verilog, single clock domain, no SDF
- **Patterns:** 10k random functional patterns per design
- **Comparison:** CuVerif vs VCS (Synopsys) value/X/Z per cycle
- **Result:** **0 mismatches** under these constraints

## Known Limitations (Current Version)

### Not Validated / Not Supported
- **Multi-clock / CDC-heavy designs:** Current scheduler assumes single synchronous clock domain.
- **SDF / Timing Annotation:** Simulations are zero-delay functional only.
- **Power-aware behavior:** UPF/CPF constructs are ignored.
- **Tri-state buses:** Z-state is supported in logic, but resolution functions for multiple drivers are basic.

### Performance Constraints
- **GPU Memory:** Max instance count is limited by VRAM (approx 10M instances on 80GB H100).
- **Compilation Time:** Python generation for >1M gate designs may be slow (regex parser limitation).

## Validation Strategy
We use a "Gold Model" approach:
1. Run standard VCS simulation to generate VCD.
2. Run CuVerif simulation with same inputs.
3. Compare output states cycle-by-cycle.

*To run the validation suite yourself, see `tests/test_x_propagation.py`.*
