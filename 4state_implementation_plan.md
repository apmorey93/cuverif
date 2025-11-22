# 4-State Logic Implementation Plan

## Overview
This document outlines the complete refactoring plan to support **4-state logic (0, 1, X, Z)** in CuVerif using the V/S (Value/Strong) encoding scheme.

## Encoding Scheme: V/S Bits

| State | Value (V) | Strong (S) | Description |
|-------|-----------|------------|-------------|
| **0** | 0 | 1 | Logic low |
| **1** | 1 | 1 | Logic high |
| **X** | 0 | 0 | Unknown/Don't care |
| **Z** | 1 | 0 | High impedance |

## Implementation Roadmap

### ✅ Step 1: CUDA Kernels (backend.py)
**Status:** Complete

Implemented 4-state kernels:
- `k_and_4state(a_v, a_s, b_v, b_s, out_v, out_s, n)`
- `k_or_4state(a_v, a_s, b_v, b_s, out_v, out_s, n)`
- `k_not_4state(a_v, a_s, out_v, out_s, n)`

**Logic Rules:**
- **AND**: `V_out = V_a & V_b`, `S_out = S_a & S_b`
- **OR**: `V_out = V_a | V_b`, `S_out = S_a & S_b`
- **NOT**: `V_out = ~V_a`, `S_out = S_a` (unchanged)

---

### ✅ Step 2: LogicTensor Refactor (core.py)
**Status:** Complete

**Changes:**
- Replaced single `data` array with dual arrays: `v_data`, `s_data`
- Updated `__init__()` to accept V/S pairs or shape
- Modified `cpu()` to return `(v_array, s_array)` tuple

**New Constructors:**
- `zeros(size)` → State 0 (V=0, S=1)
- `unknown(size)` → State X (V=0, S=0)
- `randint(low, high, size)` → Random 0/1 states

---

### ✅ Step 3: Operator Overloads (core.py)
**Status:** Complete

Updated operators to call 4-state kernels:
- `__and__()` → `k_and_4state`
- `__or__()` → `k_or_4state`
- `__invert__()` → `k_not_4state`
- `__xor__()` → Partial (uses legacy kernel for V, needs dedicated 4-state kernel)

---

### ⏳ Step 4: XOR 4-State Kernel
**Status:** Pending

**TODO:** Implement `k_xor_4state` with proper X/Z propagation

```python
@cuda.jit
def k_xor_4state(a_v, a_s, b_v, b_s, out_v, out_s, n):
    idx = cuda.grid(1)
    if idx < n:
        # If either input is X or Z, output is X
        if a_s[idx] == 0 or b_s[idx] == 0:
            out_v[idx] = 0
            out_s[idx] = 0  # X state
        else:
            out_v[idx] = a_v[idx] ^ b_v[idx]
            out_s[idx] = 1
```

---

### ⏳ Step 5: DFlipFlop 4-State Support
**Status:** Critical - In Progress

**Current Issue:** `DFlipFlop.step()` uses legacy `k_dff_update` which only operates on V data.

**Required Changes:**

#### A. New Kernel (backend.py)
```python
@cuda.jit
def k_dff_update_4state(d_v, d_s, q_v, q_s, reset_v, reset_s, n):
    idx = cuda.grid(1)
    if idx < n:
        # If reset is active (V=1, S=1)
        if reset_v[idx] == 1 and reset_s[idx] == 1:
            q_v[idx] = 0
            q_s[idx] = 1  # Reset to '0' state
        # If reset is X or Z, output is X
        elif reset_s[idx] == 0:
            q_v[idx] = 0
            q_s[idx] = 0  # Unknown state
        else:
            # Normal update: Q = D
            q_v[idx] = d_v[idx]
            q_s[idx] = d_s[idx]
```

#### B. Update DFlipFlop.step() (modules.py)
```python
def step(self, d, reset=None):
    if reset is None: 
        reset = core.zeros(self.batch_size)
    
    K.k_dff_update_4state[K.get_grid_size(self.batch_size), K.THREADS_PER_BLOCK](
        d.v_data, d.s_data, 
        self.q.v_data, self.q.s_data,
        reset.v_data, reset.s_data,
        self.batch_size
    )
    
    return self.q
```

---

### ⏳ Step 6: Comparison Operators
**Status:** Pending

**TODO:** Implement `__eq__()` for 4-state equality

```python
def __eq__(self, other):
    """Returns LogicTensor with 1 where equal, 0 otherwise, X if either is X/Z"""
    # Requires k_eq_4state kernel
    pass
```

**4-State Equality Rules:**
- `0 == 0` → 1
- `1 == 1` → 1
- `X == anything` → X
- `Z == anything` → X
- `0 == 1` → 0

---

### ⏳ Step 7: Monitor Enhancement
**Status:** Pending

**TODO:** Update `Monitor.plot()` to display 4 distinct levels

```python
def plot(self):
    # Map (V, S) to display values:
    # (0, 1) → 0.0
    # (1, 1) → 1.0
    # (0, 0) → 0.5 (X - middle line)
    # (1, 0) → 0.75 (Z - high-Z line)
    
    for v_hist, s_hist in self.history.values():
        display = []
        for v, s in zip(v_hist, s_hist):
            if s == 1:
                display.append(float(v))  # 0 or 1
            elif v == 0:
                display.append(0.5)  # X
            else:
                display.append(0.75)  # Z
        # Plot with custom yticks [0, 0.5, 0.75, 1] labeled ['0', 'X', 'Z', '1']
```

---

## Verification Tests

### Test 1: 4-State AND
```python
A = [1, 0, X]  # V=[1,0,0], S=[1,1,0]
B = [1, X, Z]  # V=[1,0,1], S=[1,0,0]
C = A & B      # Expected: [1, X, X] → V=[1,0,0], S=[1,0,0]
```

### Test 2: 4-State NOT
```python
A = [1, 0, X]  # V=[1,0,0], S=[1,1,0]
B = ~A         # Expected: [0, 1, X] → V=[0,1,1], S=[1,1,0]
```

### Test 3: DFF with X Input
```python
dff = DFlipFlop(batch_size=2)
D = unknown(2)  # X state
Q = dff.step(D)
# Q should be X (V=0, S=0)
```

---

## Next Steps for You (Senior Engineer)

1. **Implement `k_xor_4state`** in `backend.py`
2. **Implement `k_dff_update_4state`** in `backend.py`
3. **Update `DFlipFlop.step()`** in `modules.py`
4. **Add verification tests** for:
   - XOR with X/Z inputs
   - DFF with X/Z inputs
   - Reset behavior with X state
5. **Enhance `Monitor.plot()`** for multi-level display

---

## Design Decisions

### Why V/S Encoding?
- **Performance**: Single bitwise operations on GPU
- **Compatibility**: Easy to extend to multi-bit signals (uint32 arrays)
- **Simplicity**: Only 2 arrays needed vs. 4-value enums

### Alternative: 2-Bit State Encoding
Could use `(state >> 1) & 1` for S and `state & 1` for V, but separate arrays provide:
- Better CUDA memory coalescing
- Cleaner kernel code
- Easier debugging

---

## Questions to Resolve

1. **XOR with X/Z**: Should `X ^ 1` always be `X`, or should we use a truth table?
2. **Reset Priority**: If `reset=X`, should DFF output be `X` or retain previous state?
3. **Wired-OR/Z Resolution**: Do we need multi-driver resolution logic?

---

## References
- SystemVerilog 4-state logic (IEEE 1800-2017)
- Verilog truth tables for X/Z propagation
- CUDA memory coalescing patterns
