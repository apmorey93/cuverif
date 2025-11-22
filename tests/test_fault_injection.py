import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    import cuverif.core as cv
    from cuverif.faults import FaultCampaign
    print("Using Real GPU CuVerif Library")
except ImportError:
    print("GPU Library not found. Using CPU Mock for Fault Injection verification.")
    import tests.mock_cuverif as cv
    # Mock FaultCampaign for CPU testing
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

def test_fault_campaign():
    print("=" * 70)
    print("PARALLEL FAULT INJECTION CAMPAIGN")
    print("=" * 70)
    
    # 1. Setup: 5 Slots (1 Gold + 4 Faults)
    BATCH = 5
    campaign = FaultCampaign(BATCH)
    
    # 2. Define Faults
    # We will fault the "A" input
    idx_sa0 = campaign.add_fault("wire_A", 0) # Thread 1: A Stuck-at-0
    idx_sa1 = campaign.add_fault("wire_A", 1) # Thread 2: A Stuck-at-1
    
    print(f"Defined Campaign: Gold=0, A_SA0={idx_sa0}, A_SA1={idx_sa1}")

    # 3. Create Inputs
    # We apply A=1, B=1 to ALL instances
    # Expected Sum = 1^1 = 0
    # Expected Carry = 1&1 = 1
    A = cv.randint(1, 2, BATCH) # All 1s
    B = cv.randint(1, 2, BATCH) # All 1s
    
    # 4. INJECT FAULTS
    # "Force A to break based on the campaign map"
    en_mask, val_mask = campaign.get_masks("wire_A")
    
    # Note: Mock library needs force() method update too, but for now we'll assume
    # real library or update mock if needed. 
    # Let's update the mock LogicTensor in mock_cuverif.py to support force()
    # or just manually simulate it here if using mock.
    
    if hasattr(A, 'force'):
        A.force(en_mask, val_mask)
    else:
        # Manual force for mock if method missing
        print("Warning: force() not found on tensor (using Mock?), applying manually")
        for i in range(BATCH):
            if en_mask.val[i] == 1:
                A.val[i] = val_mask.val[i]
                A.x[i] = 1
    
    # 5. Run Logic (Full Adder - Half Stage)
    # Sum = A XOR B
    Sum = A ^ B
    
    # 6. Verify Results
    # Handle both real (copy_to_host) and mock (direct access)
    if hasattr(Sum.val, 'copy_to_host'):
        res = Sum.val.copy_to_host()
        inputs_a = A.val.copy_to_host()
        inputs_b = B.val.copy_to_host()
    else:
        res = Sum.val
        inputs_a = A.val
        inputs_b = B.val
    
    print("\nResults (Sum = A ^ B):")
    print(f"Inputs (A): {inputs_a}")
    print(f"Inputs (B): {inputs_b}")
    print(f"Outputs:    {res}")
    
    # Checks
    success = True
    
    # Instance 0 (Gold): 1 ^ 1 = 0
    if res[0] == 0: 
        print("[PASS] Gold Model correct (1^1=0)")
    else: 
        print(f"[FAIL] Gold Model broken! Got {res[0]}")
        success = False
        
    # Instance 1 (A SA0): 0 ^ 1 = 1 (Fault Detected!)
    if res[idx_sa0] == 1: 
        print("[PASS] A_SA0 Detected (Output flipped to 1)")
    else: 
        print(f"[FAIL] A_SA0 Not Detected! Output: {res[idx_sa0]}")
        success = False

    # Instance 2 (A SA1): 1 ^ 1 = 0 (Fault Masked / Not Detected)
    # Since input A was 1, forcing it to 1 does nothing. This is correct behavior.
    if res[idx_sa1] == 0: 
        print("[PASS] A_SA1 Masked (Input was already 1)")
    else: 
        print("[FAIL] A_SA1 behavior incorrect")
        success = False
        
    return success

if __name__ == "__main__":
    if test_fault_campaign():
        print("\n[SUCCESS] Parallel Fault Injection Verified!")
    else:
        print("\n[FAILURE] Fault Injection Tests Failed")
