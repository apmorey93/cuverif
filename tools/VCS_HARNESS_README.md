# VCS Golden Harness - Mock VCS Mode

Since VCS is a commercial tool not available in this environment, this harness supports a **mock VCS mode** for development and CI.

## Usage

### With Real VCS

```bash
# 1. Generate stimulus
python tools/generate_stimulus.py

# 2. Run CuVerif simulation
python tools/trace_cuverif.py

# 3. Compile and run VCS
vcs -sverilog tests/tb_dummy.sv dummy.v -o sim_dummy
./sim_dummy

# 4. Parse VCD output
python tools/parse_vcd.py tools/dummy_vcs.vcd tools/trace_vcs.json

# 5. Compare traces
python tools/compare_traces.py tools/trace_cuverif.json tools/trace_vcs.json
```

### Mock VCS Mode (No VCS Required)

```bash
# Run with --mock-vcs flag
python tools/compare_vs_vcs.py --netlist dummy.v --mock-vcs
```

This mode:
- Generates deterministic "VCS" output using the CPU backend
- Useful for testing the harness without VCS
- Validates stimulus generation, parsing, and comparison logic

## File Descriptions

- `generate_stimulus.py`: Creates deterministic stimulus (seed=42)
- `trace_cuverif.py`: Runs CuVerif simulation, outputs JSON
- `tb_dummy.sv`: VCS testbench (reads stimulus, dumps VCD)
- `parse_vcd.py`: Parses VCD to JSON format
- `compare_traces.py`: Compares two JSON traces, reports mismatches

## Expected Output (0 Mismatches)

```
======================================================================
VCS vs CuVerif Trace Comparison
======================================================================

Loading CuVerif trace: tools/trace_cuverif.json
Loading VCS trace: tools/trace_vcs.json

Comparing signals: ['clk', 'q', 'rst']
CuVerif cycles: 200
VCS cycles: 200

======================================================================
✅ SUCCESS: 0 mismatches found
======================================================================
```
