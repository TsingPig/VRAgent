# VRAgent Final Analysis Report

## Overview
- Generated at: 2026-03-25 19:50:26
- Test plan: D:/--UnityProject/HenryLabXR/VRAgent/VRAgent/Assets/SampleScene/HomeScene/TestPlans/HomeScene_mixed_validation_test_plan.json
- Duration: 00:00:12.0013479
- Verdict: High Rejection Risk

## Action Legality Summary
| Metric | Value |
| --- | ---: |
| Total Actions | 10 |
| Legal Actions | 4 |
| Syntax Rejected | 1 |
| Semantic Rejected | 5 |
| Skipped Total | 6 |
| Legal Action Rate | 40.00% |

## Declared vs Legal by Type
| Action Type | Declared | Legal |
| --- | ---: | ---: |
| Grab | 1 | 0 |
| Trigger | 5 | 3 |
| Transform | 0 | 0 |
| Move | 3 | 1 |
| Unknown Type | 1 | 0 |

## Runtime Execution Summary
| Metric | Value |
| --- | ---: |
| Attempted Runtime Actions | 7 |
| Runtime Success | 7 |
| Runtime Exceptions | 0 |
| Runtime Success Rate | 100.00% |

## Interpretation
- Syntax rejections usually indicate malformed JSON fields, unsupported type names, or type-body mismatch.
- Semantic rejections usually indicate unresolved object/script FileID or missing action destination.
- Runtime exceptions indicate execution-time failures after action legality checks passed.
