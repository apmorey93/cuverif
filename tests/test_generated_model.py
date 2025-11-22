import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    import cuverif.core as cv
    import cuverif.modules as modules
    print("Using Real GPU CuVerif Library")
except ImportError:
    print("GPU Library not found. Using CPU Mock for Model verification.")
    import tests.mock_cuverif as cv
    import tests.mock_cuverif as modules
    
    # MONKEY PATCH: Redirect 'cuverif.core' and 'cuverif.modules' to our mock
    # This allows the generated code (which does 'import cuverif.core') to work
    sys.modules['cuverif'] = type(sys)('cuverif')
    sys.modules['cuverif.core'] = cv
    sys.modules['cuverif.modules'] = modules

# Import the generated model
try:
    from tests.generated_model import SimpleCPU
    print("[SUCCESS] Successfully imported generated model 'SimpleCPU'")
except ImportError as e:
    print(f"[FAIL] Could not import generated model: {e}")
    sys.exit(1)
except SyntaxError as e:
    print(f"[FAIL] Syntax Error in generated model: {e}")
    sys.exit(1)

def test_instantiation():
    print("Attempting to instantiate SimpleCPU...")
    try:
        BATCH = 5
        cpu = SimpleCPU(BATCH)
        print(f"[SUCCESS] Instantiated SimpleCPU with batch size {BATCH}")
        
        # Check if internal state exists
        if hasattr(cpu, 'w_dff_out'):
            print("[PASS] Internal DFF found")
        else:
            print("[FAIL] Internal DFF missing")
            
    except Exception as e:
        print(f"[FAIL] Instantiation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_instantiation()
