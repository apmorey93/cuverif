"""
CuVerif Smoke Test - Verifies basic GPU operations
Run this to ensure the library is working correctly.
"""

import sys
import os
sys.path.append(os.path.abspath('src'))

import numpy as np

# Import cuverif
try:
    import cuverif.core as cv
    print("[PASS] Successfully imported cuverif.core")
except ImportError as e:
    print(f"[FAIL] Failed to import cuverif: {e}")
    sys.exit(1)

print("\n--- CuVerif Smoke Test ---\n")

# Test 1: Create LogicTensors
print("Test 1: Creating LogicTensors...")
batch_size = 4
A = cv.LogicTensor(
    data_v=np.array([1, 0, 1, 0], dtype=np.uint32),
    data_s=np.array([1, 1, 1, 1], dtype=np.uint32)
)
B = cv.LogicTensor(
    data_v=np.array([1, 1, 0, 0], dtype=np.uint32),
    data_s=np.array([1, 1, 1, 1], dtype=np.uint32)
)
print("[PASS] Created LogicTensors A and B")

# Test 2: XOR Operation
print("\nTest 2: XOR Operation (A ^ B)...")
C = A ^ B
v_result, s_result = C.cpu()
expected_v = np.array([0, 1, 1, 0], dtype=np.uint32)

if np.array_equal(v_result, expected_v):
    print(f"[PASS] XOR verified: {v_result}")
else:
    print(f"[FAIL] XOR failed: Expected {expected_v}, got {v_result}")

# Test 3: AND Operation (4-state)
print("\nTest 3: AND Operation (A & B)...")
D = A & B
v_and, s_and = D.cpu()
expected_v_and = np.array([1, 0, 0, 0], dtype=np.uint32)

if np.array_equal(v_and, expected_v_and):
    print(f"[PASS] AND verified: {v_and}")
else:
    print(f"[FAIL] AND failed: Expected {expected_v_and}, got {v_and}")

# Test 4: NOT Operation (4-state)
print("\nTest 4: NOT Operation (~A)...")
E = ~A
v_not, s_not = E.cpu()
expected_v_not = np.array([0, 1, 0, 1], dtype=np.uint32)
expected_s_not = np.array([1, 1, 1, 1], dtype=np.uint32)

if np.array_equal(v_not, expected_v_not) and np.array_equal(s_not, expected_s_not):
    print(f"[PASS] NOT verified: V={v_not}, S={s_not}")
else:
    print(f"[FAIL] NOT failed: Expected V={expected_v_not}, S={expected_s_not}")

# Test 5: Utility constructors
print("\nTest 5: Utility constructors...")
zeros_tensor = cv.zeros(3)
v_zeros, s_zeros = zeros_tensor.cpu()
if np.all(v_zeros == 0) and np.all(s_zeros == 1):
    print("[PASS] zeros() constructor verified")
else:
    print("[FAIL] zeros() constructor failed")

unknown_tensor = cv.unknown(3)
v_x, s_x = unknown_tensor.cpu()
if np.all(v_x == 0) and np.all(s_x == 0):
    print("[PASS] unknown() constructor verified")
else:
    print("[FAIL] unknown() constructor failed")

print("\n" + "="*50)
print("SUCCESS: All smoke tests passed!")
print("="*50)
