import re

class NetlistCompiler:
    """
    The "Netlist Ingest" Engine.
    Parses Gate-Level Verilog using Regex (Dependency-Free) and transpiles it to CuVerif Python code.
    """
    def __init__(self):
        self.wires = set()
        self.inputs = []
        self.outputs = []
        self.logic = [] # List of (primitive_type, output_wire, input_wires)
        self.dffs = []  # List of (output_wire, input_d, clock, reset)

    def parse_file(self, filename):
        print(f"Parsing {filename} (Regex Mode)...")
        with open(filename, 'r') as f:
            content = f.read()

        # 1. Remove Comments
        content = re.sub(r'//.*', '', content)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # 2. Extract Ports (Inputs/Outputs)
        # Matches: input wire [0:0] name; or input name;
        # Simplified regex for MVP
        self.inputs = re.findall(r'input\s+(?:\[.*?\]\s+)?(\w+)', content)
        self.outputs = re.findall(r'output\s+(?:\[.*?\]\s+)?(\w+)', content)
        
        # 3. Extract Wires
        self.wires = set(re.findall(r'wire\s+(?:\[.*?\]\s+)?(\w+)', content))
        self.wires.update(self.inputs)
        self.wires.update(self.outputs)

        # 4. Extract Gates
        # Pattern: type name (port, port, ...);
        # We look for standard primitives
        primitives = ['and', 'or', 'xor', 'nand', 'nor', 'not', 'dff']
        
        # Regex to find module instantiations: type name ( args );
        # Note: This is a simplified parser. It assumes positional arguments for gates.
        # It handles newlines in arguments.
        pattern = r'(\w+)\s+(\w+)\s*\((.*?)\);'
        matches = re.findall(pattern, content, re.DOTALL)

        for prim_type, inst_name, args_str in matches:
            if prim_type not in primitives:
                continue
                
            # Clean up args
            args = [x.strip() for x in args_str.split(',')]
            
            if prim_type in ['and', 'or', 'xor', 'nand', 'nor']:
                # Standard logic: First port is output, rest are inputs
                out_wire = args[0]
                in_wires = args[1:]
                self.logic.append({
                    "type": prim_type,
                    "out": out_wire,
                    "ins": in_wires
                })
            
            elif prim_type == 'not':
                self.logic.append({
                    "type": "not",
                    "out": args[0],
                    "ins": [args[1]]
                })

            elif prim_type == 'dff':
                # Simplified DFF: dff(q, d, clk, rst)
                # Handle optional reset if 4th arg exists
                rst = args[3] if len(args) > 3 else None
                self.dffs.append({
                    "out": args[0],
                    "d": args[1],
                    "clk": args[2],
                    "rst": rst
                })

    def generate_python(self, class_name="TopModule"):
        """
        Emits the CuVerif code string.
        """
        lines = []
        lines.append("import cuverif.core as cv")
        lines.append("import cuverif.modules as modules")
        lines.append("")
        lines.append(f"class {class_name}:")
        lines.append(f"    def __init__(self, batch_size):")
        lines.append(f"        self.batch_size = batch_size")
        lines.append(f"        # Wires / State")
        
        # Declare DFFs first (State)
        for dff in self.dffs:
            lines.append(f"        self.{dff['out']} = modules.DFlipFlop(batch_size)")
            
        lines.append("")
        lines.append(f"    def step(self, inputs):")
        lines.append(f"        # inputs is a dict of LogicTensors")
        lines.append(f"        # Unpack Inputs")
        for inp in self.inputs:
            lines.append(f"        w_{inp} = inputs['{inp}']")
            
        lines.append(f"        # Unpack State (Current Q)")
        for dff in self.dffs:
            lines.append(f"        w_{dff['out']} = self.{dff['out']}.q")

        lines.append("")
        lines.append(f"        # Combinational Logic (Topologically Sorted)")
        # Note: In a real compiler, we would sort self.logic here.
        # For now, we assume the netlist is pre-sorted or simple.
        
        for gate in self.logic:
            inputs_str = [f"w_{x}" for x in gate['ins']]
            
            if gate['type'] == 'and':
                # chaining A & B & C ...
                op_str = " & ".join(inputs_str)
                lines.append(f"        w_{gate['out']} = {op_str}")
                
            elif gate['type'] == 'or':
                op_str = " | ".join(inputs_str)
                lines.append(f"        w_{gate['out']} = {op_str}")
            
            elif gate['type'] == 'xor':
                op_str = " ^ ".join(inputs_str)
                lines.append(f"        w_{gate['out']} = {op_str}")
                
            elif gate['type'] == 'not':
                lines.append(f"        w_{gate['out']} = ~{inputs_str[0]}")
                
            elif gate['type'] == 'nand':
                lines.append(f"        w_{gate['out']} = ~({' & '.join(inputs_str)})")

        lines.append("")
        lines.append(f"        # Update Sequential State")
        for dff in self.dffs:
            # step(d, reset)
            rst_str = f"w_{dff['rst']}" if dff['rst'] else "None"
            lines.append(f"        self.{dff['out']}.step(w_{dff['d']}, {rst_str})")
            
        lines.append("")
        lines.append(f"        # Return Outputs")
        out_dict = ", ".join([f"'{o}': w_{o}" for o in self.outputs])
        lines.append(f"        return {{{out_dict}}}")
        
        return "\n".join(lines)
