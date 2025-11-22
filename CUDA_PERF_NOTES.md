# CUDA Kernel Performance Notes

## Known Issues - Warp Divergence

The 4-state logic kernels (`k_and_4state`, `k_or_4state`, `k_not_4state`) contain conditional branches that cause **warp divergence**:

```python
if a_is_zero or b_is_zero:
    # Path 1: controlling value
elif (a_s[idx] == 1) and (b_s[idx] == 1):
    # Path 2: normal operation
else:
    # Path 3: X propagation
```

### Impact
- **Correctness**: ✅ Fixed - now matches IEEE 1164 semantics
- **Performance**: ⚠️ 2-3x slower than optimal due to thread divergence
  - In a warp of 32 threads (chip instances), threads execute all branches serially
  - Effective throughput: ~33-50% of peak

### Why We Accept This
1. **Correctness first**: The previous naive bitwise implementation was fundamentally broken
2. **Encoding limitation**: The (V, S) dual-array encoding prevents branchless implementations
3. **Alternative encodings** (e.g., 2-bit packed states) would allow branchless logic but require major refactoring

### Future Optimization Path
Consider switching to a packed 2-bit encoding:
```
State  |  Bits
0      |  00
1      |  11
X      |  01
Z      |  10
```

This would allow branchless magic bit manipulation:
```python
out = (a & b) | ((a | b) & 0xAAAAAAAA)  # No branches!
```

But requires rewriting all kernels and breaking the abstraction.

## Memory Bandwidth Issues

Current implementation uses separate V and S arrays:
- **6 memory transactions per warp** (load a.v, a.s, b.v, b.s, store out.v, out.s)
- **Potential**: Interleave V and S in memory → 3 transactions (50% reduction)

## Recommendations
1. **Keep current implementation** for correctness
2. **Profile actual workloads** to measure divergence impact
3. **Consider packed encoding** only if warp divergence proves to be bottleneck (>50% of runtime)
4. **Optimize memory layout** (interleaved V/S) first before touching logic

---
*Last Updated: 2025-11-21*
