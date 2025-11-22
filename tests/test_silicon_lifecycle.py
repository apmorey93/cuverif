"""
Silicon Lifecycle Test - Fuses & Debug Port
===========================================
Tests OTP fuse memory and debug port functionality.
Simulates a secure boot scenario where chip behavior depends on fuse values.
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    import cuverif.core as cv
    import cuverif.modules as modules
    import cuverif.debug as debug
    print("Using Real GPU CuVerif Library")
except ImportError:
    print("GPU Library not found. Using CPU Mock for Silicon Lifecycle verification.")
    import tests.mock_cuverif as cv
    import tests.mock_cuverif as modules
    
    # Minimal mock for debug port
    class DebugPort:
        def __init__(self):
            self.reg_map = {}
        def add_register(self, name, address, tensor_ref):
            self.reg_map[name] = {"name": name, "addr": address, "ref": tensor_ref}
            self.reg_map[address] = self.reg_map[name]
        def read(self, target):
            tensor = self.reg_map[target]["ref"]
            return tensor.val, tensor.x
        def write(self, target, value, mask=None):
            tensor = self.reg_map[target]["ref"]
            if isinstance(value, int):
                import numpy as np
                tensor.val[:] = value
                tensor.x[:] = 1
    
    class Debug:
        DebugPort = DebugPort
    debug = Debug()
    
    # Mock FuseBank
    class FuseBank:
        def __init__(self, num_bits, batch_size):
            import numpy as np
            self.num_bits = num_bits
            self.batch_size = batch_size
            self.fuses = [cv.LogicTensor(data_v=np.zeros(batch_size, dtype=np.uint32),
                                          data_s=np.ones(batch_size, dtype=np.uint32)) 
                          for _ in range(num_bits)]
            self.q = [cv.LogicTensor(data_v=np.zeros(batch_size, dtype=np.uint32),
                                      data_s=np.ones(batch_size, dtype=np.uint32)) 
                      for _ in range(num_bits)]
        def step(self, read_en, prog_en, addr, wdata):
            # Simplified mock - just copy fuses to q if read_en
            if addr < self.num_bits:
                # Sticky OR for programming
                burn = prog_en.val & wdata.val
                self.fuses[addr].val[:] = self.fuses[addr].val | burn
            # Read logic
            for i in range(self.num_bits):
                if hasattr(read_en.val, '__iter__'):
                    for j in range(self.batch_size):
                        if read_en.val[j]:
                            self.q[i].val[j] = self.fuses[i].val[j]
                else:
                    if read_en.val:
                        self.q[i].val[:] = self.fuses[i].val[:]
        def backdoor_burn(self, bit_index, mask):
            self.fuses[bit_index].val[:] = self.fuses[bit_index].val | mask.val
        def backdoor_read(self):
            return [(f.val, f.x) for f in self.fuses]
    
    modules.FuseBank = FuseBank

import numpy as np

def test_secure_boot():
    print("=" * 70)
    print("SILICON LIFECYCLE TEST (Fuses & Debug)")
    print("=" * 70)
    
    BATCH = 10
    
    # 1. SETUP HARDWARE
    print("\n[Phase 1] Creating Hardware Components")
    
    # A Fuse Bank with 4 bits
    fuses = modules.FuseBank(num_bits=4, batch_size=BATCH)
    print(f"  Created FuseBank: {fuses.num_bits} bits, {BATCH} instances")
    
    # A generic control register (Flip Flop)
    # This represents "Secure Mode Enable" (1=Secure, 0=Open)
    secure_reg = modules.DFlipFlop(BATCH)
    print(f"  Created SECURE_EN register")
    
    # A Debug Port
    ral = debug.DebugPort()
    ral.add_register("SECURE_EN", 0x100, secure_reg.q)
    print(f"  Registered SECURE_EN at address 0x100")
    
    # 2. BURN FUSES (Binning)
    print("\n[Phase 2] Factory Programming (Fuse Burning)")
    print("  Burning Fuse[0] on Instance #5 (Production Chip)")
    print("  All other instances remain unfused (Debug Chips)")
    
    burn_mask_host = np.zeros(BATCH, dtype=np.uint32)
    burn_mask_host[5] = 1
    burn_mask = cv.LogicTensor(data_v=burn_mask_host, 
                                data_s=np.ones(BATCH, dtype=np.uint32))
    
    fuses.backdoor_burn(0, burn_mask)
    
    # Verify burn
    fuse_state = fuses.backdoor_read()
    vals = fuse_state[0][0] if isinstance(fuse_state[0], tuple) else fuse_state[0].cpu()[0]
    print(f"  Fuse[0] State: Instance 0={vals[0]}, Instance 5={vals[5]}")
    
    # 3. SIMULATE BOOT LOGIC
    print("\n[Phase 3] Simulating Boot Sequence")
    print("  Logic: If Fuse[0]==1 -> Set SECURE_EN=1, Else SECURE_EN=0")
    
    # Read Fuses (Enable Sense Amps)
    read_en = cv.LogicTensor(data_v=np.ones(BATCH, dtype=np.uint32),
                              data_s=np.ones(BATCH, dtype=np.uint32))
    prog_en = cv.zeros(BATCH)
    fuses.step(read_en, prog_en, 0, cv.zeros(BATCH))
    
    # Connect Fuse[0] to Secure_Reg Input
    fuse_val = fuses.q[0]
    secure_reg.step(fuse_val)  # Clock the logic
    
    # 4. VERIFY VIA DEBUG PORT
    print("\n[Phase 4] Reading Register via Debug Port")
    vals, strs = ral.read("SECURE_EN")
    
    print(f"  Instance 0 (Unfused): SECURE_EN = {vals[0]}")
    print(f"  Instance 5 (Fused):   SECURE_EN = {vals[5]}")
    
    success = True
    if vals[5] == 1 and vals[0] == 0:
        print("  [PASS] Fuse logic correctly set Secure Mode")
    else:
        print(f"  [FAIL] Secure Mode logic failed (expected 0,1 got {vals[0]},{vals[5]})")
        success = False

    # 5. TEST DEBUG OVERRIDE (HACKING)
    print("\n[Phase 5] Testing Debug Override")
    print("  Attempting to force-write '0' to all instances via debug port...")
    
    ral.write("SECURE_EN", 0)  # Broadcast 0 to all
    
    vals_hack, _ = ral.read("SECURE_EN")
    print(f"  Instance 5 Post-Override: SECURE_EN = {vals_hack[5]}")
    
    if vals_hack[5] == 0:
        print("  [PASS] Debug port successfully overrode register state")
    else:
        print(f"  [FAIL] Debug write failed (expected 0, got {vals_hack[5]})")
        success = False
        
    return success

if __name__ == "__main__":
    try:
        result = test_secure_boot()
        if result:
            print("\n[SUCCESS] Silicon Lifecycle Test Passed")
        else:
            print("\n[FAILURE] Silicon Lifecycle Test Failed")
    except Exception as e:
        print(f"\n[ERROR] Test crashed: {e}")
        import traceback
        traceback.print_exc()
