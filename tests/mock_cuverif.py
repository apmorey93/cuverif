"""
Mock CuVerif for CPU-only testing
=================================
This module mocks the core functionality of CuVerif using pure NumPy,
allowing tests to run in environments without CUDA/Numba (like this one).
"""

import numpy as np

class LogicTensor:
    def __init__(self, batch_size=None, v_data=None, s_data=None):
        if v_data is not None and s_data is not None:
            self.v_data = v_data
            self.s_data = s_data
        elif batch_size is not None:
            self.v_data = np.zeros(batch_size, dtype=np.uint32)
            self.s_data = np.ones(batch_size, dtype=np.uint32)
        else:
            raise ValueError("Invalid mock init")
            
    @classmethod
    def from_host(cls, data_v, data_s, backend=None):
        return cls(v_data=np.array(data_v, dtype=np.uint32), 
                   s_data=np.array(data_s, dtype=np.uint32))
                   
    @classmethod
    def zeros(cls, size): return cls.from_host(np.zeros(size), np.ones(size))
    @classmethod
    def ones(cls, size): return cls.from_host(np.ones(size), np.ones(size))
    @classmethod
    def unknown(cls, size): return cls.from_host(np.zeros(size), np.zeros(size))
    @classmethod
    def randint(cls, low, high, size):
        return cls.from_host(np.random.randint(low, high, size), np.ones(size))
        # Mock XOR logic
        # If either is X (S=0), output is X
        # Else output is A^B
        valid = self.s_data & other.s_data
        val = (self.v_data ^ other.v_data) * valid
        return LogicTensor(val, valid)

    def __and__(self, other):
        # Mock AND logic
        val = self.v_data & other.v_data
        valid = self.s_data & other.s_data
        return LogicTensor(val, valid)

    def __or__(self, other):
        # Mock OR logic
        val = self.v_data | other.v_data
        valid = self.s_data & other.s_data
        return LogicTensor(val, valid)

    def __invert__(self):
        # Mock NOT logic
        val = (~self.v_data) & 1 # Keep 1-bit
        valid = self.s_data
        return LogicTensor(val, valid)

# Mock Monitor that works with CPU arrays
class Monitor:
    def __init__(self, signals, instance_id=0):
        self.signals = signals
        self.instance_id = instance_id
        self.history = {k: [] for k in signals}
        self.time = []
        self.cycle = 0

    def sample(self):
        self.time.append(self.cycle)
        for k, tensor in self.signals.items():
            # Direct array access for mock
            v_val = tensor.v_data[self.instance_id]
            s_val = tensor.s_data[self.instance_id]
            
            # Plot logic: 0.5 for X (Strength=0), else Value
            plot_val = float(v_val) if s_val == 1 else 0.5
            self.history[k].append(plot_val)
            
        self.cycle += 1

    def export_vcd(self, filename="wave.vcd"):
        # Copy-pasted logic from real Monitor to ensure identical behavior
        print(f"Exporting Instance {self.instance_id} to {filename}...")
        with open(filename, "w") as f:
            import datetime
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"$date\n  {date_str}\n$end\n")
            f.write("$version\n  CuVerif GPU Simulator (Mock)\n$end\n")
            f.write("$timescale\n  1ns\n$end\n")
            f.write("$scope module top $end\n")
            
            symbols = {}
            for i, name in enumerate(self.signals.keys()):
                sym = chr(33 + i) 
                symbols[name] = sym
                f.write(f"$var wire 1 {sym} {name} $end\n")
            
            f.write("$upscope $end\n")
            f.write("$enddefinitions $end\n")
            
            f.write("#0\n")
            for name, vals in self.history.items():
                if not vals: continue
                val = vals[0]
                sym = symbols[name]
                vcd_val = 'x'
                if val == 0.0: vcd_val = '0'
                elif val == 1.0: vcd_val = '1'
                f.write(f"{vcd_val}{sym}\n")
                
            for t in range(1, len(self.time)):
                timestamp = self.time[t] * 10
                f.write(f"#{timestamp}\n")
                for name, vals in self.history.items():
                    val = vals[t]
                    prev_val = vals[t-1]
                    if val != prev_val:
                        sym = symbols[name]
                        vcd_val = 'x'
                        if val == 0.0: vcd_val = '0'
                        elif val == 1.0: vcd_val = '1'
                        f.write(f"{vcd_val}{sym}\n")

# Mock DFlipFlop
class DFlipFlop:
    def __init__(self, batch_size):
        self.q = LogicTensor(batch_size=batch_size)
        
    def step(self, d, reset=None):
        # CPU implementation of 4-state logic
        if reset is None:
            reset = zeros(len(d.v_data))
            
        for i in range(len(d.v_data)):
            # Reset logic
            if reset.s_data[i] == 0: # Reset is X
                self.q.v_data[i] = 0
                self.q.s_data[i] = 0
            elif reset.v_data[i] == 1: # Reset is 1
                self.q.v_data[i] = 0
                self.q.s_data[i] = 1
            else: # Sample data
                self.q.v_data[i] = d.v_data[i]
                self.q.s_data[i] = d.s_data[i]
        return self.q

class ScanChain:
    def __init__(self, registers):
        self.chain = registers
        self.length = len(registers)

    def scan_load(self, pattern_val, pattern_x=None):
        # Mock zero-time load
        for i, reg in enumerate(self.chain):
            col_val = pattern_val[:, i].astype(np.uint32)
            reg.q.v_data[:] = col_val
            
            if pattern_x is not None:
                col_x = pattern_x[:, i].astype(np.uint32)
                reg.q.s_data[:] = col_x
            else:
                reg.q.s_data[:] = 1

# Helper constructors
def zeros(size): return LogicTensor(np.zeros(size), np.ones(size))
def unknown(size): return LogicTensor(np.zeros(size), np.zeros(size))
def randint(low, high, size):
    """Mock randint: generates random 0/1 values with valid strength"""
    v_data = np.random.randint(low, high, size, dtype=np.uint32)
    s_data = np.ones(size, dtype=np.uint32)
    return LogicTensor(v_data, s_data)
