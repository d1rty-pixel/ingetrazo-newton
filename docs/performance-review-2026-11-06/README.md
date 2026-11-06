# Newton performance review — 6 November 2026

This directory archives the extension-only performance review requested in chat, its three experimental scripts, the available historical measurements and a fresh verification run. It contains no production performance fix.

## Contents

- [Review](review.md): prioritized findings, impact estimates, evidence, suggested minimal changes and missing tests.
- [Historical measurements](results/review-session.md): measurements reported during the original review; distinguishes reconstructed records from raw output.
- [Verification summary](results/verification-summary.md): fresh archival rerun, separate from the historical figures.
- [Archive validation](results/archive-validation.md): integrity checks and intentional raw-output whitespace.
- [Original chat response](transcript/review-response-de.txt): the German response preserved as a historical source record, not the project's English documentation.
- [Progress messages](transcript/progress-messages.txt): review progress messages and the explicit host-exclusion clarification.
- `scripts/newton_perf_review.py`, `scripts/newton_perf_followup.py`, `scripts/newton_perf_ui_followup.py`: byte-for-byte copies of the final temporary scripts, including their original machine-local paths. Intermediate overwritten versions were not retained.
- [Portable runner](scripts/run.py): runs those archived scripts without editing them, captures stdout/stderr and records provenance.
- `results/verification/`: complete raw output and environment/source hashes from the archival verification run.
- [Source manifest](source-manifest.json): reviewed revision, source hashes, original script hashes and preservation metadata.

## Scope and provenance

Reviewed files: `newton/worker.py`, `controls.py`, `interaction.py`, `collision_view.py`, `virtual_controls.py` and `performance.py`. Newton-internal supporting paths in `session.py`, `model.py`, `panel.py`, `range_control.py` and `binding_fields.py` were consulted. Existing tests and measurement records were read for context.

The reviewed checkout and the fresh `origin/main` used to create the archive branch were at `2e0d838bcd6298c3a36289d84f198e4f7d3d2da7`. The source manifest records the exact extension files, rather than relying only on that revision.

`ingetrazo-source/` is outside the review. The host repository was fetched and its revision checked before the user explicitly reiterated that it must be ignored; no host source was analyzed. The scripts retained here neither import nor inspect it. An initial pre-isolation script draft was overwritten before it was run and is not archived as an executable artifact.

The original review created only the three temporary Python scripts. No images, binary profiles or standalone historical result files were produced. Some original tool output was truncated in the conversation and no complete raw copy was available when archiving. `results/review-session.md` therefore labels the retained numeric record accurately; **new verification logs are not presented as original logs**. Unrelated earlier model-catalog/skill work and general repository inspection output are not part of this performance archive.

Two pre-existing local model modifications were excluded from the archive and commits: `models/industrial-robot-synchronous-gripper.igz` and `models/z0-contact-test.igz`. No fixture or production source was changed.

## Reproduce without the host

From the repository root, using the existing development environment:

```bash
.venv/bin/python -B docs/performance-review-2026-11-06/scripts/run.py --output /tmp/opencode/newton-review-rerun
```

The output directory must be absent or empty; existing results are never overwritten. On other machines, use another scratch output path. Dependencies: Python 3.12, MuJoCo, NumPy and PySide6. The recorded environment used MuJoCo 3.3.7, NumPy 2.5.4 and PySide6 6.11.3.

The runner substitutes only the original absolute repository path and temporary Qt settings path in memory, then executes each script in a fresh process with bytecode writes disabled and `QT_QPA_PLATFORM=offscreen`. It saves the exact executed source alongside stdout and stderr. Experimental method replacements remain process-local. The scripts do not read the user's models, start the full application or load host modules.

## Interpretation and limitations

- Timings are local synthetic medians, not application FPS, p95 latency or results for a representative production scene.
- Worker tests use separated free boxes without contacts, eight steps (33.3 ms simulation time), one substep and five timed repeats after warm-up.
- Attraction variants run sequentially on the same world, so their timed states are not identical. Weak forces and separated bodies reduce this confound but do not remove it. Force equivalence is checked at sampled states only, not over complete trajectories.
- The scalar summed-force variant reports its maximum force difference; the vectorized variant has an explicit `assert_allclose` check at `rtol=atol=1e-12`.
- Telemetry uses simplified labels and a stub translation function. Updates include offscreen event processing; widget count, visible area and platform affect the result.
- Collider tests simplify projection and omit faces, layers and selection. The indexed variant includes constructing the UID index in every measured paint. These results are not a universal lower bound for real viewports.
- The stop probe deliberately sleeps 500 ms in a fake process. It demonstrates synchronous waiting, not actual process shutdown time.
- JSON probes use repeated simple vertices. Real coordinate lengths, geometry preparation, list construction, IPC and model compilation are not included.
- Profiles perturb timings; profile durations must not replace unprofiled median measurements.
- The full host-dependent pytest suite was intentionally not run. Archival verification reruns all three isolated probes, including the vectorized force assertion.

The permanent scripts supersede `/tmp/opencode/newton_perf_*.py`; the three specifically archived temporary files are removed only after commit and push succeed.
