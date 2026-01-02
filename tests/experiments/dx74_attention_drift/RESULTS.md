# DX-74 Experiment Results

**Date:** 2026-01-02
**Model:** Claude Opus 4.5

## Results Summary

| Strategy | Issues Found | Detection Rate | Tokens (est) |
|----------|-------------|----------------|--------------|
| A: Baseline | 53 | 106% | ~10k |
| B: Enumerate-first | 52 | 104% | ~15k |
| C: Multi-subagent (R1) | 50 | 100% | ~10k |
| C: Multi-subagent (R2) | 50 | 100% | ~10k |
| D: Combined | 53 | 106% | ~18k |

All strategies achieved ~100% detection rate.

## Analysis

### Why All Strategies Performed Similarly

1. **File size too small**: Each file ~100 lines, insufficient for attention drift
2. **Bug density too high**: 50 bugs / 600 lines = 1 bug per 12 lines
3. **Obvious markers**: `# BUG-XX:` comments made bugs easy to find
4. **Model capability**: Opus 4.5 is highly capable, reducing strategy differences

### Attention Drift Not Observed

The hypothesis was that single-pass review would miss bugs due to attention drift.
This was NOT observed because:
- Linear attention in short files is sufficient
- High bug density means almost every function flagged
- Explicit bug markers act as attention anchors

## Experiment Design Improvements Needed

### For Valid Comparison

1. **Larger files**: 500+ lines each (10x current)
2. **Lower bug density**: 1 bug per 50-100 lines (5-8x lower)
3. **Hidden bugs**: No `# BUG-XX` markers
4. **Noise injection**: Add legitimate complex code as distraction
5. **Subtle bugs**: Logic errors, not obvious patterns

### Proposed Improved Scenario

```
Scenario v2:
- 6 files × 500 lines = 3000 lines
- 30 bugs total = 1 bug per 100 lines
- Bugs embedded in normal code
- No comments marking bugs
- Mix of obvious and subtle issues
```

## Conclusions

### Experiment Validity: LOW

The current test scenario does NOT adequately test attention drift because:
- Scope too small
- Density too high
- Markers too obvious

### DX-74 Hypothesis: UNVALIDATED

Cannot confirm or deny the effectiveness of enumerate-first technique
based on this experiment. Need redesigned scenario.

### Recommendations

1. **Create v2 scenario** with improved design
2. **Use haiku model** to amplify strategy differences
3. **Remove bug markers** to test true detection
4. **Add control group** with intentionally missed bugs
