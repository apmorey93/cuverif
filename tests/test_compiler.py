import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    from cuverif.compiler import NetlistCompiler
except ImportError:
    print("Could not import NetlistCompiler. Is pyverilog installed?")
    sys.exit(1)

def test_compile():
    print("=" * 70)
    print("VERILOG TO CUVERIF COMPILER TEST")
    print("=" * 70)
    
    # 1. Initialize Compiler
    compiler = NetlistCompiler()
    
    # 2. Parse the dummy Verilog
    verilog_file = os.path.join(os.path.dirname(__file__), "simple_cpu.v")
    if not os.path.exists(verilog_file):
        print(f"Error: {verilog_file} not found!")
        return False
        
    print(f"Parsing {verilog_file}...")
    compiler.parse_file(verilog_file)
    
    # 3. Generate Code
    print("Generating Python code...")
    python_code = compiler.generate_python(class_name="SimpleCPU")
    
    print("\n--- Generated Python Code ---\n")
    print(python_code)
    print("\n-----------------------------\n")
    
    # 4. Save it to a file so we can actually import it
    output_file = os.path.join(os.path.dirname(__file__), "generated_model.py")
    with open(output_file, "w") as f:
        f.write(python_code)
        
    print(f"[SUCCESS] Generated '{output_file}'")
    print("You can now import this model and run simulations on GPU!")
    return True

if __name__ == "__main__":
    test_compile()
