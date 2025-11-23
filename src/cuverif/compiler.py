"""
Verilog Compiler (Tier 2)
=========================
Parses structural Verilog (gate-level netlists) and compiles them into
a CuVerif `Chip` model for simulation.

Supported Subset:
- Modules: `module name (ports); ... endmodule`
- Declarations: `input`, `output`, `wire`
- Primitives: `and`, `or`, `xor`, `not`, `buf`, `nand`, `nor`, `xnor`
- Sequential: `dff` (Custom primitive: `dff name (q, d, clk, rst)`)

Limitatons:
- No behavioral code (`always`, `assign`, `if`, `case`).
- No vectors (everything is 1-bit scalar for now, or exploded).
- No parameters.
"""

import re
import sys
import os
import numpy as np

# Add src to path if running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cuverif.core as cv
import cuverif.modules as modules

class Chip:
    """
    Represents a compiled netlist ready for simulation.
    """
    def __init__(self, name, inputs, outputs, wires, instances, batch_size=1):
        self.name = name
        self.inputs = inputs   # List of names
        self.outputs = outputs # List of names
        self.wires = wires     # List of names (internal)
        self.instances = instances # List of (type, name, connections)
        self.batch_size = batch_size
        
        # Signal Store: {name: LogicTensor}
        self.signals = {}
        self._init_signals()
        
        # Topological sort or just list of gates?
        # For now, we assume the netlist is somewhat ordered or we iterate.
        # Ideally, we should topologically sort combinational logic.
        # But for a simple Tier 2 implementation, we might just run logic in order 
        # and assume the synthesizer did a good job, or run multiple iterations per cycle (delta cycles).
        # Let's do a simple topological sort for combinational gates.
        self.sorted_gates = self._topological_sort()
        
        # Separate DFFs
        self.dffs = [inst for inst in self.instances if inst['type'] == 'dff']

    def _init_signals(self):
        """Allocates LogicTensors for all signals."""
        # Start with explicit declarations
        all_sigs = set(self.inputs + self.outputs + self.wires)
        
        # Scan instances for implicit wires
        for inst in self.instances:
            for port in inst['ports']:
                all_sigs.add(port)
                
        for sig in all_sigs:
            self.signals[sig] = cv.zeros(self.batch_size)
            
    def _topological_sort(self):
        """
        Sorts combinational gates to ensure inputs are ready before evaluation.
        """
        comb_gates = [inst for inst in self.instances if inst['type'] != 'dff']
        
        # Build Dependency Graph
        # Node: Gate Index
        # Edge: Gate A -> Gate B if A produces a signal that B consumes
        
        # 1. Map Signal -> Producer Gate Index
        producer_map = {} # {signal_name: gate_index}
        
        for i, gate in enumerate(comb_gates):
            # Output is always port 0 for primitives
            out_sig = gate['ports'][0]
            producer_map[out_sig] = i
            
        # 2. Build Adjacency List (Gate -> Consumers)
        # and In-Degree (Gate -> Count of dependencies)
        adj = {i: [] for i in range(len(comb_gates))}
        in_degree = {i: 0 for i in range(len(comb_gates))}
        
        for i, gate in enumerate(comb_gates):
            # Inputs are ports 1..N
            inputs = gate['ports'][1:]
            for sig in inputs:
                if sig in producer_map:
                    producer = producer_map[sig]
                    adj[producer].append(i)
                    in_degree[i] += 1
                    
        # 3. Kahn's Algorithm
        queue = [i for i in range(len(comb_gates)) if in_degree[i] == 0]
        sorted_indices = []
        
        while queue:
            u = queue.pop(0)
            sorted_indices.append(u)
            
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
                    
        if len(sorted_indices) != len(comb_gates):
            # Cycle detected or logic error
            # For now, just append remaining (best effort) or raise error
            # raise ValueError("Combinational logic cycle detected!")
            pass
            
        return [comb_gates[i] for i in sorted_indices]

    def set_input(self, name, value_tensor):
        """Sets a primary input."""
        if name not in self.signals:
            raise ValueError(f"Unknown input: {name}")
        # We update the reference or copy data?
        # Copying data is safer to keep ownership clear.
        # self.signals[name].v_data[:] = value_tensor.v_data[:] # If supported
        # For now, just replace the object reference, but this breaks internal connections if they held refs.
        # The gates look up signals by name in self.signals every time? 
        # If so, replacing ref is fine.
        self.signals[name] = value_tensor

    def get_output(self, name):
        """Gets a primary output."""
        return self.signals[name]

    def step(self):
        """
        Simulates one clock cycle.
        1. Evaluate Combinational Logic (Gates)
        2. Update Sequential Logic (DFFs)
        """
        
        # 1. Combinational Logic
        # We might need multiple passes if not sorted? 
        # Let's assume sorted for now.
        for gate in self.sorted_gates:
            gtype = gate['type']
            ports = gate['ports'] # List of signal names
            
            # Convention: Output is always first port for primitives
            # and/or/xor/not (out, in1, in2...)
            out_name = ports[0]
            in_names = ports[1:]
            
            # Get Inputs
            inputs = [self.signals[n] for n in in_names]
            
            # Compute
            if gtype == 'and':
                res = inputs[0]
                for i in range(1, len(inputs)):
                    res = res & inputs[i]
            elif gtype == 'or':
                res = inputs[0]
                for i in range(1, len(inputs)):
                    res = res | inputs[i]
            elif gtype == 'xor':
                res = inputs[0]
                for i in range(1, len(inputs)):
                    res = res ^ inputs[i]
            elif gtype == 'not':
                res = ~inputs[0]
            elif gtype == 'nand':
                res = inputs[0]
                for i in range(1, len(inputs)):
                    res = res & inputs[i]
                res = ~res
            elif gtype == 'nor':
                res = inputs[0]
                for i in range(1, len(inputs)):
                    res = res | inputs[i]
                res = ~res
            elif gtype == 'xnor':
                res = inputs[0]
                for i in range(1, len(inputs)):
                    res = res ^ inputs[i]
                res = ~res
            elif gtype == 'buf':
                res = inputs[0]
            else:
                continue # Unknown
                
            # Update Output
            self.signals[out_name] = res

        # 2. Sequential Logic (DFFs)
        # dff name (q, d, clk, rst)
        # We assume implicit clocking via step(), so we ignore clk port.
        # We handle Q update.
        
        # We need to calculate next state for ALL DFFs before updating ANY Qs
        # to simulate simultaneous clock edge.
        
        dff_updates = []
        
        for dff in self.dffs:
            ports = dff['ports']
            # (q, d, clk, rst)
            q_name = ports[0]
            d_name = ports[1]
            # clk = ports[2] # Ignored
            rst_name = ports[3] if len(ports) > 3 else None
            
            d_sig = self.signals[d_name]
            rst_sig = self.signals[rst_name] if rst_name else None
            
            # We need a DFlipFlop module instance to handle the logic?
            # Or just use the backend directly?
            # Let's use a temporary DFlipFlop module for logic reuse
            # OR just call backend.dff_update directly if we had access.
            # But we want to use the DFlipFlop class logic (X-prop etc).
            
            # Actually, we can just compute the next Q and store it.
            # But DFlipFlop class holds state.
            # Let's create a shadow DFF for logic.
            
            # Optimization: We don't want to create DFlipFlop objects every cycle.
            # We should have created them in __init__.
            pass

        # Revisit __init__ to create DFF objects?
        # Or just implement DFF logic here?
        # Let's implement DFF logic here using the backend directly or reusing DFlipFlop class.
        # To keep it simple:
        
        for dff in self.dffs:
            ports = dff['ports']
            q_name = ports[0]
            d_name = ports[1]
            rst_name = ports[3] if len(ports) > 3 else None
            
            d_val = self.signals[d_name]
            rst_val = self.signals[rst_name] if rst_name else None
            
            # Create a temp DFF to calculate next state? No, that updates in place.
            # We need Q_next.
            
            # Let's manually call the update logic.
            # Q_next = D (with Reset logic)
            
            # We need a place to store Q_next.
            # Let's just calculate it.
            
            # Using the DFlipFlop logic from modules.py:
            # It updates in-place.
            # So we must calculate ALL next states first, then apply.
            
            # 1. Calc Next
            # We can use a temp tensor.
            
            # Logic:
            # If Rst=1 -> 0
            # If Rst=X -> X
            # Else -> D
            
            if rst_val is not None:
                # Rst Active (1)
                rst_active = (rst_val.val == 1) & (rst_val.strength == 1)
                # Rst Unknown (X)
                rst_unknown = (rst_val.strength == 0)
                
                # Base is D
                next_v = d_val.val.copy()
                next_s = d_val.strength.copy()
                
                # Apply Reset
                # If Active -> 0 (V=0, S=1)
                # If Unknown -> X (V=0, S=0)
                
                # We need to be careful with numpy ops on device arrays if backend is CUDA.
                # LogicTensor abstraction hides this.
                # We should use LogicTensor ops!
                
                # But LogicTensor ops create new tensors.
                # That's fine.
                
                # Q_next = (D & ~Rst) | (0 & Rst) ... wait, standard logic ops?
                # No, Reset priority logic is specific.
                
                # Let's use a helper from modules? 
                # modules.DFlipFlop.step updates in place.
                
                # Let's just use the backend's dff_update if possible, 
                # but that updates in place too?
                # backend.dff_update(q_next, d, rst, n)
                # It writes to q_next. So we can pass a temp tensor!
                
                q_next = cv.zeros(self.batch_size)
                q_next.backend.dff_update(q_next._buffers(), d_val._buffers(), rst_val._buffers(), self.batch_size)
                dff_updates.append((q_name, q_next))
                
            else:
                # No reset, just D
                dff_updates.append((q_name, d_val))

        # 3. Apply Updates
        for q_name, q_next in dff_updates:
            self.signals[q_name] = q_next


class VerilogCompiler:
    """
    Regex-based structural Verilog parser.
    """
    def __init__(self):
        self.source = ""
        self.pos = 0
        
    def compile(self, source_code, batch_size=1):
        self.source = source_code
        self.pos = 0
        
        # Remove comments
        self._remove_comments()
        
        # Parse Module
        # module name ( ... );
        m_def = re.search(r'module\s+(\w+)\s*\(([^)]*)\)\s*;', self.source)
        if not m_def:
            raise ValueError("No module definition found")
        
        mod_name = m_def.group(1)
        # Ports list is in group 2, but we rely on input/output decls
        
        self.inputs = []
        self.outputs = []
        self.wires = []
        self.instances = []
        
        # Parse Body
        body_start = m_def.end()
        body = self.source[body_start:]
        
        # Split by semicolons
        statements = body.split(';')
        
        # Parse statements (Simplified)
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt: continue
            
            if stmt.startswith('input'):
                self.inputs.extend(self._parse_list(stmt[5:]))
            elif stmt.startswith('output'):
                self.outputs.extend(self._parse_list(stmt[6:]))
            elif stmt.startswith('wire'):
                self.wires.extend(self._parse_list(stmt[4:]))
            else:
                # Instance: type name (ports);
                # Regex: (\w+)\s+(\w+)\s*\((.*)\)
                match = re.search(r'(\w+)\s+(\w+)?\s*\((.*)\)', stmt)
                if match:
                    gtype = match.group(1)
                    name = match.group(2) or ""
                    ports_str = match.group(3)
                    ports = self._parse_list(ports_str)
                    self.instances.append({
                        'type': gtype,
                        'name': name,
                        'ports': ports
                    })

    def _parse_list(self, text):
        # "a, b, c" -> ['a', 'b', 'c']
        return [x.strip() for x in text.split(',') if x.strip()]
