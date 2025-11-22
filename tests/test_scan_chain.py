import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    import cuverif.core as cv
    import cuverif.modules as modules
    from cuverif.faults import FaultCampaign
    print("Using Real GPU CuVerif Library")
except ImportError:
    print("GPU Library not found. Using CPU Mock for Scan Chain verification.")
    import tests.mock_cuverif as cv
    import tests.mock_cuverif as modules # Will need to update mock modules
    
    # Mock FaultCampaign
    class FaultCampaign:
        def __init__(self, batch_size):
            self.batch_size = batch_size
            self.fault_list = []
            self.next_free_index = 1 
        def add_fault(self, name, fault_type):
            idx = self.next_free_index
            self.fault_list.append({"name": name, "type": fault_type, "index": idx})
            self.next_free_index += 1
            return idx
        def get_masks(self, current_signal_name):
            import numpy as np
            en_host = np.zeros(self.batch_size, dtype=np.uint32)
            val_host = np.zeros(self.batch_size, dtype=np.uint32)
            for fault in self.fault_list:
                if fault["name"] == current_signal_name:
                    t_idx = fault["index"]
                    en_host[t_idx] = 1
                    val_host[t_idx] = fault["type"]
            return cv.LogicTensor(data_v=en_host, data_s=np.ones(self.batch_size)), \
                   cv.LogicTensor(data_v=val_host, data_s=np.ones(self.batch_size))

import numpy as np

def test_atpg_flow():
    print("=" * 70)
    print("ATPG FLOW TEST (Scan Load -> Capture -> Unload)")
    print("=" * 70)
    
    BATCH = 10
    
    # 1. Define Hardware (A pipeline)
    # Reg A -> Logic (NOT) -> Reg B
    reg_a = modules.DFlipFlop(BATCH)
    reg_b = modules.DFlipFlop(BATCH)
    
    # Create the Scan Chain
    # Chain: SI -> Reg A -> Reg B -> SO
    scan_chain = modules.ScanChain([reg_a, reg_b])
    
    # 2. Define Faults
    # We want to detect "Reg A Q Stuck-at-0"
    # To detect this, we must load a '1' into Reg A. 
    # If it's stuck at 0, it will stay 0.
    campaign = FaultCampaign(BATCH)
    idx_fault = campaign.add_fault("reg_a_q", 0) # SA0
    
    # 3. ATPG Pattern Generation
    # We want Pattern: A=1, B=0 (Random)
    # Shape: [Batch, 2]
    pattern_host = np.zeros((BATCH, 2), dtype=np.uint32)
    pattern_host[:, 0] = 1 # Set A=1 for ALL instances
    pattern_host[:, 1] = 0 # Set B=0
    
    print("1. [Scan Load] Loading Pattern '10' (Instant Teleport)...")
    scan_chain.scan_load(pattern_host)
    
    # Check internal state
    # Handle both real and mock return types
    val_a = reg_a.q.cpu() if hasattr(reg_a.q, 'cpu') else reg_a.q.val
    if isinstance(val_a, tuple): val_a = val_a[0] # Real lib returns (v, s)
    
    print(f"   Reg A Internal (First 5): {val_a[:5]}")
    
    # 4. INJECT FAULTS
    # Apply the fault mask to Reg A's output
    en, val = campaign.get_masks("reg_a_q")
    
    if hasattr(reg_a.q, 'force'):
        reg_a.q.force(en, val)
    else:
        # Manual force for mock
        print("   (Applying manual force for mock)")
        for i in range(BATCH):
            if en.val[i] == 1:
                reg_a.q.val[i] = val.val[i]
                reg_a.q.x[i] = 1
    
    # 5. [Capture] Run Logic
    # Combinational Logic: B_next = NOT(Reg_A)
    # If A=1 (Gold), B_next should be 0.
    # If A=0 (Fault), B_next should be 1.
    val_a_tensor = reg_a.q
    next_b = ~val_a_tensor
    
    # Clock the destination register (Reg B) to capture the result
    reg_b.step(next_b)
    
    print("2. [Capture] Clock Pulse Applied.")
    
    # 6. [Scan Unload] Check Results
    # We read Reg B.
    res_b = reg_b.q.cpu() if hasattr(reg_b.q, 'cpu') else reg_b.q.val
    if isinstance(res_b, tuple): res_b = res_b[0]
    
    print(f"3. [Result] Reg B State: {res_b}")
    
    success = True
    
    # Instance 0 (Gold): A=1 -> NOT -> B=0
    if res_b[0] == 0: 
        print("[PASS] Gold instance captured 0.")
    else: 
        print(f"[FAIL] Gold instance mismatch. Got {res_b[0]}")
        success = False
        
    # Instance 1 (Fault A SA0): A=0 -> NOT -> B=1
    if res_b[idx_fault] == 1: 
        print("[PASS] Fault detected! (Captured 1 instead of 0)")
    else: 
        print(f"[FAIL] Fault NOT detected. Got {res_b[idx_fault]}")
        success = False
        
    return success

if __name__ == "__main__":
    if test_atpg_flow():
        print("\n[SUCCESS] ATPG Scan Chain Flow Verified!")
    else:
        print("\n[FAILURE] ATPG Tests Failed")
