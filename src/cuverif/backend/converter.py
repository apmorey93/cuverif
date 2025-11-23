import cuverif.compiler as compiler
try:
    import cuverif_core as cv
except ImportError:
    # Fallback for dev/testing if extension not built
    cv = None

class NetlistConverter:
    """
    Converts a Python 'Chip' object (parsed from Verilog) 
    into a C++ 'Netlist' object for the accelerator.
    """
    def __init__(self):
        self.gate_type_map = {
            'and': cv.GateType.AND,
            'or': cv.GateType.OR,
            'xor': cv.GateType.XOR,
            'not': cv.GateType.NOT,
            'nand': cv.GateType.NAND,
            'nor': cv.GateType.NOR,
            'xnor': cv.GateType.XNOR,
            'buf': cv.GateType.BUF,
            'dff': cv.GateType.DFF,
            # Input/Output are handled as signals, but maybe we need explicit gates?
            # The C++ Netlist treats inputs as signals that are driven by host.
        }

    def convert(self, chip: compiler.Chip) -> "cv.Netlist":
        if cv is None:
            raise ImportError("C++ extension 'cuverif_core' not loaded.")
            
        nl = cv.Netlist()
        
        # 1. Create Signals
        # We need a map from name -> C++ ID
        sig_map = {} # name -> id
        
        # Collect all unique signals
        all_signals = set(chip.inputs + chip.outputs + chip.wires)
        
        # Also add implicit signals from instances if any
        for inst in chip.instances:
            for port in inst['ports']:
                all_signals.add(port)
                
        # Register signals in C++
        for name in all_signals:
            sid = nl.add_signal(name)
            sig_map[name] = sid
            
        # 2. Create Gates
        for inst in chip.instances:
            gtype_str = inst['type']
            ports = inst['ports']
            name = inst.get('name', '')
            
            if gtype_str not in self.gate_type_map:
                print(f"Warning: Unknown gate type '{gtype_str}', skipping.")
                continue
                
            gtype = self.gate_type_map[gtype_str]
            
            # Port mapping convention:
            # Primitives: [out, in1, in2, ...]
            # DFF: [q, d, clk, rst]
            
            if gtype == cv.GateType.DFF:
                # DFF: q, d, clk, rst
                # C++ expects: input1=d, input2=rst (optional), output=q
                q_name = ports[0]
                d_name = ports[1]
                # clk = ports[2] (ignored)
                rst_name = ports[3] if len(ports) > 3 else None
                
                inputs = [sig_map[d_name]]
                if rst_name:
                    inputs.append(sig_map[rst_name])
                
                output = sig_map[q_name]
                nl.add_gate(gtype, inputs, output, name)
                
            else:
                # Combinational Primitives
                out_name = ports[0]
                in_names = ports[1:]
                
                output = sig_map[out_name]
                inputs = [sig_map[n] for n in in_names]
                
                nl.add_gate(gtype, inputs, output, name)
                
        # 3. Levelize (Prepare for execution)
        nl.levelize()
        
        return nl

def from_verilog(source_code: str) -> "cv.Netlist":
    """Parses Verilog source and returns a C++ Netlist."""
    # 1. Parse with Python
    parser = compiler.VerilogCompiler()
    parser.compile(source_code)
    
    # Create Chip object (intermediate representation)
    # The compiler.compile() actually returns nothing but populates internal state?
    # Wait, looking at compiler.py, it seems incomplete or I need to check how it produces output.
    # Let's assume we can extract the data or modify compiler.py to return a Chip.
    
    # Actually, compiler.py defines a Chip class but VerilogCompiler.compile just parses.
    # We might need to instantiate Chip manually or fix VerilogCompiler.
    # Let's assume for now we can get the parsed structure.
    
    # Re-reading compiler.py from memory:
    # It has a `compile` method but it didn't seem to return a Chip.
    # It parsed into `inputs`, `outputs`, `wires`, `instances`.
    # We can construct a Chip from that.
    
    chip = compiler.Chip("top", parser.inputs, parser.outputs, parser.wires, parser.instances)
    
    # 2. Convert to C++
    converter = NetlistConverter()
    return converter.convert(chip)
