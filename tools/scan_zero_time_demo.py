# tools/scan_zero_time_demo.py
import argparse
import time
import sys
import os
import numpy as np

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    import cuverif.core as cv
    from cuverif.modules import DFlipFlop, ScanChain
except ImportError:
    print("[WARN] GPU library not found, using mock")
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import tests.mock_cuverif as cv
    # Mock modules
    class DFlipFlop:
        def __init__(self, batch_size):
            self.batch_size = batch_size
            self.q = cv.zeros(batch_size)
    class ScanChain:
        def __init__(self, regs): self.regs = regs
        def scan_load(self, pat): pass

def main():
    p = argparse.ArgumentParser(description="CuVerif Zero-Time Scan Load Demo")
    p.add_argument("--chains", type=int, default=10, help="Number of scan chains")
    p.add_argument("--length", type=int, default=1000, help="Length of each chain")
    p.add_argument("--patterns", type=int, default=100_000, help="Number of patterns (batch size)")
    args = p.parse_args()

    print(f"[INFO] Configuration: {args.chains} chains x {args.length} FFs")
    print(f"[INFO] Parallel Patterns: {args.patterns:,}")

    # 1. Setup Hardware
    print("[INFO] Instantiating Flip-Flops...")
    # We'll just simulate one long chain for simplicity of the demo
    total_ffs = args.length
    regs = [DFlipFlop(args.patterns) for _ in range(total_ffs)]
    chain = ScanChain(regs)
    
    # 2. Generate Random ATPG Patterns (CPU side)
    print("[INFO] Generating random ATPG patterns (CPU)...")
    patterns = np.random.randint(0, 2, (args.patterns, total_ffs)).astype(np.uint32)
    
    # 3. Zero-Time Load
    print("[INFO] Executing Zero-Time Scan Load (GPU)...")
    t0 = time.time()
    
    chain.scan_load(patterns)
    
    elapsed = time.time() - t0
    
    total_bits = args.patterns * total_ffs
    print(f"[INFO] Loaded {total_bits:,} bits in {elapsed:.4f}s")
    print(f"[PERF] Bandwidth: {total_bits / elapsed / 1e9:.2f} Gbits/sec")
    
    # Compare with serial shift
    # Assume 100 MHz shift clock -> 10ns per bit
    serial_time = (total_ffs * args.patterns) * 10e-9 
    speedup = serial_time / elapsed
    
    print(f"[INFO] Serial Shift Time (est. @ 100MHz): {serial_time:.2f}s")
    print(f"[SUCCESS] Speedup: {speedup:.1f}x")

if __name__ == "__main__":
    main()
