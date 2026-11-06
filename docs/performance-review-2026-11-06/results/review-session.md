# Historical measurements from the review session

These are retained values from the chat/tool results, **not newly generated raw logs**. The first broad probe's original output was truncated in the conversation; its full text could not be recovered. Numeric values retained in the review context are preserved below without inventing missing profile rows. Fresh complete logs are separately stored in `verification/`.

## Environment reported before benchmarking

```text
3.12.14 (main, Sep 29 2026, 15:01:18) [Clang 22.1.3 ]
mujoco 3.3.7 numpy 2.5.4 PySide6 6.11.3
```

Original commands ran from `/home/equinox/git/private/ingetrazo-newton`:

```bash
.venv/bin/python /tmp/opencode/newton_perf_review.py
.venv/bin/python /tmp/opencode/newton_perf_followup.py
.venv/bin/python /tmp/opencode/newton_perf_ui_followup.py
```

## Broad probe: retained numeric record

Worker median ms per eight-step / 33.3 ms batch (five repeats):

| Bodies | DOFs | Baseline | Linear damping | All attracting |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 60 | 0.039 | 0.653 | 2.955 |
| 50 | 300 | 0.120 | 3.489 | 85.538 |
| 100 | 600 | 0.202 | 7.808 | 371.809 |

Retained profile facts: 100 attracting bodies made 79,200 Jacobian calls and 79,200 `numpy.zeros` allocations in eight steps; about 399 of 400 profiled ms were in `apply_attraction`. Linear damping on 100 bodies made 800 `mj_jacBodyCom` calls and 1,600 `zeros` calls; allocations alone were a small portion.

Constant telemetry inputs, median ms including Qt event processing (20 repeats):

| Labels | Original | Duplicate styles suppressed |
| ---: | ---: | ---: |
| 10 | 0.261 | 0.024 |
| 50 | 1.202 | 0.103 |
| 100 | 2.515 | 0.209 |

Synthetic simple-box drawing, no faces, simplified projection (seven repeats):

| Colliders/groups | Median ms |
| ---: | ---: |
| 100 | 2.321 |
| 500 | 14.023 |
| 1,000 | 31.635 |

Retained 1,000-collider profile fact: about 10 ms in the group-lookup generator out of about 44 ms total profiled time.

## First follow-up run, before adding the vectorized variant

The following stdout was retained in the conversation:

```text
ATTRACTION: per-pair vs per-target Jacobian (same force math)
{'n': 50, 'original_ms': 84.243, 'per_target_ms': 43.264, 'force_max_abs_error': 0.0}
{'n': 100, 'original_ms': 359.35, 'per_target_ms': 175.621, 'force_max_abs_error': 0.0}
WORKER PROTOCOL INITIALIZATION: unused vertices on analytic boxes
{'vertices': 1000, 'payload_bytes': 17212, 'encode_ms': 0.303, 'decode_ms': 0.164}
{'vertices': 100000, 'payload_bytes': 1700212, 'encode_ms': 31.266, 'decode_ms': 22.054}
{'vertices': 250000, 'payload_bytes': 4250212, 'encode_ms': 81.03, 'decode_ms': 55.941}
STOP: exact CollisionView.stop with a non-responding fake worker (500ms kill/reap latency)
{'blocked_ui_ms': 500.084}
```

## Follow-up after adding the vectorized variant

```text
ATTRACTION: per-pair vs per-target Jacobian (same force math)
{'n': 50, 'original_ms': 84.543, 'per_target_ms': 44.071, 'force_max_abs_error': 0.0}
{'n': 50, 'vectorized_ms': 5.647, 'force_check': 'passed'}
{'n': 100, 'original_ms': 359.652, 'per_target_ms': 176.012, 'force_max_abs_error': 0.0}
{'n': 100, 'vectorized_ms': 13.054, 'force_check': 'passed'}
WORKER PROTOCOL INITIALIZATION: unused vertices on analytic boxes
{'vertices': 1000, 'payload_bytes': 17212, 'encode_ms': 0.293, 'decode_ms': 0.153}
{'vertices': 100000, 'payload_bytes': 1700212, 'encode_ms': 31.097, 'decode_ms': 20.521}
{'vertices': 250000, 'payload_bytes': 4250212, 'encode_ms': 78.251, 'decode_ms': 54.234}
STOP: exact CollisionView.stop with a non-responding fake worker (500ms kill/reap latency)
{'blocked_ui_ms': 500.085}
```

## UI follow-up

Combined stdout/stderr as displayed in the conversation (the original stream interleaving is not a timing record):

```text
This plugin does not support propagateSizeHints()
This plugin does not support propagateSizeHints()
{'probe': 'changing telemetry', 'n': 10, 'cached': False, 'ms': 0.615}
This plugin does not support propagateSizeHints()
This plugin does not support propagateSizeHints()
{'probe': 'changing telemetry', 'n': 10, 'cached': True, 'ms': 0.341}
This plugin does not support propagateSizeHints()
This plugin does not support propagateSizeHints()
{'probe': 'changing telemetry', 'n': 50, 'cached': False, 'ms': 1.224}
This plugin does not support propagateSizeHints()
This plugin does not support propagateSizeHints()
{'probe': 'changing telemetry', 'n': 50, 'cached': True, 'ms': 0.599}
This plugin does not support propagateSizeHints()
This plugin does not support propagateSizeHints()
{'probe': 'changing telemetry', 'n': 100, 'cached': False, 'ms': 2.526}
This plugin does not support propagateSizeHints()
This plugin does not support propagateSizeHints()
{'probe': 'changing telemetry', 'n': 100, 'cached': True, 'ms': 1.29}
{'probe': 'collider draw', 'n': 100, 'variant': 'original', 'ms': 3.047}
{'probe': 'collider draw', 'n': 100, 'variant': 'indexed', 'ms': 2.108}
{'probe': 'collider draw', 'n': 500, 'variant': 'original', 'ms': 13.295}
{'probe': 'collider draw', 'n': 500, 'variant': 'indexed', 'ms': 10.442}
{'probe': 'collider draw', 'n': 1000, 'variant': 'original', 'ms': 30.755}
{'probe': 'collider draw', 'n': 1000, 'variant': 'indexed', 'ms': 20.987}
```
