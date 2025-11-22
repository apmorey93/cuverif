"""
CuVerif JTAG Module - IEEE 1149.1, 1687, and 1838 Support
==========================================================
Implements:
- IEEE 1149.1: Boundary Scan (TAP Controller)
- IEEE 1687: Internal JTAG (iJTAG) with SIB
- IEEE 1838: 3D Test Access (TSV-based stacking)
"""

import numpy as np
import cuverif.core as cv
import cuverif.modules as modules

# --- CONSTANTS: IEEE 1149.1 TAP STATES ---
TEST_LOGIC_RESET = 0
RUN_TEST_IDLE    = 1
SELECT_DR_SCAN   = 2
CAPTURE_DR       = 3
SHIFT_DR         = 4
EXIT1_DR         = 5
PAUSE_DR         = 6
EXIT2_DR         = 7
UPDATE_DR        = 8
SELECT_IR_SCAN   = 9
CAPTURE_IR       = 10
SHIFT_IR         = 11
EXIT1_IR         = 12
PAUSE_IR         = 13
EXIT2_IR         = 14
UPDATE_IR        = 15

class TAPController:
    """
    Hardware Model of an IEEE 1149.1 TAP Controller.
    Manages the 16-state FSM based on TCK and TMS.
    """
    def __init__(self, batch_size):
        self.batch_size = batch_size
        # State Register (4 bits to hold 0-15)
        # We use a simplified integer tensor for state tracking in this behavioral model
        # In a gate-level netlist, this would be 4 Flip-Flops.
        self.state = cv.zeros(batch_size) 
        
        # Output Signals
        self.shift_dr = cv.zeros(batch_size)
        self.update_dr = cv.zeros(batch_size)
        self.shift_ir = cv.zeros(batch_size)
        self.update_ir = cv.zeros(batch_size)

    def step(self, tms, trst_n=None):
        """
        Advances the FSM one clock cycle based on TMS.
        This is a Behavioral Model (fast), not Gate-Level.
        """
        # 1. Handle Asynchronous Reset (TRST_N)
        if trst_n is not None:
            # If TRST_N is 0, State -> TEST_LOGIC_RESET (0)
            # We use force/mask logic here conceptually
            pass # TODO: Add explicit reset logic if needed

        # 2. Compute Next State (The Graph)
        # We pull data to CPU for FSM logic because implementing a 
        # 16-state lookup table in raw bitwise tensors is verbose.
        # For GPU speed, we would normally use a custom kernel here.
        # MVP: CPU-based state calculation, GPU-based execution.
        
        curr_s_arr = self.state.cpu()[0] # Get all instance states
        curr_tms_arr = tms.val.copy_to_host() if hasattr(tms.val, 'copy_to_host') else tms.val
        
        # Calculate next state for each instance
        next_s_arr = np.zeros(self.batch_size, dtype=np.uint32)
        for i in range(self.batch_size):
            curr_s = int(curr_s_arr[i])
            curr_tms = int(curr_tms_arr[i] if isinstance(curr_tms_arr, np.ndarray) else curr_tms_arr)
            next_s_arr[i] = self._get_next_state(curr_s, curr_tms)
        
        # Update State Tensor
        self.state = cv.LogicTensor(data_v=next_s_arr, data_s=np.ones(self.batch_size, dtype=np.uint32))
        
        # 3. Update Control Signals
        shift_dr_arr = (next_s_arr == SHIFT_DR).astype(np.uint32)
        update_dr_arr = (next_s_arr == UPDATE_DR).astype(np.uint32)
        shift_ir_arr = (next_s_arr == SHIFT_IR).astype(np.uint32)
        update_ir_arr = (next_s_arr == UPDATE_IR).astype(np.uint32)
        
        self.shift_dr = cv.LogicTensor(data_v=shift_dr_arr, data_s=np.ones(self.batch_size, dtype=np.uint32))
        self.update_dr = cv.LogicTensor(data_v=update_dr_arr, data_s=np.ones(self.batch_size, dtype=np.uint32))
        self.shift_ir = cv.LogicTensor(data_v=shift_ir_arr, data_s=np.ones(self.batch_size, dtype=np.uint32))
        self.update_ir = cv.LogicTensor(data_v=update_ir_arr, data_s=np.ones(self.batch_size, dtype=np.uint32))

    def _get_next_state(self, state, tms):
        # The standard JTAG State Diagram
        if tms == 1:
            if state == TEST_LOGIC_RESET: return TEST_LOGIC_RESET
            if state == RUN_TEST_IDLE:    return SELECT_DR_SCAN
            if state == SELECT_DR_SCAN:   return SELECT_IR_SCAN
            if state == SELECT_IR_SCAN:   return TEST_LOGIC_RESET
            if state == CAPTURE_DR:       return EXIT1_DR
            if state == SHIFT_DR:         return EXIT1_DR
            if state == EXIT1_DR:         return UPDATE_DR
            if state == PAUSE_DR:         return EXIT2_DR
            if state == EXIT2_DR:         return UPDATE_DR
            if state == UPDATE_DR:        return SELECT_DR_SCAN
            if state == CAPTURE_IR:       return EXIT1_IR
            if state == SHIFT_IR:         return EXIT1_IR
            if state == EXIT1_IR:         return UPDATE_IR
            if state == PAUSE_IR:         return EXIT2_IR
            if state == EXIT2_IR:         return UPDATE_IR
            if state == UPDATE_IR:        return SELECT_DR_SCAN
        else: # TMS == 0
            if state == TEST_LOGIC_RESET: return RUN_TEST_IDLE
            if state == RUN_TEST_IDLE:    return RUN_TEST_IDLE
            if state == SELECT_DR_SCAN:   return CAPTURE_DR
            if state == SELECT_IR_SCAN:   return CAPTURE_IR
            if state == CAPTURE_DR:       return SHIFT_DR
            if state == SHIFT_DR:         return SHIFT_DR
            if state == EXIT1_DR:         return PAUSE_DR
            if state == PAUSE_DR:         return PAUSE_DR
            if state == EXIT2_DR:         return SHIFT_DR
            if state == UPDATE_DR:        return RUN_TEST_IDLE
            if state == CAPTURE_IR:       return SHIFT_IR
            if state == SHIFT_IR:         return SHIFT_IR
            if state == EXIT1_IR:         return PAUSE_IR
            if state == PAUSE_IR:         return PAUSE_IR
            if state == EXIT2_IR:         return SHIFT_IR
            if state == UPDATE_IR:        return RUN_TEST_IDLE
        return state

class SIB:
    """
    IEEE 1687 Segment Insertion Bit (SIB).
    Manages dynamic scan chain length.
    """
    def __init__(self, tap_ctrl):
        self.batch_size = tap_ctrl.batch_size
        self.tap = tap_ctrl
        self.sib_reg = modules.DFlipFlop(self.batch_size)
        
    def step(self, tdi_in, scan_segment_func):
        """
        tdi_in: Data coming into the SIB
        scan_segment_func: A function/module that represents the sub-chain
        """
        # 1. Capture/Shift Logic
        # SIB Register only updates during SHIFT-DR or UPDATE-DR
        # 1687 says SIB configures on Update-DR.
        
        # Simplified: The SIB Reg is part of the scan chain.
        # If Tap is SHIFT-DR, we shift tdi_in into sib_reg
        
        # Mux Logic:
        # If SIB is Closed (0): TDO = SIB_Reg
        # If SIB is Open (1):   TDO = Segment_Out
        
        is_open = self.sib_reg.q
        
        # Path 1: Go through the segment (Long path)
        # We pass tdi_in to the segment
        seg_out = scan_segment_func(tdi_in) 
        
        # Path 2: Bypass (Short path)
        # TDO is just the SIB register itself
        bypass_out = self.sib_reg.q
        
        # The Output Mux
        # tdo = (is_open & seg_out) | (~is_open & bypass_out)
        # Using boolean algebra since we don't have a 'mux' kernel yet
        term1 = is_open & seg_out
        term2 = (~is_open) & bypass_out
        tdo = term1 | term2
        
        # Update SIB Register state (Shift)
        # Only shift if TAP is in SHIFT_DR
        shift_en = self.tap.shift_dr
        
        # If shifting, next state is TDI. If not, hold state.
        # d_next = (shift_en & tdi_in) | (~shift_en & current_q)
        d_next = (shift_en & tdi_in) | ((~shift_en) & self.sib_reg.q)
        
        # Update the FF
        self.sib_reg.step(d_next)
        
        return tdo

class DieWrapper:
    """
    Represents a single die in the 3D stack (IEEE 1838).
    Has specific IO for vertical connection via TSVs.
    """
    def __init__(self, name, tap_ctrl):
        self.name = name
        self.tap = tap_ctrl
        # Internal Chain (Instruction Register)
        self.ir_reg = modules.DFlipFlop(tap_ctrl.batch_size)
        # Internal Chain (Bypass Register)
        self.bypass_reg = modules.DFlipFlop(tap_ctrl.batch_size)

    def step_io(self, tck, tms, tdi, tdo_from_stack_above):
        """
        Executes one cycle of JTAG logic for this die.
        Returns dictionary of outputs (TDO_to_below, TCK_to_above, etc)
        """
        # 1. Update TAP Controller
        self.tap.step(tms)
        
        # 2. Decode Logic (Simplified)
        # If IR=All 1s -> Bypass Mode
        # If IR=All 0s -> Stack Mode (IEEE 1838)
        
        # 3. Scan Path Muxing
        # Path A: Through this die's registers (Bypass/IR)
        # Path B: Up the stack (TSV)
        
        # For this demo, we implement a simple Bypass path:
        # TDI -> Bypass Reg -> TDO
        
        # Shift Bypass Reg
        shift_en = self.tap.shift_dr
        d_next = (shift_en & tdi) | ((~shift_en) & self.bypass_reg.q)
        self.bypass_reg.step(d_next)
        
        local_tdo = self.bypass_reg.q
        
        # TSV Logic (Pass-through to go up)
        tsv_tck_up = tck
        tsv_tms_up = tms
        tsv_tdi_up = tdi 
        
        # Return IO
        return {
            'tdo_down': local_tdo,       # Goes to die below
            'tsv_tck':  tsv_tck_up,      # Goes to die above
            'tsv_tms':  tsv_tms_up,
            'tsv_tdi':  tsv_tdi_up
        }
