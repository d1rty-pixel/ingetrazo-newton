# Extension-only performance review

Date: 6 November 2026. Reviewed source revision: `2e0d838bcd6298c3a36289d84f198e4f7d3d2da7`.

## Outcome and priorities

The strongest measured bottleneck is attraction in `worker.py`: 100 mutually attracting bodies need about 360–372 ms for 33.3 ms of simulated time. GUI risks include collider painting, repeated preview initialization, synchronous process shutdown and unnecessary telemetry styling.

| ID | Priority | Trigger | Observed or estimated impact |
| --- | --- | --- | --- |
| F1 | P1 | Many active attraction sources | 100 bodies: 360–372 ms per 33.3 ms simulation; vectorized counterfactual about 13 ms |
| F2 | P1 for large scenes | Many displayed collision shapes | 1,000 simple colliders: about 31 ms per paint; UID index about 21 ms |
| F3 | P2 | Preview invalidation / detailed meshes with analytic colliders | 100k–250k unused vertices: about 31–78 ms GUI encoding alone |
| F4 | P2 | Stopping/replacing a worker | Synchronous wait up to the configured 1,000 ms timeout; real frequency unmeasured |
| F5 | P2 | Many standalone joint telemetry rows | 100 changing labels: about 2.53 → 1.29 ms when identical styles are suppressed |
| F6 | P2 | Many damped bodies or local gravity overrides | 100 bodies with linear damping: 0.20 → 7.81 ms per eight-step batch |
| F7 | P3 | Diagnosing latency | Existing metrics omit important serialization and paint phases |

P1 denotes a high-impact bottleneck under the stated trigger, not an unconditional release blocker. No application-wide FPS or mouse-to-display latency was measured. See [methodology and limits](README.md) and [historical measurements](results/review-session.md).

## F1 — Redundant per-pair Jacobians in attraction

**Location:** `newton/worker.py:664–676`, called inside `count * substeps` at `:595–640`.

`apply_attraction()` loops over sources × target bodies. Every pair allocates a dense `(3, nv)` Jacobian, calls `mj_jacBodyCom()` and transforms its force into generalized coordinates. The target Jacobian is independent of the source within a substep and can be reused.

| Bodies | Baseline, ms | Linear damping, ms | Every body attracts, ms |
| ---: | ---: | ---: | ---: |
| 10 | 0.039 | 0.653 | 2.955 |
| 50 | 0.120 | 3.489 | 85.538 |
| 100 | 0.202 | 7.808 | 371.809 |

Times are medians per eight-step batch, 33.3 ms simulated. At 100 attracting bodies, there are 79,200 Jacobian calls and allocations per batch. The pair count grows with sources × targets; dense Jacobian width also grows with degrees of freedom. The profile put approximately 399 of 400 ms in attraction.

**Impact:** About 0.09× real time in the 100-body case. New targets and drag updates must wait for the current batch because the session allows only one in-flight request. This cost is absent when attraction is disabled.

**Counterfactual:** Summing forces per target before applying its Jacobian reduced about 360 ms to 176 ms; vectorizing sources per target reduced it to 13.054 ms (roughly 27× faster). At 50 bodies the corresponding figures were 84.543, 44.071 and 5.647 ms. The scalar force difference was zero at the sampled state and the vectorized check passed at `rtol=atol=1e-12`. Sequential timings are not identical-state comparisons and do not prove long-term dynamical equivalence.

**Suggested minimal fix:** Sum forces per target, apply one Jacobian, then vectorize pair-force arithmetic. Preserve self-exclusion, softening and coincidence handling. Add physics regressions before shipping.

## F2 — Collider paint combines quadratic lookup with allocation-heavy drawing

**Location:** `newton/collision_view.py:106–132`, especially `:114`.

Each displayed collider scans `scene.groups` linearly by UID, giving O(colliders × groups) lookup work per paint. The path also creates matrices, `QVector3D` objects, transformed point lists, pens and individual drawing calls on the GUI thread.

| Colliders and groups | Original paint, ms | UID index including construction, ms |
| ---: | ---: | ---: |
| 100 | 3.047 | 2.108 |
| 500 | 13.295 | 10.442 |
| 1,000 | 30.755 | 20.987 |

The synthetic shape has eight points and twelve edges, no faces, and simplified projection. A separate 1,000-collider profile attributed about 10 ms of a 44 ms profiled paint to the group-lookup generator.

**Impact:** At 500 colliders this path alone used about 80% of a 16.7 ms frame budget; at 1,000 it exceeded the budget. GUI painting also delays input callbacks and timers. This applies only when collision shapes are displayed. Real costs depend on shape complexity, visibility and viewport behavior.

**Suggested minimal fix:** Build UID and layer-visibility maps once per paint or cache them with appropriate invalidation. Cache immutable form data; batch drawing where possible. Reuse transformed points for unchanged poses. The measured UID index saved about 9.8 ms / 32% at 1,000 colliders but left substantial drawing cost.

## F3 — Broad preview invalidation repeats GUI preparation and unused vertex transfer

**Locations:** `newton/collision_view.py:53–61,73–85`; `newton/model.py:247–264`; `newton/session.py:198–204`; `newton/worker.py:330–335`.

The preview key uses global scene version. Any version change can therefore discard the preview and restart initialization, even when collider geometry is unchanged. After a 150 ms debounce, `prepare()` runs synchronously on the GUI thread, a new worker starts and compiles a complete model, and JSON is encoded on the GUI thread.

Every ordinary body specification includes all vertices, although analytic box and sphere worker branches do not use them. Compound specifications also include the top-level vertex payload in addition to their parts.

| Unused simple vertices | Payload | GUI encoding | Worker decoding |
| ---: | ---: | ---: | ---: |
| 100,000 | 1.70 MB | about 31 ms | about 21 ms |
| 250,000 | 4.25 MB | about 78 ms | about 54 ms |

**Impact:** Pure encoding can cause 30–80 ms GUI stalls, before geometry preparation, list construction, IPC, startup and model compilation. Their combined latency was not measured. The unnecessary payload also affects simulation startup; broad invalidation can repeat the cost while editing.

**Suggested minimal fix:** Send vertices only for shapes that need them and key preview reuse to collider-relevant changes. If moving preparation off-thread, take a well-defined snapshot first rather than reading live GUI/scene objects in a background thread.

## F4 — Synchronous process shutdown can block the event loop

**Locations:** `newton/collision_view.py:63–67`; `newton/session.py:399–406`.

Both paths call `kill()` followed immediately by `waitForFinished(1000)` on the GUI thread. Preview shutdown happens on invalidation, disabling and successful result consumption.

**Impact:** The callback can wait until shutdown or the 1,000 ms timeout. Actual kill/reap latency and incidence were not measured. The archived fake-process probe sleeps 500 ms and blocks for approximately 500 ms by construction; it demonstrates the synchronous control path, not real-world shutdown performance.

**Suggested minimal fix:** Use asynchronous completion and cleanup through `finished`, with timer-based escalation if needed. Keep old process callbacks isolated from current state and preserve safe object lifetime management.

## F5 — Telemetry repeats identical stylesheet assignments

**Location:** `newton/controls.py:710–724`, especially `:723`; direct signal connection in `newton/panel.py:277`.

Every telemetry update resets each available label stylesheet even when its `at_limit` state did not change. Repeated style/repolish work is added to text and tooltip updates.

| 100 labels | Original update | Identical stylesheet writes suppressed |
| --- | ---: | ---: |
| Constant values | 2.515 ms | 0.209 ms |
| Changing position and load | 2.526 ms | 1.290 ms |

Measurements include offscreen Qt event processing, use simplified labels and stub translation, and do not render the real control-panel grid.

**Impact:** About 1.2 ms saved per changing-value update, or 2.3 ms with constant values: roughly 7–14% of a 60 Hz frame budget. Fewer displayed joints reduce the absolute gain. Joints managed through virtual controls do not necessarily have standalone telemetry rows.

**Suggested minimal fix:** Change stylesheet only when limit state changes; skip unchanged rendered text/tooltips. If needed, decouple telemetry refresh rate from physics responses.

## F6 — Environment forces use a dense general-purpose path even for simple damping

**Location:** `newton/worker.py:653–662`; environment activation at `:463–466`.

Each affected body allocates both translation and rotation Jacobians on every substep. Purely linear damping still computes angular velocity and torque-related expressions. The dense operations span all model degrees of freedom.

**Impact:** In the 100-free-body test, linear damping increased an eight-step batch from 0.202 to 7.808 ms. The additional work is about 23% of the 33.3 ms simulated interval. Extra substeps multiply invocation counts. Local gravity overrides also select this path, though their separate cost was not benchmarked.

The profile does **not** establish that allocations alone dominate: the `zeros()` calls were a small fraction relative to Jacobian evaluation and matrix operations.

**Suggested minimal fix:** Skip inactive linear/rotational branches; evaluate MuJoCo body-velocity and force-application APIs as alternatives. Buffer reuse alone is unlikely to eliminate the whole cost. No speedup for this proposed change was verified.

## F7 — Metrics leave serialization and actual painting unattributed

**Locations:** `newton/worker.py:647–650,727`; `newton/session.py:210–260`; `newton/controls.py:726–734`; `newton/performance.py:11–17`.

- `output_ms` covers creating pose/joint output, not JSON encoding or pipe output.
- `ui_ms` starts after JSON decoding and ends before the eventual paint. Later metrics slots are excluded too.
- `roundtrip_ms` ends before the current apply/paint.
- `RealtimeMeter` measures simulation throughput, not frame pacing or input-to-display latency.

**Impact:** Diagnostic rather than direct runtime cost. Low solver/apply times can coexist with visible stutter; the collider paint measured above is outside `ui_ms`.

**Suggested minimal fix:** Measure encoding, decoding, apply and overlay paint separately. Record frame intervals and p95/p99; correlate target changes with result sequence IDs for interaction latency.

## Other reviewed paths

### Interaction and backpressure

`interaction.py:81–91` only replaces the latest drag target; it does not send IPC for every mouse event. Its linear mover search (`:63`) happens on click, not every physics frame. No extension-side drag race or expensive hover loop was demonstrated. Host picking cost was not investigated.

`session.py:267–277` permits one in-flight request and uses a 16 ms timer. This prevents an unbounded IPC queue. It also means new control/drag targets wait for the current batch and the next timer callback; multi-hundred-ms worker batches directly damage responsiveness. Elapsed simulation debt is capped at 100 ms instead of growing without bound. Actual end-to-end latency was not measured.

The worker is a separate process, not a Qt worker thread. Serialization, callbacks, widgets and collider drawing execute synchronously in the GUI event loop. The observed problems are not evidence that locks or additional Python threads are required.

### Virtual controls

`virtual_controls.py:116–126` interpolates linearly in affected joints. Validation and resolution scale with stored state values but are not repeated inside each physics substep. No significant runtime bottleneck was established.

### Throughput meter

`performance.py:11–17` uses a deque over approximately two seconds; sample pruning is amortized O(1). No meaningful computation bottleneck was identified.

### Full control-panel rebuild on selection changes — unmeasured

`controls.py:283–288` includes `detail_uid` in the build signature; changing axis selection can rebuild all strips rather than just their highlight. Expansion and binding changes also rebuild. Large control panels are a plausible editing-latency hotspot, but it is not a demonstrated per-frame rebuild and was not benchmarked. Prefer a separate highlight update before broader restructuring.

### Previously documented viewport cache issue — excluded

The repository already documents per-frame cache rebuilding in `docs/known-issues.md`. Its old host measurements were not rerun or independently validated and are not included as new evidence. This review makes no claim about the host's present implementation or which bottleneck dominates an actual scene.

## Missing tests and next actions

1. Attraction scaling at 10/50/100 bodies, one versus many sources, and multiple substeps. After optimization verify force agreement, momentum conservation, softening, coincident centers, fixed/connected bodies and long-term trajectories.
2. Large collider/telemetry benchmarks plus an event-loop heartbeat during preparation and process teardown. Record distributions, not only medians.
3. Verify analytic shapes without vertex payloads and that collider-irrelevant edits do not rebuild previews. Test invalidation during an active preview and asynchronous cleanup of stale processes.
4. Preserve the single-in-flight property under many drag/slider events, and assert that the latest target reaches the next eligible request.
5. Test attribution boundaries for serialization, apply and paint; report throughput and interaction/frame latency separately.

There were no unresolved clarification questions blocking this review. The principal unknown is workload relevance: attraction matters only when enabled; collider painting only when shown; ordinary-scene dominance requires a representative live measurement.

Recommended order: attraction first if used; otherwise collider lookup/drawing, preview initialization and asynchronous shutdown. Suppressing duplicate telemetry styles is the smallest measured quick win. No production fix was made and the host-dependent full test suite was not run.
