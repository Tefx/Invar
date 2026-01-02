# DX-74: Attention Drift Experiment

Controlled experiment to measure effectiveness of different review strategies.

## Scenario V1 (deprecated)

6 files with 50 planted bugs. **Too easy** - all strategies achieved ~100% detection.

See `RESULTS.md` for analysis of why v1 failed to differentiate strategies.

## Scenario V2 (current)

6 large files with 31 hidden bugs (no markers):

| File | Lines | Bugs | Primary Issues |
|------|-------|------|----------------|
| user_service.py | ~670 | 4 | Auth, exception handling |
| order_processor.py | ~700 | 7 | Exception handling |
| payment_gateway.py | ~550 | 6 | Hardcoded secrets, defaults |
| inventory_manager.py | ~680 | 4 | SQL injection, secrets |
| notification_service.py | ~570 | 6 | Hardcoded secrets, timing |
| analytics_engine.py | ~700 | 4 | SQL injection, secrets |

**Design improvements over v1:**
- 5x larger files (500+ lines vs ~100)
- 5x lower density (1 bug/100 lines vs 1 bug/12 lines)
- No `# BUG-XX` markers
- Realistic code with working logic
- Mix of obvious and subtle bugs

Ground truth: `scenario_v2/ground_truth.yaml` (DO NOT share with agents)

## Strategies to Test

| Strategy | Description |
|----------|-------------|
| A: Baseline | Single subagent, no structure |
| B: Agent-native | Single subagent + enumerate-first |
| C: Multi-subagent | Multiple rounds, no enumerate |
| D: Combined | Multiple rounds + enumerate-first |

## Test Protocol

### Strategy A: Baseline

```
Prompt: "Review these 6 files for security and code quality issues.
Report all issues found."

Measure:
- Bugs found / 50
- False positives
- Tokens used
```

### Strategy B: Agent-Native (Enumerate-First)

```
Prompt: "Review these 6 files. For each file:
1. FIRST: grep for each pattern type to enumerate ALL locations
2. Create explicit count for each pattern
3. Judge each location explicitly
4. Report: 'N/N reviewed, M issues found'"

Patterns to enumerate:
- "except Exception" / "except:"
- Hardcoded strings (quotes with keywords)
- os.path.join without validation
- f-string with user input

Measure:
- Bugs found / 50
- Count accuracy (enumerated vs actual)
- Tokens used
```

### Strategy C: Multi-Subagent

```
For round in 1..MAX_ROUNDS:
    Spawn fresh subagent with:
    "Review ALL 6 files. Find security and quality issues.
     Previous rounds may have missed issues - be thorough."

    If verdict == APPROVED: break
    Else: log issues, continue

Measure:
- Bugs found / 50 (per round and cumulative)
- Rounds to convergence
- Tokens used (total)
```

### Strategy D: Combined

```
For round in 1..MAX_ROUNDS:
    Spawn fresh subagent with:
    "Review ALL 6 files. For each file:
     1. Enumerate patterns with grep FIRST
     2. Judge each location explicitly
     3. Report counts

     Previous rounds may have misjudged - use fresh eyes."

    If verdict == APPROVED: break
    Else: log issues, continue

Measure:
- Bugs found / 50 (per round and cumulative)
- Enumeration accuracy
- Rounds to convergence
- Tokens used (total)
```

## Metrics

| Metric | Formula |
|--------|---------|
| Detection Rate | bugs_found / 31 |
| False Positive Rate | false_positives / total_reported |
| Enumeration Accuracy | correctly_enumerated / total_patterns |
| Cost Efficiency | detection_rate / tokens_used |

## Running the Experiment

Manual process (no automation yet):

1. Choose strategy prompt from `prompts.yaml`
2. Spawn fresh agent with prompt pointing to `scenario_v2/`
3. Record issues found
4. Compare to `ground_truth.yaml`
5. Calculate metrics

## Expected Outcomes (V2)

Based on DX-74 hypothesis with harder scenario:

| Strategy | Expected Detection | Expected Cost | Notes |
|----------|-------------------|---------------|-------|
| A: Baseline | 50-65% | ~15k tokens | Miss subtle bugs |
| B: Agent-native | 65-75% | ~20k tokens | Better pattern coverage |
| C: Multi-subagent | 70-80% | ~30k tokens | Fresh eyes catch more |
| D: Combined | 80-90% | ~35k tokens | Best coverage |

**Key bugs to watch:**
- SQL injection (2) - Moderate difficulty
- Timing attack (1) - High difficulty
- Insecure defaults (2) - High difficulty (looks correct)
- Bare except handlers (14) - Should all be found
