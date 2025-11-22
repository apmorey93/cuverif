"""
VCS vs CuVerif Trace Comparison
================================

Compares signal traces from VCS and CuVerif simulations.
Reports mismatches and exits non-zero if any found.
"""

import json
import sys

def load_trace(path):
    """Load trace JSON file."""
    with open(path, 'r') as f:
        return json.load(f)

def compare_traces(cuverif_trace, vcs_trace, signals_to_compare=None):
    """
    Compare two traces cycle-by-cycle.
    
    Args:
        cuverif_trace: List of {cycle, signals}
        vcs_trace: List of {cycle, signals}
        signals_to_compare: List of signal names to check (None = all common)
        
    Returns:
        (num_mismatches, mismatch_list)
    """
    mismatches = []
    
    # Determine signals to compare
    if signals_to_compare is None:
        # Use intersection of signals
        cv_sigs = set(cuverif_trace[0]['signals'].keys()) if cuverif_trace else set()
        vcs_sigs = set(vcs_trace[0]['signals'].keys()) if vcs_trace else set()
        signals_to_compare = sorted(cv_sigs & vcs_sigs)
    
    print(f"Comparing signals: {signals_to_compare}")
    print(f"CuVerif cycles: {len(cuverif_trace)}")
    print(f"VCS cycles: {len(vcs_trace)}")
    print()
    
    # Compare cycle by cycle
    max_cycles = min(len(cuverif_trace), len(vcs_trace))
    
    for i in range(max_cycles):
        cv_cycle = cuverif_trace[i]
        vcs_cycle = vcs_trace[i]
        
        cycle_num = cv_cycle['cycle']
        
        for sig in signals_to_compare:
            cv_val = cv_cycle['signals'].get(sig, 'X')
            vcs_val = vcs_cycle['signals'].get(sig, 'X')
            
            # Normalize: treat Z same as X for comparison
            if cv_val == 'Z':
                cv_val = 'X'
            if vcs_val == 'Z' or vcs_val == 'z':
                vcs_val = 'X'
            if vcs_val == 'x':
                vcs_val = 'X'
            
            if cv_val != vcs_val:
                mismatches.append({
                    'cycle': cycle_num,
                    'signal': sig,
                    'cuverif': cv_val,
                    'vcs': vcs_val
                })
    
    return len(mismatches), mismatches

def main(cuverif_path, vcs_path, signals=None):
    """Main comparison entry point."""
    print("=" * 70)
    print("VCS vs CuVerif Trace Comparison")
    print("=" * 70)
    print()
    
    # Load traces
    print(f"Loading CuVerif trace: {cuverif_path}")
    cuverif_trace = load_trace(cuverif_path)
    
    print(f"Loading VCS trace: {vcs_path}")
    vcs_trace = load_trace(vcs_path)
    print()
    
    # Compare
    num_mismatches, mismatches = compare_traces(cuverif_trace, vcs_trace, signals)
    
    # Report
    if num_mismatches == 0:
        print("=" * 70)
        print("[SUCCESS] 0 mismatches found")
        print("=" * 70)
        return 0
    else:
        print("=" * 70)
        print(f"[FAILURE] {num_mismatches} mismatches found")
        print("=" * 70)
        print()
        
        # Show first 10 mismatches
        print("First 10 mismatches:")
        for m in mismatches[:10]:
            print(f"  Cycle {m['cycle']}, signal {m['signal']}: "
                  f"CuVerif={m['cuverif']}, VCS={m['vcs']}")
        
        if num_mismatches > 10:
            print(f"  ... and {num_mismatches - 10} more")
        
        return 1

if __name__ == "__main__":
    cuverif_trace = "tools/trace_cuverif.json"
    vcs_trace = "tools/trace_vcs.json"
    
    # Allow command-line override
    if len(sys.argv) > 1:
        cuverif_trace = sys.argv[1]
    if len(sys.argv) > 2:
        vcs_trace = sys.argv[2]
    
    exit_code = main(cuverif_trace, vcs_trace)
    sys.exit(exit_code)
